"""RPA Browser service — YAML config CRUD + execution with logging."""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["RPABrowserConfig", "RPABrowserService"]

logger = structlog.get_logger(__name__)


class RPABrowserConfig(BaseModel):
    default_timeout_ms: int = Field(default=30000)
    screenshot_on_error: bool = Field(default=True)


class RPAConfigRecord(BaseModel):
    id: str
    name: str
    description: str | None = None
    yaml_config: str
    target_url: str | None = None
    is_active: bool = True
    schedule_cron: str | None = None
    created_at: str = ""
    updated_at: str = ""


class RPAExecutionRecord(BaseModel):
    id: str
    config_id: str
    status: str = "running"
    steps_total: int | None = None
    steps_completed: int = 0
    results: dict[str, Any] | None = None
    screenshots: list[str] = Field(default_factory=list)
    error: str | None = None
    duration_ms: float | None = None
    started_at: str = ""
    completed_at: str | None = None


class RPABrowserService:
    def __init__(self, config: RPABrowserConfig | None = None, db_url: str | None = None):
        self.config = config or RPABrowserConfig()
        self._db_url = db_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            url = self._db_url or os.getenv(
                "AIFLOW_DATABASE__URL",
                "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
            ).replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
        return self._pool

    # --- Config CRUD ---

    async def create_config(self, name: str, yaml_config: str, description: str | None = None,
                            target_url: str | None = None, schedule_cron: str | None = None) -> RPAConfigRecord:
        config_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO rpa_configs (id, name, description, yaml_config, target_url, schedule_cron, created_at, updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$7)""",
                config_id, name, description, yaml_config, target_url, schedule_cron, now,
            )
        logger.info("rpa_config_created", config_id=config_id, name=name)
        return RPAConfigRecord(id=config_id, name=name, description=description,
                               yaml_config=yaml_config, target_url=target_url,
                               schedule_cron=schedule_cron, created_at=now.isoformat(), updated_at=now.isoformat())

    async def list_configs(self) -> list[RPAConfigRecord]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM rpa_configs ORDER BY created_at DESC")
        return [_row_to_config(r) for r in rows]

    async def get_config(self, config_id: str) -> RPAConfigRecord | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM rpa_configs WHERE id = $1", config_id)
        return _row_to_config(row) if row else None

    async def delete_config(self, config_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM rpa_configs WHERE id = $1", config_id)
        return result == "DELETE 1"

    # --- Execution ---

    async def execute(self, config_id: str) -> RPAExecutionRecord:
        """Execute an RPA config (stub — logs the attempt, returns result)."""
        cfg = await self.get_config(config_id)
        if not cfg:
            raise ValueError(f"Config not found: {config_id}")

        exec_id = str(uuid.uuid4())
        start = time.time()
        now = datetime.now(timezone.utc)
        pool = await self._get_pool()

        # Parse YAML to count steps
        import yaml
        try:
            parsed = yaml.safe_load(cfg.yaml_config)
            steps = parsed.get("steps", []) if isinstance(parsed, dict) else []
            steps_total = len(steps)
        except Exception:
            steps = []
            steps_total = 0

        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO rpa_execution_log (id, config_id, status, steps_total, started_at)
                   VALUES ($1,$2,'running',$3,$4)""",
                exec_id, config_id, steps_total, now,
            )

        try:
            # Execute steps (simplified — real impl would use Playwright/Robot Framework)
            results: dict[str, Any] = {"steps": []}
            for i, step_def in enumerate(steps):
                step_name = step_def.get("name", f"step_{i+1}") if isinstance(step_def, dict) else f"step_{i+1}"
                action = step_def.get("action", "unknown") if isinstance(step_def, dict) else "unknown"
                results["steps"].append({"name": step_name, "action": action, "status": "completed"})

            elapsed = (time.time() - start) * 1000
            completed_at = datetime.now(timezone.utc)

            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE rpa_execution_log SET status='completed', steps_completed=$2,
                       results=$3::jsonb, duration_ms=$4, completed_at=$5 WHERE id=$1""",
                    exec_id, steps_total, json.dumps(results), elapsed, completed_at,
                )

            logger.info("rpa_executed", exec_id=exec_id, steps=steps_total, elapsed_ms=elapsed)
            return RPAExecutionRecord(
                id=exec_id, config_id=config_id, status="completed",
                steps_total=steps_total, steps_completed=steps_total,
                results=results, duration_ms=elapsed,
                started_at=now.isoformat(), completed_at=completed_at.isoformat(),
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE rpa_execution_log SET status='failed', error=$2, duration_ms=$3, completed_at=$4 WHERE id=$1",
                    exec_id, str(e), elapsed, datetime.now(timezone.utc),
                )
            return RPAExecutionRecord(id=exec_id, config_id=config_id, status="failed",
                                      error=str(e), duration_ms=elapsed, started_at=now.isoformat())

    async def list_executions(self, config_id: str | None = None, limit: int = 50) -> list[RPAExecutionRecord]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if config_id:
                rows = await conn.fetch(
                    "SELECT * FROM rpa_execution_log WHERE config_id=$1 ORDER BY started_at DESC LIMIT $2",
                    config_id, limit,
                )
            else:
                rows = await conn.fetch("SELECT * FROM rpa_execution_log ORDER BY started_at DESC LIMIT $1", limit)
        return [_row_to_exec(r) for r in rows]


def _row_to_config(row) -> RPAConfigRecord:
    return RPAConfigRecord(
        id=row["id"], name=row["name"], description=row.get("description"),
        yaml_config=row["yaml_config"], target_url=row.get("target_url"),
        is_active=row.get("is_active", True), schedule_cron=row.get("schedule_cron"),
        created_at=row["created_at"].isoformat() if row.get("created_at") else "",
        updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
    )


def _row_to_exec(row) -> RPAExecutionRecord:
    return RPAExecutionRecord(
        id=row["id"], config_id=row["config_id"], status=row["status"],
        steps_total=row.get("steps_total"), steps_completed=row.get("steps_completed", 0),
        results=json.loads(row["results"]) if row.get("results") else None,
        screenshots=json.loads(row["screenshots"]) if row.get("screenshots") else [],
        error=row.get("error"), duration_ms=row.get("duration_ms"),
        started_at=row["started_at"].isoformat() if row.get("started_at") else "",
        completed_at=row["completed_at"].isoformat() if row.get("completed_at") else None,
    )
