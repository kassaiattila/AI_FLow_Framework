# AIFlow Sprint C — Session 39 Prompt (C2.4–C2.6: Quality + Admin CRUD + Audit)

> **Datum:** 2026-04-10
> **Branch:** `feature/v1.4.0-ui-refinement` | **HEAD:** `7a7ac67`
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** S38 — C2.1-C2.3 DONE (RunDetail page, Monitoring restart+auto-refresh)
> **Terv:** `01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md` (C2.4-C2.6 szekcio)
> **Session tipus:** CODE + UI — Quality finomitas, Admin CRUD dialogs, Audit filter+export
> **Workflow:** Quality rubric → Admin Create/Generate/Revoke → Audit filter+CSV → tsc → Commit(ok)

---

## KONTEXTUS

### S38 Eredmenyek (C2.1-C2.3 — KESZ)

```
✅ C2.1: Dashboard alert banners — mar mukodtek, SKIP
✅ C2.2: RunDetail.tsx UJ OLDAL — /runs/:id, step log, KPI, retry, export JSON
✅ C2.2: Route regisztracio + Runs.tsx onRowClick navigate
✅ C2.3: Monitoring restart gomb + ConfirmDialog + auto-refresh (10s/30s/60s)
✅ 22 i18n kulcs (hu+en) runDetail.*
✅ tsc --noEmit 0 error
```

### Sprint C Allapot

```
19 aktiv UI oldal (18 + RunDetail) + 5 archiv | Login kulon
J1 Invoice: Scan ✅ → Documents(badge) ✅ → Verify ✅ → Export ✅
J5 Pipeline: Runs ✅ → RunDetail ✅ → Retry ✅
J2a Monitoring: restart ✅, auto-refresh ✅
J2a Quality: rubric detail ❌ (kattinthato rubric hianyzik)
J2b Admin: Create User ❌, Generate Key ❌, Revoke Key ❌
J2b Audit: filter ❌, export CSV ❌
```

### API Endpointok (mar leteznek — NINCS backend munka)

```
GET  /api/v1/quality/overview     — osszes eval szam, avg score, pass rate, koltsegek
GET  /api/v1/quality/rubrics      — rubric nev:leiras map
POST /api/v1/quality/evaluate     — { actual, rubric, expected? } → { score, pass, reasoning }

GET  /api/v1/admin/users          — user lista
POST /api/v1/admin/users          — { email, name, password, role? } → UserResponse
GET  /api/v1/admin/api-keys       — key lista
POST /api/v1/admin/api-keys       — { name, user_id? } → { id, name, key, prefix }
DELETE /api/v1/admin/api-keys/{id} — revoke (204)

GET  /api/v1/admin/audit          — ?action=&entity_type=&user_id=&limit=50
GET  /api/v1/admin/audit/{id}     — reszletes entry
```

---

## S39 FELADATOK: 4 lepes

### LEPES 1: C2.4 — Quality Rubric Detail (10 perc)

```
Cel: Rubric tablaban kattinthato sorok → auto-select rubric + highlight

Fajl: aiflow-admin/src/pages-new/Quality.tsx

A) Rubric tabla sorok kattinthatova:
  - onClick={() => setSelectedRubric(name)} a <tr>-re
  - cursor-pointer + hover:bg-gray-50
  - Kivalasztott sor: bg-brand-50/50 dark:bg-brand-900/10 kiemelve

B) Rubric select dropdown sync:
  - Ha tablaban kattintasz, a <select> is frissul (mar selectedRubric state-et hasznalja)
  - Ha dropdown-bol valasztasz, a tabla kiemelese is frissul

Tehat: egyetlen selectedRubric state mindkettot vezerli — mar igy van!
Csak a tabla <tr>-re kell onClick + vizualis kiemelest adni.

tsc ellenorzes
```

---

### LEPES 2: C2.5 — Admin CRUD Dialogok (30 perc)

