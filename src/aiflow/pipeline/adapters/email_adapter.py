"""Pipeline adapter for EmailConnectorService.fetch_emails."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry


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
            emails.append({
                "message_id": getattr(email, "message_id", ""),
                "subject": getattr(email, "subject", ""),
                "sender": getattr(email, "sender", ""),
                "body_text": getattr(email, "body_text", ""),
                "received_at": str(getattr(email, "received_at", "")),
                "attachments": getattr(email, "attachments", []),
            })

        return {
            "emails": emails,
            "total": len(emails),
            "connector_id": data.connector_id,
        }


adapter_registry.register(EmailFetchAdapter())
