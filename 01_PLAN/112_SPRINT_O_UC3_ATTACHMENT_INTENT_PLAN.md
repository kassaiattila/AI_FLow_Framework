# AIFlow v1.4.11 Sprint O — UC3 Attachment-Aware Intent Signals

> **Status:** KICKOFF — S126 on 2026-04-29.
> **Branch:** `feature/v1.4.11-uc3-attachment-intent` (cut from `main` @ `13a2f08`, Sprint N squash-merge).
> **Predecessor:** v1.4.10 Sprint N MERGED 2026-04-29 (cost guardrail + per-tenant budget).
> **Target tag (post-merge):** `v1.4.11`.
> **Parent plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 (Sprint K UC3 delivery recap).

---

## 1. Why this sprint

Sprint K (v1.4.7) shipped UC3 end-to-end:
`EmailSourceAdapter` → `scan_and_classify` → `Classifier` → `IntentRoutingPolicy` → UI.

The classifier — `services/classifier/service.py` — consumes a single feature
bag built from the email **body** only. `workflow_runs.output_data` persists
the `ClassificationResult`, attachments are stored via `IntakePackageSink`,
but the classifier never reads them.

Three customer-reported gaps surfaced within two weeks of Sprint K landing:

1. **Invoice-attachment emails misclassify.** A common pattern: supplier
   emails "Please find attached the March invoice." with a PDF attached and
   one-sentence body. Sprint K's classifier sees "Please find attached" and
   routes to `INFORMATION_REQUEST` or `MANUAL_REVIEW`. The attachment would
   resolve the ambiguity instantly — an invoice-number regex on the PDF text
   settles the intent as `EXTRACT`.
2. **Contract-DOCX emails misclassify.** Similar pattern with "Please sign
   the attached contract." → routed to `INFORMATION_REQUEST` when it should
   be `EXTRACT` (contract metadata extraction).
3. **MANUAL_REVIEW queue bloat.** ~18% of scanned emails land in
   MANUAL_REVIEW in the customer's Sprint K pilot deployment. Sampling
   suggests ≥ 60% of those have a body-attachment mismatch that attachment
   signals would resolve.

Sprint O closes these. The classifier learns to see inside attachments.

---

## 2. Discovery outcome (to run in S126)

S126 will produce `docs/uc3_attachment_baseline.md` containing:

- **Misclassification rate** on a frozen 25-email fixture built from anonymised
  samples in `data/fixtures/emails_sprint_o/` (4 intent categories × ~6 each,
  with and without attachments).
- **Processing latency baseline** — how long does `AttachmentProcessor`
  currently take on each fixture email (p50 / p95)?
- **Attachment coverage** — what mime types / sizes do fixture emails have?
  (Used to scope which branches of AttachmentProcessor we actually hit.)

**Hard gate for S127 start:** baseline misclass rate ≥ 15% on the fixture.
Below that, the sprint's value is unproven and we halt to rescope.

---

## 3. Session plan

### S126 — Discovery + kickoff
**Scope.** Build the 25-email fixture, measure baseline misclass rate + p95
latency + mime coverage. Land this plan doc + `docs/sprint_o_plan.md` + S127
NEXT.md + CLAUDE.md banner flip.

**Acceptance.**
- `data/fixtures/emails_sprint_o/` exists with 25 anonymised fixture emails.
- `scripts/measure_uc3_baseline.py` produces `docs/uc3_attachment_baseline.md`
  with misclass rate, p50/p95 latency, mime profile.
- Plan docs landed and CLAUDE.md banner switched.

### S127 — AttachmentFeatureExtractor
**Scope.**
- New pure-function module `src/aiflow/services/classifier/attachment_features.py`
  exposing `extract_attachment_features(attachments: list[ProcessedAttachment])
  → AttachmentFeatures`.
