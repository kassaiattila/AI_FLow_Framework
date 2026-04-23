"""Unit tests for aiflow.tools.azure_doc_intelligence — coverage uplift (issue #7)."""

from __future__ import annotations

import pytest

from aiflow.tools.azure_doc_intelligence import AzureDocIntelligence


def test_init_strips_trailing_slash() -> None:
    c = AzureDocIntelligence("https://host.example.com/", "key")
    assert c.endpoint == "https://host.example.com"
    assert c.api_key == "key"


def test_parse_result_empty() -> None:
    c = AzureDocIntelligence("https://h", "k")
    parsed = c._parse_result({})
    assert parsed == {"text": "", "markdown": "", "tables": [], "key_value_pairs": {}}


def test_parse_result_content_only() -> None:
    c = AzureDocIntelligence("https://h", "k")
    parsed = c._parse_result({"content": "hello"})
    assert parsed["text"] == "hello"
    assert parsed["markdown"] == "hello"


def test_parse_result_tables_to_markdown() -> None:
    c = AzureDocIntelligence("https://h", "k")
    payload = {
        "content": "doc",
        "tables": [
            {
                "cells": [
                    {"rowIndex": 0, "columnIndex": 0, "content": "H1"},
                    {"rowIndex": 0, "columnIndex": 1, "content": "H2"},
                    {"rowIndex": 1, "columnIndex": 0, "content": "a"},
                    {"rowIndex": 1, "columnIndex": 1, "content": "b"},
                ],
            }
        ],
    }
    parsed = c._parse_result(payload)
    assert len(parsed["tables"]) == 1
    md = parsed["tables"][0]["markdown"]
    assert "| H1 | H2 |" in md
    assert "| a | b |" in md
    assert "| --- | --- |" in md
    assert parsed["tables"][0]["rows"] == 2
    assert parsed["tables"][0]["cols"] == 2


def test_parse_result_key_value_pairs() -> None:
    c = AzureDocIntelligence("https://h", "k")
    payload = {
        "keyValuePairs": [
            {"key": {"content": "Total"}, "value": {"content": "$42"}},
            {"key": {"content": "Date"}, "value": {"content": "2024-01-01"}},
            {"key": {"content": ""}, "value": {"content": "ignored"}},  # empty key skipped
        ]
    }
    parsed = c._parse_result(payload)
    assert parsed["key_value_pairs"] == {"Total": "$42", "Date": "2024-01-01"}


@pytest.mark.asyncio
async def test_is_available_false_when_endpoint_missing() -> None:
    c = AzureDocIntelligence("", "key")
    assert await c.is_available() is False


@pytest.mark.asyncio
async def test_is_available_false_when_key_missing() -> None:
    c = AzureDocIntelligence("https://host", "")
    assert await c.is_available() is False


@pytest.mark.asyncio
async def test_is_available_false_on_network_error() -> None:
    """Unreachable endpoint falls through the bare-except and returns False."""
    c = AzureDocIntelligence(
        "http://127.0.0.1:1",  # unbindable port
        "key",
    )
    assert await c.is_available() is False
