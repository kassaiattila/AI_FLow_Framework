"""Email Intent Processor workflow - re-exports from workflows/classify.py.

This module exists for backward compatibility and convenience.
The actual implementation is in workflows/classify.py.
"""
from skills.email_intent_processor.workflows.classify import (
    classify_intent,
    decide_routing,
    email_intent_processing,
    extract_entities,
    log_result,
    parse_email,
    process_attachments,
    score_priority,
)

__all__ = [
    "parse_email",
    "process_attachments",
    "classify_intent",
    "extract_entities",
    "score_priority",
    "decide_routing",
    "log_result",
    "email_intent_processing",
]
