# AIFlow UI — Valos Funkcionalitas Statusz

> **Datum:** 2026-03-30
> **Cel:** Oszinte attekintes arrol, mi mukodik TENYLEGESEN a feluleten, es mi demo/mock adat.

---

## 1. VEGREHAJTAS STATUSZ — MIT LAT A FELHASZNALO

### A jelenlegi helyzet egyetlen mondatban:
> **A felhasznaloi felulet minden oldalon betolt es adatot mutat, de szinte kizarolag mock/demo JSON fajlokat szolgal fel. Valos AI feldolgozas CSAK ha az LLM API kulcs (.env) be van allitva.**

---

## 2. API ROUTE-OK VALOS VISELKEDESE (backend NELKUL)

| Route | Metodus | Mi tortenik MOST | Source jeloles |
|-------|---------|-----------------|----------------|
| `/api/health` | GET | `{ status: "offline" }` — helyes | n/a |
| `/api/process-docs` | GET | Mock JSON (1786 sor) | n/a (nincs source) |
| `/api/process-docs/generate` | POST | 1. Backend FAIL → 2. Subprocess FAIL (nincs API key) → 3. **Mock clone** | `"demo"` |
| `/api/emails` | GET | Mock JSON (300 sor) | `"demo"` |
| `/api/emails/upload` | POST | **MUKODIK** — fajl mentes data/uploads/emails/ | n/a |
| `/api/emails/process` | POST | 1. Backend FAIL → 2. Subprocess FAIL (nincs API key) → **HTTP 500** | `"error"` |
| `/api/documents` | GET | Mock JSON (2269 sor, valos kinyert szamlaadatok) | n/a |
| `/api/documents/upload` | POST | **MUKODIK** — PDF mentes + invoices.json frissites | n/a |
| `/api/documents/process` | POST | 1. PDF→PNG **MUKODIK** → 2. Skill FAIL → 3. **Mock confidence** | mock |
| `/api/cubix` | GET | Mock JSON (87 sor) | `"demo"` |
| `/api/rag/stream` | POST | 1. Backend FAIL → 2. **Mock SSE streaming** (30-80ms/token) | `"demo"` |
| `/api/rag/conversations` | GET | Mock JSON (123 sor) | n/a |
| `/api/runs` | GET | Mock JSON (785 sor) | `"demo"` |

### Legenda:
- **MUKODIK** = valos muvelet (fajl irás, rendering), nincs szukseg API kulcsra
- **Mock** = statikus JSON adat, labelezve mint "demo"
- **FAIL** = hibat dob mert az AI skill API kulcsot igenyel

---

## 3. OLDAL-SZINTU ATTEKINTES

### 3.1 Dashboard (`/`)
- **Adat:** SKILLS konstansbol + runs.json mock
- **Valos?** NEM — a KPI-k mock futasokbol szamoltak
- **Mi mukodik:** Navigacio, skill card-ok, HU/EN toggle
- **Hianyzik:** Valos futasi adatok

### 3.2 Process Documentation (`/skills/process_documentation`)
- **Input:** Textarea — a felhasznalo beir szoveget, megnyomja a "Generate" gombot
- **Valos feldolgozas:** CSAK API kulccsal (subprocess: `python -m skills.process_documentation`)
- **API kulcs nelkul:** Az elso mock dokumentumot klonozza es adja vissza `source: "demo"`-val
- **Diagram:** A Mermaid render MUKODIK (client-side mermaid@11)
- **PipelineBar:** Mindig "completed" — szintetikus, nem valos step statuszok
- **Verdickt:** A felulet szep, de API kulcs nelkul SEMMIT nem general — a mock adatot mutatja

### 3.3 ASZF RAG Chat (`/skills/aszf_rag_chat`)
- **Input:** Chat mezo — a felhasznalo kerdest ir, elküldi
- **Valos feldolgozas:** CSAK ha a FastAPI backend fut (pgvector + OpenAI)
- **Backend nelkul:** Mock valaszt streamel a `rag_conversations.json`-bol
- **Streaming:** MUKODIK vizualisan (SSE token-by-token), de a tartalom mock
- **PipelineBar:** "pending" — nem futott semmi
- **Citations/Search:** Mock adatbol jön, nem valos kereses
- **Verdickt:** A chat elmenye hiteles, de az AI valasz MINDIG ugyan az (mock)

### 3.4 Email Intent Processor (`/skills/email_intent_processor`)
- **Upload:** MUKODIK — .eml/.msg fajlokat ment a szerverre
- **Feldolgozas:** A "Process" gomb **HIBAT DOB** (HTTP 500) — subprocess API kulcs nelkul nem fut
- **Lista:** Mock JSON 300 sor — lathato intent, entity, routing adatokkal
- **PipelineBar:** "completed" — de ezek a mock adatok statuszai
- **Verdickt:** Upload mukodik, feldolgozas NEM. A lista mock adat.

### 3.5 Invoice Processor (`/skills/invoice_processor`)
- **Upload:** MUKODIK — PDF fajlokat ment, invoices.json-t frissiti
- **Batch feldolgozas:** Elindul, de:
  - PDF→PNG rendering **MUKODIK** (pypdfium2)
  - AI field extraction **FAIL** (API kulcs)
  - Fallback: mock confidence (60-84%) — labelezve "mock" parser
- **Tabla:** 2269 sor valos kinyert szamla adat (korabbi futasokbol!)
- **Verdickt:** Az EGYETLEN skill ahol vannak VALOS kinyert adatok (korabbi API-kulcsos futasokbol). Upload es PDF render mukodik.

