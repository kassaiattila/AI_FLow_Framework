"""
@test_registry:
    suite: core-unit
    component: services.document_recognizer.registry (real bootstrap YAMLs)
    covers:
        - data/doctypes/hu_invoice.yaml
        - data/doctypes/hu_id_card.yaml
        - prompts/workflows/id_card_extraction_chain.yaml
    phase: v1.6.0
    priority: high
    estimated_duration_ms: 50
    requires_services: []
    tags: [unit, services, doc_recognizer, doctype_yaml, sprint_v, sv_2]
"""

from __future__ import annotations

from pathlib import Path

import yaml

from aiflow.contracts.doc_recognition import DocTypeDescriptor
from aiflow.prompts.workflow_loader import PromptWorkflowLoader
from aiflow.services.document_recognizer.registry import DocTypeRegistry

REPO_ROOT = Path(__file__).resolve().parents[4]
DOCTYPES_DIR = REPO_ROOT / "data" / "doctypes"
WORKFLOWS_DIR = REPO_ROOT / "prompts" / "workflows"


class TestRealBootstrapDoctypes:
    """SV-2 ships 2 bootstrap descriptors. Both must Pydantic-validate."""

    def test_hu_invoice_yaml_loads(self):
        path = DOCTYPES_DIR / "hu_invoice.yaml"
        assert path.exists(), f"hu_invoice.yaml missing at {path}"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        d = DocTypeDescriptor.model_validate(payload)
        assert d.name == "hu_invoice"
        assert d.language == "hu"
        assert d.category == "financial"
        assert d.pii_level == "low"
        assert d.extraction.workflow == "invoice_extraction_chain"
        # Field shape
        names = d.field_names()
        for required in (
            "invoice_number",
            "vendor_name",
            "buyer_name",
            "issue_date",
            "total_gross",
        ):
            assert required in names, f"hu_invoice missing required field {required}"
        # Rules sum to ~1.0 (well-formed descriptor)
        assert 0.95 <= d.total_rule_weight() <= 1.05

    def test_hu_id_card_yaml_loads(self):
        path = DOCTYPES_DIR / "hu_id_card.yaml"
        assert path.exists()
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        d = DocTypeDescriptor.model_validate(payload)
        assert d.name == "hu_id_card"
        assert d.language == "hu"
        assert d.category == "identity"
        assert d.pii_level == "high"
        assert d.intent_routing.pii_redaction is True
        assert d.intent_routing.default == "route_to_human"
        assert d.extraction.workflow == "id_card_extraction_chain"
        # Required PII fields
        names = d.field_names()
        for required in ("full_name", "birth_date", "id_number"):
            assert required in names

    def test_hu_address_card_yaml_loads(self):
        path = DOCTYPES_DIR / "hu_address_card.yaml"
        assert path.exists(), f"hu_address_card.yaml missing at {path}"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        d = DocTypeDescriptor.model_validate(payload)
        assert d.name == "hu_address_card"
        assert d.pii_level == "medium"
        assert d.intent_routing.pii_redaction is True
        assert d.intent_routing.default == "route_to_human"
        names = d.field_names()
        for required in ("full_name", "address_zip", "address_city", "address_street"):
            assert required in names

    def test_pdf_contract_yaml_loads(self):
        path = DOCTYPES_DIR / "pdf_contract.yaml"
        assert path.exists(), f"pdf_contract.yaml missing at {path}"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        d = DocTypeDescriptor.model_validate(payload)
        assert d.name == "pdf_contract"
        assert d.category == "legal"
        assert d.pii_level == "low"
        assert d.intent_routing.default == "rag_ingest"
        names = d.field_names()
        for required in ("contract_title", "party_a_name", "party_b_name"):
            assert required in names

    def test_registry_loads_all_four_bootstrap_descriptors(self):
        reg = DocTypeRegistry(bootstrap_dir=DOCTYPES_DIR)
        descriptors = reg.list_doctypes()
        names = {d.name for d in descriptors}
        assert "hu_invoice" in names
        assert "hu_id_card" in names
        assert "hu_address_card" in names
        assert "pdf_contract" in names


class TestIdCardExtractionChain:
    """The new PromptWorkflow descriptor referenced by hu_id_card.yaml."""

    def test_yaml_loads_and_dag_validates(self):
        path = WORKFLOWS_DIR / "id_card_extraction_chain.yaml"
        assert path.exists(), f"id_card_extraction_chain.yaml missing at {path}"
        loader = PromptWorkflowLoader(WORKFLOWS_DIR)
        workflow = loader.load_from_yaml(path)
        assert workflow.name == "id_card_extraction_chain"
        # 4-step DAG: ocr_normalize -> fields -> confidence -> validate
        step_ids = [s.id for s in workflow.steps]
        assert step_ids == ["ocr_normalize", "fields", "confidence", "validate"]
        # Per-step cost ceiling on `fields` step (Sprint U S154 check_step API target)
        fields_step = workflow.get_step("fields")
        assert fields_step.metadata.get("cost_ceiling_usd") == 0.02

    def test_validate_step_required_false(self):
        """The `validate` step is pure-Python (Sprint T S149 pattern); marked required: false
        so the executor can skip it during resolution."""
        path = WORKFLOWS_DIR / "id_card_extraction_chain.yaml"
        loader = PromptWorkflowLoader(WORKFLOWS_DIR)
        workflow = loader.load_from_yaml(path)
        validate_step = workflow.get_step("validate")
        assert validate_step.required is False
