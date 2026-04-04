"""
@test_registry:
    suite: core-unit
    component: state.repository
    covers: [src/aiflow/state/repository.py]
    phase: 1
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [state, repository, async]
"""
from unittest.mock import MagicMock

from aiflow.state.repository import StateRepository


class TestStateRepositoryInit:
    def test_creates_with_session_factory(self):
        factory = MagicMock()
        repo = StateRepository(factory)
        assert repo._session_factory is factory


class TestCreateSessionFactory:
    def test_function_exists(self):
        from aiflow.state.repository import create_session_factory
        assert callable(create_session_factory)
