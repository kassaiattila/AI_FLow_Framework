#!/usr/bin/env python3
"""Fetch emails from Outlook via COM interface and save as .eml files.

Reads from the running Outlook instance (must be open).
Exports emails + attachments to test_emails/ directory.

Usage:
    python scripts/fetch_outlook_emails.py --folder Inbox --days 7 --limit 20
    python scripts/fetch_outlook_emails.py --account attila.kassai@bestix.hu --days 30 --limit 10
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def fetch_emails(account_filter: str, folder_name: str, days: int, limit: int, output_dir: str) -> None:
    """Fetch emails from Outlook COM interface."""
    import win32com.client

    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    # Find the right account/store
    target_folder = None

    if account_filter:
        # Search in specific account
        for store in outlook.Stores:
            if account_filter.lower() in store.DisplayName.lower():
                try:
                    root = store.GetRootFolder()
                    for folder in root.Folders:
                        if folder_name.lower() in folder.Name.lower():
                            target_folder = folder
                            print(f"Account: {store.DisplayName}")
                            print(f"Folder: {folder.Name}")
                            break
                except Exception:
                    continue
            if target_folder:
                break
    else:
        # Default inbox
        target_folder = outlook.GetDefaultFolder(6)  # 6 = Inbox
        print(f"Default Inbox")

    if not target_folder:
        print(f"Folder not found: {folder_name} in {account_filter}")
        print("Available stores:")
        for store in outlook.Stores:
            print(f"  - {store.DisplayName}")
        return

    # Filter by date
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff_date.strftime("%m/%d/%Y")

    items = target_folder.Items
    items.Sort("[ReceivedTime]", True)  # Newest first
    items = items.Restrict(f"[ReceivedTime] >= '{cutoff_str}'")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Also create attachments subdir
    attach_dir = out_path / "attachments"
    attach_dir.mkdir(exist_ok=True)

    count = 0
    total_attachments = 0

    print(f"Idoszak: utolso {days} nap ({cutoff_str}-tol)")
    print(f"Limit: {limit}")
    print(f"Output: {out_path}")
    print("=" * 60)

    for item in items:
        if count >= limit:
            break

        try:
            subject = getattr(item, "Subject", "no_subject") or "no_subject"
            sender = getattr(item, "SenderEmailAddress", "") or ""
            received = getattr(item, "ReceivedTime", None)
            body = getattr(item, "Body", "") or ""
            html_body = getattr(item, "HTMLBody", "") or ""

            # Safe filename
            safe_subject = "".join(c if c.isalnum() or c in "-_ " else "_" for c in subject[:60]).strip()
            date_str = received.strftime("%Y%m%d_%H%M") if received else "nodate"
            base_name = f"{date_str}_{safe_subject}"

            # Save email body as text
            email_path = out_path / f"{base_name}.txt"
            with open(email_path, "w", encoding="utf-8") as f:
                f.write(f"From: {sender}\n")
                f.write(f"Subject: {subject}\n")
                f.write(f"Date: {received}\n")
                f.write(f"---\n")
                f.write(body)

            # Save as .eml using MIME
            try:
                eml_path = out_path / f"{base_name}.eml"
                # Use SaveAs with olMSG format then convert, or build EML manually
                import email
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart

                msg = MIMEMultipart()
                msg["From"] = sender
                msg["To"] = getattr(item, "To", "") or ""
                msg["Subject"] = subject
                msg["Date"] = str(received) if received else ""

                # Body
                msg.attach(MIMEText(body, "plain", "utf-8"))

                # Attachments
                attachments = getattr(item, "Attachments", None)
                if attachments:
                    for i in range(1, attachments.Count + 1):
                        att = attachments.Item(i)
                        att_name = att.FileName or f"attachment_{i}"
                        att_path = attach_dir / f"{base_name}_{att_name}"
                        try:
                            att.SaveAsFile(str(att_path))
                            total_attachments += 1

                            # Add to EML
                            from email.mime.base import MIMEBase
                            from email import encoders
                            with open(att_path, "rb") as af:
                                part = MIMEBase("application", "octet-stream")
                                part.set_payload(af.read())
                                encoders.encode_base64(part)
                                part.add_header("Content-Disposition", f"attachment; filename={att_name}")
                                msg.attach(part)
                        except Exception as e:
                            print(f"  !! Attachment hiba: {att_name}: {e}")

                eml_path.write_bytes(msg.as_bytes())

            except Exception as e:
                print(f"  !! EML mentes hiba: {e}")

            att_count = attachments.Count if attachments else 0
            print(f"  [{count+1}] {date_str} | {subject[:50]} | {att_count} csatolmany")
            count += 1

        except Exception as e:
            print(f"  !! Email hiba: {e}")
            continue

    print(f"\n{'=' * 60}")
    print(f"KESZ: {count} email exportalva")
    print(f"Csatolmanyok: {total_attachments}")
    print(f"Output: {out_path}")
    print(f"\nKovetkezo lepes:")
    print(f"  python scripts/test_email_from_inbox.py --eml-dir {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outlook email export")
    parser.add_argument("--account", default="bestix", help="Account filter (e.g. bestix, aam)")
    parser.add_argument("--folder", default="Inbox", help="Folder name")
    parser.add_argument("--days", type=int, default=7, help="Last N days")
    parser.add_argument("--limit", type=int, default=20, help="Max emails")
    parser.add_argument("--output", default="./test_emails", help="Output directory")
    args = parser.parse_args()
    fetch_emails(args.account, args.folder, args.days, args.limit, args.output)
