"""
@test_registry:
    suite: vectorstore-unit
    component: vectorstore.base
    covers: [src/aiflow/vectorstore/base.py]
    phase: 2
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [vectorstore, base, models]
"""

import uuid
from datetime import date

from aiflow.vectorstore.base import SearchFilter, SearchResult


class TestSearchFilter:
    def test_defaults(self):
        f = SearchFilter()
        assert f.document_status == "active"
        assert f.skill_name is None

    def test_full(self):
        f = SearchFilter(
            skill_name="aszf_rag",
            collection_name="docs",
            language="hu",
            effective_date=date(2026, 1, 1),
        )
        assert f.skill_name == "aszf_rag"


class TestSearchResult:
    def test_basic(self):
        r = SearchResult(chunk_id=uuid.uuid4(), content="Hello world", score=0.95)
        assert r.score == 0.95
        assert r.vector_score is None

    def test_full(self):
        r = SearchResult(
            chunk_id=uuid.uuid4(),
            content="Test",
            score=0.9,
            vector_score=0.85,
            keyword_score=0.7,
            document_id=uuid.uuid4(),
            document_title="ASZF",
            section_title="3.1 Fejezet",
            page_start=42,
        )
        assert r.document_title == "ASZF"
        assert r.page_start == 42
