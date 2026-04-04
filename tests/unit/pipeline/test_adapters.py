"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters
    covers: [
        src/aiflow/pipeline/adapters/email_adapter.py,
        src/aiflow/pipeline/adapters/classifier_adapter.py,
        src/aiflow/pipeline/adapters/document_adapter.py,
        src/aiflow/pipeline/adapters/rag_adapter.py,
        src/aiflow/pipeline/adapters/media_adapter.py,
        src/aiflow/pipeline/adapters/diagram_adapter.py,
    ]
    phase: C1
    priority: critical
    estimated_duration_ms: 800
    requires_services: []
    tags: [pipeline, adapter, service-wrapper]
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import adapter_registry

# --- Fake service stubs (unit test: mock the service, test the adapter logic) ---


@dataclass
class FakeEmail:
    message_id: str = "msg-1"
    subject: str = "Test Subject"
    sender: str = "test@example.com"
    body_text: str = "Hello body"
    received_at: str = "2026-04-01T10:00:00"
    attachments: list = field(default_factory=list)


@dataclass
class FakeFetchResult:
    emails: list = field(default_factory=list)
    total: int = 0


@dataclass
class FakeClassificationResult:
    label: str = "invoice"
    confidence: float = 0.92
    method: str = "llm"
    all_scores: dict = field(default_factory=dict)


@dataclass
class FakeExtractionResult:
    invoice_id: str = "doc-123"
    fields: dict = field(default_factory=lambda: {"vendor": "ACME", "total": "1000"})
    confidence: float = 0.88
    validation_errors: list = field(default_factory=list)
    raw_text: str = "raw document text"


@dataclass
class FakeIngestionResult:
    documents_processed: int = 3
    chunks_created: int = 42
    errors: list = field(default_factory=list)


@dataclass
class FakeQueryResult:
    answer: str = "The answer is 42."
    sources: list = field(default_factory=lambda: [{"chunk_id": "c1", "score": 0.95}])
    response_time_ms: float = 150.0
    query_id: str = "q-1"


@dataclass
class FakeMediaJobRecord:
    job_id: str = "job-1"
    transcript: str = "Transcribed text here."
    duration_seconds: float = 120.5
    status: str = "completed"


@dataclass
class FakeDiagramRecord:
    diagram_id: str = "diag-1"
    mermaid_code: str = "graph TD; A-->B"
    svg_content: str = "<svg>...</svg>"


class FakeEmailService:
    async def fetch_emails(self, config_id, limit=50, since_date=None):
        return FakeFetchResult(
            emails=[FakeEmail(), FakeEmail(message_id="msg-2", subject="Second")],
            total=2,
        )


class FakeClassifierService:
    async def classify(self, text, subject="", schema_labels=None, strategy=None):
        return FakeClassificationResult(label="invoice", confidence=0.92)


class FakeDocumentExtractorService:
    async def extract(self, file_path, config_name=None):
        return FakeExtractionResult()


class FakeRAGService:
    async def ingest_documents(self, collection_id, file_paths, language=None):
        return FakeIngestionResult(
            documents_processed=len(file_paths),
            chunks_created=len(file_paths) * 14,
        )

    async def query(self, collection_id, question, role="expert", top_k=None, model=None):
        return FakeQueryResult(answer=f"Answer for: {question}")


class FakeMediaService:
    async def process_media(self, file_path, stt_provider=None, created_by=None):
        return FakeMediaJobRecord()


class FakeDiagramService:
    async def generate(self, user_input, created_by=None):
        return FakeDiagramRecord()


# --- Email adapter tests ---


