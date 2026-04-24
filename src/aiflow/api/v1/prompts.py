"""Prompt management API endpoints.

Provides cache invalidation and reload endpoints for the PromptManager,
enabling release-free prompt updates via Langfuse label swaps.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path

import structlog
import yaml
from fastapi import APIRouter, HTTPException
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


# Prompt detail / edit — S109b
# -----------------------------------------------------------------------------

_PROMPT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./-]{0,127}$")


class PromptDetailResponse(BaseModel):
    """Full prompt content for the editor."""

    name: str
    version: str | int | None = None
    path: str
    updated_at: str
    tags: list[str] = []
    yaml_text: str
    source: str = "backend"


class PromptUpsertRequest(BaseModel):
    """User-edited raw YAML — validated server-side before write."""

    yaml_text: str


def _resolve_prompt_path(prompt_name: str) -> Path | None:
    """Find the on-disk YAML for a prompt_name across the configured roots."""
    for root in _prompt_search_roots():
        if not root.exists():
            continue
        for yaml_path in root.rglob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            except (yaml.YAMLError, OSError):
                continue
            if not isinstance(data, dict):
                continue
            name = str(data.get("name") or yaml_path.stem)
            if name == prompt_name:
                return yaml_path
    return None


def _validate_prompt_name(prompt_name: str) -> None:
    if not _PROMPT_NAME_PATTERN.match(prompt_name):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid prompt_name: must start with alphanumeric and only "
                "contain [a-zA-Z0-9_./-], max 128 chars."
            ),
        )


@router.get("/{prompt_name:path}", response_model=PromptDetailResponse)
async def get_prompt_detail(prompt_name: str) -> PromptDetailResponse:
    """Return the raw YAML + parsed metadata for a single prompt."""
    _validate_prompt_name(prompt_name)
    path = _resolve_prompt_path(prompt_name)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_name}")
    try:
        yaml_text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(yaml_text) or {}
    except (yaml.YAMLError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read prompt: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="Prompt YAML is not a mapping")
    stat = path.stat()
    updated = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
    tags_raw = data.get("tags") or []
    tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []
    return PromptDetailResponse(
        name=str(data.get("name") or path.stem),
        version=data.get("version"),
        path=str(path),
        updated_at=updated.isoformat(),
        tags=tags,
        yaml_text=yaml_text,
    )


@router.put("/{prompt_name:path}", response_model=PromptDetailResponse)
async def upsert_prompt(prompt_name: str, req: PromptUpsertRequest) -> PromptDetailResponse:
    """Write updated YAML back to disk and invalidate the cache.

    The prompt must already exist on disk — create-new is intentionally out of
    scope. YAML is parsed + the top-level ``name`` must match the URL to catch
    rename-vs-edit confusion.
    """
    _validate_prompt_name(prompt_name)
    path = _resolve_prompt_path(prompt_name)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_name}")
    try:
        data = yaml.safe_load(req.yaml_text)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"YAML parse error: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="YAML root must be a mapping")
    yaml_name = str(data.get("name") or path.stem)
    if yaml_name != prompt_name:
        raise HTTPException(
            status_code=422,
            detail=f"name mismatch: URL={prompt_name!r}, YAML={yaml_name!r}",
        )
    path.write_text(req.yaml_text, encoding="utf-8")
    # Invalidate cache so the next request reads the new YAML
    try:
        get_prompt_manager().invalidate(prompt_name)
    except Exception as exc:  # noqa: BLE001 — cache miss is non-fatal
        logger.warning("prompt_invalidate_failed", prompt=prompt_name, error=str(exc))
    logger.info("prompt_upserted", prompt=prompt_name, path=str(path))

    stat = path.stat()
    updated = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
    tags_raw = data.get("tags") or []
    tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []
    return PromptDetailResponse(
        name=prompt_name,
        version=data.get("version"),
        path=str(path),
        updated_at=updated.isoformat(),
        tags=tags,
        yaml_text=req.yaml_text,
    )


# Singleton — same instance used by SkillRunner / services
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """Get or create the shared PromptManager instance.

    Sprint R / S139+S140: when ``AIFLOW_PROMPT_WORKFLOWS__ENABLED=true``
    the manager is built with the workflow loader pointed at
    ``settings.prompt_workflows.workflows_dir`` so the new
    ``get_workflow`` lookup path is functional. Flag-off behaviour is
    unchanged from Sprint Q.
    """
    global _prompt_manager  # noqa: PLW0603
    if _prompt_manager is None:
        from aiflow.core.config import get_settings
        from aiflow.prompts.workflow_loader import PromptWorkflowLoader

        settings = get_settings()
        wf_settings = settings.prompt_workflows
        loader: PromptWorkflowLoader | None = None
        if wf_settings.enabled:
            workflows_dir = Path(wf_settings.workflows_dir)
            if not workflows_dir.is_absolute():
                workflows_dir = Path(__file__).resolve().parents[4] / workflows_dir
            loader = PromptWorkflowLoader(workflows_dir)
            loader.register_dir()

        _prompt_manager = PromptManager(
            workflows_enabled=wf_settings.enabled,
            workflow_loader=loader,
        )

        # Auto-discover the existing skill prompts so workflow lookups
        # can resolve nested step prompts.
        if wf_settings.enabled:
            repo_root = Path(__file__).resolve().parents[4]
            for skill_dir in (repo_root / "skills").glob("*/prompts"):
                if skill_dir.is_dir():
                    _prompt_manager.register_yaml_dir(skill_dir)
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
