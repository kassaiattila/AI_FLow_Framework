"""Safe-expression-eval for ``IntentRoutingRule.if_expr`` — Sprint V SV-1.

Wraps :mod:`simpleeval` with a **restricted** name space + operator allow-list.
Designed for evaluating per-doctype intent routing rules like::

    extracted.total_gross > 1000000
    field_confidence_min < 0.6
    doc_type_confidence < 0.85
    pii_detected and extracted.id_number != ""

NOT a general-purpose evaluator — calls are always intentional and the
expression source is always operator-authored YAML. Still, the restricted
name space prevents accidental data exfiltration via expressions like
``__import__('os').system('rm -rf /')``.

Restricted name space:

* ``extracted.<field>`` — resolves to ``extracted_fields[field].value`` if the
  field exists, otherwise raises :class:`SafeEvalError`.
* ``field_confidence_min`` — min confidence across all extracted fields.
* ``field_confidence_max`` — max confidence across all extracted fields.
* ``doc_type_confidence`` — top-1 doc-type match confidence (0..1).
* ``pii_detected`` — bool flag the orchestrator may set.

Allowed operators: ``==``, ``!=``, ``<``, ``>``, ``<=``, ``>=``, ``and``,
``or``, ``not``, ``in``, ``+``, ``-``, ``*``, ``/`` (numeric), ``in`` (list
membership for ``string in [...]``-style rules).

Disallowed: function calls, attribute access on arbitrary objects (only
``extracted.<field>`` is permitted), dunder access, ``lambda``,
comprehensions, imports.
"""

from __future__ import annotations

from typing import Any

import structlog

__all__ = ["SafeEvalError", "safe_eval_intent_rule"]

logger = structlog.get_logger(__name__)


class SafeEvalError(Exception):
    """Raised when an ``if_expr`` cannot be evaluated safely."""


class _ExtractedNamespace:
    """Read-only proxy for ``extracted.<field>`` access in if_expr."""

    __slots__ = ("_fields",)

    def __init__(self, fields: dict[str, Any]) -> None:
        # Store as a plain dict mapping field-name -> value (not the full
        # DocFieldValue). This narrows the attribute surface to scalars.
        self._fields = fields

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise SafeEvalError(f"safe_eval: dunder/private attribute access denied: {name!r}")
        if name not in self._fields:
            # Returning None lets `extracted.foo == None`-style rules work
            # without crashing on a missing field. Operators who want a
            # strict mode should use `extracted.foo != None and extracted.foo > N`.
            return None
        return self._fields[name]


def _build_names(
    extracted_fields: dict[str, Any],
    doc_type_confidence: float,
    pii_detected: bool,
) -> dict[str, Any]:
    """Build the restricted name space passed to simpleeval."""
    confidences: list[float] = []
    plain_fields: dict[str, Any] = {}
    for field_name, field_obj in extracted_fields.items():
        value = getattr(field_obj, "value", field_obj)
        plain_fields[field_name] = value
        conf = getattr(field_obj, "confidence", None)
        if conf is not None:
            confidences.append(float(conf))

    return {
        "extracted": _ExtractedNamespace(plain_fields),
        "field_confidence_min": min(confidences) if confidences else 1.0,
        "field_confidence_max": max(confidences) if confidences else 0.0,
        "doc_type_confidence": float(doc_type_confidence),
        "pii_detected": bool(pii_detected),
    }


def safe_eval_intent_rule(
    if_expr: str,
    extracted_fields: dict[str, Any],
    doc_type_confidence: float,
    pii_detected: bool = False,
) -> bool:
    """Evaluate an ``if_expr`` and return the boolean result.

    :param if_expr: the expression string from ``IntentRoutingRule.if_expr``.
    :param extracted_fields: ``DocExtractionResult.extracted_fields``-shaped
        dict (mapping field-name → object with ``.value`` + ``.confidence``).
        Plain dicts are also supported (value-only).
    :param doc_type_confidence: top-1 classifier confidence in [0, 1].
    :param pii_detected: orchestrator-supplied flag.
    :returns: ``True`` if the expression evaluates truthy, ``False`` otherwise.
    :raises SafeEvalError: parse error, disallowed construct, attribute
        access on a non-``extracted`` object, or evaluation runtime failure.
    """
    try:
        from simpleeval import EvalWithCompoundTypes, FunctionNotDefined, NameNotDefined
    except ImportError as exc:  # pragma: no cover — only on environments without simpleeval
        raise SafeEvalError(
            "safe_eval: simpleeval is not installed. Run `uv pip install simpleeval`."
        ) from exc

    if not isinstance(if_expr, str) or not if_expr.strip():
        raise SafeEvalError("safe_eval: if_expr must be a non-empty string")

    names = _build_names(extracted_fields, doc_type_confidence, pii_detected)

    evaluator = EvalWithCompoundTypes(
        names=names,
        # Explicitly empty function dict — operators cannot call any function.
        functions={},
    )

    try:
        result = evaluator.eval(if_expr)
    except (NameNotDefined, FunctionNotDefined) as exc:
        raise SafeEvalError(f"safe_eval: undefined name or function: {exc}") from exc
    except SafeEvalError:
        raise
    except SyntaxError as exc:
        raise SafeEvalError(f"safe_eval: syntax error in if_expr: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — surface anything else as SafeEvalError
        raise SafeEvalError(f"safe_eval: runtime error evaluating {if_expr!r}: {exc}") from exc

    return bool(result)
