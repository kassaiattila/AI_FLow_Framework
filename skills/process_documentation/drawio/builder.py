"""DrawIO XML builder for architecture diagrams.

Ported from the Lesotho DHA Inception Report project (create_drawio_diagrams.py).
Builds .drawio XML files with proper styling, shapes, and connectors.

Three shape systems:
1. Built-in shapes: box, diamond, cylinder, hexagon, cloud, group
2. Native mxgraph references: native() - shape=mxgraph.ns.name (small XML, sidebar-identical)
3. Stencil embedding: stencil() - shape=stencil(b64) (fallback for unsupported namespaces)
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

__all__ = ["DrawioBuilder"]


class DrawioBuilder:
    """Builds a .drawio XML file with proper styling.

    Usage::

        from skills.process_documentation.drawio import DrawioBuilder, COLORS

        d = DrawioBuilder("My Diagram", 1100, 850)
        box1 = d.box("Service A", 100, 100, 180, 60, COLORS["blue"])
        box2 = d.box("Service B", 400, 100, 180, 60, COLORS["green"])
        d.connect(box1, box2, "API call")
        d.save("my_diagram.drawio")
    """

    def __init__(self, page_name: str = "Page", page_w: int = 1100, page_h: int = 850) -> None:
        self._id_counter: int = 2
        self.cells: list[dict[str, Any]] = []
        self.page_name: str = page_name
        self.page_w: int = page_w
        self.page_h: int = page_h

    def _next_id(self) -> str:
        self._id_counter += 1
        return str(self._id_counter)

    def _style_str(self, colors: dict[str, str], extra: str | list[str] | None = None) -> str:
        """Build a CSS-like style string from a color dict and optional extras."""
        parts = [
            f"fillColor={colors['fill']}",
            f"strokeColor={colors['stroke']}",
            f"fontColor={colors['font']}",
            "rounded=1", "whiteSpace=wrap", "html=1",
            "fontSize=11", "fontFamily=Helvetica",
        ]
        if extra:
            if isinstance(extra, list):
                parts.extend(extra)
            else:
                parts.append(extra)
        return ";".join(parts) + ";"

    # ── Basic shapes ──

    def box(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        colors: dict[str, str],
        extra: str | list[str] | None = None,
        parent: str = "1",
    ) -> str:
        """Add a rounded rectangle vertex. Returns the cell ID."""
        cid = self._next_id()
        self.cells.append({
            "type": "vertex", "id": cid, "parent": parent,
            "value": label,
            "style": self._style_str(colors, extra),
            "x": x, "y": y, "w": w, "h": h,
        })
        return cid

    def group(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        colors: dict[str, str],
        extra: str | list[str] | None = None,
    ) -> str:
        """Add a dashed container group. Returns the cell ID."""
        extras: list[str] = [
            "fontSize=13", "fontStyle=1", "verticalAlign=top",
            "dashed=1", "dashPattern=8 4", "opacity=50", "strokeWidth=2",
        ]
        if extra:
            extras.extend(extra if isinstance(extra, list) else [extra])
        return self.box(label, x, y, w, h, colors, extras)

    def header(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        colors: dict[str, str],
    ) -> str:
        """Add a bold header box with shadow. Returns the cell ID."""
        return self.box(label, x, y, w, h, colors, ["fontStyle=1", "shadow=1"])

    def title(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float = 700,
        h: int | float = 40,
    ) -> str:
        """Add a centered title text element. Returns the cell ID."""
        cid = self._next_id()
        self.cells.append({
            "type": "vertex", "id": cid, "parent": "1",
            "value": label,
            "style": "text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;"
                     "fontSize=16;fontFamily=Helvetica;fontStyle=1;fillColor=none;"
                     "strokeColor=none;fontColor=#333333;",
            "x": x, "y": y, "w": w, "h": h,
        })
        return cid

    def subtitle(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float = 700,
        h: int | float = 25,
    ) -> str:
        """Add a centered subtitle text element. Returns the cell ID."""
        cid = self._next_id()
        self.cells.append({
            "type": "vertex", "id": cid, "parent": "1",
            "value": label,
            "style": "text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;"
                     "fontSize=11;fontFamily=Helvetica;fontStyle=2;fillColor=none;"
                     "strokeColor=none;fontColor=#666666;",
            "x": x, "y": y, "w": w, "h": h,
        })
        return cid

    # ── Geometric shapes ──

    def diamond(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        colors: dict[str, str],
    ) -> str:
        """Add a rhombus (decision diamond). Returns the cell ID."""
        return self.box(label, x, y, w, h, colors,
                        ["shape=rhombus", "perimeter=rhombusPerimeter"])

    def hexagon(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        colors: dict[str, str],
    ) -> str:
        """Add a hexagon shape. Returns the cell ID."""
        return self.box(label, x, y, w, h, colors,
                        ["shape=hexagon", "perimeter=hexagonPerimeter2", "size=0.25"])

    def cylinder(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        colors: dict[str, str],
    ) -> str:
        """Add a database cylinder shape. Returns the cell ID."""
        return self.box(label, x, y, w, h, colors, ["shape=cylinder3", "size=10"])

    def cloud(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        colors: dict[str, str],
    ) -> str:
        """Add a cloud shape. Returns the cell ID."""
        return self.box(label, x, y, w, h, colors, ["shape=cloud"])

    # ── Advanced shapes ──

    def native(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        shape_ref: str,
        colors: dict[str, str] | None = None,
        extra: str | list[str] | None = None,
    ) -> str:
        """Use a native draw.io shape reference (shape=mxgraph.ns.name).

        Produces smaller XML than stencil(b64) and renders identically to
        shapes dragged from draw.io Desktop's sidebar menu.

        Args:
            label: Display label for the shape.
            x: X position.
            y: Y position.
            w: Width.
            h: Height.
            shape_ref: Native reference string, e.g. ``"mxgraph.networks.server"``,
                ``"mxgraph.aws4.ec2"``, ``"mxgraph.azure.virtual_machine"``.
            colors: Optional color dict from COLORS palette.
            extra: Optional extra style parameters.

        Confirmed working namespaces (tested with CLI export)::

            mxgraph.networks.*     - ALL shapes (server, switch, router, firewall, cloud, ...)
            mxgraph.aws4.*         - Most shapes (ec2, s3, lambda, rds, vpc, sqs, sns, ...)
            mxgraph.office.*       - ALL sub-namespaces (servers, users, clouds, security, ...)
            mxgraph.gcp2.*         - Most shapes (compute_engine, cloud_storage, cloud_sql, ...)
            mxgraph.cisco.*        - Most shapes (routers.router, switches.*, security.*, ...)
            mxgraph.cisco_safe.*   - ALL sub-namespaces (architecture, capability, design, ...)
            mxgraph.cisco19.*      - Most shapes (router, firewall, server, cloud, laptop, ...)
            mxgraph.azure.*        - Partial (virtual_machine, sql_database, storage, cloud, ...)
            mxgraph.basic.*        - Most shapes (star, heart, cube, cone2, banner, ...)
            mxgraph.rack.*         - Rack equipment strips
            mxgraph.bpmn.*         - Use BPMNDiagram class instead

        NOT working (use stencil() instead)::

            mxgraph.flowchart.*    - Use built-in shapes (rhombus, cylinder3, document, ...)
            mxgraph.ibm_cloud.*    - Use stencil(b64)
            mxgraph.atlassian.*    - Use stencil(b64)

        Returns:
            The cell ID string.
        """
        parts = [
            f"shape={shape_ref}",
            "outlineConnect=0", "aspect=fixed",
            "verticalLabelPosition=bottom", "verticalAlign=top",
            "align=center", "html=1",
            "fontSize=11", "fontFamily=Helvetica",
        ]
        if colors:
            parts.extend([
                f"fillColor={colors['fill']}",
                f"strokeColor={colors['stroke']}",
                f"fontColor={colors['font']}",
            ])
        if extra:
            parts.extend(extra if isinstance(extra, list) else [extra])
        cid = self._next_id()
        self.cells.append({
            "type": "vertex", "id": cid, "parent": "1",
            "value": label,
            "style": ";".join(parts) + ";",
            "x": x, "y": y, "w": w, "h": h,
        })
        return cid

    def stencil(
        self,
        label: str,
        x: int | float,
        y: int | float,
        w: int | float,
        h: int | float,
        shape_info: dict[str, Any] | str,
        colors: dict[str, str] | None = None,
        extra: str | list[str] | None = None,
    ) -> str:
        """Use a draw.io stencil shape (from stencil_catalog).

        Args:
            label: Display label for the shape.
            x: X position.
            y: Y position.
            w: Width.
            h: Height.
            shape_info: Either a catalog dict ``{"w": .., "h": .., "b64": "..."}``
                from the stencil catalog, or a raw b64 string.
            colors: Optional color dict from COLORS palette (fill/stroke for the icon).
            extra: Optional extra style parameters.

        Returns:
            The cell ID string.
        """
        if isinstance(shape_info, dict):
            b64 = shape_info["b64"]
        else:
            b64 = shape_info
        parts = [
            f"shape=stencil({b64})",
            "verticalLabelPosition=bottom", "verticalAlign=top",
            "align=center", "html=1",
            "fontSize=11", "fontFamily=Helvetica",
        ]
        if colors:
            parts.extend([
                f"fillColor={colors['fill']}",
                f"strokeColor={colors['stroke']}",
                f"fontColor={colors['font']}",
            ])
        if extra:
            parts.extend(extra if isinstance(extra, list) else [extra])
        cid = self._next_id()
        self.cells.append({
            "type": "vertex", "id": cid, "parent": "1",
            "value": label,
            "style": ";".join(parts) + ";",
            "x": x, "y": y, "w": w, "h": h,
        })
        return cid

    # ── Connectors ──

    def connect(
        self,
        src: str,
        tgt: str,
        label: str = "",
        color: str = "#666666",
        dashed: bool = False,
        exit_xy: tuple[float, float] | None = None,
        entry_xy: tuple[float, float] | None = None,
        waypoints: list[tuple[int | float, int | float]] | None = None,
    ) -> str:
        """Connect two cells with a top-bottom orthogonal edge.

        Args:
            src: Source cell ID.
            tgt: Target cell ID.
            label: Edge label text.
            color: Stroke color (hex).
            dashed: Whether to render as dashed line.
            exit_xy: Exit point as (x_fraction, y_fraction), e.g. (0.5, 1) for bottom-center.
            entry_xy: Entry point as (x_fraction, y_fraction).
            waypoints: List of (x, y) absolute waypoints for routing control.

        Returns:
            The edge cell ID string.
        """
        cid = self._next_id()
        # Use segmentEdgeStyle when waypoints are given for exact control
        edge_style = "edgeStyle=segmentEdgeStyle" if waypoints else "edgeStyle=orthogonalEdgeStyle"
        parts = [
            f"strokeColor={color}",
            "rounded=1", "fontSize=9", "fontFamily=Helvetica",
            "fontColor=#666666", "html=1",
            edge_style,
        ]
        if exit_xy:
            parts.append(f"exitX={exit_xy[0]};exitY={exit_xy[1]};exitDx=0;exitDy=0")
        elif not waypoints:
            parts.append("exitX=0.5;exitY=1;exitDx=0;exitDy=0")
        if entry_xy:
            parts.append(f"entryX={entry_xy[0]};entryY={entry_xy[1]};entryDx=0;entryDy=0")
        if dashed:
            parts.append("dashed=1")
        cell: dict[str, Any] = {
            "type": "edge", "id": cid, "parent": "1",
            "source": src, "target": tgt,
            "value": label,
            "style": ";".join(parts) + ";",
        }
        if waypoints:
            cell["waypoints"] = waypoints
        self.cells.append(cell)
        return cid

    def connect_lr(
        self,
        src: str,
        tgt: str,
        label: str = "",
        color: str = "#666666",
        dashed: bool = False,
        exit_xy: tuple[float, float] | None = None,
        entry_xy: tuple[float, float] | None = None,
        waypoints: list[tuple[int | float, int | float]] | None = None,
    ) -> str:
        """Connect two cells with a left-right orthogonal edge.

        Same as :meth:`connect` but without default exit point, producing
        a natural left-to-right flow.

        Returns:
            The edge cell ID string.
        """
        cid = self._next_id()
        parts = [
            f"strokeColor={color}",
            "rounded=1", "fontSize=9", "fontFamily=Helvetica",
            "fontColor=#666666", "html=1",
            "edgeStyle=orthogonalEdgeStyle",
        ]
        if exit_xy:
            parts.append(f"exitX={exit_xy[0]};exitY={exit_xy[1]};exitDx=0;exitDy=0")
        if entry_xy:
            parts.append(f"entryX={entry_xy[0]};entryY={entry_xy[1]};entryDx=0;entryDy=0")
        if dashed:
            parts.append("dashed=1")
        cell: dict[str, Any] = {
            "type": "edge", "id": cid, "parent": "1",
            "source": src, "target": tgt,
            "value": label,
            "style": ";".join(parts) + ";",
        }
        if waypoints:
            cell["waypoints"] = waypoints
        self.cells.append(cell)
        return cid

    # ── Serialization ──

    def _generate_xml(self) -> str:
        """Generate the .drawio XML string without writing to file."""
        lines: list[str] = self._build_lines()
        return "\n".join(lines)

    def save(self, filepath: str) -> None:
        """Write the .drawio XML file."""
        xml = self._generate_xml()
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xml)

    def _build_lines(self) -> list[str]:
        """Build the complete XML as a list of strings."""
        lines: list[str] = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<mxfile host="AIFlow" modified="2026-01-01" agent="AIFlow" version="21.6.5">')
        lines.append(f'  <diagram name="{html.escape(self.page_name)}" id="page1">')
        lines.append(f'    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" '
                     f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
                     f'page="1" pageScale="1" pageWidth="{self.page_w}" pageHeight="{self.page_h}" '
                     f'math="0" shadow="0">')
        lines.append('      <root>')
        lines.append('        <mxCell id="0"/>')
        lines.append('        <mxCell id="1" parent="0"/>')

        for cell in self.cells:
            if cell["type"] == "vertex":
                val = html.escape(cell["value"])
                sty = html.escape(cell["style"])
                lines.append(f'        <mxCell id="{cell["id"]}" value="{val}" '
                           f'style="{sty}" vertex="1" parent="{cell["parent"]}">')
                lines.append(f'          <mxGeometry x="{cell["x"]}" y="{cell["y"]}" '
                           f'width="{cell["w"]}" height="{cell["h"]}" as="geometry"/>')
                lines.append('        </mxCell>')
            elif cell["type"] == "edge":
                val = html.escape(cell.get("value", ""))
                sty = html.escape(cell["style"])
                src_attr = f' source="{cell["source"]}"' if cell.get("source") else ""
                tgt_attr = f' target="{cell["target"]}"' if cell.get("target") else ""
                lines.append(f'        <mxCell id="{cell["id"]}" value="{val}" '
                           f'style="{sty}" edge="1" parent="1"'
                           f'{src_attr}{tgt_attr}>')
                # Support label offset positioning and waypoints
                lbl_x = cell.get("label_x")
                lbl_y = cell.get("label_y")
                wps = cell.get("waypoints")
                has_inner = (lbl_x is not None or lbl_y is not None) or wps
                if has_inner:
                    lx = lbl_x if lbl_x is not None else 0
                    ly = lbl_y if lbl_y is not None else 0
                    lines.append(f'          <mxGeometry x="{lx}" y="{ly}" relative="1" as="geometry">')
                    if wps:
                        lines.append('            <Array as="points">')
                        for px, py in wps:
                            lines.append(f'              <mxPoint x="{px}" y="{py}"/>')
                        lines.append('            </Array>')
                    lines.append('          </mxGeometry>')
                else:
                    lines.append('          <mxGeometry relative="1" as="geometry"/>')
                lines.append('        </mxCell>')

        lines.append('      </root>')
        lines.append('    </mxGraphModel>')
        lines.append('  </diagram>')
        lines.append('</mxfile>')
        return lines
