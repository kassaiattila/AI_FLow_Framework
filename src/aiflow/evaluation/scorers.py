"""Built-in scoring functions for the evaluation framework.

Each scorer returns a tuple of (score: float, passed: bool).
Score is typically 0.0-1.0 where 1.0 means perfect.
"""

from __future__ import annotations

import json
import re
from typing import Any

__all__ = [
    "exact_match",
    "contains",
    "json_valid",
    "json_field_equals",
    "threshold_check",
    "regex_match",
    "llm_rubric_placeholder",
]


def exact_match(actual: Any, expected: Any, **kwargs: Any) -> tuple[float, bool]:
    """Check if actual output exactly equals expected output.

    Args:
        actual: The actual output.
        expected: The expected output.

    Returns:
        (1.0, True) if equal, (0.0, False) otherwise.
    """
    match = actual == expected
    return (1.0, True) if match else (0.0, False)


def contains(actual: Any, expected: Any, **kwargs: Any) -> tuple[float, bool]:
    """Check if expected is contained in actual (string-based).

    Args:
        actual: The actual output (converted to string).
        expected: The substring to search for (converted to string).

    Returns:
        (1.0, True) if contained, (0.0, False) otherwise.
    """
    actual_str = str(actual)
    expected_str = str(expected)
    match = expected_str in actual_str
    return (1.0, True) if match else (0.0, False)


def json_valid(actual: Any, expected: Any = None, **kwargs: Any) -> tuple[float, bool]:
    """Check if actual output is valid JSON (string or already parsed).

    Args:
        actual: The output to check for JSON validity.
        expected: Ignored.

    Returns:
        (1.0, True) if valid JSON, (0.0, False) otherwise.
    """
    if isinstance(actual, (dict, list)):
        return (1.0, True)

    try:
        json.loads(str(actual))
        return (1.0, True)
    except (json.JSONDecodeError, TypeError, ValueError):
        return (0.0, False)


def json_field_equals(
    actual: Any,
    expected: Any = None,
    *,
    field: str = "",
    value: Any = None,
    **kwargs: Any,
) -> tuple[float, bool]:
    """Check if a specific JSON field in the actual output equals a value.

    Args:
        actual: The actual output (dict or JSON string).
        expected: Ignored (use field/value kwargs instead).
        field: Dot-separated field path (e.g., "result.status").
        value: Expected value for the field.

    Returns:
        (1.0, True) if the field equals value, (0.0, False) otherwise.
    """
    try:
        if isinstance(actual, str):
            data = json.loads(actual)
        elif isinstance(actual, dict):
            data = actual
        else:
            return (0.0, False)

        # Navigate dot-separated path
        parts = field.split(".") if field else []
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return (0.0, False)

        match = current == value
        return (1.0, True) if match else (0.0, False)

    except (json.JSONDecodeError, TypeError, KeyError):
        return (0.0, False)


def threshold_check(
    actual: Any,
    expected: Any = None,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    **kwargs: Any,
) -> tuple[float, bool]:
    """Check if a numeric actual value falls within a threshold range.

    Args:
        actual: Numeric value to check.
        expected: Ignored.
        min_value: Minimum acceptable value (inclusive).
        max_value: Maximum acceptable value (inclusive).

    Returns:
        (1.0, True) if within range, (score, False) otherwise.
        Score is proportional to how close the value is to the range.
    """
    try:
        num = float(actual)
    except (TypeError, ValueError):
        return (0.0, False)

    passed = True
    if min_value is not None and num < min_value:
        passed = False
    if max_value is not None and num > max_value:
        passed = False

    if passed:
        return (1.0, True)

    # Calculate a proportional score for near-misses
    if min_value is not None and max_value is not None:
        range_size = max_value - min_value
        if range_size > 0:
            distance = 0.0
            if num < min_value:
                distance = min_value - num
            elif num > max_value:
                distance = num - max_value
            score = max(0.0, 1.0 - distance / range_size)
            return (score, False)

    return (0.0, False)


def regex_match(
    actual: Any, expected: Any = None, *, pattern: str = "", **kwargs: Any
) -> tuple[float, bool]:
    """Check if actual output matches a regex pattern.

    Args:
        actual: The actual output (converted to string).
        expected: If pattern kwarg not set, expected is used as pattern.
        pattern: Regex pattern to match against.

    Returns:
        (1.0, True) if matches, (0.0, False) otherwise.
    """
    pat = pattern or str(expected or "")
    if not pat:
        return (0.0, False)

    try:
        match = bool(re.search(pat, str(actual)))
        return (1.0, True) if match else (0.0, False)
    except re.error:
        return (0.0, False)


def llm_rubric_placeholder(actual: Any, expected: Any = None, **kwargs: Any) -> tuple[float, bool]:
    """Placeholder for LLM-based rubric scoring.

    Will be implemented with actual LLM calls in a future phase.

    Returns:
        (0.5, True) as a placeholder neutral score.
    """
    return (0.5, True)
