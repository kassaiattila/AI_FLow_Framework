# Sprint W retrospective — v1.7.0

> **Status:** CLOSE 2026-04-26.
> **Tag:** `v1.7.0` (queued post-merge of the SW-5 close PR).
> **Branch base:** cut from `main` after each SW-N PR squash.
> **Predecessor:** v1.6.0 Sprint V (Generic Document Recognizer, MERGED).

---

## 1. Headline

**Production-readiness + multi-tenant cleanup.** Sprint W ships four
execution sessions on top of the Sprint V doc_recognizer:

* **SW-1** — wired the real PromptWorkflow extraction step into
  `DocumentRecognizerOrchestrator`, so the recognize endpoint produces
  populated `extracted_fields` (closes SV-FU-4).
* **SW-2** — markdown live-Playwright journeys for `/document-recognizer`
  and `/prompts/workflows` (closes SV-FU-3 + SR-FU-4).
* **SW-3** — `customer` → `tenant_id` rename + Alembic 049 column drop
  + audit script (closes SS-FU-1 / SS-FU-5).
* **SW-4** — `AIFLOW_ENVIRONMENT=prod` boot guard + Langfuse listing
  surface stub + operator script `--output` migration completion
  (closes SM-FU-2 + SR-FU-6 + SU-FU-1).

Every change is **default-off** at the user-visible layer:

* The boot guard fires only when `environment=prod` AND Vault is
  enabled. Local dev is unaffected.
* The Langfuse listing returns empty until the v4 SDK ships a
  list-by-prefix call.
* The `?source=` query param defaults to `local` and matches the
  pre-SW-4 behaviour byte-for-byte.

UC1 invoice_processor remains byte-stable on its golden path. UC2 RAG
retrieval is unchanged (the `tenant_id` rename touched only
`create_collection` / `list_collections` kwargs; the query path was
already on `tenant_id` since Sprint S S143). UC3 email intent untouched.

---

## 2. Test deltas

| Suite | Pre | Post | Delta |
|---|---|---|---|
| unit | 2606 | 2641 | **+35** |
| integration alembic | 50 | 51 | +1 (049 round-trip) |
| live Playwright (markdown specs) | 6 | 8 | +2 (`document-recognizer.md`, `prompt-workflows.md`) |

Breakdown of the +35 unit delta:

* SW-1 (DocRecognizer extraction wire-up): +14 (validators × 7 + extraction stage shape × 5 + cost-ceiling refusal × 2)
* SW-3 (rename) — net 0 unit (test fixtures updated, no new assertions)
* SW-4 — +12 boot guard + +4 router source-toggle + 0 net delta on script migrations = +16

Sprint V SW-FU-4-followup integration test (`test_doc_recognizer_extraction_real.py`) skips by default behind `OPENAI_API_KEY`; CI green.

---

## 3. Capability cohort delta

| Cohort | Sprint V close | Sprint W close |
|---|---|---|
| DocRecognizer extraction | classifier-only (empty fields) | **PromptWorkflow-driven extraction** for hu_invoice + hu_id_card |
| Live Playwright UI specs | `/budget-management`, `/extracted-fields`, `/rag/collections` | **+ `/document-recognizer`, + `/prompts/workflows`** |
| Multi-tenant column model | `customer` + `tenant_id` (parallel) | **`tenant_id` only** (Alembic 049 drops `customer`) |
| Prod-readiness guards | none | **`AIFLOW_ENVIRONMENT=prod` boot refuses Vault root tokens** |
| Langfuse-typed prompts visible in UI | local YAML only | **+ Langfuse listing surface** (admin UI source-toggle now wireable) |
| Operator scripts on uniform `--output` | 3 of 5 | **5 of 5** (SU-FU-1 closed) |
| Alembic head | 048 | **049** (`customer` column dropped) |
| New endpoints / UI pages | — | 0 / 0 |

---

## 4. Decisions log (SW-1 .. SW-4)

* **SW-1 — Reuse `invoice_extraction_chain` for `hu_invoice`.**
  Mapped each doctype's `extraction.workflow` field to the existing
  Sprint T descriptor where possible. Avoids duplicating prompt YAML
  and keeps UC1 byte-stable.
* **SW-1 — Per-step cost ceiling enforcement via `CostPreflightGuardrail.check_step()`.**
  Reused the Sprint U S154 API surface; added the 0.02 USD ceiling test
  per descriptor step. Refused requests raise `CostGuardrailRefused` at
  the orchestrator's `_extract` boundary.
* **SW-2 — Markdown journey scripts (NOT pytest).**
  Live Playwright specs live under `tests/ui-live/` as markdown
  documents the operator runs against the live admin stack via the
  Playwright MCP. Each execution appends a `## Utolso futtatas` section
  per file. CI does not run these — they are session-time validation,
  not regression specs.
* **SW-3 — Skip Pydantic alias shim.**
  The plan §SW-3 contemplated a `customer` → `tenant_id` API alias
  shim. After grepping the API contract surface, no Pydantic model on
  the rag_collections boundary ever exposed `customer` (`CollectionResponse`
  / `CollectionListResponse` use `tenant_id` exclusively since S143).
  The shim was unnecessary; documented in the SW-3 PR.
* **SW-3 — Out-of-scope `customer` columns explicitly preserved.**
  `skill_instances.customer`, `intent_schemas.customer`, and
  `document_extractor` config `customer` are different domains. The
  audit script `audit_customer_references.py` scopes itself to the
  rag_collections surface only.
