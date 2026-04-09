#!/usr/bin/env python3
"""Valos email teszt - postafiokbol szarmazo emailek feldolgozasa.

Ket hasznalati mod:
1. .eml fajlokbol: python scripts/test_email_from_inbox.py --eml-dir ./test_emails/
2. IMAP-bol: python scripts/test_email_from_inbox.py --imap --server imap.office365.com --email user@company.com

Az Azure Document Intelligence integracioval a csatolmanyokat is feldolgozza
(ha AZURE_DI_ENDPOINT es AZURE_DI_API_KEY konfiguralt a .env-ben).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


async def process_eml_files(eml_dir: str) -> None:
    """Process .eml files from a directory."""
    from skills.email_intent_processor.workflows.classify import (
        classify_intent,
        decide_routing,
        extract_entities,
        parse_email,
        process_attachments,
        score_priority,
    )

    from aiflow.tools.email_parser import EmailParser

    eml_path = Path(eml_dir)
    eml_files = sorted(eml_path.glob("*.eml"))

    if not eml_files:
        print(f"Nincs .eml fajl: {eml_dir}")
        print("Tipp: Outlook-bol exportalj emaileket .eml formatumba ebbe a mappaba.")
        return

    print("Email Intent Processor - Valos Teszt")
    print(f"Forras: {eml_dir}")
    print(f"Emailek: {len(eml_files)}")
    print(f"Azure DI: {'KONFIGURALT' if os.getenv('AZURE_DI_ENDPOINT') else 'NEM KONFIGURALT'}")
    print("=" * 60)

    parser = EmailParser()
    results = []

    for i, eml_file in enumerate(eml_files):
        print(f"\n[{i + 1}/{len(eml_files)}] {eml_file.name}")

        try:
            parsed = parser.parse_eml(eml_file)
            print(f"  From: {parsed.from_}")
            print(f"  Subject: {parsed.subject}")
            print(f"  Body: {len(parsed.body_text)} chars")
            print(f"  Attachments: {len(parsed.attachments)}")

            # Run through pipeline
            data = {
                "source": str(eml_file),
                "subject": parsed.subject,
                "body": parsed.body_text,
                "sender": parsed.from_,
                "raw_attachments": [
                    {
                        "filename": a.filename,
                        "mime_type": a.mime_type,
                        "size_bytes": a.size_bytes,
                        "content": a.content,
                    }
                    for a in parsed.attachments
                ],
            }

            r1 = await parse_email(data)
            r2 = await process_attachments(r1)
            r3 = await classify_intent(r2)
            r4 = await extract_entities(r3)
            r5 = await score_priority(r4)
            r6 = await decide_routing(r5)

            # Extract intent from nested dict structure
            intent_data = r3.get("intent", {})
            if isinstance(intent_data, dict):
                intent = intent_data.get("intent_id", r3.get("primary_intent", "unknown"))
                confidence = intent_data.get("confidence", 0)
            else:
                intent = r3.get("primary_intent", "unknown")
                confidence = r3.get("intent_confidence", 0)
            priority_data = r5.get("priority", {})
            if isinstance(priority_data, dict):
                priority = priority_data.get("priority_level", 3)
            else:
                priority = priority_data
            entities_data = r4.get("entities", {})
            entities = entities_data.get("entities", []) if isinstance(entities_data, dict) else []
            routing_data = r6.get("routing", {})
            if isinstance(routing_data, dict):
                queue = routing_data.get("queue_id", r6.get("routed_to", ""))
            else:
                queue = r6.get("routed_to", "")

            print(f"  -> Intent: {intent} ({confidence:.0%})")
            print(f"  -> Priority: {priority}/5")
            print(f"  -> Routing: {queue}")
            print(f"  -> Entities: {len(entities)}")
            for e in entities[:3]:
                print(f"     - {e.get('type', '?')}: {e.get('value', '?')}")

            results.append(
                {
                    "file": eml_file.name,
                    "subject": parsed.subject,
                    "intent": intent,
                    "confidence": confidence,
                    "priority": priority,
                    "routing": queue,
                    "entities": len(entities),
                    "attachments": len(parsed.attachments),
                }
            )

        except Exception as e:
            print(f"  !! HIBA: {e}")
            results.append({"file": eml_file.name, "error": str(e)})

    # Summary
    print(f"\n{'=' * 60}")
    print(f"OSSZEGZES: {len(results)} email feldolgozva")
    passed = sum(1 for r in results if "error" not in r)
    print(f"Sikeres: {passed}/{len(results)}")

    # Save results
    out_path = Path("test_output/email_test_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report: {out_path}")


async def fetch_from_imap(
    server: str, email_addr: str, password: str, folder: str, limit: int
) -> None:
    """Fetch emails from IMAP server and process them."""
    import email as email_lib
    import imaplib

    print(f"IMAP letoltes: {server} / {email_addr}")
    print(f"Mappa: {folder}, Limit: {limit}")

    mail = imaplib.IMAP4_SSL(server)
    mail.login(email_addr, password)
    mail.select(folder)

    _, data = mail.search(None, "ALL")
    msg_ids = data[0].split()[-limit:]  # Utolso N email

    eml_dir = Path("test_emails")
    eml_dir.mkdir(exist_ok=True)

    for mid in msg_ids:
        _, msg_data = mail.fetch(mid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw)
        subject = msg.get("Subject", "no_subject")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in subject[:50])
        eml_path = eml_dir / f"{safe_name}.eml"
        eml_path.write_bytes(raw)

    mail.logout()
    print(f"{len(msg_ids)} email mentve: {eml_dir}")

    # Process them
    await process_eml_files(str(eml_dir))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valos email teszt")
    parser.add_argument("--eml-dir", help="Mappa .eml fajlokkal")
    parser.add_argument("--imap", action="store_true", help="IMAP letoltes")
    parser.add_argument("--server", default="imap.office365.com")
    parser.add_argument("--email", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--folder", default="INBOX")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.imap:
        email_addr = args.email or os.getenv("IMAP_EMAIL", "")
        password = args.password or os.getenv("IMAP_PASSWORD", "")
        if not email_addr or not password:
            print("Szukseges: --email es --password, vagy IMAP_EMAIL + IMAP_PASSWORD a .env-ben")
            sys.exit(1)
        asyncio.run(fetch_from_imap(args.server, email_addr, password, args.folder, args.limit))
    elif args.eml_dir:
        asyncio.run(process_eml_files(args.eml_dir))
    else:
        print("Hasznalat:")
        print("  .eml fajlokbol: python scripts/test_email_from_inbox.py --eml-dir ./test_emails/")
        print(
            "  IMAP-bol:       python scripts/test_email_from_inbox.py --imap --email user@co.hu --password xxx"
        )
        print("")
        print("Elokeszites: exportalj 5-10 emailt .eml formatumba a test_emails/ mappaba")
