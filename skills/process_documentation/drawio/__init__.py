"""DrawIO diagram generation - architecture and BPMN diagrams.

Ported from the Lesotho DHA Inception Report project.
Provides DrawioBuilder (architecture) and BPMNDiagram (swimlane BPMN).
"""
from skills.process_documentation.drawio.builder import DrawioBuilder
from skills.process_documentation.drawio.colors import COLORS, LANE_COLORS
from skills.process_documentation.drawio.bpmn import BPMNDiagram

__all__ = ["DrawioBuilder", "BPMNDiagram", "COLORS", "LANE_COLORS"]
