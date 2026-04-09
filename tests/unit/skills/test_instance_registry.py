"""
@test_registry:
    suite: skills-unit
    component: skills.instance_registry
    covers: [src/aiflow/skills/instance_registry.py]
    phase: A
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [skills, instance, registry]
"""

import pytest

from aiflow.skills.instance import InstanceConfig, PromptConfig
from aiflow.skills.instance_registry import InstanceRegistry


def _make_config(
    name: str,
    skill: str = "aszf_rag_chat",
    customer: str = "testco",
    enabled: bool = True,
) -> InstanceConfig:
    """Helper to create a minimal InstanceConfig."""
    return InstanceConfig(
        instance_name=name,
        skill_template=skill,
        customer=customer,
        enabled=enabled,
        prompts=PromptConfig(namespace=f"{customer}/{name}"),
    )


class TestInstanceRegistry:
    def test_register_and_get(self) -> None:
        reg = InstanceRegistry()
        config = _make_config("test-1")
        reg.register(config)
        assert reg.get("test-1") is config

    def test_register_duplicate_raises(self) -> None:
        reg = InstanceRegistry()
        reg.register(_make_config("test-1"))
        with pytest.raises(ValueError, match="already registered"):
            reg.register(_make_config("test-1"))

    def test_get_missing_raises(self) -> None:
        reg = InstanceRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_get_or_none(self) -> None:
        reg = InstanceRegistry()
        assert reg.get_or_none("missing") is None
        config = _make_config("exists")
        reg.register(config)
        assert reg.get_or_none("exists") is config

    def test_has(self) -> None:
        reg = InstanceRegistry()
        assert reg.has("x") is False
        reg.register(_make_config("x"))
        assert reg.has("x") is True

    def test_unregister(self) -> None:
        reg = InstanceRegistry()
        reg.register(_make_config("del-me"))
        reg.unregister("del-me")
        assert reg.has("del-me") is False

    def test_unregister_missing_raises(self) -> None:
        reg = InstanceRegistry()
        with pytest.raises(KeyError):
            reg.unregister("nope")

    def test_list_all(self) -> None:
        reg = InstanceRegistry()
        reg.register(_make_config("a"))
        reg.register(_make_config("b"))
        assert len(reg.list_all()) == 2

    def test_list_by_customer(self) -> None:
        reg = InstanceRegistry()
        reg.register(_make_config("azhu-1", customer="azhu"))
        reg.register(_make_config("azhu-2", customer="azhu"))
        reg.register(_make_config("npra-1", customer="npra"))
        azhu = reg.list_by_customer("azhu")
        assert len(azhu) == 2
        assert all(c.customer == "azhu" for c in azhu)

    def test_list_by_skill(self) -> None:
        reg = InstanceRegistry()
        reg.register(_make_config("rag-1", skill="aszf_rag_chat"))
        reg.register(_make_config("rag-2", skill="aszf_rag_chat"))
        reg.register(_make_config("email-1", skill="email_intent"))
        rags = reg.list_by_skill("aszf_rag_chat")
        assert len(rags) == 2

    def test_list_enabled(self) -> None:
        reg = InstanceRegistry()
        reg.register(_make_config("on", enabled=True))
        reg.register(_make_config("off", enabled=False))
        enabled = reg.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].instance_name == "on"

    def test_list_names(self) -> None:
        reg = InstanceRegistry()
        reg.register(_make_config("alpha"))
        reg.register(_make_config("beta"))
        names = reg.list_names()
        assert set(names) == {"alpha", "beta"}

    def test_clear(self) -> None:
        reg = InstanceRegistry()
        reg.register(_make_config("x"))
        reg.register(_make_config("y"))
        reg.clear()
        assert len(reg) == 0

    def test_len(self) -> None:
        reg = InstanceRegistry()
        assert len(reg) == 0
        reg.register(_make_config("one"))
        assert len(reg) == 1

    def test_repr(self) -> None:
        reg = InstanceRegistry()
        assert "InstanceRegistry" in repr(reg)
