# /live-test — document-recognizer (Sprint W / SW-2)

> **Status:** SPEC PUBLISHED — operator runs against the live admin stack on demand.
>             Mirrors Sprint N S123 `/budget-management` + Sprint S S144
>             `/rag-collections` patterns. Live runs append a `## Utolso futtatas`
>             section per execution.
> **Target:** `http://localhost:5173/#/document-recognizer`
> **API:** `http://localhost:8102` (`POST /api/v1/document-recognizer/recognize`,
>          `GET/PUT/DELETE /api/v1/document-recognizer/doctypes/{name}`)
> **Services:** PostgreSQL (5433, Docker), Redis (6379, Docker)
> **Stack startup:** `bash scripts/start_stack.sh --full` then `cd aiflow-admin && npm run dev`

## Journey

### Test 1 — Browse: 5 doctypes listed

1. **Login** — `/#/login` → fill `admin@bestix.hu` / `AiFlowDev2026!` (or whatever
   the operator's `AIFLOW_ADMIN_*` env values are) → Bejelentkezes.
   `aiflow_token` lands in localStorage; sidebar nav rendered.
2. **Navigate** — `/#/document-recognizer`. Sidebar nav row `Document Recognizer`
   visible + active. Page header "Document Recognizer" rendered.
3. **Browse tab default** — `[data-testid="tab-browse"]` has the active style
   (`border-b-2 border-blue-600`). The `Recognize` tab is visible but not active.
4. **Doctype list assertion** — `[data-testid="doctype-list"] tr` row count is **5**:
   - `[data-testid="doctype-row-hu_invoice"]` — display "Magyar számla", PII low
   - `[data-testid="doctype-row-hu_id_card"]` — display "Magyar személyi igazolvány", PII high
   - `[data-testid="doctype-row-hu_address_card"]` — display "Magyar lakcímkártya", PII medium
   - `[data-testid="doctype-row-eu_passport"]` — display "EU útlevél", PII high
   - `[data-testid="doctype-row-pdf_contract"]` — display "Szerződés (PDF)", PII low
5. **PII badge color check** — `[data-testid="pii-badge-low"]`/medium/high render
   green/amber/red Tailwind v4 classes (visual screenshot if tooling captures it).
6. **Source label** — none of the 5 rows shows the "Tenant override" badge
   on a clean dev DB — all `[data-testid^="override-badge-"]` selectors return 0
   matches. The fallback "Bootstrap" plain-text label is rendered for each.
7. **Cleanup** — none required (read-only).

**Pass criteria:** 5 rows, correct display names, correct PII badges,
no JS errors in console attributable to this page.

### Test 2 — Recognize: drag-drop file → result panel populates

1. **From Test 1 final state**, click `[data-testid="tab-recognize"]`. Tab swaps;
   `[data-testid="recognize-panel"]` mounts.
2. **File upload** — page-evaluate to set `[data-testid="recognize-file-input"]`
   to the synthetic fixture `data/fixtures/doc_recognizer/hu_invoice/inv_001_simple.txt`.
   (Playwright MCP supports `setInputFiles` via `browser_evaluate` if no native
   file-picker hook; alternatively use `browser_file_upload` from the mcp-playwright
   extension.)
3. **Optional hint** — leave `[data-testid="recognize-hint-select"]` at `""`
   (Auto-detect). Operator may set it to `hu_invoice` to skip the rule-engine
   entirely.
4. **Submit** — click `[data-testid="recognize-submit"]`. The button text changes
   to "Recognizing…" while the request is in flight.
5. **Result panel assertion** — `[data-testid="recognize-result"]` mounts within
   ≤ 30 s (slow LLM invocation tolerance). Inside it:
   - `Run ID` field is a UUID (matches `[0-9a-f]{8}-[0-9a-f]{4}-...`)
   - `Doc type: hu_invoice` (rule engine top-1)
   - `Confidence`: ≥ 90.0% (the synthetic fixture matches every weighted rule)
   - `Method: rule_engine` (no LLM fallback needed)
   - `Intent: process` (default — synthetic fixture has no >1M HUF total)
   - `PII redacted: No` (hu_invoice descriptor's `pii_redaction: false`)
   - `Cost: $0.0XYZ` (post-SW-1 — depends on model and token count; ≤ $0.05)
   - **Extracted fields table** (post-SW-1 wired LLM extraction):
     - At minimum `invoice_number` and `total_gross` populated with `≥ 70%` confidence.
     - On the synthetic `inv_001_simple.txt` corpus, expected values:
       - `invoice_number`: SZLA-2026-0001
       - `total_gross`: 317500 (number) or "317.500" / "317500 Ft" (string)
   - The `(No fields extracted — SV-3 ships a placeholder; SV-3+ wires
     PromptWorkflow extraction.)` paragraph is **NOT** rendered (post-SW-1 fields
     populate).
6. **Cleanup** — Operator may issue `DELETE FROM doc_recognition_runs WHERE
   tenant_id = 'admin@bestix.hu'` (or whatever JWT `team_id` resolved to) to
   clear the audit row. Optional — not required for repeated runs.

**Pass criteria:** Result panel mounts within timeout, doc_type matches
expected, ≥ 1 extracted field with non-null value, intent matches descriptor
default, run_id format correct.

### Test 3 — Per-tenant override: edit YAML → save → refresh shows override badge

1. **From Test 1 state**, click `[data-testid="doctype-row-hu_invoice"]`. The
   `DocTypeDetailDrawer` opens (`[data-testid="doctype-detail-drawer"]` mounts).
2. **Drawer content assertion** — descriptor metadata grid populated; classifier
   rules summary shows 5 rule-kind chips; `[data-testid="yaml-editor"]` rendered
   with the bootstrap descriptor YAML preview.
3. **Toggle edit** — click `[data-testid="toggle-edit"]`. Button text swaps from
   "Override for tenant" to "Cancel edit"; the editor textarea becomes editable
   (no `readonly` attr); the `[data-testid="save-override"]` button mounts.
4. **Edit YAML** — modify the editor's first rule weight from `0.35` to `0.40`
   (page-evaluate `el.value = el.value.replace('weight: 0.35', 'weight: 0.40')`,
   dispatch `input` event). Operator may also bump the version field.
5. **Save** — click `[data-testid="save-override"]`. Button text changes to
   "Saving…" while the PUT is in flight; on completion the drawer closes and
   the parent list re-fetches.
6. **Override badge** — back on the Browse tab,
   `[data-testid="override-badge-hu_invoice"]` is now visible (purple chip
   "Tenant override").
7. **Refresh** — hard-reload the page (`page.goto` the same URL). Override badge
   re-renders from the fresh GET, confirming the file at
   `data/doctypes/_tenant/{tenant_id}/hu_invoice.yaml` is on disk + the registry
   cache invalidate fired.
8. **Delete override** — click the row again, drawer reopens with the
   `Tenant override` badge present. Click `[data-testid="delete-override"]`.
   The override file deletes; refresh shows the badge gone; descriptor falls
   back to bootstrap.
9. **Cleanup** — none required (Test 3 already restores the bootstrap state).

**Pass criteria:** Override file persists at the per-tenant path, override
badge appears post-save, registry cache invalidate works, delete restores
bootstrap state.

## Observations + diagnostics

When live runs append `## Utolso futtatas` sections, expected diagnostics:

- The recognize endpoint (post-SW-1) makes a real LLM call. Operators
  on air-gap installs without `OPENAI_API_KEY` see the `extract_fn`
  graceful fallback path: extracted_fields stays empty + a single
  `validation_warning` notes `"workflow ... not resolved"` or
  `"LLM call failed: ..."`. Doc_type match + intent decision still
  populate.
- The `audit_log` boundary writes `pii_redacted: false` for `hu_invoice`
  fixtures (descriptor flag). For PII-high doctypes (`hu_id_card`,
  `eu_passport`), value cells in the result panel render `<redacted>`
  if the descriptor's `pii_redaction: true`; the ID-number / name /
  birth-date raw values never reach the browser DOM.
- Untitled UI + Tailwind v4 dark/light tokens render correctly; PII
  badge color tokens (green/amber/red) match the descriptor's
  `pii_level` field.

## STOP conditions

- The recognize panel doesn't mount within 30 s → API server stalled
  or LLM provider timeout. Investigate `tail -f .stack_logs/api.log`.
- 0 doctype rows → registry bootstrap dir resolution broken. Verify
  `data/doctypes/*.yaml` files are present + `aiflow-admin/.env`
  points at the same API.
- Per-tenant override save returns 400 → YAML syntax invalid (the
  preview helper produced unparseable output). Triage the YAML
  preview logic in `DocTypeDetailDrawer.yamlPreview`.
- Console errors with `Authorization` headers → JWT token expired
  mid-session; refresh the login page.
