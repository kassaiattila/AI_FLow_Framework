"""Classification protocol for text categorization models.

`ClassificationResult` is re-exported from `aiflow.services.classifier.service`
— that is the single source-of-truth operational result model used at runtime
(UC3 Sprint K unification). The protocol input/output envelope here stays for
the abstract `ClassificationProtocol` contract; Phase 2 implementers return
the same 11-field result shape.
"""

from abc import abstractmethod

from pydantic import BaseModel

from aiflow.models.protocols.base import BaseModelProtocol, ModelCallResult
from aiflow.services.classifier.service import ClassificationResult

__all__ = [
    "ClassificationInput",
    "ClassificationResult",
    "ClassificationOutput",
    "ClassificationProtocol",
]


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
