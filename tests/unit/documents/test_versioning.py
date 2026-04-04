"""
@test_registry:
    suite: core-unit extended
    component: documents.versioning
    covers: [src/aiflow/documents/versioning.py]
    phase: 3
    priority: high
    estimated_duration_ms: 150
    requires_services: []
    tags: [documents, versioning, supersede]
"""

from pathlib import Path

import pytest

from aiflow.documents.registry import DocumentRegistry, DocumentStatus
from aiflow.documents.versioning import get_version_chain, supersede


@pytest.fixture
def tmp_file(tmp_path: Path) -> Path:
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"content-v1")
    return f


@pytest.fixture
def tmp_file_v2(tmp_path: Path) -> Path:
    f = tmp_path / "doc_v2.pdf"
    f.write_bytes(b"content-v2")
    return f


@pytest.fixture
def registry() -> DocumentRegistry:
    reg = DocumentRegistry()
    yield reg
    reg.clear()


class TestSupersede:
    def test_supersede_marks_old_as_superseded(
        self, registry: DocumentRegistry, tmp_file: Path, tmp_file_v2: Path
    ):
        old = registry.register(tmp_file, {"title": "V1", "status": "active"})
        registry.update_status(old.id, DocumentStatus.ACTIVE)
        new = registry.register(tmp_file_v2, {"title": "V2"})

        old_ver, new_ver = supersede(registry, old.id, new.id)

        assert registry.get(old.id).status == DocumentStatus.SUPERSEDED
        assert old_ver.version_number == 1
        assert new_ver.version_number == 2

    def test_supersede_links_new_to_old(
        self, registry: DocumentRegistry, tmp_file: Path, tmp_file_v2: Path
    ):
        old = registry.register(tmp_file, {"title": "V1"})
        new = registry.register(tmp_file_v2, {"title": "V2"})

        _, new_ver = supersede(registry, old.id, new.id)

        assert new_ver.supersedes_id == old.id
        assert registry.get(new.id).supersedes_id == old.id

    def test_supersede_increments_version(
        self, registry: DocumentRegistry, tmp_file: Path, tmp_file_v2: Path
    ):
        old = registry.register(tmp_file, {"title": "V1", "version_number": 5})
        new = registry.register(tmp_file_v2, {"title": "V2"})

        _, new_ver = supersede(registry, old.id, new.id)

        assert new_ver.version_number == 6


class TestVersionChain:
    def test_single_document_chain(self, registry: DocumentRegistry, tmp_file: Path):
        doc = registry.register(tmp_file, {"title": "Only"})
        chain = get_version_chain(registry, doc.id)

        assert len(chain) == 1
        assert chain[0].document_id == doc.id

    def test_multi_version_chain(
        self, registry: DocumentRegistry, tmp_file: Path, tmp_file_v2: Path, tmp_path: Path
    ):
        v1 = registry.register(tmp_file, {"title": "V1"})
        v2 = registry.register(tmp_file_v2, {"title": "V2"})
        supersede(registry, v1.id, v2.id)

        v3_file = tmp_path / "doc_v3.pdf"
        v3_file.write_bytes(b"content-v3")
        v3 = registry.register(v3_file, {"title": "V3"})
        supersede(registry, v2.id, v3.id)

        chain = get_version_chain(registry, v3.id)

        assert len(chain) == 3
        assert chain[0].document_id == v1.id
        assert chain[1].document_id == v2.id
        assert chain[2].document_id == v3.id
        assert chain[0].version_number == 1
        assert chain[2].version_number == 3
