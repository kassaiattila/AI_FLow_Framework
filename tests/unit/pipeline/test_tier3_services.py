"""
@test_registry:
    suite: service-unit
    component: services.tier3_rag
    covers: [
        src/aiflow/services/reranker/service.py,
        src/aiflow/services/advanced_chunker/service.py,
        src/aiflow/services/data_cleaner/service.py,
        src/aiflow/services/metadata_enricher/service.py,
        src/aiflow/services/vector_ops/service.py,
        src/aiflow/services/advanced_parser/service.py,
        src/aiflow/services/graph_rag/service.py,
    ]
    phase: C11-C16
    priority: critical
    estimated_duration_ms: 1500
    requires_services: []
    tags: [rag, reranker, chunker, cleaner, enricher, vector-ops, parser, graph]
"""

from __future__ import annotations

from typing import Any

import pytest

from aiflow.services.advanced_chunker.service import (
    AdvancedChunkerConfig,
    AdvancedChunkerService,
    ChunkConfig,
    ChunkResult,
    ChunkStrategy,
)
from aiflow.services.advanced_parser.service import (
    AdvancedParserConfig,
    AdvancedParserService,
    ParsedDocument,
)
from aiflow.services.data_cleaner.service import (
    CleanedDocument,
    CleaningConfig,
    DataCleanerConfig,
    DataCleanerService,
)
from aiflow.services.graph_rag.service import (
    GraphRAGConfig,
    GraphRAGService,
)
from aiflow.services.metadata_enricher.service import (
    EnrichedMetadata,
    EnrichmentConfig,
    MetadataEnricherConfig,
    MetadataEnricherService,
)

