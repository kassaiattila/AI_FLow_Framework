# AIFlow — Session 130 Prompt (Sprint O — Close + PR + tag v1.4.11)

> **Datum:** 2026-05-04
> **Branch:** `feature/v1.4.11-uc3-attachment-intent` (continues — cut from `main` @ `13a2f08`).
> **HEAD (parent):** S129 commit `816154d` `feat(sprint-o): S129 — UI AttachmentSignalsCard + Playwright E2E + live-test report` (landed 2026-05-03).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S129 — UI AttachmentSignalsCard + Playwright E2E + live-test
> report. AttachmentSignalsCard component + EN/HU locales + EmailDetail
> wiring + EmailDetailResponse extension + 1 Playwright E2E (route-mocked,
> green). 8 files changed. See commit `816154d` + `tests/ui-live/attachment-signals.md`.
> **Terv:** `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` §3 S130 +
> `docs/sprint_o_plan.md`.
> **Session tipus:** Sprint close — retro + PR description + CLAUDE.md
> numbers bump + PR cut + tag `v1.4.11` (queued post-merge).

---

## 1. MISSION

Close Sprint O. Write `docs/sprint_o_retro.md` (S126 → S129 walkthrough,
test deltas, decisions, follow-ups). Write `docs/sprint_o_pr_description.md`
mirroring Sprint N's format. Bump CLAUDE.md numbers. Cut PR against `main`.
Tag is queued for post-merge as `v1.4.11`.

---

## 2. KONTEXTUS

### Honnan jottunk (Sprint O recap)
| Session | Commit  | Scope                                                                              |
|---------|---------|------------------------------------------------------------------------------------|
| S126    | `2544a62`/`1a164d8`/`01e9cfa` | Discovery + 25-fixture corpus + baseline 56% misclass + plan landed.    |
| S127    | `885d336` / `8ba9ecb`         | AttachmentFeatureExtractor + flag-gated orchestrator wiring (flag off). |
| S128    | `5975296` / `9f399ef`         | Classifier consumption + signal-aligned rule boost; misclass 56%→32%.   |
| S129    | `816154d`                     | UI AttachmentSignalsCard + Playwright E2E + live-test report.           |

### Jelenlegi allapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2241 unit PASS / 1 skip / 1 xpass (Sprint O total +45: 22 S127 + 23 S128)
+1 integration test (Sprint O S128 — UC3 attachment-intent classify)
+1 E2E test (Sprint O S129 — attachment-signals)
Branch: feature/v1.4.11-uc3-attachment-intent @ 816154d
0 Alembic migrations added (Sprint O is feature-flag + JSONB only)
Misclass: 56% body-only baseline → 32% flag-on (24 pts / 42.9% relative drop)
  - invoice_attachment cohort: 3/6 → 6/6 (100% correct)
  - contract_docx cohort:      2/6 → 5/6
  - body_only cohort:          unchanged (no attachment to help)
  - mixed cohort:              unchanged
```

### Hova tartunk
After S130:
- `docs/sprint_o_retro.md` written (scope, test deltas, decisions log
  SO-1..SO-N, follow-ups + carry-overs).
- `docs/sprint_o_pr_description.md` written (mirrors Sprint N format).
- CLAUDE.md banner flipped to `v1.4.11 Sprint O DONE` + numbers updated
  (2196→2241 unit, +1 integration, +1 E2E, +1 service surface field).
- PR opened against `main` (queued behind any pending Sprint N PR).
- Tag `v1.4.11` queued post-merge.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                      # feature/v1.4.11-uc3-attachment-intent
git log --oneline -6                           # S126..S129 commits visible
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2241 pass
docker compose ps                              # postgres + redis healthy
```

---

## 4. FELADATOK

### LEPES 1 — `docs/sprint_o_retro.md`
Mirror `docs/sprint_n_retro.md` structure. Cover:

- **Headline.** `v1.4.11` Sprint O delivered the UC3 attachment-aware
  intent path end-to-end. 25-fixture misclass dropped from 56% (Sprint K
  baseline) to 32% (24 pts / 42.9% relative). Invoice-attachment cohort
  hit 100% accuracy.
- **Scope by session** (S126 discovery → S129 UI). Pull commit subjects.
- **Test deltas.** Unit 2196→2241 (+45). 1 new integration test (real
  Postgres — UC3 attachment-intent classify). 1 new E2E (Playwright
  route-mocked AttachmentSignalsCard). 0 Alembic migrations.
