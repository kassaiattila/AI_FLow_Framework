"""ChunkResult — v1 stub returned by ChunkerProvider.chunk().

Emitted by the chunker layer that sits between ParserProvider and
EmbedderProvider in the UC2 RAG pipeline. Each chunk carries enough
provenance (source_file_id, package_id, tenant_id, chunk_index) to
trace a pgvector row back to its originating intake package.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md §11,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint J.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ChunkResult",
]


class ChunkResult(BaseModel):
    """Single chunk produced by the chunker layer."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: UUID = Field(default_factory=uuid4)
    source_file_id: UUID = Field(..., description="IntakeFile.file_id this chunk was derived from.")
    package_id: UUID = Field(
        ..., description="IntakePackage.package_id containing the source file."
    )
    tenant_id: str = Field(..., min_length=1, description="Tenant boundary.")
    text: str = Field(..., min_length=1, description="Chunk text payload.")
    token_count: int = Field(..., gt=0, description="Approximate token count for the chunk.")
    chunk_index: int = Field(
        ..., ge=0, description="Zero-based index of this chunk within its source file."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Chunker-specific metadata (overlap_tokens, chunker_name, etc.).",
    )
