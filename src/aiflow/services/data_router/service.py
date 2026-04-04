"""Data router service — condition-based filtering + rule-based file routing."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import structlog
from jinja2 import BaseLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from pydantic import BaseModel, Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "DataRouterConfig",
    "DataRouterService",
    "FilterResult",
    "RoutedFile",
    "RoutingRule",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RoutingRule(BaseModel):
    """A single routing rule: condition + action + config."""

    condition: str = Field(..., description="Jinja2 boolean expression")
    action: str = Field(..., description="Action: move_to_dir, notify, create_review, tag")
    config: dict[str, Any] = Field(default_factory=dict)


class RoutedFile(BaseModel):
    """Result of routing a single file."""

    file_path: str
    target_path: str | None = None
    rule_matched: str | None = None
    action: str = ""
    success: bool = True
    error: str | None = None


class FilterResult(BaseModel):
    """Result of filter operation."""

    filtered_items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    matched: int = 0


class DataRouterConfig(ServiceConfig):
    """Data router configuration."""

    base_output_dir: str = "./data/routed"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DataRouterService(BaseService):
    """Condition-based filtering and rule-based file routing."""

    def __init__(self, config: DataRouterConfig | None = None) -> None:
        self._ext_config = config or DataRouterConfig()
        self._jinja_env = SandboxedEnvironment(
            loader=BaseLoader(),
            undefined=StrictUndefined,
        )
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "data_router"

    @property
    def service_description(self) -> str:
        return "Condition-based filtering and rule-based file routing"

    async def _start(self) -> None:
        Path(self._ext_config.base_output_dir).mkdir(parents=True, exist_ok=True)

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # filter — evaluate condition on list of items
    # ------------------------------------------------------------------

    async def filter(
        self,
        items: list[dict[str, Any]],
        condition: str,
    ) -> FilterResult:
        """Filter items by Jinja2 condition expression.

        Args:
            items: List of dicts to evaluate.
            condition: Jinja2 expression that evaluates to truthy/falsy,
                       e.g. ``"{{ total_amount > 100000 }}"`` or
                       ``"total_amount > 100000"``.
        """
        matched: list[dict[str, Any]] = []
        for item in items:
            if self._evaluate_condition(condition, item):
                matched.append(item)

        return FilterResult(
            filtered_items=matched,
            total=len(items),
            matched=len(matched),
        )

    # ------------------------------------------------------------------
    # route_files — apply routing rules to files
    # ------------------------------------------------------------------

    async def route_files(
        self,
        files: list[dict[str, Any]],
        rules: list[RoutingRule],
    ) -> list[RoutedFile]:
        """Route files according to rules.

        Each entry in *files* must have a ``file_path`` key (str or Path).
        Additional keys are available as context for condition evaluation.
        Rules are evaluated in order; first match wins.
        """
        results: list[RoutedFile] = []
        for file_entry in files:
            file_path = str(file_entry.get("file_path", ""))
            result = await self._route_single(file_path, file_entry, rules)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # move_to_dir — move file with template-expanded target
    # ------------------------------------------------------------------

    async def move_to_dir(
        self,
        file_path: str | Path,
        target_dir_template: str,
        data: dict[str, Any],
    ) -> RoutedFile:
        """Move a file to a directory resolved from a Jinja2 template.

        Args:
            file_path: Source file.
            target_dir_template: Jinja2 template for target directory,
                e.g. ``"archive/{{ vendor_id }}/{{ year }}"``.
            data: Template variables.

        Returns:
            RoutedFile with success status and new path.
        """
        src = Path(file_path)
        if not src.exists():
            return RoutedFile(
                file_path=str(src),
                success=False,
                error=f"Source file not found: {src}",
                action="move_to_dir",
            )

        try:
            resolved_dir = self._render_template(target_dir_template, data)
            base = Path(self._ext_config.base_output_dir)
            target_dir = base / resolved_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / src.name
            shutil.move(str(src), str(target))

            self._logger.info(
                "file_moved",
                source=str(src),
                target=str(target),
            )
            return RoutedFile(
                file_path=str(src),
                target_path=str(target),
                action="move_to_dir",
                success=True,
            )
        except Exception as exc:
            self._logger.error("move_failed", file=str(src), error=str(exc))
            return RoutedFile(
                file_path=str(src),
                action="move_to_dir",
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _route_single(
        self,
        file_path: str,
        context: dict[str, Any],
        rules: list[RoutingRule],
    ) -> RoutedFile:
        """Apply rules to a single file; first matching rule wins."""
        for rule in rules:
            if self._evaluate_condition(rule.condition, context):
                return await self._execute_action(file_path, rule, context)

        # No rule matched
        return RoutedFile(
            file_path=file_path,
            action="none",
            rule_matched=None,
            success=True,
        )

    async def _execute_action(
        self,
        file_path: str,
        rule: RoutingRule,
        context: dict[str, Any],
    ) -> RoutedFile:
        """Execute the action defined by a routing rule."""
        try:
            if rule.action == "move_to_dir":
                target_tmpl = rule.config.get("target_dir_template", "default")
                result = await self.move_to_dir(file_path, target_tmpl, context)
                result.rule_matched = rule.condition
                return result

            if rule.action == "tag":
                return RoutedFile(
                    file_path=file_path,
                    action="tag",
                    rule_matched=rule.condition,
                    target_path=None,
                    success=True,
                    error=None,
                )

            if rule.action in ("notify", "create_review"):
                # These actions are handled by downstream pipeline steps.
                # DataRouter just marks the match; the pipeline wires
                # the notification/review adapter as a subsequent step.
                return RoutedFile(
                    file_path=file_path,
                    action=rule.action,
                    rule_matched=rule.condition,
                    success=True,
                )

            return RoutedFile(
                file_path=file_path,
                action=rule.action,
                rule_matched=rule.condition,
                success=False,
                error=f"Unknown action: {rule.action}",
            )
        except Exception as exc:
            return RoutedFile(
                file_path=file_path,
                action=rule.action,
                rule_matched=rule.condition,
                success=False,
                error=str(exc),
            )

    def _evaluate_condition(self, condition: str, data: dict[str, Any]) -> bool:
        """Evaluate a Jinja2 condition expression against data context."""
        try:
            # Strip {{ }} wrapper if present
            expr = condition.strip()
            if expr.startswith("{{") and expr.endswith("}}"):
                expr = expr[2:-2].strip()

            tmpl = self._jinja_env.from_string("{{ " + expr + " }}")
            result = tmpl.render(**data)
            # Jinja2 renders booleans as "True"/"False" strings
            return result.strip().lower() in ("true", "1", "yes")
        except Exception as exc:
            self._logger.warning(
                "condition_eval_failed",
                condition=condition,
                error=str(exc),
            )
            return False

    def _render_template(self, template: str, data: dict[str, Any]) -> str:
        """Render a Jinja2 template string."""
        try:
            tmpl = self._jinja_env.from_string(template)
            return tmpl.render(**data)
        except Exception:
            return template
