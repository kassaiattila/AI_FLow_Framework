"""
@test_registry:
    suite: core-unit
    component: core.events
    covers: [src/aiflow/core/events.py]
    phase: 1
    priority: high
    estimated_duration_ms: 150
    requires_services: []
    tags: [events, pubsub, async]
"""
import pytest
from aiflow.core.events import EventBus


class TestEventBus:
    @pytest.fixture
    def bus(self):
        b = EventBus()
        yield b
        b.clear()

    def test_register_and_count(self, bus):
        bus.on("test_event", lambda: None)
        assert bus.handler_count == 1

    def test_register_multiple_handlers(self, bus):
        bus.on("event_a", lambda: None)
        bus.on("event_a", lambda: None)
        bus.on("event_b", lambda: None)
        assert bus.handler_count == 3

    @pytest.mark.asyncio
    async def test_emit_sync_handler(self, bus):
        results = []
        bus.on("test", lambda value=None: results.append(value))
        await bus.emit("test", value="hello")
        assert results == ["hello"]

    @pytest.mark.asyncio
    async def test_emit_async_handler(self, bus):
        results = []
        async def handler(value=None):
            results.append(value)
        bus.on("test", handler)
        await bus.emit("test", value="async_hello")
        assert results == ["async_hello"]

    @pytest.mark.asyncio
    async def test_emit_no_handlers(self, bus):
        # Should not raise
        await bus.emit("nonexistent_event")

    @pytest.mark.asyncio
    async def test_emit_multiple_handlers(self, bus):
        results = []
        bus.on("test", lambda: results.append("a"))
        bus.on("test", lambda: results.append("b"))
        await bus.emit("test")
        assert results == ["a", "b"]

    @pytest.mark.asyncio
    async def test_handler_error_does_not_stop_others(self, bus):
        results = []
        def bad_handler():
            raise ValueError("boom")
        bus.on("test", bad_handler)
        bus.on("test", lambda: results.append("ok"))
        await bus.emit("test")
        assert results == ["ok"]

    def test_off_removes_handler(self, bus):
        handler = lambda: None
        bus.on("test", handler)
        assert bus.handler_count == 1
        bus.off("test", handler)
        assert bus.handler_count == 0

    def test_clear(self, bus):
        bus.on("a", lambda: None)
        bus.on("b", lambda: None)
        bus.clear()
        assert bus.handler_count == 0
