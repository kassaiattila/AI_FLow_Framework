"""Document recognition contracts — Sprint V SV-1.

Eight Pydantic class for the generic Document Recognizer skill (UC1-General):

* :class:`DocRecognitionRequest` — input envelope (file ref + tenant + optional hint)
* :class:`DocTypeMatch` — classifier output (primary doc-type + alternatives)
* :class:`DocFieldValue` — single extracted field with confidence + source hint
* :class:`DocExtractionResult` — full extraction output for a recognized doc
* :class:`DocIntentDecision` — routing decision after extraction
* :class:`RuleSpec` — single rule in a doc-type's classifier (5 kinds)
* :class:`IntentRoutingRule` — single rule in the intent_routing config
* :class:`DocTypeDescriptor` — full operator-authored descriptor (YAML-driven)

Source: ``01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md`` + ``01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md`` §2 SV-1.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = [
    "DocExtractionResult",
    "DocFieldValue",
    "DocIntentDecision",
    "DocRecognitionRequest",
    "DocTypeDescriptor",
    "DocTypeMatch",
    "ExtractionConfig",
    "FieldSpec",
    "IntentRoutingConfig",
    "IntentRoutingRule",
    "PiiLevel",
    "RuleKind",
    "RuleSpec",
    "TypeClassifierConfig",
]

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

PiiLevel = Literal["low", "medium", "high"]
RuleKind = Literal["regex", "keyword_list", "structure_hint", "filename_match", "parser_metadata"]
DocIntent = Literal["process", "route_to_human", "rag_ingest", "respond", "reject"]


# ---------------------------------------------------------------------------
# Request / Response envelopes
# ---------------------------------------------------------------------------


class DocRecognitionRequest(BaseModel):
    """Input envelope for ``recognize_and_extract(...)``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    file_path: Path | None = None
    file_bytes: bytes | None = None
    tenant_id: str = Field(..., min_length=1, max_length=255)
    doc_type_hint: str | None = None
    filename: str | None = None

    @model_validator(mode="after")
    def _at_least_one_source(self) -> DocRecognitionRequest:
        if self.file_path is None and self.file_bytes is None:
            raise ValueError(
                "DocRecognitionRequest: at least one of file_path / file_bytes is required"
            )
        return self


class DocTypeMatch(BaseModel):
    """Classifier output — primary doc-type + top-3 alternatives."""

    doc_type: str = Field(..., min_length=1, max_length=128)
    confidence: float = Field(..., ge=0.0, le=1.0)
    alternatives: list[tuple[str, float]] = Field(default_factory=list)

    @field_validator("alternatives")
    @classmethod
    def _alternatives_shape(cls, v: list[tuple[str, float]]) -> list[tuple[str, float]]:
        if len(v) > 3:
            raise ValueError("DocTypeMatch.alternatives: at most 3 entries (top-3)")
        for name, conf in v:
            if not isinstance(name, str) or not name:
                raise ValueError("DocTypeMatch.alternatives: entry name must be a non-empty string")
            if not (0.0 <= float(conf) <= 1.0):
                raise ValueError("DocTypeMatch.alternatives: confidence must be in [0, 1]")
        return v


class DocFieldValue(BaseModel):
    """Single extracted field — value + confidence + source span hint."""

    value: str | int | float | bool | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_text_hint: str | None = Field(default=None, max_length=200)


class DocExtractionResult(BaseModel):
    """Full extraction output for a recognized document."""

    doc_type: str = Field(..., min_length=1, max_length=128)
    extracted_fields: dict[str, DocFieldValue] = Field(default_factory=dict)
    validation_warnings: list[str] = Field(default_factory=list)
    cost_usd: float = Field(default=0.0, ge=0.0)
    extraction_time_ms: float = Field(default=0.0, ge=0.0)


class DocIntentDecision(BaseModel):
    """Routing decision after extraction — what to do with this document."""

    intent: DocIntent
    reason: str = Field(default="", max_length=500)
    next_action: str | None = Field(default=None, max_length=255)


# ---------------------------------------------------------------------------
# Descriptor model + nested configs
# ---------------------------------------------------------------------------


