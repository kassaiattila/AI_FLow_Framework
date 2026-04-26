# AIFlow [Post-Sprint-V] — Audit gate session prompt

> **Datum:** 2026-04-26 (post Sprint V close, tag `v1.6.0` queued)
> **Branch:** TBD (cut from `main` after the Sprint V SV-5 close PR squash-merges).
> **HEAD (expected):** Sprint V SV-5 close PR squash on top of `b4a0358` (SV-4 squash).
> **Port:** API 8102 | UI 5173
> **Elozo session:** SV-5 — Sprint V close. `docs/sprint_v_retro.md` + `docs/sprint_v_pr_description.md` + CLAUDE.md banner flip + `data/fixtures/doc_recognizer/` + `scripts/measure_doc_recognizer_accuracy.py` + 2 CI jobs (PR-time + weekly) + tag `v1.6.0` queued.
> **Audit reference:** `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` §9 Post-Sprint-V audit gate (DEFER) + `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` §"Post-Sprint-V audit gate".
> **Session tipus:** AUDIT (no code change; produces Sprint W kickoff plan).

---

## 1. MISSION

Per the Sprint V plan §9: **after Sprint V's gate green, audit the "professzionális működéshez szükséges struktúra" topics** and produce the Sprint W kickoff plan + post-v1.6 roadmap. Sprint V is now green (5 PRs merged, 100% top-1 starter accuracy, UC1/2/3 unchanged, OpenAPI drift `[ok]`); this is the trigger.

**Highest-priority audit topic per Sprint V retro:** SV-FU-4 — wire the real PromptWorkflow extraction step into `recognize_and_extract` so the recognize endpoint produces fields, not just a doc-type match. This unblocks operator usage of the doc_recognizer in production.

### Audit topics (Sprint W kickoff candidates)

From `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` §9 + Sprint V retro:

1. **SV-FU-4** — Real PromptWorkflow-driven extraction in the orchestrator (highest priority)
2. **SV-FU-1** — Real-document fixture corpus extension (5 per doctype = 25 anonymized real PDFs/scans)
3. **SV-FU-3** — Live Playwright `tests/ui-live/document-recognizer.md` (mirror Sprint N S123 pattern)
4. **SV-FU-6** — Live Playwright `tests/ui-live/prompt-workflows.md` (carried from Sprint U SR-FU-4)
5. **Multi-tenant prod readiness** — Vault AppRole IaC, `AIFLOW_ENV=prod` boot guard, `customer` → `tenant_id` rename
6. **Observability bővítés** — Grafana panels for `cost_guardrail_refused`, `doc_recognizer_intent_distribution`; ci-cross-uc kibővítés UC1-General-rel
7. **Coverage uplift 70% → 80%** (SJ-FU-7 dormant)
8. **Profile B Azure live MRR@5** (SS-SKIP-2 — if credit lands)
9. **UC3 thread-aware classification** (body-only cohort 100% felé — SP-FU-1)
10. **Test corpus expansion** — UC1 25 fixtures + doc_recognizer per-type 10+
11. **Doc_recognizer ML classifier** (kis fasttext / sklearn / kis BERT) replacing rule-engine if accuracy demands
12. **Sprint U `invoice_date` → `issue_date` SQL column rename** (SU-FU-3)
13. **UI bundle size guardrail** in pre-commit hook (SV-FU-2)
14. **Monaco YAML editor** for the DocTypeDetailDrawer (SV-FU-5, if operator feedback demands)

### Audit deliverables

1. `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md` — Sprint W plan covering 4–5 sessions of ranked-priority work.
2. `docs/post_sprint_v_audit.md` — operator-facing audit summary (each topic: scope / risk / effort estimate / SLO target).
3. `session_prompts/NEXT.md` → first Sprint W session prompt (likely SW-1 around SV-FU-4 if approved).

### Out of scope

- Any code change in this session. Audit only.
- Sprint W execution. The audit publishes the plan; Sprint W kickoff session executes against it.

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint V closed 2026-04-26 with 5 PRs merged in 1 calendar day. The generic document recognizer skill ships with 5 initial doctypes scoring 100% top-1 on the 8-fixture synthetic corpus. UC1 byte-stable; the doc_recognizer is additive.

### Hova tartunk

The Sprint V retro identified 6 follow-ups (SV-FU-1..6). Per the audit doc + Sprint V plan §9, this session sequences them + the carry-forwards (Sprint U/S/Q/P/N/M/J residuals) into Sprint W's session list.

### Jelenlegi állapot

```
27 service | 201 endpoint (32 routers) | 51 DB tabla | 48 Alembic (head: 048)
2606 unit collected / 1 skipped (ST-SKIP-1 conditional Azure Profile B)
~116 integration | 432 e2e collected
27 UI oldal | 8 skill | 22 pipeline adapter
6 PromptWorkflow descriptors | 5 doctype descriptors
5 ci.yml jobs | 6 nightly-regression.yml jobs | 1 pre-commit hook
Default-off rollout preserved.
```

### Key files for the audit session

| Role | Path |
|---|---|
| Sprint V plan | `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` (§9 Post-Sprint-V audit gate) |
| Sprint V retro | `docs/sprint_v_retro.md` (SV-FU-1..6 inventory) |
| Audit + design depth | `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` |
| Capability roadmap | `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` (operator priorities) |
| UC trajectory | `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` |
| Carry-forward inventory | All sprint retros: `docs/sprint_*_retro.md` |

---

## 3. ELOFELTETELEK

