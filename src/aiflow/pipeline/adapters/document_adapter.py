"""Pipeline adapters for DocumentExtractorService (extract + acquire_from_email)."""

from __future__ import annotations

import re  # noqa: I001
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

logger = structlog.get_logger(__name__)


class ExtractDocumentInput(BaseModel):
    """Input schema for document extraction."""

    file_path: str = Field(..., description="Path to the document file")
    config_name: str | None = Field(None, description="Document type config name override")


class ExtractDocumentOutput(BaseModel):
    """Output schema for document extraction result."""

    document_id: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    validation_errors: list[str] = Field(default_factory=list)
    raw_text: str = ""


class DocumentExtractAdapter(BaseAdapter):
    """Adapter wrapping DocumentExtractorService.extract for pipeline use."""

    service_name = "document_extractor"
    method_name = "extract"
    input_schema = ExtractDocumentInput
    output_schema = ExtractDocumentOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.document_extractor.service import (
            DocumentExtractorConfig,
            DocumentExtractorService,
        )

        sf = await get_session_factory()
        svc = DocumentExtractorService(session_factory=sf, config=DocumentExtractorConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, ExtractDocumentInput):
            input_data = ExtractDocumentInput.model_validate(input_data)
        data = input_data
        svc = await self._get_service()

        result = await svc.extract(
            file_path=data.file_path,
            config_name=data.config_name,
        )

        return {
            "document_id": getattr(result, "invoice_id", getattr(result, "document_id", "")),
            "fields": getattr(result, "fields", {}),
            "confidence": getattr(result, "confidence", 0.0),
            "validation_errors": getattr(result, "validation_errors", []),
            "raw_text": getattr(result, "raw_text", ""),
        }


adapter_registry.register(DocumentExtractAdapter())


# ---------------------------------------------------------------------------
# Document acquisition adapter — download + parse from email
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+\.pdf", re.IGNORECASE)


def _compute_quality_score(raw_text: str, tables: list[dict[str, Any]], page_count: int) -> float:
    """Compute a simple quality score (0.0–1.0) for a parsed document.

    Factors:
    - Text length: >=200 chars → 0.3, >=1000 → 0.5
    - Has tables: +0.2
    - Multiple pages: +0.1
    - Has numeric content (amounts): +0.2
    """
    score = 0.0

    text_len = len(raw_text)
    if text_len >= 1000:
        score += 0.5
    elif text_len >= 200:
        score += 0.3
    elif text_len > 0:
        score += 0.1

    if tables:
        score += 0.2

    if page_count > 1:
        score += 0.1

    # Numeric content check (invoice amounts)
    if re.search(r"\d{1,3}[.,]\d{3}", raw_text):
        score += 0.2

    return min(score, 1.0)


class AcquireFromEmailInput(BaseModel):
    """Input schema for document acquisition from email."""

    email_id: str = Field(..., description="Source email message ID")
    attachments: list[str] = Field(default_factory=list, description="Attachment filenames")
    has_attachment: bool = Field(False, description="Whether the email has attachments")
    body_snippet: str = Field("", description="Email body text for URL extraction fallback")
    file_path: str = Field("", description="Direct file path if already downloaded")


class AcquiredDocumentOutput(BaseModel):
    """Output schema for a single acquired document."""

    email_id: str = ""
    file_name: str = ""
    file_path: str = ""
    raw_text: str = ""
    tables: list[dict[str, Any]] = Field(default_factory=list)
    page_count: int = 0
    parser_used: str = ""
    quality_score: float = 0.0
    source: str = ""  # "attachment" | "url" | "body"


class DocumentAcquireAdapter(BaseAdapter):
    """Adapter for acquiring documents from emails.

    Strategy:
    1. If attachment exists → download and parse via AttachmentProcessor
    2. If no attachment → extract PDF URLs from body → HTTP download → parse
    3. If nothing found → skip with warning
    """

    service_name = "document_extractor"
    method_name = "acquire_from_email"
    input_schema = AcquireFromEmailInput
    output_schema = AcquiredDocumentOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.document_extractor.service import (
            DocumentExtractorConfig,
            DocumentExtractorService,
        )

        sf = await get_session_factory()
        svc = DocumentExtractorService(session_factory=sf, config=DocumentExtractorConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, AcquireFromEmailInput):
            input_data = AcquireFromEmailInput.model_validate(input_data)
        data = input_data

        # Strategy 1: Direct file path provided
        if data.file_path:
            return await self._acquire_from_file(data.email_id, data.file_path)

        # Strategy 2: Attachments exist
        if data.has_attachment and data.attachments:
            pdf_attachments = [a for a in data.attachments if a.lower().endswith(".pdf")]
            if pdf_attachments:
                logger.info(
                    "acquire_from_attachment",
                    email_id=data.email_id,
                    attachment=pdf_attachments[0],
                )
                return {
                    "email_id": data.email_id,
                    "file_name": pdf_attachments[0],
                    "file_path": "",
                    "raw_text": "",
                    "tables": [],
                    "page_count": 0,
                    "parser_used": "pending_download",
                    "quality_score": 0.0,
                    "source": "attachment",
                }

        # Strategy 3: Extract URLs from body
        urls = URL_PATTERN.findall(data.body_snippet)
        if urls:
            logger.info(
                "acquire_from_url",
                email_id=data.email_id,
                url=urls[0],
            )
            return {
                "email_id": data.email_id,
                "file_name": urls[0].split("/")[-1],
                "file_path": "",
                "raw_text": "",
                "tables": [],
                "page_count": 0,
                "parser_used": "pending_download",
                "quality_score": 0.0,
                "source": "url",
            }

        # No document source found
        logger.warning("acquire_no_source", email_id=data.email_id)
        return {
            "email_id": data.email_id,
            "file_name": "",
            "file_path": "",
            "raw_text": "",
            "tables": [],
            "page_count": 0,
            "parser_used": "none",
            "quality_score": 0.0,
            "source": "",
        }

    async def _acquire_from_file(self, email_id: str, file_path: str) -> dict[str, Any]:
        """Parse an already-downloaded file via the document extractor service."""
        try:
            svc = await self._get_service()
            result = await svc.extract(file_path=file_path)

            raw_text = getattr(result, "raw_text", "")
            tables = getattr(result, "tables", [])
            if not isinstance(tables, list):
                tables = []
            page_count = getattr(result, "page_count", 1)
            parser_used = getattr(result, "parser_used", "unknown")

            quality = _compute_quality_score(raw_text, tables, page_count)

            from pathlib import Path

            logger.info(
                "acquire_from_file_complete",
                email_id=email_id,
                file_path=file_path,
                quality_score=round(quality, 3),
                parser_used=parser_used,
            )

            return {
                "email_id": email_id,
                "file_name": Path(file_path).name,
                "file_path": file_path,
                "raw_text": raw_text,
                "tables": tables,
                "page_count": page_count,
                "parser_used": parser_used,
                "quality_score": round(quality, 3),
                "source": "attachment",
            }
        except Exception as exc:
            logger.warning(
                "acquire_from_file_failed",
                email_id=email_id,
                file_path=file_path,
                error=str(exc),
            )
            return {
                "email_id": email_id,
                "file_name": "",
                "file_path": file_path,
                "raw_text": "",
                "tables": [],
                "page_count": 0,
                "parser_used": "failed",
                "quality_score": 0.0,
                "source": "attachment",
            }


adapter_registry.register(DocumentAcquireAdapter())
