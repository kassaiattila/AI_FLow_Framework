"""
@test_registry:
    suite: service-unit
    component: services.data_router
    covers: [src/aiflow/services/data_router/service.py]
    phase: C8
    priority: critical
    estimated_duration_ms: 800
    requires_services: []
    tags: [service, data-router, filter, routing, file-io]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.services.data_router.service import (
    DataRouterConfig,
    DataRouterService,
    FilterResult,
    RoutedFile,
    RoutingRule,
)


@pytest.fixture()
def svc(tmp_path: Path) -> DataRouterService:
    return DataRouterService(config=DataRouterConfig(base_output_dir=str(tmp_path)))


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_routing_rule(self) -> None:
        r = RoutingRule(condition="{{ amount > 100 }}", action="move_to_dir")
        assert r.action == "move_to_dir"
        assert r.config == {}

    def test_routed_file_defaults(self) -> None:
        rf = RoutedFile(file_path="/tmp/test.pdf")
        assert rf.success is True
        assert rf.error is None

    def test_filter_result(self) -> None:
        fr = FilterResult(filtered_items=[{"a": 1}], total=5, matched=1)
        assert fr.matched == 1

    def test_config_defaults(self) -> None:
        cfg = DataRouterConfig()
        assert cfg.base_output_dir == "./data/routed"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_service_name(self, svc: DataRouterService) -> None:
        assert svc.service_name == "data_router"

    def test_description(self, svc: DataRouterService) -> None:
        assert "routing" in svc.service_description.lower()

    @pytest.mark.asyncio
    async def test_start_stop(self, svc: DataRouterService) -> None:
        await svc.start()
        assert svc.status.value == "running"
        await svc.stop()
        assert svc.status.value == "stopped"

    @pytest.mark.asyncio
    async def test_health_check(self, svc: DataRouterService) -> None:
        assert await svc.health_check() is True


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


class TestFilter:
    @pytest.mark.asyncio
    async def test_filter_basic(self, svc: DataRouterService) -> None:
        items = [
            {"name": "a", "amount": 50},
            {"name": "b", "amount": 200},
            {"name": "c", "amount": 150},
        ]
        result = await svc.filter(items, "{{ amount > 100 }}")
        assert result.total == 3
        assert result.matched == 2
        assert len(result.filtered_items) == 2
        names = [i["name"] for i in result.filtered_items]
        assert "b" in names
        assert "c" in names

    @pytest.mark.asyncio
    async def test_filter_no_match(self, svc: DataRouterService) -> None:
        items = [{"x": 1}, {"x": 2}]
        result = await svc.filter(items, "{{ x > 100 }}")
        assert result.matched == 0
        assert result.filtered_items == []

    @pytest.mark.asyncio
    async def test_filter_all_match(self, svc: DataRouterService) -> None:
        items = [{"val": True}, {"val": True}]
        result = await svc.filter(items, "{{ val }}")
        assert result.matched == 2

    @pytest.mark.asyncio
    async def test_filter_empty_list(self, svc: DataRouterService) -> None:
        result = await svc.filter([], "{{ x > 0 }}")
        assert result.total == 0
        assert result.matched == 0

    @pytest.mark.asyncio
    async def test_filter_string_equality(self, svc: DataRouterService) -> None:
        items = [
            {"vendor": "ACME", "amount": 100},
            {"vendor": "OTHER", "amount": 200},
        ]
        result = await svc.filter(items, "{{ vendor == 'ACME' }}")
        assert result.matched == 1
        assert result.filtered_items[0]["vendor"] == "ACME"

    @pytest.mark.asyncio
    async def test_filter_unwrapped_condition(self, svc: DataRouterService) -> None:
        items = [{"a": 10}, {"a": 5}]
        result = await svc.filter(items, "a > 7")
        assert result.matched == 1


# ---------------------------------------------------------------------------
# Move to dir (REAL file I/O)
# ---------------------------------------------------------------------------


class TestMoveToDir:
    @pytest.mark.asyncio
    async def test_move_basic(self, svc: DataRouterService, tmp_path: Path) -> None:
        await svc.start()
        src = tmp_path / "input" / "invoice.pdf"
        src.parent.mkdir(parents=True)
        src.write_text("PDF content")

        result = await svc.move_to_dir(
            str(src),
            "vendor_{{ vendor }}/{{ year }}",
            {"vendor": "ACME", "year": "2026"},
        )
        assert result.success is True
        assert result.target_path is not None
        assert Path(result.target_path).exists()
        assert Path(result.target_path).read_text() == "PDF content"
        assert not src.exists()  # original moved

    @pytest.mark.asyncio
    async def test_move_file_not_found(self, svc: DataRouterService) -> None:
        await svc.start()
        result = await svc.move_to_dir("/nonexistent/file.txt", "out", {})
        assert result.success is False
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_move_preserves_filename(self, svc: DataRouterService, tmp_path: Path) -> None:
        await svc.start()
        src = tmp_path / "source" / "report.xlsx"
        src.parent.mkdir(parents=True)
        src.write_bytes(b"\x00\x01\x02")

        result = await svc.move_to_dir(str(src), "archive", {})
        assert result.success is True
        assert Path(result.target_path).name == "report.xlsx"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Route files (rule matching + real file I/O)
# ---------------------------------------------------------------------------


class TestRouteFiles:
    @pytest.mark.asyncio
    async def test_route_first_match_wins(self, svc: DataRouterService) -> None:
        files = [{"file_path": "/tmp/x.pdf", "amount": 500}]
        rules = [
            RoutingRule(condition="{{ amount > 100 }}", action="tag", config={"tag": "high"}),
            RoutingRule(condition="{{ amount > 0 }}", action="tag", config={"tag": "any"}),
        ]
        results = await svc.route_files(files, rules)
        assert len(results) == 1
        assert results[0].action == "tag"
        assert results[0].rule_matched == "{{ amount > 100 }}"

    @pytest.mark.asyncio
    async def test_route_no_match(self, svc: DataRouterService) -> None:
        files = [{"file_path": "/tmp/x.pdf", "amount": 5}]
        rules = [
            RoutingRule(condition="{{ amount > 1000 }}", action="tag"),
        ]
        results = await svc.route_files(files, rules)
        assert results[0].action == "none"
        assert results[0].rule_matched is None

    @pytest.mark.asyncio
    async def test_route_notify_action(self, svc: DataRouterService) -> None:
        files = [{"file_path": "/tmp/x.pdf", "priority": "high"}]
        rules = [
            RoutingRule(
                condition="{{ priority == 'high' }}",
                action="notify",
                config={"channel": "email"},
            ),
        ]
        results = await svc.route_files(files, rules)
        assert results[0].action == "notify"
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_route_move_to_dir_real(self, svc: DataRouterService, tmp_path: Path) -> None:
        await svc.start()
        src = tmp_path / "uploads" / "doc.pdf"
        src.parent.mkdir(parents=True)
        src.write_text("document content")

        files = [{"file_path": str(src), "vendor": "BestIx"}]
        rules = [
            RoutingRule(
                condition="{{ vendor == 'BestIx' }}",
                action="move_to_dir",
                config={"target_dir_template": "processed/{{ vendor }}"},
            ),
        ]
        results = await svc.route_files(files, rules)
        assert results[0].success is True
        assert results[0].target_path is not None
        assert Path(results[0].target_path).exists()
        assert not src.exists()

    @pytest.mark.asyncio
    async def test_route_unknown_action(self, svc: DataRouterService) -> None:
        files = [{"file_path": "/tmp/x.pdf", "val": True}]
        rules = [
            RoutingRule(condition="{{ val }}", action="explode"),
        ]
        results = await svc.route_files(files, rules)
        assert results[0].success is False
        assert "Unknown action" in (results[0].error or "")

    @pytest.mark.asyncio
    async def test_route_multiple_files(self, svc: DataRouterService) -> None:
        files = [
            {"file_path": "a.pdf", "cat": "invoice"},
            {"file_path": "b.pdf", "cat": "receipt"},
            {"file_path": "c.pdf", "cat": "invoice"},
        ]
        rules = [
            RoutingRule(condition="{{ cat == 'invoice' }}", action="tag"),
            RoutingRule(condition="{{ cat == 'receipt' }}", action="notify"),
        ]
        results = await svc.route_files(files, rules)
        assert len(results) == 3
        assert results[0].action == "tag"
        assert results[1].action == "notify"
        assert results[2].action == "tag"

    @pytest.mark.asyncio
    async def test_route_empty_files(self, svc: DataRouterService) -> None:
        results = await svc.route_files([], [])
        assert results == []
