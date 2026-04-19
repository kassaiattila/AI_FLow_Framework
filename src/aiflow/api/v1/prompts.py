"""Prompt management API endpoints.

Provides cache invalidation and reload endpoints for the PromptManager,
enabling release-free prompt updates via Langfuse label swaps.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import structlog
import yaml
from fastapi import APIRouter
from pydantic import BaseModel

from aiflow.prompts.manager import PromptManager

__all__ = ["router"]

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


def _prompt_search_roots() -> list[Path]:
    """Directories walked by ``GET /list`` to discover prompt YAMLs.

    Override via ``AIFLOW_PROMPT_DIRS`` (comma-separated absolute paths) when
    tests need an isolated fixture tree.
    """
    raw = os.getenv("AIFLOW_PROMPT_DIRS", "").strip()
    if raw:
        return [Path(p.strip()) for p in raw.split(",") if p.strip()]
    repo_root = Path(__file__).resolve().parents[4]
    return [repo_root / "prompts", repo_root / "skills"]


class PromptListItem(BaseModel):
    """Read-only metadata for one prompt YAML file."""

    name: str
    version: str | int | None = None
    path: str
    updated_at: str
    tags: list[str] = []


class PromptListResponse(BaseModel):
    prompts: list[PromptListItem]
    total: int
    source: str = "backend"


@router.get("/list", response_model=PromptListResponse)
async def list_prompts() -> PromptListResponse:
    """List prompt YAML files found on disk.

    Read-only v1 surface: walks the configured prompt roots, parses each
    YAML's top-level ``name``/``version``/``tags`` for display, and falls
    back to the file stem when ``name`` is absent. Langfuse is intentionally
    not consulted here — this is the local SSOT view the admin UI renders
    before richer Langfuse-aware tooling lands (S98+).
    """
    items: list[PromptListItem] = []
    seen: set[str] = set()

    for root in _prompt_search_roots():
        if not root.exists():
            continue
        for yaml_path in sorted(root.rglob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            except (yaml.YAMLError, OSError) as exc:
                logger.warning(
                    "prompt_list.yaml_skip",
                    path=str(yaml_path),
                    error=str(exc),
                )
                continue
            if not isinstance(data, dict):
                continue
            # Only include docs that smell like prompt definitions: presence of
            # any of name / system / user / messages keeps us from listing
            # arbitrary yaml config files.
            if not any(k in data for k in ("system", "user", "messages", "template", "prompt")):
                continue

            name = str(data.get("name") or yaml_path.stem)
            if name in seen:
                continue
            seen.add(name)

            stat = yaml_path.stat()
            updated = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            tags_raw = data.get("tags") or []
            tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []

            items.append(
                PromptListItem(
                    name=name,
                    version=data.get("version"),
                    path=str(yaml_path),
                    updated_at=updated.isoformat(),
                    tags=tags[:3],
                )
            )

    items.sort(key=lambda p: p.name)
    return PromptListResponse(prompts=items, total=len(items))


# Singleton — same instance used by SkillRunner / services
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """Get or create the shared PromptManager instance."""
    global _prompt_manager  # noqa: PLW0603
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


class InvalidateResponse(BaseModel):
    status: str
    prompt_name: str
    cache_size_after: int
    source: str = "backend"


class ReloadAllResponse(BaseModel):
    status: str
    cache_cleared: int
    source: str = "backend"


@router.post("/{prompt_name}/invalidate", response_model=InvalidateResponse)
async def invalidate_prompt(prompt_name: str) -> InvalidateResponse:
    """Invalidate a specific prompt's cache entry.

    After invalidation, the next request for this prompt will fetch
    from Langfuse (if enabled) or reload from YAML.
    """
    pm = get_prompt_manager()
    cache_before = pm.cache_size
    pm.invalidate(prompt_name)
    cache_after = pm.cache_size

    logger.info(
        "prompt.invalidated",
        prompt_name=prompt_name,
        cache_cleared=cache_before - cache_after,
        cache_size_after=cache_after,
    )

    return InvalidateResponse(
        status="invalidated",
        prompt_name=prompt_name,
        cache_size_after=cache_after,
    )


@router.post("/reload-all", response_model=ReloadAllResponse)
async def reload_all_prompts() -> ReloadAllResponse:
    """Clear the entire prompt cache.

    All prompts will be re-fetched from Langfuse or YAML on next access.
    Use after a bulk Langfuse label swap or YAML update.
    """
    pm = get_prompt_manager()
    cache_before = pm.cache_size
    pm._cache.clear()

    logger.info(
        "prompt.reload_all",
        cache_cleared=cache_before,
    )

    return ReloadAllResponse(
        status="all_cleared",
        cache_cleared=cache_before,
    )


@router.get("/cache-status")
async def cache_status() -> dict:
    """Get current prompt cache statistics."""
    pm = get_prompt_manager()
    return {
        "cache_size": pm.cache_size,
        "cache_keys": list(pm._cache.keys()),
        "source": "backend",
    }
