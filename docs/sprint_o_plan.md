# Sprint O (v1.4.11) — UC3 Attachment-Aware Intent Signals

> **Status:** KICKOFF — S126 on 2026-04-29.
> **Branch:** `feature/v1.4.11-uc3-attachment-intent` (cut from `main` @ `13a2f08`).
> **Full plan:** `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md`.
> **Predecessor:** v1.4.10 Sprint N MERGED 2026-04-29 (cost guardrail + per-tenant budget).

## TL;DR

Sprint K (v1.4.7) shipped UC3 email intent classification on email **body**
only. Emails with thin bodies but distinctive attachments (invoice PDF,
contract DOCX) underflow to `MANUAL_REVIEW` or misclassify as `SPAM`/`SUPPORT`.

Sprint O teaches the classifier to read attachments:

1. **AttachmentFeatureExtractor** — reuses `AttachmentProcessor` (Sprint K)
   to run attachments through docling (+ optional Azure DI fallback) and
   derive structured features: mime profile, invoice-number regex hits,
   total-value presence, table count, keyword buckets.
2. **Classifier consumption** — features merged into the existing classifier
   input. Rule-based boost for strong attachment signals; LLM-context path
   opt-in via env flag.
3. **UI surfacing** — `EmailDetail.tsx` gets an "Attachment signals" card
   showing what the classifier saw.

Feature flag: `AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false` by default.
Ship-off.

## Sessions

| ID   | Scope                                                                    | Alembic |
|------|--------------------------------------------------------------------------|---------|
| S126 | Kickoff — misclassification baseline fixture + plan doc (this file).     | 0       |
| S127 | `AttachmentFeatureExtractor` + `workflow_runs.output_data` cache + unit. | 0       |
| S128 | Classifier consumption + rule boost + LLM-context flag + integration.    | 0       |
| S129 | Admin UI "Attachment signals" card + 1 Playwright E2E.                   | 0       |
| S130 | Sprint close — PR, retro, tag `v1.4.11`.                                 | 0       |

## STOP conditions (summary)

- Attachment processing p95 latency > 10s per email on the 25-email fixture
  → halt S128 (classifier would slow the whole scan pipeline).
- Rule-boost regression on Sprint K golden-path E2E → halt S128 until
  regression root-caused.
- Fixture baseline shows < 15% misclassification on invoice-attachment
  emails → sprint value unproven; hand back to user for rescope.
- Azure DI fallback mandatory for > 30% of fixture → Azure cost model
  changes; halt and confirm with user.

## Out of scope

Image-only attachment intent (no LLM Vision), multi-language attachment text,
OCR-quality re-ranking, attachment-based auto-reply, thread-aware
classification — explicitly deferred to later sprints.

See full plan doc for rationale, rollback, success metrics.
