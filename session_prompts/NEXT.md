# AIFlow [Sprint X] — Session SX-1 Prompt (Post-Sprint-W audit + Sprint X kickoff)

> **Datum:** 2026-04-26 (snapshot date — adjust if session runs later)
> **Branch:** `feature/x-sx1-audit-and-kickoff` (cut from `main` after the
> Sprint W SW-5 close PR squash-merges).
> **HEAD (expected):** SW-5 close PR squash on top of `ad1b708` (SW-4 squash).
> **Predecessor:** v1.7.0 Sprint W (production-readiness + multi-tenant cleanup, MERGED).

---

## Goal

Sprint W is closed; tag `v1.7.0` queued. SX-1 is a **planning + audit
session**, not an execution session. The deliverable is a written audit
+ Sprint X scope plan, not code changes.

The operator picks Sprint X scope from the post-Sprint-W carry-forward
inventory + any new business pressure that arrived during Sprint W.

## Carry-forward inventory (pick from these)

### From Sprint W follow-ups

* **SW-FU-1** — Langfuse v4 list-by-prefix SDK helper (replace
  `list_langfuse_workflows()` stub with a real call when SDK ships)
* **SW-FU-2** — Admin UI source-toggle widget on `/prompts/workflows`
  (the router accepts `?source=`; the React page does not yet render
  a toggle)
* **SW-FU-3** — `audit_customer_references.py` extension to
  `intent_schemas` / `document_extractor` configs / `skill_instances`
* **SW-FU-4** — Vault AppRole IaC end-to-end test
* **SW-FU-5** — DocRecognizer real-document fixture corpus (carry from
  SV-FU-1; operator-driven anonymization)

### From Sprint V follow-ups (still open)

* **SV-FU-2** — UI bundle size guardrail (bundle hasn't grown
  alarmingly yet, but a CI threshold would be cheap insurance)
* **SV-FU-5** — Monaco editor for the doctype YAML drawer (textarea
  works; Monaco is nice-to-have)

### Long-deferred topics

* **Coverage uplift 70% → 80%** (SJ-FU-7) — dedicated cross-cutting
  sprint candidate
* **UC3 thread-aware classifier** (SP-FU-3) — architecture sprint
* **Vault rotation E2E + Langfuse v3→v4** — infrastructure sprint
* **Grafana cost panels** (SN-FU-3) — observability sprint
* **UC1 corpus extension to 25 fixtures** (SQ-FU-3) — operator curation
* **Profile B Azure OpenAI live MRR@5** (SS-SKIP-2) — blocked on credit

### Strategic candidates

* **DocRecognizer ML classifier** — only if SW-FU-5 corpus reveals the
  rule engine is inadequate
* **Skill multi-tenancy cleanup** — `skill_instances.customer` rename
  parallel to SW-3 (separate domain, separate cleanup pass)
* **Multi-region prod readiness** — what Sprint W boot guard implies but
  doesn't deliver: replication, failover, region-aware Vault auth

## SX-1 deliverables

1. **`docs/post_sprint_w_audit.md`** (new) — operator-facing audit
   mirroring `docs/post_sprint_v_audit.md`. Sections:
   - Sprint W trajectory recap (what shipped, what didn't)
   - Test deltas (cumulative since v1.6.0)
   - Capability cohort delta (cumulative)
   - Carry-forward inventory annotated with effort estimate (S/M/L)
   - Recommended Sprint X scope (pick 4-5 sessions worth)
   - STOP conditions if Sprint X is delayed (anything time-sensitive?)
2. **`01_PLAN/121_SPRINT_X_<theme>_PLAN.md`** (new) — Sprint X
   kickoff plan. Theme TBD; operator picks from the audit recommendation.
   The plan ships with: Goal, Capability cohort delta, Sessions
   (SX-1 already counted as kickoff), Risk register, Gate matrix,
   Skipped tracker, STOP conditions.
3. **`session_prompts/NEXT.md`** → SX-2 (the first execution session of
   Sprint X) prompt.
4. **CLAUDE.md banner update** — Sprint W DONE banner is already there;
   SX-1 adds a Sprint X kickoff banner with the chosen theme.

## Constraints

* No code changes in SX-1 — pure planning + docs.
* Carry-forward triage MUST preserve the SW-FU and SV-FU IDs verbatim
  so cross-references stay stable.
* Every recommended Sprint X session needs a UC golden-path gate
  identified up front (UC1 / UC2 / UC3 / DocRecognizer / Monitoring).
* If Sprint X picks an infrastructure topic (e.g., Vault rotation E2E),
  identify the rollback path before merging the SX-1 plan.

## Gate

* **`docs/post_sprint_w_audit.md` published** with operator sign-off
  on the recommended Sprint X scope
* **`01_PLAN/121_*` plan published** with all sections filled
* **`session_prompts/NEXT.md` → SX-2 prompt** ready to execute

## STOP conditions

* HARD: If Sprint W tag `v1.7.0` did not actually ship (the SW-5 PR is
  still pending), do NOT publish post-W audit. Wait for the tag.
* SOFT: If the operator wants to take a calendar-day break before
  Sprint X kicks off, freeze SX-1 deliverables behind a
  `01_PLAN/121_*_DRAFT.md` filename until kickoff resumes.

---

## Output / handoff format

The session ends with:
1. PR opened against `main` titled
   `docs(post-sprint-w): audit + Sprint X kickoff plan publish`
2. PR body summarizes the chosen Sprint X theme + 4-5 sessions
3. `session_prompts/NEXT.md` → SX-2 prompt that the operator can
   execute next via `/next`
