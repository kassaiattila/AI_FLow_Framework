"""EmbeddingDecision — v1 stub describing which embedder was picked for a tenant.

Emitted by PolicyEngine.pick_embedder(...) and persisted to the
`embedding_decisions` table (Alembic 040). Downstream RAG steps (S101+)
will attach this decision to every chunk batch so that we can trace which
profile / tenant override produced a given pgvector row.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md §10,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint J.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "EmbeddingDecision",
    "EmbeddingProfile",
]

EmbeddingProfile = Literal["A", "B"]


class EmbeddingDecision(BaseModel):
    """Policy decision naming the embedder a tenant's RAG pipeline should use."""

    model_config = ConfigDict(extra="forbid")

    decision_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(..., min_length=1, description="Tenant boundary.")
    provider_name: str = Field(
        ...,
        min_length=1,
        description="Embedder provider identifier (e.g. 'bge_m3', 'azure_openai').",
    )
    model_name: str = Field(
        ...,
        min_length=1,
        description=(
            "Concrete model / deployment id (e.g. 'BAAI/bge-m3', 'text-embedding-3-small')."
        ),
    )
    embedding_dim: int = Field(
        ...,
        gt=0,
        description="Output vector dimensionality for this provider.",
    )
    profile: EmbeddingProfile = Field(
        ...,
        description="A = local/free (BGE-M3), B = cloud/moderate (Azure OpenAI).",
    )
    tenant_override_applied: bool = Field(
        default=False,
        description="True when the tenant policy overrode the profile default.",
    )
    decision_at: datetime = Field(default_factory=datetime.utcnow)
