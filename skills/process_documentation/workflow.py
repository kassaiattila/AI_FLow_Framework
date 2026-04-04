"""Process Documentation workflow - BPMN extraction pipeline.

Pipeline: classify -> elaborate -> extract -> review -> generate_diagram
Each step closes over module-level models_client and prompt_manager.
"""
from __future__ import annotations

import json
from pathlib import Path

import structlog
from skills.process_documentation import models_client, prompt_manager
from skills.process_documentation.models import (
    ClassifyOutput,
    ProcessExtraction,
    ReviewOutput,
)
from skills.process_documentation.tools.drawio_exporter import DrawioExporter
from skills.process_documentation.tools.kroki_renderer import KrokiRenderer

from aiflow.engine.step import step
from aiflow.engine.workflow import WorkflowBuilder, workflow

__all__ = [
    "classify_intent",
    "elaborate",
    "extract",
    "review",
    "generate_diagram",
    "export_all",
    "reject",
    "process_documentation",
]

logger = structlog.get_logger(__name__)


@step(name="classify_intent", description="Classify user input as process or off-topic")
async def classify_intent(data: dict) -> dict:
    """Classify whether input describes a business process."""
    user_input = data.get("user_input", "")

    prompt = prompt_manager.get("process-doc/classifier")
    messages = prompt.compile(variables={"message": user_input})

    result = await models_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
        response_model=ClassifyOutput,
    )

    output = result.output.structured
    logger.info(
        "classify_result",
        category=output.category,
        confidence=output.confidence,
    )
    return {
        "category": output.category,
        "confidence": output.confidence,
        "reasoning": output.reasoning,
        "user_input": user_input,
    }


@step(name="elaborate", description="Expand terse process description")
async def elaborate(data: dict) -> dict:
    """Elaborate a terse process description into detailed steps."""
    raw_input = data.get("user_input", "")
    context = data.get("context", "")

    prompt = prompt_manager.get("process-doc/elaborator")
    messages = prompt.compile(variables={
        "raw_input": raw_input,
        "context": context,
    })

    result = await models_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
    )

    elaborated = result.output.text
    logger.info("elaborate_result", input_len=len(raw_input), output_len=len(elaborated))
    return {
        "elaborated_text": elaborated,
        "original_input": raw_input,
    }


@step(name="extract", description="Extract BPMN process structure")
async def extract(data: dict) -> dict:
    """Extract structured BPMN process from elaborated text."""
    process_description = data.get("elaborated_text", data.get("user_input", ""))

    prompt = prompt_manager.get("process-doc/extractor")
    messages = prompt.compile(variables={
        "process_description": process_description,
    })

    result = await models_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
        response_model=ProcessExtraction,
    )

    extraction = result.output.structured
    validation_errors = extraction.validate_connections()
    if validation_errors:
        logger.warning("extraction_validation_errors", errors=validation_errors)

    logger.info(
        "extract_result",
        title=extraction.title,
        steps=len(extraction.steps),
        actors=len(extraction.actors),
    )
    return {
        "extraction": extraction.model_dump(mode="json"),
        "validation_errors": validation_errors,
        "original_input": data.get("original_input", ""),
    }


@step(name="review", description="Quality gate for extraction")
async def review(data: dict) -> dict:
    """Review extraction quality and score it."""
    extraction_dict = data.get("extraction", {})
    original_input = data.get("original_input", "")

    extraction = ProcessExtraction(**extraction_dict)
    steps_count = len(extraction.steps)
    actors_count = len(extraction.actors)

    prompt = prompt_manager.get("process-doc/reviewer")
    messages = prompt.compile(variables={
        "original_description": original_input,
        "extraction_json": json.dumps(extraction_dict, ensure_ascii=False, indent=2),
        "steps_count": str(steps_count),
        "actors_count": str(actors_count),
    })

    result = await models_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
        response_model=ReviewOutput,
    )

    review_output = result.output.structured
    logger.info(
        "review_result",
        score=review_output.score,
        is_acceptable=review_output.is_acceptable,
    )

    return {
        "extraction": extraction_dict,
        "review": review_output.model_dump(mode="json"),
        "original_input": original_input,
    }


@step(name="generate_diagram", description="Generate Mermaid flowchart")
async def generate_diagram(data: dict) -> dict:
    """Generate Mermaid flowchart code from extraction."""
    extraction_dict = data.get("extraction", {})
    extraction = ProcessExtraction(**extraction_dict)

    prompt = prompt_manager.get("process-doc/mermaid_flowchart")
    messages = prompt.compile(variables={
        "title": extraction.title,
        "steps_json": json.dumps(
            [s.model_dump(mode="json") for s in extraction.steps],
            ensure_ascii=False,
            indent=2,
        ),
        "actors_json": json.dumps(
            [a.model_dump(mode="json") for a in extraction.actors],
            ensure_ascii=False,
            indent=2,
        ),
    })

    result = await models_client.generate(
        messages=messages,
        model=prompt.config.model,
        temperature=prompt.config.temperature,
        max_tokens=prompt.config.max_tokens,
    )

    mermaid_code = result.output.text.strip()
    # Strip markdown code fences if present
    if mermaid_code.startswith("```"):
        lines = mermaid_code.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        mermaid_code = "\n".join(lines).strip()

    logger.info("generate_diagram_result", title=extraction.title, code_len=len(mermaid_code))
    return {
        "mermaid_code": mermaid_code,
        "title": extraction.title,
        "extraction": extraction_dict,
    }