- **Decision log SO-1..SO-N.**
  - SO-1: Reuse `AttachmentProcessor` + JSONB persistence — no new table.
  - SO-2: Pure-function extractor (no I/O) so unit tests don't need
    docling/Azure DI.
  - SO-3: `_RUNTIME_HOOKS = (asyncio, Path)` import-pinning to defeat
    the autoformatter stripping unused-from-its-POV runtime imports
    (lessons from G0.3 — see also `feedback_*` memory entries).
  - SO-4: Body-label gate in `_apply_attachment_rule_boost` — only boost
    when body label is `unknown` ∪ EXTRACT_INTENT_IDS. Prevents the
    Sprint O first-pass 72% regression where the boost clobbered
    correctly identified non-EXTRACT intents (complaint, support, …).
  - SO-5: Signal-aligned EXTRACT label selection
    (`invoice_number_detected → invoice_received`,
    `keyword_buckets["contract"] → order`). Fixes the "always picks
    `order`" bug from naive alternatives-based selection.
  - SO-6: E2E uses `page.route` to intercept the API call — isolates
    the UI render path from FastAPI hot-reload state of the dev server.
  - SO-7: Sprint O ships the `EmailDetailResponse` extension itself
    (S128 should have shipped it; recorded as SOFT carry to retro). Live
    UI render requires `make api` restart.
- **Follow-ups (S130-FU-1..N).**
  - FU-1: Restart `make api` after merge so live `/api/v1/emails/{id}`
    returns the new fields.
  - FU-2: Add `intent.intent_class` to v1 schema so UI can show a
    generic EXTRACT pill instead of the specific label.
  - FU-3: Body_only / mixed cohort improvements — out of attachment scope;
    candidate Sprint P (LLM-context evaluation against fixtures).
  - FU-4: docling p95 cold-start (17.5 s) — instrument warm-cache or
    pre-load script. Sprint J BGE-M3 weight-cache CI artifact still open;
    docling is the next target.
  - FU-5: Resilience `Clock` seam deadline now 4 days past 2026-04-30.
    Either unquarantine `test_circuit_opens_on_failures` here or document
    a new deadline.
  - FU-6: LLM-context path (`AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT`)
    is unit-covered but not measured against fixtures (no LLM in CI).
    Carry to Sprint P / cost retro.
- **Carried from Sprint N / M / J / resilience.** Verbatim list from
  `docs/sprint_n_retro.md` §"Open follow-ups" + Sprint M + Sprint J carry.
  Update Clock seam deadline.

### LEPES 2 — `docs/sprint_o_pr_description.md`
Mirror `docs/sprint_n_pr_description.md` format. Single-PR summary for
Sprint O delivery. Include:
- Headline numbers (2241 unit, +1 integration, +1 E2E).
- Per-session commit table.
- Decision log SO-1..SO-7 (one-liners).
- Test plan (unit + integration + E2E + live-test report).
- Rollback (flag-off — `AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false`
  restores Sprint K behaviour exactly).
- Open follow-ups (FU-1..FU-6).
- Note Sprint M/N PR rebase dependency if either is still open.

### LEPES 3 — CLAUDE.md numbers + banner
- Flip the `v1.4.11 Sprint O` banner to `MERGED ...` placeholder text or
  `Sprint O CLOSE — 2026-05-04` until PR lands.
- Bump unit-test count: `2196 → 2241`.
- Add `+1 integration` (UC3 attachment-intent classify) and `+1 E2E`
  (attachment-signals).
- Add a single-line entry to the Sprint table referencing
  `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md`.

### LEPES 4 — PR cut
```bash
gh pr create \
  --title "Sprint O (v1.4.11): UC3 attachment-aware intent — extractor + classifier + UI" \
  --body-file docs/sprint_o_pr_description.md \
  --base main
```
- If Sprint M PR (#17) or Sprint N PR (#18) is still open, note the
  rebase dependency in the body. **Do not auto-merge.**
- Tag `v1.4.11` is queued post-merge.

### LEPES 5 — Final regression + commit + push
- `/regression` — full unit + Sprint K UC3 golden-path E2E + new E2E.
- `/lint-check` clean.
- Commit: `chore(sprint-o): S130 — Sprint O retro + PR description +
  CLAUDE.md numbers` + Co-Authored-By.
- Push.

### LEPES 6 — NEXT.md for Sprint P kickoff (or hand back)
- If a Sprint P plan exists, write `session_prompts/NEXT.md` with the
  S131 kickoff prompt.
- Otherwise overwrite `NEXT.md` with a minimal "Sprint O closed — awaiting
  Sprint P plan" stub so `/auto-sprint` halts cleanly on the next wakeup.

---

## 5. STOP FELTETELEK

**HARD (hand back to user):**
1. PR creation requires GitHub creds the autonomous loop doesn't have —
   if `gh pr create` fails non-interactively, halt and ask user.
2. Sprint K UC3 golden-path E2E regresses on the final regression — halt
   for root-cause.
3. CLAUDE.md update conflicts with another in-flight branch — halt and
   ask.

**SOFT (proceed with note):**
- Sprint M / N PR still open and creates a non-trivial rebase target —
  document in the PR body that Sprint O sits behind them in the merge
  queue. No code change required here.

---

## 6. NYITOTT (carried)

See `docs/sprint_o_retro.md` §"Carried" once written. The retro is the
single source of truth from this point on — this section just points
forward.

---

## 7. SESSION VEGEN

```
/session-close S130
```

Sprint O closes here. `/clear` -> hand back to user (or queue Sprint P
kickoff prompt) — there's no automatic next session unless a Sprint P
plan is on hand.
