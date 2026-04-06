"""
@test_registry:
    suite: service-unit
    component: services.diagram_generator
    covers: [src/aiflow/services/diagram_generator/service.py]
    phase: B2.1
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, diagram-generator, postgresql, kroki, mermaid]
"""

from __future__ import annotations

import json
import sys
import types
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from aiflow.services.diagram_generator.service import (
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