@step(name="export_all", description="Export diagram to all formats")
async def export_all(data: dict) -> dict:
    """Export process diagram to multiple formats (mmd, SVG, DrawIO, JSON)."""
    import re

    extraction_dict = data.get("extraction", {})
    mermaid_code = data.get("mermaid_code", "")
    title = data.get("title", "process")
    output_dir = Path(data.get("output_dir", "./test_output"))

    # Slug from title
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s]+", "_", slug).strip("_")[:60]
    export_dir = output_dir / slug
    export_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []

    # 1. Save Mermaid source
    mmd_path = export_dir / "diagram.mmd"
    mmd_path.write_text(mermaid_code, encoding="utf-8")
    saved_files.append(str(mmd_path))

    # 2. Save extraction JSON
    json_path = export_dir / "extraction.json"
    json_path.write_text(
        json.dumps(extraction_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    saved_files.append(str(json_path))

    # 2b. Save review JSON (for subprocess consumers)
    review_dict = data.get("review", {})
    if review_dict:
        review_path = export_dir / "review.json"
        review_path.write_text(
            json.dumps(review_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        saved_files.append(str(review_path))

    # 3. DrawIO XML export (architecture flowchart)
    try:
        extraction = ProcessExtraction(**extraction_dict)
        exporter = DrawioExporter()
        drawio_path = export_dir / "diagram.drawio"
        exporter.export(extraction, output_path=drawio_path)
        saved_files.append(str(drawio_path))
        logger.info("export_drawio.done", path=str(drawio_path))
    except Exception as e:
        logger.warning("export_drawio.failed", error=str(e))

    # 3b. BPMN swimlane DrawIO export
    try:
        extraction = ProcessExtraction(**extraction_dict)
        exporter = DrawioExporter()
        bpmn_path = export_dir / "diagram_bpmn.drawio"
        exporter.export_bpmn(extraction, output_path=bpmn_path)
        saved_files.append(str(bpmn_path))
        logger.info("export_bpmn.done", path=str(bpmn_path))
    except Exception as e:
        logger.warning("export_bpmn.failed", error=str(e))

    # 4. Kroki SVG render (optional - requires Kroki service)
    try:
        renderer = KrokiRenderer()
        if await renderer.is_available():
            svg_path = export_dir / "diagram.svg"
            await renderer.render_to_file(mermaid_code, svg_path, "svg")
            saved_files.append(str(svg_path))
            logger.info("export_svg.done", path=str(svg_path))
        else:
            logger.info("export_svg.skipped", reason="Kroki service not available")
        await renderer.close()
    except Exception as e:
        logger.warning("export_svg.failed", error=str(e))

    # 5. Markdown table
    try:
        extraction = ProcessExtraction(**extraction_dict)
        table_lines = ["# " + title, "", "## Aktorok", ""]
        table_lines.append("| ID | Nev | Szerep |")
        table_lines.append("|-----|------|--------|")
        for a in extraction.actors:
            table_lines.append(f"| {a.id} | {a.name} | {a.role or '-'} |")
        table_lines.extend(["", "## Lepesek", ""])
        table_lines.append("| # | Nev | Tipus | Aktor | Kovetkezo |")
        table_lines.append("|---|------|-------|-------|-----------|")
        for i, s in enumerate(extraction.steps, 1):
            next_s = ", ".join(s.next_steps) if s.next_steps else "-"
            table_lines.append(
                f"| {i} | {s.name} | {s.step_type} | {s.actor or '-'} | {next_s} |"
            )
        md_path = export_dir / "process_table.md"
        md_path.write_text("\n".join(table_lines), encoding="utf-8")
        saved_files.append(str(md_path))
    except Exception as e:
        logger.warning("export_table.failed", error=str(e))

    logger.info("export_all.done", files=len(saved_files), dir=str(export_dir))
    return {
        "export_dir": str(export_dir),
        "saved_files": saved_files,
        "mermaid_code": mermaid_code,
        "extraction": extraction_dict,
        "title": title,
    }


@step(name="reject", description="Return rejection message")
async def reject(data: dict) -> dict:
    """Return rejection for non-process input."""
    return {
        "rejected": True,
        "reason": data.get("reasoning", "Input is not a business process description."),
        "category": data.get("category", "reject"),
    }


@workflow(name="process-documentation", version="2.0.0", skill="process_documentation")
def process_documentation(wf: WorkflowBuilder) -> None:
    """Natural language -> structured BPMN documentation + diagrams."""
    wf.step(classify_intent)
    wf.step(elaborate, depends_on=["classify_intent"])
    wf.step(extract, depends_on=["elaborate"])
    wf.step(review, depends_on=["extract"])
    wf.step(generate_diagram, depends_on=["review"])
    wf.step(export_all, depends_on=["generate_diagram"])
