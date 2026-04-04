"""
@test_registry:
    suite: core-unit extended
    component: documents.registry
    covers: [src/aiflow/documents/registry.py]
    phase: 3
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [documents, registry, lifecycle]
"""

import uuid
from pathlib import Path

import pytest

from aiflow.documents.registry import (
    Document,
    DocumentRegistry,
    DocumentStatus,
    IngestionStatus,
)


@pytest.fixture
def tmp_file(tmp_path: Path) -> Path:
    """Create a small temporary file for registration tests."""
    f = tmp_path / "sample.pdf"
    f.write_bytes(b"fake-pdf-content-for-hashing")
    return f


@pytest.fixture
def registry() -> DocumentRegistry:
    reg = DocumentRegistry()
    yield reg
    reg.clear()


class TestDocumentModel:
    def test_defaults(self):
        doc = Document(
            title="ASZF",
            filename="aszf.pdf",
            file_type="pdf",
            file_hash_sha256="abc123",
        )
        assert doc.status == DocumentStatus.DRAFT
        assert doc.ingestion_status == IngestionStatus.PENDING
        assert doc.version_number == 1
        assert doc.supersedes_id is None
        assert isinstance(doc.id, uuid.UUID)

    def test_custom_fields(self):
        doc = Document(
            title="Policy",
            filename="policy.docx",
            file_type="docx",
            file_hash_sha256="def456",
            department="legal",
            language="en",
            status=DocumentStatus.ACTIVE,
            version_number=3,
        )
        assert doc.department == "legal"
        assert doc.language == "en"
        assert doc.version_number == 3
        assert doc.status == DocumentStatus.ACTIVE


class TestDocumentRegistry:
    def test_register(self, registry: DocumentRegistry, tmp_file: Path):
        doc = registry.register(tmp_file, {"title": "Test Doc"})
        assert doc.filename == "sample.pdf"
        assert doc.file_type == "pdf"
        assert len(doc.file_hash_sha256) == 64  # SHA-256 hex
        assert doc.title == "Test Doc"

    def test_get(self, registry: DocumentRegistry, tmp_file: Path):
        doc = registry.register(tmp_file, {"title": "Test"})
        fetched = registry.get(doc.id)
        assert fetched.id == doc.id

    def test_get_missing_raises(self, registry: DocumentRegistry):
        with pytest.raises(KeyError, match="not found"):
            registry.get(uuid.uuid4())

    def test_update_status(self, registry: DocumentRegistry, tmp_file: Path):
        doc = registry.register(tmp_file, {"title": "Doc"})
        updated = registry.update_status(doc.id, DocumentStatus.ACTIVE)
        assert updated.status == DocumentStatus.ACTIVE
        assert registry.get(doc.id).status == DocumentStatus.ACTIVE

    def test_list_by_collection_all(self, registry: DocumentRegistry, tmp_file: Path):
        registry.register(tmp_file, {"title": "A", "collection_name": "col1"})
        registry.register(tmp_file, {"title": "B", "collection_name": "col2"})
        assert len(registry.list_by_collection()) == 2

    def test_list_by_collection_filtered(self, registry: DocumentRegistry, tmp_file: Path):
        registry.register(tmp_file, {"title": "A", "collection_name": "col1"})
        registry.register(tmp_file, {"title": "B", "collection_name": "col2"})
        col1 = registry.list_by_collection("col1")
        assert len(col1) == 1
        assert col1[0].collection_name == "col1"

    def test_find_by_hash(self, registry: DocumentRegistry, tmp_file: Path):
        doc = registry.register(tmp_file, {"title": "Findable"})
        found = registry.find_by_hash(doc.file_hash_sha256)
        assert found is not None
        assert found.id == doc.id

    def test_find_by_hash_missing(self, registry: DocumentRegistry):
        assert registry.find_by_hash("nonexistent_hash") is None
