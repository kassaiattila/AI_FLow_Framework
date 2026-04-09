"""Spec Writer workflow — 5-step DAG.

Steps:
    1. analyze          - raw_text → SpecRequirement JSON (LLM analyzer)
    2. select_template  - spec_type → template_type dict (pure Python)
    3. generate_draft   - SpecRequirement → SpecDraft (LLM generator)
    4. review_draft     - SpecDraft → SpecReview (LLM reviewer)
    5. finalize         - bundle into SpecOutput
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from skills.spec_writer.models import (
    SpecDraft,
    SpecField,
    SpecInput,
    SpecOutput,
    SpecRequirement,
    SpecReview,
)

from aiflow.engine.step import step
from aiflow.engine.workflow import WorkflowBuilder, workflow
from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager

__all__ = [
    "analyze",
    "select_template",
    "generate_draft",
    "review_draft",
    "finalize",
    "spec_writing",
    "run_spec_writing",
]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons (lazy-safe — overridable from tests)
# ---------------------------------------------------------------------------

_backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
_models = ModelClient(generation_backend=_backend)
_prompts = PromptManager()
_prompts.register_yaml_dir(Path(__file__).parent.parent / "prompts")


def _safe_json_loads(raw: str) -> dict[str, Any]:
    """Tolerant JSON parser that strips accidental code fences."""
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        parsed = json.loads(cleaned or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _strip_markdown_fences(text: str) -> str:
    """Strip ```markdown / ``` fences around a full-document markdown block."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


# ---------------------------------------------------------------------------
# Step 1 — analyze
# ---------------------------------------------------------------------------


@step(name="analyze")
async def analyze(data: dict[str, Any]) -> dict[str, Any]:
    """Extract a SpecRequirement JSON from the raw input via the analyzer prompt."""
    inp = SpecInput.model_validate(data.get("input") or data)

    prompt_def = _prompts.get("spec-writer/analyzer")
    messages = prompt_def.compile(
        variables={
            "raw_text": inp.raw_text,
            "spec_type": inp.spec_type,
            "language": inp.language,
            "context": inp.context or "",
        }
    )
    result = await _models.generate(
        messages=messages,
        model=prompt_def.config.model,
        temperature=prompt_def.config.temperature,
        max_tokens=prompt_def.config.max_tokens,
    )
    raw = result.output.text or "{}"
    parsed = _safe_json_loads(raw)

    # Coerce inputs/outputs to SpecField regardless of analyzer variability.
    def _coerce_fields(items: Any) -> list[SpecField]:
        out: list[SpecField] = []
        if not isinstance(items, list):
            return out
        for item in items:
            if isinstance(item, dict):
                out.append(
                    SpecField(
                        name=str(item.get("name", "")),
                        type=str(item.get("type", "string") or "string"),
                        description=str(item.get("description", "")),
                    )
                )
        return out

    requirement = SpecRequirement(
        title=str(parsed.get("title") or inp.raw_text[:60] or "Untitled spec"),
        description=str(parsed.get("description") or ""),
        actors=[str(a) for a in (parsed.get("actors") or []) if a],
        goals=[str(g) for g in (parsed.get("goals") or []) if g],
        constraints=[str(c) for c in (parsed.get("constraints") or []) if c],
        inputs=_coerce_fields(parsed.get("inputs")),
        outputs=_coerce_fields(parsed.get("outputs")),
        edge_cases=[str(e) for e in (parsed.get("edge_cases") or []) if e],
    )

    logger.info(
        "spec_writer.analyze.done",
        title=requirement.title,
        goals=len(requirement.goals),
        inputs=len(requirement.inputs),
        outputs=len(requirement.outputs),
        cost=round(result.cost_usd, 6),
    )

    return {
        "input": inp.model_dump(),
        "requirement": requirement.model_dump(),
        "analyze_cost": result.cost_usd,
    }


# ---------------------------------------------------------------------------
# Step 2 — select_template (pure Python)
# ---------------------------------------------------------------------------


@step(name="select_template")
async def select_template(data: dict[str, Any]) -> dict[str, Any]:
    """Deterministic routing from spec_type to generator template key."""
    inp = SpecInput.model_validate(data["input"])
    mapping = {
        "feature": "feature-markdown",
        "api": "api-markdown",
        "db": "db-markdown",
        "user_story": "user-story-markdown",
    }
    template_type = mapping.get(inp.spec_type, "feature-markdown")

    logger.info(
        "spec_writer.select_template.done",
        spec_type=inp.spec_type,
        template_type=template_type,
    )
    return {**data, "template_type": template_type}


# ---------------------------------------------------------------------------
# Step 3 — generate_draft
# ---------------------------------------------------------------------------


