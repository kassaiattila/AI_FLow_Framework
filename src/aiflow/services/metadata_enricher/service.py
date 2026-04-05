"""Metadata enricher service — auto-extract metadata from documents."""

from __future__ import annotations

import re
from collections import Counter

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "EnrichmentConfig",
    "EnrichedMetadata",
    "MetadataEnricherConfig",
    "MetadataEnricherService",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Stopwords (minimal sets for keyword extraction)
# ---------------------------------------------------------------------------

_STOPWORDS_HU = frozenset({
    "a", "az", "egy", "es", "is", "de", "hogy", "nem", "meg", "volt",
    "van", "fel", "le", "ki", "be", "el", "ra", "re", "ban", "ben",
    "nak", "nek", "bol", "tol", "hoz", "hez", "val", "vel", "ert",
    "kent", "ul", "ig", "on", "en", "at", "et", "ot",
    "minden", "csak", "mint", "vagy", "sem", "mar",
    "itt", "ott", "akkor", "most", "ha", "mert", "ezt", "azt", "ami",
})

_STOPWORDS_EN = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "it", "its", "not", "no", "as", "if", "then",
    "than", "so", "up", "out", "about", "into", "over", "after", "before",
})


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class EnrichmentConfig(BaseModel):
    """Configuration for a single enrichment operation."""

    extract_entities: bool = True
    extract_keywords: bool = True
    language: str = "hu"


class EnrichedMetadata(BaseModel):
    """Extracted metadata from a document."""

    title: str | None = None
    language: str = ""
    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    entities: list[dict[str, str]] = Field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0


class MetadataEnricherConfig(ServiceConfig):
    """Service-level configuration."""

    default_language: str = "hu"
    max_keywords: int = 20
    min_word_length: int = 3


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class MetadataEnricherService(BaseService):
    """Auto-extract metadata from document text.

    Extracts:
    - Title: first non-empty line
    - Keywords: top words by frequency (filtered by stopwords)
    - Entities: stub (returns empty — needs NER model or LLM)
    - Summary: first 200 characters
    - Language: passed through from config
    """

    def __init__(self, config: MetadataEnricherConfig | None = None) -> None:
        self._ext_config = config or MetadataEnricherConfig()
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "metadata_enricher"

    @property
    def service_description(self) -> str:
        return "Auto-extract metadata (title, keywords, entities) from documents"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Enrich
    # ------------------------------------------------------------------

    async def enrich(
        self, text: str, config: EnrichmentConfig | None = None
    ) -> EnrichedMetadata:
        """Extract metadata from document text.

        Args:
            text: Document text to analyze.
            config: Enrichment options.

        Returns:
            EnrichedMetadata with extracted fields.
        """
        if not text.strip():
            return EnrichedMetadata(confidence=0.0)

        cfg = config or EnrichmentConfig(language=self._ext_config.default_language)

        title = self._extract_title(text)
        summary = self._extract_summary(text)
        keywords = self._extract_keywords(text, cfg.language) if cfg.extract_keywords else []
        entities = self._extract_entities(text) if cfg.extract_entities else []

        # Confidence: higher if we found more metadata
        confidence_parts = [
            0.3 if title else 0.0,
            0.3 if keywords else 0.0,
            0.2 if summary else 0.0,
            0.2 if entities else 0.0,
        ]
        confidence = sum(confidence_parts)

        self._logger.info(
            "enrich_completed",
            title=title[:50] if title else None,
            keyword_count=len(keywords),
            entity_count=len(entities),
            confidence=confidence,
        )

        return EnrichedMetadata(
            title=title,
            language=cfg.language,
            category=None,
            keywords=keywords,
            entities=entities,
            summary=summary,
            confidence=round(confidence, 2),
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_title(self, text: str) -> str | None:
        """Extract title as the first non-empty line."""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped:
                # Remove markdown heading markers
                stripped = re.sub(r"^#{1,6}\s+", "", stripped)
                return stripped[:200]
        return None

    def _extract_summary(self, text: str) -> str:
        """Extract summary as first 200 characters of content."""
        cleaned = " ".join(text.split())
        return cleaned[:200].strip()

    def _extract_keywords(self, text: str, language: str) -> list[str]:
        """Extract top keywords by word frequency, filtering stopwords."""
        stopwords = _STOPWORDS_HU if language == "hu" else _STOPWORDS_EN
        min_len = self._ext_config.min_word_length
        max_kw = self._ext_config.max_keywords

        # Tokenize: lowercase, alpha-only words
        words = re.findall(r"[a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ]+", text.lower())
        filtered = [
            w for w in words
            if len(w) >= min_len and w not in stopwords
        ]

        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(max_kw)]

    def _extract_entities(self, text: str) -> list[dict[str, str]]:
        """Extract entities — stub.

        Full implementation would use NER model or LLM for entity extraction.
        Returns empty list.
        """
        return []
