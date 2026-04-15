"""Document Extractor service — configurable document field extraction.

Generalizes invoice_processor into a config-driven extraction service.
Supports any document type via document_type_configs DB table.

Pipeline: parse (Docling) → extract (LLM) → validate → store → export
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiflow.services.base import BaseService, ServiceConfig

if TYPE_CHECKING:
    from aiflow.intake.package import IntakePackage

__all__ = [
    "DocumentTypeConfig",
    "ExtractionResult",
    "DocumentExtractorConfig",
    "DocumentExtractorService",
]

logger = structlog.get_logger(__name__)


class FieldDefinition(BaseModel):
    """A single field to extract from a document."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None


class DocumentTypeConfig(BaseModel):
    """Configuration for a document type (loaded from DB)."""

    id: str = ""
    name: str
    display_name: str = ""
    document_type: str = ""
    description: str = ""
    parser: str = "docling"
    extraction_model: str = "openai/gpt-4o"
    fields: list[FieldDefinition] = []
    validation_rules: list[str] = []
    output_formats: list[str] = Field(default_factory=lambda: ["json"])
    customer: str = "default"
    enabled: bool = True


class ExtractionResult(BaseModel):
    """Result of extracting data from a single document."""

    source_file: str
    config_name: str = ""
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    is_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)
    parser_used: str = ""
    raw_text: str = ""
    raw_markdown: str = ""
    extraction_time_ms: float = 0.0
    db_id: str | None = None


class DocumentExtractorConfig(ServiceConfig):
    """Service-level config for the Document Extractor."""

    upload_dir: str = "./data/uploads"
    default_config_name: str = "invoice-hu"


