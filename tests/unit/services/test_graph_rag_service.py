"""
@test_registry:
    suite: service-unit
    component: services.graph_rag
    covers: [src/aiflow/services/graph_rag/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, graph-rag, entity-extraction, knowledge-graph]
"""

from __future__ import annotations

import pytest

from aiflow.services.graph_rag.service import GraphRAGConfig, GraphRAGService


@pytest.fixture()
def svc() -> GraphRAGService:
    return GraphRAGService(config=GraphRAGConfig())


class TestGraphRAGService:
    @pytest.mark.asyncio
    async def test_extract_entities(self, svc: GraphRAGService) -> None:
        """extract_entities finds dates and amounts in text."""
        text = "A szamla kelt: 2024-01-15. Az osszeg: 1 500 000 Ft. Kiallito: Kovacs Peter."
        entities = await svc.extract_entities(text)
        assert len(entities) > 0
        types = {e["type"] for e in entities}
        assert "date" in types

    @pytest.mark.asyncio
    async def test_build_graph(self, svc: GraphRAGService) -> None:
        """build_graph creates graph with nodes and edges."""
        entities = [
            {"name": "2024-01-15", "type": "date", "confidence": 0.85},
            {"name": "1500000 Ft", "type": "amount", "confidence": 0.80},
            {"name": "Kovacs Peter", "type": "person", "confidence": 0.50},
        ]
        graph = await svc.build_graph(entities, "coll-001")
        assert "nodes" in graph
        assert "edges" in graph
        assert graph["collection_id"] == "coll-001"
        assert len(graph["nodes"]) == 3
        # Edges between different types
        assert len(graph["edges"]) > 0

    @pytest.mark.asyncio
    async def test_query_graph(self, svc: GraphRAGService) -> None:
        """query_graph returns result dict with answer and entities."""
        result = await svc.query_graph("Ki a kiallito?", "coll-001")
        assert "answer" in result
        assert "entities" in result
        assert "sources" in result
        assert result["collection_id"] == "coll-001"

    @pytest.mark.asyncio
    async def test_extract_entities_empty(self, svc: GraphRAGService) -> None:
        """extract_entities with empty text returns empty list."""
        entities = await svc.extract_entities("")
        assert entities == []

    @pytest.mark.asyncio
    async def test_health_check(self, svc: GraphRAGService) -> None:
        """health_check returns True."""
        assert await svc.health_check() is True
