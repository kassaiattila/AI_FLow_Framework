"""Model metadata, types, and lifecycle definitions."""

from enum import StrEnum

from pydantic import BaseModel

__all__ = ["ModelType", "ModelLifecycle", "ServingMode", "ModelMetadata"]


class ModelType(StrEnum):
    LLM = "llm"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    VISION = "vision"
    SPEECH_TO_TEXT = "speech_to_text"
    CUSTOM = "custom"


class ModelLifecycle(StrEnum):
    REGISTERED = "registered"
    TESTED = "tested"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ServingMode(StrEnum):
    API = "api"
    LOCAL = "local"
    SERVER = "server"
    SIDECAR = "sidecar"


class ModelMetadata(BaseModel):
    """Metadata for a registered model."""

    name: str
    model_type: ModelType
    provider: str
    version: str = "latest"
    lifecycle: ModelLifecycle = ModelLifecycle.REGISTERED
    serving_mode: ServingMode = ServingMode.API
    endpoint_url: str | None = None
    model_path: str | None = None
    capabilities: list[str] = []
    cost_per_input_token: float = 0.0
    cost_per_output_token: float = 0.0
    cost_per_request: float = 0.0
    priority: int = 100
    fallback_model: str | None = None
    avg_latency_ms: float | None = None
    tags: list[str] = []
