"""Email Connector service — configurable multi-provider email fetching.

Generalizes email_intent_processor into a config-driven connector service.
Supports IMAP, O365 Graph API, and Gmail providers.

Pipeline: connect → authenticate → fetch → parse → save .eml → record history
"""

from __future__ import annotations

import asyncio
import email as email_stdlib
import imaplib
import json
import time
from datetime import date, datetime
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "ConnectorProvider",
    "FetchedEmail",
    "FetchResult",
    "EmailConnectorConfig",
    "EmailConnectorService",
]

logger = structlog.get_logger(__name__)


class ConnectorProvider(str, Enum):
    """Supported email connector providers."""

    IMAP = "imap"
    O365_GRAPH = "o365_graph"
    GMAIL = "gmail"
    OUTLOOK_COM = "outlook_com"  # Local Outlook via COM/MAPI (Windows only)


class EmailAttachment(BaseModel):
    """A single email attachment.

    file_path is populated when the fetch backend saves the attachment to disk
    (Outlook COM + IMAP), allowing downstream pipeline steps to read the file
    directly. Empty string if the attachment wasn't saved (e.g., Graph API
    placeholder).
    """

    filename: str = ""
    mime_type: str = ""
    size: int = 0
    file_path: str = ""


class FetchedEmail(BaseModel):
    """A single fetched email message."""

    message_id: str = ""
    subject: str = ""
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)
    date: datetime | None = None
    body_text: str = ""
    body_html: str = ""
    attachments: list[EmailAttachment] = Field(default_factory=list)
    raw_eml_path: str | None = None


class FetchResult(BaseModel):
    """Result of a fetch operation."""

    emails: list[FetchedEmail] = Field(default_factory=list)
    total_count: int = 0
    new_count: int = 0
    duration_ms: float = 0.0
    error: str | None = None


class EmailConnectorConfig(ServiceConfig):
    """Service-level config for the Email Connector."""

    upload_dir: str = "./data/emails"


