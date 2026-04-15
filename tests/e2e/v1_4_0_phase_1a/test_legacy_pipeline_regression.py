"""Legacy v1.3 pipeline auto-upgrade regression.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, compat, pipeline, regression]

Exercises `upgrade_pipeline_v1_3_to_v1_4` against every v1.3 pipeline YAML
discovered in the repo (see `fixtures/legacy_pipelines_inventory.md`).
Guards against regressions where an upgrade rule silently drops steps,
mutates the caller's dict, or breaks idempotency.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aiflow.pipeline.compatibility import (
    detect_pipeline_version,
    upgrade_pipeline_v1_3_to_v1_4,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILTIN_TEMPLATES = REPO_ROOT / "src" / "aiflow" / "pipeline" / "builtin_templates"
FIXTURE_LEGACY = Path(__file__).parent / "fixtures" / "sample_legacy_pipeline.yaml"


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _discover_legacy_pipelines() -> list[Path]:
    candidates: list[Path] = []
    if BUILTIN_TEMPLATES.is_dir():
        for p in sorted(BUILTIN_TEMPLATES.glob("*.yaml")):
            data = _load_yaml(p)
            if detect_pipeline_version(data) == "v1.3":
                candidates.append(p)
    if FIXTURE_LEGACY.is_file():
        candidates.append(FIXTURE_LEGACY)
    return candidates


LEGACY_PIPELINES = _discover_legacy_pipelines()


@pytest.fixture(params=LEGACY_PIPELINES, ids=lambda p: p.name)
def legacy_yaml(request: pytest.FixtureRequest) -> dict:
    return _load_yaml(request.param)


class TestInventoryNonEmpty:
    """Guard: inventory must find at least the known fixture + builtin templates."""

    def test_inventory_has_fixture(self) -> None:
        assert FIXTURE_LEGACY in LEGACY_PIPELINES, (
            "sample_legacy_pipeline.yaml fixture missing from inventory"
        )

    def test_inventory_has_builtin_templates(self) -> None:
        builtin_count = sum(1 for p in LEGACY_PIPELINES if p.parent == BUILTIN_TEMPLATES)
        assert builtin_count >= 5, (
            f"Expected >=5 builtin v1.3 templates, inventory found {builtin_count}"
        )


class TestDetectPreUpgrade:
    def test_every_inventory_entry_detects_as_v1_3(self, legacy_yaml: dict) -> None:
        assert detect_pipeline_version(legacy_yaml) == "v1.3"


class TestUpgradeDoesNotRaise:
    def test_upgrade_completes(self, legacy_yaml: dict) -> None:
        upgrade_pipeline_v1_3_to_v1_4(legacy_yaml)


class TestUpgradePostconditions:
    def test_version_bumped_to_2_0(self, legacy_yaml: dict) -> None:
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_yaml)
        assert upgraded.get("version") == "2.0"

    def test_detected_as_v1_4_after_upgrade(self, legacy_yaml: dict) -> None:
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_yaml)
        assert detect_pipeline_version(upgraded) == "v1.4"

    def test_step_count_preserved_or_greater(self, legacy_yaml: dict) -> None:
        before = len(legacy_yaml.get("steps", []))
        upgraded = upgrade_pipeline_v1_3_to_v1_4(legacy_yaml)
        after = len(upgraded.get("steps", []))
        assert after >= before, f"Upgrade dropped steps: {before} -> {after}"

    def test_input_dict_not_mutated(self, legacy_yaml: dict) -> None:
        original_version = legacy_yaml.get("version")
        original_step_count = len(legacy_yaml.get("steps", []))
        upgrade_pipeline_v1_3_to_v1_4(legacy_yaml)
        assert legacy_yaml.get("version") == original_version
        assert len(legacy_yaml.get("steps", [])) == original_step_count


class TestIdempotency:
    """Upgrading an already-upgraded pipeline must be a no-op on schema markers."""

    def test_double_upgrade_yields_same_version(self, legacy_yaml: dict) -> None:
        once = upgrade_pipeline_v1_3_to_v1_4(legacy_yaml)
        twice = upgrade_pipeline_v1_3_to_v1_4(once)
        assert once.get("version") == twice.get("version") == "2.0"

    def test_double_upgrade_preserves_step_count(self, legacy_yaml: dict) -> None:
        once = upgrade_pipeline_v1_3_to_v1_4(legacy_yaml)
        twice = upgrade_pipeline_v1_3_to_v1_4(once)
        assert len(once.get("steps", [])) == len(twice.get("steps", []))

    def test_double_upgrade_still_detects_as_v1_4(self, legacy_yaml: dict) -> None:
        once = upgrade_pipeline_v1_3_to_v1_4(legacy_yaml)
        twice = upgrade_pipeline_v1_3_to_v1_4(once)
        assert detect_pipeline_version(twice) == "v1.4"


class TestAdapterStyleRewrite:
    """Fixture-level checks for the adapter rewrite branch (email_adapter path)."""

    def test_fixture_email_adapter_replaced(self) -> None:
        data = _load_yaml(FIXTURE_LEGACY)
        upgraded = upgrade_pipeline_v1_3_to_v1_4(data)
        adapters = [s.get("adapter") for s in upgraded["steps"]]
        assert "email_adapter" not in adapters
        assert "intake_normalize" in adapters

    def test_fixture_document_adapter_method_rewritten(self) -> None:
        data = _load_yaml(FIXTURE_LEGACY)
        upgraded = upgrade_pipeline_v1_3_to_v1_4(data)
        doc = next(s for s in upgraded["steps"] if s.get("adapter") == "document_adapter")
        assert doc["method"] == "extract_from_package"
        assert doc["for_each"] == "{{ intake.output.package }}"


class TestServiceStyleTemplatesPassthrough:
    """Builtin templates use `service:` keys — upgrade must not drop or rename them."""

    @pytest.mark.parametrize(
        "template_name",
        [p.name for p in LEGACY_PIPELINES if p.parent == BUILTIN_TEMPLATES],
    )
    def test_service_keys_preserved(self, template_name: str) -> None:
        path = BUILTIN_TEMPLATES / template_name
        data = _load_yaml(path)
        services_before = [s.get("service") for s in data.get("steps", [])]
        upgraded = upgrade_pipeline_v1_3_to_v1_4(data)
        services_after = [s.get("service") for s in upgraded.get("steps", [])]
        assert services_before == services_after, (
            f"{template_name}: service keys changed during upgrade"
        )
