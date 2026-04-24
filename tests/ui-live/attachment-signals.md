# /live-test — attachment-signals (Sprint O / S129)

- **Run date:** 2026-05-03 (session 129, HEAD includes S128 commit `5975296`
  + S129 working tree).
- **Runner:** Playwright (sync_api) via `pytest tests/e2e/v1_4_11_uc3_attachment/`.
- **Target:** `http://localhost:5173/#/emails/<seeded-uuid>`.
- **API:** `http://localhost:8102` (uvicorn). Note: the live API server was
  running an earlier `EmailDetailResponse` (Sprint K snapshot) when this
  test was first wired; the test pivots to `page.route` interception so the
  UI render path is exercised against the new payload contract regardless
  of API hot-reload state. Operator should restart `make api` to land the
  S128/S129 response-model fields on the live endpoint.
- **Services:** PostgreSQL (5433, Docker — healthy), Redis (6379, Docker —
  healthy). Sprint M Vault overlay running but not used here.

## Journey

1. **Login** — fixture `authenticated_page` loads `/#/login`, fills
   `admin@aiflow.local` / `AiFlowDev2026`, submits, waits for sidebar nav.
   `aiflow_token` lands in `localStorage` as expected.
2. **Mock GET /api/v1/emails/{id}** — Playwright `page.route(...)` returns a
   synthetic `EmailDetailResponse` payload with the S127/S128 shape
   (Sprint O additive fields: `attachment_features`,
   `classification_method = "keywords_no_match+attachment_rule"`,
   `attachment_features.invoice_number_detected = True`,
   `attachment_features.mime_profile = "application/pdf"`).
3. **Navigate** — `/#/emails/<uuid>`. EmailDetail page mounted; the new
   `AttachmentSignalsCard` renders below the existing intent / priority /
   routing / meta cards.
4. **Render assertions** —
   - `data-testid="attachment-signals-heading"` visible (`Attachment signals` /
     HU `Csatolmany jelek` depending on locale).
   - `data-testid="attachment-signals-boosted"` visible (`★ Classifier intent
     boosted by attachment rule` / HU `★ A csatolmany szabaly emelte a
     besorolast`).
   - `application/pdf` text visible (mime profile dl entry).
5. **Console** — no JS errors collected during the journey (filtered for
   benign WebSocket / Failed-to-load noise).

## Pass / Fail

- E2E: **PASS** — `tests/e2e/v1_4_11_uc3_attachment/test_attachment_signals.py::TestAttachmentSignalsCard::test_card_renders_with_boosted_indicator[chromium]` 1 passed.
- tsc: **PASS** — `npx tsc --noEmit` clean on the admin app.
- Manual UI smoke: queued for operator after `make api` restart so the
  live `/api/v1/emails/{id}` endpoint serves `attachment_features`. Until
  then the AttachmentSignalsCard renders nothing on the live UI for runs
  produced by the orchestrator (the data is in `output_data` but the API
  filters it out). Coverage gap noted in S130 retro.

## Follow-ups

- Restart `make api` so the OpenAPI spec exposes
  `attachment_features` + `classification_method` on
  `EmailDetailResponse`. Re-run `/live-test attachment_signals` once
  restarted; the route-mock can be removed in favor of a direct API hit
  (or kept as a defense-in-depth UI-only smoke).
- Consider an `intent.intent_class` field on the v1 schema so the UI can
  render a generic EXTRACT pill instead of the specific `invoice_received`
  / `order` label (Sprint O follow-up; tracked in S130).
