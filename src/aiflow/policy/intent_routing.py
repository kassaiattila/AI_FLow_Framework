"""Intent routing policy — map ClassificationResult.label → downstream action.

Per-tenant configurable policy. Sits alongside :class:`PolicyEngine` so that
multiple skills (email_intent_processor, spec_writer, invoice_processor queues,
etc.) can share the same routing primitive.

YAML convention (loaded by :meth:`IntentRoutingPolicy.from_yaml`):

    tenant_id: "acme"
    default_action: "manual_review"
    rules:
      - intent_label: "invoice_question"
        action: "extract"
        target: "invoice_pipeline"
        min_confidence: 0.6
      - intent_label: "support_request"
        action: "notify_dept"
        target: "helpdesk"
        min_confidence: 0.5
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel, Field

__all__ = [
    "IntentAction",
    "IntentRoutingPolicy",
    "IntentRoutingRule",
]

logger = structlog.get_logger(__name__)


class IntentAction(str, Enum):
    """Downstream actions that can follow a classified intent."""

    EXTRACT = "extract"  # UC1-style document field extraction
    NOTIFY_DEPT = "notify_dept"  # Route to department queue
    ARCHIVE = "archive"  # No further processing
    MANUAL_REVIEW = "manual_review"  # Human-in-the-loop review
    REPLY_AUTO = "reply_auto"  # Auto-reply with template


class IntentRoutingRule(BaseModel):
    """One label → action mapping with a confidence gate."""

    intent_label: str
    action: IntentAction
    target: str = ""
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class IntentRoutingPolicy(BaseModel):
    """Ordered list of routing rules for a single tenant.

    Rule evaluation is first-match-wins: rules are checked in declaration order
    and the first rule whose ``intent_label`` matches and whose ``min_confidence``
    is met decides the action. If no rule matches, ``default_action`` is used.
    """

    tenant_id: str
    default_action: IntentAction = IntentAction.MANUAL_REVIEW
    default_target: str = ""
    rules: list[IntentRoutingRule] = Field(default_factory=list)

    def decide(self, label: str, confidence: float) -> tuple[IntentAction, str]:
        """Return ``(action, target)`` for a ``(label, confidence)`` pair."""
        for rule in self.rules:
            if rule.intent_label == label and confidence >= rule.min_confidence:
                return rule.action, rule.target
        return self.default_action, self.default_target

    @classmethod
    def from_yaml(cls, path: Path | str) -> IntentRoutingPolicy:
        """Load a policy from a YAML file.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValueError: If the YAML content is not a mapping.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Intent routing policy YAML not found: {p}")
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid intent routing policy YAML: {p}")
        policy = cls(**data)
        logger.info(
            "intent_routing_policy.loaded",
            path=str(p),
            tenant_id=policy.tenant_id,
            rule_count=len(policy.rules),
        )
        return policy

    @classmethod
    def load_for_tenant(
        cls,
        tenant_id: str,
        policy_dir: Path | str,
    ) -> IntentRoutingPolicy | None:
        """Load ``{policy_dir}/intent_routing/{tenant_id}.yaml`` if present.

        Returns ``None`` silently when the file does not exist, so callers can
        treat "no policy configured" as "fall through to classification only".
        """
        p = Path(policy_dir) / "intent_routing" / f"{tenant_id}.yaml"
        if not p.exists():
            return None
        return cls.from_yaml(p)
