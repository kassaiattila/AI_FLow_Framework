#!/usr/bin/env python3
"""Fetch emails from Microsoft 365 via Microsoft Graph API.

More robust than win32com - cross-platform, doesn't need Outlook running.

Setup:
1. Register an app in Azure AD (portal.azure.com -> App registrations)
2. Grant permissions: Mail.Read, Mail.ReadBasic
3. Generate client secret
4. Set env vars in .env:
   GRAPH_TENANT_ID=your-tenant-id
   GRAPH_CLIENT_ID=your-app-id
   GRAPH_CLIENT_SECRET=your-secret
   GRAPH_USER_EMAIL=attila.kassai@bestix.hu

Usage:
    python scripts/fetch_emails_graph.py --days 30 --limit 20
    python scripts/fetch_emails_graph.py --days 7 --limit 10 --with-attachments
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def get_access_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get OAuth2 token via client credentials flow."""
    import httpx

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, data=data)
        if resp.status_code != 200:
            raise RuntimeError(f"Token error {resp.status_code}: {resp.text[:200]}")
        return resp.json()["access_token"]


async def fetch_emails(
    days: int, limit: int, with_attachments: bool, output_dir: str
) -> None:
    """Fetch emails from Microsoft Graph API."""
    import httpx

    tenant_id = os.getenv("GRAPH_TENANT_ID", "")
    client_id = os.getenv("GRAPH_CLIENT_ID", "")
    client_secret = os.getenv("GRAPH_CLIENT_SECRET", "")
    user_email = os.getenv("GRAPH_USER_EMAIL", "")

    if not all([tenant_id, client_id, client_secret, user_email]):
        print("Szukseges .env valtozok:")
        print("  GRAPH_TENANT_ID=xxx")
        print("  GRAPH_CLIENT_ID=xxx")
        print("  GRAPH_CLIENT_SECRET=xxx")
        print("  GRAPH_USER_EMAIL=attila.kassai@bestix.hu")
        print("")
        print("Setup: https://learn.microsoft.com/en-us/graph/auth-v2-service")
        return

    print(f"Microsoft Graph API Email Fetch")
    print(f"User: {user_email}")
    print(f"Period: last {days} days")
    print(f"Limit: {limit}")
    print(f"Attachments: {'YES' if with_attachments else 'NO'}")
    print("=" * 60)

    # Get access token
    token = await get_access_token(tenant_id, client_id, client_secret)
    print("Token OK")

    # Fetch emails
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = (
        f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
        f"?$filter=receivedDateTime ge {cutoff}"
        f"&$top={limit}"
        f"&$orderby=receivedDateTime desc"
        f"&$select=id,subject,from,receivedDateTime,body,hasAttachments"
    )

    headers = {"Authorization": f"Bearer {token}"}
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    att_dir = out_path / "attachments"
    att_dir.mkdir(exist_ok=True)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Graph API error {resp.status_code}: {resp.text[:300]}")
            return

        messages = resp.json().get("value", [])
        print(f"Emails: {len(messages)}")

        for i, msg in enumerate(messages):
            subject = msg.get("subject", "no_subject") or "no_subject"
            sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
            received = msg.get("receivedDateTime", "")
            body_content = msg.get("body", {}).get("content", "")
            body_type = msg.get("body", {}).get("contentType", "text")
            has_att = msg.get("hasAttachments", False)

            # Convert HTML body to text
            if body_type == "html":
                import re
                body_text = re.sub(r"<[^>]+>", "", body_content)
                body_text = re.sub(r"\s+", " ", body_text).strip()
            else:
                body_text = body_content

            # Save as .eml
            safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in subject[:50]).strip()
            date_str = received[:10].replace("-", "") if received else "nodate"
            base = f"{date_str}_{safe}"

            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            eml = MIMEMultipart()
            eml["From"] = sender
            eml["Subject"] = subject
            eml["Date"] = received
            eml.attach(MIMEText(body_text, "plain", "utf-8"))

            # Fetch attachments
            att_count = 0
            if has_att and with_attachments:
                att_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{msg['id']}/attachments"
                att_resp = await client.get(att_url, headers=headers)
                if att_resp.status_code == 200:
                    for att in att_resp.json().get("value", []):
                        att_name = att.get("name", f"att_{att_count}")
                        att_bytes = att.get("contentBytes", "")
                        if att_bytes:
                            import base64
                            content = base64.b64decode(att_bytes)
                            att_path = att_dir / f"{base}_{att_name}"
                            att_path.write_bytes(content)
                            att_count += 1

                            from email.mime.base import MIMEBase
                            from email import encoders
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(content)
                            encoders.encode_base64(part)
                            part.add_header("Content-Disposition", f"attachment; filename={att_name}")
                            eml.attach(part)

            eml_path = out_path / f"{base}.eml"
            eml_path.write_bytes(eml.as_bytes())

            print(f"  [{i+1}] {date_str} | {sender[:30]:30} | {att_count} att | {subject[:45]}")

    print(f"\nKESZ: {len(messages)} email -> {out_path}")
    print(f"\nKovetkezo:")
    print(f"  python scripts/test_email_from_inbox.py --eml-dir {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Microsoft Graph API email fetch")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--with-attachments", action="store_true")
    parser.add_argument("--output", default="./test_emails/graph")
    args = parser.parse_args()
    asyncio.run(fetch_emails(args.days, args.limit, args.with_attachments, args.output))
