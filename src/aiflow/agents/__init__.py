"""AIFlow 2-level agent system - Orchestrator + max 6 Specialists.

DEPRECATED: Not used by any working skill. Planned for Phase B review.
"""

from aiflow.agents.messages import AgentRequest, AgentResponse
from aiflow.agents.specialist import AgentSpec, SpecialistAgent
from aiflow.agents.orchestrator import OrchestratorAgent
from aiflow.agents.quality_gate import QualityGate, QualityGateResult
from aiflow.agents.human_loop import HumanLoopManager, HumanReviewRequest, HumanReviewResponse
from aiflow.agents.reflection import ReflectionLoop, ReflectionResult

__all__ = [
    "AgentRequest",
    "AgentResponse",
    "AgentSpec",
    "SpecialistAgent",
    "OrchestratorAgent",
    "QualityGate",
    "QualityGateResult",
    "HumanLoopManager",
    "HumanReviewRequest",
    "HumanReviewResponse",
    "ReflectionLoop",
    "ReflectionResult",
]