```
Cel: "Halott gombok" feloldasa: Add User, Generate Key, Revoke Key
     A gombok mar latszanak de nem csinalnak semmit.

Fajl: aiflow-admin/src/pages-new/Admin.tsx

A) Create User dialog:
  State: createUserOpen (boolean), creating (boolean)
  Form state: newEmail, newName, newPassword, newRole (default: "viewer")
  
  Dialog trigger: az actions-beli "Add User" gomb → setCreateUserOpen(true)
  
  Dialog UI (ConfirmDialog HELYETT sajat modal, mert form kell):
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl border ... bg-white p-6 ...">
        <h3>{translate("aiflow.admin.createUserTitle")}</h3>
        <form 4 field: email, name, password, role (select: viewer/operator/admin)>
        <div className="flex justify-end gap-2">
          <button Cancel>
          <button Submit → handleCreateUser>
        </div>
      </div>
    </div>
  
  handleCreateUser:
    POST /api/v1/admin/users { email, name, password, role }
    → setCreateUserOpen(false), resetForm(), ur() (refetch users)
    → catch: error toast (simple alert vagy setError)

B) Generate API Key dialog + key reveal:
  State: generateKeyOpen (boolean), generating (boolean), revealedKey (string | null)
  Form: keyName (string)
  
  Dialog trigger: az actions-beli "Generate Key" gomb → setGenerateKeyOpen(true)
  
  handleGenerateKey:
    POST /api/v1/admin/api-keys { name: keyName }
    → response.key → setRevealedKey(response.key)
    → NEM zarjuk be a dialogot! Key reveal panel jelenik meg:
      - Sarga figyelmeztetes: translate("aiflow.admin.keyRevealWarning")
      - Key megjelenitese: <code className="break-all">{revealedKey}</code>
      - Copy gomb: navigator.clipboard.writeText(revealedKey)
      - "OK" gomb → setRevealedKey(null), setGenerateKeyOpen(false), kr() (refetch keys)

C) Revoke (Delete) API Key:
  State: revokeTarget (string | null), revoking (boolean)
  
  Keys tablaba uj "actions" oszlop:
    { key: "actions", label: "", sortable: false, render: (item) => {
      if (!(item.is_active as boolean)) return null;
      return <button onClick={(e) => { e.stopPropagation(); setRevokeTarget(item.id as string); }} className="text-xs text-red-600 hover:text-red-800">Revoke</button>;
    }}
  
  ConfirmDialog:
    open={!!revokeTarget}
    title={translate("aiflow.admin.revokeKeyConfirm")}
    message={`Key ID: ${revokeTarget?.substring(0, 8)}...`}
    variant="danger"
    onConfirm → DELETE /api/v1/admin/api-keys/{revokeTarget} → setRevokeTarget(null), kr()
    onCancel → setRevokeTarget(null)

D) Actions gomb dinamikus (tab-fuggo):
  Jelenlegi: statikus gomb.
  Uj: onClick bekotes + tab-fuggo logika (mar megvan)
    tab === "users" → setCreateUserOpen(true)
    tab === "keys" → setGenerateKeyOpen(true)

Import: ConfirmDialog, fetchApi

tsc ellenorzes
```

---

### LEPES 3: C2.6 — Audit Filter + Export CSV (20 perc)

```
Cel: Audit oldalon szuro dropdownok + CSV export gomb mukodjon

Fajl: aiflow-admin/src/pages-new/Audit.tsx

A) Filter controls (a PageLayout actions-be vagy a DataTable fole):
  State: filterAction (string), filterEntity (string)
  
  UI (a DataTable folott egy filter sor):
    <div className="mb-4 flex items-center gap-3">
      <select value={filterAction} onChange={...} className="rounded-lg border ...">
        <option value="">{translate("aiflow.audit.all")} - {translate("aiflow.audit.filterAction")}</option>
        <option value="create">create</option>
        <option value="update">update</option>
        <option value="delete">delete</option>
        <option value="login">login</option>
        <option value="evaluate">evaluate</option>
      </select>
      <select value={filterEntity} onChange={...}>
        <option value="">{translate("aiflow.audit.all")} - {translate("aiflow.audit.filterEntity")}</option>
        <option value="user">user</option>
        <option value="api_key">api_key</option>
        <option value="document">document</option>
        <option value="pipeline">pipeline</option>
        <option value="collection">collection</option>
      </select>
    </div>
  
  API hivas modositas:
    Jelenleg: useApi("/api/v1/admin/audit")
    Uj: useApi(`/api/v1/admin/audit?${params}`) ahol params az action + entity_type filter
    
    useMemo url:
      const auditUrl = useMemo(() => {
        const p = new URLSearchParams();
        if (filterAction) p.set("action", filterAction);
        if (filterEntity) p.set("entity_type", filterEntity);
        return `/api/v1/admin/audit?${p.toString()}`;
      }, [filterAction, filterEntity]);
    
    useApi(auditUrl) — ez automatikusan refetch-el URL valtozaskor

B) Export CSV gomb mukodjon:
  Jelenlegi: actions gombban van de nem csinal semmit.
  
  handleExportCsv:
    if (!data?.entries?.length) return;
    const header = "timestamp,action,resource,user_id,details\n";
    const rows = data.entries.map(e =>
      `"${e.created_at}","${e.action}","${e.resource}","${e.user_id}","${JSON.stringify(e.details ?? {}).replace(/"/g, '""')}"`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);

  Actions gomb: onClick={handleExportCsv}
  Szoveg: translate("aiflow.audit.exportCsv")

Import: useMemo, useState

