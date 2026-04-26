"""
@test_registry:
    suite: core-unit
    component: services.document_recognizer.registry
    covers:
        - src/aiflow/services/document_recognizer/registry.py
    phase: v1.6.0
    priority: critical
    estimated_duration_ms: 60
    requires_services: []
    tags: [unit, services, doc_recognizer, sprint_v, sv_1]
"""

from __future__ import annotations

from pathlib import Path

import yaml

from aiflow.contracts.doc_recognition import (
    DocTypeDescriptor,
    ExtractionConfig,
    FieldSpec,
    IntentRoutingConfig,
    IntentRoutingRule,
    RuleSpec,
    TypeClassifierConfig,
)
from aiflow.services.document_recognizer.registry import DocTypeRegistry


def _minimal_descriptor_dict(
    name: str = "hu_invoice", workflow: str = "invoice_extraction_chain"
) -> dict:
    """Build a minimal-but-valid descriptor dict for YAML write."""
    return {
        "name": name,
        "display_name": f"Display {name}",
        "language": "hu",
        "category": "financial",
        "version": 1,
        "parser_preferences": ["docling"],
        "type_classifier": {
            "rules": [{"kind": "regex", "weight": 0.5, "pattern": r"\bSzámla\b"}],
            "llm_fallback": True,
            "llm_threshold_below": 0.7,
        },
        "extraction": {
            "workflow": workflow,
            "fields": [{"name": "invoice_number", "type": "string", "required": True}],
        },
    }


def _build_descriptor(
    name: str = "hu_id_card", workflow: str = "id_card_extraction_chain"
) -> DocTypeDescriptor:
    return DocTypeDescriptor(
        name=name,
        display_name=f"Display {name}",
        language="hu",
        category="identity",
        type_classifier=TypeClassifierConfig(
            rules=[RuleSpec(kind="regex", weight=0.4, pattern=r"\d{6}[A-Z]{2}")]
        ),
        extraction=ExtractionConfig(
            workflow=workflow,
            fields=[FieldSpec(name="id_number", type="string", required=True)],
        ),
        intent_routing=IntentRoutingConfig(
            default="route_to_human",
            conditions=[
                IntentRoutingRule(
                    if_expr="doc_type_confidence < 0.85",
                    intent="reject",
                    reason="too uncertain",
                )
            ],
        ),
    )


class TestDocTypeRegistryEmpty:
    def test_empty_dir_returns_empty_list(self, tmp_path: Path):
        reg = DocTypeRegistry(bootstrap_dir=tmp_path / "doctypes")
        assert reg.list_doctypes() == []

    def test_get_doctype_unknown_returns_none(self, tmp_path: Path):
        reg = DocTypeRegistry(bootstrap_dir=tmp_path / "doctypes")
        assert reg.get_doctype("nonexistent") is None


class TestDocTypeRegistryBootstrap:
    def test_loads_two_yaml_descriptors(self, tmp_path: Path):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()

        (bootstrap_dir / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice", "invoice_extraction_chain")),
            encoding="utf-8",
        )
        (bootstrap_dir / "hu_id_card.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_id_card", "id_card_extraction_chain")),
            encoding="utf-8",
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir)
        items = reg.list_doctypes()
        assert len(items) == 2
        # Sorted by name -> hu_id_card first
        assert [d.name for d in items] == ["hu_id_card", "hu_invoice"]

    def test_skips_underscore_prefixed_files(self, tmp_path: Path):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()

        (bootstrap_dir / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice")), encoding="utf-8"
        )
        (bootstrap_dir / "_template.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("_template")), encoding="utf-8"
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir)
        names = [d.name for d in reg.list_doctypes()]
        assert "hu_invoice" in names
        # _template is skipped by the leading-underscore filter
        assert "_template" not in names

    def test_invalid_yaml_logs_warning_and_skips(self, tmp_path: Path, caplog):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()

        # Valid descriptor
        (bootstrap_dir / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice")), encoding="utf-8"
        )
        # Invalid YAML
        (bootstrap_dir / "broken.yaml").write_text(
            "name: broken\nlevel: [unclosed bracket\n",
            encoding="utf-8",
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir)
        items = reg.list_doctypes()

        assert len(items) == 1
        assert items[0].name == "hu_invoice"

    def test_validation_error_logs_warning_and_skips(self, tmp_path: Path):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()

        # Missing required field 'extraction'
        (bootstrap_dir / "incomplete.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "incomplete",
                    "display_name": "Bad",
                    "type_classifier": {"rules": []},
                    # missing 'extraction'
                }
            ),
            encoding="utf-8",
        )
        # Valid descriptor
        (bootstrap_dir / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice")), encoding="utf-8"
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir)
        names = [d.name for d in reg.list_doctypes()]
        assert names == ["hu_invoice"]


