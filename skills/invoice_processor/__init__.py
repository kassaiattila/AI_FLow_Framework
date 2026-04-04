"""Invoice Processor skill - extract structured data from Hungarian PDF invoices."""
from __future__ import annotations

from pathlib import Path

from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager

__all__ = ["models_client", "prompt_manager"]

_backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
models_client = ModelClient(generation_backend=_backend, embedding_backend=_backend)
prompt_manager = PromptManager()
prompt_manager.register_yaml_dir(Path(__file__).parent / "prompts")
