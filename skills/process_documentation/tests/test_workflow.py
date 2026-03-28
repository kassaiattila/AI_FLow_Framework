"""
@test_registry:
    suite: skills-unit
    component: skills.process_documentation
    covers: [skills/process_documentation/workflow.py]
    phase: C
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [skills, process-doc, workflow, steps]
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.generation import GenerationOutput
from aiflow.prompts.schema import PromptConfig, PromptDefinition
from skills.process_documentation.models import (
    Actor,
    ClassifyOutput,
    Decision,
    ProcessExtraction,
    ProcessStep,
    ReviewOutput,
    StepType,
)
from skills.process_documentation.tools.diagram_generator import generate_flowchart
from skills.process_documentation.workflow import (
    classify_intent,
    elaborate,
    extract,
    generate_diagram,
    reject,
    review,
)

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

_MOCK_PROMPT = PromptDefinition(
    name="test",
    system="system",
    user="user",
    config=PromptConfig(model="test-model"),
)


def _make_extraction(
    *,
    title: str = "Test Process",
    bad_next: bool = False,
) -> ProcessExtraction:
    """Build a minimal ProcessExtraction for tests.

    Args:
        title: Process title.
        bad_next: If True, add a next_steps reference to a non-existent step
                  so validate_connections() returns errors.
    """
    steps = [
        ProcessStep(
            id="start",
            name="Start",
            step_type=StepType.start_event,
            next_steps=["task1"],
        ),
        ProcessStep(
            id="task1",
            name="Do Work",
            step_type=StepType.user_task,
            actor="actor1",
            next_steps=["end"] if not bad_next else ["nonexistent"],
        ),
        ProcessStep(
            id="end",
            name="End",
            step_type=StepType.end_event,
            next_steps=[],
        ),
    ]
    actors = [Actor(id="actor1", name="Worker", role="employee")]
    return ProcessExtraction(
        title=title,
        description="Test process description",
        actors=actors,
        steps=steps,
        start_step_id="start",
    )


# ---------------------------------------------------------------------------
# classify_intent tests
# ---------------------------------------------------------------------------


class TestClassifyIntent:
    """Tests for the classify_intent step."""

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_classify_process_input(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """When the LLM classifies input as 'process', output must contain
        category='process' and the original user_input."""
        mock_pm.get.return_value = _MOCK_PROMPT

        structured = ClassifyOutput(
            category="process", confidence=0.95, reasoning="Describes a workflow"
        )
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(
                    text="", structured=structured, model_used="test"
                ),
                model_used="test",
            )
        )

        result = await classify_intent({"user_input": "Employee submits leave request"})

        assert result["category"] == "process"
        assert result["confidence"] == 0.95
        assert result["user_input"] == "Employee submits leave request"
        mock_client.generate.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_classify_offtopic(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """Off-topic input should be classified with category='reject'."""
        mock_pm.get.return_value = _MOCK_PROMPT

        structured = ClassifyOutput(
            category="reject", confidence=0.88, reasoning="Greeting, not a process"
        )
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(
                    text="", structured=structured, model_used="test"
                ),
                model_used="test",
            )
        )

        result = await classify_intent({"user_input": "Szia, jó napot!"})

        assert result["category"] == "reject"
        assert result["confidence"] == 0.88
        assert "Greeting" in result["reasoning"]


# ---------------------------------------------------------------------------
# elaborate tests
# ---------------------------------------------------------------------------


class TestElaborate:
    """Tests for the elaborate step."""

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_elaborate_expands(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """Elaborate should pass through the LLM-generated elaborated text."""
        mock_pm.get.return_value = _MOCK_PROMPT

        long_text = (
            "1. A dolgozó kitölti az igénylőlapot.\n"
            "2. A vezető megvizsgálja az igényt.\n"
            "3. A HR rögzíti a rendszerben.\n"
            "4. A rendszer visszaigazolást küld."
        )
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(text=long_text, model_used="test"),
                model_used="test",
            )
        )

        result = await elaborate({"user_input": "Szabadság igénylés", "context": ""})

        assert result["elaborated_text"] == long_text
        assert result["original_input"] == "Szabadság igénylés"
        mock_client.generate.assert_awaited_once()


# ---------------------------------------------------------------------------
# extract tests
# ---------------------------------------------------------------------------


class TestExtract:
    """Tests for the extract step."""

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_extract_produces_extraction(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """Extract should return a serialized ProcessExtraction dict with no errors."""
        mock_pm.get.return_value = _MOCK_PROMPT

        extraction = _make_extraction(title="Leave Request")
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(
                    text="", structured=extraction, model_used="test"
                ),
                model_used="test",
            )
        )

        result = await extract({
            "elaborated_text": "Detailed leave process description",
            "original_input": "Szabadság igénylés",
        })

        assert result["extraction"]["title"] == "Leave Request"
        assert len(result["extraction"]["steps"]) == 3
        assert result["validation_errors"] == []
        assert result["original_input"] == "Szabadság igénylés"

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_extract_reports_validation_errors(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """When the extraction has a bad next_steps reference, validation_errors
        should be non-empty."""
        mock_pm.get.return_value = _MOCK_PROMPT

        extraction = _make_extraction(bad_next=True)
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(
                    text="", structured=extraction, model_used="test"
                ),
                model_used="test",
            )
        )

        result = await extract({"elaborated_text": "Some description"})

        assert len(result["validation_errors"]) > 0
        assert "nonexistent" in result["validation_errors"][0]


# ---------------------------------------------------------------------------
# review tests
# ---------------------------------------------------------------------------


class TestReview:
    """Tests for the review step."""

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_review_acceptable(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """A high-score review should produce is_acceptable=True."""
        mock_pm.get.return_value = _MOCK_PROMPT

        review_out = ReviewOutput(
            score=8,
            is_acceptable=True,
            completeness_score=8,
            logic_score=9,
            actors_score=7,
            decisions_score=8,
            issues=[],
            suggestions=["Add duration estimates"],
            reasoning="Good overall quality",
        )
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(
                    text="", structured=review_out, model_used="test"
                ),
                model_used="test",
            )
        )

        extraction = _make_extraction()
        result = await review({
            "extraction": extraction.model_dump(mode="json"),
            "original_input": "Leave request process",
        })

        assert result["review"]["score"] == 8
        assert result["review"]["is_acceptable"] is True
        assert result["extraction"]["title"] == "Test Process"

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_review_low_score(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """A low-score review should produce is_acceptable=False."""
        mock_pm.get.return_value = _MOCK_PROMPT

        review_out = ReviewOutput(
            score=4,
            is_acceptable=False,
            completeness_score=3,
            logic_score=5,
            actors_score=4,
            decisions_score=3,
            issues=["Missing actors", "Incomplete flow"],
            suggestions=["Add actor roles", "Define decision outcomes"],
            reasoning="Insufficient detail",
        )
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(
                    text="", structured=review_out, model_used="test"
                ),
                model_used="test",
            )
        )

        extraction = _make_extraction()
        result = await review({
            "extraction": extraction.model_dump(mode="json"),
            "original_input": "Some process",
        })

        assert result["review"]["score"] == 4
        assert result["review"]["is_acceptable"] is False
        assert len(result["review"]["issues"]) == 2


# ---------------------------------------------------------------------------
# generate_diagram tests
# ---------------------------------------------------------------------------


class TestGenerateDiagram:
    """Tests for the generate_diagram step."""

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_generate_diagram(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """Generate diagram should return the mermaid code from the LLM."""
        mock_pm.get.return_value = _MOCK_PROMPT

        mermaid_code = (
            "flowchart TD\n"
            '    start(["Start"])\n'
            '    task1["Do Work"]\n'
            '    end1(["End"])\n'
            "    start --> task1\n"
            "    task1 --> end1"
        )
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(text=mermaid_code, model_used="test"),
                model_used="test",
            )
        )

        extraction = _make_extraction(title="My Process")
        result = await generate_diagram({
            "extraction": extraction.model_dump(mode="json"),
        })

        assert result["mermaid_code"] == mermaid_code
        assert result["title"] == "My Process"
        assert "extraction" in result

    @pytest.mark.asyncio
    @patch("skills.process_documentation.workflow.prompt_manager")
    @patch("skills.process_documentation.workflow.models_client")
    async def test_generate_diagram_strips_fences(
        self, mock_client: MagicMock, mock_pm: MagicMock
    ) -> None:
        """Markdown code fences around mermaid output should be stripped."""
        mock_pm.get.return_value = _MOCK_PROMPT

        raw_code = "flowchart TD\n    A --> B"
        fenced = f"```mermaid\n{raw_code}\n```"
        mock_client.generate = AsyncMock(
            return_value=ModelCallResult(
                output=GenerationOutput(text=fenced, model_used="test"),
                model_used="test",
            )
        )

        extraction = _make_extraction()
        result = await generate_diagram({
            "extraction": extraction.model_dump(mode="json"),
        })

        assert "```" not in result["mermaid_code"]
        assert result["mermaid_code"] == raw_code


# ---------------------------------------------------------------------------
# reject tests
# ---------------------------------------------------------------------------


class TestReject:
    """Tests for the reject step."""

    @pytest.mark.asyncio
    async def test_reject_step(self) -> None:
        """Reject step returns rejection dict without needing LLM calls."""
        result = await reject({
            "reasoning": "Not a process description",
            "category": "reject",
        })

        assert result["rejected"] is True
        assert result["reason"] == "Not a process description"
        assert result["category"] == "reject"

    @pytest.mark.asyncio
    async def test_reject_step_defaults(self) -> None:
        """Reject step uses default values when no reasoning/category provided."""
        result = await reject({})

        assert result["rejected"] is True
        assert "not a business process" in result["reason"].lower()
        assert result["category"] == "reject"


# ---------------------------------------------------------------------------
# diagram_generator tool tests
# ---------------------------------------------------------------------------


class TestDiagramGeneratorTool:
    """Tests for the template-based diagram generator (no LLM)."""

    def test_diagram_generator_tool(self) -> None:
        """generate_flowchart should produce valid Mermaid flowchart code."""
        extraction = _make_extraction(title="Leave Request")
        code = generate_flowchart(extraction)

        assert code.startswith("flowchart TD")
        assert "start" in code
        assert "task1" in code
        assert "end" in code
        assert "Start" in code
        assert "Do Work" in code
        assert "-->" in code

    def test_diagram_generator_with_decision(self) -> None:
        """generate_flowchart should handle exclusive gateways with decisions."""
        steps = [
            ProcessStep(
                id="start",
                name="Start",
                step_type=StepType.start_event,
                next_steps=["gw1"],
            ),
            ProcessStep(
                id="gw1",
                name="Amount check",
                step_type=StepType.exclusive_gateway,
                decision=Decision(
                    condition="amount > 100000",
                    yes_target="approve",
                    no_target="auto",
                    yes_label="Igen",
                    no_label="Nem",
                ),
                next_steps=[],
            ),
            ProcessStep(
                id="approve",
                name="Manager Approval",
                step_type=StepType.user_task,
                next_steps=["end"],
            ),
            ProcessStep(
                id="auto",
                name="Auto Process",
                step_type=StepType.service_task,
                next_steps=["end"],
            ),
            ProcessStep(
                id="end",
                name="End",
                step_type=StepType.end_event,
                next_steps=[],
            ),
        ]
        extraction = ProcessExtraction(
            title="Invoice Processing",
            actors=[Actor(id="mgr", name="Manager")],
            steps=steps,
            start_step_id="start",
        )

        code = generate_flowchart(extraction)

        assert "flowchart TD" in code
        assert "|Igen|" in code
        assert "|Nem|" in code
        assert "approve" in code
        assert "auto" in code
