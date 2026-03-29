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
        """Process an attachment through the appropriate processor."""
        if len(content) > self.config.max_size_mb * 1024 * 1024:
            return ProcessedAttachment(
                filename=filename, error=f"File too large: {len(content)} bytes"
            )

        result = ProcessedAttachment(filename=filename, mime_type=mime_type)

        # Layer 1: Docling (local, free)
        if mime_type in self.DOCLING_TYPES or self._extension_matches_docling(filename):
            result = await self._process_docling(filename, content)
            if result.text:
                return result
            logger.info("docling_fallback", filename=filename, reason="empty result")

        # Layer 2: Azure Document Intelligence (cloud, OCR)
        if self.config.azure_enabled and (
            mime_type in self.OCR_TYPES or not result.text
        ):
            result = await self._process_azure(filename, content, mime_type)
            if result.text:
                return result

        # Layer 3: LLM Vision (for images)
        if mime_type.startswith("image/"):
            return await self._process_llm_vision(filename, content, mime_type)

        return ProcessedAttachment(
            filename=filename,
            mime_type=mime_type,
            error="Unsupported format",
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
