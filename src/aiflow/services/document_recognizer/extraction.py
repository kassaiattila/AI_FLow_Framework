"""LLM-driven extraction stage for the document recognizer — Sprint W SW-1.

Builds an ``ExtractFn`` (per the orchestrator's contract) that:

1. Resolves the descriptor's ``extraction.workflow`` PromptWorkflow descriptor
   via :class:`aiflow.prompts.workflow_executor.PromptWorkflowExecutor`.
2. For each step that has a resolved prompt definition, invokes the LLM
   via the supplied ``models_client.generate(...)``-style callable, gating
   the call with :meth:`CostPreflightGuardrail.check_step` (Sprint U S154
   API) using the descriptor step's ``metadata.cost_ceiling_usd``.
3. Parses the final-step JSON response and maps each extracted value into
   :class:`DocFieldValue` per the descriptor's ``extraction.fields`` schema.
4. Aggregates per-step costs + elapsed wall time + parse warnings into
   the returned :class:`DocExtractionResult`.

Sprint W SW-1 keeps the implementation **modular** — the orchestrator
constructs an ``ExtractFn`` by calling :func:`build_extract_fn` with its
PromptWorkflowExecutor + CostPreflightGuardrail + ModelClient instances.
Tests can pass deterministic fakes for any of the three.
"""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocFieldValue,
    DocTypeDescriptor,
)
from aiflow.core.errors import CostGuardrailRefused
from aiflow.services.document_recognizer.classifier import ClassifierInput

__all__ = [
    "GenerateFn",
    "build_extract_fn",
]

logger = structlog.get_logger(__name__)


# Type alias for the LLM generate callable — tests inject fakes; production
# wires `models_client.generate(...)` from the skill.
# Returns a structured response with `.output.text` (or `.output.structured`)
# + `.cost_usd` + `.input_tokens` + `.output_tokens`.
GenerateFn = Callable[..., Awaitable[Any]]


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------