class TestDocTypeRegistryTenantOverride:
    def test_tenant_override_replaces_bootstrap(self, tmp_path: Path):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()
        tenant_dir = tmp_path / "doctypes_tenant"
        tenant_dir.mkdir()

        (bootstrap_dir / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice", "invoice_extraction_chain")),
            encoding="utf-8",
        )
        # Tenant-specific override with different workflow
        tenant_acme = tenant_dir / "acme"
        tenant_acme.mkdir()
        (tenant_acme / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice", "acme_custom_invoice_chain")),
            encoding="utf-8",
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir, tenant_overrides_dir=tenant_dir)

        # Tenant view -> override
        d_acme = reg.get_doctype("hu_invoice", tenant_id="acme")
        assert d_acme is not None
        assert d_acme.extraction.workflow == "acme_custom_invoice_chain"

        # Default view (no tenant) -> bootstrap
        d_default = reg.get_doctype("hu_invoice")
        assert d_default is not None
        assert d_default.extraction.workflow == "invoice_extraction_chain"

    def test_other_tenants_dont_see_acme_override(self, tmp_path: Path):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()
        tenant_dir = tmp_path / "doctypes_tenant"
        tenant_dir.mkdir()

        (bootstrap_dir / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice", "invoice_extraction_chain")),
            encoding="utf-8",
        )
        tenant_acme = tenant_dir / "acme"
        tenant_acme.mkdir()
        (tenant_acme / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice", "acme_custom")),
            encoding="utf-8",
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir, tenant_overrides_dir=tenant_dir)

        d_other = reg.get_doctype("hu_invoice", tenant_id="globex")
        assert d_other is not None
        assert d_other.extraction.workflow == "invoice_extraction_chain"


class TestDocTypeRegistryRuntimeRegister:
    def test_register_global(self, tmp_path: Path):
        reg = DocTypeRegistry(bootstrap_dir=tmp_path / "doctypes")
        descriptor = _build_descriptor("hu_id_card")
        reg.register_doctype(descriptor)
        items = reg.list_doctypes()
        assert len(items) == 1
        assert items[0].name == "hu_id_card"

    def test_register_tenant_only(self, tmp_path: Path):
        reg = DocTypeRegistry(bootstrap_dir=tmp_path / "doctypes")
        descriptor = _build_descriptor("hu_id_card")
        reg.register_doctype(descriptor, tenant_id="acme")

        # Acme sees it
        assert reg.get_doctype("hu_id_card", tenant_id="acme") is not None
        # Other tenant doesn't
        assert reg.get_doctype("hu_id_card", tenant_id="globex") is None
        # Default view also doesn't (it was tenant-scoped registration)
        assert reg.get_doctype("hu_id_card") is None

    def test_runtime_overrides_disk(self, tmp_path: Path):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()
        (bootstrap_dir / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice", "from_disk")),
            encoding="utf-8",
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir)
        # Verify disk version first
        assert reg.get_doctype("hu_invoice").extraction.workflow == "from_disk"  # type: ignore[union-attr]

        # Runtime register a different version
        runtime = DocTypeDescriptor.model_validate(
            _minimal_descriptor_dict("hu_invoice", "from_runtime")
        )
        reg.register_doctype(runtime)
        # Runtime takes precedence
        assert reg.get_doctype("hu_invoice").extraction.workflow == "from_runtime"  # type: ignore[union-attr]


class TestDocTypeRegistrySummary:
    def test_to_summary_shape(self, tmp_path: Path):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()
        (bootstrap_dir / "hu_invoice.yaml").write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice")), encoding="utf-8"
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir)
        s = reg.to_summary()
        assert s["count"] == 1
        assert s["items"][0]["name"] == "hu_invoice"
        assert "field_count" in s["items"][0]
        assert s["items"][0]["pii_level"] == "low"


class TestDocTypeRegistryCacheInvalidate:
    def test_invalidate_re_reads_disk(self, tmp_path: Path):
        bootstrap_dir = tmp_path / "doctypes"
        bootstrap_dir.mkdir()
        path = bootstrap_dir / "hu_invoice.yaml"
        path.write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice", "version_a")),
            encoding="utf-8",
        )

        reg = DocTypeRegistry(bootstrap_dir=bootstrap_dir)
        assert reg.get_doctype("hu_invoice").extraction.workflow == "version_a"  # type: ignore[union-attr]

        # Update the descriptor on disk
        path.write_text(
            yaml.safe_dump(_minimal_descriptor_dict("hu_invoice", "version_b")),
            encoding="utf-8",
        )

        # Without invalidate, cached version still served
        assert reg.get_doctype("hu_invoice").extraction.workflow == "version_a"  # type: ignore[union-attr]

        # After invalidate, fresh read
        reg.invalidate_cache()
        assert reg.get_doctype("hu_invoice").extraction.workflow == "version_b"  # type: ignore[union-attr]
