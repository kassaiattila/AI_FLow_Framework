"""Extraction protocol for NER and entity extraction models."""
from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from aiflow.models.protocols.base import BaseModelProtocol, ModelCallResult

__all__ = ["ExtractionEntity", "ExtractionInput", "ExtractionOutput", "ExtractionProtocol"]

class ExtractionEntity(BaseModel):
    text: str
    label: str
    start: int | None = None
    end: int | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = {}

class ExtractionInput(BaseModel):
    text: str
    entity_types: list[str] | None = None  # Filter to specific entity types
    model: str | None = None

class ExtractionOutput(BaseModel):
    entities: list[ExtractionEntity]
    model_used: str = ""

class ExtractionProtocol(BaseModelProtocol):
    @abstractmethod
    async def extract(self, input_data: ExtractionInput) -> ModelCallResult[ExtractionOutput]: ...
