"""Advanced parser service — multi-parser document extraction with fallback chain."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "ParserConfig",
    "ParsedDocument",
    "AdvancedParserConfig",
    "AdvancedParserService",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ParserConfig(BaseModel):
    """Configuration for a single parse operation."""

    parser: str = "auto"
    ocr_enabled: bool = True
    language: str = "hu"


class ParsedDocument(BaseModel):
    """Result of a document parse operation."""

    text: str = ""
    pages: int = 0
    parser_used: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0


class AdvancedParserConfig(ServiceConfig):
    """Service-level configuration."""

    default_parser: str = "auto"
    fallback_chain: list[str] = Field(
        default_factory=lambda: ["docling", "unstructured", "tesseract"]
    )
    max_file_size_mb: int = 100


# ---------------------------------------------------------------------------
# Supported extensions per parser
# ---------------------------------------------------------------------------

_DOCLING_EXTENSIONS = frozenset({
    ".pdf", ".docx", ".xlsx", ".pptx", ".html", ".htm", ".md", ".txt",
})

_UNSTRUCTURED_EXTENSIONS = frozenset({
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".html", ".htm", ".txt", ".md", ".csv", ".tsv", ".rtf", ".odt",
})

_TEXT_EXTENSIONS = frozenset({
    ".txt", ".md", ".csv", ".tsv", ".log", ".json", ".xml", ".yaml", ".yml",
    ".py", ".js", ".ts", ".html", ".htm", ".css",
})


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AdvancedParserService(BaseService):
    """Document parser with fallback chain: docling -> unstructured -> tesseract.

    For each file:
    1. Check extension compatibility
    2. Try docling (best for PDF, DOCX, XLSX)
    3. Fall back to unstructured if docling fails/unavailable
    4. Fall back to tesseract for scanned images
    5. Last resort: read as raw text
    """

    def __init__(self, config: AdvancedParserConfig | None = None) -> None:
        self._ext_config = config or AdvancedParserConfig()
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "advanced_parser"

    @property
    def service_description(self) -> str:
        return "Multi-parser document extraction with fallback chain"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    async def parse(
        self, file_path: str, config: ParserConfig | None = None
    ) -> ParsedDocument:
        """Parse a document file using the fallback chain.

        Args:
            file_path: Path to the document file.
            config: Parser configuration (parser choice, OCR, language).

        Returns:
            ParsedDocument with extracted text and metadata.
        """
        cfg = config or ParserConfig(parser=self._ext_config.default_parser)
        path = Path(file_path)

        if not path.exists():
            self._logger.error("file_not_found", path=file_path)
            return ParsedDocument(
                parser_used="none",
                metadata={"error": f"File not found: {file_path}"},
            )

        extension = path.suffix.lower()

        # Determine parser order
        chain = (
            [cfg.parser]
            if cfg.parser != "auto"
            else list(self._ext_config.fallback_chain)
        )

        # Try each parser in the chain
        for parser_name in chain:
            result = await self._try_parser(parser_name, path, extension, cfg)
            if result is not None:
                self._logger.info(
                    "parse_completed",
                    file=file_path,
                    parser=parser_name,
                    pages=result.pages,
                    text_length=len(result.text),
                )
                return result

        # Last resort: raw text read
        result = self._read_raw_text(path, extension)
        self._logger.info(
            "parse_fallback_raw",
            file=file_path,
            text_length=len(result.text),
        )
        return result

    # ------------------------------------------------------------------
    # Parser backends
    # ------------------------------------------------------------------

    async def _try_parser(
        self,
        parser_name: str,
        path: Path,
        extension: str,
        config: ParserConfig,
    ) -> ParsedDocument | None:
        """Attempt to parse with a specific parser backend."""
        dispatch = {
            "docling": self._parse_docling,
            "unstructured": self._parse_unstructured,
            "tesseract": self._parse_tesseract,
            "raw": self._parse_raw,
        }
        handler = dispatch.get(parser_name)
        if handler is None:
            self._logger.warning("unknown_parser", parser=parser_name)
            return None

        try:
            return await handler(path, extension, config)
        except Exception as exc:
            self._logger.warning(
                "parser_failed",
                parser=parser_name,
                file=str(path),
                error=str(exc),
            )
            return None

    async def _parse_docling(
        self, path: Path, extension: str, config: ParserConfig
    ) -> ParsedDocument | None:
        """Parse using docling library."""
        if extension not in _DOCLING_EXTENSIONS:
            return None

        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(str(path))
            text = result.document.export_to_markdown()

            return ParsedDocument(
                text=text,
                pages=max(1, text.count("\n---\n") + 1),
                parser_used="docling",
                metadata={
                    "source": str(path),
                    "extension": extension,
                },
                confidence=0.9,
            )
        except ImportError:
            self._logger.debug("docling_not_installed")
            return None

    async def _parse_unstructured(
        self, path: Path, extension: str, config: ParserConfig
    ) -> ParsedDocument | None:
        """Parse using unstructured library."""
        if extension not in _UNSTRUCTURED_EXTENSIONS:
            return None

        try:
            from unstructured.partition.auto import partition

            elements = partition(filename=str(path))
            text = "\n\n".join(str(el) for el in elements)

            return ParsedDocument(
                text=text,
                pages=max(1, len(elements) // 10),
                parser_used="unstructured",
                metadata={
                    "source": str(path),
                    "extension": extension,
                    "element_count": len(elements),
                },
                confidence=0.8,
            )
        except ImportError:
            self._logger.debug("unstructured_not_installed")
            return None

    async def _parse_tesseract(
        self, path: Path, extension: str, config: ParserConfig
    ) -> ParsedDocument | None:
        """Parse using tesseract OCR (for scanned images/PDFs)."""
        if not config.ocr_enabled:
            return None

        image_extensions = frozenset({".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"})
        if extension not in image_extensions and extension != ".pdf":
            return None

        try:
            import pytesseract
            from PIL import Image

            if extension == ".pdf":
                # For PDF, would need pdf2image — return None to fall through
                return None

            img = Image.open(path)
            text = pytesseract.image_to_string(img, lang=config.language)

            return ParsedDocument(
                text=text,
                pages=1,
                parser_used="tesseract",
                metadata={
                    "source": str(path),
                    "extension": extension,
                    "ocr_language": config.language,
                },
                confidence=0.6,
            )
        except ImportError:
            self._logger.debug("tesseract_not_installed")
            return None

    async def _parse_raw(
        self, path: Path, extension: str, config: ParserConfig
    ) -> ParsedDocument | None:
        """Read file as raw text."""
        return self._read_raw_text(path, extension)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read_raw_text(self, path: Path, extension: str) -> ParsedDocument:
        """Read file as UTF-8 text (last resort)."""
        if extension not in _TEXT_EXTENSIONS:
            return ParsedDocument(
                text="",
                parser_used="raw",
                metadata={
                    "source": str(path),
                    "error": f"Unsupported extension for raw read: {extension}",
                },
                confidence=0.1,
            )

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            return ParsedDocument(
                text=text,
                pages=max(1, text.count("\n\n") + 1),
                parser_used="raw",
                metadata={"source": str(path), "extension": extension},
                confidence=0.4,
            )
        except Exception as exc:
            return ParsedDocument(
                text="",
                parser_used="raw",
                metadata={"source": str(path), "error": str(exc)},
                confidence=0.0,
            )
