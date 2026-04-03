"""Audit logging helper — fire-and-forget audit entries for API actions."""
import structlog

__all__ = ["audit_log"]

logger = structlog.get_logger(__name__)

_service = None


def _get_service():
    global _service
    if _service is None:
        from aiflow.services.audit import AuditTrailService
        _service = AuditTrailService()
    return _service


async def audit_log(
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Log an audit event. Best-effort — never raises."""
    try:
        svc = _get_service()
        await svc.log(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    except Exception as e:
        logger.warning("audit_log_failed", error=str(e), action=action)
