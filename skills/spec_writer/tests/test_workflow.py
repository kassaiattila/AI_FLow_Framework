"""
@test_registry:
    suite: spec-writer-unit
    component: skills.spec_writer.workflows.spec_writing
    covers: [skills/spec_writer/workflows/spec_writing.py]
    phase: B5.2
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [spec_writer, workflow, llm-mocked, b5]
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from skills.spec_writer.models import (
    SpecDraft,
    SpecInput,
    SpecOutput,
    SpecRequirement,
    SpecReview,
)

from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.generation import GenerationOutput

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wrap(text: str) -> ModelCallResult:
    """Fake ModelCallResult that carries the given text verbatim."""
    return ModelCallResult(
        output=GenerationOutput(text=text, model_used="mock-gpt"),
        model_used="mock-gpt",
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.0001,
        latency_ms=1.0,
    )


ANALYZER_OK_HU = json.dumps(
    {
        "title": "Szamla feldolgozas",
        "description": "Bejovo szamlak automatikus feldolgozasa.",
        "actors": ["konyvelo", "rendszer"],
        "goals": ["Szamlaadatok extrakcioja", "Duplikatumok szurese"],
        "constraints": ["HU AAM tamogatas"],
        "inputs": [{"name": "pdf_file", "type": "file", "description": "Szamla PDF"}],
        "outputs": [
            {"name": "invoice", "type": "object", "description": "Strukturalt adatok"}
        ],
        "edge_cases": ["Homalyos PDF", "Tobb oldalas szamla"],
    }
)

GENERATOR_OK_HU_FEATURE = """# Szamla feldolgozas

## Attekintes
Bejovo szamlak automatikus feldolgozasa.

## Celok
- Szamlaadatok extrakcioja
- Duplikatumok szurese

## Bemenetek
- pdf_file (file): Szamla PDF

## Kimenetek
- invoice (object): Strukturalt adatok

## Peremfeltetelek
- Homalyos PDF
- Tobb oldalas szamla

## Elfogadasi feltetelek
- 95% pontossag
- Max 10s feldolgozas
"""

REVIEWER_OK = json.dumps(
    {
        "is_acceptable": True,
        "score": 8.5,
        "missing_sections": [],
        "questions": [],
        "suggestions": ["OCR minoseg meressel gazdagitsd"],
    }
)

REVIEWER_LOW = json.dumps(
    {
        "is_acceptable": False,
        "score": 4.0,
        "missing_sections": ["edge_cases", "acceptance"],
        "questions": ["Mi tortenik hiba eseten?"],
        "suggestions": ["Add hozza a peremfelteteleket"],
    }
)


ANALYZER_OK_EN_API = json.dumps(
    {
        "title": "POST /invoices",
        "description": "Create an invoice resource.",
        "actors": ["api_client"],
        "goals": ["Persist new invoice", "Return 201"],
        "constraints": [],
        "inputs": [
            {"name": "body", "type": "object", "description": "InvoiceCreate payload"}
        ],
        "outputs": [
            {"name": "invoice", "type": "object", "description": "Created invoice"}
        ],
        "edge_cases": ["Duplicate invoice_number"],
    }
)

GENERATOR_OK_EN_API = """# POST /invoices

## Endpoint
`POST /api/v1/invoices`

## Request
Body: `InvoiceCreate`

## Response
- 201 Created with invoice
- 409 Conflict on duplicate

## Error Codes
- 400 validation
- 409 duplicate

## Examples
curl -XPOST ...
"""


ANALYZER_OK_STORY = json.dumps(
    {
        "title": "User can filter invoices",
        "description": "Filter by vendor + date range.",
        "actors": ["accountant"],
        "goals": ["Find invoices faster"],
        "constraints": [],
        "inputs": [],
        "outputs": [],
        "edge_cases": [],
    }
)

GENERATOR_OK_STORY = """# User can filter invoices

## As a
accountant

## I want
to filter invoices by vendor and date range

## So that
I can find invoices faster

