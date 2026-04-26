"""DEPRECATED: skill renamed to ``document_recognizer`` in Sprint V (v1.6.0).

This shim re-exports the new entry point + emits :class:`DeprecationWarning`
on first import. Will be deleted in Sprint W (v1.7.0).

Old:
    from skills.invoice_finder import models_client, prompt_manager

New:
    from skills.document_recognizer import models_client, prompt_manager
"""

from __future__ import annotations

import warnings

warnings.warn(
    "skills.invoice_finder is deprecated; use skills.document_recognizer instead. "
    "This shim will be removed in v1.7.0 (Sprint W).",
    DeprecationWarning,
    stacklevel=2,
)

from skills.document_recognizer import (  # noqa: E402, F401
    SKILL_NAME,
    models_client,
    prompt_manager,
)

__all__ = ["SKILL_NAME", "models_client", "prompt_manager"]
