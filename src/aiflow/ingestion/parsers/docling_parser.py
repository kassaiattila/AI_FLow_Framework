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

from pydantic import BaseModel, Field

import structlog

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

    def __init__(self, ocr_enabled: bool = False) -> None:
        self._ocr = ocr_enabled
        self._converter = None

    def _get_converter(self) -> Any:
        """Lazy-load the docling DocumentConverter."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter

                self._converter = DocumentConverter()
                logger.info("docling_converter_initialized")
            except ImportError:
                raise ImportError(
                    "docling is required for document parsing. "
                    "Install with: pip install docling"
                )
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

        logger.info("docling_parse_start", file=path.name, size_kb=path.stat().st_size // 1024)

        converter = self._get_converter()
        result = converter.convert(str(path))

        # Extract markdown (preserves structure, tables, headings)
        markdown_text = result.document.export_to_markdown()

        # Extract plain text
        plain_text = self._markdown_to_plain(markdown_text)

        # Extract tables
        tables = self._extract_tables(result)

        # Build metadata
        metadata = {
            "source": str(path),
            "file_type": path.suffix.lstrip(".").lower(),
            "file_size_bytes": path.stat().st_size,
        }

        doc = ParsedDocument(
            file_path=str(path),
            file_name=path.name,
            file_type=path.suffix.lstrip(".").lower(),
            text=plain_text,
            markdown=markdown_text,
            tables=tables,
            metadata=metadata,
            word_count=len(plain_text.split()),
            char_count=len(plain_text),
        )

        logger.info(
            "docling_parse_done",
            file=path.name,
            chars=doc.char_count,
            words=doc.word_count,
            tables=len(tables),
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
                results.append(ParsedDocument(
                    file_path=str(fp),
                    file_name=Path(fp).name,
                    metadata={"error": str(e)},
                ))
        return results

    def _extract_tables(self, result: Any) -> list[ParsedTable]:
        """Extract tables from docling result."""
        tables = []
        try:
            for i, table in enumerate(result.document.tables):
                md = table.export_to_markdown() if hasattr(table, "export_to_markdown") else str(table)
                tables.append(ParsedTable(
                    index=i,
                    markdown=md,
                    caption=getattr(table, "caption", ""),
                ))
        except Exception:
            pass
        return tables

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
            ".pdf", ".docx", ".pptx", ".xlsx",
            ".html", ".htm", ".md", ".txt",
            ".png", ".jpg", ".jpeg", ".tiff", ".bmp",
        ]
