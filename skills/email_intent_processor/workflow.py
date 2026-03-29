"""Email Intent Processor workflow - re-exports from workflows/classify.py.

This module exists for backward compatibility and convenience.
The actual implementation is in workflows/classify.py.
"""
from skills.email_intent_processor.workflows.classify import (
    parse_email,
    process_attachments,
    classify_intent,
    extract_entities,
    score_priority,
    decide_routing,
    log_result,
    email_intent_processing,
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
