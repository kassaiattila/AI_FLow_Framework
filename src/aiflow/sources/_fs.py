"""Shared filesystem helpers for source adapters.

Source: 01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md (Week 1 Day 4 — E1.3).

Extracted from `email_adapter.py` when `FileSourceAdapter` landed so both
adapters sanitize filenames identically. Any future adapter that spills bytes
to disk (folder_watch, api_push) should reuse this module instead of rolling
its own sanitizer.
"""

from __future__ import annotations

import re

__all__ = [
    "sanitize_filename",
]

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    """Collapse unsafe characters to underscore; keep name non-empty and bounded.

    - Unsafe chars (anything outside [A-Za-z0-9._-]) collapse to single `_`.
    - Path separators, null bytes, and shell metacharacters are all in the
      unsafe set, so `../../etc/passwd` → `_etc_passwd`.
    - Empty / whitespace-only input falls back to `attachment.bin`.
    - Result is truncated to 200 chars to stay well under Windows MAX_PATH.
    """
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", name.strip()) or "attachment.bin"
    return cleaned[:200]
