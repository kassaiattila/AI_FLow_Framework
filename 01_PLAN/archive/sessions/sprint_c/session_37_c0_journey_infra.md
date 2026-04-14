# AIFlow Sprint C — Session 37 Prompt (C0+C1: Journey Infra + J1 Invoice Flow + J4 Archive)

> **Datum:** 2026-04-12
> **Branch:** `feature/v1.4.0-ui-refinement` (UJ, main-bol) | **HEAD main:** `9113c43`
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** S36 — B11 DONE (v1.3.0 tag + squash merge → main)
> **Terv:** `01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md` (C0 + C1 szekcio)
> **Session tipus:** CODE + UI — J4 archivalas, ConfirmDialog, J1 Invoice flow fix
> **Workflow:** Branch → J4 archive → ConfirmDialog → Dashboard fix → Scan trigger → Documents badge → Commit(ok)

---

## KONTEXTUS

### Miert Sprint C?

A v1.3.0-ban 23 UI oldal van, de ~8-nak hasznalhatosagi problemaja van (halott gombok, hianyzo CRUD).
Sprint C **szukiti a portalt 3 fo funkciora** es azokat **melyiti journey-first megkozelitessel:**

1. **Dokumentum Feldolgozas + Email Intent** (J1) — fo uzleti ertek
2. **RAG Chat** (J3) — tudasbazis
3. **Pipeline Management** (J5) — orchestration + debug

Plusz kiegeszito: Monitoring (J2a) + Admin (J2b).

A J4 (Generation: ProcessDocs, SpecWriter, Media, Cubix, RPA) oldalak **archivalva** lesznek —
fajlok atkerulnek `pages-archive/` mappaba, sidebar-ban halvany "Archiv" csoport marad.

### Sprint B Vegleges Allapot (v1.3.0 — kiindulas)

```
27 service | 175 endpoint | 48 DB tabla | 31 migracio | 7 skill
23 UI oldal | 1443 unit | 121 E2E | 96 promptfoo | ruff+tsc CLEAN
```

### Sprint C Cel Allapot (v1.4.0)

```
18 aktiv UI oldal + 5 archiv | 1 UJ oldal (RunDetail)
0 halott gomb | minden journey E2E PASS
0 backend valtozas — tisztan frontend sprint
```

---

## S37 FELADATOK: 6 lepes

### LEPES 1: Branch letrehozas (2 perc)

```
git checkout main
git pull origin main
git checkout -b feature/v1.4.0-ui-refinement
```

---

### LEPES 2: C0.3 — J4 Archivalas (20 perc)

```
Cel: 5 oldal athelyezese archive mappaba + router + sidebar update.

KONKRET TEENDOK:

2a) Archive mappa letrehozasa:
    mkdir -p aiflow-admin/src/pages-archive

2b) Fajlok athelyezese:
    git mv aiflow-admin/src/pages-new/ProcessDocs.tsx  aiflow-admin/src/pages-archive/
    git mv aiflow-admin/src/pages-new/SpecWriter.tsx   aiflow-admin/src/pages-archive/
    git mv aiflow-admin/src/pages-new/Media.tsx        aiflow-admin/src/pages-archive/
    git mv aiflow-admin/src/pages-new/Cubix.tsx        aiflow-admin/src/pages-archive/
    git mv aiflow-admin/src/pages-new/Rpa.tsx          aiflow-admin/src/pages-archive/

2c) router.tsx modositas:
    - Torold az 5 import sort (ProcessDocs, SpecWriter, Media, Cubix, Rpa)
    - Torold a route definiciokat VAGY csereld Navigate to="/" redirect-re:
      { path: "process-docs", element: <Navigate to="/" replace /> },
      { path: "spec-writer", element: <Navigate to="/" replace /> },
      { path: "media", element: <Navigate to="/" replace /> },
      { path: "cubix", element: <Navigate to="/" replace /> },
      { path: "rpa", element: <Navigate to="/" replace /> },

2d) Sidebar.tsx modositas:
    JELENLEGI 6 csoport:
      documentProcessing, knowledgeBase, generation, monitoring, settings, bottom
    
    UJ 6 csoport:
      documentProcessing:  Documents, Emails, Reviews(→"Review Queue")
      knowledgeBase:       RAG
      pipelineAndRuns:     Runs, Pipelines, Services  (UJ csoport!)
      monitoring:          Costs, Monitoring, Quality
      admin:               Admin, Audit
      archive:             ProcessDocs, SpecWriter, Media, Cubix, RPA
                           (collapsed by default, halvany/disabled stilus)

    A "generation" es "bottom" csoportok → "archive" csoportba osszevonva
    
    Archive csoport stilusa:
      - defaultOpen: false (mindig collapsed)
      - labelKey: "aiflow.menu.archive"
      - item szin: text-gray-400 (halvany)
      - Kattintasra: navigate("/") (dashboard redirect, nem az archivalt oldal)
      
2e) Dashboard.tsx: 
    - Torold a J4 "Generalas" journey kartyat
    - Maradt: J1 "Szamlafeldolgozas", J3 "Tudasbazis", J5 "Pipeline Futasok"
    - J1 kartya onClick: navigate("/emails") (NEM /documents — R9 fix!)

2f) tsc ellenorzes: cd aiflow-admin && npx tsc --noEmit → 0 error

Commit: refactor(ui): C0.3 archive J4 pages (ProcessDocs, SpecWriter, Media, Cubix, RPA) + sidebar restructure
```