class EmailConnectorService(BaseService):
    """Configurable email connector service.

    Supports IMAP, O365 Graph API, and Gmail providers.
    Connector configurations are stored in the DB (email_connector_configs table).
    Each fetch operation is recorded in email_fetch_history.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        config: EmailConnectorConfig | None = None,
    ) -> None:
        self._ext_config = config or EmailConnectorConfig()
        self._session_factory = session_factory
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "email_connector"

    @property
    def service_description(self) -> str:
        return "Configurable multi-provider email connector (IMAP, O365 Graph, Gmail)"

    async def _start(self) -> None:
        Path(self._ext_config.upload_dir).mkdir(parents=True, exist_ok=True)

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        try:
            async with self._session_factory() as session:
                r = await session.execute(text("SELECT 1"))
                return r.scalar() == 1
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Config CRUD
    # -------------------------------------------------------------------------

    async def list_configs(self) -> list[dict[str, Any]]:
        """List all connector configurations from the DB."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, name, provider, host, port, use_ssl,
                           mailbox, credentials_encrypted, filters,
                           polling_interval_minutes, max_emails_per_fetch,
                           is_active, last_fetched_at, created_at, updated_at
                    FROM email_connector_configs
                    ORDER BY name
                """)
            )
            return [self._row_to_config_dict(row) for row in result.fetchall()]

    async def get_config(self, config_id: str) -> dict[str, Any] | None:
        """Get a single connector config by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, name, provider, host, port, use_ssl,
                           mailbox, credentials_encrypted, filters,
                           polling_interval_minutes, max_emails_per_fetch,
                           is_active, last_fetched_at, created_at, updated_at
                    FROM email_connector_configs
                    WHERE id = CAST(:id AS uuid)
                """),
                {"id": config_id},
            )
            row = result.fetchone()
            return self._row_to_config_dict(row) if row else None

    async def create_config(
        self,
        *,
        name: str,
        provider: str,
        host: str | None = None,
        port: int | None = None,
        use_ssl: bool = True,
        mailbox: str | None = None,
        credentials_encrypted: str | None = None,
        filters: dict[str, Any] | None = None,
        polling_interval: int = 15,
        max_emails: int = 50,
    ) -> dict[str, Any]:
        """Create a new connector configuration."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO email_connector_configs
                        (name, provider, host, port, use_ssl, mailbox,
                         credentials_encrypted, filters,
                         polling_interval_minutes, max_emails_per_fetch)
                    VALUES
                        (:name, :provider, :host, :port, :use_ssl, :mailbox,
                         :credentials_encrypted, CAST(:filters AS jsonb),
                         :polling_interval, :max_emails)
                    RETURNING id
                """),
                {
                    "name": name,
                    "provider": provider,
                    "host": host,
                    "port": port,
                    "use_ssl": use_ssl,
                    "mailbox": mailbox,
                    "credentials_encrypted": credentials_encrypted,
                    "filters": json.dumps(filters or {}),
                    "polling_interval": polling_interval,
                    "max_emails": max_emails,
                },
            )
            row = result.fetchone()
            await session.commit()
            config_id = str(row[0]) if row else None
            self._logger.info("connector_config_created", name=name, id=config_id)
            return await self.get_config(config_id)  # type: ignore[return-value]

    async def update_config(self, config_id: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a connector configuration. Only provided kwargs are updated."""
        # Build SET clause dynamically from provided kwargs
        allowed_fields = {
            "name",
            "provider",
            "host",
            "port",
            "use_ssl",
            "mailbox",
            "credentials_encrypted",
            "filters",
            "polling_interval_minutes",
            "max_emails_per_fetch",
            "is_active",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return await self.get_config(config_id)

        set_parts = []
        params: dict[str, Any] = {"id": config_id}
        for field_name, value in updates.items():
            if field_name == "filters":
                set_parts.append(f"{field_name} = CAST(:{field_name} AS jsonb)")
                params[field_name] = json.dumps(value)
            else:
                set_parts.append(f"{field_name} = :{field_name}")
                params[field_name] = value

        set_parts.append("updated_at = NOW()")
        set_clause = ", ".join(set_parts)

        async with self._session_factory() as session:
            await session.execute(
                text(f"""
                    UPDATE email_connector_configs
                    SET {set_clause}
                    WHERE id = CAST(:id AS uuid)
                """),  # noqa: S608
                params,
            )
            await session.commit()
            self._logger.info(
                "connector_config_updated",
                config_id=config_id,
                fields=list(updates.keys()),
            )
            return await self.get_config(config_id)

    async def delete_config(self, config_id: str) -> bool:
        """Delete a connector configuration (cascades to fetch history)."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    DELETE FROM email_connector_configs
                    WHERE id = CAST(:id AS uuid)
                """),
                {"id": config_id},
            )
            await session.commit()
            deleted = result.rowcount > 0
            self._logger.info("connector_config_deleted", config_id=config_id, deleted=deleted)
            return deleted

    # -------------------------------------------------------------------------
    # Connection test
    # -------------------------------------------------------------------------

    async def test_connection(self, config_id: str) -> dict[str, Any]:
        """Test connectivity for a configured connector.

        Returns {"success": bool, "message": str, "provider": str}.
        """
        cfg = await self.get_config(config_id)
        if not cfg:
            return {"success": False, "message": "Config not found", "provider": ""}

        provider = cfg["provider"]
        try:
            if provider == ConnectorProvider.IMAP.value:
                result = await self._test_imap_connection(cfg)
            elif provider == ConnectorProvider.O365_GRAPH.value:
                result = await self._test_o365_connection(cfg)
            elif provider == ConnectorProvider.OUTLOOK_COM.value:
                result = await self._test_outlook_com_connection(cfg)
            elif provider == ConnectorProvider.GMAIL.value:
                return {
                    "success": False,
                    "message": "Gmail provider not yet implemented",
                    "provider": provider,
                }
            else:
                return {
                    "success": False,
                    "message": f"Unknown provider: {provider}",
                    "provider": provider,
                }
            return {**result, "provider": provider}
        except Exception as exc:
            self._logger.error(
                "connection_test_failed",
                config_id=config_id,
                error=str(exc),
            )
            return {"success": False, "message": str(exc), "provider": provider}

    # -------------------------------------------------------------------------
    # Email fetching
    # -------------------------------------------------------------------------

    async def fetch_emails(
        self,
        config_id: str,
        limit: int = 50,
        since_date: date | None = None,
    ) -> FetchResult:
        """Fetch emails using the configured provider.

        Steps:
        1. Load config from DB
        2. Record fetch start in email_fetch_history
        3. Connect to provider and fetch messages
        4. Parse each message and save as .eml
        5. Update fetch history with result
        """
        start = time.time()
        cfg = await self.get_config(config_id)
        if not cfg:
            return FetchResult(error="Config not found")

        # Record fetch start
        history_id = await self._record_fetch_start(config_id)

        provider = cfg["provider"]
        try:
            if provider == ConnectorProvider.IMAP.value:
                fetched = await self._fetch_imap(cfg, limit, since_date)
            elif provider == ConnectorProvider.O365_GRAPH.value:
                fetched = await self._fetch_o365(cfg, limit, since_date)
            elif provider == ConnectorProvider.OUTLOOK_COM.value:
                fetched = await self._fetch_outlook_com(cfg, limit, since_date)
            elif provider == ConnectorProvider.GMAIL.value:
                raise NotImplementedError("Gmail provider not yet implemented")
            else:
                raise ValueError(f"Unknown provider: {provider}")

            elapsed = (time.time() - start) * 1000
            result = FetchResult(
                emails=fetched,
                total_count=len(fetched),
                new_count=len(fetched),
                duration_ms=elapsed,
            )

            # Update fetch history and last_fetched_at
            await self._record_fetch_complete(history_id, config_id, result)
            self._logger.info(
                "emails_fetched",
                config_id=config_id,
                provider=provider,
                count=len(fetched),
                time_ms=round(elapsed),
            )
            return result

        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            error_msg = str(exc)
            await self._record_fetch_failed(history_id, error_msg, elapsed)
            self._logger.error(
                "email_fetch_failed",
                config_id=config_id,
                provider=provider,
                error=error_msg,
            )
            return FetchResult(error=error_msg, duration_ms=elapsed)

    # -------------------------------------------------------------------------
    # Fetch history
    # -------------------------------------------------------------------------

    async def get_fetch_history(self, config_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get fetch history for a connector configuration."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, config_id, status, email_count, new_emails,
                           duration_ms, error, fetched_at
                    FROM email_fetch_history
                    WHERE config_id = CAST(:config_id AS uuid)
                    ORDER BY fetched_at DESC
                    LIMIT :limit
                """),
                {"config_id": config_id, "limit": limit},
            )
            return [
                {
                    "id": str(row[0]),
                    "config_id": str(row[1]),
                    "status": row[2],
                    "email_count": row[3],
                    "new_emails": row[4],
                    "duration_ms": row[5],
                    "error": row[6],
                    "fetched_at": str(row[7]) if row[7] else None,
                }
                for row in result.fetchall()
            ]

    # =========================================================================
    # IMAP provider implementation
    # =========================================================================

    async def _test_imap_connection(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Test IMAP connectivity in a thread (imaplib is blocking)."""

        def _test() -> dict[str, Any]:
            host = cfg.get("host", "")
            port = cfg.get("port") or (993 if cfg.get("use_ssl") else 143)
            credentials = cfg.get("credentials_encrypted", "")

            if not host:
                return {"success": False, "message": "Host not configured"}
            if not credentials:
                return {"success": False, "message": "Credentials not configured"}

            # Parse credentials (expected format: "username:password")
            parts = credentials.split(":", 1)
            if len(parts) != 2:
                return {
                    "success": False,
                    "message": "Invalid credentials format (expected user:password)",
                }

            username, password = parts

            try:
                if cfg.get("use_ssl", True):
                    conn = imaplib.IMAP4_SSL(host, port)
                else:
                    conn = imaplib.IMAP4(host, port)

                conn.login(username, password)
                mailbox = cfg.get("mailbox") or "INBOX"
                status, _data = conn.select(mailbox, readonly=True)
                conn.logout()

                if status == "OK":
                    return {
                        "success": True,
                        "message": f"Connected to {host}:{port}, mailbox '{mailbox}' accessible",
                    }
                return {
                    "success": False,
                    "message": f"Could not select mailbox '{mailbox}'",
                }
            except imaplib.IMAP4.error as exc:
                msg = f"IMAP error: {exc}"
                if "LOGIN failed" in str(exc) and "office365" in host.lower():
                    msg += " — Microsoft 365 disabled basic auth in 2022. Use the O365 Graph API provider instead (provider='o365_graph' with tenant_id:client_id:client_secret:user_email credentials)."
                return {"success": False, "message": msg}

        return await asyncio.to_thread(_test)

    async def _fetch_imap(
        self,
        cfg: dict[str, Any],
        limit: int,
        since_date: date | None,
    ) -> list[FetchedEmail]:
        """Fetch emails via IMAP in a background thread."""

        upload_dir = Path(self._ext_config.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        def _fetch() -> list[FetchedEmail]:
            host = cfg.get("host", "")
            port = cfg.get("port") or (993 if cfg.get("use_ssl") else 143)
            credentials = cfg.get("credentials_encrypted", "")
            mailbox = cfg.get("mailbox") or "INBOX"
            filters = cfg.get("filters") or {}

            if not host or not credentials:
                raise ValueError("IMAP host and credentials are required")

            parts = credentials.split(":", 1)
            if len(parts) != 2:
                raise ValueError("Invalid credentials format (expected user:password)")
            username, password = parts

            # Connect
            if cfg.get("use_ssl", True):
                conn = imaplib.IMAP4_SSL(host, port)
            else:
                conn = imaplib.IMAP4(host, port)

            conn.login(username, password)
            conn.select(mailbox, readonly=True)

            # Build search criteria
            criteria = _build_imap_search_criteria(since_date, filters)
            _status, msg_numbers = conn.search(None, *criteria)

            if not msg_numbers or not msg_numbers[0]:
                conn.logout()
                return []

            # Parse message IDs and apply limit
            ids = msg_numbers[0].split()
            # Take the most recent N messages (last in the list)
            ids = ids[-limit:]

            emails: list[FetchedEmail] = []
            for msg_id in ids:
                try:
                    _status, msg_data = conn.fetch(msg_id, "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue
                    raw_bytes = msg_data[0][1]  # type: ignore[index]
                    if not isinstance(raw_bytes, bytes):
                        continue

                    parsed = _parse_email_message(raw_bytes)

                    # Save .eml file
                    safe_id = (
                        (parsed.message_id or str(msg_id))
                        .replace("/", "_")
                        .replace("\\", "_")
                        .replace("<", "")
                        .replace(">", "")[:80]
                    )
                    eml_path = upload_dir / f"{safe_id}.eml"
                    eml_path.write_bytes(raw_bytes)
                    parsed.raw_eml_path = str(eml_path)

                    emails.append(parsed)
                except Exception as exc:
                    logger.warning(
                        "imap_message_parse_failed",
                        msg_id=str(msg_id),
                        error=str(exc),
                    )

            conn.logout()
            return emails

        return await asyncio.to_thread(_fetch)

    # =========================================================================
    # Outlook COM/MAPI provider (Windows — local Outlook)
    # =========================================================================

    async def _test_outlook_com_connection(self, cfg: dict[str, Any]) -> dict[str, Any]:
        return await _test_outlook_com_connection_impl(cfg)

    async def _fetch_outlook_com(
        self, cfg: dict[str, Any], limit: int, since_date: date | None
    ) -> list[FetchedEmail]:
        upload_dir = Path(self._ext_config.upload_dir) / "outlook"
        return await _fetch_outlook_com_impl(cfg, limit, since_date, upload_dir)

    # =========================================================================
    # O365 Graph API provider implementation
    # =========================================================================

    async def _test_o365_connection(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Test O365 Graph API connectivity."""
        try:
            import httpx
        except ImportError:
            return {
                "success": False,
                "message": "httpx not installed (required for O365 Graph provider)",
            }

        credentials = cfg.get("credentials_encrypted", "")
        if not credentials:
            return {"success": False, "message": "Credentials not configured"}

        # Parse O365 credentials (format: "tenant_id:client_id:client_secret:user_email")
        parts = credentials.split(":", 3)
        if len(parts) != 4:
            return {
                "success": False,
                "message": "Invalid O365 credentials format "
                "(expected tenant_id:client_id:client_secret:user_email)",
            }

        tenant_id, client_id, client_secret, user_email = parts

        try:
            token = await self._get_o365_token(tenant_id, client_id, client_secret)
            if not token:
                return {"success": False, "message": "Failed to obtain access token"}

            # Test with a simple messages query
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://graph.microsoft.com/v1.0/users/{user_email}/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"$top": "1", "$select": "id"},
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Connected to O365 Graph API for {user_email}",
                    }
                return {
                    "success": False,
                    "message": f"Graph API returned {resp.status_code}: {resp.text[:200]}",
                }
        except Exception as exc:
            return {"success": False, "message": f"O365 connection error: {exc}"}

    async def _fetch_o365(
        self,
        cfg: dict[str, Any],
        limit: int,
        since_date: date | None,
    ) -> list[FetchedEmail]:
        """Fetch emails via Microsoft Graph API."""
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "httpx is required for O365 Graph provider. Install with: uv pip install httpx"
            ) from exc

        credentials = cfg.get("credentials_encrypted", "")
        parts = credentials.split(":", 3)
        if len(parts) != 4:
            raise ValueError(
                "Invalid O365 credentials format "
                "(expected tenant_id:client_id:client_secret:user_email)"
            )
        tenant_id, client_id, client_secret, user_email = parts

        token = await self._get_o365_token(tenant_id, client_id, client_secret)
        if not token:
            raise RuntimeError("Failed to obtain O365 access token")

        upload_dir = Path(self._ext_config.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Build query params
        params: dict[str, str] = {
            "$top": str(limit),
            "$select": "id,subject,from,toRecipients,receivedDateTime,"
            "body,bodyPreview,hasAttachments",
            "$orderby": "receivedDateTime desc",
        }

        # Add date filter
        if since_date:
            iso_date = since_date.isoformat()
            params["$filter"] = f"receivedDateTime ge {iso_date}T00:00:00Z"

        # Apply config filters
        filters = cfg.get("filters") or {}
        if filters.get("unread_only"):
            existing_filter = params.get("$filter", "")
            unread_clause = "isRead eq false"
            if existing_filter:
                params["$filter"] = f"{existing_filter} and {unread_clause}"
            else:
                params["$filter"] = unread_clause

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://graph.microsoft.com/v1.0/users/{user_email}/messages",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

        messages = data.get("value", [])
        emails: list[FetchedEmail] = []
        for msg in messages:
            try:
                fetched = _parse_o365_message(msg)

                # For O365, we don't have raw .eml, but store the JSON
                safe_id = msg.get("id", "")[:80].replace("/", "_").replace("\\", "_")
                json_path = upload_dir / f"{safe_id}.json"
                json_path.write_text(json.dumps(msg, default=str), encoding="utf-8")
                fetched.raw_eml_path = str(json_path)

                emails.append(fetched)
            except Exception as exc:
                logger.warning(
                    "o365_message_parse_failed",
                    msg_id=msg.get("id", ""),
                    error=str(exc),
                )

        return emails

    async def _get_o365_token(
        self, tenant_id: str, client_id: str, client_secret: str
    ) -> str | None:
        """Obtain OAuth2 access token using client_credentials flow."""
        import httpx

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json().get("access_token")
            logger.error(
                "o365_token_failed",
                status=resp.status_code,
                body=resp.text[:300],
            )
            return None

    # =========================================================================
    # Fetch history helpers
    # =========================================================================

    async def _record_fetch_start(self, config_id: str) -> str | None:
        """Insert a pending fetch history record and return its ID."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    text("""
                        INSERT INTO email_fetch_history (config_id, status)
                        VALUES (CAST(:config_id AS uuid), 'running')
                        RETURNING id
                    """),
                    {"config_id": config_id},
                )
                row = result.fetchone()
                await session.commit()
                return str(row[0]) if row else None
        except Exception as exc:
            self._logger.error("record_fetch_start_failed", error=str(exc))
            return None

    async def _record_fetch_complete(
        self,
        history_id: str | None,
        config_id: str,
        result: FetchResult,
    ) -> None:
        """Update fetch history with success and update last_fetched_at."""
        try:
            async with self._session_factory() as session:
                if history_id:
                    await session.execute(
                        text("""
                            UPDATE email_fetch_history
                            SET status = 'completed',
                                email_count = :count,
                                new_emails = :new_count,
                                duration_ms = :duration_ms
                            WHERE id = CAST(:id AS uuid)
                        """),
                        {
                            "id": history_id,
                            "count": result.total_count,
                            "new_count": result.new_count,
                            "duration_ms": result.duration_ms,
                        },
                    )
                # Update last_fetched_at on the config
                await session.execute(
                    text("""
                        UPDATE email_connector_configs
                        SET last_fetched_at = NOW(), updated_at = NOW()
                        WHERE id = CAST(:id AS uuid)
                    """),
                    {"id": config_id},
                )
                await session.commit()
        except Exception as exc:
            self._logger.error("record_fetch_complete_failed", error=str(exc))

    async def _record_fetch_failed(
        self,
        history_id: str | None,
        error: str,
        duration_ms: float,
    ) -> None:
        """Update fetch history with failure."""
        if not history_id:
            return
        try:
            async with self._session_factory() as session:
                await session.execute(
                    text("""
                        UPDATE email_fetch_history
                        SET status = 'failed',
                            error = :error,
                            duration_ms = :duration_ms
                        WHERE id = CAST(:id AS uuid)
                    """),
                    {
                        "id": history_id,
                        "error": error[:2000],
                        "duration_ms": duration_ms,
                    },
                )
                await session.commit()
        except Exception as exc:
            self._logger.error("record_fetch_failed_error", error=str(exc))

    # =========================================================================
    # Row mapping helper
    # =========================================================================

    @staticmethod
    def _row_to_config_dict(row: Any) -> dict[str, Any]:
        """Convert a DB row to a config dict."""
        return {
            "id": str(row[0]),
            "name": row[1],
            "provider": row[2],
            "host": row[3] or "",
            "port": row[4],
            "use_ssl": row[5],
            "mailbox": row[6] or "",
            "credentials_encrypted": row[7] or "",
            "filters": row[8] or {},
            "polling_interval_minutes": row[9],
            "max_emails_per_fetch": row[10],
            "is_active": row[11],
            "last_fetched_at": str(row[12]) if row[12] else None,
            "created_at": str(row[13]) if row[13] else "",
            "updated_at": str(row[14]) if row[14] else "",
            "source": "backend",
        }


# =============================================================================
# Module-level helper functions (used by provider implementations)
# =============================================================================


def _build_imap_search_criteria(
    since_date: date | None,
    filters: dict[str, Any],
) -> list[str]:
    """Build IMAP SEARCH criteria from filters."""
    criteria: list[str] = []

    if since_date:
        # IMAP date format: DD-Mon-YYYY
        date_str = since_date.strftime("%d-%b-%Y")
        criteria.append(f"SINCE {date_str}")

    if filters.get("unread_only"):
        criteria.append("UNSEEN")

    if filters.get("from"):
        criteria.append(f'FROM "{filters["from"]}"')

    if filters.get("subject"):
        criteria.append(f'SUBJECT "{filters["subject"]}"')

    # Default: all messages
    if not criteria:
        criteria.append("ALL")

    return criteria


def _decode_header_value(value: str | None) -> str:
    """Decode a potentially encoded email header value."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result_parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result_parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result_parts.append(str(part))
    return " ".join(result_parts)


def _parse_email_message(raw_bytes: bytes) -> FetchedEmail:
    """Parse raw email bytes into a FetchedEmail model."""
    msg = email_stdlib.message_from_bytes(raw_bytes)

    # Message ID
    message_id = msg.get("Message-ID", "") or ""

    # Subject
    subject = _decode_header_value(msg.get("Subject"))

    # Sender
    _name, sender_addr = parseaddr(msg.get("From", ""))
    sender = sender_addr or _decode_header_value(msg.get("From"))

    # Recipients
    recipients: list[str] = []
    for header in ("To", "Cc"):
        raw = msg.get(header, "")
        if raw:
            # Simple split — handles "Name <email>, Name <email>" format
            for addr in raw.split(","):
                _n, a = parseaddr(addr.strip())
                if a:
                    recipients.append(a)

    # Date
    msg_date: datetime | None = None
    raw_date = msg.get("Date")
    if raw_date:
        try:
            msg_date = parsedate_to_datetime(raw_date)
        except Exception:
            pass

    # Body
    body_text = ""
    body_html = ""
    attachments: list[EmailAttachment] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                attachments.append(
                    EmailAttachment(
                        filename=part.get_filename() or "unknown",
                        mime_type=content_type,
                        size=len(part.get_payload(decode=True) or b""),
                    )
                )
            elif content_type == "text/plain" and not body_text:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")
            elif content_type == "text/html" and not body_html:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_html = payload.decode(charset, errors="replace")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if content_type == "text/html":
                body_html = decoded
            else:
                body_text = decoded

    return FetchedEmail(
        message_id=message_id,
        subject=subject,
        sender=sender,
        recipients=recipients,
        date=msg_date,
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
    )


def _parse_o365_message(msg: dict[str, Any]) -> FetchedEmail:
    """Parse a Microsoft Graph API message JSON into a FetchedEmail."""
    # Sender
    from_obj = msg.get("from", {}).get("emailAddress", {})
    sender = from_obj.get("address", "")

    # Recipients
    recipients = [
        r.get("emailAddress", {}).get("address", "")
        for r in msg.get("toRecipients", [])
        if r.get("emailAddress", {}).get("address")
    ]

    # Date
    msg_date: datetime | None = None
    raw_date = msg.get("receivedDateTime")
    if raw_date:
        try:
            msg_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except Exception:
            pass

    # Body
    body_obj = msg.get("body", {})
    body_type = body_obj.get("contentType", "text")
    body_content = body_obj.get("content", "")

    body_text = ""
    body_html = ""
    if body_type.lower() == "html":
        body_html = body_content
    else:
        body_text = body_content

    # Note: attachment details require a separate Graph API call;
    # we only know hasAttachments at this point.
    attachments: list[EmailAttachment] = []
    if msg.get("hasAttachments"):
        attachments.append(
            EmailAttachment(
                filename="(attachments present — fetch separately)",
                mime_type="unknown",
                size=0,
            )
        )

    return FetchedEmail(
        message_id=msg.get("id", ""),
        subject=msg.get("subject", ""),
        sender=sender,
        recipients=recipients,
        date=msg_date,
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
    )


# ---------------------------------------------------------------------------
# Outlook COM/MAPI provider (Windows only — requires running Outlook)
# ---------------------------------------------------------------------------


async def _test_outlook_com_connection_impl(cfg: dict[str, Any]) -> dict[str, Any]:
    """Test Outlook COM connection (blocking, runs in thread)."""
    import sys

    if sys.platform != "win32":
        return {"success": False, "message": "Outlook COM only available on Windows"}

    def _test() -> dict[str, Any]:
        try:
            import pythoncom

            pythoncom.CoInitialize()
        except Exception:
            pass
        try:
            import win32com.client
        except ImportError:
            return {"success": False, "message": "pywin32 not installed (pip install pywin32)"}

        try:
            outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            stores = []
            for store in outlook.Stores:
                stores.append(store.DisplayName)
            if not stores:
                return {"success": False, "message": "No Outlook accounts found"}

            account = cfg.get("mailbox") or cfg.get("credentials_encrypted") or ""
            matched = None
            for s in stores:
                if account.lower() in s.lower() if account else True:
                    matched = s
                    break

            if matched:
                return {
                    "success": True,
                    "message": f"Connected to Outlook — account: {matched}",
                    "folders": stores,
                }
            return {
                "success": True,
                "message": f"Outlook connected. Available: {', '.join(stores)}",
                "folders": stores,
            }
        except Exception as e:
            return {"success": False, "message": f"Outlook COM error: {e}"}

    return await asyncio.to_thread(_test)


async def _fetch_outlook_com_impl(
    cfg: dict[str, Any],
    limit: int,
    since_date: date | None,
    upload_dir: Path,
) -> list[FetchedEmail]:
    """Fetch emails from local Outlook via COM/MAPI."""
    import sys

    if sys.platform != "win32":
        raise RuntimeError("Outlook COM only available on Windows")

    def _fetch() -> list[FetchedEmail]:
        try:
            import pythoncom

            pythoncom.CoInitialize()
        except Exception:
            pass
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        import win32com.client

        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

        # Find account by mailbox/credentials field
        account_filter = cfg.get("mailbox") or cfg.get("credentials_encrypted") or ""
        folder_name = (
            cfg.get("filters", {}).get("folder", "Inbox")
            if isinstance(cfg.get("filters"), dict)
            else "Inbox"
        )

        # Localized inbox folder names (EN, HU, DE, FR, ES, IT, NL, PL, CZ)
        inbox_aliases = {
            "inbox",
            "beérkezett üzenetek",
            "beerkezett uzenetek",
            "posteingang",
            "boîte de réception",
            "bandeja de entrada",
            "posta in arrivo",
            "postvak in",
            "skrzynka odbiorcza",
            "doručená pošta",
        }

        target_folder = None
        if account_filter:
            for store in outlook.Stores:
                if account_filter.lower() in store.DisplayName.lower():
                    try:
                        root = store.GetRootFolder()
                        for folder in root.Folders:
                            fname = folder.Name.lower()
                            if folder_name.lower() in fname or fname in inbox_aliases:
                                target_folder = folder
                                break
                        if not target_folder:
                            # Fallback: use store's default Inbox (olFolderInbox=6)
                            try:
                                target_folder = store.GetDefaultFolder(6)
                            except Exception:
                                pass
                    except Exception:
                        continue
                if target_folder:
                    break

        if not target_folder:
            target_folder = outlook.GetDefaultFolder(6)  # 6 = Inbox

        # Date filter
        from datetime import datetime as dt
        from datetime import timedelta

        cutoff = since_date or (dt.now() - timedelta(days=7)).date()
        cutoff_str = cutoff.strftime("%m/%d/%Y")

        items = target_folder.Items
        items.Sort("[ReceivedTime]", True)
        items = items.Restrict(f"[ReceivedTime] >= '{cutoff_str}'")

        upload_dir.mkdir(parents=True, exist_ok=True)
        attach_dir = upload_dir / "attachments"
        attach_dir.mkdir(exist_ok=True)

        results: list[FetchedEmail] = []
        count = 0

        for item in items:
            if count >= limit:
                break
            try:
                subject = getattr(item, "Subject", "no_subject") or "no_subject"
                sender = getattr(item, "SenderEmailAddress", "") or ""
                received = getattr(item, "ReceivedTime", None)
                body = getattr(item, "Body", "") or ""
                html_body = getattr(item, "HTMLBody", "") or ""
                msg_id = getattr(item, "EntryID", "") or ""

                # Safe filename
                safe_subject = "".join(
                    c if c.isalnum() or c in "-_ " else "_" for c in subject[:60]
                ).strip()
                date_str = received.strftime("%Y%m%d_%H%M") if received else "nodate"
                base_name = f"{date_str}_{safe_subject}"

                # Build .eml
                msg = MIMEMultipart()
                msg["From"] = sender
                msg["To"] = getattr(item, "To", "") or ""
                msg["Subject"] = subject
                msg["Date"] = str(received) if received else ""
                msg.attach(MIMEText(body, "plain", "utf-8"))

                # Attachments
                att_list: list[EmailAttachment] = []
                attachments_com = getattr(item, "Attachments", None)
                if attachments_com:
                    for i in range(1, attachments_com.Count + 1):
                        att = attachments_com.Item(i)
                        att_name = att.FileName or f"attachment_{i}"
                        att_path = attach_dir / f"{base_name}_{att_name}"
                        try:
                            att.SaveAsFile(str(att_path))
                            att_list.append(
                                EmailAttachment(
                                    filename=att_name,
                                    mime_type="application/octet-stream",
                                    size=att_path.stat().st_size if att_path.exists() else 0,
                                    file_path=str(att_path) if att_path.exists() else "",
                                )
                            )
                            with open(att_path, "rb") as af:
                                part = MIMEBase("application", "octet-stream")
                                part.set_payload(af.read())
                                encoders.encode_base64(part)
                                part.add_header(
                                    "Content-Disposition", f"attachment; filename={att_name}"
                                )
                                msg.attach(part)
                        except Exception:
                            pass

                # Save .eml
                eml_path = upload_dir / f"{base_name}.eml"
                eml_path.write_bytes(msg.as_bytes())

                received_dt = None
                if received:
                    try:
                        received_dt = dt(
                            received.year,
                            received.month,
                            received.day,
                            received.hour,
                            received.minute,
                            received.second,
                        )
                    except Exception:
                        pass

                results.append(
                    FetchedEmail(
                        message_id=msg_id,
                        subject=subject,
                        sender=sender,
                        recipients=[
                            r.strip()
                            for r in (getattr(item, "To", "") or "").split(";")
                            if r.strip()
                        ],
                        date=received_dt,
                        body_text=body,
                        body_html=html_body,
                        attachments=att_list,
                        raw_eml_path=str(eml_path),
                    )
                )
                count += 1
            except Exception as e:
                logger.warning("outlook_com_item_error", error=str(e))
                continue

        return results

    return await asyncio.to_thread(_fetch)
