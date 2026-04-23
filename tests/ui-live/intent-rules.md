# Live E2E: Intent Rules module

> **Module:** `aiflow-admin/src/pages-new/IntentRules.tsx` (list + editor, URL-controlled)
> **API:** `src/aiflow/api/v1/emails.py` — `GET/PUT/DELETE /api/v1/emails/intent-rules[/{tenant_id}]`
> **Contract:** `src/aiflow/policy/intent_routing.py::IntentRoutingPolicy`
> **Storage:** `$AIFLOW_POLICY_DIR/intent_routing/{tenant_id}.yaml`
> **Verzio:** v1.4.7 Sprint K S109a

## Elofeltetelek

```
curl -sf http://127.0.0.1:8102/health
curl -sf http://127.0.0.1:5173
ls config/policies/intent_routing/  # empty OK
```

## Journey

### 1. Login + navigate

```
navigate → http://localhost:5173/#/emails/intent-rules
```

**Expect**
- Sidebar: "Intent szabalyok" (filter icon) highlighted
- Heading "Intent szabalyok" + subtitle "Intent → downstream action routing policy YAML editor"
- ← Vissza button
- "UJ SZABALY" card with tenant_id input + Letrehozas button
- Table of existing policies (or empty-state message)

### 2. Create new rule — input validation

```
type in tenant_id input → "acme-test/../escape"
```

**Expect**
- `Ervenytelen tenant_id` helper text appears under input
- Letrehozas button disabled

```
type valid tenant_id → "acme"
click Letrehozas
```

**Expect**
- Navigate → `/emails/intent-rules/acme`
- Page shows "Szabaly szerkesztes" + "uj" badge
- YAML textarea pre-seeded with template including `tenant_id: acme`
- Schema cheatsheet panel right side

### 3. Save — happy path

```
edit YAML (or keep template) → click Mentes
```

**Expect**
- Network: `PUT /api/v1/emails/intent-rules/acme` → 200
- ✓ Mentve indicator appears, fades after 2s
- File on disk: `config/policies/intent_routing/acme.yaml`

### 4. Save — validation error (tenant_id mismatch)

```
edit YAML: change tenant_id line to "DIFFERENT"
click Mentes
```

**Expect**
- Network: PUT returns 422
- Red pre block with `422: tenant_id mismatch: URL='acme', YAML='DIFFERENT'`

### 5. Save — malformed YAML

```
edit YAML: break a line, e.g. "rules: [unclosed"
click Mentes
```

**Expect**
- Network: PUT returns 422
- Red pre block with `YAML parse error: ...`

### 6. Save — invalid action enum

```
edit YAML: default_action: "BOGUS"
click Mentes
```

**Expect**
- Network: PUT returns 422
- Red pre block with Pydantic validation errors (mentions `action`, enum values)

### 7. List reflect

```
click ← Vissza
```

**Expect**
- Navigate → `/emails/intent-rules`
- Table now has 1 row: tenant_id=acme, szabalyok=N, default_action=manual_review
- Click row → navigate back to editor

### 8. Delete

```
in editor view → click Torles
```

**Expect**
- Confirmation modal appears: "Szabaly torlese: acme?"
- Shows file path
- Mégse closes modal; Torles does DELETE /intent-rules/acme → 204
- Navigate back to list, acme no longer in table

## Sikerkriteriumok (PASS)

- [ ] 0 console error across all 8 steps
- [ ] All 422 errors show with readable detail (not raw JSON)
- [ ] File appears/disappears under `config/policies/intent_routing/` matching UI state
- [ ] Back navigation works without losing state

## Utolso futtatas

### 2026-04-23 08:47 — **PASS (S109a initial)**
- Tool csomag: `mcp__plugin_playwright_playwright__*`
- Preflight: API UP, Vite UP
- Lepes 1 (list navigation): PASS, sidebar highlight, heading, breadcrumb
- Lepes 2 (editor open via URL): PASS, YAML pre-loaded for acme (previous curl PUT)
- Lepes 3-6 (save paths): nem futtatva ebben a session-ben
- Integration tests: **5/5 PASS** (`tests/integration/api/test_intent_rules.py`) — happy path + path-traversal + tenant_id mismatch + malformed YAML + invalid enum
- **Commit (ebben a commit-ban landol):** l TBD (S109a end-of-session)
