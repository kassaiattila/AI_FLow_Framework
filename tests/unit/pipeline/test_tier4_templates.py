"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.templates
    covers: [
        src/aiflow/pipeline/templates.py,
        src/aiflow/pipeline/builtin_templates/knowledge_base_update.yaml,
        src/aiflow/pipeline/builtin_templates/email_triage.yaml,
        src/aiflow/pipeline/builtin_templates/advanced_rag_ingest.yaml,
        src/aiflow/pipeline/builtin_templates/contract_analysis.yaml,
    ]
    phase: C19
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [pipeline, templates, registry, tier4]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.pipeline.templates import TemplateInfo, TemplateRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Path to the built-in templates directory
BUILTIN_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "aiflow"
    / "pipeline"
    / "builtin_templates"
)


@pytest.fixture()
def registry() -> TemplateRegistry:
    return TemplateRegistry(template_dir=BUILTIN_DIR)


# ===========================================================================
# TestTemplateRegistry
# ===========================================================================


class TestTemplateRegistry:
    def test_discover_templates(self, registry: TemplateRegistry) -> None:
        """Discover finds all YAML files in the template directory."""
        templates = registry.discover()
        assert len(templates) >= 6, (
            f"Expected at least 6 templates, found {len(templates)}: "
            f"{[t.name for t in templates]}"
        )
        assert all(isinstance(t, TemplateInfo) for t in templates)

    def test_template_count(self, registry: TemplateRegistry) -> None:
        """Should have at least 6 templates: v1, v2, knowledge_base,
        email_triage, advanced_rag, contract."""
        templates = registry.list_all()
        names = {t.name for t in templates}
        expected = {
            "invoice_automation_v1",
            "invoice_automation_v2",
            "knowledge_base_update",
            "email_triage",
            "advanced_rag_ingest",
            "contract_analysis",
        }
        missing = expected - names
        assert not missing, f"Missing templates: {missing}"

    def test_get_template(self, registry: TemplateRegistry) -> None:
        """Get a specific template by name."""
        info = registry.get("knowledge_base_update")
        assert info is not None
        assert info.name == "knowledge_base_update"
        assert info.version == "1.0.0"
        assert info.step_count > 0
        assert len(info.description) > 0

    def test_get_nonexistent(self, registry: TemplateRegistry) -> None:
        """Get returns None for unknown template."""
        info = registry.get("nonexistent_template_xyz")
        assert info is None

    def test_get_yaml(self, registry: TemplateRegistry) -> None:
        """Get raw YAML content for a template."""
        yaml_content = registry.get_yaml("email_triage")
        assert yaml_content is not None
        assert "name: email_triage" in yaml_content
        assert "steps:" in yaml_content

    def test_get_yaml_nonexistent(self, registry: TemplateRegistry) -> None:
        """Get YAML returns None for unknown template."""
        content = registry.get_yaml("nonexistent_xyz")
        assert content is None

    def test_list_all(self, registry: TemplateRegistry) -> None:
        """List all returns all templates."""
        templates = registry.list_all()
        assert len(templates) >= 6
        names = [t.name for t in templates]
        assert "invoice_automation_v1" in names
        assert "contract_analysis" in names

    def test_template_has_metadata(self, registry: TemplateRegistry) -> None:
        """Each template has required metadata fields."""
        for tmpl in registry.list_all():
            assert tmpl.name, "Template missing name"
            assert tmpl.version, f"Template {tmpl.name} missing version"
            assert tmpl.step_count > 0, (
                f"Template {tmpl.name} has 0 steps"
            )

    def test_knowledge_base_template_steps(
        self, registry: TemplateRegistry
    ) -> None:
        """Knowledge base template has 5 steps."""
        info = registry.get("knowledge_base_update")
        assert info is not None
        assert info.step_count == 5
        assert info.category == "rag"

    def test_email_triage_template_steps(
        self, registry: TemplateRegistry
    ) -> None:
        """Email triage template has 4 steps."""
        info = registry.get("email_triage")
        assert info is not None
        assert info.step_count == 4
        assert info.category == "email"

    def test_advanced_rag_template_steps(
        self, registry: TemplateRegistry
    ) -> None:
        """Advanced RAG ingest template has 5 steps."""
        info = registry.get("advanced_rag_ingest")
        assert info is not None
        assert info.step_count == 5
        assert info.category == "rag"

    def test_contract_analysis_template_steps(
        self, registry: TemplateRegistry
    ) -> None:
        """Contract analysis template has 5 steps."""
        info = registry.get("contract_analysis")
        assert info is not None
        assert info.step_count == 5
        assert info.category == "legal"

    def test_template_tags(self, registry: TemplateRegistry) -> None:
        """Templates have category and tier tags."""
        info = registry.get("knowledge_base_update")
        assert info is not None
        assert "rag" in info.tags
        assert any("tier" in t for t in info.tags)

    def test_empty_dir(self, tmp_path: Path) -> None:
        """Registry with empty directory returns no templates."""
        reg = TemplateRegistry(template_dir=tmp_path)
        templates = reg.discover()
        assert templates == []

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        """Registry with nonexistent directory returns no templates."""
        reg = TemplateRegistry(
            template_dir=tmp_path / "nonexistent_dir_abc"
        )
        templates = reg.discover()
        assert templates == []

    def test_invoice_v1_exists(self, registry: TemplateRegistry) -> None:
        """Invoice V1 template (pre-existing) is discovered."""
        info = registry.get("invoice_automation_v1")
        assert info is not None
        assert info.version == "1.0.0"
        assert info.step_count == 3

    def test_invoice_v2_exists(self, registry: TemplateRegistry) -> None:
        """Invoice V2 template (pre-existing) is discovered."""
        info = registry.get("invoice_automation_v2")
        assert info is not None
        assert info.version == "2.0.0"
        assert info.step_count == 5