* **SW-4 — `hvs.CAES` prefix as AppRole positive signal.**
  Vault AppRole-derived tokens carry the `hvs.CAES` prefix; root tokens
  use `hvs.` directly. The boot guard treats `hvs.CAES` tokens as
  acceptable. False-positive risk: an operator with a non-AppRole
  `hvs.CAES`-prefixed token gets through. Risk accepted; the runbook
  documents the AppRole-first path.
* **SW-4 — `list_langfuse_workflows()` ships as stub.**
  The Langfuse v4 Python SDK has no cheap list-by-prefix call as of
  this writing. The router accepts `?source=langfuse` and returns
  empty; the wiring is in place so the admin UI source-toggle can flip
  on once the SDK helper lands. Documented as SW-FU-1.
* **SW-4 — `?source=` did NOT change response shape.**
  The `WorkflowListResponse.source` field continues to be the
  `"backend"` provenance marker (frontend-vs-backend). The query
  parameter filters internally; the response shape stays
  backward-compatible.

---

## 5. Open follow-ups

* **SW-FU-1 — Langfuse v4 list-by-prefix SDK helper.** When the SDK
  ships an `api.prompts.list(prefix=...)` method, swap the
  `list_langfuse_workflows()` stub for a real call.
* **SW-FU-2 — Admin UI source-toggle widget on `/prompts/workflows`.**
  The router accepts `?source=`; the React page does not yet render a
  toggle. Wire in Sprint X.
* **SW-FU-3 — `audit_customer_references.py` extension to other tables.**
  Sprint W scoped the audit to the rag_collections surface; expanding
  to `intent_schemas` / `document_extractor` configs is a separate
  cleanup pass.
* **SW-FU-4 — Vault AppRole IaC end-to-end test.**
  The runbook documents Terraform + CLI; an automated round-trip
  (provision role → mint secret_id → AIFlow boots cleanly) lives in a
  future infrastructure sprint.
* **SW-FU-5 — DocRecognizer real-document fixture corpus.**
  Synthetic 8-fixture starter is enough for the rule-engine smoke. Real
  PDFs / scans / ID images need operator-driven anonymization.
  Carried from SV-FU-1.

---

## 6. What worked

* **Default-off rollout discipline.** Every behavior change shipped
  behind a flag or with a query-param fallback. Zero regression
  reports across 4 PRs in 1 calendar day.
* **Reuse of Sprint U/T scaffolding.** SW-1 leveraged
  `CostPreflightGuardrail.check_step()` (S154), `argparse_output()`
  (S156), and `invoice_extraction_chain` (T S149) without re-implementing.
* **Skill rename via `git mv`.** Sprint V's preserve-history rename
  paid off in SW-1 — the wire-up landed cleanly without git log
  noise.

## 7. What hurt

* **Pydantic Settings `extra_forbidden` on the bypass env var.**
  Initial SW-4 PR shipped with `AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD`
  as a free-floating env var; Pydantic rejected it on `VaultSettings`
  load. Fixed by adding the field to `VaultSettings` with `bool = False`
  default.
* **Live Playwright spec ergonomics.** The markdown journey scripts
  read clearly but require manual operator execution every time. CI
  cannot enforce them; the next refactor should evaluate Playwright
  Python codegen vs the markdown-script pattern.
* **`customer` column drop pre-flight.** Operators must run the
  pre-flight check (`SELECT COUNT(*) FROM rag_collections WHERE
  customer != tenant_id`) before `alembic upgrade head` because
  Alembic doesn't model conditional aborts. Documented in the migration
  docstring + retro; risk accepted.

---

## 8. Numbers (Sprint W close)

* **Tag:** `v1.7.0` (queued post-merge)
* **Sessions:** 5 (SW-1, SW-2, SW-3, SW-4, SW-5)
* **PRs:** 5 (one per session)
* **Calendar days:** 1 (autonomous chain)
* **Unit test delta:** +35 (2606 → 2641)
* **Integration alembic delta:** +1 (50 → 51)
* **Live Playwright delta:** +2 (6 → 8)
* **Endpoints:** unchanged (201 total)
* **Routers:** unchanged (32 total)
* **UI pages:** unchanged (27 total)
* **Alembic head:** 048 → 049
* **PromptWorkflow descriptors:** unchanged (6 total)
* **DocType descriptors:** unchanged (5 total)
* **CI jobs (`ci.yml`):** unchanged (5)
* **Operator scripts on `argparse_output`:** 3 → 5

---

## 9. References

* `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md` — Sprint W scope + session breakdown
* `docs/post_sprint_v_audit.md` — operator-facing audit pre-Sprint-W
* `docs/sprint_v_retro.md` — Sprint V retro + follow-ups
* `docs/runbooks/vault_approle_iac.md` — SW-4 AppRole runbook
* `src/aiflow/security/boot_guards.py` — SW-4 prod boot guard
* `src/aiflow/services/document_recognizer/extraction.py` — SW-1 extraction wire-up
* `src/aiflow/services/document_recognizer/validators.py` — SW-1 7 validators
* `alembic/versions/049_rag_collections_drop_customer.py` — SW-3 column drop
* `scripts/audit_customer_references.py` — SW-3 audit
* `tests/ui-live/document-recognizer.md` — SW-2 live spec
* `tests/ui-live/prompt-workflows.md` — SW-2 live spec
