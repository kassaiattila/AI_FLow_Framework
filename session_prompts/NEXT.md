# AIFlow [Sprint V] — Session SV-1 Prompt (Document Recognizer kickoff)

> **Datum:** 2026-04-26 (snapshot date — adjust if session runs later)
> **Branch:** `feature/v-sv1-doc-recognizer-contracts` (cut from `main` after the Sprint U S157 close PR squash-merges → new tip).
> **HEAD (expected):** Sprint U S157 close PR squash on top of `f5c0234` (Sprint U S156 squash).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S157 — Sprint U close. `docs/sprint_u_retro.md` + `docs/sprint_u_pr_description.md` + `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` + CLAUDE.md banner flip + tag `v1.5.4` queued.
> **Terv:** `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` §2 / SV-1 row.
> **Session tipus:** IMPLEMENTATION (foundation layer — contracts + safe-eval + skill rename, zero LLM, zero DB).

---

## 1. MISSION

Sprint V's foundation layer. The session that everything else builds on — pure-Python contracts, the DocTypeRegistry skeleton, the safe-expression-eval engine, and the skill rename `invoice_finder` → `document_recognizer` (preserving git history). **Zero LLM call. Zero DB write. Zero new endpoint.** SV-2 wires up the classifier; SV-3 ships the API; SV-4 the admin UI; SV-5 the corpora + accuracy gates + close.

### Five deliverables

1. **Contracts** — `src/aiflow/contracts/doc_recognition.py` (~150 LOC, 8 Pydantic class): `DocRecognitionRequest`, `DocTypeMatch`, `DocFieldValue`, `DocExtractionResult`, `DocIntentDecision`, `DocTypeDescriptor`, `RuleSpec`, `IntentRoutingRule`. Per the design in `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` "YAML descriptor minta — `hu_invoice`" + "Field types + validators".
2. **DocTypeRegistry skeleton** — `src/aiflow/services/document_recognizer/registry.py`: YAML loader (`data/doctypes/<name>.yaml`), per-tenant override loader (`data/doctypes/_tenant/<tenant_id>/<name>.yaml`), `register_doctype` / `list_doctypes(tenant_id?)` / `get_doctype(name, tenant_id?)`. **No actual descriptors loaded yet** (those land in SV-2); validation that the loader correctly rejects malformed YAML.
3. **Safe-expression-eval** — `src/aiflow/services/document_recognizer/safe_eval.py` (~80 LOC): wraps `simpleeval` (pinned version added to `pyproject.toml` as a new optional dependency). Restricted operator list (`==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`, `in`); restricted name space (`extracted.<field>`, `field_confidence_min`, `field_confidence_max`, `doc_type_confidence`, `pii_detected`). **NOT Python `eval()`**.
4. **Skill rename** — `git mv skills/invoice_finder skills/document_recognizer` (preserves history). Update `skill.yaml` (`name: document_recognizer`, `display_name: "Document Recognizer"`). Stub `__init__.py` + `__main__.py`. Skeleton `workflows/recognize_and_extract.py` + `prompts/doctype_classifier.yaml` (placeholder DAG, no LLM call yet).
5. **`invoice_finder` deprecated alias** — `skills/invoice_finder/__init__.py` re-exports from `skills.document_recognizer` + emits `DeprecationWarning` on first import. Keeps old imports compiling for one minor version. (Optional: full delete in Sprint W.)

### Out of scope for SV-1

- Any classifier rule engine code (SV-2 scope).
- Any actual descriptor YAML in `data/doctypes/` (SV-2 scope).
- `id_card_extraction_chain.yaml` PromptWorkflow descriptor (SV-2 scope).
- API router (SV-3 scope).
- Alembic migration `048` (SV-3 scope).
- Admin UI page (SV-4 scope).
- Per-doctype golden-path corpora (SV-5 scope).
- Sprint U follow-ups (SU-FU-1..4 are post-Sprint-V).

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint U closed 2026-04-26. Operational hardening + carry-forward catch-up shipped across 5 PRs in 2 calendar days. Sprint V's headline scope (generic document recognizer skill, 5 doc-types initially) was published in `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` at S157 close.

### Hova tartunk

SV-1 → SV-2 (classifier + 2 doctype) → SV-3 (API + Alembic 048 + 2 doctype) → SV-4 (admin UI + 1 doctype + Playwright) → SV-5 (corpus + accuracy gate + close + tag `v1.6.0`).

### Jelenlegi állapot

