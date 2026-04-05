"""ServiceAdapter protocol and AdapterRegistry for pipeline orchestration.

Each adapter wraps a specific service method with unified execution semantics:
  - Pydantic input/output schema validation
  - Config dict → service kwargs translation
  - for_each concurrency handling via asyncio.Semaphore
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, runtime_checkable

import structlog
from pydantic import BaseModel, ValidationError

from aiflow.core.context import ExecutionContext

__all__ = ["AdapterRegistry", "ServiceAdapter"]

logger = structlog.get_logger(__name__)


@runtime_checkable
class ServiceAdapter(Protocol):
    """Unified interface for pipeline step adapters.

    Each adapter maps to one (service_name, method_name) pair and translates
    between the pipeline's dict-based data flow and the service's typed API.
    """

    service_name: str
    method_name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    async def execute(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute the adapter with validated input, return validated output dict."""
        ...


class BaseAdapter:
    """Convenience base class implementing common adapter logic.

    Subclasses must set class attributes and implement _run().
    """

    service_name: str
    method_name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    async def execute(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        """Validate input, call _run, validate output, return dict."""
        validated_input = self.input_schema.model_validate(input_data)

        result = await self._run(validated_input, config, ctx)

        if isinstance(result, BaseModel):
            validated_output = result
        else:
            validated_output = self.output_schema.model_validate(result)

        return validated_output.model_dump()

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> BaseModel | dict[str, Any]:
        """Override in subclass: call the actual service method."""
        raise NotImplementedError

    async def execute_for_each(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
        concurrency: int = 5,
    ) -> list[dict[str, Any]]:
        """Execute adapter on each item with bounded concurrency."""
        sem = asyncio.Semaphore(concurrency)
        results: list[dict[str, Any]] = []

        async def _run_one(idx: int, item: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                try:
                    return await self.execute(item, config, ctx)
                except (ValidationError, Exception) as exc:
                    logger.error(
                        "for_each_item_failed",
                        adapter=f"{self.service_name}.{self.method_name}",
                        item_index=idx,
                        error=str(exc),
                    )
                    raise

        tasks = [_run_one(i, item) for i, item in enumerate(items)]
        results = await asyncio.gather(*tasks)
        return list(results)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.service_name}.{self.method_name}>"


class AdapterRegistry:
    """Registry of pipeline adapters keyed by (service_name, method_name).

    Supports manual registration and auto-discovery of adapter modules.
    """

    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], ServiceAdapter] = {}

    def register(self, adapter: ServiceAdapter) -> None:
        """Register an adapter. Raises ValueError if key already taken."""
        key = (adapter.service_name, adapter.method_name)
        if key in self._adapters:
            raise ValueError(
                f"Adapter already registered for {key}. "
                f"Existing: {self._adapters[key]!r}"
            )
        self._adapters[key] = adapter
        logger.info(
            "adapter_registered",
            service=adapter.service_name,
            method=adapter.method_name,
        )

    def get(self, service_name: str, method_name: str) -> ServiceAdapter:
        """Get adapter by (service, method). Raises KeyError if not found."""
        key = (service_name, method_name)
        if key not in self._adapters:
            raise KeyError(
                f"No adapter for ({service_name}, {method_name}). "
                f"Available: {self.list_adapters()}"
            )
        return self._adapters[key]

    def get_or_none(
        self, service_name: str, method_name: str
    ) -> ServiceAdapter | None:
        """Get adapter or None."""
        return self._adapters.get((service_name, method_name))

    def has(self, service_name: str, method_name: str) -> bool:
        """Check if adapter is registered."""
        return (service_name, method_name) in self._adapters

    def unregister(self, service_name: str, method_name: str) -> None:
        """Remove adapter. Raises KeyError if not found."""
        key = (service_name, method_name)
        if key not in self._adapters:
            raise KeyError(f"No adapter for {key}")
        del self._adapters[key]
        logger.info("adapter_unregistered", service=service_name, method=method_name)

    def list_adapters(self) -> list[tuple[str, str]]:
        """Return all registered (service_name, method_name) pairs."""
        return list(self._adapters.keys())

    def discover(self, package: str = "aiflow.pipeline.adapters") -> list[str]:
        """Auto-import all adapter modules in package for self-registration.

        Each adapter module is expected to register itself on import via
        the module-level `registry.register(...)` call.
        """
        from aiflow.pipeline.adapters import discover_adapters

        return discover_adapters()

    def __len__(self) -> int:
        return len(self._adapters)

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self._adapters

    def __repr__(self) -> str:
        return f"AdapterRegistry(adapters={self.list_adapters()})"


# Global registry instance — adapters self-register on import
adapter_registry = AdapterRegistry()
