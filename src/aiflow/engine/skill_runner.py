"""SkillRunner - simple sequential step executor for AIFlow skills.

Unlike WorkflowRunner (which handles DAGs, branching, checkpoints),
SkillRunner just runs steps in order, passing output -> input.

Usage:
    runner = SkillRunner.from_env()
    result = await runner.run_steps(
        [classify, elaborate, extract, review, generate],
        {"user_input": "Szabadsag igenyeles..."},
    )

    # Or run a single step:
    output = await runner.run_step(classify, {"user_input": "..."})
"""
from __future__ import annotations

import inspect
import time
from pathlib import Path
from typing import Any, Callable

import structlog

from aiflow.core.context import ExecutionContext
from aiflow.models.client import ModelClient
from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.prompts.manager import PromptManager

__all__ = ["SkillRunner"]

logger = structlog.get_logger(__name__)


class SkillRunner:
    """Sequential step runner with service injection.

    Steps can accept these optional keyword parameters:
        models: ModelClient - for LLM calls
        prompts: PromptManager - for prompt loading
        ctx: ExecutionContext - for request context
    """

    def __init__(
        self,
        models: ModelClient,
        prompts: PromptManager,
        ctx: ExecutionContext | None = None,
    ) -> None:
        self.models = models
        self.prompts = prompts
        self.ctx = ctx or ExecutionContext()

    @classmethod
    def from_env(
        cls,
        default_model: str = "openai/gpt-4o-mini",
        prompt_dirs: list[Path | str] | None = None,
    ) -> SkillRunner:
        """Create a SkillRunner from environment variables.

        Reads OPENAI_API_KEY from env (via litellm).
        Loads prompts from given directories.
        """
        backend = LiteLLMBackend(default_model=default_model)
        models = ModelClient(generation_backend=backend)
        prompts = PromptManager()

        for d in prompt_dirs or []:
            prompts.register_yaml_dir(Path(d))

        return cls(models=models, prompts=prompts)

    async def run_step(
        self,
        step_func: Callable,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a single step with service injection."""
        sig = inspect.signature(step_func)
        kwargs: dict[str, Any] = {}

        params = sig.parameters
        if "models" in params:
            kwargs["models"] = self.models
        if "prompts" in params:
            kwargs["prompts"] = self.prompts
        if "ctx" in params:
            kwargs["ctx"] = self.ctx

        start = time.monotonic()

        if kwargs:
            result = await step_func(input_data, **kwargs)
        else:
            result = await step_func(input_data)

        duration = (time.monotonic() - start) * 1000
        step_name = getattr(step_func, "__wrapped__", step_func).__name__
        logger.info("skill_step_done", step=step_name, duration_ms=round(duration))

        return result if isinstance(result, dict) else {"result": result}

    async def run_steps(
        self,
        steps: list[Callable],
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run steps sequentially. Each step's output is merged with accumulated data."""
        data = dict(input_data)
        total_start = time.monotonic()

        for step_func in steps:
            result = await self.run_step(step_func, data)
            data = {**data, **result}

        total_duration = (time.monotonic() - total_start) * 1000
        logger.info(
            "skill_run_complete",
            steps=len(steps),
            duration_ms=round(total_duration),
        )
        return data
