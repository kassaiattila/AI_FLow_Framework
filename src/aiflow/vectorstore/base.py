"""Abstract base for vector store implementations."""
import uuid
from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from pydantic import BaseModel

__all__ = ["SearchResult", "SearchFilter", "VectorStore"]

class SearchFilter(BaseModel):
    skill_name: str | None = None
    collection_name: str | None = None
    document_status: str = "active"
    language: str | None = None
    department: str | None = None
    effective_date: date | None = None
    metadata_filters: dict[str, Any] = {}

class SearchResult(BaseModel):
    chunk_id: uuid.UUID
    content: str
    score: float
    vector_score: float | None = None
    keyword_score: float | None = None
    document_id: uuid.UUID | None = None
    document_title: str | None = None
    section_title: str | None = None
    page_start: int | None = None
    effective_from: date | None = None
    metadata: dict[str, Any] = {}

class VectorStore(ABC):
    @abstractmethod
    async def upsert_chunks(self, collection: str, skill_name: str,
                            chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> int: ...
    @abstractmethod
    async def search(self, collection: str, skill_name: str, query_embedding: list[float],
                     query_text: str | None = None, top_k: int = 10,
                     filters: SearchFilter | None = None,
                     search_mode: str = "hybrid") -> list[SearchResult]: ...
    @abstractmethod
    async def delete_by_document(self, collection: str, skill_name: str,
                                  document_id: uuid.UUID) -> int: ...
    @abstractmethod
    async def health_check(self) -> bool: ...
