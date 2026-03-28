"""Color palettes for DrawIO diagrams.

Ported from the Lesotho DHA Inception Report project.
Contains the architecture color palette (COLORS), BPMN lane colors (LANE_COLORS),
BPMN element colors, and sizing constants.
"""
from __future__ import annotations

__all__ = [
    "COLORS",
    "LANE_COLORS",
    "C_USR", "C_SVC", "C_MAN", "C_SND",
    "C_START", "C_END", "C_INTER", "C_GW", "C_NOTE",
    "EV_SZ", "TASK_W", "TASK_H", "GW_SZ", "ICON_SZ",
    "LANE_HDR", "LANE_H", "TITLE_H",
]

# ============================================================
# Architecture Color Palette (14 colors)
# ============================================================
COLORS: dict[str, dict[str, str]] = {
    "green":      {"fill": "#C8E6C9", "stroke": "#2E7D32", "font": "#1B5E20"},
    "blue":       {"fill": "#E3F2FD", "stroke": "#1565C0", "font": "#0D47A1"},
    "red":        {"fill": "#FFCCCC", "stroke": "#CC0000", "font": "#8B0000"},
    "yellow":     {"fill": "#FFF9C4", "stroke": "#F9A825", "font": "#F57F17"},
    "orange":     {"fill": "#FFF3E0", "stroke": "#E65100", "font": "#BF360C"},
    "purple":     {"fill": "#E1BEE7", "stroke": "#7B1FA2", "font": "#4A148C"},
    "gray":       {"fill": "#F5F5F5", "stroke": "#9E9E9E", "font": "#424242"},
    "dark_blue":  {"fill": "#1565C0", "stroke": "#0D47A1", "font": "#FFFFFF"},
    "dark_green": {"fill": "#2E7D32", "stroke": "#1B5E20", "font": "#FFFFFF"},
    "dark_red":   {"fill": "#CC0000", "stroke": "#8B0000", "font": "#FFFFFF"},
    "white":      {"fill": "#FFFFFF", "stroke": "#333333", "font": "#333333"},
    "teal":       {"fill": "#E0F2F1", "stroke": "#00695C", "font": "#004D40"},
    "light_gray": {"fill": "#FAFAFA", "stroke": "#BDBDBD", "font": "#616161"},
    "none":       {"fill": "none",    "stroke": "none",    "font": "#333333"},
}

# ============================================================
# BPMN Lane Colors (5 roles)
# ============================================================
LANE_COLORS: dict[str, dict[str, str]] = {
    "citizen":  {"fill": "#E8F5E9", "stroke": "#2E7D32", "font": "#1B5E20"},
    "officer":  {"fill": "#E3F2FD", "stroke": "#1565C0", "font": "#0D47A1"},
    "system":   {"fill": "#FFF3E0", "stroke": "#E65100", "font": "#BF360C"},
    "external": {"fill": "#F3E5F5", "stroke": "#7B1FA2", "font": "#4A148C"},
    "database": {"fill": "#E0F2F1", "stroke": "#00695C", "font": "#004D40"},
}

# ============================================================
# BPMN Element Colors
# ============================================================
C_USR:   dict[str, str] = {"fill": "#E3F2FD", "stroke": "#1565C0", "font": "#0D47A1"}
C_SVC:   dict[str, str] = {"fill": "#FFF3E0", "stroke": "#E65100", "font": "#BF360C"}
C_MAN:   dict[str, str] = {"fill": "#F5F5F5", "stroke": "#616161", "font": "#424242"}
C_SND:   dict[str, str] = {"fill": "#FCE4EC", "stroke": "#C62828", "font": "#B71C1C"}

C_START: dict[str, str] = {"fill": "#E8F5E9", "stroke": "#2E7D32", "font": "#2E7D32"}
C_END:   dict[str, str] = {"fill": "#FFEBEE", "stroke": "#C62828", "font": "#C62828"}
C_INTER: dict[str, str] = {"fill": "#FFF3E0", "stroke": "#E65100", "font": "#E65100"}
C_GW:    dict[str, str] = {"fill": "#FFF9C4", "stroke": "#F57F17", "font": "#F57F17"}
C_NOTE:  dict[str, str] = {"fill": "#FAFAFA", "stroke": "#9E9E9E", "font": "#424242"}

# ============================================================
# BPMN Sizing Constants
# ============================================================
EV_SZ: int = 36        # Event circle diameter
TASK_W: int = 160      # Default task width
TASK_H: int = 60       # Default task height
GW_SZ: int = 44        # Gateway diamond size
ICON_SZ: int = 14      # Marker icon size
LANE_HDR: int = 55     # Lane header width (left label column)
LANE_H: int = 160      # Lane height (row height per swimlane)
TITLE_H: int = 65      # Title area height at top of diagram
