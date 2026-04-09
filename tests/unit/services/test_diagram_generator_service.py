"""
@test_registry:
    suite: service-unit
    component: services.diagram_generator
    covers: [src/aiflow/services/diagram_generator/service.py]
    phase: B5.1
    priority: high
    estimated_duration_ms: 600
    requires_services: []
    tags: [service, diagram-generator, postgresql, kroki, mermaid, b5]
"""

from __future__ import annotations

import json
import sys
import types
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.generation import GenerationOutput
from aiflow.services.diagram_generator.service import (
    SUPPORTED_DIAGRAM_TYPES,
    DiagramGeneratorConfig,
    DiagramGeneratorService,
    DiagramRecord,
)


def _make_diagram_row(diagram_id: str = "diag-001") -> dict:
    now = datetime.now(UTC)
    return {
        "id": diagram_id,
        "user_input": "Login flow diagram",
        "mermaid_code": "graph TD\n  A[Start] --> B[Login]",
        "drawio_xml": None,
        "bpmn_xml": None,
        "svg_content": "<svg>...</svg>",
        "review": json.dumps({"score": 0.9}),
        "export_formats": json.dumps(["mermaid", "svg"]),
        "created_by": "admin",
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture()
def svc(mock_pool) -> DiagramGeneratorService:
    pool, _conn = mock_pool
    service = DiagramGeneratorService(config=DiagramGeneratorConfig())
    service._pool = pool
    return service


async def _mock_step(data):
    return {
        **data,
        "mermaid_code": "graph TD\n  A --> B",
        "review": {"score": 0.9},
    }


@pytest.fixture()
def _mock_skill_workflow():
    """Inject a mock skills.process_documentation.workflow module."""
    mod = types.ModuleType("skills.process_documentation.workflow")
    mod.classify_intent = _mock_step
    mod.elaborate = _mock_step
    mod.extract = _mock_step
    mod.review = _mock_step
    mod.generate_diagram = _mock_step
    mod.export_all = _mock_step

    old = sys.modules.get("skills.process_documentation.workflow")
    sys.modules["skills.process_documentation.workflow"] = mod
    yield mod
    if old is not None:
        sys.modules["skills.process_documentation.workflow"] = old
    else:
        sys.modules.pop("skills.process_documentation.workflow", None)


# ---------------------------------------------------------------------------
# Helpers for the B5.1 prompt-based path (sequence / bpmn_swimlane)
# ---------------------------------------------------------------------------


def _wrap_generation(text: str) -> ModelCallResult:
    """Build a minimal ModelCallResult that mimics a real LLM response."""
    return ModelCallResult(
        output=GenerationOutput(text=text, model_used="mock-gpt"),
        model_used="mock-gpt",
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.0001,
        latency_ms=1.0,
    )


def _install_kroki_stub(svg: str | None = "<svg>rendered</svg>") -> None:
    """Register a fake KrokiRenderer in sys.modules so the service import succeeds."""
    tools_mod = sys.modules.get("skills.process_documentation.tools")
    if tools_mod is None:
        tools_mod = types.ModuleType("skills.process_documentation.tools")
        sys.modules["skills.process_documentation.tools"] = tools_mod

    kroki_mod = types.ModuleType("skills.process_documentation.tools.kroki_renderer")

    class _FakeRenderer:
        async def is_available(self) -> bool:
            return svg is not None

        async def render(self, code: str, fmt: str = "svg") -> str | None:
            return svg

        async def close(self) -> None:
            return None

    kroki_mod.KrokiRenderer = _FakeRenderer
    sys.modules["skills.process_documentation.tools.kroki_renderer"] = kroki_mod


def _build_prompt_path_service(
    mock_pool,
    planner_json: dict,
    mermaid_code: str,
    reviewer_json: dict,
) -> tuple[DiagramGeneratorService, MagicMock]:
    """Wire a DiagramGeneratorService with stubbed ModelClient + PromptManager."""
    pool, conn = mock_pool
    conn.execute = AsyncMock(return_value="INSERT 0 1")

    service = DiagramGeneratorService(config=DiagramGeneratorConfig())
    service._pool = pool

    fake_models = MagicMock()
    fake_models.generate = AsyncMock(
        side_effect=[
            _wrap_generation(json.dumps(planner_json)),
            _wrap_generation(mermaid_code),
            _wrap_generation(json.dumps(reviewer_json)),
        ]
    )
    service._models = fake_models

    # Use the real PromptManager so we cover the YAML loading path as well.
    _install_kroki_stub()
    return service, fake_models


class TestDiagramGeneratorService:
    @pytest.mark.asyncio
    async def test_generate_creates_record(
        self, svc: DiagramGeneratorService, mock_pool, _mock_skill_workflow
    ) -> None:
        """generate() runs pipeline and persists DiagramRecord."""
        _pool, conn = mock_pool
        conn.execute = AsyncMock(return_value="INSERT 0 1")

        record = await svc.generate("Login flow diagram", created_by="admin")

        assert isinstance(record, DiagramRecord)
        assert record.user_input == "Login flow diagram"
        assert "graph TD" in record.mermaid_code

    @pytest.mark.asyncio
    async def test_list_diagrams_pagination(self, svc: DiagramGeneratorService, mock_pool) -> None:
        """list_diagrams returns paginated results with total count."""
        _pool, conn = mock_pool
        conn.fetchval = AsyncMock(return_value=2)
        conn.fetch = AsyncMock(return_value=[_make_diagram_row(), _make_diagram_row("diag-002")])

        diagrams, total = await svc.list_diagrams(limit=10, offset=0)
        assert total == 2
        assert len(diagrams) == 2

    @pytest.mark.asyncio
    async def test_get_diagram_existing(self, svc: DiagramGeneratorService, mock_pool) -> None:
        """get_diagram returns DiagramRecord for existing ID."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=_make_diagram_row())

        record = await svc.get_diagram("diag-001")
        assert record is not None
        assert record.id == "diag-001"
        assert record.mermaid_code.startswith("graph TD")

    @pytest.mark.asyncio
    async def test_export_diagram_svg(self, svc: DiagramGeneratorService, mock_pool) -> None:
        """export_diagram returns SVG content for a stored diagram."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=_make_diagram_row())

        svg = await svc.export_diagram("diag-001", fmt="svg")
        assert svg is not None
        assert "<svg>" in svg

    @pytest.mark.asyncio
    async def test_delete_diagram(self, svc: DiagramGeneratorService, mock_pool) -> None:
        """delete_diagram returns True when row is deleted."""
        _pool, conn = mock_pool
        conn.execute = AsyncMock(return_value="DELETE 1")

        result = await svc.delete_diagram("diag-001")
        assert result is True


# ---------------------------------------------------------------------------
# B5.1 — diagram_type routing + prompt-based path tests
# ---------------------------------------------------------------------------


class TestDiagramTypeRouting:
    """New tests introduced in B5.1 for the multi-type diagram generator."""

    def test_supported_diagram_types_whitelist(self) -> None:
        """The public whitelist covers flowchart / sequence / bpmn_swimlane only."""
        assert SUPPORTED_DIAGRAM_TYPES == ("flowchart", "sequence", "bpmn_swimlane")

    @pytest.mark.asyncio
    async def test_generate_sequence_diagram_new(self, mock_pool) -> None:
        """diagram_type='sequence' uses the prompt path and emits a sequenceDiagram header."""
        planner = {
            "diagram_type": "sequence",
            "title": "Login flow",
            "actors": ["User", "Frontend", "Backend"],
            "steps": [],
            "interactions": [
                {"from": "User", "to": "Frontend", "label": "login", "type": "sync"},
                {"from": "Frontend", "to": "Backend", "label": "auth", "type": "sync"},
                {"from": "Backend", "to": "Frontend", "label": "token", "type": "response"},
            ],
            "edges": [],
            "reason": None,
        }
        mermaid = (
            "sequenceDiagram\n"
            "    participant U as User\n"
            "    participant F as Frontend\n"
            "    participant B as Backend\n"
            "    U->>F: login\n"
            "    F->>B: auth\n"
            "    B-->>F: token\n"
        )
        reviewer = {
            "valid": True,
            "errors": [],
            "suggestions": [],
            "fixed_code": None,
        }

        service, fake_models = _build_prompt_path_service(mock_pool, planner, mermaid, reviewer)

        record = await service.generate(
            "User logs in via frontend that calls backend",
            diagram_type="sequence",
            created_by="admin",
        )

        assert isinstance(record, DiagramRecord)
        assert record.mermaid_code.startswith("sequenceDiagram")
        assert "participant" in record.mermaid_code
        # All three prompts must have been invoked in order.
        assert fake_models.generate.await_count == 3
        # Kroki stub should have populated svg_content.
        assert record.svg_content == "<svg>rendered</svg>"

    @pytest.mark.asyncio
    async def test_generate_bpmn_swimlane_new(self, mock_pool) -> None:
        """diagram_type='bpmn_swimlane' produces a flowchart LR + subgraph layout."""
        planner = {
            "diagram_type": "bpmn_swimlane",
            "title": "HR/IT onboarding",
            "actors": ["HR", "IT"],
            "steps": [
                {"id": "hr1", "label": "Create contract", "actor": "HR", "kind": "task"},
                {"id": "it1", "label": "Create account", "actor": "IT", "kind": "task"},
            ],
            "interactions": [],
            "edges": [{"from": "hr1", "to": "it1", "label": "", "condition": None}],
            "reason": None,
        }
        mermaid = (
            "flowchart LR\n"
            "    subgraph HR[HR]\n"
            "        hr1[Create contract]\n"
            "    end\n"
            "    subgraph IT[IT]\n"
            "        it1[Create account]\n"
            "    end\n"
            "    hr1 --> it1\n"
        )
        reviewer = {"valid": True, "errors": [], "suggestions": [], "fixed_code": None}

        service, _ = _build_prompt_path_service(mock_pool, planner, mermaid, reviewer)

        record = await service.generate(
            "HR creates contract then IT creates account",
            diagram_type="bpmn_swimlane",
        )

        assert "flowchart LR" in record.mermaid_code
        assert "subgraph HR" in record.mermaid_code
        assert "subgraph IT" in record.mermaid_code

    @pytest.mark.asyncio
    async def test_diagram_adapter_passes_type(self, mock_pool) -> None:
        """DiagramGenerateAdapter._run must forward diagram_type to the service."""
        from aiflow.core.context import ExecutionContext
        from aiflow.pipeline.adapters.diagram_adapter import (
            DiagramGenerateAdapter,
            GenerateDiagramInput,
        )

        captured: dict = {}

        class _StubService:
            async def generate(
                self,
                user_input: str,
                diagram_type: str = "flowchart",
                created_by: str | None = None,
            ) -> DiagramRecord:
                captured["user_input"] = user_input
                captured["diagram_type"] = diagram_type
                captured["created_by"] = created_by
                return DiagramRecord(
                    id="diag-adapter-1",
                    user_input=user_input,
                    mermaid_code="sequenceDiagram\n  U->>F: hi\n",
                )

        adapter = DiagramGenerateAdapter(service=_StubService())
        ctx = ExecutionContext(run_id="run-1", user_id="tester")
        inp = GenerateDiagramInput(description="Login flow", diagram_type="sequence")
        result = await adapter._run(inp, {}, ctx)

        assert captured["diagram_type"] == "sequence"
        assert captured["user_input"] == "Login flow"
        assert captured["created_by"] == "tester"
        assert result["diagram_type"] == "sequence"
        assert result["mermaid_code"].startswith("sequenceDiagram")

    @pytest.mark.asyncio
    async def test_diagram_reviewer_auto_fix(self, mock_pool) -> None:
        """When reviewer returns fixed_code, the service replaces the broken mermaid."""
        planner = {
            "diagram_type": "sequence",
            "title": "Broken flow",
            "actors": ["A", "B"],
            "steps": [],
            "interactions": [{"from": "A", "to": "B", "label": "ping", "type": "sync"}],
            "edges": [],
            "reason": None,
        }
        # Broken output (missing header).
        broken = "A->>B: ping\n"
        fixed = "sequenceDiagram\n    A->>B: ping\n"
        reviewer = {
            "valid": False,
            "errors": ["Missing sequenceDiagram header"],
            "suggestions": ["Add sequenceDiagram as the first line"],
            "fixed_code": fixed,
        }

        service, _ = _build_prompt_path_service(mock_pool, planner, broken, reviewer)

        record = await service.generate("A pings B", diagram_type="sequence")

        assert record.mermaid_code.startswith("sequenceDiagram")
        assert record.review is not None
        assert record.review.get("valid") is False
        assert "Missing sequenceDiagram header" in record.review.get("errors", [])

    @pytest.mark.asyncio
    async def test_generate_invalid_type_fallback(
        self, svc: DiagramGeneratorService, mock_pool, _mock_skill_workflow
    ) -> None:
        """Unknown diagram_type falls back to the flowchart path (no exception)."""
        _pool, conn = mock_pool
        conn.execute = AsyncMock(return_value="INSERT 0 1")

        record = await svc.generate(
            "Some process",
            diagram_type="gantt",  # unsupported
            created_by="admin",
        )

        assert isinstance(record, DiagramRecord)
        # Flowchart path populates mermaid_code from the mocked workflow.
        assert "graph TD" in record.mermaid_code
