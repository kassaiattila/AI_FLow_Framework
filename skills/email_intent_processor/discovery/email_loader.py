"""Email loader - load and parse .eml files for intent discovery.

Recursively scans a directory for .eml files, decodes MIME content
(including base64 bodies), and returns structured DiscoveryEmail objects.
"""
from __future__ import annotations

import email as email_stdlib
from email import policy
from pathlib import Path

import structlog
from pydantic import BaseModel

__all__ = ["DiscoveryEmail", "load_emails_from_dir"]

logger = structlog.get_logger(__name__)


class DiscoveryEmail(BaseModel):
    """Parsed email for intent discovery."""

    file_path: str
    subject: str = ""
    body: str = ""
    sender: str = ""
    date: str = ""
    language_hint: str = "hu"  # "hu" or "en"


def load_emails_from_dir(email_dir: Path) -> list[DiscoveryEmail]:
    """Load all .eml files from a directory recursively.

    Args:
        email_dir: Directory to scan for .eml files.

    Returns:
        List of parsed DiscoveryEmail objects.

    Raises:
        FileNotFoundError: If email_dir does not exist.
        ValueError: If no .eml files found.
    """
    email_dir = Path(email_dir)
    if not email_dir.exists():
        raise FileNotFoundError(f"Email directory not found: {email_dir}")

    eml_files = sorted(email_dir.rglob("*.eml"))
    if not eml_files:
        raise ValueError(f"No .eml files found in {email_dir}")

    results: list[DiscoveryEmail] = []
    for eml_path in eml_files:
        try:
            parsed = _parse_eml_file(eml_path)
            results.append(parsed)
        except Exception as exc:
            logger.warning("email_loader.parse_error", file=str(eml_path), error=str(exc))

    logger.info("email_loader.done", total_files=len(eml_files), parsed=len(results))
    return results


def _parse_eml_file(eml_path: Path) -> DiscoveryEmail:
    """Parse a single .eml file into a DiscoveryEmail."""
    with open(eml_path, "rb") as f:
        msg = email_stdlib.message_from_binary_file(f, policy=policy.default)

    subject = msg["subject"] or ""
    sender = msg["from"] or ""
    date = str(msg["date"] or "")

    # Extract plain text body (handles base64, quoted-printable, etc.)
    body = ""
    text_part = msg.get_body(preferencelist=("plain",))
    if text_part:
        body = text_part.get_content()
    else:
        # Fallback: try HTML with basic tag stripping
        html_part = msg.get_body(preferencelist=("html",))
        if html_part:
            import re

            html = html_part.get_content()
            body = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
            body = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL)
            body = re.sub(r"<[^>]+>", " ", body)
            body = re.sub(r"&nbsp;", " ", body)
            body = re.sub(r"\s+", " ", body).strip()

    # Detect language hint
    language_hint = _detect_language(body)

    return DiscoveryEmail(
        file_path=str(eml_path),
        subject=subject,
        body=body[:10000],  # Truncate very long bodies
        sender=sender,
        date=date,
        language_hint=language_hint,
    )


def _detect_language(text: str) -> str:
    """Simple language detection based on Hungarian accented characters."""
    if not text:
        return "unknown"

    hungarian_chars = set("áéíóöőúüűÁÉÍÓÖŐÚÜŰ")
    hu_count = sum(1 for c in text if c in hungarian_chars)
    total_alpha = sum(1 for c in text if c.isalpha())

    if total_alpha == 0:
        return "unknown"

    hu_ratio = hu_count / total_alpha
    if hu_ratio > 0.02:  # 2%+ accented chars → likely Hungarian
        return "hu"
    return "en"
