"""ExtractionResult v1 contract — unit tests.

@test_registry
suite: unit_contracts
tags: [unit, contracts, phase_1_5_sprint_i]
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from aiflow.contracts.extraction_result import ExtractionResult


class TestExtractionResultDefaults:
    def test_minimal_construction(self) -> None:
        pkg = uuid4()
        file = uuid4()
        result = ExtractionResult(
            package_id=pkg,
            file_id=file,
            tenant_id="tenant_a",
            parser_used="docling_standard",
        )
        assert result.package_id == pkg
        assert result.file_id == file
        assert result.tenant_id == "tenant_a"
        assert result.parser_used == "docling_standard"
        assert result.extracted_text == ""
        assert result.structured_fields == {}
        assert result.confidence == 0.0
        assert result.cost_attribution is None
        assert result.extracted_at is not None


class TestExtractionResultValidation:
    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExtractionResult(
                package_id=uuid4(),
                file_id=uuid4(),
                tenant_id="t",
                parser_used="docling_standard",
                confidence=1.5,
            )

    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExtractionResult(
                package_id=uuid4(),
                file_id=uuid4(),
                tenant_id="t",
                parser_used="docling_standard",
                confidence=-0.1,
            )

    def test_empty_tenant_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExtractionResult(
                package_id=uuid4(),
                file_id=uuid4(),
                tenant_id="",
                parser_used="docling_standard",
            )

    def test_empty_parser_used_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExtractionResult(
                package_id=uuid4(),
                file_id=uuid4(),
                tenant_id="t",
                parser_used="",
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ExtractionResult(
                package_id=uuid4(),
                file_id=uuid4(),
                tenant_id="t",
                parser_used="docling_standard",
                bogus_field="nope",  # type: ignore[call-arg]
            )


class TestExtractionResultRoundTrip:
    def test_serialize_deserialize_preserves_values(self) -> None:
        pkg = uuid4()
        file = uuid4()
        original = ExtractionResult(
            package_id=pkg,
            file_id=file,
            tenant_id="tenant_b",
            parser_used="docling_standard",
            extracted_text="hello world",
            structured_fields={"page_count": 3},
            confidence=0.85,
            cost_attribution={"parser_cost": 0.0},
        )
        dumped = original.model_dump(mode="json")
        restored = ExtractionResult.model_validate(dumped)
        assert restored.package_id == pkg
        assert restored.file_id == file
        assert restored.extracted_text == "hello world"
        assert restored.structured_fields == {"page_count": 3}
        assert restored.confidence == 0.85
        assert restored.cost_attribution == {"parser_cost": 0.0}

    def test_skipped_policy_sentinel_roundtrips(self) -> None:
        result = ExtractionResult(
            package_id=uuid4(),
            file_id=uuid4(),
            tenant_id="t",
            parser_used="skipped_policy",
            structured_fields={"skip_reason": "cloud_ai_disallowed_for_mime"},
        )
        dumped = result.model_dump(mode="json")
        assert dumped["parser_used"] == "skipped_policy"
        restored = ExtractionResult.model_validate(dumped)
        assert restored.parser_used == "skipped_policy"
        assert restored.confidence == 0.0
