#!/usr/bin/env python3
"""Fetch emails from ANY mailbox via IMAP.

Works with: Outlook/Exchange, Gmail, any IMAP server.
Saves emails as .eml files + attachments for processing.

Setup (.env):
    IMAP_SERVER=outlook.office365.com     # or imap.gmail.com
    IMAP_EMAIL=attila.kassai@bestix.hu
    IMAP_PASSWORD=your-app-password       # App password, NOT regular password!

For Office 365: Generate app password at https://mysignins.microsoft.com/security-info
For Gmail: Enable 2FA, then https://myaccount.google.com/apppasswords

Usage:
    python scripts/fetch_emails_imap.py --days 30 --limit 20
    python scripts/fetch_emails_imap.py --server imap.gmail.com --email x@gmail.com --folder INBOX
    python scripts/fetch_emails_imap.py --list-folders   # Show available folders
"""
from __future__ import annotations

import argparse
import email as email_lib
import imaplib
import os
import sys
from datetime import datetime, timedelta
from email import policy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


def list_folders(server: str, email_addr: str, password: str) -> None:
    """List all IMAP folders."""
    mail = imaplib.IMAP4_SSL(server)
    mail.login(email_addr, password)

    print(f"Mailbox: {email_addr} @ {server}")
    print("Folders:")
    _, folders = mail.list()
    for folder in folders:
        decoded = folder.decode("utf-8", errors="replace")
        print(f"  {decoded}")

    mail.logout()


def fetch_emails(
    server: str,
    email_addr: str,
    password: str,
    folder: str,
    days: int,
    limit: int,
    with_attachments: bool,
    output_dir: str,
) -> None:
    """Fetch emails from IMAP server."""
    print(f"IMAP Email Fetch")
    print(f"Server: {server}")
    print(f"Email: {email_addr}")
    print(f"Folder: {folder}")
    print(f"Period: last {days} days")
    print(f"Limit: {limit}")
    print(f"Attachments: {'YES' if with_attachments else 'NO'}")
    print("=" * 60)

    # Connect
    try:
        mail = imaplib.IMAP4_SSL(server, timeout=30)
        mail.login(email_addr, password)
        print("Login OK")
    except imaplib.IMAP4.error as e:
        print(f"Login FAILED: {e}")
        print("\nTipp: Hasznalj App Password-ot (nem a rendes jelszot)!")
        print("  Office 365: https://mysignins.microsoft.com/security-info")
        print("  Gmail: https://myaccount.google.com/apppasswords")
        return
    except Exception as e:
        print(f"Connection FAILED: {e}")
        return

    # Select folder
    try:
        status, data = mail.select(folder)
        if status != "OK":
            print(f"Folder nem talalhato: {folder}")
            print("Hasznald --list-folders a mappak listajahoz")
            mail.logout()
            return
        total = int(data[0])
        print(f"Folder: {folder} ({total} emails)")
    except Exception as e:
        print(f"Folder hiba: {e}")
        mail.logout()
        return

    # Search by date
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    _, msg_nums = mail.search(None, f'(SINCE "{cutoff}")')
    msg_ids = msg_nums[0].split()

    if not msg_ids:
        print(f"Nincs email az utolso {days} napbol")
        mail.logout()
        return

    # Take last N
    msg_ids = msg_ids[-limit:]
    print(f"Feldolgozando: {len(msg_ids)} email")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    att_dir = out_path / "attachments"
    att_dir.mkdir(exist_ok=True)

    count = 0
    total_att = 0

    for msg_id in reversed(msg_ids):  # Newest first
        try:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw, policy=policy.default)

            subject = str(msg.get("Subject", "no_subject") or "no_subject")
            sender = str(msg.get("From", ""))
            date_str = str(msg.get("Date", ""))

            # Parse date for filename
            try:
                from email.utils import parsedate_to_datetime
                recv_dt = parsedate_to_datetime(date_str)
                file_date = recv_dt.strftime("%Y%m%d_%H%M")
            except Exception:
                file_date = "nodate"

            # Safe filename
            safe_subject = "".join(
                c if c.isalnum() or c in "-_ " else "_" for c in subject[:50]
            ).strip()
            base_name = f"{file_date}_{safe_subject}"

            # Save raw .eml
            eml_path = out_path / f"{base_name}.eml"
            eml_path.write_bytes(raw)

            # Extract and save attachments separately
            att_count = 0
            if with_attachments and msg.is_multipart():
                for part in msg.walk():
                    cd = str(part.get("Content-Disposition", ""))
                    filename = part.get_filename()
                    if "attachment" in cd or (filename and not filename.startswith("image0")):
                        content = part.get_payload(decode=True)
                        if content and filename:
                            safe_att = "".join(
                                c if c.isalnum() or c in "-_." else "_" for c in filename
                            )
                            att_path = att_dir / f"{base_name}_{safe_att}"
                            att_path.write_bytes(content)
                            att_count += 1
                            total_att += 1

            # Extract sender email address
            sender_email = sender
            if "<" in sender and ">" in sender:
                sender_email = sender[sender.index("<")+1:sender.index(">")]

            print(f"  [{count+1}] {file_date} | {sender_email[:30]:30} | {att_count} att | {subject[:45]}")
            count += 1

        except Exception as e:
            print(f"  !! Hiba: {e}")

    mail.logout()

    print(f"\n{'=' * 60}")
    print(f"KESZ: {count} email, {total_att} csatolmany")
    print(f"Output: {out_path}")
    print(f"\nKovetkezo lepes:")
    print(f"  python scripts/test_email_from_inbox.py --eml-dir {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IMAP email fetcher")
    parser.add_argument("--server", default=os.getenv("IMAP_SERVER", "outlook.office365.com"))
    parser.add_argument("--email", default=os.getenv("IMAP_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("IMAP_PASSWORD", ""))
    parser.add_argument("--folder", default="INBOX")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--with-attachments", action="store_true", default=True)
    parser.add_argument("--output", default="./test_emails/imap")
    parser.add_argument("--list-folders", action="store_true")
    args = parser.parse_args()

    if not args.email:
        args.email = input("Email cim: ")
    if not args.password:
        import getpass
        args.password = getpass.getpass("Jelszo (app password): ")

    if args.list_folders:
        list_folders(args.server, args.email, args.password)
    else:
        fetch_emails(
            args.server, args.email, args.password,
            args.folder, args.days, args.limit,
            args.with_attachments, args.output,
        )
