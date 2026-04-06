"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.adapters.payment_status_adapter
    covers: [src/aiflow/pipeline/adapters/payment_status_adapter.py]
    phase: B3
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [pipeline, adapter, invoice-finder, payment-status]
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from aiflow.pipeline.adapters.payment_status_adapter import (
    PaymentStatusAdapter,
    PaymentStatusOutput,
    _determine_payment_status,
)


@pytest.fixture()
def mock_ctx() -> MagicMock:
    return MagicMock()


class TestPaymentStatusOverdue:
    """Payment status: overdue invoices."""

    def test_payment_status_overdue(self) -> None:
        """Invoice with past due date is marked overdue."""
        yesterday = (date.today() - timedelta(days=5)).isoformat()
        status, days, is_overdue = _determine_payment_status(yesterday)
        assert status == "overdue"
        assert days < 0
        assert is_overdue is True


class TestPaymentStatusDueSoon:
    """Payment status: invoices due within 30 days."""

    def test_payment_status_due_soon(self) -> None:
        """Invoice due within 30 days is marked due_soon."""
        in_15_days = (date.today() + timedelta(days=15)).isoformat()
        status, days, is_overdue = _determine_payment_status(in_15_days)
        assert status == "due_soon"
        assert 0 <= days <= 30
        assert is_overdue is False


class TestPaymentStatusNotDue:
    """Payment status: invoices not yet due."""

    def test_payment_status_not_due(self) -> None:
        """Invoice due in more than 30 days is marked not_due."""
        in_60_days = (date.today() + timedelta(days=60)).isoformat()
        status, days, is_overdue = _determine_payment_status(in_60_days)
        assert status == "not_due"
        assert days > 30
        assert is_overdue is False


class TestPaymentStatusUnknown:
    """Payment status: missing or invalid due date."""

    def test_payment_status_unknown_date(self) -> None:
        """Empty due date results in unknown status."""
        status, days, is_overdue = _determine_payment_status("")
        assert status == "unknown"
        assert days == 0
        assert is_overdue is False

    def test_payment_status_invalid_date_format(self) -> None:
        """Invalid date format also results in unknown status."""
        status, days, is_overdue = _determine_payment_status("not-a-date")
        assert status == "unknown"
        assert days == 0
        assert is_overdue is False


class TestPaymentStatusAdapterOutput:
    """Payment status adapter produces valid Pydantic output."""

    @pytest.mark.asyncio()
    async def test_payment_status_adapter_output(self, mock_ctx: MagicMock) -> None:
        """Adapter returns validated PaymentStatusOutput with correct fields."""
        overdue_date = (date.today() - timedelta(days=10)).isoformat()
        adapter = PaymentStatusAdapter()
        result = await adapter.execute(
            {
                "invoice_number": "INV-2026-001",
                "due_date": overdue_date,
                "amount": 127000.0,
            },
            {},
            mock_ctx,
        )
        assert isinstance(result, dict)
        # Validate through Pydantic
        output = PaymentStatusOutput.model_validate(result)
        assert output.invoice_number == "INV-2026-001"
        assert output.payment_status == "overdue"
        assert output.is_overdue is True
        assert output.amount == 127000.0
        assert output.days_until_due < 0
