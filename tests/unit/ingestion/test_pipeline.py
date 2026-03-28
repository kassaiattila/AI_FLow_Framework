"""
@test_registry:
    suite: core-unit extended
    component: ingestion.pipeline
    covers: [src/aiflow/ingestion/pipeline.py]
    phase: 3
    priority: medium
    estimated_duration_ms: 200
    requires_services: []
    tags: [ingestion, pipeline, orchestration]
"""
import uuid
from pathlib import Path

import pytest

from aiflow.documents.registry import DocumentRegistry, DocumentStatus
from aiflow.ingestion.pipeline import (
    IngestionPipeline,
    IngestionResult,
    IngestionResultStatus,
)


@pytest.fixture
def tmp_text_file(tmp_path: Path) -> Path:
    f = tmp_path / "document.txt"
    f.write_text(
        "Introduction to the policy.\n\n"
        "## Section 1\n\n"
        "Details of section one with enough content to form a chunk.\n\n"
        "## Section 2\n\n"
        "Details of section two with additional meaningful content.",
        encoding="utf-8",
    )
    return f


@pytest.fixture
def registry() -> DocumentRegistry:
    reg = DocumentRegistry()
    yield reg
    reg.clear()


class TestIngestionResult:
    def test_model_defaults(self):
        r = IngestionResult(document_id=uuid.uuid4())
        assert r.chunk_count == 0
        assert r.status == IngestionResultStatus.SUCCESS
        assert r.duration_ms == 0.0
        assert r.error is None


class TestIngestionPipeline:
    def test_run_success(self, registry: DocumentRegistry, tmp_text_file: Path):
        pipeline = IngestionPipeline(registry)
        result = pipeline.run(tmp_text_file, skill_name="test_rag", collection_name="docs")

        assert result.status == IngestionResultStatus.SUCCESS
        assert result.chunk_count >= 1
        assert result.duration_ms > 0

        # Document should be active after successful ingestion
        doc = registry.get(result.document_id)
        assert doc.status == DocumentStatus.ACTIVE
        assert doc.skill_name == "test_rag"
        assert doc.collection_name == "docs"

    def test_run_with_preextracted_text(self, registry: DocumentRegistry, tmp_text_file: Path):
        pipeline = IngestionPipeline(registry)
        result = pipeline.run(
            tmp_text_file,
            skill_name="rag",
            collection_name="col",
            text_content=(
                "This is a pre-extracted text section containing sufficient content "
                "to meet the minimum token threshold for chunking. It includes multiple "
                "sentences so the semantic chunker will produce at least one valid chunk."
            ),
        )
        assert result.status == IngestionResultStatus.SUCCESS
        assert result.chunk_count >= 1

    def test_run_missing_file_fails(self, registry: DocumentRegistry, tmp_path: Path):
        pipeline = IngestionPipeline(registry)
        result = pipeline.run(
            tmp_path / "nonexistent.txt",
            skill_name="rag",
            collection_name="col",
        )
        assert result.status == IngestionResultStatus.FAILED
        assert result.error is not None
