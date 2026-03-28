"""Template-based Mermaid flowchart generator (no LLM needed).

Deterministically converts a ProcessExtraction to Mermaid flowchart code.
Useful as a fallback or for testing.
"""
from __future__ import annotations

from skills.process_documentation.models import ProcessExtraction, StepType

__all__ = ["generate_flowchart"]

_SHAPE_MAP = {
    StepType.start_event: ("([", "])", ":::startEnd"),
    StepType.end_event: ("([", "])", ":::startEnd"),
    StepType.user_task: ("[", "]", ""),
    StepType.service_task: ("[[", "]]", ""),
    StepType.exclusive_gateway: ("{", "}", ":::decision"),
    StepType.parallel_gateway: ("{", "}", ":::decision"),
    StepType.inclusive_gateway: ("{", "}", ":::decision"),
    StepType.subprocess: ("[", "]", ""),
}


def _sanitize_label(text: str) -> str:
    """Escape characters that break Mermaid syntax."""
    return text.replace('"', "'").replace("(", "").replace(")", "").replace("[", "").replace("]", "")


def generate_flowchart(process: ProcessExtraction) -> str:
    """Generate Mermaid flowchart code from a ProcessExtraction model.

    Args:
        process: Validated ProcessExtraction with steps and connections.

    Returns:
        Mermaid flowchart code string.
    """
    lines = ["flowchart TD"]

    # Node definitions
    for step in process.steps:
        open_br, close_br, _cls = _SHAPE_MAP.get(
            step.step_type, ("[", "]", "")
        )
        label = _sanitize_label(step.name)
        lines.append(f"    {step.id}{open_br}\"{label}\"{close_br}")

    lines.append("")

    # Edges
    for step in process.steps:
        if step.decision and step.step_type == StepType.exclusive_gateway:
            lines.append(f"    {step.id} -->|{step.decision.yes_label}| {step.decision.yes_target}")
            lines.append(f"    {step.id} -->|{step.decision.no_label}| {step.decision.no_target}")
        else:
            for next_id in step.next_steps:
                lines.append(f"    {step.id} --> {next_id}")

    return "\n".join(lines)
