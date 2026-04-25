"""Email Intent Processor skill - Kafka-triggered email classification and routing.

Module-level service initialization for step function closures.

Sprint T / S148 (S141-FU-1): when ``AIFLOW_PROMPT_WORKFLOWS__ENABLED=true``
the module-level :data:`prompt_manager` is built workflow-aware so the
``classify_intent`` step can opt into the ``email_intent_chain``
descriptor via :class:`PromptWorkflowExecutor`. Flag-off keeps the
legacy single-prompt resolution byte-for-byte unchanged.
"""

from pathlib import Path

from aiflow.core.config import get_settings
from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager
from aiflow.prompts.workflow_loader import PromptWorkflowLoader

__all__ = ["models_client", "prompt_manager"]

# Module-level singletons (step functions close over these)
_backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
models_client = ModelClient(generation_backend=_backend)

_wf_settings = get_settings().prompt_workflows
_workflow_loader: PromptWorkflowLoader | None = None
if _wf_settings.enabled:
    _wf_dir = Path(_wf_settings.workflows_dir)
    if not _wf_dir.is_absolute():
        # Repo root = three parents up from this file (skills/<name>/__init__.py)
        _wf_dir = Path(__file__).resolve().parents[2] / _wf_dir
    _workflow_loader = PromptWorkflowLoader(_wf_dir)
    _workflow_loader.register_dir()

prompt_manager = PromptManager(
    workflows_enabled=_wf_settings.enabled,
    workflow_loader=_workflow_loader,
)
prompt_manager.register_yaml_dir(Path(__file__).parent / "prompts")
