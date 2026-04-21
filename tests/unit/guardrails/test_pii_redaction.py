"""PIIRedactionGate — v0 unit tests.

@test_registry
suite: unit_guardrails
tags: [unit, guardrails, phase_1_5_sprint_i, s96]
"""

from __future__ import annotations

from aiflow.guardrails.pii_redaction import PIIRedactionGate, PIIRedactionReport


def test_plain_text_no_pii_returns_zero_matches() -> None:
    gate = PIIRedactionGate()
    report = gate.redact("Hello, this is a perfectly ordinary sentence.")

    assert isinstance(report, PIIRedactionReport)
    assert report.total_count == 0
    assert report.matches == []
    assert report.redacted_text == "Hello, this is a perfectly ordinary sentence."


def test_empty_string_handled() -> None:
    gate = PIIRedactionGate()
    report = gate.redact("")

    assert report.redacted_text == ""
    assert report.total_count == 0
    assert report.matches == []


def test_email_single_match_redacted() -> None:
    gate = PIIRedactionGate()
    text = "Keress: jegesparos@gmail.com — köszi."
    report = gate.redact(text)

    assert report.total_count == 1
    assert report.matches[0].type == "email"
    assert report.matches[0].masked_value == "[REDACTED_EMAIL]"
    assert "jegesparos@gmail.com" not in report.redacted_text
    assert "[REDACTED_EMAIL]" in report.redacted_text


def test_hu_phone_and_e164_both_redacted() -> None:
    gate = PIIRedactionGate()
    text = "Hívj: +36 30 123 4567 vagy +14155551234."
    report = gate.redact(text)

    types = {m.type for m in report.matches}
    assert "phone_hu" in types
    assert "phone_e164" in types
    assert report.total_count >= 2
    assert "30 123 4567" not in report.redacted_text
    assert "14155551234" not in report.redacted_text


def test_iban_and_taj_redacted() -> None:
    gate = PIIRedactionGate()
    text = "IBAN: HU42117730161111101800000000, TAJ: 123-456-789."
    report = gate.redact(text)

    types = [m.type for m in report.matches]
    assert "iban" in types
    assert "taj" in types
    assert "HU42117730161111101800000000" not in report.redacted_text
    assert "123-456-789" not in report.redacted_text


def test_overlapping_phone_patterns_prefer_longer_match() -> None:
    """HU phone and E.164 both fit ``+36301234567`` — accept one, not both."""
    gate = PIIRedactionGate()
    text = "Tel: +36301234567 vége."
    report = gate.redact(text)

    assert report.total_count == 1
    assert report.matches[0].span[1] - report.matches[0].span[0] >= 12
    assert "+36301234567" not in report.redacted_text


def test_spans_are_non_overlapping_and_monotonic() -> None:
    gate = PIIRedactionGate()
    text = (
        "Email: a@b.co, phone: +36 1 222 3333, IBAN: DE89370400440532013000, TAJ: 987 654 321 vége."
    )
    report = gate.redact(text)

    last_end = -1
    for match in report.matches:
        start, end = match.span
        assert start >= last_end, "spans must be non-overlapping"
        last_end = end
    assert report.total_count == len(report.matches)
