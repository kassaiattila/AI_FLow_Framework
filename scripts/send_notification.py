#!/usr/bin/env python3
"""Notification helper for the AIFlow /auto-sprint loop.

File-log mode (default): appends a structured entry to
``session_prompts/.notifications.log`` and exits 0. Used when
``AIFLOW_AUTOSPRINT_NO_EMAIL=1`` is set (the project default — see
``.claude/settings.json``).

Gmail mode (Phase 2): not implemented in this version. Calling the script
without the env var raises ``NotImplementedError`` so the structure is
preserved for a future Gmail OAuth branch (mirroring DOHA's
``scripts/send_notification.py`` Gmail-API helper).

Exit codes:
    0 — written to log (file-log mode) or sent (Gmail mode, future)
    1 — auth / credential failure (Gmail mode, future)
    2 — send / write failure (file unwritable, Gmail API error)
    3 — unexpected error

Usage:
    python scripts/send_notification.py \\
        --kind info \\
        --subject "auto-sprint iter 3 done" \\
        --body "S83 closed at commit abc1234"

    # body from file (the auto-sprint loop renders to .notifications_body.md)
    python scripts/send_notification.py \\
        --kind stop \\
        --subject "[AIFlow STOP] S84 — decision-required" \\
        --body-file session_prompts/.notifications_body.md
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

LOG_PATH = Path("session_prompts/.notifications.log")
ENV_NO_EMAIL = "AIFLOW_AUTOSPRINT_NO_EMAIL"
VALID_KINDS = ("info", "done", "stop", "cap")


def _file_log(*, kind: str, subject: str, body: str) -> int:
    """Append a single notification entry to the log file. Returns exit code."""
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    indented_body = "\n".join(f"  {line}" for line in body.splitlines()) if body else "  (no body)"
    entry = f"[{ts}] [{kind.upper()}] {subject}\n{indented_body}\n---\n"
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(entry)
    except OSError as exc:
        print(f"WRITE_FAIL: {LOG_PATH}: {exc}", file=sys.stderr)
        return 2
    print(f"LOGGED kind={kind} path={LOG_PATH}")
    return 0


def _gmail_send(*, kind: str, subject: str, body: str) -> int:
    raise NotImplementedError(
        "Gmail send branch not implemented in this AIFlow version. "
        "Set AIFLOW_AUTOSPRINT_NO_EMAIL=1 (default in .claude/settings.json) "
        "to use file-log mode, or implement the Gmail OAuth branch in a "
        "future session (mirror DOHA scripts/send_notification.py)."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Notification helper for AIFlow /auto-sprint (file-log mode)"
    )
    parser.add_argument(
        "--kind",
        required=True,
        choices=VALID_KINDS,
        help="Notification kind: info | done | stop | cap",
    )
    parser.add_argument("--subject", required=True, help="Short notification subject")
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body", help="Inline body string")
    body_group.add_argument("--body-file", help="Path to a UTF-8 body file")
    args = parser.parse_args()

    if args.body is not None:
        body = args.body
    else:
        body_path = Path(args.body_file)
        if not body_path.is_file():
            print(
                f"BODY_FILE_MISSING: {body_path} not found or not a regular file",
                file=sys.stderr,
            )
            return 1
        try:
            body = body_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"BODY_READ_FAIL: {body_path}: {exc}", file=sys.stderr)
            return 1

    no_email = os.environ.get(ENV_NO_EMAIL, "").strip()
    if no_email == "1":
        return _file_log(kind=args.kind, subject=args.subject, body=body)

    try:
        return _gmail_send(kind=args.kind, subject=args.subject, body=body)
    except NotImplementedError as exc:
        print(f"NOT_IMPLEMENTED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
