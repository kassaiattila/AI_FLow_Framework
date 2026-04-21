"""ParserResult v1 contract — unit tests.

@test_registry
suite: unit_contracts
tags: [unit, contracts, phase_1_5_sprint_i]
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from aiflow.contracts.parser_result import ParserResult


def test_minimal_parser_result() -> None:
    file_id = uuid4()
    r = ParserResult(file_id=file_id, parser_name="docling_standard")
    assert r.file_id == file_id
    assert r.parser_name == "docling_standard"
    assert r.text == ""
    assert r.tables == []
    assert r.page_count == 0


def test_parser_name_required_nonempty() -> None:
    with pytest.raises(ValidationError):
        ParserResult(file_id=uuid4(), parser_name="")


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        ParserResult(
            file_id=uuid4(),
            parser_name="docling_standard",
            unknown="x",  # type: ignore[call-arg]
        )


def test_page_count_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        ParserResult(file_id=uuid4(), parser_name="docling_standard", page_count=-1)


def test_roundtrip_preserves_tables() -> None:
    r = ParserResult(
        file_id=uuid4(),
        parser_name="docling_standard",
        text="hello",
        tables=[{"index": 0, "markdown": "| a | b |"}],
        page_count=2,
        parse_duration_ms=12.5,
    )
    restored = ParserResult.model_validate(r.model_dump(mode="json"))
    assert restored.tables == [{"index": 0, "markdown": "| a | b |"}]
    assert restored.page_count == 2
    assert restored.parse_duration_ms == 12.5