class RuleSpec(BaseModel):
    """One rule in the type classifier — 5 kinds, each weight-scored."""

    kind: RuleKind
    weight: float = Field(..., gt=0.0, le=1.0)
    pattern: str | None = None
    keywords: list[str] | None = None
    threshold: int | None = Field(default=None, ge=1)
    hint: str | None = None  # for structure_hint / parser_metadata

    @model_validator(mode="after")
    def _kind_appropriate_fields(self) -> RuleSpec:
        if self.kind == "regex" and not self.pattern:
            raise ValueError("RuleSpec(kind='regex'): pattern is required")
        if self.kind == "keyword_list":
            if not self.keywords:
                raise ValueError("RuleSpec(kind='keyword_list'): keywords is required")
            if self.threshold is None:
                raise ValueError("RuleSpec(kind='keyword_list'): threshold is required")
        if self.kind == "structure_hint" and not self.hint:
            raise ValueError("RuleSpec(kind='structure_hint'): hint is required")
        if self.kind == "filename_match" and not self.pattern:
            raise ValueError("RuleSpec(kind='filename_match'): pattern is required")
        if self.kind == "parser_metadata" and not self.hint:
            raise ValueError("RuleSpec(kind='parser_metadata'): hint is required")
        return self


class TypeClassifierConfig(BaseModel):
    """Doc-type classifier rules + LLM fallback gate."""

    rules: list[RuleSpec] = Field(default_factory=list)
    llm_fallback: bool = True
    llm_threshold_below: float = Field(default=0.7, ge=0.0, le=1.0)


class FieldSpec(BaseModel):
    """One field in a doc-type's extraction config."""

    name: str = Field(..., min_length=1, max_length=128)
    type: Literal["string", "date", "money", "int", "enum", "bool"] | str = "string"
    required: bool = False
    validators: list[str] = Field(default_factory=list)
    enum: list[str] | None = None
    currency_default: str | None = None
    schema_ref: str | None = None  # for list[<type>] entries — points to a sibling sub-doctype


class ExtractionConfig(BaseModel):
    """Doc-type extraction config — workflow descriptor + field schema."""

    workflow: str = Field(..., min_length=1, max_length=128)
    fields: list[FieldSpec] = Field(default_factory=list)


class IntentRoutingRule(BaseModel):
    """One conditional rule in intent_routing.conditions."""

    if_expr: str = Field(..., min_length=1, max_length=500, alias="if")
    intent: DocIntent
    reason: str = Field(default="", max_length=500)

    model_config = ConfigDict(populate_by_name=True)


class IntentRoutingConfig(BaseModel):
    """Intent routing — default + conditional rules."""

    default: DocIntent = "process"
    pii_redaction: bool = False
    conditions: list[IntentRoutingRule] = Field(default_factory=list)


class DocTypeDescriptor(BaseModel):
    """Full operator-authored descriptor (YAML-driven).

    Loaded from ``data/doctypes/<name>.yaml`` (bootstrap) or
    ``data/doctypes/_tenant/<tenant_id>/<name>.yaml`` (per-tenant override).
    """

    name: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    language: str = Field(default="hu", min_length=2, max_length=10)
    category: str = Field(default="other", min_length=1, max_length=64)
    version: int = Field(default=1, ge=1)
    pii_level: PiiLevel = "low"
    parser_preferences: list[str] = Field(default_factory=list)
    type_classifier: TypeClassifierConfig
    extraction: ExtractionConfig
    intent_routing: IntentRoutingConfig = Field(default_factory=IntentRoutingConfig)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("parser_preferences")
    @classmethod
    def _parser_prefs_known(cls, v: list[str]) -> list[str]:
        # Permissive — operators can register custom parsers later. Just validate
        # non-empty entries.
        for entry in v:
            if not entry or not isinstance(entry, str):
                raise ValueError(
                    "DocTypeDescriptor.parser_preferences: entries must be non-empty str"
                )
        return v

    def total_rule_weight(self) -> float:
        """Sum of all rule weights — should normalize to ~1.0 in well-formed descriptors."""
        return sum(r.weight for r in self.type_classifier.rules)

    def field_names(self) -> list[str]:
        """Return the list of declared extraction field names (in order)."""
        return [f.name for f in self.extraction.fields]

    def model_dump_yaml_safe(self) -> dict[str, Any]:
        """Dump the descriptor as a YAML-safe dict (drops created_at)."""
        d = self.model_dump(mode="json", exclude={"created_at"}, by_alias=True)
        return d
