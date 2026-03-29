"""Email Intent Processor workflow - 7-step classification pipeline.

Pipeline:
  1. parse_email - Parse email (EmailParser from tools)
  2. process_attachments - Process attachments (AttachmentProcessor from tools)
  3. classify_intent - Hybrid (sklearn + LLM) using FULL context
  4. extract_entities - NER using entities.json schema
  5. score_priority - Priority from priorities.json rules
  6. decide_routing - Route from routing_rules.json
  7. log_result - Assemble final result

Module-level singletons: ModelClient, PromptManager, SchemaRegistry,
HybridClassifier, EmailParser, AttachmentProcessor.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import structlog

from aiflow.engine.step import step
from aiflow.engine.workflow import workflow, WorkflowBuilder
from aiflow.tools.email_parser import EmailParser
from aiflow.tools.attachment_processor import AttachmentProcessor, AttachmentConfig
from aiflow.tools.schema_registry import SchemaRegistry

from skills.email_intent_processor import models_client, prompt_manager
from skills.email_intent_processor.classifiers import HybridClassifier
from skills.email_intent_processor.classifiers.sklearn_classifier import SklearnClassifier
from skills.email_intent_processor.classifiers.llm_classifier import LLMClassifier
from skills.email_intent_processor.models import (
    AttachmentInfo,
    IntentResult,
    Entity,
    EntityResult,
    PriorityResult,
    RoutingDecision,
    EmailProcessingResult,
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

logger = structlog.get_logger(__name__)

# --- Module-level singletons ---

email_parser = EmailParser()
attachment_processor = AttachmentProcessor(AttachmentConfig())

# Schema registry - loads from skills/email_intent_processor/schemas/
_skills_dir = Path(__file__).parent.parent.parent
schema_registry = SchemaRegistry(skills_dir=_skills_dir)

# Sklearn classifier (optional - only if model file exists)
_model_path = Path(__file__).parent.parent / "models" / "intent_model.joblib"
sklearn_clf = SklearnClassifier(model_path=_model_path if _model_path.exists() else None)

# LLM classifier
llm_clf = LLMClassifier(
    models_client=models_client,
    prompt_manager=prompt_manager,
    prompt_name="email-intent/classifier",
)

# Hybrid classifier combining both
hybrid_classifier = HybridClassifier(
    sklearn_classifier=sklearn_clf if sklearn_clf.is_loaded else None,
    llm_classifier=llm_clf,
    strategy="sklearn_first" if sklearn_clf.is_loaded else "llm_only",
    confidence_threshold=0.6,
)


# --- Step 1: Parse Email ---

@step(name="parse_email", description="Parse raw email into structured fields")
async def parse_email(data: dict) -> dict:
    """Parse email from .eml path or raw text fields."""
    start = time.monotonic()

    raw_eml_path = data.get("raw_eml_path", "")
    if raw_eml_path and Path(raw_eml_path).exists():
        parsed = email_parser.parse_eml(raw_eml_path)
    else:
        parsed = email_parser.parse_text(
            subject=data.get("subject", ""),
            body=data.get("body", ""),
            sender=data.get("sender", ""),
        )

    attachments_raw = []
    for att in parsed.attachments:
        attachments_raw.append({
            "filename": att.filename,
            "mime_type": att.mime_type,
            "size_bytes": att.size_bytes,
            "content_b64": "",  # Content stays in memory, not serialized
        })

    duration = (time.monotonic() - start) * 1000
    logger.info(
        "parse_email_done",
        subject=parsed.subject[:50],
        body_len=len(parsed.body_text),
        attachments=len(parsed.attachments),
        duration_ms=round(duration),
    )

    return {
        "subject": parsed.subject,
        "body": parsed.body_text,
        "body_html": parsed.body_html,
        "sender": parsed.from_,
        "recipients": parsed.to,
        "date": parsed.date,
        "message_id": parsed.message_id,
        "in_reply_to": parsed.in_reply_to,
        "thread_id": parsed.thread_id,
        "attachments_raw": attachments_raw,
        "_parsed_attachments": parsed.attachments,  # Keep raw for processing
    }


# --- Step 2: Process Attachments ---

@step(name="process_attachments", description="Extract text and fields from attachments")
async def process_attachments(data: dict) -> dict:
    """Process email attachments through docling/Azure DI/LLM vision."""
    raw_attachments = data.get("_parsed_attachments", [])
    doc_types_schema = schema_registry.load_schema(
        "email_intent_processor", "document_types"
    )
    doc_types = doc_types_schema.get("document_types", [])

    attachment_summaries: list[dict] = []
    all_attachment_text = ""

    for att in raw_attachments:
        processed = await attachment_processor.process(
            filename=att.filename,
            content=att.content,
            mime_type=att.mime_type,
        )

        # Determine document type from schema
        doc_type = _match_document_type(att.filename, att.mime_type, doc_types)

        info = AttachmentInfo(
            filename=att.filename,
            mime_type=att.mime_type,
            size_bytes=att.size_bytes,
            extracted_text=processed.text[:2000],
            extracted_fields=processed.extracted_fields,
            document_type=doc_type,
            processor_used=processed.processor_used,
            error=processed.error,
        )
        attachment_summaries.append(info.model_dump())

        if processed.text:
            all_attachment_text += f"\n[{att.filename}]: {processed.text[:1000]}"

    logger.info(
        "process_attachments_done",
        count=len(raw_attachments),
        extracted_text_len=len(all_attachment_text),
    )

    return {
        **{k: v for k, v in data.items() if not k.startswith("_")},
        "attachment_summaries": attachment_summaries,
        "attachment_text": all_attachment_text.strip(),
    }


# --- Step 3: Classify Intent ---

@step(name="classify_intent", description="Classify email intent using hybrid sklearn+LLM")
async def classify_intent(data: dict) -> dict:
    """Classify email intent using full context (subject + body + attachments)."""
    subject = data.get("subject", "")
    body = data.get("body", "")
    attachment_text = data.get("attachment_text", "")

    # Combine all text for classification
    full_text = body
    if attachment_text:
        full_text += f"\n\n--- Csatolt dokumentumok ---\n{attachment_text}"

    # Load intent schema
    intents_schema = schema_registry.load_schema(
        "email_intent_processor", "intents"
    )
    schema_intents = intents_schema.get("intents", [])

    intent_result = await hybrid_classifier.classify(
        text=full_text,
        subject=subject,
        schema_intents=schema_intents,
    )

    # Enrich with display name from schema
    if not intent_result.intent_display_name:
        for intent_def in schema_intents:
            if intent_def.get("id") == intent_result.intent_id:
                intent_result.intent_display_name = intent_def.get("display_name", "")
                break

    logger.info(
        "classify_intent_done",
        intent=intent_result.intent_id,
        confidence=intent_result.confidence,
        method=intent_result.method,
    )

    return {
        **data,
        "intent": intent_result.model_dump(),
    }


# --- Step 4: Extract Entities ---

@step(name="extract_entities", description="Extract named entities from email content")
async def extract_entities(data: dict) -> dict:
    """Extract entities using regex + LLM based on entities.json schema."""
    subject = data.get("subject", "")
    body = data.get("body", "")
    attachment_text = data.get("attachment_text", "")

    entities_schema = schema_registry.load_schema(
        "email_intent_processor", "entities"
    )
    entity_types = entities_schema.get("entity_types", [])

    all_entities: list[Entity] = []
    methods_used: set[str] = set()

    # Phase 1: Regex extraction
    for etype in entity_types:
        if "regex" in etype.get("extraction_methods", []):
            for pattern in etype.get("regex_patterns", []):
                for source_name, source_text in [
                    ("subject", subject),
                    ("body", body),
                    ("attachment", attachment_text),
                ]:
                    if source_name not in etype.get("source_priority", ["body"]):
                        continue
                    try:
                        matches = re.finditer(pattern, source_text)
                        for match in matches:
                            entity = Entity(
                                entity_type=etype["id"],
                                value=match.group().strip(),
                                confidence=0.9,
                                source=source_name,
                                extraction_method="regex",
                                start_offset=match.start(),
                                end_offset=match.end(),
                            )
                            all_entities.append(entity)
                            methods_used.add("regex")
                    except re.error:
                        logger.warning("regex_error", entity_type=etype["id"], pattern=pattern)

    # Phase 2: LLM extraction for entity types that need it
    llm_entity_types = [
        et for et in entity_types if "llm" in et.get("extraction_methods", [])
    ]
    if llm_entity_types:
        try:
            llm_entities = await _extract_entities_llm(
                subject, body, llm_entity_types
            )
            all_entities.extend(llm_entities)
            if llm_entities:
                methods_used.add("llm")
        except Exception as e:
            logger.error("llm_entity_extraction_failed", error=str(e))

    # Deduplicate entities (same type + same value)
    all_entities = _deduplicate_entities(all_entities)

    entity_result = EntityResult(
        entities=all_entities,
        entity_count=len(all_entities),
        extraction_methods_used=sorted(methods_used),
    )

    logger.info(
        "extract_entities_done",
        entity_count=len(all_entities),
        methods=sorted(methods_used),
    )

    return {
        **data,
        "entities": entity_result.model_dump(),
    }


async def _extract_entities_llm(
    subject: str,
    body: str,
    entity_types: list[dict],
) -> list[Entity]:
    """Extract entities using LLM with the entity schema as context."""
    # Build entity type descriptions for the prompt
    entity_catalog = "\n".join(
        f"- {et['id']} ({et['display_name']}): {et.get('llm_prompt_hint', '')}"
        for et in entity_types
    )

    prompt = prompt_manager.get("email-intent/entity_extractor")
    messages = prompt.compile(
        variables={
            "subject": subject,
            "body": body[:3000],
            "entity_catalog": entity_catalog,
        }
    )

    result = await models_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
    )

    return _parse_llm_entities(result.output.text)


def _parse_llm_entities(text: str) -> list[Entity]:
    """Parse LLM entity extraction response."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
        entities_data = data.get("entities", data) if isinstance(data, dict) else data
        if not isinstance(entities_data, list):
            return []

        entities = []
        for item in entities_data:
            if isinstance(item, dict) and "entity_type" in item and "value" in item:
                entities.append(
                    Entity(
                        entity_type=item["entity_type"],
                        value=item["value"],
                        normalized_value=item.get("normalized_value", ""),
                        confidence=float(item.get("confidence", 0.8)),
                        source="body",
                        extraction_method="llm",
                    )
                )
        return entities
    except (json.JSONDecodeError, TypeError):
        return []


