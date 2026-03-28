"""Draw.io export - ProcessExtraction to .drawio files.

Uses the DrawioBuilder (architecture) and BPMNDiagram (swimlane BPMN)
ported from the Lesotho DHA project. Supports two export modes:

1. Architecture flowchart (default) - top-down BFS layout with shaped nodes
2. BPMN swimlane - actors become lanes, steps become typed BPMN elements
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

import structlog

from skills.process_documentation.drawio.builder import DrawioBuilder
from skills.process_documentation.drawio.bpmn import BPMNDiagram
from skills.process_documentation.drawio.colors import COLORS, LANE_COLORS
from skills.process_documentation.models import (
    ProcessExtraction,
    ProcessStep,
    StepType,
)

__all__ = ["DrawioExporter"]

logger = structlog.get_logger(__name__)

# Map StepType to DrawioBuilder shape method + color
_STEP_MAP = {
    StepType.start_event: ("box", "green", ["shape=mxgraph.flowchart.start_2"]),
    StepType.end_event: ("box", "red", ["shape=mxgraph.flowchart.start_2"]),
    StepType.user_task: ("box", "blue", []),
    StepType.service_task: ("box", "purple", []),
    StepType.exclusive_gateway: ("diamond", "yellow", []),
    StepType.parallel_gateway: ("diamond", "yellow", []),
    StepType.inclusive_gateway: ("diamond", "yellow", []),
    StepType.subprocess: ("box", "gray", []),
}

# Map StepType to BPMN element type
_BPMN_STEP_MAP = {
    StepType.start_event: "start",
    StepType.end_event: "end",
    StepType.user_task: "user_task",
    StepType.service_task: "service_task",
    StepType.exclusive_gateway: "xor",
    StepType.parallel_gateway: "parallel_gw",
    StepType.inclusive_gateway: "inclusive_gw",
    StepType.subprocess: "service_task",
}

# Map actor role to BPMN lane color
_LANE_COLOR_MAP = {
    "citizen": "citizen",
    "officer": "officer",
    "system": "system",
    "external": "external",
    "database": "database",
}

NODE_W = 140
NODE_H = 60
H_GAP = 60
V_GAP = 90


class DrawioExporter:
    """Export ProcessExtraction to Draw.io .drawio files."""

    def export(
        self,
        process: ProcessExtraction,
        output_path: Path | None = None,
    ) -> str:
        """Export as architecture-style flowchart using DrawioBuilder.

        Returns XML string. Saves to output_path if given.
        """
        positions = self._bfs_layout(process)

        max_x = max((x for x, _ in positions.values()), default=800) + NODE_W + 100
        max_y = max((y for _, y in positions.values()), default=600) + NODE_H + 100

        d = DrawioBuilder(process.title, max(max_x, 800), max(max_y, 600))
        d.title(f"<b>{process.title}</b>", 20, 10, max_x - 40, 35)

        step_index = {s.id: s for s in process.steps}
        cell_ids: dict[str, str] = {}

        # Create nodes
        for step in process.steps:
            x, y = positions.get(step.id, (0, 0))
            shape_type, color, extra = _STEP_MAP.get(
                step.step_type, ("box", "gray", [])
            )

            if shape_type == "diamond":
                cid = d.diamond(step.name, x, y + 50, NODE_W, NODE_H, COLORS[color])
            else:
                cid = d.box(step.name, x, y + 50, NODE_W, NODE_H, COLORS[color], extra)

            cell_ids[step.id] = cid

        # Create edges
        for step in process.steps:
            src = cell_ids.get(step.id)
            if not src:
                continue

            if step.decision and step.step_type in (
                StepType.exclusive_gateway,
                StepType.inclusive_gateway,
            ):
                tgt_yes = cell_ids.get(step.decision.yes_target)
                tgt_no = cell_ids.get(step.decision.no_target)
                if tgt_yes:
                    d.connect(src, tgt_yes, step.decision.yes_label)
                if tgt_no:
                    d.connect_lr(src, tgt_no, step.decision.no_label, dashed=True)
            else:
                for next_id in step.next_steps:
                    tgt = cell_ids.get(next_id)
                    if tgt:
                        d.connect(src, tgt)

        xml_str = d.save(str(output_path)) if output_path else d._generate_xml()
        logger.info("drawio_export_ok", title=process.title, mode="architecture")
        return xml_str

    def export_bpmn(
        self,
        process: ProcessExtraction,
        output_path: Path | None = None,
    ) -> str:
        """Export as BPMN swimlane diagram. Actors become lanes.

        Returns XML string. Saves to output_path if given.
        """
        # Build lane definitions from actors
        lane_defs = []
        actor_lane_map: dict[str, int] = {}
        lane_colors = list(LANE_COLORS.keys())

        for i, actor in enumerate(process.actors):
            color = lane_colors[i % len(lane_colors)]
            lane_defs.append((actor.name, color))
            actor_lane_map[actor.id] = i

        if not lane_defs:
            lane_defs = [("Process", "system")]

        # Calculate page width from step count
        page_w = max(1200, len(process.steps) * 200 + 200)

        bpmn = BPMNDiagram(
            process.title,
            process.description or "",
            page_w,
            lane_defs,
        )

        step_index = {s.id: s for s in process.steps}
        cell_ids: dict[str, str] = {}

        # Position steps by order (x = index * spacing)
        sorted_steps = self._topo_sort(process)
        x_positions: dict[str, int] = {}
        for i, step_id in enumerate(sorted_steps):
            x_positions[step_id] = i * 180

        # Create BPMN elements
        for step_id in sorted_steps:
            step = step_index.get(step_id)
            if not step:
                continue

            lane_idx = actor_lane_map.get(step.actor or "", 0)
            x = x_positions.get(step.id, 0)
            bpmn_type = _BPMN_STEP_MAP.get(step.step_type, "user_task")

            if bpmn_type == "start":
                cid = bpmn.start(lane_idx, x)
            elif bpmn_type == "end":
                cid = bpmn.end(lane_idx, x)
            elif bpmn_type == "xor":
                cid = bpmn.xor(lane_idx, x)
            elif bpmn_type == "parallel_gw":
                cid = bpmn.parallel_gw(lane_idx, x)
            elif bpmn_type == "inclusive_gw":
                cid = bpmn.inclusive_gw(lane_idx, x)
            elif bpmn_type == "service_task":
                cid = bpmn.service_task(lane_idx, x, f"<b>{step.name}</b>")
            else:
                cid = bpmn.user_task(lane_idx, x, f"<b>{step.name}</b>")

            cell_ids[step.id] = cid

        # Create flows
        for step in process.steps:
            src = cell_ids.get(step.id)
            if not src:
                continue

            if step.decision and step.step_type in (
                StepType.exclusive_gateway,
                StepType.inclusive_gateway,
            ):
                tgt_yes = cell_ids.get(step.decision.yes_target)
                tgt_no = cell_ids.get(step.decision.no_target)
                if tgt_yes:
                    bpmn.flow(src, tgt_yes, step.decision.yes_label)
                if tgt_no:
                    bpmn.flow(src, tgt_no, step.decision.no_label)
            else:
                for next_id in step.next_steps:
                    tgt = cell_ids.get(next_id)
                    if tgt:
                        bpmn.flow(src, tgt)

        if output_path:
            bpmn.save(str(output_path))

        logger.info("drawio_export_ok", title=process.title, mode="bpmn",
                     lanes=len(lane_defs), steps=len(process.steps))
        return ""

    # ── Layout helpers ──

    def _bfs_layout(self, process: ProcessExtraction) -> dict[str, tuple[int, int]]:
        """BFS layout: returns {step_id: (x, y)}."""
        step_index = {s.id: s for s in process.steps}
        start_id = process.start_step_id
        if start_id not in step_index and process.steps:
            start_id = process.steps[0].id
        if not start_id:
            return {}

        positions: dict[str, tuple[int, int]] = {}
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        visited.add(start_id)
        level_counts: dict[int, int] = {}

        while queue:
            step_id, level = queue.popleft()
            col = level_counts.get(level, 0)
            level_counts[level] = col + 1
            positions[step_id] = (col * (NODE_W + H_GAP), level * (NODE_H + V_GAP))

            step = step_index.get(step_id)
            if not step:
                continue

            children = []
            if step.decision and step.step_type in (
                StepType.exclusive_gateway, StepType.inclusive_gateway,
            ):
                children.append(step.decision.yes_target)
                children.append(step.decision.no_target)
            else:
                children.extend(step.next_steps)

            for cid in children:
                if cid not in visited and cid in step_index:
                    visited.add(cid)
                    queue.append((cid, level + 1))

        return positions

    def _topo_sort(self, process: ProcessExtraction) -> list[str]:
        """Simple topological sort for BPMN element ordering."""
        step_index = {s.id: s for s in process.steps}
        visited: set[str] = set()
        order: list[str] = []
        queue: deque[str] = deque()

        start_id = process.start_step_id
        if start_id not in step_index and process.steps:
            start_id = process.steps[0].id

        queue.append(start_id)
        visited.add(start_id)

        while queue:
            sid = queue.popleft()
            order.append(sid)
            step = step_index.get(sid)
            if not step:
                continue

            children = []
            if step.decision:
                children.extend([step.decision.yes_target, step.decision.no_target])
            else:
                children.extend(step.next_steps)

            for cid in children:
                if cid not in visited and cid in step_index:
                    visited.add(cid)
                    queue.append(cid)

        return order
