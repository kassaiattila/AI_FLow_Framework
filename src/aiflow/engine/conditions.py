"""Condition evaluation for workflow branching.

Supports simple expression evaluation on step outputs.
Example: "output.category == 'process'" or "output.score >= 8"
"""
import operator
import re
from typing import Any

import structlog
from pydantic import BaseModel

__all__ = ["Condition", "evaluate_condition"]

logger = structlog.get_logger(__name__)

# Supported operators
OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "in": lambda a, b: a in b,
}

# Pattern: "output.field op value" or "output.field op 'string'"
CONDITION_PATTERN = re.compile(
    r"^(output\.[\w.]+)\s*(==|!=|>=|<=|>|<|in)\s*(.+)$"
)


class Condition(BaseModel):
    """A condition that evaluates against step output."""
    expression: str
    target_steps: list[str] = []

    def evaluate(self, output: dict[str, Any]) -> bool:
        """Evaluate this condition against step output data."""
        return evaluate_condition(self.expression, output)


def _resolve_path(data: dict[str, Any], path: str) -> Any:
    """Resolve a dotted path like 'output.category' from data."""
    # Remove 'output.' prefix
    if path.startswith("output."):
        path = path[7:]

    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _parse_value(value_str: str) -> Any:
    """Parse a value string into Python type."""
    value_str = value_str.strip()
    # String (single or double quotes)
    if (value_str.startswith("'") and value_str.endswith("'")) or \
       (value_str.startswith('"') and value_str.endswith('"')):
        return value_str[1:-1]
    # Boolean
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    # None
    if value_str.lower() == "none" or value_str.lower() == "null":
        return None
    # Number
    try:
        if "." in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        return value_str


def evaluate_condition(expression: str, output: dict[str, Any]) -> bool:
    """Evaluate a condition expression against output data.

    Args:
        expression: e.g., "output.category == 'process'" or "output.score >= 8"
        output: Step output data dict

    Returns:
        True if condition is met
    """
    match = CONDITION_PATTERN.match(expression.strip())
    if not match:
        logger.warning("invalid_condition", expression=expression)
        return False

    path, op_str, value_str = match.groups()
    actual = _resolve_path(output, path)
    expected = _parse_value(value_str)
    op_func = OPS.get(op_str)

    if op_func is None:
        logger.warning("unknown_operator", operator=op_str)
        return False

    try:
        result = op_func(actual, expected)
        logger.debug("condition_evaluated", expression=expression, result=result,
                     actual=actual, expected=expected)
        return bool(result)
    except (TypeError, ValueError) as e:
        logger.warning("condition_evaluation_error", expression=expression, error=str(e))
        return False
