"""PromptWorkflowExecutor — resolution-only helper for skill consumers.

Sprint R / S141: provides the minimal surface a skill needs to *opt
into* a workflow without owning the LLM call. The executor:

* checks per-skill opt-in via :class:`PromptWorkflowSettings.skills`;
* resolves the workflow + nested step prompts via
  :meth:`PromptManager.get_workflow`;
* returns a tuple suitable for the skill to consume — or ``None`` if
  the shim is off / the lookup failed (caller falls back to its
  legacy per-prompt path).

**This class never invokes an LLM.** Execution belongs to the skill.
S141 is intentionally scoped to the *contract* — per-skill migrations
land in follow-up sessions where each skill's golden path can be
validated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from aiflow.core.errors import FeatureDisabled
from aiflow.prompts.manager import PromptManager, WorkflowResolutionError
from aiflow.prompts.schema import PromptDefinition
from aiflow.prompts.workflow import PromptWorkflow

if TYPE_CHECKING:
    from aiflow.core.config import PromptWorkflowSettings

__all__ = ["PromptWorkflowExecutor", "ResolvedWorkflow"]

logger = structlog.get_logger(__name__)


ResolvedWorkflow = tuple[PromptWorkflow, dict[str, PromptDefinition]]


class PromptWorkflowExecutor:
    """Skill-side shim around :meth:`PromptManager.get_workflow`.

    Args:
        manager: An already-built :class:`PromptManager`. The caller is
            responsible for registering nested skill prompt YAMLs on
            the manager (the skill itself usually does this in its
            ``__init__``).
        settings: The current :class:`PromptWorkflowSettings`. The
            executor uses ``settings.enabled`` and ``settings.skills``
            for gating.
    """

    def __init__(
        self,
        manager: PromptManager,
        settings: PromptWorkflowSettings,
    ) -> None:
        self._manager = manager
        self._settings = settings

    def is_skill_migrated(self, skill_name: str) -> bool:
        """Return True iff the workflow shim is on for ``skill_name``."""
        if not self._settings.enabled:
            return False
        return skill_name in self._settings.skills

    def resolve_for_skill(
        self,
        skill_name: str,
        workflow_name: str,
        *,
        label: str | None = None,
    ) -> ResolvedWorkflow | None:
        """Resolve a workflow for a skill, or return ``None`` to fall back.

        Returns ``None`` when:
            * the skill is not opted in (``is_skill_migrated`` is False);
            * the workflow lookup raises ``KeyError`` (descriptor missing);
            * the workflow loads but a nested prompt cannot be resolved
              (caller will hit the legacy per-prompt path which has its
              own error reporting).

        Re-raises :class:`FeatureDisabled` only when the flag check is
        consistent (the global flag is on, but the skill is not in the
        opt-in list) — this is the explicit "not yet migrated" signal
        and callers handle it as a non-event.
        """
        if not self.is_skill_migrated(skill_name):
            return None

        try:
            return self._manager.get_workflow(workflow_name, label=label)
        except FeatureDisabled:
            # Defensive: settings + manager state out of sync.
            logger.warning(
                "workflow_executor.flag_mismatch",
                skill=skill_name,
                workflow=workflow_name,
            )
            return None
        except KeyError:
            logger.warning(
                "workflow_executor.descriptor_missing",
                skill=skill_name,
                workflow=workflow_name,
            )
            return None
        except WorkflowResolutionError as exc:
            logger.warning(
                "workflow_executor.nested_prompt_unresolved",
                skill=skill_name,
                workflow=workflow_name,
                step_id=exc.step_id,
                prompt_name=exc.prompt_name,
            )
            return None
