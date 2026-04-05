"""Graph RAG service — entity extraction and knowledge graph queries."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "EntityType",
    "GraphEntity",
    "GraphRAGConfig",
    "GraphRAGService",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class EntityType(StrEnum):
    PERSON = "person"
    ORGANIZATION = "organization"
    DOCUMENT = "document"
    CONCEPT = "concept"
    DATE = "date"
    AMOUNT = "amount"


class GraphEntity(BaseModel):
    """A single extracted entity."""

    name: str
    type: str  # EntityType value
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphRAGConfig(ServiceConfig):
    """Service-level configuration."""

    min_entity_confidence: float = 0.3
    max_entities_per_text: int = 100
    date_patterns: list[str] = Field(
        default_factory=lambda: [
            r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",  # 2024-01-15
            r"\d{1,2}[-/.]\d{1,2}[-/.]\d{4}",  # 15.01.2024
            r"\d{4}\.\s?\w+\s?\d{1,2}",  # 2024. januar 15
        ]
    )
    amount_patterns: list[str] = Field(
        default_factory=lambda: [
            r"\d[\d\s.,]*\s*(?:Ft|HUF|EUR|USD|forint)",  # 1 234 Ft
            r"(?:Ft|HUF|EUR|USD)\s*\d[\d\s.,]*",  # HUF 1234
        ]
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GraphRAGService(BaseService):
    """Entity extraction and knowledge graph queries for RAG enhancement.

    Provides:
    - Regex-based NER for dates, amounts, and capitalized-word entities
    - Graph building from entity lists (stub — needs graph DB)
    - Graph-augmented question answering (stub — needs LLM + graph DB)
    """

    def __init__(self, config: GraphRAGConfig | None = None) -> None:
        self._ext_config = config or GraphRAGConfig()
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "graph_rag"

    @property
    def service_description(self) -> str:
        return "Entity extraction and knowledge graph queries for RAG"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Extract entities
    # ------------------------------------------------------------------

    async def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Extract entities from text using regex patterns.

        Extracts:
        - Dates (ISO, European formats)
        - Monetary amounts (HUF, EUR, USD)
        - Capitalized multi-word phrases (potential person/org names)

        Args:
            text: Input text to analyze.

        Returns:
            List of dicts with keys: name, type, confidence.
        """
        if not text.strip():
            return []

        entities: list[dict[str, Any]] = []
        seen: set[str] = set()
        max_count = self._ext_config.max_entities_per_text

        # --- Dates ---
        for pattern in self._ext_config.date_patterns:
            for match in re.finditer(pattern, text):
                name = match.group().strip()
                if name not in seen and len(entities) < max_count:
                    entities.append({
                        "name": name,
                        "type": EntityType.DATE.value,
                        "confidence": 0.85,
                    })
                    seen.add(name)

        # --- Amounts ---
        for pattern in self._ext_config.amount_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group().strip()
                if name not in seen and len(entities) < max_count:
                    entities.append({
                        "name": name,
                        "type": EntityType.AMOUNT.value,
                        "confidence": 0.80,
                    })
                    seen.add(name)

        # --- Capitalized phrases (potential persons / organizations) ---
        _upper = r"A-Z\u00C1\u00C9\u00CD\u00D3\u00D6\u0150\u00DA\u00DC\u0170"
        _lower = r"a-z\u00E1\u00E9\u00ED\u00F3\u00F6\u0151\u00FA\u00FC\u0171"
        cap_pattern = (
            rf"\b[{_upper}][{_lower}]+"
            rf"(?:\s+[{_upper}][{_lower}]+)+"
        )
        for match in re.finditer(cap_pattern, text):
            name = match.group().strip()
            # Skip very short or very common patterns
            if len(name) < 4 or name.lower() in {"the", "this", "that", "with"}:
                continue
            if name not in seen and len(entities) < max_count:
                # Heuristic: 3+ words more likely org, 2 words more likely person
                word_count = len(name.split())
                entity_type = (
                    EntityType.ORGANIZATION.value
                    if word_count >= 3
                    else EntityType.PERSON.value
                )
                entities.append({
                    "name": name,
                    "type": entity_type,
                    "confidence": 0.50,
                })
                seen.add(name)

        self._logger.info(
            "entities_extracted",
            total=len(entities),
            types={e["type"] for e in entities},
        )

        return entities

    # ------------------------------------------------------------------
    # Build graph
    # ------------------------------------------------------------------

    async def build_graph(
        self, entities: list[dict[str, Any]], collection_id: str
    ) -> dict[str, Any]:
        """Build a knowledge graph from extracted entities.

        Stub implementation — returns graph structure without persisting.
        Full implementation would use Microsoft GraphRAG or a graph DB.

        Args:
            entities: List of entity dicts (name, type, confidence).
            collection_id: Collection to associate the graph with.

        Returns:
            Dict with nodes, edges, and collection_id.
        """
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        # Create nodes from entities
        for i, entity in enumerate(entities):
            nodes.append({
                "id": f"node_{i}",
                "name": entity.get("name", ""),
                "type": entity.get("type", "concept"),
                "confidence": entity.get("confidence", 0.0),
            })

        # Create co-occurrence edges between entities of different types
        for i, node_a in enumerate(nodes):
            for j, node_b in enumerate(nodes):
                if i >= j:
                    continue
                if node_a["type"] != node_b["type"]:
                    edges.append({
                        "source": node_a["id"],
                        "target": node_b["id"],
                        "relation": "co_occurs_with",
                        "weight": 1.0,
                    })

        self._logger.info(
            "graph_built",
            collection_id=collection_id,
            node_count=len(nodes),
            edge_count=len(edges),
        )

        return {
            "nodes": nodes,
            "edges": edges,
            "collection_id": collection_id,
        }

    # ------------------------------------------------------------------
    # Query graph
    # ------------------------------------------------------------------

    async def query_graph(
        self, question: str, collection_id: str
    ) -> dict[str, Any]:
        """Query the knowledge graph to augment RAG answers.

        Stub implementation — extracts entities from question and returns them.
        Full implementation would traverse graph + retrieve context + LLM answer.

        Args:
            question: Natural language question.
            collection_id: Collection to query.

        Returns:
            Dict with answer, entities, and sources.
        """
        # Extract entities from the question itself
        question_entities = await self.extract_entities(question)

        self._logger.info(
            "graph_query",
            collection_id=collection_id,
            question_entities=len(question_entities),
        )

        return {
            "answer": (
                f"Graph query for collection '{collection_id}': "
                f"found {len(question_entities)} entities in question. "
                "Full graph traversal requires GraphRAG integration."
            ),
            "entities": question_entities,
            "sources": [],
            "collection_id": collection_id,
        }
