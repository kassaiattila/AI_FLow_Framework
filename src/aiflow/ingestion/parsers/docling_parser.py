"""Universal document parser powered by docling.

Docling handles PDF, DOCX, PPTX, XLSX, HTML, images, and more with
advanced features: table structure recognition, reading order detection,
layout analysis, code/formula extraction.

This replaces the individual pdf_parser.py and docx_parser.py stubs
with a single, more capable parser.

Usage:
    parser = DoclingParser()
    result = parser.parse("document.pdf")
    # result.text - full extracted text
    # result.markdown - markdown-formatted text (preserves tables, headings)
    # result.pages - per-page text (if applicable)
    # result.tables - extracted tables as markdown
    # result.metadata - document metadata
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["DoclingParser", "ParsedDocument", "ParsedPage", "ParsedTable"]

logger = structlog.get_logger(__name__)


class ParsedTable(BaseModel):
    """A table extracted from a document."""

    index: int = 0
    markdown: str = ""
    page_number: int | None = None
    caption: str = ""


class ParsedPage(BaseModel):
    """A single page from a parsed document."""

    page_number: int
    text: str = ""


class ParsedDocument(BaseModel):
    """Result of parsing a document with docling."""

    file_path: str
    file_name: str = ""
    file_type: str = ""
    text: str = ""
    markdown: str = ""
    pages: list[ParsedPage] = Field(default_factory=list)
    tables: list[ParsedTable] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0


class DoclingParser:
    """Universal document parser using docling.

    Supports: PDF, DOCX, PPTX, XLSX, HTML, MD, TXT, images
    Features: table recognition, layout analysis, reading order
    """

    def __init__(self, ocr_enabled: bool = False, max_pages: int = 50) -> None:
        self._ocr = ocr_enabled
        self._max_pages = max_pages
        self._converter = None

    def _get_converter(self) -> Any:
        """Lazy-load the docling DocumentConverter."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter

                self._converter = DocumentConverter()
                logger.info("docling_converter_initialized")
            except ImportError as exc:
                raise ImportError(
                    "docling is required for document parsing. Install with: pip install docling"
                ) from exc
        return self._converter

    def parse(self, file_path: str | Path) -> ParsedDocument:
        """Parse a document file and return structured content.

        Args:
            file_path: Path to the document file.

        Returns:
            ParsedDocument with text, markdown, pages, tables, metadata.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ImportError: If docling is not installed.
            ValueError: If file format is not supported.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        size_kb = path.stat().st_size // 1024
        logger.info("docling_parse_start", file=path.name, size_kb=size_kb)

        # Check page count for large PDFs — route to Azure DI or pypdfium2
        page_count = self._get_pdf_page_count(path)
        if page_count and page_count > self._max_pages:
            logger.warning(
                "docling_large_pdf",
                file=path.name,
                pages=page_count,
                max_pages=self._max_pages,
            )
            # Try Azure DI first (better quality), fallback to pypdfium2
            azure_result = self._try_azure_di(path)
            if azure_result:
                return azure_result
            logger.info("azure_di_unavailable_using_pypdfium2", file=path.name)
            return self._fallback_parse(path, page_count)

        try:
            converter = self._get_converter()
            result = converter.convert(str(path))

            # Extract markdown (preserves structure, tables, headings)
            markdown_text = result.document.export_to_markdown()

            # Extract plain text
            plain_text = self._markdown_to_plain(markdown_text)

            # Extract tables
            tables = self._extract_tables(result)
        except (RuntimeError, MemoryError, Exception) as e:
            err_str = str(e)
            if (
                "bad_alloc" in err_str
                or "memory" in err_str.lower()
                or "MemoryError" in type(e).__name__
            ):
                logger.warning("docling_memory_error", file=path.name, error=err_str)
                azure_result = self._try_azure_di(path)
                if azure_result:
                    return azure_result
                return self._fallback_parse(path, page_count or 0)
            raise

        # Build metadata
        metadata = {
            "source": str(path),
            "file_type": path.suffix.lstrip(".").lower(),
            "file_size_bytes": path.stat().st_size,
            "parser": "docling",
        }

        doc = ParsedDocument(
            file_path=str(path),
            file_name=path.name,
            file_type=path.suffix.lstrip(".").lower(),
            text=plain_text,
            markdown=markdown_text,
            tables=tables,
            metadata=metadata,
            page_count=page_count or 0,
            word_count=len(plain_text.split()),
            char_count=len(plain_text),
        )

        logger.info(
            "docling_parse_done",
            file=path.name,
            chars=doc.char_count,
            words=doc.word_count,
            tables=len(tables),
            pages=page_count,
        )
        return doc

    def parse_batch(self, file_paths: list[str | Path]) -> list[ParsedDocument]:
        """Parse multiple documents."""
        results = []
        for fp in file_paths:
            try:
                results.append(self.parse(fp))
            except Exception as e:
                logger.warning("docling_parse_failed", file=str(fp), error=str(e))
                results.append(
                    ParsedDocument(
                        file_path=str(fp),
                        file_name=Path(fp).name,
                        metadata={"error": str(e)},
                    )
                )
        return results

    def _extract_tables(self, result: Any) -> list[ParsedTable]:
        """Extract tables from docling result."""
        tables = []
        try:
            for i, table in enumerate(result.document.tables):
                md = (
                    table.export_to_markdown()
                    if hasattr(table, "export_to_markdown")
                    else str(table)
                )
                tables.append(
                    ParsedTable(
                        index=i,
                        markdown=md,
                        caption=getattr(table, "caption", ""),
                    )
                )
        except Exception:
            pass
        return tables

    def _try_azure_di(self, path: Path) -> ParsedDocument | None:
        """Try parsing with Azure Document Intelligence. Returns None if unavailable."""
        import os

        endpoint = os.environ.get("AZURE_DI_ENDPOINT", "")
        api_key = os.environ.get("AZURE_DI_API_KEY", "") or os.environ.get("AZURE_DI_KEY", "")
        enabled = os.environ.get("AZURE_DI_ENABLED", "false").lower() == "true"
        if not enabled or not endpoint or not api_key:
            return None

        try:
            import asyncio

            from aiflow.tools.azure_doc_intelligence import AzureDocIntelligence

            client = AzureDocIntelligence(endpoint, api_key)
            content = path.read_bytes()

            # Run async in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, client.analyze(content)).result()
            else:
                result = asyncio.run(client.analyze(content))

            text = result.get("text", "")
            tables = [
                ParsedTable(index=i, markdown=t.get("markdown", ""))
                for i, t in enumerate(result.get("tables", []))
            ]

            logger.info("azure_di_parse_done", file=path.name, chars=len(text), tables=len(tables))
            return ParsedDocument(
                file_path=str(path),
                file_name=path.name,
                file_type=path.suffix.lstrip(".").lower(),
                text=text,
                markdown=result.get("markdown", text),
                tables=tables,
                metadata={
                    "source": str(path),
                    "file_type": path.suffix.lstrip(".").lower(),
                    "file_size_bytes": path.stat().st_size,
                    "parser": "azure_document_intelligence",
                },
                page_count=self._get_pdf_page_count(path) or 0,
                word_count=len(text.split()),
                char_count=len(text),
            )
        except Exception as e:
            logger.warning("azure_di_failed", file=path.name, error=str(e))
            return None

    @staticmethod
    def _get_pdf_page_count(path: Path) -> int | None:
        """Get PDF page count without parsing the whole document."""
        if path.suffix.lower() != ".pdf":
            return None
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(path))
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return None

    def _fallback_parse(self, path: Path, page_count: int) -> ParsedDocument:
        """Fallback parser using pypdfium2 for large/problematic PDFs."""
        logger.info("fallback_parse_start", file=path.name, parser="pypdfium2")
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(path))
            pages_text: list[str] = []
            parsed_pages: list[ParsedPage] = []
            max_p = min(len(doc), self._max_pages)

            for i in range(max_p):
                try:
                    page = doc[i]
                    text = page.get_textpage().get_text_range()
                    pages_text.append(text)
                    parsed_pages.append(ParsedPage(page_number=i + 1, text=text))
                except Exception as e:
                    logger.debug("fallback_page_error", page=i + 1, error=str(e))

            doc.close()
            full_text = "\n\n".join(pages_text)

            logger.info("fallback_parse_done", file=path.name, pages=max_p, chars=len(full_text))
            return ParsedDocument(
                file_path=str(path),
                file_name=path.name,
                file_type=path.suffix.lstrip(".").lower(),
                text=full_text,
                markdown=full_text,
                pages=parsed_pages,
                metadata={
                    "source": str(path),
                    "file_type": path.suffix.lstrip(".").lower(),
                    "file_size_bytes": path.stat().st_size,
                    "parser": "pypdfium2_fallback",
                    "total_pages": page_count,
                    "parsed_pages": max_p,
                },
                page_count=page_count,
                word_count=len(full_text.split()),
                char_count=len(full_text),
            )
        except ImportError:
            logger.error("pypdfium2_not_installed")
            return ParsedDocument(
                file_path=str(path),
                file_name=path.name,
                metadata={"error": "pypdfium2 not installed for fallback"},
            )

    @staticmethod
    def _markdown_to_plain(markdown: str) -> str:
        """Simple markdown to plain text conversion."""
        import re

        text = markdown
        # Remove headers (# ## ###)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        # Remove bold/italic markers
        text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
        # Remove links [text](url) -> text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
        # Clean extra whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def supported_formats() -> list[str]:
        """Return list of supported file extensions."""
        return [
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
            ".html",
            ".htm",
            ".md",
            ".txt",
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".bmp",
        ]
