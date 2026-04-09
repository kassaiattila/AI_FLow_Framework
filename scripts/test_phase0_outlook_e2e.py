#!/usr/bin/env python3
"""Fazis 0 — Outlook Multi-Account Fetch + Email Intent Classification E2E.

3 fiok emailjeinek letoltese Outlook COM-on, intent klasszifikacio,
szamla-relevans emailek kiszurese.

Hasznalat:
  python scripts/test_phase0_outlook_e2e.py [--since-days 7] [--limit 30]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


# --- Config ---
ACCOUNTS = [
    {
        "name": "bestix",
        "mailbox": "attila.kassai@bestix.hu",
        "label": "BestIx (uzleti)",
    },
    {
        "name": "kodosok",
        "mailbox": "kassaia@kodosok.hu",
        "label": "Kodosok (dev)",
    },
    {
        "name": "gmail",
        "mailbox": "jegesparos@gmail.com",
        "label": "Gmail (szemelyes)",
    },
]

RESULTS_DIR = Path("data/e2e_results/outlook_fetch")

# Invoice scoring keywords & weights
INVOICE_KEYWORDS_SUBJECT = [
    ("számla", 0.4),
    ("szamla", 0.4),
    ("invoice", 0.4),
    ("faktura", 0.3),
    ("díjbekérő", 0.3),
    ("dijbekero", 0.3),
    ("fizetési", 0.2),
    ("fizetesi", 0.2),
    ("payment", 0.2),
    ("licenc", 0.15),
    ("előfizetés", 0.15),
    ("elofizetes", 0.15),
    ("subscription", 0.15),
    ("receipt", 0.15),
    ("billing", 0.15),
]
INVOICE_KEYWORDS_BODY = [
    ("számla", 0.15),
    ("szamla", 0.15),
    ("invoice", 0.15),
    ("fizetendő", 0.1),
    ("fizetendo", 0.1),
    ("bruttó", 0.1),
    ("brutto", 0.1),
    ("nettó", 0.1),
    ("netto", 0.1),
    ("áfa", 0.1),
    ("afa", 0.1),
    ("adószám", 0.1),
    ("adoszam", 0.1),
    ("bankszámlaszám", 0.1),
    ("esedékesség", 0.08),
    ("due date", 0.08),
    ("total", 0.05),
    ("amount", 0.05),
]
INVOICE_ATTACHMENT_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".doc", ".docx"}


def score_email_for_invoice(subject: str, body: str, attachments: list[dict]) -> float:
    """Score an email for invoice relevance (0.0 - 1.0)."""
    score = 0.0
    subj_lower = subject.lower()
    body_lower = body[:3000].lower()

    for kw, weight in INVOICE_KEYWORDS_SUBJECT:
        if kw in subj_lower:
            score += weight

    for kw, weight in INVOICE_KEYWORDS_BODY:
        if kw in body_lower:
            score += weight

    # Attachment bonus
    for att in attachments:
        fname = att.get("filename", "").lower()
        ext = Path(fname).suffix
        if ext in INVOICE_ATTACHMENT_EXTENSIONS:
            score += 0.15
            # Filename contains invoice-related words
            for kw in ["szamla", "számla", "invoice", "faktura"]:
                if kw in fname:
                    score += 0.2
                    break

    return min(score, 1.0)


# ---- STEP 1: Outlook COM Fetch ----


async def fetch_account_emails(mailbox: str, name: str, since_days: int, limit: int) -> list[dict]:
    """Fetch emails from a single Outlook account via COM."""
    from aiflow.services.email_connector.service import _fetch_outlook_com_impl

    upload_dir = RESULTS_DIR / name
    upload_dir.mkdir(parents=True, exist_ok=True)

    cutoff = (datetime.now() - timedelta(days=since_days)).date()
    cfg = {"mailbox": mailbox, "filters": {"folder": "Inbox"}}

    print(f"\n{'=' * 60}")
    print(f"FETCH: {mailbox} (utolso {since_days} nap, max {limit})")
    print(f"{'=' * 60}")

    t0 = time.time()
    fetched = await _fetch_outlook_com_impl(cfg, limit, cutoff, upload_dir)
    duration = time.time() - t0

    print(f"  Letoltve: {len(fetched)} email ({duration:.1f}s)")

    emails = []
    for fe in fetched:
        emails.append(
            {
                "message_id": fe.message_id,
                "subject": fe.subject,
                "sender": fe.sender,
                "recipients": fe.recipients,
                "date": fe.date.isoformat() if fe.date else None,
                "body_text_len": len(fe.body_text),
                "body_text_preview": fe.body_text[:200],
                "attachments": [
                    {"filename": a.filename, "mime_type": a.mime_type, "size": a.size}
                    for a in fe.attachments
                ],
                "raw_eml_path": fe.raw_eml_path,
            }
        )

    return emails


# ---- STEP 2: Email Intent Classification ----


async def classify_emails(name: str, eml_dir: Path) -> list[dict]:
    """Run intent classification on .eml files in a directory."""
    from skills.email_intent_processor.workflows.classify import (
        classify_intent,
        decide_routing,
        extract_entities,
        parse_email,
        process_attachments,
        score_priority,
    )

    from aiflow.tools.email_parser import EmailParser

    eml_files = sorted(eml_dir.glob("*.eml"))
    if not eml_files:
        print(f"  Nincs .eml fajl: {eml_dir}")
        return []

    print(f"\n  INTENT CLASSIFICATION: {name} ({len(eml_files)} email)")
    print(f"  {'-' * 50}")

    parser = EmailParser()
    results = []

    for i, eml_file in enumerate(eml_files):
        try:
            parsed = parser.parse_eml(eml_file)

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

            # Extract intent
            intent_data = r3.get("intent", {})
            if isinstance(intent_data, dict):
                intent = intent_data.get("intent_id", r3.get("primary_intent", "unknown"))
                confidence = intent_data.get("confidence", 0)
                method = intent_data.get("method", "unknown")
            else:
                intent = r3.get("primary_intent", "unknown")
                confidence = r3.get("intent_confidence", 0)
                method = "unknown"

            priority_data = r5.get("priority", {})
            priority = (
                priority_data.get("priority_level", 3)
                if isinstance(priority_data, dict)
                else priority_data
            )

            entities_data = r4.get("entities", {})
            entities = entities_data.get("entities", []) if isinstance(entities_data, dict) else []
            routing_data = r6.get("routing", {})
            queue = (
                routing_data.get("queue_id", "")
                if isinstance(routing_data, dict)
                else r6.get("routed_to", "")
            )

            # Invoice score
            inv_score = score_email_for_invoice(
                parsed.subject,
                parsed.body_text,
                [{"filename": a.filename} for a in parsed.attachments],
            )

            status_icon = "OK" if confidence > 0.5 else "??"
            print(
                f"  [{i + 1:2d}/{len(eml_files)}] {status_icon} {intent:<15s} ({confidence:.0%}) inv={inv_score:.2f} | {parsed.subject[:50]}"
            )

            results.append(
                {
                    "file": eml_file.name,
                    "subject": parsed.subject,
                    "sender": parsed.from_,
                    "intent": intent,
                    "confidence": confidence,
                    "method": method,
                    "priority": priority,
                    "routing": queue,
                    "entities": [
                        {"type": e.get("type", ""), "value": e.get("value", "")} for e in entities
                    ],
                    "entity_count": len(entities),
                    "attachment_count": len(parsed.attachments),
                    "invoice_score": inv_score,
                }
            )

        except Exception as e:
            print(f"  [{i + 1:2d}/{len(eml_files)}] !! HIBA: {eml_file.name}: {e}")
            results.append({"file": eml_file.name, "error": str(e)})

    return results


# ---- MAIN ----


async def run_phase0(since_days: int = 7, limit: int = 30) -> None:
    """Execute full Phase 0 E2E test."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    print("=" * 70)
    print("FAZIS 0: Outlook Multi-Account Fetch + Email Intent Classification")
    print(f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Since: {since_days} nap | Limit/fiok: {limit}")
    print("=" * 70)

    all_results = {}
    all_emails = {}
    total_emails = 0
    total_classified = 0
    total_entities = 0
    intent_counter = Counter()
    invoice_candidates = []

    for account in ACCOUNTS:
        name = account["name"]
        mailbox = account["mailbox"]

        # Step 1: Fetch
        emails = await fetch_account_emails(mailbox, name, since_days, limit)
        all_emails[name] = emails
        total_emails += len(emails)

        # Step 2: Classify
        eml_dir = RESULTS_DIR / name
        classified = await classify_emails(name, eml_dir)
        all_results[name] = classified

        # Stats
        for r in classified:
            if "error" not in r:
                total_classified += 1
                intent_counter[r["intent"]] += 1
                total_entities += r.get("entity_count", 0)
                if r.get("invoice_score", 0) >= 0.3:
                    invoice_candidates.append(
                        {
                            "account": name,
                            "file": r["file"],
                            "subject": r["subject"],
                            "sender": r.get("sender", ""),
                            "invoice_score": r["invoice_score"],
                            "intent": r["intent"],
                            "confidence": r["confidence"],
                        }
                    )

    duration = time.time() - t_start

    # ---- Summary ----
    print(f"\n{'=' * 70}")
    print("OSSZEGZES")
    print(f"{'=' * 70}")
    print(f"  Fiokok:             {len(ACCOUNTS)}")
    print(f"  Ossz email:         {total_emails}")
    print(f"  Klasszifikalva:     {total_classified}")
    errors = sum(1 for acct in all_results.values() for r in acct if "error" in r)
    print(f"  Hibak:              {errors}")
    if total_emails > 0:
        pct = total_classified / total_emails * 100
        print(f"  Siker arany:        {pct:.1f}%")
    print(f"  Intent tipusok:     {len(intent_counter)}")
    print(f"  Entitasok:          {total_entities}")
    print(f"  Invoice candidates: {len(invoice_candidates)}")
    print(f"  Ido:                {duration:.1f}s")

    print("\n  Intent eloszlas:")
    for intent, count in intent_counter.most_common():
        print(f"    {intent:<20s}: {count}")

    if invoice_candidates:
        print("\n  Invoice candidates:")
        for ic in sorted(invoice_candidates, key=lambda x: -x["invoice_score"]):
            print(f"    [{ic['account']}] score={ic['invoice_score']:.2f} | {ic['subject'][:55]}")

    # ---- Save results ----
    for name, classified in all_results.items():
        out = RESULTS_DIR / f"{name}_emails.json"
        out.write_text(json.dumps(classified, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  Mentve: {out}")

    intent_dist = RESULTS_DIR / "intent_distribution.json"
    intent_dist.write_text(
        json.dumps(dict(intent_counter.most_common()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  Mentve: {intent_dist}")

    inv_out = RESULTS_DIR / "invoice_candidates.json"
    inv_out.write_text(
        json.dumps(invoice_candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  Mentve: {inv_out}")

    summary = {
        "date": datetime.now().isoformat(),
        "since_days": since_days,
        "limit_per_account": limit,
        "accounts": len(ACCOUNTS),
        "total_emails_fetched": total_emails,
        "total_classified": total_classified,
        "total_errors": errors,
        "success_rate_pct": round(total_classified / max(total_emails, 1) * 100, 1),
        "unique_intents": len(intent_counter),
        "total_entities": total_entities,
        "invoice_candidate_count": len(invoice_candidates),
        "duration_seconds": round(duration, 1),
        "intent_distribution": dict(intent_counter.most_common()),
        "per_account": {
            name: {
                "fetched": len(all_emails.get(name, [])),
                "classified": sum(1 for r in classified if "error" not in r),
                "errors": sum(1 for r in classified if "error" in r),
                "invoice_candidates": sum(1 for ic in invoice_candidates if ic["account"] == name),
            }
            for name, classified in all_results.items()
        },
    }
    summary_out = RESULTS_DIR / "summary.json"
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Mentve: {summary_out}")

    # ---- Success criteria check ----
    print(f"\n{'=' * 70}")
    print("SIKER KRITERIUMOK")
    print(f"{'=' * 70}")
    checks = [
        ("3/3 fiok email letoltese sikeres", all(len(all_emails[a["name"]]) > 0 for a in ACCOUNTS)),
        ("60+ email letoltve osszesen", total_emails >= 60),
        ("90%+ sikeresen klasszifikalva", total_classified / max(total_emails, 1) >= 0.9),
        ("4+ kulonbozo intent", len(intent_counter) >= 4),
        ("10+ entitas kinyerve", total_entities >= 10),
        ("2+ szamla-relevans email", len(invoice_candidates) >= 2),
        ("Eredmeny JSON-ok mentve", (RESULTS_DIR / "summary.json").exists()),
    ]
    all_pass = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {label}")

    print(f"\n  VEGEREDMENY: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    return all_pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fazis 0 — Outlook E2E teszt")
    parser.add_argument("--since-days", type=int, default=7, help="Email cutoff (napok)")
    parser.add_argument("--limit", type=int, default=30, help="Max email per fiok")
    args = parser.parse_args()

    result = asyncio.run(run_phase0(since_days=args.since_days, limit=args.limit))
    sys.exit(0 if result else 1)
