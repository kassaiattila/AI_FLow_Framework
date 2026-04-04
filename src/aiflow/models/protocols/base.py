"""Base protocol and result types for model calls."""
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

__all__ = ["ModelCallResult", "BaseModelProtocol"]

TOutput = TypeVar("TOutput", bound=BaseModel)


class ModelCallResult(BaseModel, Generic[TOutput]):
    """Standard result wrapper for all model calls."""
    output: Any  # The actual result (type varies by protocol)
    model_used: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    cached: bool = False
    metadata: dict[str, Any] = {}


class BaseModelProtocol(ABC):
    """Abstract base for all model protocols."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the model backend is available."""
        ...