```bash
git switch main
git pull --ff-only origin main
git log --oneline -5                                              # confirm SV-5 close squash on tip
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current        # head: 048
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1  # 2606 collected
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/ --quiet
PYTHONPATH=src .venv/Scripts/python.exe scripts/measure_doc_recognizer_accuracy.py 2>&1 | tail -10  # 5 doctypes PASS
```

Stop, ha:
- Sprint V SV-5 close PR not yet merged → wait or escalate.
- Alembic head ≠ 048 → drift; investigate before opening the audit session.
- DocRecognizer accuracy drops below SLO on the starter corpus → halt; SV-FU-4 cannot proceed without a stable rule-engine baseline.

---

## 4. FELADATOK (audit, no code)

### LEPES 1 — Read the inputs

- `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` §9 (the deferred audit topics)
- `docs/sprint_v_retro.md` §"Open follow-ups (Sprint W or later)" + §"Carried"
- The 4 most-recent sprint retros (`sprint_t`, `sprint_u`, `sprint_v`) for unresolved carry-forwards.

### LEPES 2 — Score each audit topic

For each topic in the Sprint V plan §9 list + SV-FU-1..6:
- **Scope** — what concretely ships
- **Risk class** — UC1/2/3 regression / endpoint surface / multi-tenant / external dependency
- **Effort** — in session-multiples (1 / 2 / 3+)
- **SLO** — measurable gate at session close
- **Dependencies** — which other Sprint W topics block / are blocked by this

### LEPES 3 — Sequence Sprint W

Pick **4–5 sessions** for Sprint W. Recommended ordering (operator-pickable):

- **SW-1** — SV-FU-4: real PromptWorkflow extraction in `recognize_and_extract` orchestrator. Unblocks doc_recognizer production usage. Highest priority.
- **SW-2** — SV-FU-1 + SV-FU-3: real-document fixture corpus + live Playwright `/document-recognizer` spec. Operator-curated content + UI gate.
- **SW-3** — Multi-tenant prod readiness slice 1: `customer` → `tenant_id` rename + `AIFLOW_ENV=prod` guard. Prep for Vault AppRole.
- **SW-4** — Observability bővítés: Grafana panels + ci-cross-uc UC1-General slot.
- **SW-5** — Sprint W close + tag `v1.7.0` (or queue earlier if scope cuts).

Operator may swap SW-2 ↔ SW-3 depending on tenancy demand vs operator-content readiness.

### LEPES 4 — Author `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md`

Mirror the structure of `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md`:
1. Goal
2. Sessions (4–5 with concrete deliverables, LOC + test estimates)
3. Plan / gate matrix
4. Risk register
5. Definition of done
6. Out of scope (deferred to post-Sprint-W)
7. Skipped tracker

### LEPES 5 — Write `docs/post_sprint_v_audit.md`

Operator-facing summary. Each topic gets a 1-paragraph block: what it is, why it matters now, what changes if we ship it, what changes if we defer.

### LEPES 6 — `session_prompts/NEXT.md` → SW-1

Detailed kickoff prompt for the first Sprint W session.

### LEPES 7 — Validate + commit + push + PR

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/ --quiet
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1   # 2606 collected (no test changes)

git checkout -b chore/post-sprint-v-audit
git add 01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md \
        docs/post_sprint_v_audit.md \
        session_prompts/NEXT.md \
        CLAUDE.md
git commit -m "docs(post-sprint-v): audit + Sprint W kickoff plan"
git push -u origin chore/post-sprint-v-audit
gh pr create --base main --head chore/post-sprint-v-audit \
  --title "Post-Sprint-V audit + Sprint W kickoff plan"
```

Then `/session-close post-sprint-v-audit` — which queues SW-1.

---

## 5. STOP FELTETELEK

**HARD:**
1. Sprint V SV-5 close PR not yet merged on `main` → wait.
2. Alembic head ≠ 048 → drift.
3. DocRecognizer accuracy script reports any below-SLO on the starter corpus → halt; the audit cannot land while Sprint V's gate is red.

**SOFT:**
- Operator chooses to skip the audit session and go straight to SW-1 implementation → bypass this prompt; the Sprint V plan §9 + retro are sufficient inputs for SW-1 kickoff.
- Audit reveals that 4–5 sessions is too tight for the carry-forward + new debt; Sprint W splits into Sprint W (5) + Sprint X (4) — document the split rationale.

---

## 6. SESSION VEGEN

```
/session-close post-sprint-v-audit
```

The `/session-close` will:
- Validate lint + unit collect.
- Stage + commit the audit + Sprint W kickoff plan diff.
- Push the branch.
- Open the PR.
- Generate `session_prompts/NEXT.md` for SW-1 — the first Sprint W execution session.

---

## 7. SKIPPED-ITEMS TRACKER (carry from Sprint V)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SU-SKIP-1 | `.github/workflows/nightly-regression.yml` `uc3-4combo-matrix` | Weekly job skip-by-default on PR runs | `secrets.OPENAI_API_KEY` + scheduled trigger |
| SS-SKIP-2 | `tests/integration/services/rag_engine/test_retrieval_baseline.py::test_retrieval_baseline_profile_b_openai` | Profile B Azure live MRR@5 | Azure credit |
| SV-SKIP-1 | `.github/workflows/nightly-regression.yml` `doc-recognizer-weekly-matrix` | Weekly DocRecognizer per-doctype matrix | Mon 08:00 UTC schedule + workflow_dispatch |

SU-FU-1..4 (operator-script `--output`, `scripts/` ruff cleanup, Alembic `invoice_date` rename, UC1 full-corpus verification) tracked in `docs/sprint_u_retro.md`. SV-FU-1..6 tracked in `docs/sprint_v_retro.md`. The audit session sequences these into Sprint W.
