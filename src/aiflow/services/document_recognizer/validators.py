"""DocRecognizer field validators — Sprint W SW-1.

7 pure-Python validators referenced by doctype YAML descriptors via the
``validators`` field of :class:`aiflow.contracts.doc_recognition.FieldSpec`.

Each validator returns ``(passed: bool, warning: str | None)``. Warnings
flow into :class:`DocExtractionResult.validation_warnings` — the recognizer
never crashes on a validation failure.

Validator string syntax (parsed by :func:`apply_validators`):

* ``"non_empty"``                          — value must not be None/"" /[]/false
* ``"regex:<pattern>"``                    — full match against pattern (case-sensitive)
* ``"iso_date"``                           — value parseable as ``YYYY-MM-DD`` ISO date
* ``"before_today"``                       — ISO date that is strictly before today (UTC)
* ``"after_today"``                        — ISO date that is strictly after today (UTC)
* ``"min:<N>"``                            — numeric value ≥ N (also supports ISO date ≥ N if N is a date)
* ``"max:<N>"``                            — numeric value ≤ N (mirror)

Operators add new validators by extending :data:`_DISPATCH` + writing a
new top-level function with the same ``(value, *args) -> tuple[bool, str | None]``
shape.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

import structlog

__all__ = [
    "ValidatorResult",
    "after_today",
    "apply_validators",
    "before_today",
    "iso_date",
    "max_value",
    "min_value",
    "non_empty",
    "regex_validator",
]

logger = structlog.get_logger(__name__)

ValidatorResult = tuple[bool, str | None]


# ---------------------------------------------------------------------------
# Individual validators
# ---------------------------------------------------------------------------


def non_empty(value: Any) -> ValidatorResult:
    """Reject None, empty str, empty list/dict, False, 0 (numeric zero is fine).

    Numeric ``0`` is **considered non-empty** because ``"min:0"`` is a more
    explicit way to bound a numeric field. ``False`` is empty (boolean
    rejection); empty lists/dicts/strings are empty.
    """
    if value is None:
        return False, "non_empty: value is None"
    if isinstance(value, str) and not value.strip():
        return False, "non_empty: empty string"
    if isinstance(value, (list, dict)) and not value:
        return False, "non_empty: empty collection"
    if value is False:
        return False, "non_empty: False"
    return True, None


def regex_validator(value: Any, pattern: str) -> ValidatorResult:
    """``re.fullmatch(pattern, str(value))``. Case-sensitive."""
    if value is None:
        return False, f"regex: value is None (expected match for {pattern!r})"
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        return False, f"regex: invalid pattern {pattern!r}: {exc}"
    if not compiled.fullmatch(str(value)):
        return False, f"regex: {value!r} does not match {pattern!r}"
    return True, None


def _parse_iso_date(value: Any) -> date | None:
    """Try to parse ``value`` as an ISO ``date``. Returns ``None`` on any failure."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    s = value.strip()
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def iso_date(value: Any) -> ValidatorResult:
    """Value must parse as an ISO ``YYYY-MM-DD`` date."""
    if _parse_iso_date(value) is None:
        return False, f"iso_date: {value!r} not a valid ISO date"
    return True, None


def before_today(value: Any) -> ValidatorResult:
    """ISO date strictly before ``today (UTC)``."""
    parsed = _parse_iso_date(value)
    if parsed is None:
        return False, f"before_today: {value!r} not a valid ISO date"
    today = datetime.now(UTC).date()
    if parsed >= today:
        return False, f"before_today: {parsed.isoformat()} is not before {today.isoformat()}"
    return True, None


def after_today(value: Any) -> ValidatorResult:
    """ISO date strictly after ``today (UTC)``."""
    parsed = _parse_iso_date(value)
    if parsed is None:
        return False, f"after_today: {value!r} not a valid ISO date"
    today = datetime.now(UTC).date()
    if parsed <= today:
        return False, f"after_today: {parsed.isoformat()} is not after {today.isoformat()}"
    return True, None


def _coerce_to_float(value: Any) -> float | None:
    """Coerce numeric / numeric-string to float, or ``None``."""
    if isinstance(value, bool):
        return None  # avoid the int(True)==1 trap
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(" ", "").replace(",", "."))
        except ValueError:
            return None
    return None


def min_value(value: Any, n: float) -> ValidatorResult:
    """Numeric value must be ≥ ``n``."""
    coerced = _coerce_to_float(value)
    if coerced is None:
        return False, f"min:{n}: {value!r} is not numeric"
    if coerced < n:
        return False, f"min:{n}: {coerced} < {n}"
    return True, None


def max_value(value: Any, n: float) -> ValidatorResult:
    """Numeric value must be ≤ ``n``."""
    coerced = _coerce_to_float(value)
    if coerced is None:
        return False, f"max:{n}: {value!r} is not numeric"
    if coerced > n:
        return False, f"max:{n}: {coerced} > {n}"
    return True, None


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


_DISPATCH: dict[str, Callable[..., ValidatorResult]] = {
    "non_empty": non_empty,
    "iso_date": iso_date,
    "before_today": before_today,
    "after_today": after_today,
}


def _parse_validator_spec(spec: str) -> tuple[str, list[Any]]:
    """Split ``"regex:^foo$"`` into ``("regex", ["^foo$"])``.

    Validators with arguments use ``<name>:<arg>`` (single arg). The arg is
    passed to the validator as a positional after ``value``.
    """
    if ":" in spec:
        name, raw_arg = spec.split(":", 1)
        return name.strip(), [raw_arg]
    return spec.strip(), []


def apply_validators(value: Any, validator_specs: list[str]) -> list[str]:
    """Run every validator spec; return the list of warning strings.

    Empty list means "all validators passed (or no validators were declared)".
    Unknown validator names emit a warning but do not raise.
    """
    warnings: list[str] = []
    for spec in validator_specs:
        if not spec or not isinstance(spec, str):
            continue
        name, args = _parse_validator_spec(spec)

        if name == "regex":
            if not args:
                warnings.append("regex: missing pattern")
                continue
            ok, warning = regex_validator(value, args[0])
        elif name == "min":
            if not args:
                warnings.append("min: missing N")
                continue
            try:
                n = float(args[0])
            except ValueError:
                warnings.append(f"min: invalid numeric arg {args[0]!r}")
                continue
            ok, warning = min_value(value, n)
        elif name == "max":
            if not args:
                warnings.append("max: missing N")
                continue
            try:
                n = float(args[0])
            except ValueError:
                warnings.append(f"max: invalid numeric arg {args[0]!r}")
                continue
            ok, warning = max_value(value, n)
        elif name in _DISPATCH:
            ok, warning = _DISPATCH[name](value)
        else:
            logger.debug("validators.unknown_spec", name=name)
            warnings.append(f"unknown validator: {name!r}")
            continue

        if not ok and warning:
            warnings.append(warning)

    return warnings
