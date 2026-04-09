"""Prompt management API endpoints.

Provides cache invalidation and reload endpoints for the PromptManager,
enabling release-free prompt updates via Langfuse label swaps.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from aiflow.prompts.manager import PromptManager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])

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
