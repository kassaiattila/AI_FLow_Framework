"""RoutingDecision v1 contract — unit tests.

@test_registry
suite: unit_contracts
tags: [unit, contracts, phase_1_5_sprint_i, s95]
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from aiflow.contracts.routing_decision import RoutingDecision


def test_minimal_routing_decision() -> None:
    package_id = uuid4()
    file_id = uuid4()
    d = RoutingDecision(
        package_id=package_id,
        file_id=file_id,
        tenant_id="tenant_unit",
        chosen_parser="unstructured_fast",
        reason="small born-digital pdf",
    )
    assert d.package_id == package_id
    assert d.file_id == file_id
    assert d.tenant_id == "tenant_unit"
    assert d.chosen_parser == "unstructured_fast"
    assert d.reason == "small born-digital pdf"
    assert d.signals == {}
    assert d.fallback_chain == []
    assert d.cost_estimate == 0.0


def test_tenant_id_required_nonempty() -> None:
    with pytest.raises(ValidationError):
        RoutingDecision(
            package_id=uuid4(),
            file_id=uuid4(),
            tenant_id="",
            chosen_parser="unstructured_fast",
            reason="x",
        )


def test_chosen_parser_required_nonempty() -> None:
    with pytest.raises(ValidationError):
        RoutingDecision(
            package_id=uuid4(),
            file_id=uuid4(),
            tenant_id="t",
            chosen_parser="",
            reason="x",
        )


def test_reason_required_nonempty() -> None:
    with pytest.raises(ValidationError):
        RoutingDecision(
            package_id=uuid4(),
            file_id=uuid4(),
            tenant_id="t",
            chosen_parser="docling_standard",
            reason="",
        )


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        RoutingDecision(
            package_id=uuid4(),
            file_id=uuid4(),
            tenant_id="t",
            chosen_parser="docling_standard",
            reason="x",
            unknown="nope",  # type: ignore[call-arg]
        )


def test_cost_estimate_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        RoutingDecision(
            package_id=uuid4(),
            file_id=uuid4(),
            tenant_id="t",
            chosen_parser="docling_standard",
            reason="x",
            cost_estimate=-0.1,
        )


def test_roundtrip_preserves_signals_and_fallbacks() -> None:
    d = RoutingDecision(
        package_id=uuid4(),
        file_id=uuid4(),
        tenant_id="tenant_unit",
        chosen_parser="unstructured_fast",
        reason="small born-digital",
        signals={"size_bytes": 1024, "mime_type": "application/pdf", "cloud_ai_allowed": False},
        fallback_chain=["docling_standard"],
        cost_estimate=0.0,
    )
    restored = RoutingDecision.model_validate(d.model_dump(mode="json"))
    assert restored.signals == {
        "size_bytes": 1024,
        "mime_type": "application/pdf",
        "cloud_ai_allowed": False,
    }
    assert restored.fallback_chain == ["docling_standard"]
    assert restored.chosen_parser == "unstructured_fast"