# ---------------------------------------------------------------------------
# Service imports
# ---------------------------------------------------------------------------
from aiflow.services.reranker.service import (
    RankedResult,
    RerankConfig,
    RerankerConfig,
    RerankerService,
)
from aiflow.services.vector_ops.service import (
    CollectionHealth,
    VectorOpsConfig,
    VectorOpsService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def reranker_svc() -> RerankerService:
    return RerankerService(config=RerankerConfig())


@pytest.fixture()
def chunker_svc() -> AdvancedChunkerService:
    return AdvancedChunkerService(config=AdvancedChunkerConfig())


@pytest.fixture()
def cleaner_svc() -> DataCleanerService:
    return DataCleanerService(config=DataCleanerConfig())


@pytest.fixture()
def enricher_svc() -> MetadataEnricherService:
    return MetadataEnricherService(config=MetadataEnricherConfig())


@pytest.fixture()
def vector_ops_svc() -> VectorOpsService:
    return VectorOpsService(session_factory=None, config=VectorOpsConfig())


@pytest.fixture()
def parser_svc() -> AdvancedParserService:
    return AdvancedParserService(config=AdvancedParserConfig())


@pytest.fixture()
def graph_rag_svc() -> GraphRAGService:
    return GraphRAGService(config=GraphRAGConfig())


# ===========================================================================
# TestRerankerService
# ===========================================================================


class TestRerankerService:
    def test_service_name(self, reranker_svc: RerankerService) -> None:
        assert reranker_svc.service_name == "reranker"

    @pytest.mark.asyncio
    async def test_rerank_fallback(self, reranker_svc: RerankerService) -> None:
        """Rerank with no ML libraries installed uses decaying-score fallback."""
        candidates = [
            {"content": "First result", "chunk_id": "c1"},
            {"content": "Second result", "chunk_id": "c2"},
            {"content": "Third result", "chunk_id": "c3"},
        ]
        await reranker_svc.start()
        results = await reranker_svc.rerank(
            query="test query",
            candidates=candidates,
            config=RerankConfig(model="bge-reranker-v2-m3", return_top=3),
        )
        # Fallback assigns decaying scores 1.0, 0.5, 0.333..., sorted desc
        assert len(results) == 3
        assert all(isinstance(r, RankedResult) for r in results)
        assert results[0].score >= results[1].score >= results[2].score

    @pytest.mark.asyncio
    async def test_empty_candidates(self, reranker_svc: RerankerService) -> None:
        await reranker_svc.start()
        results = await reranker_svc.rerank(query="test", candidates=[])
        assert results == []

    @pytest.mark.asyncio
    async def test_score_threshold(self, reranker_svc: RerankerService) -> None:
        """Score threshold filters out low-scoring candidates."""
        candidates = [{"content": f"Result {i}", "chunk_id": f"c{i}"} for i in range(10)]
        await reranker_svc.start()
        results = await reranker_svc.rerank(
            query="test",
            candidates=candidates,
            config=RerankConfig(
                model="bge-reranker-v2-m3",
                return_top=10,
                score_threshold=0.5,
            ),
        )
        # Fallback: score = 1/(i+1). Only i=0 (1.0) and i=1 (0.5) pass >= 0.5
        assert len(results) == 2
        assert all(r.score >= 0.5 for r in results)

    @pytest.mark.asyncio
    async def test_health_check(self, reranker_svc: RerankerService) -> None:
        result = await reranker_svc.health_check()
        assert result is True


# ===========================================================================
# TestChunkerService
# ===========================================================================


class TestChunkerService:
    def test_service_name(self, chunker_svc: AdvancedChunkerService) -> None:
        assert chunker_svc.service_name == "advanced_chunker"

    @pytest.mark.asyncio
    async def test_fixed_chunking(self, chunker_svc: AdvancedChunkerService) -> None:
        text = "A" * 1000
        await chunker_svc.start()
        result = await chunker_svc.chunk(
            text=text,
            config=ChunkConfig(strategy=ChunkStrategy.FIXED, chunk_size=200, chunk_overlap=0),
        )
        assert isinstance(result, ChunkResult)
        assert result.total_chunks == 5
        assert result.strategy_used == "fixed"
        assert all(c["char_count"] == 200 for c in result.chunks)

    @pytest.mark.asyncio
    async def test_recursive_chunking(self, chunker_svc: AdvancedChunkerService) -> None:
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        await chunker_svc.start()
        result = await chunker_svc.chunk(
            text=text,
            config=ChunkConfig(strategy=ChunkStrategy.RECURSIVE, chunk_size=5000),
        )
        assert isinstance(result, ChunkResult)
        assert result.total_chunks >= 1
        assert result.strategy_used == "recursive"

    @pytest.mark.asyncio
    async def test_empty_text(self, chunker_svc: AdvancedChunkerService) -> None:
        await chunker_svc.start()
        result = await chunker_svc.chunk(text="")
        assert result.total_chunks == 0
        assert result.chunks == []

    @pytest.mark.asyncio
    async def test_sentence_window_chunking(self, chunker_svc: AdvancedChunkerService) -> None:
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        await chunker_svc.start()
        result = await chunker_svc.chunk(
            text=text,
            config=ChunkConfig(strategy=ChunkStrategy.SENTENCE_WINDOW, window_size=2),
        )
        assert isinstance(result, ChunkResult)
        assert result.total_chunks >= 1
        assert result.strategy_used == "sentence_window"

    @pytest.mark.asyncio
    async def test_health_check(self, chunker_svc: AdvancedChunkerService) -> None:
        result = await chunker_svc.health_check()
        assert result is True


# ===========================================================================
# TestDataCleanerService
# ===========================================================================


class TestDataCleanerService:
    def test_service_name(self, cleaner_svc: DataCleanerService) -> None:
        assert cleaner_svc.service_name == "data_cleaner"

    @pytest.mark.asyncio
    async def test_normalize_whitespace(self, cleaner_svc: DataCleanerService) -> None:
        text = "Hello    world\r\n\r\n\r\nFoo   bar"
        await cleaner_svc.start()
        result = await cleaner_svc.clean(
            text=text,
            config=CleaningConfig(normalize_whitespace=True),
        )
        assert isinstance(result, CleanedDocument)
        # Multiple spaces collapsed, excessive newlines reduced
        assert "    " not in result.cleaned_text
        assert "\r\n" not in result.cleaned_text
        assert result.cleaned_length <= result.original_length

    @pytest.mark.asyncio
    async def test_clean_preserves_content(self, cleaner_svc: DataCleanerService) -> None:
        text = "Important content with special chars: 123 ABC"
        await cleaner_svc.start()
        result = await cleaner_svc.clean(text=text)
        # Content words must survive cleaning
        assert "Important" in result.cleaned_text
        assert "123" in result.cleaned_text
        assert "ABC" in result.cleaned_text

    @pytest.mark.asyncio
    async def test_clean_batch(self, cleaner_svc: DataCleanerService) -> None:
        docs = ["Doc  one.", "Doc   two.", "Doc    three."]
        await cleaner_svc.start()
        results = await cleaner_svc.clean_batch(docs)
        assert len(results) == 3
        assert all(isinstance(r, CleanedDocument) for r in results)

    @pytest.mark.asyncio
    async def test_health_check(self, cleaner_svc: DataCleanerService) -> None:
        result = await cleaner_svc.health_check()
        assert result is True


# ===========================================================================
# TestMetadataEnricherService
# ===========================================================================


class TestMetadataEnricherService:
    def test_service_name(self, enricher_svc: MetadataEnricherService) -> None:
        assert enricher_svc.service_name == "metadata_enricher"

    @pytest.mark.asyncio
    async def test_enrich_basic(self, enricher_svc: MetadataEnricherService) -> None:
        text = "# Project Report\n\nThis document describes the project goals and timeline."
        await enricher_svc.start()
        result = await enricher_svc.enrich(text=text)
        assert isinstance(result, EnrichedMetadata)
        assert result.title is not None
        assert "Project Report" in result.title
        assert len(result.summary) > 0
        assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_keyword_extraction(self, enricher_svc: MetadataEnricherService) -> None:
        text = (
            "Python programming language. Python is great. Python for data science. Python modules."
        )
        await enricher_svc.start()
        result = await enricher_svc.enrich(
            text=text,
            config=EnrichmentConfig(extract_keywords=True, language="en"),
        )
        assert isinstance(result.keywords, list)
        assert "python" in result.keywords

    @pytest.mark.asyncio
    async def test_enrich_empty_text(self, enricher_svc: MetadataEnricherService) -> None:
        await enricher_svc.start()
        result = await enricher_svc.enrich(text="   ")
        assert result.confidence == 0.0
        assert result.title is None

    @pytest.mark.asyncio
    async def test_health_check(self, enricher_svc: MetadataEnricherService) -> None:
        result = await enricher_svc.health_check()
        assert result is True


# ===========================================================================
# TestVectorOpsService
# ===========================================================================


class TestVectorOpsService:
    def test_service_name(self, vector_ops_svc: VectorOpsService) -> None:
        assert vector_ops_svc.service_name == "vector_ops"

    @pytest.mark.asyncio
    async def test_health_no_db(self, vector_ops_svc: VectorOpsService) -> None:
        """Without a session factory, health check returns True (trivially healthy)."""
        result = await vector_ops_svc.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_collection_health_no_db(self, vector_ops_svc: VectorOpsService) -> None:
        """Without DB, returns default empty health."""
        await vector_ops_svc.start()
        result = await vector_ops_svc.get_collection_health("test-collection")
        assert isinstance(result, CollectionHealth)
        assert result.total_vectors == 0
        assert result.index_type == "none"

    @pytest.mark.asyncio
    async def test_optimize_index_no_db(self, vector_ops_svc: VectorOpsService) -> None:
        """Without DB, optimize returns skipped status."""
        await vector_ops_svc.start()
        result = await vector_ops_svc.optimize_index("test-collection")
        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_bulk_delete_no_db(self, vector_ops_svc: VectorOpsService) -> None:
        """Without DB, bulk delete returns 0."""
        await vector_ops_svc.start()
        result = await vector_ops_svc.bulk_delete("test-collection", {"document_id": "d1"})
        assert result == 0


# ===========================================================================
# TestAdvancedParserService
# ===========================================================================


class TestAdvancedParserService:
    def test_service_name(self, parser_svc: AdvancedParserService) -> None:
        assert parser_svc.service_name == "advanced_parser"

    @pytest.mark.asyncio
    async def test_parse_nonexistent(self, parser_svc: AdvancedParserService) -> None:
        """Parsing a nonexistent file returns empty ParsedDocument with error metadata."""
        await parser_svc.start()
        result = await parser_svc.parse("/nonexistent/file.pdf")
        assert isinstance(result, ParsedDocument)
        assert result.parser_used == "none"
        assert "error" in result.metadata

    @pytest.mark.asyncio
    async def test_parse_unsupported_extension(
        self, parser_svc: AdvancedParserService, tmp_path: Any
    ) -> None:
        """Unsupported extension falls back to raw text or returns empty."""
        test_file = tmp_path / "test.xyz123"
        test_file.write_text("some content", encoding="utf-8")
        await parser_svc.start()
        result = await parser_svc.parse(str(test_file))
        assert isinstance(result, ParsedDocument)
        # Raw text reader rejects unknown extensions
        assert result.parser_used in ("raw", "none", "")

    @pytest.mark.asyncio
    async def test_parse_text_file(self, parser_svc: AdvancedParserService, tmp_path: Any) -> None:
        """Plain text file can be read as raw text."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world from test file.", encoding="utf-8")
        await parser_svc.start()
        result = await parser_svc.parse(str(test_file))
        assert isinstance(result, ParsedDocument)
        assert "Hello world" in result.text
        assert result.parser_used in ("raw", "docling")

    @pytest.mark.asyncio
    async def test_health_check(self, parser_svc: AdvancedParserService) -> None:
        result = await parser_svc.health_check()
        assert result is True


# ===========================================================================
# TestGraphRAGService
# ===========================================================================


class TestGraphRAGService:
    def test_service_name(self, graph_rag_svc: GraphRAGService) -> None:
        assert graph_rag_svc.service_name == "graph_rag"

    @pytest.mark.asyncio
    async def test_extract_entities_basic(self, graph_rag_svc: GraphRAGService) -> None:
        text = "The meeting was on 2024-01-15 with 5000 Ft payment."
        await graph_rag_svc.start()
        entities = await graph_rag_svc.extract_entities(text)
        assert isinstance(entities, list)
        assert len(entities) > 0
        entity_types = {e["type"] for e in entities}
        assert "date" in entity_types or "amount" in entity_types

    @pytest.mark.asyncio
    async def test_extract_entities_empty(self, graph_rag_svc: GraphRAGService) -> None:
        await graph_rag_svc.start()
        entities = await graph_rag_svc.extract_entities("   ")
        assert entities == []

    @pytest.mark.asyncio
    async def test_build_graph(self, graph_rag_svc: GraphRAGService) -> None:
        entities = [
            {"name": "2024-01-15", "type": "date", "confidence": 0.85},
            {"name": "5000 Ft", "type": "amount", "confidence": 0.80},
        ]
        await graph_rag_svc.start()
        graph = await graph_rag_svc.build_graph(entities, collection_id="test-col")
        assert "nodes" in graph
        assert "edges" in graph
        assert graph["collection_id"] == "test-col"
        assert len(graph["nodes"]) == 2
        # Two nodes of different types create one co-occurrence edge
        assert len(graph["edges"]) == 1

    @pytest.mark.asyncio
    async def test_query_graph(self, graph_rag_svc: GraphRAGService) -> None:
        await graph_rag_svc.start()
        result = await graph_rag_svc.query_graph(
            question="What happened on 2024-01-15?",
            collection_id="test-col",
        )
        assert "answer" in result
        assert result["collection_id"] == "test-col"

    @pytest.mark.asyncio
    async def test_health_check(self, graph_rag_svc: GraphRAGService) -> None:
        result = await graph_rag_svc.health_check()
        assert result is True


# ===========================================================================
# TestAdapterRegistration
# ===========================================================================


class TestAdapterRegistration:
    def test_all_tier3_adapters_registered(self) -> None:
        """Verify all 7 Tier 3 adapters are registered in the adapter registry."""
        import aiflow.pipeline.adapters.advanced_parser_adapter  # noqa: F401
        import aiflow.pipeline.adapters.chunker_adapter  # noqa: F401
        import aiflow.pipeline.adapters.data_cleaner_adapter  # noqa: F401
        import aiflow.pipeline.adapters.graph_rag_adapter  # noqa: F401
        import aiflow.pipeline.adapters.metadata_enricher_adapter  # noqa: F401

        # Force import of all Tier 3 adapter modules to trigger registration
        import aiflow.pipeline.adapters.reranker_adapter  # noqa: F401
        import aiflow.pipeline.adapters.vector_ops_adapter  # noqa: F401
        from aiflow.pipeline.adapter_base import adapter_registry

        expected = [
            ("reranker", "rerank"),
            ("advanced_chunker", "chunk"),
            ("data_cleaner", "clean"),
            ("metadata_enricher", "enrich"),
            ("vector_ops", "get_collection_health"),
            ("advanced_parser", "parse"),
            ("graph_rag", "extract_entities"),
        ]

        for service_name, method_name in expected:
            assert adapter_registry.has(service_name, method_name), (
                f"Adapter ({service_name}, {method_name}) not found in registry. "
                f"Available: {adapter_registry.list_adapters()}"
            )

    def test_adapter_input_output_schemas(self) -> None:
        """Each adapter must have Pydantic BaseModel input/output schemas."""
        from pydantic import BaseModel as PydanticBaseModel

        import aiflow.pipeline.adapters.advanced_parser_adapter  # noqa: F401
        import aiflow.pipeline.adapters.chunker_adapter  # noqa: F401
        import aiflow.pipeline.adapters.data_cleaner_adapter  # noqa: F401
        import aiflow.pipeline.adapters.graph_rag_adapter  # noqa: F401
        import aiflow.pipeline.adapters.metadata_enricher_adapter  # noqa: F401
        import aiflow.pipeline.adapters.reranker_adapter  # noqa: F401
        import aiflow.pipeline.adapters.vector_ops_adapter  # noqa: F401
        from aiflow.pipeline.adapter_base import adapter_registry

        tier3_keys = [
            ("reranker", "rerank"),
            ("advanced_chunker", "chunk"),
            ("data_cleaner", "clean"),
            ("metadata_enricher", "enrich"),
            ("vector_ops", "get_collection_health"),
            ("advanced_parser", "parse"),
            ("graph_rag", "extract_entities"),
        ]

        for service_name, method_name in tier3_keys:
            adapter = adapter_registry.get(service_name, method_name)
            assert issubclass(adapter.input_schema, PydanticBaseModel), (
                f"({service_name}, {method_name}) input_schema is not a Pydantic BaseModel"
            )
            assert issubclass(adapter.output_schema, PydanticBaseModel), (
                f"({service_name}, {method_name}) output_schema is not a Pydantic BaseModel"
            )

    def test_adapter_service_method_names(self) -> None:
        """Each adapter's service_name and method_name must match the expected values."""
        import aiflow.pipeline.adapters.advanced_parser_adapter  # noqa: F401
        import aiflow.pipeline.adapters.chunker_adapter  # noqa: F401
        import aiflow.pipeline.adapters.data_cleaner_adapter  # noqa: F401
        import aiflow.pipeline.adapters.graph_rag_adapter  # noqa: F401
        import aiflow.pipeline.adapters.metadata_enricher_adapter  # noqa: F401
        import aiflow.pipeline.adapters.reranker_adapter  # noqa: F401
        import aiflow.pipeline.adapters.vector_ops_adapter  # noqa: F401
        from aiflow.pipeline.adapter_base import adapter_registry

        tier3_keys = [
            ("reranker", "rerank"),
            ("advanced_chunker", "chunk"),
            ("data_cleaner", "clean"),
            ("metadata_enricher", "enrich"),
            ("vector_ops", "get_collection_health"),
            ("advanced_parser", "parse"),
            ("graph_rag", "extract_entities"),
        ]

        for service_name, method_name in tier3_keys:
            adapter = adapter_registry.get(service_name, method_name)
            assert adapter.service_name == service_name
            assert adapter.method_name == method_name
