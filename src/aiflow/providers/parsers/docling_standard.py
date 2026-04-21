"""DoclingStandardParser — default ParserProvider for UC1 document processing.

Wraps the existing ``aiflow.ingestion.parsers.docling_parser.DoclingParser``
(sync API) into the async ``ParserProvider`` ABC introduced in Phase 1a.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N6,
        106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md Section 5.6,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel, Field

from aiflow.contracts.parser_result import ParserResult
from aiflow.providers.interfaces import ParserProvider
from aiflow.providers.metadata import ProviderMetadata

if TYPE_CHECKING:
    from aiflow.intake.package import IntakeFile, IntakePackage

__all__ = [
    "DoclingConfig",
    "DoclingStandardParser",
]

logger = structlog.get_logger(__name__)

_SUPPORTED_MIMES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/html",
        "text/markdown",
        "text/plain",
        "image/png",
        "image/jpeg",
        "image/tiff",
    }
)


class DoclingConfig(BaseModel):
    """Runtime config for DoclingStandardParser."""

    do_ocr: bool = Field(default=True, description="Run OCR on image/scanned content.")
    do_table_structure: bool = Field(
        default=True,
        description="Extract table structure (cells, spans, captions).",
    )
    max_pages: int = Field(
        default=50,
        ge=1,
        description="Large-PDF routing threshold; Docling itself falls back to pypdfium2 beyond this.",
    )


class DoclingStandardParser(ParserProvider):
    """Self-hosted Docling-backed parser. Free, CPU-bound, no network."""

    PROVIDER_NAME = "docling_standard"

    def __init__(self, config: DoclingConfig | None = None) -> None:
        self._config = config or DoclingConfig()
        self._metadata = ProviderMetadata(
            name=self.PROVIDER_NAME,
            version="2.84.0",
            supported_types=["pdf", "docx", "pptx", "xlsx", "html", "md", "txt", "png", "jpg"],
            speed_class="normal",
            gpu_required=False,
            cost_class="free",
            license="MIT",
        )

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    async def parse(
        self,
        file: IntakeFile,
        package_context: IntakePackage,
    ) -> ParserResult:
        """Parse ``file`` via Docling on a worker thread."""
        start = time.perf_counter()
        path = Path(file.file_path)

        def _do_parse() -> ParserResult:
            from aiflow.ingestion.parsers.docling_parser import DoclingParser

            parser = DoclingParser(
                ocr_enabled=self._config.do_ocr,
                max_pages=self._config.max_pages,
            )
            parsed = parser.parse(path)
            duration_ms = (time.perf_counter() - start) * 1000.0
            return ParserResult(
                file_id=file.file_id,
                parser_name=self.PROVIDER_NAME,
                text=parsed.text,
                markdown=parsed.markdown,
                tables=[t.model_dump() for t in parsed.tables],
                page_count=parsed.page_count,
                parse_duration_ms=duration_ms,
                metadata={
                    "mime_type": file.mime_type,
                    "file_size_bytes": file.size_bytes,
                    "word_count": parsed.word_count,
                    "char_count": parsed.char_count,
                    "parser_used": parsed.metadata.get("parser", "docling"),
                    "package_id": str(package_context.package_id),
                    "tenant_id": package_context.tenant_id,
                },
            )

        result = await asyncio.to_thread(_do_parse)
        logger.info(
            "docling_standard_parse_done",
            file_id=str(file.file_id),
            package_id=str(package_context.package_id),
            chars=len(result.text),
            pages=result.page_count,
            duration_ms=round(result.parse_duration_ms),
        )
        return result

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._import_check)
            return True
        except Exception as exc:
            logger.warning("docling_standard_health_check_failed", error=str(exc))
            return False

    @staticmethod
    def _import_check() -> None:
        from docling.document_converter import DocumentConverter  # noqa: F401

    async def estimate_cost(self, file: IntakeFile) -> float:
        """Self-hosted Docling is free — returns 0.0."""
        return 0.0

    @classmethod
    def supports_mime(cls, mime_type: str) -> bool:
        """Heuristic capability probe used by the PolicyEngine gate."""
        return mime_type in _SUPPORTED_MIMES
