"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.template
    covers: [src/aiflow/pipeline/template.py]
    phase: C2
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [pipeline, jinja2, template, security]
"""

from __future__ import annotations

import pytest

from aiflow.pipeline.template import SecurityError, TemplateResolver


@pytest.fixture
def resolver():
    return TemplateResolver()


class TestResolveValue:
    def test_plain_string(self, resolver):
        assert resolver.resolve_value("hello", {}) == "hello"

    def test_non_string(self, resolver):
        assert resolver.resolve_value(42, {}) == 42
        assert resolver.resolve_value(True, {}) is True
        assert resolver.resolve_value(None, {}) is None

    def test_simple_variable(self, resolver):
        result = resolver.resolve_value("{{ input.name }}", {"input": {"name": "test"}})
        assert result == "test"

    def test_nested_variable(self, resolver):
        ctx = {"step1": {"output": {"emails": [{"subject": "Hi"}]}}}
        result = resolver.resolve_value("{{ step1.output.emails[0].subject }}", ctx)
        assert result == "Hi"

    def test_integer_coercion(self, resolver):
        result = resolver.resolve_value("{{ input.count }}", {"input": {"count": 5}})
        assert result == 5
        assert isinstance(result, int)

    def test_boolean_coercion(self, resolver):
        result = resolver.resolve_value("{{ input.flag }}", {"input": {"flag": True}})
        assert result is True

    def test_string_concat(self, resolver):
        ctx = {"item": {"first": "John", "last": "Doe"}}
        result = resolver.resolve_value("{{ item.first }} {{ item.last }}", ctx)
        assert result == "John Doe"


class TestResolveConfig:
    def test_flat_config(self, resolver):
        config = {"name": "{{ input.name }}", "count": 3}
        ctx = {"input": {"name": "test"}}
        result = resolver.resolve_config(config, ctx)
        assert result == {"name": "test", "count": 3}

    def test_nested_config(self, resolver):
        config = {"outer": {"inner": "{{ input.val }}"}}
        ctx = {"input": {"val": "hello"}}
        result = resolver.resolve_config(config, ctx)
        assert result == {"outer": {"inner": "hello"}}

    def test_list_config(self, resolver):
        config = {"items": ["{{ input.a }}", "{{ input.b }}"]}
        ctx = {"input": {"a": "x", "b": "y"}}
        result = resolver.resolve_config(config, ctx)
        assert result == {"items": ["x", "y"]}

    def test_mixed_config(self, resolver):
        config = {
            "id": "{{ input.id }}",
            "static": "hello",
            "count": 42,
        }
        ctx = {"input": {"id": "abc"}}
        result = resolver.resolve_config(config, ctx)
        assert result == {"id": "abc", "static": "hello", "count": 42}


class TestResolveExpression:
    def test_wrapped_expression(self, resolver):
        ctx = {"step1": {"output": {"emails": [1, 2, 3]}}}
        result = resolver.resolve_expression("{{ step1.output.emails }}", ctx)
        # compile_expression returns native Python objects, not strings
        assert result == [1, 2, 3]

    def test_unwrapped_expression(self, resolver):
        ctx = {"input": {"value": "hello"}}
        result = resolver.resolve_expression("input.value", ctx)
        assert result == "hello"

    def test_expression_returns_dict(self, resolver):
        ctx = {"step1": {"output": {"data": {"key": "val"}}}}
        result = resolver.resolve_expression("step1.output.data", ctx)
        assert result == {"key": "val"}

    def test_expression_empty_list(self, resolver):
        ctx = {"step1": {"output": {"emails": []}}}
        result = resolver.resolve_expression("step1.output.emails", ctx)
        assert result == []


class TestSecurity:
    def test_blocks_dunder(self, resolver):
        with pytest.raises(SecurityError, match="Blocked pattern"):
            resolver.resolve_value("{{ obj.__class__ }}", {"obj": {}})

    def test_blocks_import(self, resolver):
        with pytest.raises(SecurityError, match="Blocked pattern"):
            resolver.resolve_value("{{ import os }}", {})

    def test_blocks_exec(self, resolver):
        with pytest.raises(SecurityError, match="Blocked pattern"):
            resolver.resolve_value("{{ exec('code') }}", {})

    def test_blocks_eval(self, resolver):
        with pytest.raises(SecurityError, match="Blocked pattern"):
            resolver.resolve_value("{{ eval('1+1') }}", {})

    def test_missing_var_raises_strict(self, resolver):
        with pytest.raises(Exception):
            resolver.resolve_value("{{ nonexistent }}", {})


class TestTypeCoercion:
    def test_true(self, resolver):
        assert resolver._coerce_type("True") is True

    def test_false(self, resolver):
        assert resolver._coerce_type("False") is False

    def test_none(self, resolver):
        assert resolver._coerce_type("None") is None

    def test_int(self, resolver):
        assert resolver._coerce_type("42") == 42

    def test_float(self, resolver):
        assert resolver._coerce_type("3.14") == pytest.approx(3.14)

    def test_string(self, resolver):
        assert resolver._coerce_type("hello") == "hello"