@step(name="generate_draft")
async def generate_draft(data: dict[str, Any]) -> dict[str, Any]:
    """Render the Markdown spec draft via the generator prompt."""
    inp = SpecInput.model_validate(data["input"])
    requirement = SpecRequirement.model_validate(data["requirement"])

    prompt_def = _prompts.get("spec-writer/generator")
    messages = prompt_def.compile(
        variables={
            "spec_type": inp.spec_type,
            "language": inp.language,
            "requirement_json": requirement.model_dump_json(indent=2),
        }
    )
    result = await _models.generate(
        messages=messages,
        model=prompt_def.config.model,
        temperature=prompt_def.config.temperature,
        max_tokens=prompt_def.config.max_tokens,
    )
    markdown = _strip_markdown_fences(result.output.text or "")
    sections = [line for line in markdown.splitlines() if line.startswith("##")]

    draft = SpecDraft(
        title=requirement.title,
        spec_type=inp.spec_type,
        language=inp.language,
        markdown=markdown,
        sections_count=len(sections),
        word_count=len(markdown.split()),
    )

    logger.info(
        "spec_writer.generate_draft.done",
        spec_type=inp.spec_type,
        sections=draft.sections_count,
        words=draft.word_count,
        cost=round(result.cost_usd, 6),
    )

    return {**data, "draft": draft.model_dump(), "generate_cost": result.cost_usd}


# ---------------------------------------------------------------------------
# Step 4 — review_draft
# ---------------------------------------------------------------------------


@step(name="review_draft")
async def review_draft(data: dict[str, Any]) -> dict[str, Any]:
    """Score the draft via the reviewer prompt."""
    inp = SpecInput.model_validate(data["input"])
    draft = SpecDraft.model_validate(data["draft"])

    prompt_def = _prompts.get("spec-writer/reviewer")
    messages = prompt_def.compile(
        variables={
            "spec_type": inp.spec_type,
            "language": inp.language,
            "markdown": draft.markdown,
        }
    )
    result = await _models.generate(
        messages=messages,
        model=prompt_def.config.model,
        temperature=prompt_def.config.temperature,
        max_tokens=prompt_def.config.max_tokens,
    )
    raw = result.output.text or "{}"
    parsed = _safe_json_loads(raw)

    try:
        score = float(parsed.get("score", 0.0) or 0.0)
    except (TypeError, ValueError):
        score = 0.0

    review = SpecReview(
        is_acceptable=bool(parsed.get("is_acceptable") or score >= 7.0),
        score=max(0.0, min(10.0, score)),
        missing_sections=[str(m) for m in (parsed.get("missing_sections") or []) if m],
        questions=[str(q) for q in (parsed.get("questions") or []) if q],
        suggestions=[str(s) for s in (parsed.get("suggestions") or []) if s],
    )

    logger.info(
        "spec_writer.review_draft.done",
        score=review.score,
        is_acceptable=review.is_acceptable,
        missing=len(review.missing_sections),
        cost=round(result.cost_usd, 6),
    )

    return {**data, "review": review.model_dump(), "review_cost": result.cost_usd}


# ---------------------------------------------------------------------------
# Step 5 — finalize
# ---------------------------------------------------------------------------


@step(name="finalize")
async def finalize(data: dict[str, Any]) -> dict[str, Any]:
    """Bundle requirement + draft + review into the final SpecOutput."""
    requirement = SpecRequirement.model_validate(data["requirement"])
    draft = SpecDraft.model_validate(data["draft"])
    review = SpecReview.model_validate(data["review"])

    output = SpecOutput(
        requirement=requirement,
        draft=draft,
        review=review,
        final_markdown=draft.markdown,
    )
    logger.info(
        "spec_writer.finalize.done",
        title=output.draft.title,
        score=output.review.score,
    )
    return output.model_dump()


# ---------------------------------------------------------------------------
# Workflow definition
# ---------------------------------------------------------------------------


@workflow(name="spec-writer", version="1.0.0", skill="spec_writer")
def spec_writing(wf: WorkflowBuilder) -> None:
    """Five-step DAG: analyze → select_template → generate_draft → review_draft → finalize."""
    wf.step(analyze)
    wf.step(select_template, depends_on=["analyze"])
    wf.step(generate_draft, depends_on=["select_template"])
    wf.step(review_draft, depends_on=["generate_draft"])
    wf.step(finalize, depends_on=["review_draft"])


# ---------------------------------------------------------------------------
# Convenience runner (used by CLI + adapter)
# ---------------------------------------------------------------------------


async def run_spec_writing(inp: SpecInput) -> SpecOutput:
    """Execute the full spec-writing DAG in-process and return a SpecOutput."""
    data: dict[str, Any] = {"input": inp.model_dump()}
    data = await analyze(data)
    data = await select_template(data)
    data = await generate_draft(data)
    data = await review_draft(data)
    final = await finalize(data)
    return SpecOutput.model_validate(final)
