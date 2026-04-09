"""Pipeline adapter for payment status checking (date-based, no external service)."""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

logger = structlog.get_logger(__name__)

__all__ = [
    "PaymentStatusInput",
    "PaymentStatusOutput",
    "PaymentStatusAdapter",
]


class PaymentStatusInput(BaseModel):
    """Input schema for payment status check."""

    invoice_number: str = Field("", description="Invoice number")
    due_date: str = Field("", description="Due date in YYYY-MM-DD format")
    amount: float = Field(0.0, description="Invoice gross total amount")


class PaymentStatusOutput(BaseModel):
    """Output schema for payment status check."""

    invoice_number: str = ""
    due_date: str = ""
    amount: float = 0.0
    payment_status: str = Field("unknown", description="overdue | due_soon | not_due | unknown")
    days_until_due: int = 0
    is_overdue: bool = False


def _determine_payment_status(
    due_date_str: str,
    reference_date: date | None = None,
) -> tuple[str, int, bool]:
    """Determine payment status from due date string.

    Returns:
        Tuple of (status, days_until_due, is_overdue).
    """
    if not due_date_str or not due_date_str.strip():
        return "unknown", 0, False

    ref = reference_date or date.today()

    try:
        due = date.fromisoformat(due_date_str.strip())
    except ValueError:
        logger.warning("invalid_due_date_format", due_date=due_date_str)
        return "unknown", 0, False

    days_until = (due - ref).days

    if days_until < 0:
        return "overdue", days_until, True
    elif days_until <= 30:
        return "due_soon", days_until, False
    else:
        return "not_due", days_until, False


class PaymentStatusAdapter(BaseAdapter):
    """Adapter for invoice payment status checking.

    This adapter does NOT use an external service — all logic is date-based
    computation within the adapter itself.
    """

    service_name = "payment_status"
    method_name = "check"
    input_schema = PaymentStatusInput
    output_schema = PaymentStatusOutput

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> PaymentStatusOutput:
        if not isinstance(input_data, PaymentStatusInput):
            input_data = PaymentStatusInput.model_validate(input_data)
        data = input_data

        status, days_until, is_overdue = _determine_payment_status(data.due_date)

        logger.info(
            "payment_status_checked",
            invoice_number=data.invoice_number,
            due_date=data.due_date,
            status=status,
            days_until_due=days_until,
        )

        return PaymentStatusOutput(
            invoice_number=data.invoice_number,
            due_date=data.due_date,
            amount=data.amount,
            payment_status=status,
            days_until_due=days_until,
            is_overdue=is_overdue,
        )


adapter_registry.register(PaymentStatusAdapter())
