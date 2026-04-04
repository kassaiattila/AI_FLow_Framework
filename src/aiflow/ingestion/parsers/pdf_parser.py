"""PDF parser — legacy interface.

DEPRECATED: Use ``aiflow.ingestion.parsers.docling_parser.DoclingParser`` instead.
DoclingParser handles PDF, DOCX, XLSX, and HTML via a single unified interface.
This module is retained for backward compatibility only.
"""

from __future__ import annotations

from pathlib import Path

import structlog
from pydantic import BaseModel

__all__ = ["PdfPage", "PdfParser"]

logger = structlog.get_logger(__name__)


class PdfPage(BaseModel):
    """One page extracted from a PDF."""

    text: str
    page_number: int


class PdfParser:
    """Parse PDF files into a list of :class:`PdfPage` objects.

    This is a placeholder; the real implementation will use ``pymupdf``.
    """

    def parse(self, file_path: str | Path) -> list[PdfPage]:
        """Parse *file_path* and return one :class:`PdfPage` per page.

        Raises ``ImportError`` if ``pymupdf`` is not installed, or
        ``FileNotFoundError`` if the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        try:
            import pymupdf  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "pymupdf is required for PDF parsing.  "
                "Install with: pip install 'aiflow[vectorstore]'"
            ) from exc

        # Placeholder: real implementation goes here
        logger.info("pdf.parse", file=str(path))
        return []
