"""Email parser - extract headers, body, and attachments from .eml/.msg files."""
from __future__ import annotations

import email
import email.policy
from email import message_from_bytes, message_from_string
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
import structlog

__all__ = ["EmailParser", "ParsedEmail", "EmailAttachment"]
logger = structlog.get_logger(__name__)


class EmailAttachment(BaseModel):
    filename: str
    mime_type: str = ""
    size_bytes: int = 0
    content: bytes = b""  # Raw content

    class Config:
        arbitrary_types_allowed = True


class ParsedEmail(BaseModel):
    message_id: str = ""
    from_: str = ""
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    subject: str = ""
    date: str = ""
    body_text: str = ""
    body_html: str = ""
    attachments: list[EmailAttachment] = Field(default_factory=list)
    in_reply_to: str = ""
    references: list[str] = Field(default_factory=list)
    thread_id: str = ""  # Derived from In-Reply-To/References


class EmailParser:
    """Parse .eml files and extract structured data."""

    def parse_eml(self, source: str | Path | bytes) -> ParsedEmail:
        """Parse an .eml file or raw email bytes."""
        # Handle file path, raw bytes, or string
        if isinstance(source, (str, Path)) and Path(source).exists():
            raw = Path(source).read_bytes()
        elif isinstance(source, bytes):
            raw = source
        elif isinstance(source, str):
            # Raw email text
            msg = message_from_string(source, policy=email.policy.default)
            return self._extract(msg)
        else:
            raise ValueError(f"Cannot parse: {type(source)}")

        msg = message_from_bytes(raw, policy=email.policy.default)
        return self._extract(msg)

    def parse_text(self, subject: str, body: str, sender: str = "") -> ParsedEmail:
        """Create ParsedEmail from raw text (no .eml file)."""
        return ParsedEmail(
            subject=subject,
            body_text=body,
            from_=sender,
        )

    def _extract(self, msg: Any) -> ParsedEmail:
        """Extract all fields from an email.message.EmailMessage."""
        # Headers
        from_ = str(msg.get("From", ""))
        to = [a.strip() for a in str(msg.get("To", "")).split(",") if a.strip()]
        cc = [a.strip() for a in str(msg.get("Cc", "")).split(",") if a.strip()]
        subject = str(msg.get("Subject", ""))
        date = str(msg.get("Date", ""))
        message_id = str(msg.get("Message-ID", ""))
        in_reply_to = str(msg.get("In-Reply-To", ""))
        references = [
            r.strip() for r in str(msg.get("References", "")).split() if r.strip()
        ]

        # Body
        body_text = ""
        body_html = ""
        attachments: list[EmailAttachment] = []

        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                cd = str(part.get("Content-Disposition", ""))

                if "attachment" in cd or part.get_filename():
                    # Attachment
                    content = part.get_payload(decode=True) or b""
                    attachments.append(
                        EmailAttachment(
                            filename=part.get_filename() or "unnamed",
                            mime_type=ct,
                            size_bytes=len(content),
                            content=content,
                        )
                    )
                elif ct == "text/plain" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="replace")
                elif ct == "text/html" and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode("utf-8", errors="replace")
        else:
            ct = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode("utf-8", errors="replace")
                if ct == "text/html":
                    body_html = text
                else:
                    body_text = text

        # Convert HTML to text if no plain text body
        if not body_text and body_html:
            try:
                import html2text

                body_text = html2text.html2text(body_html)
            except ImportError:
                # Simple fallback: strip HTML tags
                import re

                body_text = re.sub(r"<[^>]+>", "", body_html)

        # Thread ID from In-Reply-To or first Reference
        thread_id = in_reply_to or (references[0] if references else message_id)

        result = ParsedEmail(
            message_id=message_id,
            from_=from_,
            to=to,
            cc=cc,
            subject=subject,
            date=date,
            body_text=body_text.strip(),
            body_html=body_html,
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=references,
            thread_id=thread_id,
        )
        logger.info(
            "email_parsed",
            subject=subject[:50],
            attachments=len(attachments),
            body_len=len(body_text),
        )
        return result