---

### LEPES 3: C0.1 — ConfirmDialog Komponens (15 perc)

```
Cel: Ujrahasznosithato megerosito dialog minden torlesi/veszélyes muvelethez.

Fajl: aiflow-admin/src/components-new/ConfirmDialog.tsx

Minta: Emails.tsx ConnectorFormDialog (542-642. sor) overlay minta

Props interface:
  interface ConfirmDialogProps {
    open: boolean;
    title: string;
    message: string;
    confirmLabel?: string;     // default: "Confirm"
    cancelLabel?: string;      // default: "Cancel"
    variant?: "danger" | "default";  // danger = piros gomb
    loading?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
  }

Implementacio:
  - if (!open) return null;
  - Portal: fixed inset-0 z-50 bg-black/40 overlay
  - Kartya: max-w-md rounded-xl border bg-white dark:bg-gray-900
  - Title: text-lg font-semibold
  - Message: text-sm text-gray-600
  - Gombok: Cancel (gray outline) + Confirm (brand/red based on variant)
  - Loading: spinner a Confirm gombon + disabled
  - Esc billentyű: onCancel
  - aria-label mindket gombon

tsc ellenorzes

Commit: feat(ui): C0.1 ConfirmDialog reusable component
```

---

### LEPES 4: C0.2 — i18n Kulcsok (10 perc)

```
Cel: Minden C1-C6 dialoghoz kellő i18n kulcsok.

Fajlok: aiflow-admin/src/locales/hu.json + en.json

UJ KULCSOK (hu/en):
  # Admin (C2.5)
  aiflow.admin.createUserTitle:     "Felhasznalo letrehozasa" / "Create User"
  aiflow.admin.createUserSuccess:   "Felhasznalo sikeresen letrehozva" / "User created successfully"
  aiflow.admin.generateKeyTitle:    "API Kulcs generalas" / "Generate API Key"
  aiflow.admin.keyRevealWarning:    "Ez a kulcs tobbe nem jelenik meg!" / "This key will not be shown again!"
  aiflow.admin.copyKey:             "Masolas" / "Copy"
  aiflow.admin.revokeKeyConfirm:    "Biztosan visszavonod ezt az API kulcsot?" / "Revoke this API key?"
  
  # Monitoring (C2.3)
  aiflow.monitoring.restartConfirm:  "Biztosan ujrainditod a {{service}} szolgaltatast?" / "Restart {{service}}?"
  aiflow.monitoring.autoRefresh:     "Auto-frissites" / "Auto-refresh"
  
  # Audit (C2.6)
  aiflow.audit.filterAction:   "Muvelet szurése" / "Filter by action"
  aiflow.audit.filterEntity:   "Tipus szurése" / "Filter by entity"
  aiflow.audit.exportCsv:      "Exportalas CSV" / "Export CSV"
  
  # Documents (C1.2)
  aiflow.documents.confidence:      "Biztossag" / "Confidence"
  aiflow.documents.summaryApproved: "jovahagyva" / "approved"
  aiflow.documents.summaryRejected: "elutasitva" / "rejected"
  aiflow.documents.summaryPending:  "fuggoben" / "pending"
  
  # Emails (C1.1)
  aiflow.emails.scanStart:    "Scan Inditas" / "Start Scan"
  aiflow.emails.scanRunning:  "Pipeline fut..." / "Pipeline running..."
  aiflow.emails.scanComplete: "Eredmenyek megtekintese" / "View Results"
  
  # Sidebar (C0.3)
  aiflow.menu.pipelineAndRuns: "Pipeline & Futasok" / "Pipelines & Runs"
  aiflow.menu.admin:           "Adminisztracio" / "Administration"
  aiflow.menu.archive:         "Archiv" / "Archive"
  aiflow.menu.reviewQueue:     "Review Queue" / "Review Queue"

tsc ellenorzes

Commit: feat(ui): C0.2 i18n keys for Sprint C dialogs
```

