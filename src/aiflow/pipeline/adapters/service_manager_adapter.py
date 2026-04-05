"""Pipeline adapter for ServiceManagerService.get_service_detail."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class ServiceDetailInput(BaseModel):
    """Input schema for service_manager.get_service_detail."""

    name: str = Field(..., description="Service name to query")


class ServiceDetailOutput(BaseModel):
    """Output schema for service_manager.get_service_detail."""

    name: str = ""
    status: str = "unknown"
    description: str = ""
    has_adapter: bool = False
    adapter_methods: list[str] = Field(default_factory=list)
    pipelines_using: list[str] = Field(default_factory=list)


class ServiceManagerDetailAdapter(BaseAdapter):
    """Adapter wrapping ServiceManagerService.get_service_detail."""

    service_name = "service_manager"
    method_name = "get_service_detail"
    input_schema = ServiceDetailInput
    output_schema = ServiceDetailOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.services.service_manager.service import (
            ServiceManagerConfig,
            ServiceManagerService,
        )

        svc = ServiceManagerService(config=ServiceManagerConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, ServiceDetailInput):
            input_data = ServiceDetailInput.model_validate(input_data)

        name = config.get("name", input_data.name)
        svc = await self._get_service()
        detail = await svc.get_service_detail(name)

        return detail.model_dump()


adapter_registry.register(ServiceManagerDetailAdapter())
