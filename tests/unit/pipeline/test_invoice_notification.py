"""
@test_registry:
    suite: pipeline-unit
    component: skills.invoice_finder.prompts.notification
    covers: [skills/invoice_finder/prompts/invoice_report_notification.yaml]
    phase: B3
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [pipeline, prompt, invoice-finder, notification]
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jinja2 import Template

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "skills"
    / "document_recognizer"
    / "prompts"
    / "invoice_report_notification.yaml"
)


@pytest.fixture(scope="module")
def template_data() -> dict:
    return yaml.safe_load(TEMPLATE_PATH.read_text(encoding="utf-8"))


class TestInvoiceNotificationTemplate:
    """Validate invoice_report_notification.yaml template."""

    def test_notification_template_yaml_valid(self, template_data: dict) -> None:
        """YAML parses correctly with required keys: name, channel, subject, body."""
        assert TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}"
        assert isinstance(template_data, dict)
        assert template_data["name"] == "invoice_finder/report_notification"
        assert template_data["channel"] == "email"
        assert "subject" in template_data
        assert "body" in template_data
        # Subject must contain Jinja2 variables
        assert "{{ date }}" in template_data["subject"]
        assert "{{ total_invoices }}" in template_data["subject"]
        # Body must contain key template variables
        body = template_data["body"]
        assert "{{ total_invoices }}" in body
        assert "{{ overdue_count }}" in body
        assert "{{ total_amount }}" in body

    def test_notification_template_renders(self, template_data: dict) -> None:
        """Jinja2 template renders correctly with sample data."""
        subject_tpl = Template(template_data["subject"])
        body_tpl = Template(template_data["body"])

        context = {
            "date": "2026-04-06",
            "total_invoices": 5,
            "overdue_count": 2,
            "due_soon_count": 1,
            "total_amount": "381,000",
            "currency": "HUF",
            "csv_path": "/data/invoices/invoices.csv",
            "overdue_invoices": [
                {
                    "invoice_number": "INV-2026-001",
                    "vendor_name": "Test Kft.",
                    "amount": "127,000",
                    "currency": "HUF",
                    "days_overdue": 36,
                },
            ],
        }

        rendered_subject = subject_tpl.render(**context)
        assert "2026-04-06" in rendered_subject
        assert "5 invoices" in rendered_subject

        rendered_body = body_tpl.render(**context)
        assert "5" in rendered_body
        assert "2" in rendered_body  # overdue_count
        assert "381,000" in rendered_body
        assert "INV-2026-001" in rendered_body
        assert "Test Kft." in rendered_body
