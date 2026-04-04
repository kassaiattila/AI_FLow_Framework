"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters.notification
    covers: [src/aiflow/pipeline/adapters/notification_adapter.py]
    phase: C7
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [pipeline, adapter, notification]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapters.notification_adapter import (
    NotificationSendAdapter,
    NotifySendInput,
    NotifySendOutput,
)

# --- Fake service ---


@dataclass
class FakeNotificationResult:
    channel: str = "email"
    sent: bool = True
    message_id: str | None = "msg-001"
    recipient: str = "test@example.com"
    error: str | None = None


class FakeNotificationService:
    """Fake service for unit testing the adapter logic."""

    def __init__(self, results: list[FakeNotificationResult] | None = None) -> None:
        self._results = results or [FakeNotificationResult()]
        self.last_call: dict[str, Any] = {}

    async def send(
        self,
        channel: str,
        template: str,
        data: dict,
        recipients: list[str],
        config_name: str | None = None,
        subject: str | None = None,
        pipeline_run_id: str | None = None,
    ) -> list[FakeNotificationResult]:
        self.last_call = {
            "channel": channel,
            "template": template,
            "data": data,
            "recipients": recipients,
            "config_name": config_name,
            "subject": subject,
            "pipeline_run_id": pipeline_run_id,
        }
        return self._results


@pytest.fixture()
def ctx() -> ExecutionContext:
    return ExecutionContext()


@pytest.fixture()
def fake_svc() -> FakeNotificationService:
    return FakeNotificationService()


@pytest.fixture()
def adapter(fake_svc: FakeNotificationService) -> NotificationSendAdapter:
    return NotificationSendAdapter(service=fake_svc)


# --- Tests ---


class TestNotificationSendAdapter:
    """Unit tests for NotificationSendAdapter."""

    @pytest.mark.asyncio
    async def test_basic_send(
        self, adapter: NotificationSendAdapter, fake_svc: FakeNotificationService, ctx: ExecutionContext
    ) -> None:
        result = await adapter.execute(
            input_data={
                "channel": "email",
                "template": "Hello {{ name }}",
                "data": {"name": "World"},
                "recipients": ["user@test.com"],
            },
            config={},
            ctx=ctx,
        )
        assert result["sent_count"] == 1
        assert result["failed_count"] == 0
        assert len(result["results"]) == 1
        assert fake_svc.last_call["channel"] == "email"
        assert fake_svc.last_call["recipients"] == ["user@test.com"]

    @pytest.mark.asyncio
    async def test_config_overrides_input(
        self, adapter: NotificationSendAdapter, fake_svc: FakeNotificationService, ctx: ExecutionContext
    ) -> None:
        result = await adapter.execute(
            input_data={
                "channel": "email",
                "template": "default template",
                "recipients": ["default@test.com"],
            },
            config={
                "channel": "slack",
                "template": "override template",
                "recipients": ["#alerts"],
                "config_name": "bestix_slack",
                "subject": "Override subject",
            },
            ctx=ctx,
        )
        assert fake_svc.last_call["channel"] == "slack"
        assert fake_svc.last_call["template"] == "override template"
        assert fake_svc.last_call["recipients"] == ["#alerts"]
        assert fake_svc.last_call["config_name"] == "bestix_slack"
        assert fake_svc.last_call["subject"] == "Override subject"

    @pytest.mark.asyncio
    async def test_data_merge(
        self, adapter: NotificationSendAdapter, fake_svc: FakeNotificationService, ctx: ExecutionContext
    ) -> None:
        result = await adapter.execute(
            input_data={
                "channel": "email",
                "template": "test",
                "data": {"a": 1, "b": 2},
                "recipients": ["x@y.com"],
            },
            config={"data": {"b": 99, "c": 3}},
            ctx=ctx,
        )
        # Config data should override input data
        assert fake_svc.last_call["data"] == {"a": 1, "b": 99, "c": 3}

    @pytest.mark.asyncio
    async def test_multiple_recipients(self, ctx: ExecutionContext) -> None:
        results = [
            FakeNotificationResult(recipient="a@test.com"),
            FakeNotificationResult(recipient="b@test.com"),
        ]
        fake = FakeNotificationService(results=results)
        adapter = NotificationSendAdapter(service=fake)

        result = await adapter.execute(
            input_data={
                "channel": "email",
                "template": "hi",
                "recipients": ["a@test.com", "b@test.com"],
            },
            config={},
            ctx=ctx,
        )
        assert result["sent_count"] == 2
        assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_failed_send(self, ctx: ExecutionContext) -> None:
        results = [
            FakeNotificationResult(sent=False, error="SMTP timeout", recipient="fail@test.com"),
        ]
        fake = FakeNotificationService(results=results)
        adapter = NotificationSendAdapter(service=fake)

        result = await adapter.execute(
            input_data={
                "channel": "email",
                "template": "test",
                "recipients": ["fail@test.com"],
            },
            config={},
            ctx=ctx,
        )
        assert result["sent_count"] == 0
        assert result["failed_count"] == 1
        assert result["results"][0]["error"] == "SMTP timeout"

    @pytest.mark.asyncio
    async def test_mixed_results(self, ctx: ExecutionContext) -> None:
        results = [
            FakeNotificationResult(sent=True, recipient="ok@test.com"),
            FakeNotificationResult(sent=False, error="Bad address", recipient="bad@test.com"),
        ]
        fake = FakeNotificationService(results=results)
        adapter = NotificationSendAdapter(service=fake)

        result = await adapter.execute(
            input_data={
                "channel": "email",
                "template": "test",
                "recipients": ["ok@test.com", "bad@test.com"],
            },
            config={},
            ctx=ctx,
        )
        assert result["sent_count"] == 1
        assert result["failed_count"] == 1

    @pytest.mark.asyncio
    async def test_empty_recipients(
        self, adapter: NotificationSendAdapter, fake_svc: FakeNotificationService, ctx: ExecutionContext
    ) -> None:
        fake_svc._results = []
        result = await adapter.execute(
            input_data={
                "channel": "email",
                "template": "test",
                "recipients": [],
            },
            config={},
            ctx=ctx,
        )
        assert result["sent_count"] == 0
        assert result["failed_count"] == 0
        assert result["results"] == []

    def test_adapter_registered(self) -> None:
        from aiflow.pipeline.adapter_base import adapter_registry

        a = adapter_registry.get("notification", "send")
        assert a is not None
        assert a.service_name == "notification"
        assert a.method_name == "send"

    def test_input_schema(self) -> None:
        inp = NotifySendInput(
            channel="slack",
            template="Hello {{ name }}",
            data={"name": "World"},
            recipients=["#general"],
            config_name="my_slack",
            subject="Test",
        )
        assert inp.channel == "slack"
        assert inp.config_name == "my_slack"

    def test_output_schema(self) -> None:
        out = NotifySendOutput(sent_count=2, failed_count=1, results=[])
        assert out.sent_count == 2
        assert out.failed_count == 1
