"""UnstructuredParser — fast-path ParserProvider backed by the ``unstructured`` library.

Introduced by S95 (Sprint I / UC1 session 2). Handles the born-digital text
fast path: small PDFs (<=5MB), DOCX, TXT, HTML, MD. For anything the router
sends outside this set, it falls back to DoclingStandardParser via the
fallback chain on the RoutingDecision.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N6,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from aiflow.contracts.parser_result import ParserResult
from aiflow.providers.interfaces import ParserProvider
from aiflow.providers.metadata import ProviderMetadata

if TYPE_CHECKING:
    from aiflow.intake.package import IntakeFile, IntakePackage

__all__ = [
    "UnstructuredParser",
]

logger = structlog.get_logger(__name__)

_SUPPORTED_MIMES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/html",
        "text/markdown",
    }
)


class UnstructuredParser(ParserProvider):
    """``unstructured`` fast-path parser for born-digital text documents."""

    PROVIDER_NAME = "unstructured_fast"

    def __init__(self) -> None:
        self._metadata = ProviderMetadata(
            name=self.PROVIDER_NAME,
            version="0.22",
            supported_types=["pdf", "docx", "txt", "html", "md"],
            speed_class="fast",
            gpu_required=False,
            cost_class="free",
            license="Apache-2.0",
        )

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    async def parse(
        self,
        file: IntakeFile,
        package_context: IntakePackage,
    ) -> ParserResult:
        """Partition ``file`` with ``unstructured`` on a worker thread."""
        start = time.perf_counter()
        path = Path(file.file_path)

        def _do_parse() -> ParserResult:
            from unstructured.partition.auto import partition

            elements = partition(filename=str(path), strategy="fast")

            text_parts: list[str] = []
            markdown_parts: list[str] = []
            tables: list[dict[str, object]] = []
            page_numbers: set[int] = set()

            for element in elements:
                element_text = str(element).strip()
                if not element_text:
                    continue
                category = type(element).__name__
                text_parts.append(element_text)

                if category == "Title":
                    markdown_parts.append(f"# {element_text}")
                elif category == "Table":
                    md_table = _element_markdown(element) or element_text
                    markdown_parts.append(md_table)
                    tables.append(
                        {
                            "index": len(tables),
                            "markdown": md_table,
                            "caption": "",
                            "page_number": _element_page_number(element),
                        }
                    )
                else:
                    markdown_parts.append(element_text)

                page_no = _element_page_number(element)
                if page_no is not None:
                    page_numbers.add(page_no)

            duration_ms = (time.perf_counter() - start) * 1000.0
            return ParserResult(
                file_id=file.file_id,
                parser_name=self.PROVIDER_NAME,
                text="\n\n".join(text_parts),
                markdown="\n\n".join(markdown_parts),
                tables=tables,
                page_count=len(page_numbers),
                parse_duration_ms=duration_ms,
                metadata={
                    "mime_type": file.mime_type,
                    "file_size_bytes": file.size_bytes,
                    "element_count": len(elements),
                    "parser_used": "unstructured",
                    "package_id": str(package_context.package_id),
                    "tenant_id": package_context.tenant_id,
                },
            )

        result = await asyncio.to_thread(_do_parse)
        logger.info(
            "unstructured_fast_parse_done",
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
            logger.warning("unstructured_fast_health_check_failed", error=str(exc))
            return False

    @staticmethod
    def _import_check() -> None:
        from unstructured.partition.auto import partition  # noqa: F401

    async def estimate_cost(self, file: IntakeFile) -> float:
        """Self-hosted unstructured is free — returns 0.0."""
        return 0.0

    @classmethod
    def supports_mime(cls, mime_type: str) -> bool:
        return mime_type in _SUPPORTED_MIMES


def _element_page_number(element: object) -> int | None:
    metadata = getattr(element, "metadata", None)
    if metadata is None:
        return None
    page = getattr(metadata, "page_number", None)
    return int(page) if isinstance(page, int) else None


def _element_markdown(element: object) -> str:
    metadata = getattr(element, "metadata", None)
    if metadata is None:
        return ""
    html = getattr(metadata, "text_as_html", None)
    return str(html) if html else ""
