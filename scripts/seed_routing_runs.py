"""Seed the ``routing_runs`` table with a deterministic mix of rows for
live-testing the SX-3 admin page.

Usage::

    PYTHONPATH=src .venv/Scripts/python.exe scripts/seed_routing_runs.py
    # → wipes existing test rows for the seed tenant, inserts 12 fresh ones.

    PYTHONPATH=src .venv/Scripts/python.exe scripts/seed_routing_runs.py --extra 1
    # → appends N additional success rows (used by Test 11 — Refresh).

The script is idempotent for the **default** seed: it deletes every row
under the seed tenants before re-seeding so re-running the script gives
exactly the same final state. The ``--extra`` mode is *additive* (no
delete) so the Refresh test can witness the row-count delta.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from typing import Any

import asyncpg

DEFAULT_DSN = "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev"

SEED_TENANT_DEFAULT = "default"
SEED_TENANT_OTHER = "other-tenant"

TRUNCATED_FILENAME_MARKER = "truncated_marker.pdf"


def _wide_attachments(n: int = 80, blob_size: int = 200) -> list[dict[str, Any]]:
    """Build a metadata payload that exceeds the 8 KB cap.

    The first attachment carries :data:`TRUNCATED_FILENAME_MARKER` so the
    Playwright spec can locate this row by inspecting the cropped
    metadata that survives truncation.
    """
    items = [
        {
            "attachment_id": str(0),
            "filename": TRUNCATED_FILENAME_MARKER,
            "doctype_detected": "hu_invoice",
            "doctype_confidence": 0.93,
            "extraction_path": "invoice_processor",
            "extraction_outcome": "succeeded",
            "cost_usd": 0.004,
            "latency_ms": 200.0,
            "blob": "x" * blob_size,
        }
    ]
    items.extend(
        {
            "attachment_id": str(i),
            "filename": f"line_item_{i}.pdf",
            "doctype_detected": "hu_invoice",
            "doctype_confidence": 0.91,
            "extraction_path": "invoice_processor",
            "extraction_outcome": "succeeded",
            "cost_usd": 0.001,
            "latency_ms": 50.0,
            "blob": "y" * blob_size,
        }
        for i in range(1, n)
    )
    return items


def _build_seed_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # 5 × hu_invoice / success / invoice_processor
    for i, (cost, latency) in enumerate(
        [(0.001, 120), (0.004, 235), (0.006, 310), (0.009, 420), (0.012, 480)]
    ):
        rows.append(
            dict(
                tenant_id=SEED_TENANT_DEFAULT,
                doctype_detected="hu_invoice",
                doctype_confidence=0.90 + 0.01 * i,
                extraction_path="invoice_processor",
                extraction_outcome="success",
                cost_usd=cost,
                latency_ms=latency,
                metadata={
                    "attachments": [
                        {
                            "filename": f"invoice_{i:03d}.pdf",
                            "extraction_path": "invoice_processor",
                            "extraction_outcome": "succeeded",
                        }
                    ]
                },
            )
        )

    # 2 × hu_id_card / success / doc_recognizer_workflow
    for i, (cost, latency) in enumerate([(0.003, 280), (0.005, 360)]):
        rows.append(
            dict(
                tenant_id=SEED_TENANT_DEFAULT,
                doctype_detected="hu_id_card",
                doctype_confidence=0.88 + 0.02 * i,
                extraction_path="doc_recognizer_workflow",
                extraction_outcome="success",
                cost_usd=cost,
                latency_ms=latency,
                metadata={
                    "attachments": [
                        {
                            "filename": f"id_card_{i:03d}.jpg",
                            "extraction_path": "doc_recognizer_workflow",
                            "extraction_outcome": "succeeded",
                        }
                    ]
                },
            )
        )

    # 1 × hu_invoice / partial / multi-attachment
    rows.append(
        dict(
            tenant_id=SEED_TENANT_DEFAULT,
            doctype_detected="hu_invoice",
            doctype_confidence=0.85,
            extraction_path="invoice_processor",
            extraction_outcome="partial",
            cost_usd=0.007,
            latency_ms=440,
            metadata={
                "attachments": [
                    {
                        "filename": "good_invoice.pdf",
                        "extraction_path": "invoice_processor",
                        "extraction_outcome": "succeeded",
                    },
                    {
                        "filename": "bad_invoice.pdf",
                        "extraction_path": "invoice_processor",
                        "extraction_outcome": "failed",
                        "error": "parser timeout",
                    },
                ]
            },
        )
    )

    # 1 × NULL doctype / failed (fallback policy hit)
    rows.append(
        dict(
            tenant_id=SEED_TENANT_DEFAULT,
            doctype_detected=None,
            doctype_confidence=None,
            extraction_path="invoice_processor",
            extraction_outcome="failed",
            cost_usd=0.0,
            latency_ms=85,
            metadata={
                "flag_off": True,
                "attachments": [
                    {
                        "filename": "unknown.pdf",
                        "extraction_path": "invoice_processor",
                        "extraction_outcome": "failed",
                        "error": "doctype below threshold",
                    }
                ],
            },
        )
    )

    # 1 × NULL doctype / refused_cost
    rows.append(
        dict(
            tenant_id=SEED_TENANT_DEFAULT,
            doctype_detected=None,
            doctype_confidence=None,
            extraction_path="invoice_processor",
            extraction_outcome="refused_cost",
            cost_usd=0.0,
            latency_ms=10,
            metadata={
                "flag_off": True,
                "attachments": [
                    {
                        "filename": "expensive.pdf",
                        "extraction_path": "invoice_processor",
                        "extraction_outcome": "refused_cost",
                    }
                ],
            },
        )
    )

    # 1 × NULL doctype / skipped (extraction disabled)
    rows.append(
        dict(
            tenant_id=SEED_TENANT_DEFAULT,
            doctype_detected=None,
            doctype_confidence=None,
            extraction_path="skipped",
            extraction_outcome="skipped",
            cost_usd=None,
            latency_ms=None,
            metadata={"reason": "extraction_disabled_or_no_files"},
        )
    )

    # 1 × hu_invoice / success / TRUNCATED metadata
    rows.append(
        dict(
            tenant_id=SEED_TENANT_DEFAULT,
            doctype_detected="hu_invoice",
            doctype_confidence=0.95,
            extraction_path="invoice_processor",
            extraction_outcome="success",
            cost_usd=0.005,
            latency_ms=300,
            metadata={"attachments": _wide_attachments(n=80, blob_size=200)},
        )
    )

    # 1 × cross-tenant row (other-tenant)
    rows.append(
        dict(
            tenant_id=SEED_TENANT_OTHER,
            doctype_detected="hu_invoice",
            doctype_confidence=0.92,
            extraction_path="invoice_processor",
            extraction_outcome="success",
            cost_usd=0.004,
            latency_ms=200,
            metadata={
                "attachments": [
                    {
                        "filename": "tenant_isolation_proof.pdf",
                        "extraction_path": "invoice_processor",
                        "extraction_outcome": "succeeded",
                    }
                ]
            },
        )
    )

    return rows


async def _connect(dsn: str) -> asyncpg.Connection:
    return await asyncpg.connect(dsn, timeout=10)


async def _truncate(conn: asyncpg.Connection) -> int:
    deleted = await conn.execute(
        "DELETE FROM routing_runs WHERE tenant_id = ANY($1::text[])",
        [SEED_TENANT_DEFAULT, SEED_TENANT_OTHER],
    )
    # asyncpg returns "DELETE <count>" — split for the count
    try:
        return int(deleted.split()[-1])
    except (ValueError, IndexError):
        return 0


async def _insert_one(conn: asyncpg.Connection, row: dict[str, Any]) -> uuid.UUID:
    """Use the repository's cap helper so truncation is enforced exactly
    like the orchestrator hook would do."""
    from aiflow.services.routing_runs.repository import _cap_metadata

    metadata, _truncated_count = _cap_metadata(row.get("metadata"))
    metadata_json = json.dumps(metadata) if metadata is not None else None

    run_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO routing_runs (
            id, tenant_id, email_id, intent_class,
            doctype_detected, doctype_confidence,
            extraction_path, extraction_outcome,
            cost_usd, latency_ms, metadata
        ) VALUES (
            $1, $2, $3, 'EXTRACT', $4, $5, $6, $7, $8, $9, $10::jsonb
        )
        """,
        run_id,
        row["tenant_id"],
        uuid.uuid4(),
        row.get("doctype_detected"),
        row.get("doctype_confidence"),
        row["extraction_path"],
        row["extraction_outcome"],
        row.get("cost_usd"),
        row.get("latency_ms"),
        metadata_json,
    )
    return run_id


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dsn",
        default=DEFAULT_DSN,
        help="PostgreSQL DSN (raw asyncpg form).",
    )
    parser.add_argument(
        "--extra",
        type=int,
        default=0,
        help="Append N extra success rows without truncating; used by Test 11.",
    )
    args = parser.parse_args()

    conn = await _connect(args.dsn)
    try:
        if args.extra > 0:
            for i in range(args.extra):
                await _insert_one(
                    conn,
                    dict(
                        tenant_id=SEED_TENANT_DEFAULT,
                        doctype_detected="hu_invoice",
                        doctype_confidence=0.92,
                        extraction_path="invoice_processor",
                        extraction_outcome="success",
                        cost_usd=0.002,
                        latency_ms=180,
                        metadata={
                            "attachments": [
                                {
                                    "filename": f"extra_seed_{i}.pdf",
                                    "extraction_path": "invoice_processor",
                                    "extraction_outcome": "succeeded",
                                }
                            ]
                        },
                    ),
                )
            print(f"Inserted {args.extra} extra row(s).")
            return

        deleted = await _truncate(conn)
        print(f"Deleted {deleted} pre-existing seed row(s).")
        rows = _build_seed_rows()
        for row in rows:
            await _insert_one(conn, row)
        print(
            f"Inserted {len(rows)} fresh seed row(s) "
            f"(default={sum(1 for r in rows if r['tenant_id'] == SEED_TENANT_DEFAULT)}, "
            f"other={sum(1 for r in rows if r['tenant_id'] == SEED_TENANT_OTHER)})."
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
