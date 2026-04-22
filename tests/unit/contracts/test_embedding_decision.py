"""Unit tests for EmbeddingDecision contract stub.

@test_registry
suite: unit
tags: [unit, contracts, embedding_decision]
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from aiflow.contracts import EmbeddingDecision


class TestEmbeddingDecisionHappyPath:
    def test_minimal_construct(self) -> None:
        decision = EmbeddingDecision(
            tenant_id="tenant-a",
            provider_name="bge_m3",
            model_name="BAAI/bge-m3",
            embedding_dim=1024,
            profile="A",
        )
        assert decision.tenant_id == "tenant-a"
        assert decision.provider_name == "bge_m3"
        assert decision.profile == "A"
        assert decision.tenant_override_applied is False
        assert decision.embedding_dim == 1024
        assert isinstance(decision.decision_id, UUID)
        assert isinstance(decision.decision_at, datetime)

    def test_profile_b_with_override(self) -> None:
        decision = EmbeddingDecision(
            tenant_id="tenant-b",
            provider_name="azure_openai",
            model_name="text-embedding-3-small",
            embedding_dim=1536,
            profile="B",
            tenant_override_applied=True,
        )
        assert decision.profile == "B"
        assert decision.tenant_override_applied is True
        assert decision.model_name == "text-embedding-3-small"

    def test_decision_id_is_unique_per_instance(self) -> None:
        d1 = EmbeddingDecision(
            tenant_id="t",
            provider_name="bge_m3",
            model_name="BAAI/bge-m3",
            embedding_dim=1024,
            profile="A",
        )
        d2 = EmbeddingDecision(
            tenant_id="t",
            provider_name="bge_m3",
            model_name="BAAI/bge-m3",
            embedding_dim=1024,
            profile="A",
        )
        assert d1.decision_id != d2.decision_id


class TestEmbeddingDecisionValidation:
    def test_missing_tenant_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingDecision(
                provider_name="bge_m3",
                model_name="BAAI/bge-m3",
                embedding_dim=1024,
                profile="A",
            )  # type: ignore[call-arg]

    def test_empty_tenant_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingDecision(
                tenant_id="",
                provider_name="bge_m3",
                model_name="BAAI/bge-m3",
                embedding_dim=1024,
                profile="A",
            )

    def test_invalid_profile_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingDecision(
                tenant_id="t",
                provider_name="bge_m3",
                model_name="BAAI/bge-m3",
                embedding_dim=1024,
                profile="C",  # type: ignore[arg-type]
            )

    def test_non_positive_embedding_dim_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingDecision(
                tenant_id="t",
                provider_name="bge_m3",
                model_name="BAAI/bge-m3",
                embedding_dim=0,
                profile="A",
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddingDecision(
                tenant_id="t",
                provider_name="bge_m3",
                model_name="BAAI/bge-m3",
                embedding_dim=1024,
                profile="A",
                mystery_field="nope",  # type: ignore[call-arg]
            )