## Acceptance Criteria
- filter persists across sessions
- max 100 results per page
"""


def _install_models_stub(monkeypatch: pytest.MonkeyPatch, generations: list[str]) -> MagicMock:
    """Replace the module-level _models with a mock returning `generations` in order."""
    from skills.spec_writer.workflows import spec_writing

    fake = MagicMock()
    fake.generate = AsyncMock(side_effect=[_wrap(t) for t in generations])
    monkeypatch.setattr(spec_writing, "_models", fake)
    return fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSpecWriterWorkflow:
    @pytest.mark.asyncio
    async def test_analyze_structures_requirement(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """analyze() turns raw_text into a well-formed SpecRequirement."""
        from skills.spec_writer.workflows.spec_writing import analyze

        _install_models_stub(monkeypatch, [ANALYZER_OK_HU])

        result = await analyze(
            {
                "input": SpecInput(
                    raw_text="Szamla feldolgozas automatizalva",
                    spec_type="feature",
                    language="hu",
                ).model_dump()
            }
        )

        req = SpecRequirement.model_validate(result["requirement"])
        assert req.title == "Szamla feldolgozas"
        assert "Szamlaadatok extrakcioja" in req.goals
        assert len(req.inputs) == 1
        assert req.inputs[0].name == "pdf_file"
        assert len(req.edge_cases) == 2

    @pytest.mark.asyncio
    async def test_generate_draft_hu_feature(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """generate_draft() writes a feature spec with '## Celok' and inputs table."""
        from skills.spec_writer.workflows.spec_writing import (
            analyze,
            generate_draft,
            select_template,
        )

        _install_models_stub(monkeypatch, [ANALYZER_OK_HU, GENERATOR_OK_HU_FEATURE])

        data = await analyze(
            {
                "input": SpecInput(
                    raw_text="Szamla feldolgozas", spec_type="feature", language="hu"
                ).model_dump()
            }
        )
        data = await select_template(data)
        data = await generate_draft(data)

        draft = SpecDraft.model_validate(data["draft"])
        assert draft.spec_type == "feature"
        assert draft.language == "hu"
        assert "## Celok" in draft.markdown
        assert "## Bemenetek" in draft.markdown
        assert draft.sections_count >= 5

    @pytest.mark.asyncio
    async def test_generate_draft_en_api(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """API spec path in English emits '## Endpoint' / '## Request' / '## Response'."""
        from skills.spec_writer.workflows.spec_writing import (
            analyze,
            generate_draft,
            select_template,
        )

        _install_models_stub(monkeypatch, [ANALYZER_OK_EN_API, GENERATOR_OK_EN_API])

        data = await analyze(
            {
                "input": SpecInput(
                    raw_text="POST /invoices endpoint",
                    spec_type="api",
                    language="en",
                ).model_dump()
            }
        )
        data = await select_template(data)
        data = await generate_draft(data)

        draft = SpecDraft.model_validate(data["draft"])
        assert "## Endpoint" in draft.markdown
        assert "## Request" in draft.markdown
        assert "## Response" in draft.markdown
        assert draft.spec_type == "api"

    @pytest.mark.asyncio
    async def test_review_acceptable_score(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """review_draft() flags is_acceptable=True for score >= 7."""
        from skills.spec_writer.workflows.spec_writing import review_draft

        _install_models_stub(monkeypatch, [REVIEWER_OK])

        data: dict[str, Any] = {
            "input": SpecInput(
                raw_text="x", spec_type="feature", language="hu"
            ).model_dump(),
            "draft": SpecDraft(
                title="Test",
                spec_type="feature",
                language="hu",
                markdown="## Celok\n- goal",
                sections_count=1,
                word_count=4,
            ).model_dump(),
        }

        out = await review_draft(data)
        review = SpecReview.model_validate(out["review"])

        assert review.is_acceptable is True
        assert review.score == pytest.approx(8.5)
        assert review.missing_sections == []

    @pytest.mark.asyncio
    async def test_review_missing_sections(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """review_draft() surfaces missing_sections + questions when score is low."""
        from skills.spec_writer.workflows.spec_writing import review_draft

        _install_models_stub(monkeypatch, [REVIEWER_LOW])

        data: dict[str, Any] = {
            "input": SpecInput(
                raw_text="x", spec_type="feature", language="hu"
            ).model_dump(),
            "draft": SpecDraft(
                title="Test",
                spec_type="feature",
                language="hu",
                markdown="## Celok\n",
                sections_count=1,
                word_count=1,
            ).model_dump(),
        }

        out = await review_draft(data)
        review = SpecReview.model_validate(out["review"])

        assert review.is_acceptable is False
        assert review.score == pytest.approx(4.0)
        assert "edge_cases" in review.missing_sections
        assert len(review.questions) >= 1

    @pytest.mark.asyncio
    async def test_full_pipeline_integration_hu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """run_spec_writing() chains all 5 steps and returns a complete SpecOutput."""
        from skills.spec_writer.workflows.spec_writing import run_spec_writing

        _install_models_stub(
            monkeypatch,
            [ANALYZER_OK_HU, GENERATOR_OK_HU_FEATURE, REVIEWER_OK],
        )

        inp = SpecInput(
            raw_text="Szamla feldolgozas automatizalva",
            spec_type="feature",
            language="hu",
        )
        result = await run_spec_writing(inp)

        assert isinstance(result, SpecOutput)
        assert result.requirement.title == "Szamla feldolgozas"
        assert "## Celok" in result.final_markdown
        assert result.review.is_acceptable is True
        assert result.review.score >= 7.0

    @pytest.mark.asyncio
    async def test_full_pipeline_integration_user_story(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """user_story template emits 'As a' / 'I want' / 'Acceptance Criteria'."""
        from skills.spec_writer.workflows.spec_writing import run_spec_writing

        _install_models_stub(
            monkeypatch,
            [ANALYZER_OK_STORY, GENERATOR_OK_STORY, REVIEWER_OK],
        )

        result = await run_spec_writing(
            SpecInput(
                raw_text="accountant wants to filter invoices",
                spec_type="user_story",
                language="en",
            )
        )

        assert "## As a" in result.final_markdown
        assert "## I want" in result.final_markdown
        assert "## Acceptance Criteria" in result.final_markdown
        assert result.draft.spec_type == "user_story"