class DocumentExtractorService(BaseService):
    """Configurable document extraction service.

    Uses DoclingParser for document parsing, LLM for field extraction,
    and stores results in PostgreSQL.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        config: DocumentExtractorConfig | None = None,
    ) -> None:
        self._ext_config = config or DocumentExtractorConfig()
        self._session_factory = session_factory
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "document_extractor"

    @property
    def service_description(self) -> str:
        return "Configurable document field extraction (Docling + LLM)"

    async def _start(self) -> None:
        Path(self._ext_config.upload_dir).mkdir(parents=True, exist_ok=True)

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        try:
            async with self._session_factory() as session:
                r = await session.execute(text("SELECT 1"))
                return r.scalar() == 1
        except Exception:
            return False

    # --- Config CRUD ---

    async def list_configs(self, customer: str = "default") -> list[DocumentTypeConfig]:
        """List all document type configurations."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, name, display_name, document_type, description,
                           parser, extraction_model, fields, validation_rules,
                           output_formats, customer, enabled
                    FROM document_type_configs
                    WHERE customer = :customer OR customer = 'default'
                    ORDER BY name
                """),
                {"customer": customer},
            )
            return [self._row_to_config(row) for row in result.fetchall()]

    async def get_config(self, name: str) -> DocumentTypeConfig | None:
        """Get a document type config by name."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, name, display_name, document_type, description,
                           parser, extraction_model, fields, validation_rules,
                           output_formats, customer, enabled
                    FROM document_type_configs
                    WHERE name = :name
                """),
                {"name": name},
            )
            row = result.fetchone()
            return self._row_to_config(row) if row else None

    async def create_config(self, config: DocumentTypeConfig) -> DocumentTypeConfig:
        """Create a new document type configuration."""
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO document_type_configs
                        (name, display_name, document_type, description,
                         parser, extraction_model, fields, validation_rules,
                         output_formats, customer, enabled)
                    VALUES (:name, :display_name, :document_type, :description,
                            :parser, :extraction_model,
                            CAST(:fields AS jsonb), CAST(:validation_rules AS jsonb),
                            CAST(:output_formats AS jsonb), :customer, :enabled)
                """),
                {
                    "name": config.name,
                    "display_name": config.display_name,
                    "document_type": config.document_type,
                    "description": config.description,
                    "parser": config.parser,
                    "extraction_model": config.extraction_model,
                    "fields": json.dumps([f.model_dump() for f in config.fields]),
                    "validation_rules": json.dumps(config.validation_rules),
                    "output_formats": json.dumps(config.output_formats),
                    "customer": config.customer,
                    "enabled": config.enabled,
                },
            )
            await session.commit()
            self._logger.info("config_created", name=config.name)
            return config

    # --- Extraction pipeline ---

    async def extract(
        self,
        file_path: str | Path,
        config_name: str | None = None,
    ) -> ExtractionResult:
        """Extract fields from a document using the configured pipeline.

        .. deprecated:: 1.4.0
            Use :meth:`extract_from_package` with an :class:`IntakePackage` instead.
        """
        import warnings

        warnings.warn(
            "extract(file_path) is deprecated in v1.4.0. "
            "Use extract_from_package(package) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        start = time.time()

        # Defensive: reject empty / missing paths before Path("") → "."
        if not file_path or str(file_path).strip() in ("", "."):
            raise ValueError("file_path is required for document extraction")
        file_path = Path(file_path)
        if not file_path.exists():
            raise ValueError(f"file_path does not exist: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"file_path is not a file: {file_path}")

        config_name = config_name or self._ext_config.default_config_name

        # Load config
        doc_config = await self.get_config(config_name)
        if not doc_config:
            raise ValueError(f"Document type config '{config_name}' not found")

        # Step 1: Parse with Docling
        parsed = await self._parse_document(file_path, doc_config.parser)

        # Step 2: Extract fields with LLM
        extracted = await self._extract_fields(
            parsed["text"],
            parsed["markdown"],
            doc_config,
        )

        # Step 3: Validate
        errors = self._validate_fields(extracted, doc_config)

        # Step 4: Store in DB
        raw_hash = hashlib.sha256(parsed["text"].encode()).hexdigest()[:32]
        db_id = await self._store_result(
            file_path, config_name, extracted, errors, parsed, raw_hash, doc_config
        )

        elapsed = (time.time() - start) * 1000
        self._logger.info(
            "document_extracted",
            file=file_path.name,
            config=config_name,
            fields=len(extracted),
            errors=len(errors),
            time_ms=round(elapsed),
        )

        return ExtractionResult(
            source_file=file_path.name,
            config_name=config_name,
            extracted_fields=extracted,
            confidence=extracted.get("_confidence", 0.0),
            is_valid=len(errors) == 0,
            validation_errors=errors,
            parser_used=parsed.get("parser_used", "docling"),
            raw_text=parsed["text"][:500],
            raw_markdown=parsed["markdown"][:500],
            extraction_time_ms=elapsed,
            db_id=db_id,
        )

    async def extract_from_package(
        self,
        package: IntakePackage,
        config_name: str | None = None,
    ) -> ExtractionResult:
        """Extract fields from an IntakePackage (v2 primary API).

        Full implementation in Phase 1c. Phase 1a raises NotImplementedError.
        """

        raise NotImplementedError(
            "extract_from_package() is a Phase 1a skeleton. "
            "Full implementation arrives in Phase 1c."
        )

    def _build_single_file_package(
        self,
        file_path: str | Path,
        tenant_id: str = "default",
    ) -> IntakePackage:
        """Build an IntakePackage from a single file path (shim helper)."""
        import hashlib as _hashlib
        import mimetypes
        from uuid import uuid4

        from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType

        fp = Path(file_path)
        sha256 = _hashlib.sha256(fp.read_bytes()).hexdigest()
        mime_type = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
        return IntakePackage(
            package_id=uuid4(),
            source_type=IntakeSourceType.FILE_UPLOAD,
            tenant_id=tenant_id,
            files=[
                IntakeFile(
                    file_id=uuid4(),
                    file_path=str(fp),
                    file_name=fp.name,
                    mime_type=mime_type,
                    size_bytes=fp.stat().st_size,
                    sha256=sha256,
                )
            ],
        )

    async def _parse_document(self, file_path: Path, parser: str) -> dict[str, Any]:
        """Parse document with Docling (or fallback)."""
        import asyncio

        from aiflow.ingestion.parsers.docling_parser import DoclingParser

        def _parse():
            p = DoclingParser()
            result = p.parse(file_path)
            return {
                "text": result.text,
                "markdown": result.markdown,
                "tables": [t.model_dump() for t in result.tables],
                "page_count": result.page_count,
                "parser_used": "docling",
            }

        try:
            return await asyncio.to_thread(_parse)
        except Exception as exc:
            self._logger.warning("docling_parse_failed", file=str(file_path), error=str(exc))
            # Fallback: read raw text
            try:
                raw = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                raw = f"[Could not read file: {file_path.name}]"
            return {
                "text": raw[:50000],
                "markdown": raw[:50000],
                "tables": [],
                "page_count": 0,
                "parser_used": "fallback",
            }

    async def _extract_fields(
        self,
        text: str,
        markdown: str,
        config: DocumentTypeConfig,
    ) -> dict[str, Any]:
        """Extract fields from document text using LLM."""
        from aiflow.models.backends.litellm_backend import LiteLLMBackend
        from aiflow.models.client import ModelClient

        # Build dynamic prompt from field definitions
        field_descriptions = "\n".join(
            f"- {f.name} ({f.type}): {f.description}" + (" [REQUIRED]" if f.required else "")
            for f in config.fields
        )

        field_names_json = json.dumps({f.name: f"<{f.type}>" for f in config.fields}, indent=2)

        system_prompt = f"""You are a document data extractor. Extract the following fields from the provided {config.document_type} document.

Fields to extract:
{field_descriptions}

Return a JSON object with exactly these field names. Use null for fields you cannot find.
Include a "_confidence" field (0.0-1.0) indicating overall extraction confidence.

Expected output format:
{field_names_json}
"""

        user_prompt = f"Extract the fields from this document:\n\n{markdown[:8000]}"

        try:
            backend = LiteLLMBackend(default_model=config.extraction_model)
            client = ModelClient(generation_backend=backend)
            result = await client.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=config.extraction_model,
                temperature=0.0,
            )
            # Strip ```json markdown wrapper if present (LLMs often add it)
            output_text = result.output.text.strip()
            if output_text.startswith("```"):
                import re

                output_text = re.sub(r"^```(?:json)?\s*\n?", "", output_text)
                output_text = re.sub(r"\n?```\s*$", "", output_text)
            return json.loads(output_text.strip())
        except Exception as exc:
            self._logger.error("llm_extraction_failed", error=str(exc))
            # Return empty fields with 0 confidence
            return {f.name: f.default for f in config.fields} | {"_confidence": 0.0}

    def _validate_fields(self, extracted: dict[str, Any], config: DocumentTypeConfig) -> list[str]:
        """Validate extracted fields against config rules."""
        errors = []

        # Check required fields
        for field in config.fields:
            if field.required and not extracted.get(field.name):
                errors.append(f"Required field '{field.name}' is missing or empty")

        # Check validation rules (simple expression evaluation)
        for rule in config.validation_rules:
            try:
                # Safe eval for simple math expressions
                local_vars = {
                    k: v
                    for k, v in extracted.items()
                    if isinstance(v, (int, float)) and k != "_confidence"
                }
                if local_vars and not eval(rule, {"__builtins__": {}}, local_vars):  # noqa: S307
                    errors.append(f"Validation rule failed: {rule}")
            except Exception:
                pass  # Skip rules that can't be evaluated

        return errors

    async def _store_result(
        self,
        file_path: Path,
        config_name: str,
        extracted: dict[str, Any],
        errors: list[str],
        parsed: dict[str, Any],
        raw_hash: str,
        config: DocumentTypeConfig,
    ) -> str | None:
        """Store extraction result in the invoices table."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    text("""
                        INSERT INTO invoices (
                            source_file, direction, config_name,
                            vendor_name, vendor_address, vendor_tax_number,
                            buyer_name, buyer_address, buyer_tax_number,
                            invoice_number, invoice_date, currency,
                            net_total, vat_total, gross_total,
                            is_valid, validation_errors, confidence_score,
                            parser_used, extraction_model, raw_text_hash,
                            customer
                        ) VALUES (
                            :source_file, :direction, :config_name,
                            :vendor_name, :vendor_address, :vendor_tax_number,
                            :buyer_name, :buyer_address, :buyer_tax_number,
                            :invoice_number, :invoice_date, :currency,
                            :net_total, :vat_total, :gross_total,
                            :is_valid, CAST(:validation_errors AS jsonb), :confidence_score,
                            :parser_used, :extraction_model, :raw_text_hash,
                            :customer
                        )
                        ON CONFLICT (source_file, raw_text_hash) DO UPDATE SET
                            vendor_name = EXCLUDED.vendor_name,
                            confidence_score = EXCLUDED.confidence_score,
                            updated_at = NOW()
                        RETURNING id
                    """),
                    {
                        "source_file": file_path.name,
                        "direction": extracted.get("direction", ""),
                        "config_name": config_name,
                        "vendor_name": extracted.get("vendor_name", ""),
                        "vendor_address": extracted.get("vendor_address", ""),
                        "vendor_tax_number": extracted.get("vendor_tax_number", ""),
                        "buyer_name": extracted.get("buyer_name", ""),
                        "buyer_address": extracted.get("buyer_address", ""),
                        "buyer_tax_number": extracted.get("buyer_tax_number", ""),
                        "invoice_number": extracted.get("invoice_number", ""),
                        "invoice_date": extracted.get("invoice_date"),
                        "currency": extracted.get("currency", "HUF"),
                        "net_total": extracted.get("net_total"),
                        "vat_total": extracted.get("vat_total"),
                        "gross_total": extracted.get("gross_total"),
                        "is_valid": len(errors) == 0,
                        "validation_errors": json.dumps(errors),
                        "confidence_score": extracted.get("_confidence", 0.0),
                        "parser_used": parsed.get("parser_used", "docling"),
                        "extraction_model": config.extraction_model,
                        "raw_text_hash": raw_hash,
                        "customer": config.customer,
                    },
                )
                row = result.fetchone()
                await session.commit()
                db_id = str(row[0]) if row else None
                self._logger.info("extraction_stored", db_id=db_id)
                return db_id
        except Exception as exc:
            self._logger.error("store_failed", error=str(exc))
            return None

    # --- Verification ---

    async def verify(
        self,
        invoice_id: str,
        verified_fields: dict[str, Any],
        verified_by: str = "user",
    ) -> bool:
        """Mark an extracted document as verified with corrected fields."""
        async with self._session_factory() as session:
            # Update verification status
            await session.execute(
                text("""
                    UPDATE invoices SET
                        verified = true,
                        verified_by = :verified_by,
                        verified_at = NOW(),
                        verified_fields = CAST(:fields AS jsonb),
                        -- Also update the corrected field values
                        vendor_name = COALESCE(:vendor_name, vendor_name),
                        buyer_name = COALESCE(:buyer_name, buyer_name),
                        invoice_number = COALESCE(:invoice_number, invoice_number),
                        net_total = COALESCE(:net_total, net_total),
                        vat_total = COALESCE(:vat_total, vat_total),
                        gross_total = COALESCE(:gross_total, gross_total),
                        updated_at = NOW()
                    WHERE id = CAST(:id AS uuid)
                """),
                {
                    "id": invoice_id,
                    "verified_by": verified_by,
                    "fields": json.dumps(verified_fields),
                    "vendor_name": verified_fields.get("vendor_name"),
                    "buyer_name": verified_fields.get("buyer_name"),
                    "invoice_number": verified_fields.get("invoice_number"),
                    "net_total": verified_fields.get("net_total"),
                    "vat_total": verified_fields.get("vat_total"),
                    "gross_total": verified_fields.get("gross_total"),
                },
            )
            await session.commit()
            self._logger.info("document_verified", invoice_id=invoice_id, by=verified_by)
            return True

    async def get_invoice(self, invoice_id: str) -> dict[str, Any] | None:
        """Get a single invoice by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, source_file, direction, config_name,
                           vendor_name, vendor_address, vendor_tax_number,
                           buyer_name, buyer_address, buyer_tax_number,
                           invoice_number, invoice_date, currency,
                           net_total, vat_total, gross_total,
                           is_valid, validation_errors, confidence_score,
                           parser_used, verified, verified_by, verified_at,
                           verified_fields, created_at
                    FROM invoices WHERE id = CAST(:id AS uuid)
                """),
                {"id": invoice_id},
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                "id": str(row[0]),
                "source_file": row[1],
                "direction": row[2] or "",
                "config_name": row[3] or "",
                "vendor_name": row[4] or "",
                "vendor_address": row[5] or "",
                "vendor_tax_number": row[6] or "",
                "buyer_name": row[7] or "",
                "buyer_address": row[8] or "",
                "buyer_tax_number": row[9] or "",
                "invoice_number": row[10] or "",
                "invoice_date": str(row[11]) if row[11] else "",
                "currency": row[12] or "HUF",
                "net_total": float(row[13]) if row[13] else 0,
                "vat_total": float(row[14]) if row[14] else 0,
                "gross_total": float(row[15]) if row[15] else 0,
                "is_valid": row[16],
                "validation_errors": row[17] or [],
                "confidence_score": float(row[18]) if row[18] else 0,
                "parser_used": row[19] or "",
                "verified": row[20] or False,
                "verified_by": row[21] or "",
                "verified_at": str(row[22]) if row[22] else None,
                "verified_fields": row[23] or {},
                "created_at": str(row[24]) if row[24] else "",
                "source": "backend",
            }

    # --- Helpers ---

    @staticmethod
    def _row_to_config(row: Any) -> DocumentTypeConfig:
        return DocumentTypeConfig(
            id=str(row[0]),
            name=row[1],
            display_name=row[2] or "",
            document_type=row[3] or "",
            description=row[4] or "",
            parser=row[5] or "docling",
            extraction_model=row[6] or "openai/gpt-4o",
            fields=[FieldDefinition(**f) for f in (row[7] or [])],
            validation_rules=row[8] or [],
            output_formats=row[9] or ["json"],
            customer=row[10] or "default",
            enabled=row[11] if row[11] is not None else True,
        )
