"""Pipeline adapters for DataRouterService — filter + route_files."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


# ---------------------------------------------------------------------------
# Filter adapter
# ---------------------------------------------------------------------------


class FilterInput(BaseModel):
    """Input schema for data_router.filter."""

    items: list[dict[str, Any]] = Field(..., description="Items to filter")
    condition: str = Field(..., description="Jinja2 boolean condition")


class FilterOutput(BaseModel):
    """Output schema for data_router.filter."""

    filtered_items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    matched: int = 0


class DataRouterFilterAdapter(BaseAdapter):
    """Adapter wrapping DataRouterService.filter for pipeline use."""

    service_name = "data_router"
    method_name = "filter"
    input_schema = FilterInput
    output_schema = FilterOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.data_router.service import (
            DataRouterConfig,
            DataRouterService,
        )

        svc = DataRouterService(config=DataRouterConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, FilterInput):
            input_data = FilterInput.model_validate(input_data)

        condition = config.get("condition", input_data.condition)
        items = config.get("items", input_data.items)

        svc = await self._get_service()
        result = await svc.filter(items=items, condition=condition)

        return {
            "filtered_items": result.filtered_items,
            "total": result.total,
            "matched": result.matched,
        }


# ---------------------------------------------------------------------------
# Route files adapter
# ---------------------------------------------------------------------------


class RouteFilesInput(BaseModel):
    """Input schema for data_router.route_files."""

    files: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of dicts with 'file_path' + metadata",
    )
    rules: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of RoutingRule dicts {condition, action, config}",
    )


class RoutedFileOutput(BaseModel):
    """Single routed file in output."""

    file_path: str = ""
    target_path: str | None = None
    rule_matched: str | None = None
    action: str = ""
    success: bool = True
    error: str | None = None


class RouteFilesOutput(BaseModel):
    """Output schema for data_router.route_files."""

    routed_files: list[RoutedFileOutput] = Field(default_factory=list)
    total: int = 0
    success_count: int = 0
    failed_count: int = 0


class DataRouterRouteAdapter(BaseAdapter):
    """Adapter wrapping DataRouterService.route_files for pipeline use."""

    service_name = "data_router"
    method_name = "route_files"
    input_schema = RouteFilesInput
    output_schema = RouteFilesOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.data_router.service import (
            DataRouterConfig,
            DataRouterService,
        )

        svc = DataRouterService(config=DataRouterConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, RouteFilesInput):
            input_data = RouteFilesInput.model_validate(input_data)

        from aiflow.services.data_router.service import RoutingRule

        files = config.get("files", input_data.files)
        raw_rules = config.get("rules", input_data.rules)
        rules = [RoutingRule.model_validate(r) if isinstance(r, dict) else r for r in raw_rules]

        svc = await self._get_service()
        results = await svc.route_files(files=files, rules=rules)

        routed = [
            {
                "file_path": r.file_path,
                "target_path": r.target_path,
                "rule_matched": r.rule_matched,
                "action": r.action,
                "success": r.success,
                "error": r.error,
            }
            for r in results
        ]
        ok = sum(1 for r in results if r.success)
        fail = sum(1 for r in results if not r.success)

        return {
            "routed_files": routed,
            "total": len(results),
            "success_count": ok,
            "failed_count": fail,
        }


adapter_registry.register(DataRouterFilterAdapter())
adapter_registry.register(DataRouterRouteAdapter())