```
27 service | 196 endpoint (31 routers) | 50 DB tabla | 47 Alembic (head: 047)
2475 unit collected / 1 skipped (ST-SKIP-1 conditional Azure Profile B)
~116 integration | 432 e2e collected
26 UI oldal | 8 skill | 22 pipeline adapter
5 PromptWorkflow descriptors live (email_intent_chain, invoice_extraction_chain, aszf_rag_chain baseline, aszf_rag_chain_expert, aszf_rag_chain_mentor)
4 ci.yml jobs | 5 nightly-regression.yml jobs | 1 pre-commit hook
Default-off rollout preserved.
```

### Key files for SV-1

| Role | Path |
|---|---|
| Sprint V plan | `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` (§2 / SV-1 row, §3 gate matrix) |
| Audit + design depth | `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` (full descriptor examples, intent routing semantics, multi-tenancy) |
| Sprint U retro | `docs/sprint_u_retro.md` (open SU-FU-1..4 — none block SV-1) |
| Existing reusable contracts | `src/aiflow/contracts/cost_attribution.py`, `intake_package.py`, `routing_decision.py`, `extraction_result.py` |
| Reusable services | `src/aiflow/services/document_extractor/`, `src/aiflow/services/classifier/`, `src/aiflow/guardrails/cost_preflight.py` |
| Reusable PromptWorkflow | `src/aiflow/prompts/workflow.py`, `workflow_executor.py` |
| Skill being renamed | `skills/invoice_finder/` |
| Target skill location | `skills/document_recognizer/` (after `git mv`) |

---

## 3. ELOFELTETELEK

```bash
git switch main
git pull --ff-only origin main
git checkout -b feature/v-sv1-doc-recognizer-contracts
git log --oneline -5                                                # confirm S157 close squash on tip
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current           # head: 047
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1  # 2475 collected
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/ --quiet
ls skills/invoice_finder/                                           # confirm skill exists pre-rename
# SU-FU-4 first action (UC1 full-corpus issue_date verification — operator-discretion):
# .venv/Scripts/python.exe scripts/measure_uc1_golden_path.py --output text | grep issue_date
```

Stop, ha:
- Sprint U S157 close PR not yet merged → wait or escalate.
- Alembic head ≠ 047 → drift; investigate before opening SV-1.
- `skills/invoice_finder/` missing → triage before authoring rename.
- `git status` dirty → finish or stash first.
- SU-FU-4 verification (if run) reports `issue_date` < 90% on full 10-fixture corpus → halt, raise issue, defer SV-1 until Sprint Q polish is verified live.

---

## 4. FELADATOK

### LEPES 1 — Contracts (`src/aiflow/contracts/doc_recognition.py`)

Author 8 Pydantic classes per `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` "Field types + validators" + "Intent routing semantics":

1. `DocRecognitionRequest` — `file_path: Path | None`, `file_bytes: bytes | None`, `tenant_id: str`, `doc_type_hint: str | None`, `filename: str | None`. Validator: at least one of `file_path` / `file_bytes` must be set.
2. `DocTypeMatch` — `doc_type: str`, `confidence: float` (0..1), `alternatives: list[tuple[str, float]]` (top-3, sorted desc). Validator: confidence + alternatives don't sum to > 1.0.
3. `DocFieldValue` — `value: str | int | float | bool | None`, `confidence: float`, `source_text_hint: str | None` (first 200 chars of the source span if available).
4. `DocExtractionResult` — `doc_type: str`, `extracted_fields: dict[str, DocFieldValue]`, `validation_warnings: list[str]`, `cost_usd: float`.
5. `DocIntentDecision` — `intent: Literal["process","route_to_human","rag_ingest","respond","reject"]`, `reason: str`, `next_action: str | None`.
6. `DocTypeDescriptor` — full descriptor model. `name: str`, `display_name: str`, `description: str | None`, `language: str`, `category: str`, `version: int`, `pii_level: Literal["low","medium","high"] = "low"`, `parser_preferences: list[str]`, `type_classifier: TypeClassifierConfig`, `extraction: ExtractionConfig`, `intent_routing: IntentRoutingConfig`. With nested config classes — keep them in the same module for now; later can split.
7. `RuleSpec` — `kind: Literal["regex","keyword_list","structure_hint","filename_match","parser_metadata"]`, `pattern: str | None`, `keywords: list[str] | None`, `threshold: int | None`, `hint: str | None`, `weight: float` (0..1). Validator: kind-appropriate fields are set.
8. `IntentRoutingRule` — `if_expr: str`, `intent: str` (matches `DocIntentDecision.intent` literal), `reason: str`.

