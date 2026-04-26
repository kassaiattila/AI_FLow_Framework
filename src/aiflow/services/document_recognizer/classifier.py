"""DocType classifier — Sprint V SV-2 rule engine + LLM fallback.

3-stage pipeline (the head of the recognize_and_extract orchestrator):

1. **Parse signals** — collect from the parsed-document context the inputs
   that any rule kind can read: text, tables, page_count, mime_type,
   filename, parser_metadata. Provided by the caller as
   :class:`ClassifierInput`.

2. **Rule engine** — for each candidate :class:`DocTypeDescriptor`,
   evaluate every :class:`RuleSpec` in its ``type_classifier.rules`` list.
   Score = sum of matched-rule weights. Returns the top-k matches.

3. **LLM fallback gate** — when the top-1 score is below
   ``descriptor.type_classifier.llm_threshold_below`` (default 0.7), the
   caller may invoke a small LLM with the top-k descriptors' metadata +
   first 1500 chars of parsed text to override the classifier's choice.
   This module exposes :func:`needs_llm_fallback` so the caller decides
   whether to spend the LLM call.

The classifier itself is **synchronous and pure** — no DB, no LLM, no
network. The orchestrator (SV-2 next file) wires it together with parser
routing + extraction + intent routing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from aiflow.contracts.doc_recognition import (
    DocTypeDescriptor,
    DocTypeMatch,
    RuleSpec,
)

__all__ = [
    "ClassifierInput",
    "RuleEngine",
    "classify_doctype",
    "needs_llm_fallback",
]

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ClassifierInput:
    """Signals available to the rule engine after parser routing.

    Operators don't construct this directly — the orchestrator builds it
    from the parser's ParserResult + the original request envelope.
    """

    text: str
    """Parsed document body (full text). Rule engine matches regex / keyword_list."""

    filename: str | None = None
    """Original filename if available — used by ``filename_match`` rules."""

    table_count: int = 0
    """Number of detected tables (from docling / Azure DI)."""

    page_count: int = 1
    """Number of pages in the source document."""

    mime_type: str | None = None
    """Detected MIME type (e.g. ``application/pdf``, ``image/jpeg``)."""

    parser_used: str = "unknown"
    """Which parser produced this result (``docling`` / ``azure_di`` / ``unstructured``)."""

    language: str | None = None
    """Detected language code if the parser supplied one."""

    extras: dict[str, Any] = field(default_factory=dict)
    """Open bucket for parser-specific signals (operator-extensible)."""


# ---------------------------------------------------------------------------
# Single-rule evaluation
# ---------------------------------------------------------------------------


def _eval_regex(rule: RuleSpec, ctx: ClassifierInput) -> bool:
    """``regex`` kind: ``re.search(rule.pattern, ctx.text, re.IGNORECASE)``."""
    if not rule.pattern:
        return False
    try:
        return bool(re.search(rule.pattern, ctx.text, re.IGNORECASE))
    except re.error as exc:
        logger.warning(
            "doctype_classifier.invalid_regex",
            pattern=rule.pattern,
            error=str(exc),
        )
        return False


def _eval_keyword_list(rule: RuleSpec, ctx: ClassifierInput) -> bool:
    """``keyword_list`` kind: at least ``threshold`` keywords present (case-insensitive)."""
    if not rule.keywords or rule.threshold is None:
        return False
    text_low = ctx.text.lower()
    hits = sum(1 for kw in rule.keywords if kw.lower() in text_low)
    return hits >= rule.threshold


def _eval_structure_hint(rule: RuleSpec, ctx: ClassifierInput) -> bool:
    """``structure_hint`` kind: parses simple ``key OP value`` expressions.

    Supported variables: ``table_count``, ``page_count``.
    Supported operators: ``==``, ``!=``, ``<``, ``>``, ``<=``, ``>=``.
    """
    if not rule.hint:
        return False
    expr = rule.hint.strip()
    # Simple parser: split on operator
    for op_str in (">=", "<=", "==", "!=", ">", "<"):
        if op_str in expr:
            left, right = expr.split(op_str, 1)
            left = left.strip()
            right = right.strip()
            try:
                right_val = int(right)
            except ValueError:
                logger.warning("doctype_classifier.structure_hint_non_int_rhs", hint=rule.hint)
                return False
            value: int
            if left == "table_count":
                value = ctx.table_count
            elif left == "page_count":
                value = ctx.page_count
            else:
                logger.warning(
                    "doctype_classifier.structure_hint_unknown_var",
                    hint=rule.hint,
                    var=left,
                )
                return False
            if op_str == ">=":
                return value >= right_val
            if op_str == "<=":
                return value <= right_val
            if op_str == "==":
                return value == right_val
            if op_str == "!=":
                return value != right_val
            if op_str == ">":
                return value > right_val
            if op_str == "<":
                return value < right_val
    logger.warning("doctype_classifier.structure_hint_no_operator", hint=rule.hint)
    return False


def _eval_filename_match(rule: RuleSpec, ctx: ClassifierInput) -> bool:
    """``filename_match`` kind: ``re.search(rule.pattern, ctx.filename or "")``."""
    if not rule.pattern or not ctx.filename:
        return False
    try:
        return bool(re.search(rule.pattern, ctx.filename, re.IGNORECASE))
    except re.error:
        return False


def _eval_parser_metadata(rule: RuleSpec, ctx: ClassifierInput) -> bool:
    """``parser_metadata`` kind: ``key==value`` against ctx.mime_type / parser_used / language.

    Supported keys: ``mime_type``, ``parser_used``, ``language``.
    """
    if not rule.hint:
        return False
    expr = rule.hint.strip()
    if "==" not in expr:
        logger.warning("doctype_classifier.parser_metadata_no_eq", hint=rule.hint)
        return False
    key, raw_val = (s.strip() for s in expr.split("==", 1))
    val = raw_val.strip("\"'")
    actual: str | None
    if key == "mime_type":
        actual = ctx.mime_type
    elif key == "parser_used":
        actual = ctx.parser_used
    elif key == "language":
        actual = ctx.language
    else:
        logger.warning("doctype_classifier.parser_metadata_unknown_key", hint=rule.hint, key=key)
        return False
    return actual == val


_RULE_DISPATCH = {
    "regex": _eval_regex,
    "keyword_list": _eval_keyword_list,
    "structure_hint": _eval_structure_hint,
    "filename_match": _eval_filename_match,
    "parser_metadata": _eval_parser_metadata,
}


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------


class RuleEngine:
    """Stateless rule evaluator. Operators rarely instantiate directly —
    use :func:`classify_doctype` instead."""

    def score_descriptor(self, descriptor: DocTypeDescriptor, ctx: ClassifierInput) -> float:
        """Return the aggregate weight of all matched rules (0..sum-of-weights).

        Note: the score is **not** normalized to [0, 1] inside this method —
        well-formed descriptors should sum their rule weights to ~1.0.
        :func:`classify_doctype` does the final normalize / clamp.
        """
        total = 0.0
        for rule in descriptor.type_classifier.rules:
            evaluator = _RULE_DISPATCH.get(rule.kind)
            if evaluator is None:
                logger.warning(
                    "doctype_classifier.unknown_rule_kind",
                    descriptor=descriptor.name,
                    kind=rule.kind,
                )
                continue
            try:
                matched = evaluator(rule, ctx)
            except Exception as exc:  # noqa: BLE001 — rules must never crash classification
                logger.warning(
                    "doctype_classifier.rule_eval_error",
                    descriptor=descriptor.name,
                    kind=rule.kind,
                    error=str(exc)[:200],
                )
                matched = False
            if matched:
                total += float(rule.weight)
        return total


# ---------------------------------------------------------------------------
# Top-level helpers
# ---------------------------------------------------------------------------


def classify_doctype(
    descriptors: list[DocTypeDescriptor],
    ctx: ClassifierInput,
    *,
    top_k: int = 3,
) -> DocTypeMatch | None:
    """Return the best-matching :class:`DocTypeMatch` or ``None`` if no rules fire.

    Score normalization: each descriptor's score is divided by its
    ``total_rule_weight`` so cross-descriptor comparison is fair. Matches
    with normalized score == 0.0 are dropped from the alternatives.

    :param descriptors: candidate doc-types to consider.
    :param ctx: parsed-document signals.
    :param top_k: number of alternatives to include in the result (top-1
        is the primary; up to ``top_k - 1`` go into ``alternatives``).
    """
    if not descriptors:
        return None

    engine = RuleEngine()
    scored: list[tuple[DocTypeDescriptor, float]] = []
    for descriptor in descriptors:
        raw = engine.score_descriptor(descriptor, ctx)
        norm_factor = descriptor.total_rule_weight() or 1.0
        normalized = max(0.0, min(1.0, raw / norm_factor))
        scored.append((descriptor, normalized))

    # Sort descending by score; stable sort keeps deterministic order for ties.
    scored.sort(key=lambda item: item[1], reverse=True)

    primary, primary_score = scored[0]
    if primary_score <= 0.0:
        # No rules fired for any descriptor.
        logger.debug(
            "doctype_classifier.no_match",
            candidates=len(descriptors),
            text_len=len(ctx.text),
        )
        return None

    alternatives: list[tuple[str, float]] = []
    for descriptor, score in scored[1:top_k]:
        if score <= 0.0:
            break
        alternatives.append((descriptor.name, score))

    return DocTypeMatch(
        doc_type=primary.name,
        confidence=primary_score,
        alternatives=alternatives,
    )


def needs_llm_fallback(
    match: DocTypeMatch | None,
    descriptor: DocTypeDescriptor | None,
) -> bool:
    """Return True when the top-1 score is below the descriptor's gate.

    Caller logic:

    * ``match is None`` → no rules fired → fallback to LLM with all
      candidates (the orchestrator decides whether to attempt this).
    * ``descriptor is None`` (matched name unknown to registry) → fallback.
    * ``confidence < descriptor.type_classifier.llm_threshold_below`` AND
      ``descriptor.type_classifier.llm_fallback`` is True → fallback.
    """
    if match is None:
        return True
    if descriptor is None:
        return True
    if not descriptor.type_classifier.llm_fallback:
        return False
    return match.confidence < descriptor.type_classifier.llm_threshold_below
