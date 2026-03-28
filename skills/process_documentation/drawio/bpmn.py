"""BPMN 2.0 swimlane diagram generator using DrawioBuilder.

Ported from the Lesotho DHA project. Generates professional BPMN diagrams
with swimlanes, typed tasks, events, gateways, and flows.
"""
from __future__ import annotations

from skills.process_documentation.drawio.builder import DrawioBuilder
from skills.process_documentation.drawio.colors import (
    LANE_COLORS,
    C_USR,
    C_SVC,
    C_MAN,
    C_SND,
    C_START,
    C_END,
    C_INTER,
    C_GW,
    C_NOTE,
    EV_SZ,
    TASK_W,
    TASK_H,
    GW_SZ,
    LANE_HDR,
    LANE_H,
    TITLE_H,
)

__all__ = ["BPMNDiagram"]

# ============================================================
# Native draw.io BPMN shape style templates
# ============================================================

# Connection points for proper edge anchoring
_PTS_EV = (
    "points=[[0.145,0.145,0],[0.5,0,0],[0.855,0.145,0],[1,0.5,0],"
    "[0.855,0.855,0],[0.5,1,0],[0.145,0.855,0],[0,0.5,0]];"
)
_PTS_GW = (
    "points=[[0.25,0.25,0],[0.5,0,0],[0.75,0.25,0],[1,0.5,0],"
    "[0.75,0.75,0],[0.5,1,0],[0.25,0.75,0],[0,0.5,0]];"
)

# Task: shape=mxgraph.bpmn.task;taskMarker={abstract|user|service|send|...}
_TASK_STYLE = (
    "shape=mxgraph.bpmn.task;taskMarker={marker};"
    "html=1;whiteSpace=wrap;fontSize=10;fontFamily=Helvetica;"
    "rounded=1;arcSize=10;shadow=1;"
    "fillColor={fill};strokeColor={stroke};fontColor={font};"
)

# Event: shape=mxgraph.bpmn.event;outline={standard|catching|throwing|end};symbol={...}
_EVENT_STYLE = (
    _PTS_EV
    + "shape=mxgraph.bpmn.event;html=1;fontSize=9;fontFamily=Helvetica;"
    "verticalLabelPosition=bottom;verticalAlign=top;align=center;"
    "perimeter=ellipsePerimeter;outlineConnect=0;aspect=fixed;"
    "outline={outline};symbol={symbol};"
    "fillColor={fill};strokeColor={stroke};fontColor={font};"
)

# Gateway: shape=mxgraph.bpmn.gateway2;gwType={exclusive|inclusive|parallel|...}
_GW_STYLE = (
    _PTS_GW
    + "shape=mxgraph.bpmn.gateway2;html=1;fontSize=9;fontFamily=Helvetica;"
    "verticalLabelPosition=bottom;verticalAlign=top;align=center;"
    "perimeter=rhombusPerimeter;outlineConnect=0;"
    "outline=none;symbol=none;gwType={gwType};"
    "fillColor={fill};strokeColor={stroke};fontColor={font};"
)


