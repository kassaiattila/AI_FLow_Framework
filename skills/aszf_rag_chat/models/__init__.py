"""ASZF RAG Chat models - I/O types for query and ingestion workflows."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

__all__ = [
    "QueryInput", "QueryOutput", "SearchResult", "Citation",
    "IngestInput", "IngestOutput", "ChunkResult",
    "ConversationMessage", "RoleType",
]


class RoleType:
    BASELINE = "baseline"
    MENTOR = "mentor"
    EXPERT = "expert"


class ConversationMessage(BaseModel):
    role: str  # user | assistant
    content: str


class QueryInput(BaseModel):
    question: str
    collection: str = "default"
    role: str = "baseline"  # baseline | mentor | expert
    language: str = "hu"
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    top_k: int = 5
    similarity_threshold: float = 0.3


class SearchResult(BaseModel):
    chunk_id: str = ""
    content: str = ""
    similarity_score: float = 0.0
    document_name: str = ""
    document_category: str = ""
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    document_name: str
    section: str = ""
    page: int | None = None
    chunk_index: int = 0
    relevance_score: float = 0.0
    excerpt: str = ""


class QueryOutput(BaseModel):
    answer: str = ""
    citations: list[Citation] = Field(default_factory=list)
    search_results: list[SearchResult] = Field(default_factory=list)
    hallucination_score: float = 1.0  # 1.0 = fully grounded, 0.0 = hallucinated
    processing_time_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0


class IngestInput(BaseModel):
    source_path: str  # directory or file path
    collection: str = "default"
    customer: str = ""
    language: str = "hu"
    category: str = ""
    chunk_size: int = 500  # tokens
    chunk_overlap: int = 100


class ChunkResult(BaseModel):
    document_name: str
    chunk_count: int = 0
    embedding_cost_usd: float = 0.0
    status: str = "pending"  # pending | completed | failed
    error: str = ""


class IngestOutput(BaseModel):
    total_documents: int = 0
    total_chunks: int = 0
    results: list[ChunkResult] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    processing_time_ms: float = 0.0
