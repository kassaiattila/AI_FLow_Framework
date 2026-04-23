# Live E2E: Prompts module

> **Module:** `aiflow-admin/src/pages-new/Prompts.tsx` + `PromptDetail.tsx`
> **API:** `src/aiflow/api/v1/prompts.py` (GET list / GET detail / PUT)
> **Storage:** `prompts/` + `skills/*/prompts/*.yaml` (walker-based discovery)
> **Verzio:** v1.4.7 Sprint K S109b

## Elofeltetelek

```
curl -sf http://127.0.0.1:8102/health
curl -sf http://127.0.0.1:5173
```

## Journey

### 1. Login + list

```
navigate → http://localhost:5173/#/prompts
```

**Expect**
- Heading "Prompts" + count badge (37 typical)
- Table with Name / Version / Updated / Tags columns
- Row hover shows cursor pointer

### 2. Drilldown to detail

```
click any row (e.g. aszf-rag/answer_generator)
```

**Expect**
- Navigate → `/prompts/aszf-rag/answer_generator`
- Heading "Prompt szerkesztes"
- ← Vissza back button
- Name + version badge (blue) + updated timestamp
- YAML textarea with full content

### 3. Edit + save

```
modify a benign line (e.g. description)
click Mentes
```

**Expect**
- Network: `PUT /api/v1/prompts/:name` → 200
- ✓ Mentve pill appears, fades after 2s
- Dirty indicator "Mentetlen valtoztatasok" disappears
- File on disk updated

### 4. Save — name mismatch

```
change name: line to "different/name"
click Mentes
```

**Expect**
- Network: PUT returns 422
- Red pre block: `422: name mismatch: URL='...', YAML='different/name'`

### 5. Save — malformed YAML

```
add "[unclosed-list" to YAML
click Mentes
```

**Expect**
- Network: PUT returns 422
- Red pre block with parse error

### 6. 404 handling

```
navigate → /prompts/does-not-exist
```

**Expect**
- ErrorState component, retry button

## Sikerkriteriumok (PASS)

- [ ] 0 console error
- [ ] Disk reflect save (file mtime updated)
- [ ] PromptManager cache invalidated after PUT (next skill run reads fresh YAML)

## Utolso futtatas

### 2026-04-23 09:01 — **PASS (S109b initial)**
- Tool csomag: `mcp__plugin_playwright_playwright__*`
- Lepes 1 (list): PASS, 37 prompts, row hover pointer
- Lepes 2 (detail navigate): PASS, `/prompts/aszf-rag/answer_generator` loads with v1.1 badge, full YAML in textarea
- Lepes 3-5 (save paths): nem futtatva élőben, de integration test-ek PASS (5/5)
- Integration tests: **5/5 PASS** (`tests/integration/api/test_prompts_edit.py`) — detail + 404 + upsert round-trip + name mismatch + malformed YAML
- **Commit:** TBD