### 3.6 Cubix Course Capture (`/skills/cubix_course_capture`)
- **Input:** NINCS — read-only viewer (info bar mutatja)
- **Adat:** Mock JSON — nincs `output/` konyvtar a skill-ben
- **Verdickt:** Tisztan demo viewer. Ez helyes es oszinten jelzett.

### 3.7 Costs (`/costs`) + Runs (`/runs`)
- **Adat:** runs.json mock — aggregalt koltseg/token szamok
- **Verdickt:** A szamok koherensek de mock

---

## 4. MI KELL AHHOZ HOGY VALOS LEGYEN

### 4.1 Prerequisites (mindegyik skill-hez)
1. **`.env` fajl** a projekt gyokereben a megfelelo API kulcsokkal:
   ```
   OPENAI_API_KEY=sk-...          # gpt-4o-mini a legtobb skill-hez
   # VAGY
   ANTHROPIC_API_KEY=sk-ant-...   # Claude ha azt hasznalja
   ```
2. **Docker services** a RAG-hoz:
   ```bash
   docker compose up -d db        # PostgreSQL + pgvector
   docker compose up -d redis     # Redis (queue-hoz)
   docker compose up -d kroki     # Kroki (SVG diagramokhoz)
   ```

### 4.2 Skill-enkenti igeny

| Skill | API kulcs | Docker | Egyeb |
|-------|-----------|--------|-------|
| process_documentation | OpenAI (gpt-4o-mini) | Kroki (opcio, SVG-hez) | — |
| aszf_rag_chat | OpenAI | PostgreSQL+pgvector | Eloszor `ingest` kell: `python -m skills.aszf_rag_chat ingest --source docs/` |
| email_intent_processor | OpenAI | — | Schema fajlok (`skills/email_intent_processor/schemas/`) |
| invoice_processor | OpenAI (gpt-4o) | — | PDF fajlok a `data/uploads/` mappaban |
| cubix_course_capture | OpenAI | — | Video fajlok + Playwright (nem UI-bol inditható) |

### 4.3 Hogyan tesztelhetjük a valos mukodest

```bash
# 1. API kulcs beallitas
cp .env.example .env
# Szerkeszd a .env-t: OPENAI_API_KEY=sk-...

# 2. Teszteld a skill-t CLI-bol ELOSZOR
python -m skills.process_documentation --input "Szabadsag igenyeles folyamata" --output ./test_out

# 3. Ha a CLI mukodik, a UI subprocess is mukodni fog
cd aiflow-ui && npm run dev
# Nyisd meg http://localhost:3000/skills/process_documentation
# Irj be szoveget → "Generate" → valos diagram jelenik meg source: "subprocess"-sel
```

---

## 5. A MOCK ADAT HELYZETE

### Jelenlegi mock fajlok (aiflow-ui/data/)
| Fajl | Meret | Tartalom |
|------|-------|----------|
| `invoices.json` | 2269 sor | **VALOS** kinyert szamla adatok (korabbi futasokbol) |
| `process_docs.json` | 1786 sor | **VALOS** generalt BPMN diagramok (korabbi futasokbol) |
| `runs.json` | 785 sor | Futasi naplo (keverek: valos + mock) |
| `emails.json` | 300 sor | **SZINTETIKUS** minta email klasszifikaciok |
| `rag_conversations.json` | 123 sor | **SZINTETIKUS** minta RAG beszelgetesek |
| `cubix_courses.json` | 87 sor | **SZINTETIKUS** minta kurzus adatok |

> Megjegyzes: Az `invoices.json` es `process_docs.json` **valos AI kimeneteket** tartalmaz korabbi fejlesztesi futasokbol. A tobbi szintetikus.

---

## 6. MI A KOVETKEZO LEPES?

### Opcio A: "Demo-First" megkozlites
A jelenlegi allapot elfogadhato DEMO celra:
- Minden oldal betolt, szep, navigalhato
- Source badge-ek oszintek ("Demo")
- Mock adatok realistak
- **Teendo:** Dokumentalni mint demo, ne reklamazzon mint production

### Opcio B: "One Skill End-to-End" megkozlites
Valasszunk EGY skill-t es vigyuk vegig:
1. API kulcs beallitas
2. CLI teszteles
3. UI teszteles valos adattal
4. A tobbi skill marad demo
- **Ajanlott skill:** `process_documentation` (legegyszerubb, nincs DB fugges)

### Opcio C: "Full Stack" megkozlites
Minden skill valosra:
1. Docker compose up (PostgreSQL, Redis, Kroki)
2. API kulcsok beallitas
3. RAG ingest futatas
4. Minden skill CLI teszteles
5. FastAPI backend inditasa
- **Idoigeny:** 2-4 ora setup + debugging

---

## 7. OSSZEFOGLALAS TABLAZAT

| Skill | UI felulet | Mock adat | Valos subprocess | Valos backend |
|-------|-----------|-----------|-----------------|---------------|
| Process Docs | ✅ Egyszeru | ✅ Demo labelezve | ⚠️ API kulcs kell | ❌ Nem fut |
| RAG Chat | ✅ Egyszeru | ✅ Demo streaming | ❌ Nincs subprocess | ⚠️ DB + API kell |
| Email Intent | ✅ Egyszeru | ✅ Demo labelezve | ⚠️ API kulcs kell | ❌ Nem fut |
| Invoice | ✅ Komplex | ✅ Valos korabbi adat | ⚠️ API kulcs kell | ❌ Nem fut |
| Cubix | ✅ Viewer | ✅ Demo labelezve | ❌ CLI only | ❌ CLI only |

> ✅ = Mukodik most | ⚠️ = Mukodhet beallitassal | ❌ = Nem elerheto