- `AttachmentFeatures` is a pydantic model:
  - `invoice_number_detected: bool` (regex on extracted text)
  - `total_value_detected: bool` (currency + number near total/össz/amount)
  - `table_count: int` (from ProcessedAttachment.tables)
  - `mime_profile: str` (primary dominant mime)
  - `keyword_buckets: dict[str, int]` (invoice, contract, support, report hits)
  - `text_quality: float` (reuse `_compute_quality_score`)
- Cache computed features in
  `workflow_runs.output_data.attachment_features` (JSONB — no migration).
- Thin orchestrator hook in `scan_and_classify` to run extraction **only**
  when `AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=true`.
- Size/time caps: skip attachments > 10 MB, total budget 5s per email.

**Acceptance.**
- `AttachmentFeatureExtractor` has ≥ 12 unit tests (fixture-driven).
- Feature flag off → extractor never runs, zero new log events.
- Feature flag on → extractor populates `attachment_features` for all 25
  fixture emails in total < 120s wall-clock.

### S128 — Classifier consumption + LLM-context path
**Scope.**
- `services/classifier/service.py` reads `attachment_features` from
  `ClassifierInput.context` (extend contract with optional field).
- **Rule boost:** `invoice_number_detected` OR `total_value_detected` AND
  `body_intent_confidence < 0.6` → boost `EXTRACT` by +0.3 (capped at 0.95).
- **LLM-context path** (opt-in via `AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT=true`):
  append attachment-extract summary (first 500 chars + feature summary) to
  the LLM classification prompt as an additional system message.
- 1 integration test on real Docker PG: process one fixture email with
  invoice-number attachment, assert intent = `EXTRACT`.
- Sprint K UC3 golden-path E2E must stay green unchanged.

**Acceptance.**
- ≥ 15 new unit tests.
- 1 integration test green.
- Sprint K golden-path E2E green (regression gate).
- Fixture misclassification rate drops by ≥ 50% relative to S126 baseline
  (exact target set from baseline measurement).

### S129 — UI surfacing + E2E
**Scope.**
- `EmailDetail.tsx`: new "Attachment signals" collapsible card below the
  existing intent/priority cards. Shows per-attachment: mime, page count,
  invoice-number regex hit, total-value regex hit, table count, keyword
  buckets (top 3), quality score. Only rendered when
  `attachment_features` present on the run.
- EN/HU localisation strings.
- 1 Playwright E2E (`test_uc3_attachment_signals.py`):
  fixture invoice-attachment email → scan → open detail page → assert
  "Attachment signals" card visible with `invoice_number_detected=true`
  badge, intent = `EXTRACT`.
- Live-test under `tests/ui-live/attachment_signals.md`.

**Acceptance.**
- tsc clean.
- E2E green.
- Live-test run + report landed.

### S130 — Sprint close
**Scope.** Retro + PR description + CLAUDE.md numbers bump + PR cut + tag
`v1.4.11` (queued post-merge).

**Acceptance.**
- `docs/sprint_o_retro.md` with scope + test deltas + decisions + follow-ups.
- `docs/sprint_o_pr_description.md` mirroring Sprint N's format.
- CLAUDE.md banner flipped to "v1.4.11 Sprint O DONE".
- PR opened against `main`.

---

## 4. STOP conditions

**HARD (halt + escalate):**
1. **Attachment processing p95 latency > 10s per email** on the 25-email
   fixture → classifier-path slowdown is a real-user UX hit; halt S128.
2. **Sprint K UC3 golden-path E2E regresses** → halt S128 until
   root-caused; do not proceed.
3. **Fixture misclass rate < 15%** in S126 baseline → sprint value
   unproven; halt and hand back to user.
4. **Azure DI fallback required for > 30% of fixture emails** → Azure cost
   profile changes materially; halt S127 and confirm Azure budget with user.
5. **Classifier output contract breakage** — if the `ClassifierInput`
   extension would require a non-optional field, halt and redesign
   (contract must stay backward-compatible with Sprint K callers).

