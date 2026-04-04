"""
@test_registry:
    suite: core-unit extended
    component: documents.freshness
    covers: [src/aiflow/documents/freshness.py]
    phase: 3
    priority: high
    estimated_duration_ms: 150
    requires_services: []
    tags: [documents, freshness, enforcement]
"""

from datetime import date
from pathlib import Path

import pytest

from aiflow.documents.freshness import FreshnessEnforcer
from aiflow.documents.registry import Document, DocumentRegistry, DocumentStatus


@pytest.fixture
def registry() -> DocumentRegistry:
    reg = DocumentRegistry()
    yield reg
    reg.clear()


@pytest.fixture
def tmp_file(tmp_path: Path) -> Path:
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"content")
    return f


def _make_doc(
    status: DocumentStatus = DocumentStatus.ACTIVE,
    effective_from: date | None = None,
    effective_until: date | None = None,
) -> Document:
    return Document(
        title="Test",
        filename="test.pdf",
        file_type="pdf",
        file_hash_sha256="a" * 64,
        status=status,
        effective_from=effective_from,
        effective_until=effective_until,
    )


class TestIsFresh:
    def test_active_no_dates_is_fresh(self):
        enforcer = FreshnessEnforcer(DocumentRegistry(), today=date(2026, 3, 15))
        doc = _make_doc(status=DocumentStatus.ACTIVE)
        assert enforcer.is_fresh(doc) is True

    def test_active_within_date_range(self):
        enforcer = FreshnessEnforcer(DocumentRegistry(), today=date(2026, 6, 15))
        doc = _make_doc(
            status=DocumentStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31),
        )
        assert enforcer.is_fresh(doc) is True

    def test_expired_document(self):
        enforcer = FreshnessEnforcer(DocumentRegistry(), today=date(2026, 6, 15))
        doc = _make_doc(
            status=DocumentStatus.ACTIVE,
            effective_until=date(2026, 1, 1),
        )
        assert enforcer.is_fresh(doc) is False

    def test_future_document(self):
        enforcer = FreshnessEnforcer(DocumentRegistry(), today=date(2026, 1, 1))
        doc = _make_doc(
            status=DocumentStatus.ACTIVE,
            effective_from=date(2026, 6, 1),
        )
        assert enforcer.is_fresh(doc) is False

    def test_superseded_not_fresh(self):
        enforcer = FreshnessEnforcer(DocumentRegistry(), today=date(2026, 3, 15))
        doc = _make_doc(status=DocumentStatus.SUPERSEDED)
        assert enforcer.is_fresh(doc) is False


class TestFreshnessReport:
    def test_check_freshness_mixed(self, registry: DocumentRegistry, tmp_file: Path):
        # Register a mix of documents
        registry.register(
            tmp_file,
            {
                "title": "Active",
                "skill_name": "rag",
                "collection_name": "docs",
                "status": DocumentStatus.ACTIVE,
                "effective_from": date(2026, 1, 1),
                "effective_until": date(2026, 12, 31),
            },
        )

        registry.register(
            tmp_file,
            {
                "title": "Expired",
                "skill_name": "rag",
                "collection_name": "docs",
                "status": DocumentStatus.ACTIVE,
                "effective_until": date(2025, 6, 1),
            },
        )

        registry.register(
            tmp_file,
            {
                "title": "Draft",
                "skill_name": "rag",
                "collection_name": "docs",
                "status": DocumentStatus.DRAFT,
            },
        )

        enforcer = FreshnessEnforcer(registry, today=date(2026, 6, 15))
        report = enforcer.check_freshness("rag", "docs")

        assert report.total_docs == 3
        assert report.active == 1
        assert report.expired == 1
        assert report.stale == 1
        assert report.is_healthy is False

    def test_healthy_collection(self, registry: DocumentRegistry, tmp_file: Path):
        registry.register(
            tmp_file,
            {
                "title": "Good",
                "skill_name": "rag",
                "collection_name": "docs",
                "status": DocumentStatus.ACTIVE,
            },
        )

        enforcer = FreshnessEnforcer(registry, today=date(2026, 6, 15))
        report = enforcer.check_freshness("rag", "docs")

        assert report.total_docs == 1
        assert report.active == 1
        assert report.is_healthy is True