def _extract_json_block(text: str) -> dict[str, Any] | None:
    """Find the first ``{...}`` JSON block in ``text``. Returns ``None`` on
    parse failure. Tolerant of leading prose / code fences."""
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        # Strip code fences (```json\n...\n``` etc.)
        lines = s.split("\n")
        if lines:
            s = "\n".join(line for line in lines if not line.startswith("```")).strip()
    # Find the first '{' and the last '}' that still parse as a single JSON object.
    start = s.find("{")
    if start < 0:
        return None
    end = s.rfind("}")
    if end <= start:
        return None
    blob = s[start : end + 1]
    try:
        parsed = json.loads(blob)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _coerce_value(raw: Any) -> str | int | float | bool | None:
    """Coerce a JSON-extracted value into the DocFieldValue scalar shape.

    Lists / nested dicts are stringified (JSON-encoded) so the field still
    has a value the validators can inspect.
    """
    if raw is None:
        return None
    if isinstance(raw, (str, bool)):
        return raw
    if isinstance(raw, (int, float)):
        return raw
    # Fallback: serialize complex shapes
    try:
        return json.dumps(raw, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(raw)


# ---------------------------------------------------------------------------
# Cost preflight wrapper (Sprint U S154 check_step API)
# ---------------------------------------------------------------------------


def _enforce_step_ceiling(
    *,
    cost_guardrail: Any | None,
    step_name: str,
    model: str,
    input_tokens: int,
    max_output_tokens: int,
    ceiling_usd: float | None,
) -> None:
    """Run :meth:`CostPreflightGuardrail.check_step` and raise on refusal.

    Caller passes ``cost_guardrail=None`` to skip preflight (e.g. tests
    that exercise the parsing path independently). When the guardrail is
    set + ceiling is set + decision is not allowed, raise
    :class:`CostGuardrailRefused` (caller logs structured event).
    """
    if cost_guardrail is None or ceiling_usd is None:
        return
    decision = cost_guardrail.check_step(
        step_name=step_name,
        model=model,
        input_tokens=input_tokens,
        max_output_tokens=max_output_tokens,
        ceiling_usd=ceiling_usd,
    )
    if not decision.allowed:
        raise CostGuardrailRefused(
            tenant_id="default",
            projected_usd=decision.projected_usd,
            remaining_usd=decision.remaining_usd or ceiling_usd,
            period="per_step",
            reason=decision.reason,
        )


# ---------------------------------------------------------------------------
# build_extract_fn
# ---------------------------------------------------------------------------


def build_extract_fn(
    *,
    workflow_executor: Any,
    cost_guardrail: Any | None,
    generate_fn: GenerateFn,
    skill_name: str = "document_recognizer",
) -> Callable[
    [DocTypeDescriptor, ClassifierInput, str],
    Awaitable[DocExtractionResult],
]:
    """Construct an ``ExtractFn`` that the orchestrator can pass through.

    :param workflow_executor: a ``PromptWorkflowExecutor`` instance whose
        ``resolve_for_skill(skill, workflow_name)`` returns the resolved
        PromptWorkflow + step→prompt-definition map (or ``None`` if the
        flag is off / descriptor missing).
    :param cost_guardrail: a ``CostPreflightGuardrail`` instance whose
        ``check_step(...)`` enforces per-step ceilings. ``None`` skips
        preflight (tests).
    :param generate_fn: an ``async`` callable matching ``models_client.generate``
        (returns response with ``output.text`` / ``output.structured`` /
        ``cost_usd`` / ``input_tokens`` / ``output_tokens``).
    :param skill_name: skill key for the executor's flag / opt-in lookup.
        Default: ``"document_recognizer"``.

    Returns a coroutine function the orchestrator can call as its
    ``extract_fn``.
    """

    async def extract_fn(
        descriptor: DocTypeDescriptor,
        ctx: ClassifierInput,
        tenant_id: str,
    ) -> DocExtractionResult:
        start = time.monotonic()
        warnings: list[str] = []
        extracted: dict[str, DocFieldValue] = {}
        total_cost_usd = 0.0

        # 1. Resolve the descriptor's extraction.workflow PromptWorkflow.
        resolved = workflow_executor.resolve_for_skill(skill_name, descriptor.extraction.workflow)
        if resolved is None:
            # Flag-off (skill not in CSV) OR descriptor missing → empty result + warning.
            logger.info(
                "doc_recognizer.extract_workflow_unresolved",
                doc_type=descriptor.name,
                workflow=descriptor.extraction.workflow,
                reason="resolve_for_skill_returned_none",
            )
            return DocExtractionResult(
                doc_type=descriptor.name,
                extracted_fields={},
                validation_warnings=[
                    f"workflow {descriptor.extraction.workflow!r} not resolved "
                    "(flag-off, skill not in CSV, or descriptor missing)",
                ],
                cost_usd=0.0,
                extraction_time_ms=(time.monotonic() - start) * 1000.0,
            )

        workflow, prompt_map = resolved

        # 2. Per-step LLM invocation.
        last_step_payload: dict[str, Any] | None = None
        for step in workflow.steps:
            prompt_def = prompt_map.get(step.id)
            if prompt_def is None:
                if step.required:
                    warnings.append(
                        f"step {step.id!r}: prompt {step.prompt_name!r} unresolved "
                        f"(required step skipped)"
                    )
                else:
                    # Optional step (e.g. `validate` Sprint T S149 pattern) —
                    # pure-Python validators run separately in the orchestrator.
                    logger.debug(
                        "doc_recognizer.extract_step_skipped_optional",
                        step_id=step.id,
                        prompt_name=step.prompt_name,
                    )
                continue

            ceiling = None
            if step.metadata:
                raw_ceiling = step.metadata.get("cost_ceiling_usd")
                if raw_ceiling is not None:
                    try:
                        ceiling = float(raw_ceiling)
                    except (TypeError, ValueError):
                        warnings.append(
                            f"step {step.id!r}: invalid cost_ceiling_usd {raw_ceiling!r}"
                        )

            input_tokens_est = max(256, len(ctx.text) // 4 + 256)
            max_output_tokens = prompt_def.config.max_tokens

            # 2a. Cost preflight (Sprint U S154 check_step API).
            try:
                _enforce_step_ceiling(
                    cost_guardrail=cost_guardrail,
                    step_name=step.id,
                    model=prompt_def.config.model,
                    input_tokens=input_tokens_est,
                    max_output_tokens=max_output_tokens,
                    ceiling_usd=ceiling,
                )
            except CostGuardrailRefused:
                logger.warning(
                    "doc_recognizer.extract_step_cost_refused",
                    doc_type=descriptor.name,
                    step_id=step.id,
                    ceiling_usd=ceiling,
                )
                raise

            # 2b. Compile the prompt + invoke LLM.
            try:
                messages = prompt_def.compile(
                    variables={
                        "text": ctx.text,
                        "filename": ctx.filename or "",
                        "doc_type": descriptor.name,
                    }
                )
            except Exception as exc:  # noqa: BLE001 — bad template should warn, not crash
                warnings.append(f"step {step.id!r}: prompt compile failed: {exc}")
                continue

            try:
                response = await generate_fn(
                    messages=messages,
                    model=prompt_def.config.model,
                    temperature=prompt_def.config.temperature,
                    max_tokens=max_output_tokens,
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"step {step.id!r}: LLM call failed: {exc}")
                logger.warning(
                    "doc_recognizer.extract_llm_call_failed",
                    doc_type=descriptor.name,
                    step_id=step.id,
                    error=str(exc)[:200],
                )
                continue

            cost = float(getattr(response, "cost_usd", 0.0) or 0.0)
            total_cost_usd += cost

            # 2c. Parse the response — prefer structured, fall back to text JSON.
            output = getattr(response, "output", None)
            structured = getattr(output, "structured", None) if output else None
            text = getattr(output, "text", None) if output else None

            payload: dict[str, Any] | None = None
            if isinstance(structured, dict):
                payload = structured
            elif isinstance(text, str):
                payload = _extract_json_block(text)
                if payload is None:
                    warnings.append(f"step {step.id!r}: LLM response not valid JSON")
                    continue
            else:
                warnings.append(f"step {step.id!r}: LLM response missing output")
                continue

            last_step_payload = payload

        # 3. Map the last successful payload into DocFieldValue per descriptor.
        if last_step_payload is None:
            warnings.append("no successful extraction step produced a payload")
            return DocExtractionResult(
                doc_type=descriptor.name,
                extracted_fields={},
                validation_warnings=warnings,
                cost_usd=total_cost_usd,
                extraction_time_ms=(time.monotonic() - start) * 1000.0,
            )

        # Per-field confidence: prefer the LLM-returned `confidence` dict if
        # present, otherwise default to 0.7 (mid-tier confidence for LLM
        # outputs that don't self-score).
        confidence_map: dict[str, float] = {}
        raw_confidences = last_step_payload.get("per_field_confidence")
        if isinstance(raw_confidences, dict):
            for k, v in raw_confidences.items():
                if isinstance(v, (int, float)) and 0.0 <= v <= 1.0:
                    confidence_map[str(k)] = float(v)

        for field_spec in descriptor.extraction.fields:
            raw = _resolve_field_value(last_step_payload, field_spec.name)
            if raw is None:
                continue
            value = _coerce_value(raw)
            confidence = confidence_map.get(field_spec.name, 0.7)
            extracted[field_spec.name] = DocFieldValue(
                value=value,
                confidence=confidence,
            )

        elapsed_ms = (time.monotonic() - start) * 1000.0

        return DocExtractionResult(
            doc_type=descriptor.name,
            extracted_fields=extracted,
            validation_warnings=warnings,
            cost_usd=total_cost_usd,
            extraction_time_ms=elapsed_ms,
        )

    return extract_fn


def _resolve_field_value(payload: dict[str, Any], field_name: str) -> Any:
    """Look up ``field_name`` in the LLM payload, supporting nested shapes.

    LLM responses tend to follow one of two shapes:

    1. Flat: ``{"invoice_number": "INV-1", "total_gross": 12500, ...}``
    2. Nested by category: ``{"header": {"invoice_number": "INV-1"}, "totals": {"total_gross": 12500}}``

    This helper checks the flat path first, then descends one level into
    common category keys (``header``, ``vendor``, ``buyer``, ``totals``,
    ``fields``).
    """
    if field_name in payload:
        return payload[field_name]
    for category in ("fields", "header", "vendor", "buyer", "totals", "data", "extracted"):
        sub = payload.get(category)
        if isinstance(sub, dict) and field_name in sub:
            return sub[field_name]
    return None
