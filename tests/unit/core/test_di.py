"""
@test_registry:
    suite: core-unit
    component: core.di
    covers: [src/aiflow/core/di.py]
    phase: 1
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [di, container, injection]
"""
import pytest

from aiflow.core.di import Container


class FakeDatabase:
    def __init__(self, url: str = "test://"):
        self.url = url


class FakeCache:
    pass


class TestContainer:
    @pytest.fixture
    def container(self):
        c = Container()
        yield c
        c.clear()

    def test_register_and_resolve(self, container):
        db = FakeDatabase()
        container.register(FakeDatabase, db)
        assert container.resolve(FakeDatabase) is db

    def test_resolve_missing_raises(self, container):
        with pytest.raises(KeyError, match="not registered"):
            container.resolve(FakeDatabase)

    def test_factory_lazy_creation(self, container):
        created = []
        def factory():
            db = FakeDatabase("lazy://")
            created.append(db)
            return db
        container.register_factory(FakeDatabase, factory)
        assert len(created) == 0  # not created yet
        result = container.resolve(FakeDatabase)
        assert len(created) == 1  # created on first resolve
        assert result.url == "lazy://"

    def test_factory_called_once(self, container):
        call_count = 0
        def factory():
            nonlocal call_count
            call_count += 1
            return FakeDatabase()
        container.register_factory(FakeDatabase, factory)
        container.resolve(FakeDatabase)
        container.resolve(FakeDatabase)
        assert call_count == 1  # factory called only once

    def test_has(self, container):
        assert container.has(FakeDatabase) is False
        container.register(FakeDatabase, FakeDatabase())
        assert container.has(FakeDatabase) is True

    def test_has_factory(self, container):
        container.register_factory(FakeDatabase, FakeDatabase)
        assert container.has(FakeDatabase) is True

    def test_clear(self, container):
        container.register(FakeDatabase, FakeDatabase())
        container.register(FakeCache, FakeCache())
        container.clear()
        assert container.has(FakeDatabase) is False
        assert container.has(FakeCache) is False

    def test_multiple_services(self, container):
        db = FakeDatabase()
        cache = FakeCache()
        container.register(FakeDatabase, db)
        container.register(FakeCache, cache)
        assert container.resolve(FakeDatabase) is db
        assert container.resolve(FakeCache) is cache

    def test_repr(self, container):
        container.register(FakeDatabase, FakeDatabase())
        r = repr(container)
        assert "FakeDatabase" in r
