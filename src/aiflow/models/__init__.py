"""AIFlow model abstraction layer - LLM, embedding, classification, extraction, vision."""

from aiflow.models.client import ModelClient
from aiflow.models.metadata import ModelMetadata, ModelType
from aiflow.models.protocols.base import BaseModelProtocol, ModelCallResult
from aiflow.models.protocols.classification import ClassificationProtocol
from aiflow.models.protocols.embedding import EmbeddingProtocol
from aiflow.models.protocols.extraction import ExtractionProtocol
from aiflow.models.protocols.generation import TextGenerationProtocol
from aiflow.models.registry import ModelRegistry

__all__ = [
    # Client
    "ModelClient",
    # Registry
    "ModelRegistry",
    # Metadata
    "ModelMetadata",
    "ModelType",
    # Protocols
    "BaseModelProtocol",
    "ClassificationProtocol",
    "EmbeddingProtocol",
    "ExtractionProtocol",
    "ModelCallResult",
    "TextGenerationProtocol",
]
