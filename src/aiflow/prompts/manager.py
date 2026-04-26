"""PromptManager - multi-layer prompt loading with caching.

Resolution order: 1) in-memory cache, 2) Langfuse (if enabled), 3) local YAML fallback.
Supports label-based environments: dev/test/staging/prod.
Uses Langfuse v4 SDK get_prompt() for remote prompt resolution.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel

from aiflow.core.errors import FeatureDisabled
from aiflow.prompts.schema import PromptConfig, PromptDefinition
from aiflow.prompts.workflow import PromptWorkflow
from aiflow.prompts.workflow_loader import PromptWorkflowLoader, WorkflowYamlError

# Re-export workflow types so callers can import them via `aiflow.prompts.manager`
# (also keeps the formatter from stripping these "unused" imports).
_RUNTIME_HOOKS = (FeatureDisabled, PromptWorkflow, PromptWorkflowLoader, WorkflowYamlError)

__all__ = ["PromptManager", "WorkflowResolutionError"]


class WorkflowResolutionError(LookupError):
    """Raised when a workflow's nested prompt cannot be resolved.

    Carries ``workflow`` + ``step_id`` so callers can pinpoint the
    failure (vs. a bare ``KeyError`` from the underlying ``get`` call).
    """

    def __init__(self, workflow: str, step_id: str, prompt_name: str, cause: Exception) -> None:
        self.workflow = workflow
        self.step_id = step_id
        self.prompt_name = prompt_name
        self.__cause__ = cause
        super().__init__(
            f"workflow {workflow!r}: step {step_id!r} prompt {prompt_name!r} not resolvable: {cause}"
        )


logger = structlog.get_logger(__name__)


class _CacheEntry(BaseModel):
    """Internal cache entry with TTL tracking."""

    prompt: PromptDefinition
    label: str
    expires_at: float


class PromptManager:
    """Multi-layer prompt manager with in-memory cache and YAML fallback.

    Resolution order for get():
        1. In-memory cache (if not expired)
        2. Langfuse remote (if enabled, via v4 get_prompt API)
        3. Local YAML file fallback

    Args:
        cache_ttl: Cache time-to-live in seconds (default 300).
        langfuse_enabled: Whether to attempt Langfuse lookup (default False).
    """

    def __init__(
        self,
        cache_ttl: float = 300.0,
        langfuse_enabled: bool = False,
        langfuse_client: Any = None,
        *,
        workflows_enabled: bool = False,
        workflow_loader: PromptWorkflowLoader | None = None,
    ) -> None:
        self._cache: dict[str, _CacheEntry] = {}
        self._cache_ttl = cache_ttl
        self._langfuse_enabled = langfuse_enabled
        self._langfuse_client = langfuse_client
        self._yaml_registry: dict[str, Path] = {}  # prompt_name -> yaml_path
        self._workflows_enabled = workflows_enabled
        self._workflow_loader = workflow_loader
        self._workflow_cache: dict[str, tuple[PromptWorkflow, float]] = {}
        logger.info(
            "prompt_manager.init",
            cache_ttl=cache_ttl,
            langfuse_enabled=langfuse_enabled,
            has_langfuse_client=langfuse_client is not None,
            workflows_enabled=workflows_enabled,
            has_workflow_loader=workflow_loader is not None,
        )

    # --- Public API ---

    def get(self, prompt_name: str, label: str = "prod") -> PromptDefinition:
        """Load a prompt by name with label-based environment resolution.

        Resolution order:
            1. In-memory cache (if not expired)
            2. Langfuse (if enabled, via v4 get_prompt API)
            3. Local YAML fallback

        Args:
            prompt_name: The prompt's unique name.
            label: Environment label (dev/test/staging/prod).

        Returns:
            The resolved PromptDefinition.

        Raises:
            KeyError: If prompt not found in any layer.
        """
        cache_key = f"{prompt_name}:{label}"

        # 1. Cache lookup
        entry = self._cache.get(cache_key)
        if entry is not None and entry.expires_at > time.monotonic():
            logger.debug("prompt_manager.cache_hit", prompt=prompt_name, label=label)
            return entry.prompt

        # 2. Langfuse lookup (real v4 API)
        if self._langfuse_enabled:
            langfuse_prompt = self._fetch_from_langfuse(prompt_name, label)
            if langfuse_prompt is not None:
                self._put_cache(cache_key, langfuse_prompt, label)
                return langfuse_prompt

        # 3. YAML fallback
        if prompt_name in self._yaml_registry:
            yaml_path = self._yaml_registry[prompt_name]
            prompt = self.load_yaml(yaml_path)
            self._put_cache(cache_key, prompt, label)
            logger.info("prompt_manager.yaml_fallback", prompt=prompt_name, path=str(yaml_path))
            return prompt

        raise KeyError(f"Prompt '{prompt_name}' not found in cache, Langfuse, or YAML registry")

    def load_yaml(self, path: Path | str) -> PromptDefinition:
        """Load a single YAML prompt file and return a PromptDefinition.

        Args:
            path: Path to the YAML prompt file.

        Returns:
            Parsed PromptDefinition.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValueError: If the YAML content is invalid.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Prompt YAML not found: {path}")

        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML prompt format in {path}")

        prompt = PromptDefinition(**data)
        logger.debug("prompt_manager.load_yaml", path=str(path), name=prompt.name)
        return prompt

    def register_yaml_dir(self, directory: Path | str) -> int:
        """Discover and register all YAML prompt files in a directory.

        Scans for .yaml and .yml files, parses each, and registers by name.

        Args:
            directory: Directory path to scan.

        Returns:
            Number of prompts discovered and registered.
        """
        directory = Path(directory)
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        count = 0
        for ext in ("*.yaml", "*.yml"):
            for yaml_path in sorted(directory.glob(ext)):
                try:
                    prompt = self.load_yaml(yaml_path)
                    self._yaml_registry[prompt.name] = yaml_path
                    count += 1
                    logger.debug(
                        "prompt_manager.registered",
                        name=prompt.name,
                        path=str(yaml_path),
                    )
                except Exception as exc:
                    logger.warning(
                        "prompt_manager.register_skip",
                        path=str(yaml_path),
                        error=str(exc),
                    )

        logger.info(
            "prompt_manager.register_yaml_dir",
            directory=str(directory),
            count=count,
        )
        return count

    def get_workflow(
        self,
        name: str,
        *,
        label: str | None = None,
    ) -> tuple[PromptWorkflow, dict[str, PromptDefinition]]:
        """Resolve a :class:`PromptWorkflow` and all its nested prompts.

        Sprint R / S139 — descriptor lookup only. Resolution order:
            1. In-memory workflow cache (TTL-bounded).
            2. Langfuse JSON-typed prompt under ``workflow:<name>``
               (if ``langfuse_enabled``).
            3. Local YAML via the configured :class:`PromptWorkflowLoader`.

        Each step's prompt is then resolved through the existing
        :meth:`get` 3-layer lookup using the workflow's ``default_label``
        (or the override passed in).

        Args:
            name: Workflow name.
            label: Override for nested prompt label resolution; defaults
                to the workflow's ``default_label``.

        Returns:
            ``(workflow, {step_id: PromptDefinition})``

        Raises:
            FeatureDisabled: When ``workflows_enabled`` is False.
            KeyError: When the workflow itself cannot be found in any
                layer.
            WorkflowResolutionError: When the workflow loads but a
                nested prompt cannot be resolved.
        """
        if not self._workflows_enabled:
            raise FeatureDisabled("prompt_workflows")

        workflow = self._resolve_workflow(name)
        effective_label = label or workflow.default_label

        resolved: dict[str, PromptDefinition] = {}
        for step in workflow.steps:
            try:
                resolved[step.id] = self.get(step.prompt_name, label=effective_label)
            except Exception as exc:  # noqa: BLE001 — caught + rewrapped
                raise WorkflowResolutionError(
                    workflow=workflow.name,
                    step_id=step.id,
                    prompt_name=step.prompt_name,
                    cause=exc,
                ) from exc

        logger.info(
            "prompt_manager.get_workflow_ok",
            workflow=workflow.name,
            label=effective_label,
            steps=len(resolved),
        )
        return workflow, resolved

    def _resolve_workflow(self, name: str) -> PromptWorkflow:
        """3-layer resolution for a workflow descriptor itself."""
        cached = self._workflow_cache.get(name)
        if cached is not None and cached[1] > time.monotonic():
            return cached[0]

        # 2. Langfuse (JSON-typed prompt under workflow:<name>)
        if self._langfuse_enabled:
            wf = self._fetch_workflow_from_langfuse(name)
            if wf is not None:
                self._workflow_cache[name] = (wf, time.monotonic() + self._cache_ttl)
                return wf

        # 3. Local YAML via the loader
        if self._workflow_loader is not None:
            path = self._workflow_loader.path_for(name)
            if path is not None:
                wf = self._workflow_loader.load_from_yaml(path)
                self._workflow_cache[name] = (wf, time.monotonic() + self._cache_ttl)
                logger.info(
                    "prompt_manager.workflow_yaml_fallback",
                    workflow=name,
                    path=str(path),
                )
                return wf

        raise KeyError(f"Workflow {name!r} not found in cache, Langfuse, or local YAML registry")

    def _fetch_workflow_from_langfuse(self, name: str) -> PromptWorkflow | None:
        """Fetch a workflow descriptor from Langfuse as a JSON prompt.

        Convention: workflows live under the prompt name
        ``workflow:<name>`` with ``type="text"`` and JSON content.
        Returns ``None`` on miss / failure (caller falls back to local).
        """
        client = self._langfuse_client
        if client is None:
            try:
                from aiflow.observability.tracing import get_langfuse_client

                client = get_langfuse_client()
            except ImportError:
                return None

        if client is None:
            return None

        langfuse_key = f"workflow:{name}"
        try:
            remote = client.get_prompt(name=langfuse_key, label="prod", type="text")
            payload = remote.prompt
            if isinstance(payload, str):
                import json as _json

                payload = _json.loads(payload)
            if not isinstance(payload, dict):
                logger.warning(
                    "prompt_manager.workflow_langfuse_bad_payload",
                    workflow=name,
                    payload_type=type(payload).__name__,
                )
                return None
            return PromptWorkflow(**payload)
        except Exception as exc:  # noqa: BLE001 — Langfuse is best-effort
            error_str = str(exc)
            if "not found" in error_str.lower() or "404" in error_str:
                logger.debug(
                    "prompt_manager.workflow_langfuse_miss",
                    workflow=name,
                )
            else:
                logger.warning(
                    "prompt_manager.workflow_langfuse_error",
                    workflow=name,
                    error=error_str,
                )
            return None

    def list_langfuse_workflows(self) -> list[PromptWorkflow]:
        """Sprint W SW-4 (SR-FU-6) — list ``workflow:<name>`` Langfuse prompts.

        Returns the descriptors hosted on Langfuse under the
        ``workflow:<name>`` JSON-typed prompt convention. Today this is a
        **stub** that returns an empty list when:

        * The Langfuse client is unavailable, OR
        * The v4 SDK does not expose a list-by-prefix call.

        When the Langfuse SDK ships a list endpoint, swap the body out
        for a real call. The router consumes whatever this returns.
        """
        client = self._langfuse_client
        if client is None:
            try:
                from aiflow.observability.tracing import get_langfuse_client

                client = get_langfuse_client()
            except ImportError:
                return []

        if client is None:
            return []

        # The Langfuse v4 Python SDK has no cheap list-by-prefix call as
        # of this writing. Operators that want Langfuse-hosted workflows
        # in the admin UI will get an empty list until the helper lands.
        # The local YAML path keeps working unchanged.
        return []

    def invalidate(self, prompt_name: str, label: str | None = None) -> None:
        """Remove prompt(s) from cache.

        Args:
            prompt_name: Name of the prompt to invalidate.
            label: If given, only invalidate that label; otherwise all labels.
        """
        if label:
            cache_key = f"{prompt_name}:{label}"
            self._cache.pop(cache_key, None)
        else:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{prompt_name}:")]
            for k in keys_to_remove:
                del self._cache[k]

    @property
    def cache_size(self) -> int:
        """Return current number of cached entries."""
        return len(self._cache)

    @property
    def registered_prompts(self) -> list[str]:
        """Return list of registered prompt names."""
        return list(self._yaml_registry.keys())

    # --- Private helpers ---

    def _put_cache(self, cache_key: str, prompt: PromptDefinition, label: str) -> None:
        """Store a prompt in the in-memory cache with TTL."""
        self._cache[cache_key] = _CacheEntry(
            prompt=prompt,
            label=label,
            expires_at=time.monotonic() + self._cache_ttl,
        )

    def _fetch_from_langfuse(self, prompt_name: str, label: str) -> PromptDefinition | None:
        """Fetch prompt from Langfuse v4 API.

        Retrieves a chat prompt from Langfuse and converts it back to a
        PromptDefinition. Falls back to None if not found or client unavailable.
        """
        client = self._langfuse_client
        if not client:
            # Try global client as fallback
            try:
                from aiflow.observability.tracing import get_langfuse_client

                client = get_langfuse_client()
            except ImportError:
                pass

        if not client:
            logger.debug("prompt_manager.langfuse_no_client", prompt=prompt_name)
            return None

        try:
            remote = client.get_prompt(name=prompt_name, label=label, type="chat")
            # ChatPromptClient: name, version, config, labels, prompt are direct attributes

            # Reconstruct PromptDefinition from Langfuse chat prompt
            system_text = ""
            user_text = ""
            messages = remote.prompt  # list of message dicts
            if isinstance(messages, list):
                for msg in messages:
                    if isinstance(msg, dict):
                        if msg.get("role") == "system":
                            system_text = msg.get("content", "")
                        elif msg.get("role") == "user":
                            user_text = msg.get("content", "")

            # Reconstruct config from Langfuse config field
            remote_config = remote.config or {}
            config = PromptConfig(
                model=remote_config.get("model", "gpt-4o"),
                temperature=remote_config.get("temperature", 0.7),
                max_tokens=remote_config.get("max_tokens", 2048),
                response_format=remote_config.get("response_format"),
            )

            prompt_def = PromptDefinition(
                name=remote.name,
                version=remote_config.get("yaml_version", str(remote.version)),
                description=remote_config.get("description", ""),
                system=system_text,
                user=user_text,
                config=config,
            )

            logger.info(
                "prompt_manager.langfuse_fetch_ok",
                prompt=prompt_name,
                label=label,
                version=prompt_def.version,
            )
            return prompt_def

        except Exception as exc:
            error_str = str(exc)
            if "not found" in error_str.lower() or "404" in error_str:
                logger.debug("prompt_manager.langfuse_not_found", prompt=prompt_name, label=label)
            else:
                logger.warning(
                    "prompt_manager.langfuse_fetch_failed", prompt=prompt_name, error=error_str
                )
            return None
