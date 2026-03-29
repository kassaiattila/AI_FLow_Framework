"""Multi-layer attachment processor - docling (local) -> Azure DI (cloud) -> LLM vision."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
import structlog

__all__ = ["AttachmentProcessor", "ProcessedAttachment", "AttachmentConfig"]
logger = structlog.get_logger(__name__)


class AttachmentConfig(BaseModel):
    primary_processor: str = "docling"
    fallback_processor: str = "azure_di"
    azure_enabled: bool = False
    azure_endpoint: str = ""
    azure_api_key: str = ""
    azure_model: str = "prebuilt-layout"
    max_size_mb: int = 25


class ProcessedAttachment(BaseModel):
    filename: str
    mime_type: str = ""
    text: str = ""
    markdown: str = ""
    tables: list[dict] = Field(default_factory=list)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    processor_used: str = ""
    error: str = ""


class AttachmentProcessor:
    """Three-layer attachment processor: docling -> Azure DI -> LLM vision."""

    DOCLING_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/html",
        "text/markdown",
        "text/plain",
    }
    OCR_TYPES = {"image/png", "image/jpeg", "image/tiff", "image/bmp"}

    def __init__(self, config: AttachmentConfig | None = None):
        self.config = config or AttachmentConfig()

    async def process(
        self, filename: str, content: bytes, mime_type: str
    ) -> ProcessedAttachment:
        """Process attachment with intelligent routing.

        Cost-optimized 3-layer strategy:
        1. Docling (local, free, fast) - always try first for supported types
        2. Azure DI (cloud, paid) - ONLY when docling fails quality check:
           - Empty/too short text vs file size (= likely scan/image PDF)
           - Image files (PNG/JPG/TIFF) needing OCR
           - Docling returned text but quality is poor (ratio check)
        3. LLM Vision - images where text extraction isn't enough

        Azure DI cost: ~$1-10 per 1000 pages. Used sparingly.
        """
        if len(content) > self.config.max_size_mb * 1024 * 1024:
            return ProcessedAttachment(
                filename=filename, error=f"File too large: {len(content)} bytes"
            )

        file_size_kb = len(content) / 1024

        # --- Images: always need OCR (Azure DI or LLM Vision) ---
        if mime_type in self.OCR_TYPES:
            if self.config.azure_enabled:
                result = await self._process_azure(filename, content, mime_type)
                if result.text:
                    logger.info("azure_di_ocr_image", filename=filename, chars=len(result.text))
                    return result
            # Fallback: LLM Vision for images
            return await self._process_llm_vision(filename, content, mime_type)

        # --- Documents (PDF/DOCX/XLSX etc): try docling first ---
        if mime_type in self.DOCLING_TYPES or self._extension_matches_docling(filename):
            result = await self._process_docling(filename, content)

            if result.text:
                # Quality check: is the extracted text reasonable for the file size?
                chars_per_kb = len(result.text) / max(file_size_kb, 1)
                has_tables = len(result.tables) > 0

                # Heuristic: if very few chars per KB, might be scanned PDF
                is_likely_scan = chars_per_kb < 2.0 and file_size_kb > 50
                # Heuristic: very short text from a large file = poor extraction
                is_poor_quality = len(result.text) < 100 and file_size_kb > 100

                if is_likely_scan or is_poor_quality:
                    logger.info(
                        "docling_quality_low",
                        filename=filename,
                        chars=len(result.text),
                        file_kb=round(file_size_kb),
                        chars_per_kb=round(chars_per_kb, 1),
                        reason="likely_scan" if is_likely_scan else "poor_quality",
                    )
                    # Escalate to Azure DI for better OCR
                    if self.config.azure_enabled:
                        azure_result = await self._process_azure(filename, content, mime_type)
                        if azure_result.text and len(azure_result.text) > len(result.text):
                            logger.info(
                                "azure_di_improved",
                                filename=filename,
                                docling_chars=len(result.text),
                                azure_chars=len(azure_result.text),
                            )
                            return azure_result
                        # Azure didn't improve - keep docling result
                        logger.info("azure_di_no_improvement", filename=filename)

                # Docling result is good enough
                return result

            # Docling returned empty - try Azure DI
            logger.info("docling_empty", filename=filename, file_kb=round(file_size_kb))
            if self.config.azure_enabled:
                result = await self._process_azure(filename, content, mime_type)
                if result.text:
                    return result

        return ProcessedAttachment(
            filename=filename,
            mime_type=mime_type,
            error="Unsupported format or all processors failed",
            processor_used="none",
        )

    async def _process_docling(
        self, filename: str, content: bytes
    ) -> ProcessedAttachment:
        try:
            from aiflow.ingestion.parsers.docling_parser import DoclingParser

            parser = DoclingParser()

            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix, delete=False
            ) as f:
                f.write(content)
                f.flush()
                tmp_path = f.name

            parsed = parser.parse(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)

            return ProcessedAttachment(
                filename=filename,
                text=parsed.text,
                markdown=parsed.markdown,
                tables=[t.model_dump() for t in parsed.tables],
                metadata=parsed.metadata,
                processor_used="docling",
            )
        except Exception as e:
            logger.warning("docling_process_failed", filename=filename, error=str(e))
            return ProcessedAttachment(
                filename=filename, error=str(e), processor_used="docling_failed"
            )

    async def _process_azure(
        self, filename: str, content: bytes, mime_type: str
    ) -> ProcessedAttachment:
        try:
            from aiflow.tools.azure_doc_intelligence import AzureDocIntelligence

            client = AzureDocIntelligence(
                self.config.azure_endpoint, self.config.azure_api_key
            )
            result = await client.analyze(content, model=self.config.azure_model)

            return ProcessedAttachment(
                filename=filename,
                text=result.get("text", ""),
                markdown=result.get("markdown", ""),
                tables=result.get("tables", []),
                extracted_fields=result.get("key_value_pairs", {}),
                metadata={"azure_model": self.config.azure_model},
                processor_used="azure_di",
            )
        except Exception as e:
            logger.warning("azure_process_failed", filename=filename, error=str(e))
            return ProcessedAttachment(
                filename=filename, error=str(e), processor_used="azure_failed"
            )

    async def _process_llm_vision(
        self, filename: str, content: bytes, mime_type: str
    ) -> ProcessedAttachment:
        import base64

        b64 = base64.b64encode(content).decode("ascii")
        # Use ModelClient for vision (placeholder - actual implementation depends on LLM)
        return ProcessedAttachment(
            filename=filename,
            text=f"[Image: {filename}, {len(content)} bytes - LLM vision analysis pending]",
            metadata={"base64_length": len(b64)},
            processor_used="llm_vision_placeholder",
        )

    def _extension_matches_docling(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in {
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
            ".html",
            ".htm",
            ".md",
            ".txt",
        }
