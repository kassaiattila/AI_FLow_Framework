"""Pipeline adapter for NotificationService.send."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

if TYPE_CHECKING:
    from aiflow.core.context import ExecutionContext


class NotifySendInput(BaseModel):
    """Input schema for notification send."""

    channel: str = Field("email", description="Channel type: email, slack, webhook, in_app")
    template: str = Field(..., description="Jinja2 template string or template name")
    data: dict[str, Any] = Field(default_factory=dict, description="Template variables")
    recipients: list[str] = Field(default_factory=list, description="Recipient list")
    config_name: str | None = Field(None, description="Pre-configured channel name")
    subject: str | None = Field(None, description="Notification subject")


class NotifySendOutput(BaseModel):
    """Output schema for notification send."""

    sent_count: int = 0
    failed_count: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)


class NotificationSendAdapter(BaseAdapter):
    """Adapter wrapping NotificationService.send for pipeline use."""

    service_name = "notification"
    method_name = "send"
    input_schema = NotifySendInput
    output_schema = NotifySendOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.notification.service import (
            NotificationConfig,
            NotificationService,
        )

        sf = await get_session_factory()
        svc = NotificationService(session_factory=sf, config=NotificationConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, NotifySendInput):
            input_data = NotifySendInput.model_validate(input_data)
        data = input_data

        # Allow config overrides from pipeline step config
        channel = config.get("channel", data.channel)
        template = config.get("template", data.template)
        subject = config.get("subject", data.subject)
        config_name = config.get("config_name", data.config_name)
        recipients = config.get("recipients", data.recipients)
        tmpl_data = {**data.data, **config.get("data", {})}

        svc = await self._get_service()

        pipeline_run_id = None
        if ctx and hasattr(ctx, "run_id"):
            pipeline_run_id = str(ctx.run_id) if ctx.run_id else None

        results = await svc.send(
            channel=channel,
            template=template,
            data=tmpl_data,
            recipients=recipients,
            config_name=config_name,
            subject=subject,
            pipeline_run_id=pipeline_run_id,
        )

        result_dicts = [
            {
                "channel": r.channel,
                "sent": r.sent,
                "message_id": r.message_id,
                "recipient": r.recipient,
                "error": r.error,
            }
            for r in results
        ]

        sent = sum(1 for r in results if r.sent)
        failed = sum(1 for r in results if not r.sent)

        return {
            "sent_count": sent,
            "failed_count": failed,
            "results": result_dicts,
        }


adapter_registry.register(NotificationSendAdapter())
