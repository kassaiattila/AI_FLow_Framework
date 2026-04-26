"""Document Recognizer service — Sprint V SV-1 foundation layer.

Modules:

* :mod:`aiflow.services.document_recognizer.registry` — DocTypeRegistry +
  per-tenant override loader.
* :mod:`aiflow.services.document_recognizer.safe_eval` — restricted
  expression evaluator for ``IntentRoutingRule.if_expr``.

SV-2 will add ``classifier.py`` (rule engine + LLM fallback);
SV-2 will add ``orchestrator.py`` (parse → classify → extract → intent);
SV-3 will add the API router + Alembic 048;
SV-4 will add the admin UI page;
SV-5 will add the corpus + accuracy gate.
"""

from __future__ import annotations

from aiflow.services.document_recognizer.registry import DocTypeRegistry
from aiflow.services.document_recognizer.safe_eval import (
    SafeEvalError,
    safe_eval_intent_rule,
)

__all__ = [
    "DocTypeRegistry",
    "SafeEvalError",
    "safe_eval_intent_rule",
]
