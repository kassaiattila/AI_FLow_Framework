"""Pipeline compatibility — version detection and auto-upgrade (v1.3 → v1.4).

Source: 100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md Section 3.3
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

import structlog

__all__ = [
    "detect_pipeline_version",
    "upgrade_pipeline_v1_3_to_v1_4",
]

logger = structlog.get_logger(__name__)


def detect_pipeline_version(pipeline_yaml: dict[str, Any]) -> Literal["v1.3", "v1.4"]:
    """Detect pipeline schema version from YAML dict.

    Rules:
    - Explicit ``version`` field starting with ``"2."`` → v1.4
    - Any step with ``adapter == "intake_normalize"`` → v1.4
    - Otherwise → v1.3
    """
    version_field = str(pipeline_yaml.get("version", ""))
    if version_field.startswith("2."):
        return "v1.4"

    steps: list[dict[str, Any]] = pipeline_yaml.get("steps", [])
    if any(step.get("adapter") == "intake_normalize" for step in steps):
        return "v1.4"

    return "v1.3"


def upgrade_pipeline_v1_3_to_v1_4(pipeline_yaml: dict[str, Any]) -> dict[str, Any]:
    """Auto-upgrade a v1.3 pipeline dict to v1.4 schema (in-memory only).

    Transformations:
    - Sets ``version: "2.0"``
    - Wraps ``email_adapter`` step into ``intake_normalize`` with ``source_type: email``
    - Translates ``document_adapter`` + ``method: extract`` → ``method: extract_from_package``
    - Rewrites ``for_each`` to iterate over ``intake.output.package``
    - Passes through all other steps unchanged
    """
    upgraded = deepcopy(pipeline_yaml)
    upgraded["version"] = "2.0"

    old_steps: list[dict[str, Any]] = pipeline_yaml.get("steps", [])
    new_steps: list[dict[str, Any]] = []
    intake_added = False

    for step in old_steps:
        if not intake_added and step.get("adapter") == "email_adapter":
            new_steps.append(
                {
                    "name": "intake",
                    "adapter": "intake_normalize",
                    "config": {
                        "source_type": "email",
                        "source_config": step.get("config", {}),
                    },
                }
            )
            intake_added = True
            continue

        if step.get("adapter") == "document_adapter" and step.get("method") == "extract":
            new_step = deepcopy(step)
            new_step["method"] = "extract_from_package"
            if "for_each" in step:
                new_step["for_each"] = "{{ intake.output.package }}"
            new_steps.append(new_step)
            continue

        new_steps.append(deepcopy(step))

    upgraded["steps"] = new_steps

    logger.info(
        "pipeline_upgraded",
        from_version="v1.3",
        to_version="v1.4",
        steps_before=len(old_steps),
        steps_after=len(new_steps),
    )
    return upgraded