Tests: round-trip Pydantic JSON serialize → deserialize for all 8 classes. Validator failure cases for 4 classes (3 minimum from RuleSpec + DocRecognitionRequest + DocTypeMatch + IntentRoutingRule).

### LEPES 2 — DocTypeRegistry skeleton (`src/aiflow/services/document_recognizer/registry.py`)

```python
class DocTypeRegistry:
    def __init__(self, bootstrap_dir: Path, tenant_overrides_dir: Path | None = None) -> None: ...
    def list_doctypes(self, tenant_id: str | None = None) -> list[DocTypeDescriptor]: ...
    def get_doctype(self, name: str, tenant_id: str | None = None) -> DocTypeDescriptor | None: ...
    def register_doctype(self, descriptor: DocTypeDescriptor, tenant_id: str | None = None) -> None: ...
```

Loader behavior:
- Bootstrap descriptors loaded from `data/doctypes/<name>.yaml` on first `list_doctypes()` call (lazy + cached).
- Per-tenant override at `data/doctypes/_tenant/<tenant_id>/<name>.yaml` overrides the bootstrap when `tenant_id` is supplied.
- Invalid YAML / Pydantic parse error → log warning + audit log entry + skip that descriptor (do NOT raise; service must keep working).

Tests: empty bootstrap dir → empty list. Mock bootstrap dir with 2 valid YAML → list returns 2. Tenant override → `get_doctype(name, tenant_id)` returns override; `get_doctype(name)` returns bootstrap. Invalid YAML → warning + skip + remaining valid descriptors load.

### LEPES 3 — Safe-expression-eval (`src/aiflow/services/document_recognizer/safe_eval.py`)

```python
def safe_eval_intent_rule(
    if_expr: str,
    extracted_fields: dict[str, DocFieldValue],
    doc_type_confidence: float,
    pii_detected: bool = False,
) -> bool: ...
```

Implementation:
- Use `simpleeval` (`uv pip install simpleeval`); add to `pyproject.toml` `[project.dependencies]`
- Restricted name space: `extracted.<field>` resolves to `extracted_fields[field].value`; computed names: `field_confidence_min`, `field_confidence_max`, `doc_type_confidence`, `pii_detected`
- Restricted operators: `==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`, `in`
- Disallowed: function calls, attribute access on arbitrary objects, dunder access, `lambda`, comprehensions

Tests: `if_expr="extracted.total_gross > 1000000"` evaluates correctly. `if_expr="field_confidence_min < 0.6"` evaluates correctly. `if_expr="__import__('os').system('rm -rf /')"` raises (security). `if_expr="invalid syntax !"` raises (parse error). Empty `extracted_fields` does not crash on `extracted.foo > 0` (returns False or raises NameError — pick one and document).

### LEPES 4 — Skill rename `invoice_finder` → `document_recognizer`

```bash
git mv skills/invoice_finder skills/document_recognizer
```

Update:
- `skills/document_recognizer/skill.yaml` — `name: document_recognizer`, `display_name: "Document Recognizer"`, `description: "Generic doc-type recognition + extraction"`, version bump
- `skills/document_recognizer/__init__.py` — entry point, sets `SKILL_NAME = "document_recognizer"`
- `skills/document_recognizer/__main__.py` — CLI entry stub
- `skills/document_recognizer/workflows/recognize_and_extract.py` — skeleton workflow (raises `NotImplementedError` for now; SV-2 fills it in)
- `skills/document_recognizer/prompts/doctype_classifier.yaml` — placeholder PromptDefinition (system + user template stubs)

Verify imports compile:
```bash
PYTHONPATH=src .venv/Scripts/python.exe -c "from skills.document_recognizer import SKILL_NAME; print(SKILL_NAME)"
```

### LEPES 5 — `invoice_finder` deprecated alias

Create `skills/invoice_finder/__init__.py` (just this one file — the rest of the dir was moved):

```python
"""DEPRECATED: skill renamed to ``document_recognizer`` in Sprint V (v1.6.0).

This shim re-exports the new entry point + emits DeprecationWarning on first
import. Will be deleted in Sprint W (v1.7.0).
"""
import warnings

warnings.warn(
    "skills.invoice_finder is deprecated; use skills.document_recognizer instead. "
    "This shim will be removed in v1.7.0.",
    DeprecationWarning,
    stacklevel=2,
)

from skills.document_recognizer import *  # noqa: F401, F403
from skills.document_recognizer import SKILL_NAME  # noqa: F401
```

