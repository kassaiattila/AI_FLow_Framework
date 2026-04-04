"""Diagram Generator service implementation.

Generates BPMN diagrams from natural language using the process_documentation skill,
persists results to generated_diagrams table, and supports export to multiple formats.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["DiagramGeneratorConfig", "DiagramGeneratorService"]

logger = structlog.get_logger(__name__)


class DiagramGeneratorConfig(BaseModel):
    """Configuration for Diagram Generator service."""

    default_export_formats: list[str] = Field(default=["mermaid", "svg"])
    kroki_url: str = Field(default="http://localhost:8000")
    max_input_length: int = Field(default=5000)


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
    """Service for generating and persisting BPMN diagrams."""

    def __init__(self, config: DiagramGeneratorConfig | None = None, db_url: str | None = None):
        self.config = config or DiagramGeneratorConfig()
        self._db_url = db_url
        self._pool = None

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

    async def generate(self, user_input: str, created_by: str | None = None) -> DiagramRecord:
        """Generate a diagram from natural language and persist it."""
        if not user_input.strip():
            raise ValueError("user_input is required")

        output_dir = Path(tempfile.mkdtemp(prefix="aiflow_diagram_"))
        diagram_id = str(uuid.uuid4())

        # Run the process_documentation skill pipeline
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

        svg_content = None
        svg_file = output_dir / "diagram.svg"
        if svg_file.exists():
            svg_content = svg_file.read_text(encoding="utf-8")

        drawio_xml = None
        drawio_file = output_dir / "diagram.drawio"
        if drawio_file.exists():
            drawio_xml = drawio_file.read_text(encoding="utf-8")

        review_data = data.get("review")
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

        logger.info("diagram_generated", diagram_id=diagram_id, mermaid_len=len(mermaid_code))

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
    import json

    return json.dumps(data)


def _row_to_record(row) -> DiagramRecord:
    """Convert a DB row to a DiagramRecord."""
    import json

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