---

### LEPES 5: C1.1 + C1.2 — J1 Invoice Journey Fix (45 perc)

```
Cel: J1 journey fo flow mukodjon: Scan → Documents(badge) → Verify → Export

=== C1.1: Email Scan Pipeline Trigger (20 perc) ===

Fajl: aiflow-admin/src/pages-new/Emails.tsx

Pozicio: Inbox tab fejlec (a "Process All" gomb melle)

Uj state: const [scanning, setScanning] = useState(false);
          const [scanResult, setScanResult] = useState<string | null>(null);

Uj gomb JSX (az Inbox tab actions regiojaba):
  <button
    onClick={handleScan}
    disabled={scanning}
    className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
  >
    {scanning ? translate("aiflow.emails.scanRunning") : translate("aiflow.emails.scanStart")}
  </button>

handleScan implementacio:
  const handleScan = async () => {
    setScanning(true);
    setScanResult(null);
    try {
      // Eloszor probaljuk a template deploy-t
      await fetchApi("POST", "/api/v1/pipelines/templates/invoice_finder_v3_offline/deploy");
      setScanResult("success");
    } catch (err) {
      // Ha a template nem letezik, probaljuk a sima invoice finder-t
      try {
        await fetchApi("POST", "/api/v1/pipelines/templates/invoice_finder_v3/deploy");
        setScanResult("success");
      } catch {
        setScanResult("error");
      }
    } finally {
      setScanning(false);
    }
  };

Scan eredmeny banner (az Inbox tab tetejen):
  {scanResult === "success" && (
    <div className="mb-3 rounded-lg bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/20">
      Pipeline elindult — <button onClick={() => navigate("/documents")} className="font-semibold underline">
        {translate("aiflow.emails.scanComplete")} →
      </button>
    </div>
  )}

=== C1.2: Documents Confidence + Export + Banner (25 perc) ===

Fajl: aiflow-admin/src/pages-new/Documents.tsx

A) Confidence badge oszlop — uj oszlop a columns array-ba:
  {
    key: "extraction_confidence",
    label: translate("aiflow.documents.confidence"),
    render: (item) => {
      const conf = Number(item.extraction_confidence ?? 0);
      if (!conf) return <span className="text-xs text-gray-400">—</span>;
      const level = conf >= 0.9 ? "high" : conf >= 0.7 ? "medium" : "low";
      const colors = {
        high: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400",
        medium: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
        low: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400",
      };
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[level]}`}>
        {Math.round(conf * 100)}%
      </span>;
    }
  }

B) Export auth fix — keresendo: export link/gomb, cserélendo:
  const handleExport = async (format: "csv" | "json") => {
    const res = await fetchApi("GET", `/api/v1/documents/export/${format}`, null, { rawResponse: true });
    const blob = await (res as Response).blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aiflow_documents.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

C) Summary banner — a DataTable felett, uj szekció:
  const approved = (data?.documents ?? []).filter(d => d.status === "approved").length;
  const rejected = (data?.documents ?? []).filter(d => d.status === "rejected").length;
  const pending = (data?.documents ?? []).filter(d => !["approved","rejected"].includes(d.status)).length;

  {data && (
    <div className="mb-3 flex gap-3 text-sm">
      <span className="rounded-full bg-green-50 px-3 py-1 text-green-700">✅ {approved} {translate("aiflow.documents.summaryApproved")}</span>
      <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700">⏳ {pending} {translate("aiflow.documents.summaryPending")}</span>
      <span className="rounded-full bg-red-50 px-3 py-1 text-red-700">❌ {rejected} {translate("aiflow.documents.summaryRejected")}</span>
    </div>
  )}

tsc ellenorzes

