# AIFlow Sprint C — Session 40 Prompt (C4.2: RAG Chunk Search + C5 Sidebar Cleanup)

> **Datum:** 2026-04-10
> **Branch:** `feature/v1.4.0-ui-refinement` | **HEAD:** `9b57471`
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** S39 — C2.4-C2.6 DONE (Quality rubric click, Admin CRUD, Audit filter/export)
> **Terv:** `01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md` (C4 + C5 szekcio)
> **Session tipus:** CODE + UI — RAG chunk keresés + Sidebar cleanup + Reviews rename + polish
> **Workflow:** Chunk search backend+UI → Sidebar rename → Dark mode + aria fix → tsc → Commit

---

## KONTEXTUS

### S39 Eredmenyek (C2.4-C2.6 — KESZ)

```
✅ C2.4: Quality rubric tabla sorok kattinthatova, selectedRubric sync
✅ C2.5: Admin Create User dialog, Generate Key + key reveal + copy, Revoke Key ConfirmDialog
✅ C2.6: Audit filter dropdownok (action + entity_type), Export CSV gomb
✅ tsc --noEmit 0 error
```

### Sprint C Allapot

```
19 aktiv UI oldal (18 + RunDetail) + 5 archiv | Login kulon
J1 Invoice: Scan ✅ → Documents(badge) ✅ → Verify ✅ → Export ✅
J5 Pipeline: Runs ✅ → RunDetail ✅ → Retry ✅
J2a Monitoring: restart ✅, auto-refresh ✅
J2a Quality: rubric kattinthato ✅
J2b Admin: Create User ✅, Generate Key ✅, Revoke Key ✅
J2b Audit: filter ✅, export CSV ✅
J3 RAG: Ingest ✅ → Chat ✅ → Chunks (kereses hianyzik) ❌
C5 Sidebar: 6-csoport mar megvan ✅, Reviews "Review Queue" ❌, cleanup ❌
```

---

## S40 FELADATOK: 4 lepes

### LEPES 1: C4.2 — Chunk Kereses Backend (10 perc)

```
Cel: Backend API-ban legyen search query parameter a chunks endpointra.

Fajl: src/aiflow/api/v1/rag_engine.py — list_chunks() fuggveny (~682. sor)

A) Uj query parameter:
  @router.get("/collections/{collection_id}/chunks", response_model=ChunkListResponse)
  async def list_chunks(
      collection_id: str,
      limit: int = Query(50, ge=1, le=200),
      offset: int = Query(0, ge=0),
      q: str = Query("", description="Search chunks by content"),   ← UJ
      document_name: str = Query("", description="Filter by document name"),  ← UJ
  ):

B) SQL modositas (WHERE clause bovites):
  Jelenlegi: WHERE collection = $1
  
  Uj logika:
    conditions = ["collection = $1"]
    params: list[Any] = [coll.name]
    idx = 2
    
    if q.strip():
        conditions.append(f"content ILIKE ${idx}")
        params.append(f"%{q.strip()}%")
        idx += 1
    
    if document_name.strip():
        conditions.append(f"document_name = ${idx}")
        params.append(document_name.strip())
        idx += 1
    
    where = " AND ".join(conditions)
    
    SQL:
      SELECT id, content, document_name, metadata, created_at
      FROM rag_chunks WHERE {where}
      ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx+1}
    
    COUNT is:
      SELECT COUNT(*) FROM rag_chunks WHERE {where}

Tesztelés: curl "http://localhost:8102/api/v1/rag/collections/{id}/chunks?q=szabadsag&limit=10"
```

---

### LEPES 2: C4.2 — Chunk Kereses UI (15 perc)

