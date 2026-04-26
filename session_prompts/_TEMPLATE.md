# AIFlow [Sprint <X>] — Session S<X>-<N> Prompt

> **Template version:** 1.0 (introduced SX-1, 2026-04-26).
> **Binding:** every `session_prompts/NEXT.md` MUST follow this template.
> **Source:** `docs/honest_alignment_audit.md` §4.1.

---

## Quality target (MANDATORY)

> Every session-prompt MUST start with this block. `/next` blocks the
> session if the block is missing or any field is empty/non-measurable.

- **Use-case:** <UC1 / UC2 / UC3 / DocRecognizer / process>
- **Metric:** <specific number, e.g. "UC1 invoice accuracy on 25-fixture mixed corpus">
- **Baseline (now):** <current measurement, e.g. "85.7% on 10-fixture synthetic">
- **Target (after this session):** <desired number, e.g. "≥ 92% on 25-fixture mixed">
- **Measurement command:** <one bash one-liner that produces the number, e.g. `bash scripts/run_quality_baseline.sh --uc UC1 --output json`>

> Special case — process/doc-only sessions (e.g. SX-1 audit, SX-6 close):
> set Use-case to `process` and Metric to a deliverable checklist (count of
> shipped docs/files). Baseline / Target / Measurement command still required.

---

## Goal

<One paragraph: what this session ships and why it matters for the
quality target above. NOT a feature description — explain the metric
delta the session is responsible for.>

---

## Predecessor context

> **Datum:** YYYY-MM-DD
> **Branch:** `feature/x-sx<N>-<short-slug>` (cut from `main` after the
> previous SX-(N-1) PR squash-merges).
> **HEAD (expected):** SX-(N-1) close commit on top of <prev-tag>.
> **Predecessor session:** SX-(N-1) — <one-line scope>.

---

## Pre-conditions

- [ ] Previous session PR merged on `main`
- [ ] Branch cut: `feature/x-sx<N>-<slug>`
- [ ] Stack runnable (`bash scripts/start_stack.sh --validate-only` GREEN)
- [ ] `bash scripts/run_quality_baseline.sh --uc <UC>` produces the baseline number
- [ ] Required env vars / fixtures available (list specific ones)

---

## Tasks

1. **<Task 1>** — <what to ship>
2. **<Task 2>** — <what to ship>
3. ...

---

## Acceptance criteria

- [ ] **Quality target met** — `<measurement command>` produces a number ≥ target
- [ ] All unit tests PASS (`make test`)
- [ ] All affected integration tests PASS
- [ ] No regression on byte-stable golden paths (UC1/UC2/UC3 baselines unchanged)
- [ ] Documentation updated (retro doc or PR description)
- [ ] PR opened against `main`, CI green
- [ ] OpenAPI snapshot refreshed (if router/endpoint changed)

---

## STOP conditions

**HARD:**
- Quality target NOT met after best effort → halt, document gap, escalate to extension session
- Byte-stable regression on a non-target UC → halt, revert
- Test failure in unrelated module → halt, investigate

**SOFT:**
- Operator-driven dependency missing (e.g. anonimizalt corpus) → defer this session, swap with next-in-queue

---

## Output / handoff format

The session ends with:

1. PR opened against `main` titled `<conv-prefix>: SX-<N> — <one-line scope>`
2. PR body summarizes the quality target delta (baseline → measured value)
3. `/session-close` invoked → generates `session_prompts/NEXT.md` for SX-<N+1>
4. `01_PLAN/ROADMAP.md` Sprint X table row updated (status → DONE for SX-<N>)
5. `docs/SPRINT_HISTORY.md` entry appended (only at sprint-close, SX-6)

---

## References

- Sprint X plan: `01_PLAN/121_SPRINT_X_QUALITY_PUSH_PLAN.md`
- Forward queue: `01_PLAN/ROADMAP.md`
- Honest alignment audit: `docs/honest_alignment_audit.md`
- Quality baseline script: `scripts/run_quality_baseline.sh`
- Use-case-first replan (policy): `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