Verify:
```bash
PYTHONPATH=src .venv/Scripts/python.exe -W default::DeprecationWarning -c "import skills.invoice_finder"
# Expected: DeprecationWarning: skills.invoice_finder is deprecated; ...
```

### LEPES 6 — Validate + commit + push + PR

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/ --quiet
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1   # +18 unit (~2493)
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/contracts/test_doc_recognition.py tests/unit/services/document_recognizer/ -v
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/skills/document_recognizer/ -v

git add src/aiflow/contracts/doc_recognition.py \
        src/aiflow/services/document_recognizer/ \
        skills/document_recognizer/ \
        skills/invoice_finder/__init__.py \
        tests/unit/contracts/test_doc_recognition.py \
        tests/unit/services/document_recognizer/ \
        tests/unit/skills/document_recognizer/ \
        pyproject.toml
git commit -m "feat(sprint-v): SV-1 — Document Recognizer contracts + safe-eval + skill rename"
git push -u origin feature/v-sv1-doc-recognizer-contracts
gh pr create --base main --head feature/v-sv1-doc-recognizer-contracts \
  --title "Sprint V SV-1 — Document Recognizer contracts + safe-eval + skill rename"
```

Then `/session-close SV-1` — which queues SV-2 (classifier + 2 doctype kickoff).

---

## 5. STOP FELTETELEK

**HARD:**
1. `simpleeval` library install fails on Windows / air-gap CI → halt; pick alternative (write a small custom restricted-AST evaluator) and re-plan.
2. Skill rename `git mv` corrupts history (Windows long-path or symlink edge case) → halt; manual cherry-pick or split into two commits.
3. `from skills.invoice_finder` import hard-fails after the deprecated-alias shim ships → fix shim re-exports before SV-1 PR.
4. Pydantic round-trip test fails on any of the 8 contracts → fix model definition, do not commit.
5. ruff finds an issue → fix before commit (pre-commit hook will block anyway).

**SOFT:**
- Safe-eval `simpleeval` is too restrictive for some legitimate `if_expr` patterns the operator wants → SOFT halt; document the limitation in `safe_eval.py` docstring + accept narrower grammar.
- Skill rename causes a flake in unrelated tests because of the deprecated-alias warning → suppress the warning in `tests/conftest.py` for the duration of SV-1; revisit in SV-2.

---

## 6. SESSION VEGEN

```
/session-close SV-1
```

The `/session-close` will:
- Validate lint + unit collect.
- Stage + commit the doc-recognizer foundation diff (contracts + registry + safe-eval + skill rename + alias shim).
- Push the branch.
- Open the PR.
- Generate `session_prompts/NEXT.md` for SV-2 — the classifier + 2 doctype kickoff session.

---

## 7. SKIPPED-ITEMS TRACKER (carry from Sprint U S157)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SU-SKIP-1 | `.github/workflows/nightly-regression.yml` `uc3-4combo-matrix` | Weekly job skip-by-default on PR runs | `secrets.OPENAI_API_KEY` + scheduled trigger |
| SU-SKIP-2 (planned) | `tests/ui-live/prompt-workflows.md` (S155 rescope) | Live Playwright `/prompts/workflows` deferred | Sprint V SV-4 admin UI work or post-Sprint-V |
| SS-SKIP-2 | `tests/integration/services/rag_engine/test_retrieval_baseline.py::test_retrieval_baseline_profile_b_openai` | Profile B Azure live MRR@5 measurement | Azure credit |
| SV-SKIP-1 (planned, SV-2) | `tests/integration/services/document_recognizer/test_classifier_real.py` | Real-LLM classifier accuracy on 25-fixture corpus | `secrets.OPENAI_API_KEY` + scheduled (Mon 08:00 UTC weekly, after `uc3-4combo-matrix` at 07:00) |
| SV-SKIP-2 (planned, SV-4) | `tests/ui-live/document-recognizer.md` | Live Playwright spec on doc-recognizer page | Live admin stack (`bash scripts/start_stack.sh --full`) |

SU-FU-1..4 (operator-script `--output`, `scripts/` ruff cleanup, Alembic 048 invoice_date rename, UC1 full-corpus verification) are tracked in `docs/sprint_u_retro.md` — SU-FU-4 is the recommended SV-1 first action (operator discretion).

SV-1 hits contracts + service registry skeleton + safe-eval + skill rename + deprecated alias. SV-2+ continues per the Sprint V plan.