```
Cel: RagDetail Chunks tab-ban kereso mezo + dokumentum filter

Fajl: aiflow-admin/src/pages-new/RagDetail.tsx — ChunksTab komponens (~534. sor)

A) ChunksTab state bovites:
  const [searchQuery, setSearchQuery] = useState("");
  const [filterDoc, setFilterDoc] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  // Debounce a keresest (300ms)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

B) API URL dinamikus:
  Jelenlegi: useApi<ChunksResponse>(`/api/v1/rag/collections/${collectionId}/chunks?limit=50`)
  
  Uj (useMemo):
    const chunksUrl = useMemo(() => {
      const p = new URLSearchParams();
      p.set("limit", "50");
      if (debouncedQuery) p.set("q", debouncedQuery);
      if (filterDoc) p.set("document_name", filterDoc);
      return `/api/v1/rag/collections/${collectionId}/chunks?${p.toString()}`;
    }, [collectionId, debouncedQuery, filterDoc]);
    
    const { data, loading, error, refetch } = useApi<ChunksResponse>(chunksUrl);

C) Kereso UI (DataTable folott):
  <div className="mb-4 flex items-center gap-3">
    <input
      type="text"
      value={searchQuery}
      onChange={(e) => setSearchQuery(e.target.value)}
      placeholder={translate("aiflow.rag.searchChunks")}
      className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm ... dark:..."
    />
    <select value={filterDoc} onChange={(e) => setFilterDoc(e.target.value)}
      className="rounded-lg border border-gray-300 ...">
      <option value="">{translate("aiflow.audit.all")} — {translate("aiflow.rag.chunkSource")}</option>
      {/* Doksi neveket a chunk adatokbol szedjuk - unique set */}
      {[...new Set((data?.chunks ?? []).map(c => c.document_name).filter(Boolean))].map(d => (
        <option key={d} value={d!}>{d}</option>
      ))}
    </select>
    {(debouncedQuery || filterDoc) && (
      <button onClick={() => { setSearchQuery(""); setFilterDoc(""); }}
        className="text-xs text-gray-500 hover:text-gray-700">Clear</button>
    )}
  </div>

D) Total szam kijelzes (DataTable folott):
  {data && (
    <p className="mb-2 text-xs text-gray-500">{data.total} chunk(s) found</p>
  )}

Import: useState, useEffect, useMemo

i18n uj kulcs szukseges:
  "searchChunks": "Search chunks..." (en), "Chunk keresés..." (hu)
```

---

### LEPES 3: C5 — Sidebar Cleanup + Reviews Rename (15 perc)

```
Cel: Sidebar finomhangolás + Reviews → "Review Queue" + dark mode / aria fix

Fajl: aiflow-admin/src/layout/Sidebar.tsx

A) Reviews atnevezes — MAR MEGVAN! (sor 30):
  { path: "/reviews", labelKey: "aiflow.menu.reviewQueue", icon: "check-circle" }
  
  Ellenorizni en.json + hu.json:
    aiflow.menu.reviewQueue → "Review Queue" (en) / "Ellenorzes" (hu)
    Ha a kulcs nem letezik → hozzaadni (LEPES 4-ben)

B) Sidebar aria-label:
  <aside aria-label="Main navigation" className=...>
  Minden NavLink: uj aria-current="page" support (NavLink mar csinalja)

C) Dark mode konzisztencia ellenorzes:
  - Minden csoport header: dark:text-* MEGVAN ✅
  - Archive csoport: dark:text-gray-600 MEGVAN ✅
  - Osszes interakcio: dark:hover:bg-gray-800 MEGVAN ✅
  → Ha valahol hianyzik, potolni

D) Console error ellenorzes:
  - Figyelni: key= warning, React strict mode duplication, 404-es image, stb.
  - Ha az appot nem tudjuk futtatni, legalabb tsc 0 error

Fajl: aiflow-admin/src/pages-new/Reviews.tsx
  - Ellenorizni, hogy az oldal title "Review Queue"-t mutat
  - Ha meg "Reviews": titleKey-t cserelni

tsc ellenorzes
```

---