class TestEmailFetchAdapter:
    @pytest.mark.asyncio
    async def test_fetch_emails_basic(self):
        from aiflow.pipeline.adapters.email_adapter import EmailFetchAdapter

        adapter = EmailFetchAdapter(service=FakeEmailService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"connector_id": "cfg-1", "limit": 10}, {}, ctx
        )
        assert result["total"] == 2
        assert len(result["emails"]) == 2
        assert result["emails"][0]["subject"] == "Test Subject"
        assert result["connector_id"] == "cfg-1"

    @pytest.mark.asyncio
    async def test_fetch_emails_with_since_days(self):
        from aiflow.pipeline.adapters.email_adapter import EmailFetchAdapter

        adapter = EmailFetchAdapter(service=FakeEmailService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"connector_id": "cfg-1", "since_days": 7}, {}, ctx
        )
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_fetch_emails_input_validation(self):
        from aiflow.pipeline.adapters.email_adapter import EmailFetchAdapter

        adapter = EmailFetchAdapter(service=FakeEmailService())
        ctx = ExecutionContext()
        with pytest.raises(Exception):
            await adapter.execute({}, {}, ctx)  # missing connector_id


# --- Classifier adapter tests ---


class TestClassifierAdapter:
    @pytest.mark.asyncio
    async def test_classify_basic(self):
        from aiflow.pipeline.adapters.classifier_adapter import ClassifierAdapter

        adapter = ClassifierAdapter(service=FakeClassifierService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"text": "Please process this invoice"}, {}, ctx
        )
        assert result["label"] == "invoice"
        assert result["confidence"] == pytest.approx(0.92)
        assert result["method"] == "llm"

    @pytest.mark.asyncio
    async def test_classify_with_subject(self):
        from aiflow.pipeline.adapters.classifier_adapter import ClassifierAdapter

        adapter = ClassifierAdapter(service=FakeClassifierService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"text": "body text", "subject": "Invoice #123"}, {}, ctx
        )
        assert result["label"] == "invoice"

    @pytest.mark.asyncio
    async def test_classify_input_validation(self):
        from aiflow.pipeline.adapters.classifier_adapter import ClassifierAdapter

        adapter = ClassifierAdapter(service=FakeClassifierService())
        ctx = ExecutionContext()
        with pytest.raises(Exception):
            await adapter.execute({}, {}, ctx)  # missing text


# --- Document extractor adapter tests ---


class TestDocumentExtractAdapter:
    @pytest.mark.asyncio
    async def test_extract_basic(self):
        from aiflow.pipeline.adapters.document_adapter import DocumentExtractAdapter

        adapter = DocumentExtractAdapter(service=FakeDocumentExtractorService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"file_path": "/tmp/invoice.pdf"}, {}, ctx
        )
        assert result["document_id"] == "doc-123"
        assert result["fields"]["vendor"] == "ACME"
        assert result["confidence"] == pytest.approx(0.88)

    @pytest.mark.asyncio
    async def test_extract_with_config_name(self):
        from aiflow.pipeline.adapters.document_adapter import DocumentExtractAdapter

        adapter = DocumentExtractAdapter(service=FakeDocumentExtractorService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"file_path": "/tmp/doc.pdf", "config_name": "invoice_hu"}, {}, ctx
        )
        assert result["document_id"] == "doc-123"

    @pytest.mark.asyncio
    async def test_extract_missing_file_path(self):
        from aiflow.pipeline.adapters.document_adapter import DocumentExtractAdapter

        adapter = DocumentExtractAdapter(service=FakeDocumentExtractorService())
        ctx = ExecutionContext()
        with pytest.raises(Exception):
            await adapter.execute({}, {}, ctx)


# --- RAG adapter tests ---


class TestRAGIngestAdapter:
    @pytest.mark.asyncio
    async def test_ingest_basic(self):
        from aiflow.pipeline.adapters.rag_adapter import RAGIngestAdapter

        adapter = RAGIngestAdapter(service=FakeRAGService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"collection_id": "col-1", "file_paths": ["/a.pdf", "/b.pdf"]}, {}, ctx
        )
        assert result["documents_processed"] == 2
        assert result["chunks_created"] == 28
        assert result["collection_id"] == "col-1"

    @pytest.mark.asyncio
    async def test_ingest_missing_fields(self):
        from aiflow.pipeline.adapters.rag_adapter import RAGIngestAdapter

        adapter = RAGIngestAdapter(service=FakeRAGService())
        ctx = ExecutionContext()
        with pytest.raises(Exception):
            await adapter.execute({}, {}, ctx)


