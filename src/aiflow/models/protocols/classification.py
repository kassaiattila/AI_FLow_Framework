"""Classification protocol for text categorization models."""

from abc import abstractmethod

from pydantic import BaseModel

from aiflow.models.protocols.base import BaseModelProtocol, ModelCallResult

__all__ = [
    "ClassificationInput",
    "ClassificationResult",
    "ClassificationOutput",
    "ClassificationProtocol",
]


class ClassificationResult(BaseModel):
    label: str
    confidence: float
    all_scores: dict[str, float] = {}


class ClassificationInput(BaseModel):
    text: str
    labels: list[str] | None = None  # Zero-shot candidate labels
    multi_label: bool = False
    model: str | None = None


class ClassificationOutput(BaseModel):
    results: list[ClassificationResult]
    model_used: str = ""


class ClassificationProtocol(BaseModelProtocol):
    @abstractmethod
    async def classify(
        self, input_data: ClassificationInput
    ) -> ModelCallResult[ClassificationOutput]: ...