# ============================================================
# BPMNDiagram class
# ============================================================
class BPMNDiagram:
    """Builds BPMN 2.0 diagrams using draw.io native BPMN shapes.

    Uses mxgraph.bpmn.task / event / gateway2 -- identical to shapes
    from draw.io Desktop's BPMN sidebar. No stencil catalog needed.
    """

    def __init__(
        self,
        title: str,
        subtitle: str,
        width: int = 1400,
        lane_defs: list[tuple[str, str]] | None = None,
    ) -> None:
        self.width = width
        self.lane_defs = lane_defs or []
        total_h = TITLE_H + len(self.lane_defs) * LANE_H + 30
        self.d = DrawioBuilder(title, width, total_h)
        self.d.title(f"<b>{title}</b>", width // 2 - 350, 8, 700, 30)
        self.d.subtitle(subtitle, width // 2 - 350, 35, 700, 22)

        self.lane_y: dict[str, int] = {}
        y = TITLE_H
        lane_w = width - 20
        for lane_name, color_key in self.lane_defs:
            lc = LANE_COLORS[color_key]
            self.d.box(
                "",
                10,
                y,
                lane_w,
                LANE_H,
                lc,
                ["rounded=0", "opacity=30", "strokeWidth=1"],
            )
            self.d.box(
                f"<b>{lane_name}</b>",
                10,
                y,
                LANE_HDR,
                LANE_H,
                lc,
                [
                    "rounded=0",
                    "fontSize=9",
                    "fontStyle=1",
                    "verticalAlign=middle",
                    "align=center",
                    "whiteSpace=wrap",
                    "opacity=80",
                ],
            )
            self.lane_y[lane_name] = y
            y += LANE_H

    # ── Positioning helpers ──

    def _resolve_lane(self, lane: int | str) -> str:
        """Resolve lane index or name to lane name string."""
        if isinstance(lane, int):
            if lane < len(self.lane_defs):
                return self.lane_defs[lane][0]
            raise IndexError(f"Lane index {lane} out of range (0-{len(self.lane_defs)-1})")
        return lane

    def _lane_cy(self, lane: int | str) -> int:
        """Return the vertical center Y coordinate for a lane."""
        name = self._resolve_lane(lane)
        return self.lane_y[name] + LANE_H // 2

    def _pos(self, lane: int | str, x_offset: int) -> tuple[int, int]:
        """Return (x, cy) for a shape placed at *x_offset* within *lane*."""
        x = LANE_HDR + 15 + x_offset
        cy = self._lane_cy(lane)
        return x, cy

    def _cell(
        self,
        label: str,
        x: int,
        y: int,
        w: int,
        h: int,
        style: str,
    ) -> str:
        """Create a raw mxCell vertex and return its ID."""
        cid = self.d._next_id()
        self.d.cells.append(
            {
                "type": "vertex",
                "id": cid,
                "parent": "1",
                "value": label,
                "style": style,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
        )
        return cid

    # ── Tasks (native mxgraph.bpmn.task) ──

    def _task(
        self,
        lane: str,
        x_off: int,
        label: str,
        marker: str,
        colors: dict[str, str],
        w: int | None = None,
    ) -> str:
        """Create a BPMN task shape and return its cell ID."""
        tw = w or TASK_W
        x, cy = self._pos(lane, x_off)
        ty = cy - TASK_H // 2
        style = _TASK_STYLE.format(
            marker=marker,
            fill=colors["fill"],
            stroke=colors["stroke"],
            font=colors["font"],
        )
        return self._cell(label, x, ty, tw, TASK_H, style)

    def user_task(
        self, lane: str, x_off: int, label: str, w: int | None = None
    ) -> str:
        """User task (person icon)."""
        return self._task(lane, x_off, label, "user", C_USR, w)

    def service_task(
        self, lane: str, x_off: int, label: str, w: int | None = None
    ) -> str:
        """Service / automated task (gear icon)."""
        return self._task(lane, x_off, label, "service", C_SVC, w)

    def manual_task(
        self, lane: str, x_off: int, label: str, w: int | None = None
    ) -> str:
        """Manual task (hand icon)."""
        return self._task(lane, x_off, label, "manual", C_MAN, w)

    def send_task(
        self, lane: str, x_off: int, label: str, w: int | None = None
    ) -> str:
        """Send task (envelope icon)."""
        return self._task(lane, x_off, label, "send", C_SND, w)

    def script_task(
        self, lane: str, x_off: int, label: str, w: int | None = None
    ) -> str:
        """Script task (script icon)."""
        return self._task(lane, x_off, label, "script", C_SVC, w)

    def rule_task(
        self, lane: str, x_off: int, label: str, w: int | None = None
    ) -> str:
        """Business rule task (table icon)."""
        return self._task(lane, x_off, label, "businessRule", C_SVC, w)

    # ── Events (native mxgraph.bpmn.event) ──

    def _event(
        self,
        lane: str,
        x_off: int,
        label: str,
        outline: str,
        symbol: str,
        colors: dict[str, str],
    ) -> str:
        """Create a BPMN event shape and return its cell ID."""
        x, cy = self._pos(lane, x_off)
        style = _EVENT_STYLE.format(
            outline=outline,
            symbol=symbol,
            fill=colors["fill"],
            stroke=colors["stroke"],
            font=colors["font"],
        )
        return self._cell(label, x, cy - EV_SZ // 2, EV_SZ, EV_SZ, style)

    def start(self, lane: str, x_off: int = 0, label: str = "") -> str:
        """Start event (thin green circle)."""
        return self._event(lane, x_off, label, "standard", "general", C_START)

    def end(self, lane: str, x_off: int, label: str = "") -> str:
        """End event (thick red circle with filled dot)."""
        return self._event(lane, x_off, label, "end", "terminate2", C_END)

    def end_error(self, lane: str, x_off: int, label: str = "") -> str:
        """Error end event (thick red circle with lightning bolt)."""
        return self._event(lane, x_off, label, "end", "error", C_END)

    def end_terminate(self, lane: str, x_off: int, label: str = "") -> str:
        """Terminate end event (thick red circle with filled dot)."""
        return self._event(lane, x_off, label, "end", "terminate2", C_END)

    def timer(self, lane: str, x_off: int, label: str = "") -> str:
        """Timer intermediate catching event (clock icon)."""
        return self._event(lane, x_off, label, "catching", "timer", C_INTER)

    def message_catch(self, lane: str, x_off: int, label: str = "") -> str:
        """Message intermediate catching event (white envelope)."""
        return self._event(lane, x_off, label, "catching", "message", C_INTER)

    def message_throw(self, lane: str, x_off: int, label: str = "") -> str:
        """Message intermediate throwing event (black envelope)."""
        return self._event(lane, x_off, label, "throwing", "message", C_INTER)

    # ── Gateways (native mxgraph.bpmn.gateway2) ──

    def _gateway(
        self, lane: str, x_off: int, gwType: str, label: str = ""
    ) -> str:
        """Create a BPMN gateway shape and return its cell ID."""
        x, cy = self._pos(lane, x_off)
        style = _GW_STYLE.format(
            gwType=gwType,
            fill=C_GW["fill"],
            stroke=C_GW["stroke"],
            font=C_GW["font"],
        )
        return self._cell(label, x, cy - GW_SZ // 2, GW_SZ, GW_SZ, style)

    def xor(self, lane: str, x_off: int, label: str = "") -> str:
        """Exclusive (XOR) gateway -- diamond with X."""
        return self._gateway(lane, x_off, "exclusive", label)

    def parallel_gw(self, lane: str, x_off: int, label: str = "") -> str:
        """Parallel (AND) gateway -- diamond with +."""
        return self._gateway(lane, x_off, "parallel", label)

    def inclusive_gw(self, lane: str, x_off: int, label: str = "") -> str:
        """Inclusive (OR) gateway -- diamond with circle."""
        return self._gateway(lane, x_off, "inclusive", label)

    # ── Annotations ──

    def label_at(
        self, x: int, y: int, text: str, color: str = "#666666"
    ) -> str:
        """Place a small text label at absolute (x, y) coordinates."""
        return self._cell(
            f"<span style='font-size:8px;color:{color}'>{text}</span>",
            x,
            y,
            60,
            14,
            "text;html=1;strokeColor=none;fillColor=none;align=center;"
            "verticalAlign=middle;whiteSpace=nowrap;overflow=hidden;"
            "fontFamily=Helvetica;fontSize=8;",
        )

    def annotation(
        self, x: int, y: int, label: str, w: int = 180, h: int = 55
    ) -> str:
        """Place a dashed annotation box at absolute (x, y) coordinates."""
        return self.d.box(
            label,
            x,
            y,
            w,
            h,
            C_NOTE,
            [
                "fontSize=8",
                "rounded=0",
                "align=left",
                "spacingLeft=5",
                "dashed=1",
                "dashPattern=3 3",
            ],
        )

    # ── Flows ──

    def flow(
        self,
        src: str,
        tgt: str,
        label: str = "",
        exit_xy: tuple[float, float] | None = None,
        entry_xy: tuple[float, float] | None = None,
        label_x: float | None = None,
        label_y: float | None = None,
        waypoints: list[tuple[int, int]] | None = None,
    ) -> str:
        """Create a sequence flow (solid arrow) between two cells."""
        cid = self.d._next_id()
        extra = ""
        if exit_xy:
            extra += (
                f"exitX={exit_xy[0]};exitY={exit_xy[1]};"
                f"exitDx=0;exitDy=0;"
            )
        if entry_xy:
            extra += (
                f"entryX={entry_xy[0]};entryY={entry_xy[1]};"
                f"entryDx=0;entryDy=0;"
            )
        cell: dict = {
            "type": "edge",
            "id": cid,
            "parent": "1",
            "source": src,
            "target": tgt,
            "value": label,
            "style": (
                "edgeStyle=orthogonalEdgeStyle;rounded=1;"
                "strokeColor=#333333;strokeWidth=1.5;"
                "fontSize=9;fontFamily=Helvetica;fontColor=#666666;html=1;"
                f"endArrow=blockThin;endFill=1;{extra}"
            ),
        }
        if label_x is not None:
            cell["label_x"] = label_x
        if label_y is not None:
            cell["label_y"] = label_y
        if waypoints:
            cell["waypoints"] = waypoints
        self.d.cells.append(cell)
        return cid

    def msg_flow(
        self,
        src: str,
        tgt: str,
        label: str = "",
        exit_xy: tuple[float, float] | None = None,
        entry_xy: tuple[float, float] | None = None,
        waypoints: list[tuple[int, int]] | None = None,
    ) -> str:
        """Create a message flow (dashed open arrow) between two cells."""
        cid = self.d._next_id()
        extra = ""
        if exit_xy:
            extra += (
                f"exitX={exit_xy[0]};exitY={exit_xy[1]};"
                f"exitDx=0;exitDy=0;"
            )
        if entry_xy:
            extra += (
                f"entryX={entry_xy[0]};entryY={entry_xy[1]};"
                f"entryDx=0;entryDy=0;"
            )
        cell: dict = {
            "type": "edge",
            "id": cid,
            "parent": "1",
            "source": src,
            "target": tgt,
            "value": label,
            "style": (
                "edgeStyle=orthogonalEdgeStyle;rounded=1;"
                "strokeColor=#999999;strokeWidth=1;"
                "fontSize=8;fontFamily=Helvetica;fontColor=#999999;html=1;"
                f"dashed=1;dashPattern=8 4;endArrow=open;endFill=0;{extra}"
            ),
        }
        if waypoints:
            cell["waypoints"] = waypoints
        self.d.cells.append(cell)
        return cid

    # ── Save ──

    def save(self, filename: str) -> str:
        """Write the diagram to *filename* via the underlying DrawioBuilder."""
        self.d.save(filename)
        return filename
