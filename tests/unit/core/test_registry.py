"""
@test_registry:
    suite: core-unit
    component: core.registry
    covers: [src/aiflow/core/registry.py]
    phase: 1
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [registry, lookup, components]
"""

import pytest

from aiflow.core.registry import Registry


class TestRegistry:
    @pytest.fixture
    def reg(self):
        r = Registry(name="test")
        yield r
        r.clear()

    def test_register_and_get(self, reg):
        reg.register("item1", {"value": 42})
        assert reg.get("item1") == {"value": 42}

    def test_register_duplicate_raises(self, reg):
        reg.register("item1", "a")
        with pytest.raises(ValueError, match="already registered"):
            reg.register("item1", "b")

    def test_get_missing_raises(self, reg):
        with pytest.raises(KeyError, match="not found"):
            reg.get("nonexistent")

    def test_get_or_none(self, reg):
        assert reg.get_or_none("missing") is None
        reg.register("exists", 123)
        assert reg.get_or_none("exists") == 123

    def test_has(self, reg):
        assert reg.has("x") is False
        reg.register("x", "val")
        assert reg.has("x") is True

    def test_unregister(self, reg):
        reg.register("item", "val")
        reg.unregister("item")
        assert reg.has("item") is False

    def test_unregister_missing_raises(self, reg):
        with pytest.raises(KeyError):
            reg.unregister("nonexistent")

    def test_list_keys(self, reg):
        reg.register("a", 1)
        reg.register("b", 2)
        assert sorted(reg.list_keys()) == ["a", "b"]

    def test_len(self, reg):
        assert len(reg) == 0
        reg.register("x", 1)
        assert len(reg) == 1

    def test_contains(self, reg):
        reg.register("x", 1)
        assert "x" in reg
        assert "y" not in reg

    def test_clear(self, reg):
        reg.register("a", 1)
        reg.register("b", 2)
        reg.clear()
        assert len(reg) == 0

    def test_repr(self, reg):
        assert "test" in repr(reg)
