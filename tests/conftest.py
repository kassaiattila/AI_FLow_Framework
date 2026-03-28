"""Global test fixtures for AIFlow."""
import pytest
from aiflow.core.config import AIFlowSettings
from aiflow.core.context import ExecutionContext, TraceContext
from aiflow.core.events import EventBus
from aiflow.core.registry import Registry
from aiflow.core.di import Container


@pytest.fixture
def test_settings() -> AIFlowSettings:
    """Test-specific settings (no real LLM, no Langfuse)."""
    return AIFlowSettings(
        environment="test",
        debug=True,
        log_level="DEBUG",
    )


@pytest.fixture
def mock_ctx() -> ExecutionContext:
    """Mock ExecutionContext for unit tests."""
    return ExecutionContext(
        run_id="test-run-001",
        prompt_label="test",
        budget_remaining_usd=10.0,
        team_id="test-team",
        user_id="test-user",
    )


@pytest.fixture
def event_bus_clean() -> EventBus:
    """Fresh event bus for each test."""
    bus = EventBus()
    yield bus
    bus.clear()


@pytest.fixture
def registry() -> Registry:
    """Fresh registry for each test."""
    reg = Registry(name="test")
    yield reg
    reg.clear()


@pytest.fixture
def container() -> Container:
    """Fresh DI container for each test."""
    c = Container()
    yield c
    c.clear()
