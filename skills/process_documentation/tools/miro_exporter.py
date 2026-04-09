"""Miro board export - ProcessExtraction to Miro shapes and connectors.

Ported from 06_Diagram_Gen_AI_Agent pilot with adaptations for the AIFlow
framework: structlog instead of print, async-first httpx, AIFlow models,
inclusive_gateway support, and frame grouping.
"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field
from skills.process_documentation.models import ProcessExtraction, StepType

__all__ = ["MiroExporter", "MiroResult"]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

class MiroResult(BaseModel):
    """Outcome of a Miro export operation."""

    success: bool = Field(..., description="Whether the export succeeded")
    board_id: str | None = Field(default=None, description="Miro board ID")
    board_url: str | None = Field(default=None, description="Board view URL")
    shapes_created: int = Field(default=0, description="Number of shapes created")
    connectors_created: int = Field(default=0, description="Number of connectors created")
    error: str | None = Field(default=None, description="Error message on failure")


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------

class MiroExporter:
    """Export a ``ProcessExtraction`` to a Miro board via the Miro REST API v2.

    Usage::

        async with MiroExporter(api_token="...") as exporter:
            result = await exporter.export(process)
    """

    BASE_URL = "https://api.miro.com/v2"

    # Layout constants (pixels)
    NODE_WIDTH = 200
    NODE_HEIGHT = 80
    H_SPACING = 100
    V_SPACING = 150
    FRAME_PADDING = 80

    # Step type -> Miro shape + colour mapping
    STEP_STYLES: dict[StepType, dict[str, str]] = {
        StepType.start_event: {
            "shape": "round_rectangle",
            "fill": "#d5e8d4",
            "border": "#82b366",
        },
        StepType.end_event: {
            "shape": "round_rectangle",
            "fill": "#f8cecc",
            "border": "#b85450",
        },
        StepType.user_task: {
            "shape": "rectangle",
            "fill": "#dae8fc",
            "border": "#6c8ebf",
        },
        StepType.service_task: {
            "shape": "rectangle",
            "fill": "#e1d5e7",
            "border": "#9673a6",
        },
        StepType.exclusive_gateway: {
            "shape": "rhombus",
            "fill": "#fff2cc",
            "border": "#d6b656",
        },
        StepType.parallel_gateway: {
            "shape": "rhombus",
            "fill": "#fff2cc",
            "border": "#d6b656",
        },
        StepType.inclusive_gateway: {
            "shape": "rhombus",
            "fill": "#ffe6cc",
            "border": "#d79b00",
        },
        StepType.subprocess: {
            "shape": "rectangle",
            "fill": "#f5f5f5",
            "border": "#666666",
        },
    }

    _DEFAULT_STYLE: dict[str, str] = {
        "shape": "rectangle",
        "fill": "#dae8fc",
        "border": "#6c8ebf",
    }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, api_token: str) -> None:
        self.api_token = api_token
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def __aenter__(self) -> MiroExporter:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def export(
        self,
        process: ProcessExtraction,
        board_name: str | None = None,
        board_id: str | None = None,
    ) -> MiroResult:
        """Export *process* to a Miro board.

        If *board_id* is given the shapes are added to the existing board;
        otherwise a new board is created with *board_name* (falling back to
        ``process.title``).

        Returns a :class:`MiroResult` with the board URL on success.
        """
        if not self.api_token:
            return MiroResult(
                success=False,
                error="Miro API token is not configured",
            )

        try:
            return await self._do_export(process, board_name, board_id)
        except httpx.HTTPError as exc:
            logger.error("miro_export_http_error", error=str(exc))
            return MiroResult(success=False, error=f"HTTP error: {exc}")
        except Exception as exc:
            logger.error("miro_export_error", error=str(exc))
            return MiroResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    async def _do_export(
        self,
        process: ProcessExtraction,
        board_name: str | None,
        board_id: str | None,
    ) -> MiroResult:
        # 1. Create or validate board --------------------------------
        if board_id:
            resp = await self._client.get(f"/boards/{board_id}")
            if resp.status_code != 200:
                return MiroResult(
                    success=False,
                    error=f"Board not found: {board_id} (HTTP {resp.status_code})",
                )
            board_url: str | None = None
        else:
            board_id, board_url = await self._create_board(
                board_name or process.title,
            )
            if board_id is None:
                return MiroResult(
                    success=False,
                    error=board_url or "Failed to create Miro board",
                )

        # 2. BFS layout ----------------------------------------------
        positions = self._calculate_layout(process)

        # 3. Create shapes -------------------------------------------
        {s.id: s for s in process.steps}
        shape_ids: dict[str, str] = {}
        shapes_created = 0

        for step in process.steps:
            x, y = positions.get(step.id, (0.0, 0.0))
            style = self.STEP_STYLES.get(step.step_type, self._DEFAULT_STYLE)

            shape_id = await self._create_shape(
                board_id=board_id,
                text=step.name,
                x=x,
                y=y,
                shape=style["shape"],
                fill=style["fill"],
                border=style["border"],
            )
            if shape_id:
                shape_ids[step.id] = shape_id
                shapes_created += 1

            await asyncio.sleep(0.1)  # rate limit

        # 4. Create connectors ---------------------------------------
        connectors_created = 0

        for step in process.steps:
            start_shape = shape_ids.get(step.id)
            if not start_shape:
                continue

            if step.step_type in (
                StepType.exclusive_gateway,
                StepType.inclusive_gateway,
            ) and step.decision:
                for target_id, label in (
                    (step.decision.yes_target, step.decision.yes_label),
                    (step.decision.no_target, step.decision.no_label),
                ):
                    end_shape = shape_ids.get(target_id)
                    if end_shape:
                        cid = await self._create_connector(
                            board_id, start_shape, end_shape, caption=label,
                        )
                        if cid:
                            connectors_created += 1
                        await asyncio.sleep(0.1)
            else:
                for next_id in step.next_steps:
                    end_shape = shape_ids.get(next_id)
                    if end_shape:
                        cid = await self._create_connector(
                            board_id, start_shape, end_shape,
                        )
                        if cid:
                            connectors_created += 1
                        await asyncio.sleep(0.1)

        # 5. Add surrounding frame -----------------------------------
        if positions:
            await self._create_surrounding_frame(
                board_id, process.title, positions,
            )

        # 6. Resolve final board URL ----------------------------------
        if board_url is None:
            board_url = await self._resolve_board_url(board_id)

        logger.info(
            "miro_export_complete",
            board_id=board_id,
            shapes=shapes_created,
            connectors=connectors_created,
        )

        return MiroResult(
            success=True,
            board_id=board_id,
            board_url=board_url,
            shapes_created=shapes_created,
            connectors_created=connectors_created,
        )

    # ------------------------------------------------------------------
    # Miro API helpers
    # ------------------------------------------------------------------

    async def _create_board(self, name: str) -> tuple[str | None, str | None]:
        """POST /boards -> (board_id, view_link) or (None, error_message)."""
        payload: dict[str, Any] = {
            "name": name,
            "description": "Generated by AIFlow Process Documentation skill",
        }
        resp = await self._client.post("/boards", json=payload)
        if resp.status_code in (200, 201):
            data = resp.json()
            logger.info("miro_board_created", board_id=data["id"], name=name)
            return data["id"], data.get("viewLink")

        msg = f"Failed to create board: HTTP {resp.status_code} - {resp.text}"
        logger.error("miro_create_board_failed", status=resp.status_code)
        return None, msg

    async def _create_shape(
        self,
        board_id: str,
        text: str,
        x: float,
        y: float,
        shape: str,
        fill: str,
        border: str,
    ) -> str | None:
        """POST /boards/{id}/shapes -> shape_id or None."""
        payload: dict[str, Any] = {
            "data": {
                "shape": shape,
                "content": f"<p>{text}</p>",
            },
            "style": {
                "fillColor": fill,
                "borderColor": border,
                "borderWidth": "2",
                "fontFamily": "open_sans",
                "fontSize": "14",
                "textAlign": "center",
                "textAlignVertical": "middle",
            },
            "position": {"x": x, "y": y},
            "geometry": {
                "width": self.NODE_WIDTH,
                "height": self.NODE_HEIGHT,
            },
        }

        resp = await self._client.post(
            f"/boards/{board_id}/shapes", json=payload,
        )
        if resp.status_code in (200, 201):
            return resp.json().get("id")

        logger.warning(
            "miro_create_shape_failed",
            board_id=board_id,
            text=text,
            status=resp.status_code,
            detail=resp.text,
        )
        return None

    async def _create_connector(
        self,
        board_id: str,
        start_id: str,
        end_id: str,
        caption: str | None = None,
    ) -> str | None:
        """POST /boards/{id}/connectors -> connector_id or None."""
        payload: dict[str, Any] = {
            "startItem": {"id": start_id},
            "endItem": {"id": end_id},
            "style": {
                "strokeColor": "#1a1a1a",
                "strokeWidth": "2",
                "endStrokeCap": "arrow",
            },
        }
        if caption:
            payload["captions"] = [{"content": caption}]

        resp = await self._client.post(
            f"/boards/{board_id}/connectors", json=payload,
        )
        if resp.status_code in (200, 201):
            return resp.json().get("id")

        logger.warning(
            "miro_create_connector_failed",
            board_id=board_id,
            start=start_id,
            end=end_id,
            status=resp.status_code,
            detail=resp.text,
        )
        return None

    async def _create_surrounding_frame(
        self,
        board_id: str,
        title: str,
        positions: dict[str, tuple[float, float]],
    ) -> str | None:
        """Create a frame that wraps all placed shapes."""
        if not positions:
            return None

        xs = [p[0] for p in positions.values()]
        ys = [p[1] for p in positions.values()]

        min_x = min(xs) - self.FRAME_PADDING
        min_y = min(ys) - self.FRAME_PADDING
        max_x = max(xs) + self.NODE_WIDTH + self.FRAME_PADDING
        max_y = max(ys) + self.NODE_HEIGHT + self.FRAME_PADDING

        width = max_x - min_x
        height = max_y - min_y
        center_x = min_x + width / 2
        center_y = min_y + height / 2

        payload: dict[str, Any] = {
            "data": {
                "title": title,
                "type": "freeform",
            },
            "position": {"x": center_x, "y": center_y},
            "geometry": {"width": width, "height": height},
        }

        resp = await self._client.post(
            f"/boards/{board_id}/frames", json=payload,
        )
        if resp.status_code in (200, 201):
            return resp.json().get("id")

        logger.warning(
            "miro_create_frame_failed",
            board_id=board_id,
            status=resp.status_code,
        )
        return None

    async def _resolve_board_url(self, board_id: str) -> str:
        """GET /boards/{id} and extract viewLink, fall back to constructed URL."""
        resp = await self._client.get(f"/boards/{board_id}")
        if resp.status_code == 200:
            return resp.json().get(
                "viewLink",
                f"https://miro.com/app/board/{board_id}/",
            )
        return f"https://miro.com/app/board/{board_id}/"

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _calculate_layout(
        self, process: ProcessExtraction,
    ) -> dict[str, tuple[float, float]]:
        """BFS layout starting from ``process.start_step_id``.

        Nodes are arranged top-to-bottom (increasing Y per BFS level).
        Siblings within a level are spread horizontally and centred around
        X = 0 so the diagram stays balanced.

        Returns:
            Mapping of step_id -> (x, y) board coordinates.
        """
        if not process.steps:
            return {}

        step_index = {s.id: s for s in process.steps}

        # Determine start node
        start_id = process.start_step_id
        if start_id not in step_index:
            # Fallback: first step typed start_event, or simply the first step
            for s in process.steps:
                if s.step_type == StepType.start_event:
                    start_id = s.id
                    break
            else:
                start_id = process.steps[0].id

        # BFS
        visited: set[str] = set()
        levels: dict[int, list[str]] = {}
        queue: deque[tuple[str, int]] = deque()
        queue.append((start_id, 0))
        visited.add(start_id)

        while queue:
            node_id, level = queue.popleft()
            levels.setdefault(level, []).append(node_id)

            step = step_index.get(node_id)
            if step is None:
                continue

            # Collect children ------------------------------------------
            children: list[str] = []
            if step.step_type in (
                StepType.exclusive_gateway,
                StepType.inclusive_gateway,
            ) and step.decision:
                for target in (step.decision.yes_target, step.decision.no_target):
                    if target and target not in visited:
                        children.append(target)
            else:
                for nid in step.next_steps:
                    if nid not in visited:
                        children.append(nid)

            for child_id in children:
                visited.add(child_id)
                queue.append((child_id, level + 1))

        # Handle orphan steps (not reachable from start) ----------------
        max_level = max(levels.keys()) if levels else 0
        for step in process.steps:
            if step.id not in visited:
                max_level += 1
                levels.setdefault(max_level, []).append(step.id)

        # Assign (x, y) centred per level ------------------------------
        positions: dict[str, tuple[float, float]] = {}
        cell_w = self.NODE_WIDTH + self.H_SPACING
        cell_h = self.NODE_HEIGHT + self.V_SPACING

        for level, node_ids in levels.items():
            count = len(node_ids)
            total_width = count * cell_w - self.H_SPACING
            start_x = -total_width / 2 + self.NODE_WIDTH / 2

            y = level * cell_h
            for i, nid in enumerate(node_ids):
                x = start_x + i * cell_w
                positions[nid] = (x, y)

        return positions