**SOFT (proceed with note):**
- If p95 latency is 5–10s: gate extraction behind a per-tenant config
  instead of a global flag, document in retro.
- If a specific fixture email's docling output is garbage: note in retro,
  keep it in the fixture (edge case), verify the pipeline degrades
  gracefully.

---

## 5. Out of scope (explicit)

- **Image attachment intent.** No OCR / LLM vision inside this sprint.
  Images short-circuit to "no attachment features".
- **Multi-language attachment text.** First cut is HU + EN regex buckets
  only. SK / DE / etc. deferred to a follow-up if customer demand surfaces.
- **Attachment-based auto-reply composer.** (Was Lane B option 2 from
  S125 triage — separate sprint.)
- **Thread-aware classification.** (Was Lane B option 3 from S125 triage —
  separate sprint.)
- **OAuth-based live mailbox connect.** (Was Lane B option 4.)
- **Langfuse prompt for attachment classification.** LLM-context path uses
  the existing `email_intent` prompt; a dedicated attachment-aware prompt
  variant is deferred.
- **Per-attachment cost accounting.** Sprint N cost recorder sees the
  docling+Azure DI spend as a single classifier-run cost. Splitting per
  attachment is a follow-up if it materializes as a budget question.

---

## 6. Rollback plan

Sprint O is a pure additive feature. Rollback strategy:

1. **Flag-off rollback.** `AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false`
   restores exact Sprint K behavior — no DB rows written differently, no
   UI cards rendered, no classifier input change. Primary rollback lever.
2. **Revert rollback.** The S127 extractor and S128 classifier diff are
   isolated to 3 files each. `git revert` on the two squash-merge commits
   if the flag-off rollback is insufficient.
3. **Data rollback.** Nothing to roll back — `attachment_features` is
   additive JSONB in `workflow_runs.output_data`; leftover keys are ignored
   by Sprint K callers.

---

## 7. Success metrics

| Metric                                             | Source                             | Target                       |
|----------------------------------------------------|------------------------------------|------------------------------|
| Fixture misclass rate drop                         | `scripts/measure_uc3_baseline.py`  | ≥ 50% relative drop          |
| p95 scan latency w/ flag ON                        | S128 integration + live-test       | < 8s per email               |
| Sprint K UC3 golden-path E2E                       | existing 4 Playwright tests        | green, 0 regressions         |
| Unit test delta                                    | pytest collect                     | +30 tests minimum            |
| Flag-off is true no-op                             | S127 unit                          | zero new log events asserted |
| MANUAL_REVIEW queue reduction (synthetic estimate) | fixture replay                     | ≥ 30% reduction              |

---

## 8. Carry-over / NYITOTT

From Sprint N retro `docs/sprint_n_retro.md` §"Follow-up issues" — not in
Sprint O scope unless flagged:

1. `CostAttributionRepository` ↔ `record_cost` consolidation.
2. Model-tier fallback ceilings → `CostGuardrailSettings`.
3. Grafana panel for `cost_guardrail_refused` vs `cost_cap_breached`.
4. litellm pricing coverage audit as CI step.
5. `/status` OpenAPI tag diff.
6. `CostSettings` umbrella.
7. Soft-quota / over-draft semantics.
8. `scripts/seed_tenant_budgets_dev.py`.

Sprint M carry: live Vault rotation E2E, `AIFLOW_ENV=prod` root-token
guard, `make langfuse-bootstrap`, AppRole prod IaC, Langfuse v3→v4,
`SecretProvider` registry slot.

Sprint J carry: BGE-M3 weight cache CI artifact, Azure OpenAI Profile B
live, coverage uplift (issue #7 — partially addressed S125 tools tests).

Resilience `Clock` seam — deadline 2026-04-30 **tomorrow** (last chance —
unquarantine `test_circuit_opens_on_failures` or document decision to drop).
