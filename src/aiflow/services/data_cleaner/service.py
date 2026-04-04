"""Data cleaner service — LLM-based document cleanup and normalization."""

from __future__ import annotations

import re

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "CleaningConfig",
    "CleanedDocument",
    "DataCleanerConfig",
    "DataCleanerService",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CleaningConfig(BaseModel):
    """Configuration for a single cleaning operation."""

    remove_headers_footers: bool = True
    fix_ocr_errors: bool = True
    normalize_whitespace: bool = True
    language: str = "hu"


class CleanedDocument(BaseModel):
    """Result of a document cleaning operation."""

    cleaned_text: str
    original_length: int
    cleaned_length: int
    removed_sections: list[str] = Field(default_factory=list)


class DataCleanerConfig(ServiceConfig):
    """Service-level configuration."""

    max_document_length: int = 500_000
    default_language: str = "hu"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DataCleanerService(BaseService):
    """Document cleanup service for pre-processing text before RAG ingestion.

    Supports:
    - Whitespace normalization (implemented in pure Python)
    - Header/footer removal (stub — needs heuristic/LLM)
    - OCR error correction (stub — needs LLM)
    """

    def __init__(self, config: DataCleanerConfig | None = None) -> None:
        self._ext_config = config or DataCleanerConfig()
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "data_cleaner"

    @property
    def service_description(self) -> str:
        return "LLM-based document cleanup and normalization"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Clean
    # ------------------------------------------------------------------

    async def clean(
        self, text: str, config: CleaningConfig | None = None
    ) -> CleanedDocument:
        """Clean a single document.

        Args:
            text: Raw document text.
            config: Cleaning options.

        Returns:
            CleanedDocument with cleaned text and metadata.
        """
        cfg = config or CleaningConfig(language=self._ext_config.default_language)
        original_length = len(text)
        cleaned = text
        removed: list[str] = []

        # --- Normalize whitespace (pure Python) ---
        if cfg.normalize_whitespace:
            cleaned = self._normalize_whitespace(cleaned)

        # --- Remove headers/footers (stub) ---
        if cfg.remove_headers_footers:
            cleaned, header_footer_removed = self._remove_headers_footers(cleaned)
            removed.extend(header_footer_removed)

        # --- Fix OCR errors (stub) ---
        if cfg.fix_ocr_errors:
            cleaned = self._fix_ocr_errors(cleaned)

        self._logger.info(
            "clean_completed",
            original_length=original_length,
            cleaned_length=len(cleaned),
            removed_count=len(removed),
        )

        return CleanedDocument(
            cleaned_text=cleaned,
            original_length=original_length,
            cleaned_length=len(cleaned),
            removed_sections=removed,
        )

    async def clean_batch(
        self, documents: list[str], config: CleaningConfig | None = None
    ) -> list[CleanedDocument]:
        """Clean multiple documents.

        Args:
            documents: List of raw document texts.
            config: Cleaning options (applied to all).

        Returns:
            List of CleanedDocument results.
        """
        results: list[CleanedDocument] = []
        for doc in documents:
            result = await self.clean(doc, config)
            results.append(result)

        self._logger.info(
            "clean_batch_completed",
            document_count=len(documents),
            total_cleaned=len(results),
        )
        return results

    # ------------------------------------------------------------------
    # Implementation helpers
    # ------------------------------------------------------------------

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace: collapse runs, trim lines, normalize newlines."""
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse multiple blank lines into two newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Collapse multiple spaces/tabs into single space (within lines)
        text = re.sub(r"[^\S\n]+", " ", text)
        # Trim leading/trailing whitespace per line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # Trim overall
        return text.strip()

    def _remove_headers_footers(self, text: str) -> tuple[str, list[str]]:
        """Remove repeated headers/footers (stub).

        Full implementation would detect repeated patterns across pages
        using LLM or heuristic line-frequency analysis.
        Returns text unchanged with empty removed list.
        """
        return text, []

    def _fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors (stub).

        Full implementation would use an LLM to detect and correct
        OCR artifacts (broken words, misread characters).
        Returns text unchanged.
        """
        return text
