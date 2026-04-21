"""PIIRedactionGate — v0 regex-based PII redaction gate.

S96 scope (UC1 session 3). A lightweight, deterministic gate that the
DocumentExtractorService can call before any LLM hop. The gate only
masks — it does not block. Provenance records go to ``pii_redaction_reports``
(Alembic 039). A full, ML-backed gate with confidence scores arrives in
Phase 2b (v1.5.1) — this v0 is intentionally narrow.

Registration into ``extract_from_package`` is S97 scope; this module only
delivers the gate, its report shape, and the DB stub.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N8,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I / §10.3.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "PII_TYPES",
    "PIIMatch",
    "PIIRedactionReport",
    "PIIRedactionGate",
]

PIIType = Literal["email", "phone_hu", "phone_e164", "iban", "taj"]
PII_TYPES: tuple[PIIType, ...] = ("email", "phone_hu", "phone_e164", "iban", "taj")

_PII_PATTERNS: tuple[tuple[PIIType, re.Pattern[str]], ...] = (
    (
        "email",
        re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ),
    (
        "phone_hu",
        re.compile(r"\+?36[\s-]?\(?\d{1,2}\)?[\s-]?\d{3}[\s-]?\d{4}"),
    ),
    (
        "phone_e164",
        re.compile(r"\+\d{8,15}"),
    ),
    (
        "iban",
        re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    ),
    (
        "taj",
        re.compile(r"\b\d{3}[\s-]?\d{3}[\s-]?\d{3}\b"),
    ),
)


class PIIMatch(BaseModel):
    """Single PII hit with its span in the original text."""

    model_config = ConfigDict(extra="forbid")

    type: PIIType = Field(..., description="PII category identifier.")
    span: tuple[int, int] = Field(
        ...,
        description="[start, end) character span into the original string.",
    )
    masked_value: str = Field(
        ...,
        description="Mask token that replaced the PII value in redacted_text.",
    )


class PIIRedactionReport(BaseModel):
    """Redaction outcome — stub shape; Phase 2b extends with provenance."""

    model_config = ConfigDict(extra="forbid")

    redacted_text: str = Field(..., description="Text with PII matches replaced by mask tokens.")
    matches: list[PIIMatch] = Field(default_factory=list, description="Per-hit metadata.")
    total_count: int = Field(default=0, ge=0, description="Number of matches redacted.")


class PIIRedactionGate:
    """Regex-based PII redaction — v0, deterministic, CPU-only."""

    name = "pii_redaction_v0"

    def redact(self, text: str) -> PIIRedactionReport:
        """Return a report with mask-token redacted text and per-hit metadata."""
        if not text:
            return PIIRedactionReport(redacted_text=text, matches=[], total_count=0)

        raw_matches: list[tuple[int, int, PIIType]] = []
        for pii_type, pattern in _PII_PATTERNS:
            for m in pattern.finditer(text):
                raw_matches.append((m.start(), m.end(), pii_type))

        raw_matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
        accepted: list[tuple[int, int, PIIType]] = []
        cursor = -1
        for start, end, pii_type in raw_matches:
            if start < cursor:
                continue
            accepted.append((start, end, pii_type))
            cursor = end

        redacted_chars: list[str] = []
        last = 0
        matches: list[PIIMatch] = []
        for start, end, pii_type in accepted:
            if start > last:
                redacted_chars.append(text[last:start])
            mask = f"[REDACTED_{pii_type.upper()}]"
            redacted_chars.append(mask)
            matches.append(PIIMatch(type=pii_type, span=(start, end), masked_value=mask))
            last = end
        if last < len(text):
            redacted_chars.append(text[last:])

        return PIIRedactionReport(
            redacted_text="".join(redacted_chars),
            matches=matches,
            total_count=len(matches),
        )
