"""PromptDefinition Pydantic model matching the YAML prompt format.

Supports Jinja2 template rendering for system/user messages and
label-based environments (dev/test/staging/prod).
"""

from __future__ import annotations

from typing import Any

from jinja2 import BaseLoader, Environment, StrictUndefined
from pydantic import BaseModel, Field

__all__ = [
    "PromptDefinition",
    "PromptConfig",
    "PromptExample",
    "LangfuseSettings",
]

_JINJA_ENV = Environment(loader=BaseLoader(), undefined=StrictUndefined)


class PromptConfig(BaseModel):
    """LLM configuration parameters."""

    model_config = {"extra": "ignore"}

    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2048
    response_format: str | None = None


class PromptExample(BaseModel):
    """Few-shot example for a prompt."""

    input: str
    output: str
    explanation: str = ""


class LangfuseSettings(BaseModel):
    """Langfuse sync and label settings."""

    sync: bool = True
    labels: list[str] = Field(default_factory=lambda: ["dev", "test", "staging", "prod"])


class PromptMetadata(BaseModel):
    """Prompt metadata for cataloguing."""

    model_config = {"extra": "ignore"}

    language: str = "en"
    tags: list[str] = Field(default_factory=list)


class PromptDefinition(BaseModel):
    """Full prompt definition matching the YAML source format.

    Architecture: YAML source (Git) -> Langfuse (Cloud SSOT) -> Runtime cache.
    """

    model_config = {"extra": "ignore"}

    name: str
    version: str = "1.0"
    description: str = ""

    # Template fields (Jinja2)
    system: str = ""
    user: str = ""

    # Configuration
    config: PromptConfig = Field(default_factory=PromptConfig)
    metadata: PromptMetadata = Field(default_factory=PromptMetadata)
    examples: list[PromptExample] = Field(default_factory=list)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)

    def compile(self, variables: dict[str, Any] | None = None) -> list[dict[str, str]]:
        """Render Jinja2 templates and return an OpenAI-compatible messages list.

        Args:
            variables: Template variables to substitute into system/user templates.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        vars_ = variables or {}
        messages: list[dict[str, str]] = []

        if self.system:
            system_template = _JINJA_ENV.from_string(self.system)
            messages.append(
                {
                    "role": "system",
                    "content": system_template.render(**vars_),
                }
            )

        # Inject examples as assistant/user turns
        for example in self.examples:
            messages.append({"role": "user", "content": example.input})
            messages.append({"role": "assistant", "content": example.output})

        if self.user:
            user_template = _JINJA_ENV.from_string(self.user)
            messages.append(
                {
                    "role": "user",
                    "content": user_template.render(**vars_),
                }
            )

        return messages
