"""Jinja2 sandboxed template resolver for pipeline config values.

Security: SandboxedEnvironment blocks __dunder__ access, callable(),
import statements, and eval()/exec(). StrictUndefined fails fast on
missing variables.
"""

from __future__ import annotations

from typing import Any

import structlog
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

__all__ = ["TemplateResolver"]

logger = structlog.get_logger(__name__)

# Jinja2 patterns that should never appear in pipeline templates
_BLOCKED_PATTERNS = ("__", "import", "exec(", "eval(", "compile(")


class TemplateResolver:
    """Resolve Jinja2 templates in pipeline step configs.

    Context variables:
      - input: pipeline input parameters
      - <step_name>: output dict from completed steps
      - item: current element when inside a for_each iteration
    """

    def __init__(self) -> None:
        self._env = SandboxedEnvironment(
            undefined=StrictUndefined,
            autoescape=False,
        )

    def resolve_value(
        self, value: Any, context: dict[str, Any]
    ) -> Any:
        """Resolve a single value. If it's a string with {{ }}, render it."""
        if not isinstance(value, str):
            return value
        if "{{" not in value and "{%" not in value:
            return value

        self._check_blocked(value)

        template = self._env.from_string(value)
        rendered = template.render(**context)

        return self._coerce_type(rendered)

    def resolve_config(
        self, config: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve all Jinja2 templates in a step config dict."""
        resolved: dict[str, Any] = {}
        for key, value in config.items():
            if isinstance(value, dict):
                resolved[key] = self.resolve_config(value, context)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_value(item, context) for item in value
                ]
            else:
                resolved[key] = self.resolve_value(value, context)
        return resolved

    def resolve_expression(
        self, expression: str, context: dict[str, Any]
    ) -> Any:
        """Resolve a Jinja2 expression (for for_each, conditions).

        Uses compile_expression to return the native Python object
        (list, dict, etc.) instead of rendering to string.
        """
        self._check_blocked(expression)

        # Strip {{ }} wrapper if present — compile_expression needs raw expr
        expr = expression.strip()
        if expr.startswith("{{") and expr.endswith("}}"):
            expr = expr[2:-2].strip()

        compiled = self._env.compile_expression(expr)
        return compiled(**context)

    def _check_blocked(self, template_str: str) -> None:
        """Raise SecurityError if template contains blocked patterns."""
        for pattern in _BLOCKED_PATTERNS:
            if pattern in template_str:
                raise SecurityError(
                    f"Blocked pattern '{pattern}' in template: "
                    f"{template_str[:80]}"
                )

    @staticmethod
    def _coerce_type(rendered: str) -> Any:
        """Try to coerce rendered string to Python type."""
        stripped = rendered.strip()

        if stripped.lower() in ("true", "false"):
            return stripped.lower() == "true"
        if stripped.lower() == "none":
            return None

        try:
            return int(stripped)
        except ValueError:
            pass
        try:
            return float(stripped)
        except ValueError:
            pass

        return rendered


class SecurityError(Exception):
    """Raised when a Jinja2 template contains blocked patterns."""