Commit: feat(ui): C1 J1 Invoice journey — scan trigger + confidence badge + export fix + summary banner
```

---

### LEPES 6: Regresszio + Veglegesites (15 perc)

```
6a) Unit tesztek:
    pytest tests/unit/ -q --tb=line → 1443+ PASS

6b) TypeScript + lint:
    cd aiflow-admin && npx tsc --noEmit → 0 error
    ruff check src/aiflow/ tests/ → 0 error

6c) Manualis tesztek (futo app):
    - Login → Dashboard: 3 journey kartya (nem 4!)
    - J1 kartya → /emails (NEM /documents!)
    - Emails Inbox: "Scan Inditas" gomb lathato
    - Documents lista: confidence badge szinekkel
    - Documents: Export CSV letoltes mukodik
    - Documents: Summary banner lathato (X jova / Y fugg / Z elut)
    - Sidebar: Archiv csoport halvany, collapsed
    - Sidebar: "Pipeline & Futasok" uj csoport (Runs, Pipelines, Services)
    - /process-docs, /spec-writer, /media, /cubix, /rpa → redirect /

Gate: Minden fenti pont PASS
```

---

## KORNYEZET ELLENORZES

```bash
# Jelenlegi allapot
git branch --show-current     # → main
git log --oneline -3           # → 9113c43 (v1.3.0)

# UI fajlok (ezeket modositjuk)
wc -l aiflow-admin/src/pages-new/Emails.tsx      # → ~1000+ sor
wc -l aiflow-admin/src/pages-new/Documents.tsx    # → ~400+ sor
wc -l aiflow-admin/src/pages-new/Dashboard.tsx    # → ~460+ sor
wc -l aiflow-admin/src/layout/Sidebar.tsx         # → ~175 sor
wc -l aiflow-admin/src/router.tsx                 # → ~100 sor

# Dashboard J1 kartya (ellenorizni — hova navigal jelenleg?)
grep -n "navigate" aiflow-admin/src/pages-new/Dashboard.tsx | head -10

# Admin halott gomb (45. sor — onClick nincs)
sed -n '44,46p' aiflow-admin/src/pages-new/Admin.tsx

# Pipeline templates (Scan trigger endpoint)
curl -s http://localhost:8102/api/v1/pipelines/templates/list 2>/dev/null | head -5

# Jelenlegi sidebar csoportok
grep -A2 "labelKey" aiflow-admin/src/layout/Sidebar.tsx
```

---

## MEGLEVO KOD REFERENCIAK

```
# Sprint C terv:
01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md   — Fokuszalt journey-first terv (5 journey, 10 session)
01_PLAN/64_SPRINT_C_UI_FIX_PLAN.md             — Fix referencia (Reusable Assets tabla)

# Minta komponensek:
aiflow-admin/src/pages-new/Emails.tsx:542-642   — ConnectorFormDialog (ConfirmDialog minta)
aiflow-admin/src/pages-new/Emails.tsx:160-169   — CSV export Blob URL minta
aiflow-admin/src/pages-new/Verification.tsx     — Confidence szin-kodolas minta

# Modositando fajlok (ebben a session-ben):
aiflow-admin/src/components-new/ConfirmDialog.tsx  (UJ)
aiflow-admin/src/pages-new/Dashboard.tsx           (J4 kartya torles + J1 fix)
aiflow-admin/src/pages-new/Emails.tsx              (Scan trigger gomb)
aiflow-admin/src/pages-new/Documents.tsx           (badge + export + banner)
aiflow-admin/src/layout/Sidebar.tsx                (6 csoport atstruktura)
aiflow-admin/src/router.tsx                        (J4 route-ok redirect)
aiflow-admin/src/locales/hu.json + en.json         (i18n kulcsok)
```

---

## SPRINT C TELJES UTEMTERV

```
S37: C0+C1 — J4 archive + infra + J1 Invoice flow       ← EZ A SESSION
S38: C2.1-C2.3 — RunDetail UJ OLDAL + Monitoring restart
S39: C2.4-C2.6 — Quality + Admin CRUD + Audit
S40: C4 — RAG chunk search
S41: C5 — Sidebar final + cleanup + polish
S42-S44: C6 — Journey E2E validacio (5 journey)
S45: C7 — Regresszio + v1.4.0 tag
```

---

*Sprint C elso session: S37 = C0+C1 (J4 archivalas + Journey infra + J1 Invoice flow)*
