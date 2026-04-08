"""Per-field + document-level confidence scoring (B3.5).

This module computes *deterministic*, rule-based confidence scores for
document extraction results instead of trusting LLM self-reported values.
The design follows the 5-factor pattern from
``aiflow/tools/attachment_processor.py::_compute_quality_score`` but
applied per field, with structural penalties for missing mandatory fields.

Overall confidence:
    overall = weighted_mean(field_scores) * structural_penalty

Per-field confidence (4 factors, weights sum to 1.0):
    format_match           0.30 — field-type-specific format detection
    regex_validation       0.25 — field-name-specific regex match
    cross_field_consistency 0.25 — relationships between fields
    source_quality         0.20 — parser reliability (Docling, Azure DI, ...)

Used by ``confidence_router.route_by_confidence`` to decide
auto-approve / review / reject for extracted documents.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "DEFAULT_FIELD_WEIGHTS",
    "DEFAULT_SOURCE_QUALITY",
    "DocumentConfidence",
    "FieldConfidence",
    "FieldConfidenceCalculator",
]

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

#: Weights for the 4 per-field confidence factors. Must sum to 1.0.
FIELD_FACTOR_WEIGHTS: dict[str, float] = {
    "format_match": 0.30,
    "regex_validation": 0.25,
    "cross_field_consistency": 0.25,
    "source_quality": 0.20,
}

#: Per-field aggregation weights for document-overall confidence. Financial
#: fields have higher weight because they drive routing decisions.
DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "invoice_number": 0.15,
    "invoice_date": 0.10,
    "due_date": 0.10,
    "vendor_name": 0.10,
    "vendor_tax_number": 0.10,
    "gross_total": 0.20,
    "net_total": 0.10,
    "vat_total": 0.05,
    "line_items": 0.10,
}

#: Source quality multipliers keyed by parser type string.
DEFAULT_SOURCE_QUALITY: dict[str, float] = {
    "docling_clean": 1.0,
    "docling": 1.0,
    "azure_di": 0.9,
    "ocr_scan": 0.7,
    "ocr": 0.7,
    "handwriting": 0.4,
    "fallback": 0.5,
    "unknown": 0.5,
}

#: Structural penalty per missing mandatory field. Capped so overall
#: score can never drop below ``_MIN_STRUCTURAL``.
_PENALTY_PER_MISSING_MANDATORY = 0.15
_MIN_STRUCTURAL = 0.30

# ---------------------------------------------------------------------------
# Field-specific regex patterns
# ---------------------------------------------------------------------------

_REGEX_PATTERNS: dict[str, re.Pattern[str]] = {
    # HU invoice number: letters + digits with - or / separators (loose)
    "invoice_number": re.compile(r"^[A-Z0-9]{1,8}[-/]?\d{2,6}[-/]?\d{1,6}$", re.IGNORECASE),
    # HU tax number: XXXXXXXX-X-XX
    "tax_number": re.compile(r"^\d{8}-\d-\d{2}$"),
    "vendor_tax_number": re.compile(r"^\d{8}-\d-\d{2}$"),
    "buyer_tax_number": re.compile(r"^\d{8}-\d-\d{2}$"),
    # HU bank account: 8-8-(8)
    "bank_account": re.compile(r"^\d{8}-\d{8}(-\d{8})?$"),
    # Email
    "email": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$"),
    # ISO date
    "invoice_date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "due_date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "fulfillment_date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
}

_DATE_ANY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{4}\.\d{2}\.\d{2}\.?$")
_NUMBER_PATTERN = re.compile(r"^-?\d+([.,]\d+)?$")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FieldConfidence(BaseModel):
    """Per-field confidence breakdown."""

    field_name: str
    value: Any = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    factors: dict[str, float] = Field(default_factory=dict)


class DocumentConfidence(BaseModel):
    """Document-level aggregated confidence."""

    overall: float = Field(..., ge=0.0, le=1.0)
    field_scores: list[FieldConfidence] = Field(default_factory=list)
    structural_penalty: float = Field(1.0, ge=0.0, le=1.0)
    source_quality: float = Field(0.5, ge=0.0, le=1.0)
    missing_mandatory: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------


class FieldConfidenceCalculator:
    """Compute deterministic field- and document-level confidence.

    Stateless — safe to reuse across requests. Configuration (weights,
    mandatory fields, source quality table) is passed per call, so the
    same calculator can serve multiple pipelines with different configs.
    """

    def __init__(
        self,
        *,
        field_weights: dict[str, float] | None = None,
        source_quality_map: dict[str, float] | None = None,
    ) -> None:
        self._field_weights = field_weights or DEFAULT_FIELD_WEIGHTS
        self._source_quality_map = source_quality_map or DEFAULT_SOURCE_QUALITY

    # ------------------------------------------------------------------
    # Factor computations
    # ------------------------------------------------------------------

    def _compute_format_match(self, field_name: str, value: Any, field_type: str) -> float:
        """Field-type-specific format detection.

        Empty values score 0.0 regardless of type — the absence of a value
        is a confidence signal on its own.
        """
        if value is None or value == "":
            return 0.0

        value_str = str(value).strip()
        if not value_str:
            return 0.0

        if field_type == "date":
            if _DATE_ANY_PATTERN.match(value_str):
                return 1.0
            # "2021. április 15" style → partial
            if re.search(r"\d{4}.*\d{1,2}", value_str):
                return 0.7
            return 0.3

        if field_type == "number":
            cleaned = value_str.replace(" ", "").replace(",", ".")
            try:
                float(cleaned)
                return 1.0
            except ValueError:
                if _NUMBER_PATTERN.match(cleaned):
                    return 0.7
                return 0.3

        if field_type in ("string", "text", ""):
            if len(value_str) >= 2:
                return 1.0
            return 0.3

        # Unknown type — neutral
        return 0.5

    def _compute_regex_validation(self, field_name: str, value: Any) -> float:
        """Field-name-specific regex match (1.0 / 0.0 / 0.5 neutral)."""
        if value is None or value == "":
            return 0.0

        pattern = _REGEX_PATTERNS.get(field_name)
        if pattern is None:
            # No specific regex for this field — treat as neutral pass
            return 0.7

        value_str = str(value).strip()
        if pattern.match(value_str):
            return 1.0
        return 0.2

    def _compute_cross_field_consistency(
        self,
        field_name: str,
        value: Any,
        all_fields: dict[str, Any],
    ) -> float:
        """Relationships between fields.

        Each field gets a consistency score based on how well it fits
        with its neighbours:

        - ``net_total`` / ``vat_total`` / ``gross_total``: net + vat ≈ gross
          (within 1% tolerance → 1.0, within 5% → 0.5, beyond → 0.2)
        - ``invoice_date`` / ``fulfillment_date`` / ``due_date``: must be
          chronologically ordered (date1 ≤ date2 ≤ date3)
        - Other fields: neutral 1.0 (no consistency penalty)
        """
        if value is None or value == "":
            return 0.0

        if field_name in ("net_total", "vat_total", "gross_total"):
            return _amount_consistency(all_fields)

        if field_name in ("invoice_date", "fulfillment_date", "due_date"):
            return _date_ordering(all_fields)

        return 1.0

    def _compute_source_quality(self, parser_used: str) -> float:
        """Parser type → reliability score."""
        return self._source_quality_map.get(
            parser_used.lower() if parser_used else "unknown",
            self._source_quality_map.get("unknown", 0.5),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_field(
        self,
        field_name: str,
        value: Any,
        *,
        field_type: str = "string",
        all_fields: dict[str, Any] | None = None,
        parser_used: str = "unknown",
    ) -> FieldConfidence:
        """Return a ``FieldConfidence`` for one extracted field."""
        all_fields = all_fields or {}

        factors = {
            "format_match": self._compute_format_match(field_name, value, field_type),
            "regex_validation": self._compute_regex_validation(field_name, value),
            "cross_field_consistency": self._compute_cross_field_consistency(
                field_name, value, all_fields
            ),
            "source_quality": self._compute_source_quality(parser_used),
        }

        confidence = sum(factors[k] * FIELD_FACTOR_WEIGHTS[k] for k in FIELD_FACTOR_WEIGHTS)
        confidence = max(0.0, min(1.0, confidence))

        return FieldConfidence(
            field_name=field_name,
            value=value,
            confidence=round(confidence, 4),
            factors={k: round(v, 4) for k, v in factors.items()},
        )

    def compute_document(
        self,
        fields: dict[str, Any],
        *,
        field_types: dict[str, str] | None = None,
        mandatory_fields: list[str] | None = None,
        parser_used: str = "unknown",
    ) -> DocumentConfidence:
        """Return aggregated ``DocumentConfidence`` for all fields.

        Args:
            fields: Mapping of field_name → extracted value.
            field_types: Optional mapping of field_name → type hint
                (``"string"`` / ``"date"`` / ``"number"``). Missing
                entries default to ``"string"``.
            mandatory_fields: Fields that MUST be present. Each missing
                one subtracts ``_PENALTY_PER_MISSING_MANDATORY`` from
                the structural multiplier.
            parser_used: Source parser used (for source_quality factor).
        """
        field_types = field_types or {}
        mandatory = mandatory_fields or []

        # Per-field scores
        scores: list[FieldConfidence] = []
        for name, value in fields.items():
            ftype = field_types.get(name, "string")
            scores.append(
                self.compute_field(
                    name,
                    value,
                    field_type=ftype,
                    all_fields=fields,
                    parser_used=parser_used,
                )
            )

        # Weighted mean across fields
        if scores:
            total_weight = 0.0
            weighted_sum = 0.0
            for s in scores:
                w = self._field_weights.get(s.field_name, 0.05)
                total_weight += w
                weighted_sum += s.confidence * w
            mean_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        else:
            mean_confidence = 0.0

        # Structural penalty for missing mandatory fields
        missing = [
            name for name in mandatory if name not in fields or fields[name] in (None, "", [], {})
        ]
        structural_penalty = max(
            _MIN_STRUCTURAL,
            1.0 - _PENALTY_PER_MISSING_MANDATORY * len(missing),
        )

        overall = max(0.0, min(1.0, mean_confidence * structural_penalty))

        return DocumentConfidence(
            overall=round(overall, 4),
            field_scores=scores,
            structural_penalty=round(structural_penalty, 4),
            source_quality=round(self._compute_source_quality(parser_used), 4),
            missing_mandatory=missing,
        )


# ---------------------------------------------------------------------------
# Cross-field helpers (private)
# ---------------------------------------------------------------------------


def _amount_consistency(fields: dict[str, Any]) -> float:
    """Check net + vat ≈ gross.

    Returns 1.0 if within 1%, 0.5 if within 5%, 0.2 otherwise, or 0.7
    (neutral) if any of the three amounts is missing / unparseable.
    """
    net = _parse_number(fields.get("net_total"))
    vat = _parse_number(fields.get("vat_total"))
    gross = _parse_number(fields.get("gross_total"))

    if net is None or vat is None or gross is None or gross == 0:
        return 0.7

    expected = net + vat
    diff_ratio = abs(expected - gross) / abs(gross)
    if diff_ratio <= 0.01:
        return 1.0
    if diff_ratio <= 0.05:
        return 0.5
    return 0.2


def _date_ordering(fields: dict[str, Any]) -> float:
    """Check invoice_date ≤ fulfillment_date ≤ due_date.

    Missing dates are tolerated — only the available dates are checked.
    Returns 1.0 if ordering holds, 0.5 if one pair is out of order,
    0.7 if fewer than 2 dates are available (can't verify).
    """
    d1 = _parse_iso_date(fields.get("invoice_date"))
    d2 = _parse_iso_date(fields.get("fulfillment_date"))
    d3 = _parse_iso_date(fields.get("due_date"))

    dates = [d for d in (d1, d2, d3) if d is not None]
    if len(dates) < 2:
        return 0.7

    ordered = all(dates[i] <= dates[i + 1] for i in range(len(dates) - 1))
    return 1.0 if ordered else 0.5


def _parse_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except (ValueError, TypeError):
        return None


def _parse_iso_date(value: Any) -> str | None:
    """Return the ISO date string if value is a plausible YYYY-MM-DD date."""
    if value is None or value == "":
        return None
    value_str = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value_str):
        return value_str
    return None