class TestRAGQueryAdapter:
    @pytest.mark.asyncio
    async def test_query_basic(self):
        from aiflow.pipeline.adapters.rag_adapter import RAGQueryAdapter

        adapter = RAGQueryAdapter(service=FakeRAGService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"collection_id": "col-1", "question": "What is X?"}, {}, ctx
        )
        assert "Answer for:" in result["answer"]
        assert len(result["sources"]) > 0

    @pytest.mark.asyncio
    async def test_query_with_overrides(self):
        from aiflow.pipeline.adapters.rag_adapter import RAGQueryAdapter

        adapter = RAGQueryAdapter(service=FakeRAGService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {
                "collection_id": "col-1",
                "question": "test",
                "role": "analyst",
                "top_k": 3,
                "model": "gpt-4o-mini",
            },
            {},
            ctx,
        )
        assert result["answer"] != ""


# --- Media adapter tests ---


class TestMediaProcessAdapter:
    @pytest.mark.asyncio
    async def test_process_basic(self):
        from aiflow.pipeline.adapters.media_adapter import MediaProcessAdapter

        adapter = MediaProcessAdapter(service=FakeMediaService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"file_path": "/tmp/video.mkv"}, {}, ctx
        )
        assert result["job_id"] == "job-1"
        assert result["transcript"] == "Transcribed text here."
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_process_with_provider(self):
        from aiflow.pipeline.adapters.media_adapter import MediaProcessAdapter

        adapter = MediaProcessAdapter(service=FakeMediaService())
        ctx = ExecutionContext(user_id="testuser")
        result = await adapter.execute(
            {"file_path": "/tmp/audio.wav", "stt_provider": "whisper"}, {}, ctx
        )
        assert result["job_id"] == "job-1"


# --- Diagram adapter tests ---


class TestDiagramGenerateAdapter:
    @pytest.mark.asyncio
    async def test_generate_basic(self):
        from aiflow.pipeline.adapters.diagram_adapter import DiagramGenerateAdapter

        adapter = DiagramGenerateAdapter(service=FakeDiagramService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"description": "Invoice processing workflow"}, {}, ctx
        )
        assert result["diagram_id"] == "diag-1"
        assert "graph TD" in result["mermaid_code"]
        assert result["diagram_type"] == "mermaid"

    @pytest.mark.asyncio
    async def test_generate_with_type(self):
        from aiflow.pipeline.adapters.diagram_adapter import DiagramGenerateAdapter

        adapter = DiagramGenerateAdapter(service=FakeDiagramService())
        ctx = ExecutionContext()
        result = await adapter.execute(
            {"description": "Flow diagram", "diagram_type": "bpmn"}, {}, ctx
        )
        assert result["diagram_type"] == "bpmn"


# --- Global registry tests ---


class TestGlobalAdapterRegistry:
    def test_registry_has_all_core_adapters(self):
        """After importing all adapter modules, the global registry has them all."""
        # Force imports (normally done by discover_adapters)
        import aiflow.pipeline.adapters.classifier_adapter  # noqa: F401
        import aiflow.pipeline.adapters.diagram_adapter  # noqa: F401
        import aiflow.pipeline.adapters.document_adapter  # noqa: F401
        import aiflow.pipeline.adapters.email_adapter  # noqa: F401
        import aiflow.pipeline.adapters.media_adapter  # noqa: F401
        import aiflow.pipeline.adapters.rag_adapter  # noqa: F401

        expected = [
            ("email_connector", "fetch_emails"),
            ("classifier", "classify"),
            ("document_extractor", "extract"),
            ("rag_engine", "ingest"),
            ("rag_engine", "query"),
            ("media_processor", "process"),
            ("diagram_generator", "generate"),
        ]
        for service_name, method_name in expected:
            assert adapter_registry.has(service_name, method_name), (
                f"Missing: ({service_name}, {method_name})"
            )

    def test_registry_adapter_count(self):
        """7 adapters registered (RAG has 2: ingest + query)."""
        assert len(adapter_registry) >= 7