def _deduplicate_entities(entities: list[Entity]) -> list[Entity]:
    """Remove duplicate entities (same type + value)."""
    seen: set[tuple[str, str]] = set()
    unique: list[Entity] = []
    for entity in entities:
        key = (entity.entity_type, entity.value.lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(entity)
    return unique


# --- Step 5: Score Priority ---

@step(name="score_priority", description="Score email priority using rules matrix")
async def score_priority(data: dict) -> dict:
    """Score priority using priorities.json rules and entity/intent context."""
    intent_data = data.get("intent", {})
    entities_data = data.get("entities", {})
    body = data.get("body", "")
    in_reply_to = data.get("in_reply_to", "")

    intent_id = intent_data.get("intent_id", "unknown")
    entity_list = entities_data.get("entities", [])
    entity_types_present = {e["entity_type"] for e in entity_list if isinstance(e, dict)}

    priorities_schema = schema_registry.load_schema(
        "email_intent_processor", "priorities"
    )
    rules = priorities_schema.get("rules", [])
    boost_rules = priorities_schema.get("boost_rules", [])
    priority_levels = {
        p["level"]: p for p in priorities_schema.get("priority_levels", [])
    }
    default_priority = priorities_schema.get("default_priority", 4)

    # Find matching rule
    matched_rule = ""
    priority_level = default_priority

    for rule in rules:
        conditions = rule.get("conditions", {})
        if conditions.get("intent") != intent_id:
            continue

        # Check entity_present condition
        entity_req = conditions.get("entity_present", [])
        if entity_req and not all(et in entity_types_present for et in entity_req):
            continue

        # Check is_thread_reply condition
        if conditions.get("is_thread_reply") and not in_reply_to:
            continue

        # Check keywords_present condition
        kw_present = conditions.get("keywords_present", [])
        if kw_present:
            body_lower = body.lower()
            if not any(kw.lower() in body_lower for kw in kw_present):
                continue

        # Rule matched
        priority_level = rule["result_priority"]
        matched_rule = rule["id"]
        break

    # Apply boost rules
    boosts_applied: list[str] = []
    for boost in boost_rules:
        boost_val = boost.get("boost", 0)
        if boost_val == 0:
            continue

        keywords = boost.get("keywords", [])
        if keywords:
            body_lower = body.lower()
            if any(kw.lower() in body_lower for kw in keywords):
                priority_level = max(1, priority_level + boost_val)
                boosts_applied.append(boost["id"])

    # Clamp to valid range
    priority_level = max(1, min(5, priority_level))

    # Look up priority metadata
    priority_meta = priority_levels.get(priority_level, {})

    result = PriorityResult(
        priority_level=priority_level,
        priority_name=priority_meta.get("name", "medium"),
        priority_display_name=priority_meta.get("display_name", "Kozepes"),
        sla_hours=priority_meta.get("sla_hours", 48),
        matched_rule=matched_rule,
        boosts_applied=boosts_applied,
    )

    logger.info(
        "score_priority_done",
        level=result.priority_level,
        name=result.priority_name,
        rule=matched_rule,
        boosts=boosts_applied,
    )

    return {
        **data,
        "priority": result.model_dump(),
    }


# --- Step 6: Decide Routing ---

@step(name="decide_routing", description="Decide routing queue and department")
async def decide_routing(data: dict) -> dict:
    """Route email based on intent + priority using routing_rules.json."""
    intent_data = data.get("intent", {})
    priority_data = data.get("priority", {})
    body = data.get("body", "")

    intent_id = intent_data.get("intent_id", "unknown")
    sub_intent = intent_data.get("sub_intent", "")
    priority_level = priority_data.get("priority_level", 4)

    routing_schema = schema_registry.load_schema(
        "email_intent_processor", "routing_rules"
    )
    routing_rules = routing_schema.get("routing_rules", [])
    escalation_rules = routing_schema.get("escalation_rules", [])
    departments = {d["id"]: d for d in routing_schema.get("departments", [])}
    queues = {q["id"]: q for q in routing_schema.get("queues", [])}
    default_route = routing_schema.get("default_route", {})

    # Find matching routing rule
    matched_rule = ""
    queue_id = default_route.get("queue", "q_inquiry")
    department_id = default_route.get("department", "informacio")
    auto_escalate = 0
    notes = ""

    for rule in routing_rules:
        if rule.get("intent") != intent_id:
            continue

        # Check priority range
        prange = rule.get("priority_range", [1, 5])
        if not (prange[0] <= priority_level <= prange[1]):
            continue

        # Check sub_intent match (if rule specifies sub_intents)
        rule_sub_intents = rule.get("sub_intents", [])
        if rule_sub_intents and sub_intent not in rule_sub_intents:
            continue

        # Rule matched
        queue_id = rule["queue"]
        department_id = rule["department"]
        auto_escalate = rule.get("auto_escalate_after_minutes", 0)
        matched_rule = rule["id"]
        notes = rule.get("notes", "")
        break

    # Check escalation overrides
    escalation_triggered = False
    escalation_reason = ""
    for esc in escalation_rules:
        trigger = esc.get("trigger", "")
        if trigger == "legal_keywords_detected":
            legal_kw = ["ugyved", "per", "birosag", "feljelentes", "lawyer", "court"]
            if any(kw in body.lower() for kw in legal_kw):
                queue_id = esc["override_queue"]
                department_id = esc["override_department"]
                escalation_triggered = True
                escalation_reason = "legal_keywords"
                break

    # Resolve names
    dept = departments.get(department_id, {})
    queue = queues.get(queue_id, {})

    result = RoutingDecision(
        queue_id=queue_id,
        queue_name=queue.get("department", queue_id),
        department_id=department_id,
        department_name=dept.get("display_name", department_id),
        department_email=dept.get("email", ""),
        auto_escalate_after_minutes=auto_escalate,
        matched_rule=matched_rule,
        escalation_triggered=escalation_triggered,
        escalation_reason=escalation_reason,
        notes=notes,
    )

    logger.info(
        "decide_routing_done",
        queue=result.queue_id,
        department=result.department_id,
        rule=matched_rule,
        escalation=escalation_triggered,
    )

    return {
        **data,
        "routing": result.model_dump(),
    }


# --- Step 7: Log Result ---

@step(name="log_result", description="Assemble and log final processing result")
async def log_result(data: dict) -> dict:
    """Assemble the final EmailProcessingResult."""
    intent_data = data.get("intent", {})
    entities_data = data.get("entities", {})
    priority_data = data.get("priority", {})
    routing_data = data.get("routing", {})

    result = EmailProcessingResult(
        email_id=data.get("message_id", ""),
        subject=data.get("subject", ""),
        sender=data.get("sender", ""),
        received_date=data.get("date", ""),
        has_attachments=len(data.get("attachment_summaries", [])) > 0,
        attachment_count=len(data.get("attachment_summaries", [])),
        intent=IntentResult(**intent_data) if intent_data else None,
        entities=EntityResult(**entities_data) if entities_data else None,
        priority=PriorityResult(**priority_data) if priority_data else None,
        routing=RoutingDecision(**routing_data) if routing_data else None,
        attachment_summaries=[
            AttachmentInfo(**a) for a in data.get("attachment_summaries", [])
        ],
        pipeline_version="1.0.0",
    )

    logger.info(
        "email_processing_complete",
        email_id=result.email_id,
        intent=result.intent.intent_id if result.intent else "none",
        priority=result.priority.priority_level if result.priority else 0,
        routing=result.routing.queue_id if result.routing else "none",
        entities=result.entities.entity_count if result.entities else 0,
    )

    return result.model_dump()


# --- Helper ---

def _match_document_type(
    filename: str, mime_type: str, doc_types: list[dict]
) -> str:
    """Match an attachment to a document type from the schema."""
    ext = Path(filename).suffix.lower() if filename else ""
    for dt in doc_types:
        if mime_type in dt.get("mime_types", []):
            return dt["id"]
        if ext in dt.get("extensions", []):
            return dt["id"]
    return "unknown"


# --- Workflow Registration ---

@workflow(
    name="email-intent-processing",
    version="1.0.0",
    skill="email_intent_processor",
)
def email_intent_processing(wf: WorkflowBuilder) -> None:
    """Kafka-triggered email classification and routing pipeline."""
    wf.step(parse_email)
    wf.step(process_attachments, depends_on=["parse_email"])
    wf.step(classify_intent, depends_on=["process_attachments"])
    wf.step(extract_entities, depends_on=["process_attachments"])
    wf.step(score_priority, depends_on=["classify_intent", "extract_entities"])
    wf.step(decide_routing, depends_on=["score_priority"])
    wf.step(log_result, depends_on=["decide_routing"])
