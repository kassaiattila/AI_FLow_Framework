"""Pipeline adapters for EmailConnectorService (fetch_emails + search_invoices)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

logger = structlog.get_logger(__name__)


class FetchEmailsInput(BaseModel):
    """Input schema for email fetch operation."""

    connector_id: str = Field(..., description="Email connector config ID")
    limit: int = Field(50, description="Max emails to fetch")
    since_days: int | None = Field(None, description="Fetch emails from last N days")


class FetchedEmailOutput(BaseModel):
    """Single email in the output."""

    message_id: str = ""
    subject: str = ""
    sender: str = ""
    body_text: str = ""
    received_at: str = ""
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class FetchEmailsOutput(BaseModel):
    """Output schema for email fetch operation."""

    emails: list[FetchedEmailOutput] = Field(default_factory=list)
    total: int = 0
    connector_id: str = ""


class EmailFetchAdapter(BaseAdapter):
    """Adapter wrapping EmailConnectorService.fetch_emails for pipeline use."""

    service_name = "email_connector"
    method_name = "fetch_emails"
    input_schema = FetchEmailsInput
    output_schema = FetchEmailsOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.email_connector.service import (
            EmailConnectorConfig,
            EmailConnectorService,
        )

        sf = await get_session_factory()
        svc = EmailConnectorService(session_factory=sf, config=EmailConnectorConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, FetchEmailsInput):
            input_data = FetchEmailsInput.model_validate(input_data)
        data = input_data
        svc = await self._get_service()

        since_date = None
        if data.since_days is not None:
            from datetime import timedelta

            since_date = date.today() - timedelta(days=data.since_days)

        result = await svc.fetch_emails(
            config_id=data.connector_id,
            limit=data.limit,
            since_date=since_date,
        )

        emails = []
        for email in result.emails:
            emails.append(
                {
                    "message_id": getattr(email, "message_id", ""),
                    "subject": getattr(email, "subject", ""),
                    "sender": getattr(email, "sender", ""),
                    "body_text": getattr(email, "body_text", ""),
                    "received_at": str(getattr(email, "received_at", "")),
                    "attachments": getattr(email, "attachments", []),
                }
            )

        return {
            "emails": emails,
            "total": len(emails),
            "connector_id": data.connector_id,
        }


adapter_registry.register(EmailFetchAdapter())


# ---------------------------------------------------------------------------
# Invoice search adapter — keyword + attachment scoring
# ---------------------------------------------------------------------------

# Default keyword sets for invoice detection
SUBJECT_KEYWORDS: set[str] = {
    "szamla",
    "invoice",
    "számla",
    "fizetesi",
    "payment",
    "faktura",
    "szla",
    "fizetési",
}
BODY_KEYWORDS: set[str] = {
    "fizetendo",
    "hatarido",
    "osszeg",
    "netto",
    "brutto",
    "due date",
    "total amount",
    "áfa",
    "vat",
    "fizetendő",
    "határidő",
    "összeg",
    "nettó",
    "bruttó",
}
ATTACHMENT_PATTERNS: list[str] = [
    r"szamla.*\.pdf",
    r"számla.*\.pdf",
    r"invoice.*\.pdf",
    r"szla.*\.pdf",
    r"faktura.*\.pdf",
]


def _score_email_for_invoice(
    subject: str,
    body_text: str,
    attachment_names: list[str],
) -> float:
    """Score an email's relevance as an invoice carrier (0.0–1.0).

    Scoring:
    - Subject keyword match: +0.15 per keyword (max 0.45)
    - Body keyword match: +0.05 per keyword (max 0.30)
    - PDF attachment: +0.15
    - Invoice-pattern attachment name: +0.10
    """
    score = 0.0
    subject_lower = subject.lower()
    body_lower = body_text[:2000].lower()

    # Subject keyword matches
    subject_hits = sum(1 for kw in SUBJECT_KEYWORDS if kw in subject_lower)
    score += min(subject_hits * 0.15, 0.45)

    # Body keyword matches
    body_hits = sum(1 for kw in BODY_KEYWORDS if kw in body_lower)
    score += min(body_hits * 0.05, 0.30)

    # Attachment scoring
    for att_name in attachment_names:
        att_lower = att_name.lower()
        if att_lower.endswith(".pdf"):
            score += 0.15
            # Pattern match bonus
            for pattern in ATTACHMENT_PATTERNS:
                if re.search(pattern, att_lower):
                    score += 0.10
                    break
            break  # Only score first PDF attachment

    return min(score, 1.0)


class SearchInvoicesInput(BaseModel):
    """Input schema for invoice-focused email search."""

    connector_id: str = Field(..., description="Email connector config ID")
    limit: int = Field(50, description="Max emails to scan")
    since_days: int | None = Field(30, description="Scan emails from last N days")
    relevance_threshold: float = Field(0.3, description="Minimum score to include email")


class InvoiceEmailResult(BaseModel):
    """Single email result from invoice search."""

    email_id: str = ""
    subject: str = ""
    sender: str = ""
    date: str = ""
    score: float = 0.0
    has_attachment: bool = False
    attachment_names: list[str] = Field(default_factory=list)
    body_snippet: str = ""


class SearchInvoicesOutput(BaseModel):
    """Output schema for invoice email search."""

    emails: list[InvoiceEmailResult] = Field(default_factory=list)
    total_scanned: int = 0
    total_matched: int = 0
    connector_id: str = ""


class EmailSearchInvoicesAdapter(BaseAdapter):
    """Adapter for invoice-focused mailbox scanning.

    Reuses EmailConnectorService.fetch_emails, then applies keyword-based
    relevance scoring to filter for potential invoice emails.
    """

    service_name = "email_connector"
    method_name = "search_invoices"
    input_schema = SearchInvoicesInput
    output_schema = SearchInvoicesOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.email_connector.service import (
            EmailConnectorConfig,
            EmailConnectorService,
        )

        sf = await get_session_factory()
        svc = EmailConnectorService(session_factory=sf, config=EmailConnectorConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, SearchInvoicesInput):
            input_data = SearchInvoicesInput.model_validate(input_data)
        data = input_data
        svc = await self._get_service()

        since_date = None
        if data.since_days is not None:
            from datetime import timedelta

            since_date = date.today() - timedelta(days=data.since_days)

        result = await svc.fetch_emails(
            config_id=data.connector_id,
            limit=data.limit,
            since_date=since_date,
        )

        matched: list[dict[str, Any]] = []
        total_scanned = len(result.emails)

        for email in result.emails:
            subject = getattr(email, "subject", "")
            body_text = getattr(email, "body_text", "")
            attachments = getattr(email, "attachments", [])

            att_names = []
            for att in attachments:
                if isinstance(att, dict):
                    att_names.append(att.get("filename", att.get("name", "")))
                else:
                    att_names.append(getattr(att, "filename", getattr(att, "name", "")))

            score = _score_email_for_invoice(subject, body_text, att_names)

            if score >= data.relevance_threshold:
                matched.append(
                    {
                        "email_id": getattr(email, "message_id", ""),
                        "subject": subject,
                        "sender": getattr(email, "sender", ""),
                        "date": str(getattr(email, "received_at", "")),
                        "score": round(score, 3),
                        "has_attachment": len(att_names) > 0,
                        "attachment_names": att_names,
                        "body_snippet": body_text[:200],
                    }
                )

        # Sort by score descending
        matched.sort(key=lambda x: x["score"], reverse=True)

        logger.info(
            "search_invoices_complete",
            total_scanned=total_scanned,
            total_matched=len(matched),
            connector_id=data.connector_id,
        )

        return {
            "emails": matched,
            "total_scanned": total_scanned,
            "total_matched": len(matched),
            "connector_id": data.connector_id,
        }


adapter_registry.register(EmailSearchInvoicesAdapter())
