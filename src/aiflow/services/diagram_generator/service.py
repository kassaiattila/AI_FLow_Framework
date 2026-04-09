"""Diagram Generator service implementation.

Supports three diagram semantics:
- flowchart          → runs the process_documentation skill pipeline (default).
- sequence           → uses dedicated service prompts (planner → mermaid → reviewer).
- bpmn_swimlane      → uses dedicated service prompts (planner → mermaid → reviewer).

Persists results to generated_diagrams table and supports export to multiple formats.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "SUPPORTED_DIAGRAM_TYPES",
    "DiagramGeneratorConfig",
    "DiagramGeneratorService",
]

logger = structlog.get_logger(__name__)

SUPPORTED_DIAGRAM_TYPES = ("flowchart", "sequence", "bpmn_swimlane")


class DiagramGeneratorConfig(BaseModel):
    """Configuration for Diagram Generator service."""

    default_export_formats: list[str] = Field(default=["mermaid", "svg"])
    kroki_url: str = Field(default="http://localhost:8000")
    max_input_length: int = Field(default=5000)
    planner_model: str = Field(default="openai/gpt-4o-mini")
    mermaid_model: str = Field(default="openai/gpt-4o-mini")
    reviewer_model: str = Field(default="openai/gpt-4o-mini")


class DiagramRecord(BaseModel):
    """A persisted diagram record."""

    id: str
    user_input: str
    mermaid_code: str
    drawio_xml: str | None = None
    bpmn_xml: str | None = None
    svg_content: str | None = None
    review: dict[str, Any] | None = None
    export_formats: list[str] = []
    created_by: str | None = None
    created_at: str = ""
    updated_at: str = ""


class DiagramGeneratorService:
    """Service for generating and persisting diagrams (flowchart / sequence / bpmn_swimlane)."""

    def __init__(self, config: DiagramGeneratorConfig | None = None, db_url: str | None = None):
        self.config = config or DiagramGeneratorConfig()
        self._db_url = db_url
        self._pool = None
        self._models = None
        self._prompts = None

    async def _get_pool(self):
        if self._pool is None:
            import os

            import asyncpg

            url = self._db_url or os.getenv(
                "AIFLOW_DATABASE__URL",
                "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
            ).replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
        return self._pool

    def _get_models(self):
        """Lazy init of ModelClient so unit tests can monkey-patch before use."""
        if self._models is None:
            from aiflow.models.backends.litellm_backend import LiteLLMBackend
            from aiflow.models.client import ModelClient

            backend = LiteLLMBackend(default_model=self.config.planner_model)
            self._models = ModelClient(generation_backend=backend)
        return self._models

    def _get_prompt_manager(self):
        """Lazy init of PromptManager with the service's own prompt directory."""
        if self._prompts is None:
            from aiflow.prompts.manager import PromptManager

            pm = PromptManager()
            prompt_dir = Path(__file__).parent / "prompts"
            if prompt_dir.is_dir():
                pm.register_yaml_dir(prompt_dir)
            self._prompts = pm
        return self._prompts

    async def generate(
        self,
        user_input: str,
        diagram_type: str = "flowchart",
        created_by: str | None = None,
    ) -> DiagramRecord:
        """Generate a diagram from natural language and persist it.

        Args:
            user_input: Free-form process / flow description.
            diagram_type: One of ``flowchart`` (default, uses the
                ``process_documentation`` skill pipeline), ``sequence``,
                or ``bpmn_swimlane`` (both use dedicated service prompts).
            created_by: Optional user id for audit.
        """
        if not user_input.strip():
            raise ValueError("user_input is required")

        # Normalise diagram_type. Anything outside the whitelist silently
        # falls back to flowchart so the adapter never crashes.
        if diagram_type not in SUPPORTED_DIAGRAM_TYPES:
            logger.warning(
                "diagram_type_unsupported_fallback",
                requested=diagram_type,
                fallback="flowchart",
            )
            diagram_type = "flowchart"

        output_dir = Path(tempfile.mkdtemp(prefix="aiflow_diagram_"))
        diagram_id = str(uuid.uuid4())

        if diagram_type == "flowchart":
            mermaid_code, svg_content, drawio_xml, review_data = await self._generate_flowchart(
                user_input, output_dir
            )
        else:
            mermaid_code, svg_content, drawio_xml, review_data = await self._generate_with_prompts(
                user_input, diagram_type
            )

        now = datetime.now(UTC).isoformat()

        # Persist to DB
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO generated_diagrams
                   (id, user_input, mermaid_code, drawio_xml, svg_content, review, export_formats, created_by, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, $9, $9)""",
                diagram_id,
                user_input,
                mermaid_code,
                drawio_xml,
                svg_content,
                _to_json(review_data),
                _to_json(["mermaid", "svg"]),
                created_by,
                datetime.now(UTC),
            )

        logger.info(
            "diagram_generated",
            diagram_id=diagram_id,
            diagram_type=diagram_type,
            mermaid_len=len(mermaid_code),
        )

        return DiagramRecord(
            id=diagram_id,
            user_input=user_input,
            mermaid_code=mermaid_code,
            drawio_xml=drawio_xml,
            svg_content=svg_content,
            review=review_data,
            export_formats=["mermaid", "svg"],
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    async def _generate_flowchart(
        self, user_input: str, output_dir: Path
    ) -> tuple[str, str | None, str | None, dict[str, Any] | None]:
        """Legacy flowchart path — delegates to the process_documentation skill."""
        try:
            from skills.process_documentation.workflow import (
                classify_intent,
                elaborate,
                export_all,
                extract,
                generate_diagram,
                review,
            )
        except ImportError as e:
            logger.error("skill_import_failed", error=str(e))
            raise RuntimeError(f"process_documentation skill not available: {e}") from e

        input_data = {"user_input": user_input, "output_dir": str(output_dir)}
        data = await classify_intent(input_data)
        data = await elaborate(data)
        data = await extract(data)
        data = await review(data)
        data = await generate_diagram(data)
        data = await export_all(data)

        mermaid_code = data.get("mermaid_code", "")
        if not mermaid_code:
            mmd_file = output_dir / "diagram.mmd"
            if mmd_file.exists():
                mermaid_code = mmd_file.read_text(encoding="utf-8")

        svg_content: str | None = None
        svg_file = output_dir / "diagram.svg"
        if svg_file.exists():
            svg_content = svg_file.read_text(encoding="utf-8")

        drawio_xml: str | None = None
        drawio_file = output_dir / "diagram.drawio"
        if drawio_file.exists():
            drawio_xml = drawio_file.read_text(encoding="utf-8")

        return mermaid_code, svg_content, drawio_xml, data.get("review")

    async def _generate_with_prompts(
        self, user_input: str, diagram_type: str
    ) -> tuple[str, str | None, str | None, dict[str, Any]]:
        """Sequence / swimlane path — uses the 3 dedicated service prompts."""
        models = self._get_models()
        prompts = self._get_prompt_manager()

        # --- Step 1: planner → structured plan JSON ---
        planner_def = prompts.get("diagram-generator/planner")
        planner_messages = planner_def.compile(
            variables={"user_input": user_input, "requested_type": diagram_type},
        )
        planner_result = await models.generate(
            messages=planner_messages,
            model=self.config.planner_model,
            temperature=0.1,
            max_tokens=2048,
        )
        plan_json_raw = (planner_result.output.text or "{}").strip()
        plan = _safe_json_loads(plan_json_raw) or {}

        # Honour planner refusal for non-process inputs.
        if plan.get("diagram_type") == "none":
            reason = str(plan.get("reason") or "not a diagram-worthy description")
            raise ValueError(f"NOT_A_DIAGRAM: {reason}")

        effective_type = plan.get("diagram_type") or diagram_type
        if effective_type not in SUPPORTED_DIAGRAM_TYPES:
            effective_type = diagram_type

        # --- Step 2: mermaid generator → raw Mermaid code ---
        mermaid_def = prompts.get("diagram-generator/mermaid")
        mermaid_messages = mermaid_def.compile(
            variables={"diagram_type": effective_type, "plan_json": plan_json_raw},
        )
        mermaid_result = await models.generate(
            messages=mermaid_messages,
            model=self.config.mermaid_model,
            temperature=0.1,
            max_tokens=2048,
        )
        mermaid_code = _strip_mermaid_fences((mermaid_result.output.text or "").strip())

        # --- Step 3: reviewer → validate + optional auto-fix ---
        reviewer_def = prompts.get("diagram-generator/reviewer")
        reviewer_messages = reviewer_def.compile(
            variables={"diagram_type": effective_type, "mermaid_code": mermaid_code},
        )
        reviewer_result = await models.generate(
            messages=reviewer_messages,
            model=self.config.reviewer_model,
            temperature=0.0,
            max_tokens=2048,
        )
        review_raw = (reviewer_result.output.text or "{}").strip()
        review_data = _safe_json_loads(review_raw) or {
            "valid": False,
            "errors": ["reviewer output could not be parsed"],
            "suggestions": [],
            "fixed_code": None,
        }
        fixed = review_data.get("fixed_code")
        if fixed and isinstance(fixed, str) and fixed.strip():
            mermaid_code = _strip_mermaid_fences(fixed.strip())

        # --- Step 4: render SVG via Kroki (best-effort) ---
        svg_content: str | None = None
        try:
            from skills.process_documentation.tools.kroki_renderer import KrokiRenderer

            renderer = KrokiRenderer()
            if await renderer.is_available():
                raw_svg = await renderer.render(mermaid_code, "svg")
                # Kroki returns bytes; decode to str for DB persistence.
                if isinstance(raw_svg, bytes):
                    svg_content = raw_svg.decode("utf-8", errors="replace")
                else:
                    svg_content = raw_svg
            await renderer.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("diagram_kroki_render_failed", error=str(exc))

        review_data.setdefault("plan", plan)
        review_data.setdefault("effective_type", effective_type)

        return mermaid_code, svg_content, None, review_data

    async def list_diagrams(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[DiagramRecord], int]:
        """List persisted diagrams with pagination."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM generated_diagrams")
            rows = await conn.fetch(
                "SELECT * FROM generated_diagrams ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit,
                offset,
            )
        diagrams = [_row_to_record(r) for r in rows]
        return diagrams, total

    async def get_diagram(self, diagram_id: str) -> DiagramRecord | None:
        """Get a single diagram by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM generated_diagrams WHERE id = $1", diagram_id)
        return _row_to_record(row) if row else None

    async def delete_diagram(self, diagram_id: str) -> bool:
        """Delete a diagram by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM generated_diagrams WHERE id = $1", diagram_id)
        deleted = result == "DELETE 1"
        if deleted:
            logger.info("diagram_deleted", diagram_id=diagram_id)
        return deleted

    async def export_diagram(self, diagram_id: str, fmt: str = "svg") -> str | None:
        """Export a diagram in the requested format."""
        record = await self.get_diagram(diagram_id)
        if not record:
            return None
        if fmt == "mermaid":
            return record.mermaid_code
        if fmt == "svg":
            if record.svg_content:
                return record.svg_content
            # Fallback: try Kroki render on-demand
            try:
                from skills.process_documentation.tools.kroki_renderer import KrokiRenderer

                renderer = KrokiRenderer()
                if await renderer.is_available():
                    svg = await renderer.render(record.mermaid_code, "svg")
                    await renderer.close()
                    return svg
                await renderer.close()
            except Exception:
                pass
            # Last resort: wrap mermaid code in a basic SVG text
            return None
        if fmt == "drawio" and record.drawio_xml:
            return record.drawio_xml
        if fmt == "bpmn" and record.bpmn_xml:
            return record.bpmn_xml
        return None


def _to_json(data: Any) -> str | None:
    """Convert Python object to JSON string for asyncpg."""
    if data is None:
        return None

    return json.dumps(data)


def _safe_json_loads(raw: str) -> dict[str, Any] | None:
    """Tolerant JSON parser — strips accidental code fences before parsing."""
    if not raw:
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # remove leading ```json / ``` and trailing ```
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _strip_mermaid_fences(code: str) -> str:
    """Strip accidental ```mermaid / ``` fences from LLM output."""
    cleaned = code.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _row_to_record(row) -> DiagramRecord:
    """Convert a DB row to a DiagramRecord."""

    return DiagramRecord(
        id=row["id"],
        user_input=row["user_input"],
        mermaid_code=row["mermaid_code"],
        drawio_xml=row.get("drawio_xml"),
        bpmn_xml=row.get("bpmn_xml"),
        svg_content=row.get("svg_content"),
        review=json.loads(row["review"]) if row.get("review") else None,
        export_formats=json.loads(row["export_formats"]) if row.get("export_formats") else [],
        created_by=row.get("created_by"),
        created_at=row["created_at"].isoformat() if row.get("created_at") else "",
        updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
    )
