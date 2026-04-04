"""DOCX parser — legacy interface.

DEPRECATED: Use ``aiflow.ingestion.parsers.docling_parser.DoclingParser`` instead.
DoclingParser handles PDF, DOCX, XLSX, and HTML via a single unified interface.
This module is retained for backward compatibility only.
"""

from __future__ import annotations

from pathlib import Path

import structlog
from pydantic import BaseModel

__all__ = ["DocxParagraph", "DocxParser"]

logger = structlog.get_logger(__name__)


class DocxParagraph(BaseModel):
    """A single paragraph extracted from a DOCX file."""

    text: str
    style: str = ""
    index: int = 0


class DocxParser:
    """Parse DOCX files into a list of :class:`DocxParagraph` objects.

    This is a placeholder; the real implementation will use ``python-docx``.
    """

    def parse(self, file_path: str | Path) -> list[DocxParagraph]:
        """Parse *file_path* and return one :class:`DocxParagraph` per paragraph.

        Raises ``ImportError`` if ``python-docx`` is not installed, or
        ``FileNotFoundError`` if the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"DOCX file not found: {path}")

        try:
            import docx  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "python-docx is required for DOCX parsing.  Install with: pip install python-docx"
            ) from exc

        # Placeholder: real implementation goes here
        logger.info("docx.parse", file=str(path))
        return []
