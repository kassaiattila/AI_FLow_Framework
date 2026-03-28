"""PromptManager - multi-layer prompt loading with caching.

Resolution order: 1) in-memory cache, 2) Langfuse (if enabled), 3) local YAML fallback.
Supports label-based environments: dev/test/staging/prod.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel

from aiflow.prompts.schema import PromptDefinition

__all__ = ["PromptManager"]

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
        2. Langfuse remote (if enabled) -- placeholder for Phase 5
        3. Local YAML file fallback

    Args:
        cache_ttl: Cache time-to-live in seconds (default 300).
        langfuse_enabled: Whether to attempt Langfuse lookup (default False).
    """

    def __init__(
        self,
        cache_ttl: float = 300.0,
        langfuse_enabled: bool = False,
    ) -> None:
        self._cache: dict[str, _CacheEntry] = {}
        self._cache_ttl = cache_ttl
        self._langfuse_enabled = langfuse_enabled
        self._yaml_registry: dict[str, Path] = {}  # prompt_name -> yaml_path
        logger.info(
            "prompt_manager.init",
            cache_ttl=cache_ttl,
            langfuse_enabled=langfuse_enabled,
        )

    # --- Public API ---

    def get(self, prompt_name: str, label: str = "prod") -> PromptDefinition:
        """Load a prompt by name with label-based environment resolution.

        Resolution order:
            1. In-memory cache (if not expired)
            2. Langfuse (if enabled) -- placeholder
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

        # 2. Langfuse lookup (placeholder for Phase 5)
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

        raise KeyError(
            f"Prompt '{prompt_name}' not found in cache, Langfuse, or YAML registry"
        )

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

    def _put_cache(
        self, cache_key: str, prompt: PromptDefinition, label: str
    ) -> None:
        """Store a prompt in the in-memory cache with TTL."""
        self._cache[cache_key] = _CacheEntry(
            prompt=prompt,
            label=label,
            expires_at=time.monotonic() + self._cache_ttl,
        )

    def _fetch_from_langfuse(
        self, prompt_name: str, label: str
    ) -> PromptDefinition | None:
        """Fetch prompt from Langfuse API (placeholder for Phase 5).

        Returns:
            PromptDefinition if found, None otherwise.
        """
        logger.debug(
            "prompt_manager.langfuse_placeholder",
            prompt=prompt_name,
            label=label,
            note="Langfuse integration will be implemented in Phase 5",
        )
        return None
