"""File upload security utilities — filename sanitization and path traversal prevention."""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["secure_filename", "validate_upload_path"]


def secure_filename(filename: str) -> str:
    """Sanitize an uploaded filename to prevent path traversal and injection.

    Removes directory separators, null bytes, and dangerous characters.
    Returns a safe filename suitable for filesystem storage.
    """
    # Strip directory components (Unix and Windows separators)
    filename = filename.split("/")[-1].split("\\")[-1]
    # Remove null bytes
    filename = filename.replace("\x00", "")
    # Allow only word chars, hyphens, dots, spaces
    filename = re.sub(r"[^\w\s\-.]", "", filename)
    # Collapse multiple dots/spaces, strip leading/trailing dots and spaces
    filename = re.sub(r"\.{2,}", ".", filename)
    filename = filename.strip(". ")
    # Fallback for empty result
    if not filename:
        filename = "unnamed"
    return filename


def validate_upload_path(path: Path, allowed_base: Path) -> Path:
    """Ensure a resolved path is within the allowed base directory.

    Prevents path traversal attacks (e.g., ../../etc/passwd).
    Raises ValueError if the path escapes the allowed directory.
    """
    resolved = path.resolve()
    base_resolved = allowed_base.resolve()
    if not resolved.is_relative_to(base_resolved):
        raise ValueError(f"Path traversal detected: {path} escapes {allowed_base}")
    return resolved