### LEPES 4: i18n + tsc + Commit (10 perc)

```
4a) i18n — uj kulcsok (ha szukseges):
  en.json:
    "aiflow.rag.searchChunks": "Search chunks..."
  hu.json:
    "aiflow.rag.searchChunks": "Chunk keresés..."
  
  Ellenorizni: aiflow.menu.reviewQueue letezik-e (valoszinuleg igen)

4b) tsc:
    cd aiflow-admin && npx tsc --noEmit → 0 error

4c) Manualis check (ha app fut):
    - /rag/:id Chunks tab: kereso mezo megjelenik, kereses mukodik
    - /rag/:id Chunks tab: dokumentum filter dropdown
    - Sidebar: "Review Queue" nev
    - Dark mode: sidebar + oldalak konzisztensek
    
4d) Commit:
    git add src/aiflow/api/v1/rag_engine.py \
            aiflow-admin/src/pages-new/RagDetail.tsx \
            aiflow-admin/src/layout/Sidebar.tsx \
            aiflow-admin/src/pages-new/Reviews.tsx \    (ha kellett)
            aiflow-admin/src/locales/hu.json \
            aiflow-admin/src/locales/en.json
    
    Commit message:
    feat(ui): Sprint C S40 — C4.2 RAG chunk search + C5 sidebar cleanup

Gate: tsc 0 error, chunk keresés működik, sidebar clean
```

---

## KORNYEZET ELLENORZES

```bash
# Jelenlegi allapot
git branch --show-current     # → feature/v1.4.0-ui-refinement
git log --oneline -3           # → 9b57471 (S39 commit)

# API endpoint letezik?
curl -s http://localhost:8102/api/v1/rag/collections 2>/dev/null | head -3

# Modositando fajlok
wc -l src/aiflow/api/v1/rag_engine.py                   # chunk list endpoint
wc -l aiflow-admin/src/pages-new/RagDetail.tsx           # ChunksTab
wc -l aiflow-admin/src/layout/Sidebar.tsx                # sidebar cleanup
```

---

## MEGLEVO KOD REFERENCIAK

```
# Sprint C terv:
01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md   — C4.2 + C5 szekcio

# Backend:
src/aiflow/api/v1/rag_engine.py:682             — list_chunks() endpoint, WHERE + LIMIT/OFFSET
  Jelenleg: WHERE collection = $1, nincs kereses
  Cél: WHERE collection = $1 AND content ILIKE $2 AND document_name = $3

# UI:
aiflow-admin/src/pages-new/RagDetail.tsx:534     — ChunksTab komponens (jelenleg: useApi fix URL)
aiflow-admin/src/layout/Sidebar.tsx              — 6 csoport, archive halvanyan
aiflow-admin/src/pages-new/Reviews.tsx           — review queue oldal

# Ujrahasznalas:
aiflow-admin/src/pages-new/Audit.tsx             — MINTA: filter dropdown + useMemo URL (S39-ben keszult)
aiflow-admin/src/lib/hooks.ts                    — useApi automatikusan refetch-el URL valtozaskor

# i18n:
aiflow-admin/src/locales/en.json
aiflow-admin/src/locales/hu.json
```

---

## SPRINT C UTEMTERV

```
S37: C0+C1 — J4 archive + infra + J1 Invoice flow       ✅ DONE
S38: C2.1-C2.3 — RunDetail + Monitoring                  ✅ DONE
S39: C2.4-C2.6 — Quality + Admin CRUD + Audit            ✅ DONE
S40: C4+C5 — RAG chunk search + Sidebar cleanup           ← EZ A SESSION
S41: (MERGED with S40) → tovabblepunk C6-ra
S42-S44: C6 — Journey E2E validacio (5 journey)
S45: C7 — Regresszio + v1.4.0 tag
```

---

*Sprint C negyedik session: S40 = C4.2 + C5 (RAG chunk search + sidebar final)*
