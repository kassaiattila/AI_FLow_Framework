"""Document freshness enforcement.

Determines whether documents are still valid based on their effective dates
and status, producing per-collection freshness reports.
"""
from __future__ import annotations

from datetime import date

import structlog
from pydantic import BaseModel

from aiflow.documents.registry import Document, DocumentRegistry, DocumentStatus

__all__ = [
    "FreshnessReport",
    "FreshnessEnforcer",
]

logger = structlog.get_logger(__name__)


class FreshnessReport(BaseModel):
    """Summary of document freshness for a skill/collection pair."""

    skill_name: str
    collection_name: str
    total_docs: int = 0
    active: int = 0
    expired: int = 0
    future: int = 0
    stale: int = 0

    @property
    def is_healthy(self) -> bool:
        """Collection is healthy when all non-stale documents are active."""
        return self.expired == 0 and self.stale == 0


class FreshnessEnforcer:
    """Evaluates document freshness against a registry."""

    def __init__(self, registry: DocumentRegistry, today: date | None = None) -> None:
        self._registry = registry
        self._today = today or date.today()

    @property
    def today(self) -> date:
        return self._today

    # -- public API --------------------------------------------------------

    def is_fresh(self, document: Document) -> bool:
        """Return ``True`` if the document is considered fresh (usable for RAG).

        A document is fresh when:
        1. Its status is ``active``.
        2. ``effective_from`` is None **or** <= today.
        3. ``effective_until`` is None **or** >= today.
        """
        if document.status != DocumentStatus.ACTIVE:
            return False

        if document.effective_from is not None and document.effective_from > self._today:
            return False

        if document.effective_until is not None and document.effective_until < self._today:
            return False

        return True

    def classify(self, document: Document) -> str:
        """Classify a document as 'active', 'expired', 'future', or 'stale'.

        - **active**: status is active and within effective date window.
        - **expired**: effective_until is in the past.
        - **future**: effective_from is in the future.
        - **stale**: status is not active (superseded, revoked, archived, draft).
        """
        if document.status != DocumentStatus.ACTIVE:
            return "stale"

        if document.effective_from is not None and document.effective_from > self._today:
            return "future"

        if document.effective_until is not None and document.effective_until < self._today:
            return "expired"

        return "active"

    def check_freshness(
        self,
        skill_name: str,
        collection_name: str,
    ) -> FreshnessReport:
        """Produce a :class:`FreshnessReport` for a skill/collection pair."""
        docs = [
            d
            for d in self._registry.list_by_collection(collection_name)
            if d.skill_name == skill_name
        ]

        report = FreshnessReport(
            skill_name=skill_name,
            collection_name=collection_name,
            total_docs=len(docs),
        )

        for doc in docs:
            category = self.classify(doc)
            if category == "active":
                report.active += 1
            elif category == "expired":
                report.expired += 1
            elif category == "future":
                report.future += 1
            elif category == "stale":
                report.stale += 1

        logger.info(
            "freshness.checked",
            skill=skill_name,
            collection=collection_name,
            total=report.total_docs,
            active=report.active,
            expired=report.expired,
            future=report.future,
            stale=report.stale,
        )
        return report