tsc ellenorzes
```

---

### LEPES 4: i18n + tsc + Commit (10 perc)

```
4a) i18n — nincs uj kulcs szukseges! Minden kulcs mar letezik:
    - aiflow.admin.createUserTitle ✅
    - aiflow.admin.keyRevealWarning ✅
    - aiflow.admin.revokeKeyConfirm ✅
    - aiflow.audit.filterAction ✅
    - aiflow.audit.filterEntity ✅
    - aiflow.audit.exportCsv ✅
    
    Ellenorizni: ha megis kell uj kulcs (pl. form label), LEPES 4-ben hozzaadni.

4b) tsc:
    cd aiflow-admin && npx tsc --noEmit → 0 error

4c) Manualis check (ha app fut):
    - /quality: rubric sor kattintas → evaluate form auto-select
    - /admin Users tab: "Add User" → dialog → form → Submit → uj user megjelenik
    - /admin Keys tab: "Generate Key" → dialog → key reveal → Copy → OK → refetch
    - /admin Keys tab: Revoke gomb → ConfirmDialog → DELETE → key eltunt
    - /audit: action + entity filter dropdown → tabla szurodott
    - /audit: "Export CSV" → csv fajl letoltes

4d) Commit:
    git add aiflow-admin/src/pages-new/Quality.tsx \
            aiflow-admin/src/pages-new/Admin.tsx \
            aiflow-admin/src/pages-new/Audit.tsx \
            aiflow-admin/src/locales/hu.json \  (ha kellett)
            aiflow-admin/src/locales/en.json    (ha kellett)
    
    Commit message:
    feat(ui): Sprint C S39 — C2.4-C2.6 Quality rubric click + Admin CRUD + Audit filter/export

Gate: tsc 0 error, Admin CRUD mukodik, Audit CSV exportal
```

---

## KORNYEZET ELLENORZES

```bash
# Jelenlegi allapot
git branch --show-current     # → feature/v1.4.0-ui-refinement
git log --oneline -3           # → 7a7ac67 (S38 commit)

# API endpoint letezik?
curl -s http://localhost:8102/api/v1/admin/users 2>/dev/null | head -3
curl -s http://localhost:8102/api/v1/admin/api-keys 2>/dev/null | head -3
curl -s http://localhost:8102/api/v1/admin/audit?limit=3 2>/dev/null | head -3
curl -s http://localhost:8102/api/v1/quality/rubrics 2>/dev/null | head -3

# Modositando fajlok
wc -l aiflow-admin/src/pages-new/Quality.tsx      # → 320 sor
wc -l aiflow-admin/src/pages-new/Admin.tsx         # → 66 sor
wc -l aiflow-admin/src/pages-new/Audit.tsx         # → 34 sor
```

---

## MEGLEVO KOD REFERENCIAK

```
# Sprint C terv:
01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md   — C2.4-C2.6 szekcio

# API modellek:
src/aiflow/api/v1/admin.py                      — CreateUserRequest, CreateAPIKeyRequest, APIKeyCreatedResponse, DELETE api-keys, audit list (action/entity_type/user_id filter)
src/aiflow/api/v1/quality.py                    — overview, rubrics, evaluate, estimate-cost

# Modositando oldalak:
aiflow-admin/src/pages-new/Quality.tsx           — rubric tabla kattinthato sorok
aiflow-admin/src/pages-new/Admin.tsx             — Create User + Generate Key + Revoke dialog
aiflow-admin/src/pages-new/Audit.tsx             — filter dropdown + export CSV

# Ujrahasznalhato komponensek:
aiflow-admin/src/components-new/ConfirmDialog.tsx — Revoke Key dialoghoz
aiflow-admin/src/lib/api-client.ts               — fetchApi
aiflow-admin/src/lib/hooks.ts                    — useApi (refetch URL valtozaskor)
aiflow-admin/src/lib/i18n.ts                     — useTranslate

# Minta admin CRUD:
aiflow-admin/src/pages-new/Rag.tsx               — Create/Edit/Delete collection dialogs (minta)
aiflow-admin/src/pages-new/Emails.tsx             — Connector CRUD dialog (minta)
```

---

## SPRINT C UTEMTERV

```
S37: C0+C1 — J4 archive + infra + J1 Invoice flow       ✅ DONE
S38: C2.1-C2.3 — RunDetail + Monitoring                  ✅ DONE
S39: C2.4-C2.6 — Quality + Admin CRUD + Audit             ← EZ A SESSION
S40: C4 — RAG chunk search
S41: C5 — Sidebar final + cleanup + polish
S42-S44: C6 — Journey E2E validacio (5 journey)
S45: C7 — Regresszio + v1.4.0 tag
```

---

*Sprint C harmadik session: S39 = C2.4-C2.6 (Quality rubric click + Admin CRUD dialogs + Audit filter/export)*
