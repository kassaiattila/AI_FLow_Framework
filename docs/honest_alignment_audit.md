# AIFlow honest alignment audit

> **Datum:** 2026-04-26
> **Trigger:** Sprint W close (`v1.7.0` queued, SW-5 PR #60 merged at `fed97af`).
> **Statusz:** OPERATOR-APPROVED — ez a doc valtoztatja meg a Sprint X iranyt
> es a sprint-tervezesi folyamatot.
> **Output deliverables (mind ebben az SX-1 PR-ben):**
> - `docs/honest_alignment_audit.md` (ez a fajl)
> - `docs/SPRINT_HISTORY.md` (uj — a regi CLAUDE.md banner ide kerul)
> - `01_PLAN/121_SPRINT_X_QUALITY_PUSH_PLAN.md` (uj)
> - `01_PLAN/ROADMAP.md` (rewrite — aktualis allapotra)
> - `CLAUDE.md` (slim, ~80-100 sor)
> - `session_prompts/_TEMPLATE.md` (uj — Quality target kotelezo fej)
> - `scripts/run_quality_baseline.sh` (uj — 4 UC merhetoseg)
> - `session_prompts/NEXT.md` → SX-2 prompt

---

## 0. Vezetoi osszefoglalo

8 sprint mult el a `110_USE_CASE_FIRST_REPLAN.md` policy authoring-ja
(S93, 2026-04-19) ota. A policy egyetlen szabaly volt:

> *every sprint from v1.4.5 forward must close with exactly one
> use-case going end-to-end green. Architecture work rides the use-case
> it enables; it does not get its own sprint.*

A Sprint M-W trajectory ezt a szabalyt **rendszeresen megsertette.** A
sprintek tartalma egyre inkabb infrastrukturara, polish-ra, scaffold-ra
(PromptWorkflow, multi-tenant cleanup) tolodott el — ahelyett, hogy a
ket fo felhasznaloi funkciot melyitettuk volna:

1. **dokumentum + email tortzs intent + adatpont kinyeres + routing**
2. **RAG chat — professzionalis chunkolas + vektor DB menedzsment**

Ez a doc:
- megerositi a drift-et szam szerint (1. szakasz)
- meri a 4 use-case **tenyleges** allapotat es a `professzionalis`-tol valo
  tavolsagat (2. szakasz)
- definialja a Sprint X-Y-Z helyes iranyat (3. szakasz)
- operacionalizalja a folyamatot (4. szakasz) — uj template + run_quality_baseline.sh
  + sprint-close metric gate, hogy a drift NE ismetlodjon

---

## 1. A drift szam szerint

### 1.1. ROADMAP.md elavult — utolso frissitese 2026-04-28 (S93 close)

A `01_PLAN/ROADMAP.md` aktivnak hirdeti **Sprint I-t (v1.4.5)** S94 "QUEUED"
szessziojaval. A valosagban azota Sprint M, N, O, P, Q, R, S, T, U, V, W
shipped (v1.4.9 → v1.7.0). A roadmap **8 sprintet kihagyott** a frissites
soran — ez maga is statussz-toxin: ha a forward queue a multbeli celokat
hirdeti, az operator es az ev jelenlegi szessziok nem latjak melyik valos
fok mar zarult vagy mar mas iranyt vett.

### 1.2. A 110_*-replan policy compliance tabla

| Sprint | Tag | Kohorsz | Use-case-et zart? | Megjegyzes |
|---|---|---|---|---|
| M | v1.4.9 | Vault hvac + Langfuse self-host | ❌ infra-only | Phase 3 munka, de a `110_*` szabaly szerint ennek egy use-case-en kellett volna `ride`-olnia |
| N | v1.4.10 | Cost guardrail + per-tenant budget | ❌ infra-only | UC4 monitoring/cost cohort, de nem koncentralt UC1/2/3 konkret melyitesere |
| O | v1.4.11 | UC3 attachment-aware intent | ✅ UC3 | korrekt — UC3 misclass 56% → 32% |
| P | v1.4.12 | UC3 LLM-fallback body/mixed | ✅ UC3 | korrekt — UC3 misclass 32% → 4% |
| Q | v1.5.0 | UC1 intent + extraction unification | ✅ UC1 | korrekt — UC1 85.7% accuracy 10-fixture |
| R | v1.5.1 | PromptWorkflow scaffold | ❌ scaffold-only | "Per-skill code migration explicitly deferred" — szabaly szerint nem futhatott volna ki kulon sprintkent |
| S | v1.5.2 | Multi-tenant + multi-profile vector DB | ⚠️ infra (UC2 cohort) | tenant filter + embedder profile editor — UI shipped de UC2 retrieval quality nem javult |
| T | v1.5.3 | PromptWorkflow per-skill consumer migration | ⚠️ refactor | 3 skill (UC1+UC2+UC3) erintett, de mindharom **byte-stable** maradt — semmi minosegi javulas |
| U | v1.5.4 | "Operational hardening + carry-forward catch-up" | ❌ polish | sajat plan deklaralja: "Zero new functional capability; the win is operability" |
| V | v1.6.0 | Generic DocRecognizer skill | ✅ uj use-case (UC1-General) | korrekt — uj use-case shipped, de csak synthetic fixture-on |
| W | v1.7.0 | Multi-tenant cleanup + boot guard + Langfuse stub | ❌ polish | a `AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` explicit megmondta: ezeket halasszuk amig a 4 UC szilardan mukodik. Nem vartuk meg. |

**Osszesen 11 sprintbol 6 (M, N, R, S, U, W) tisztan infra/polish/scaffold.** Nem
tortene meg, ha a sprint-close gate ellenorizte volna a use-case metric
javulast.

### 1.3. Az AUDIT_2026_04_26 explicit eldontotte, mit NE csinaljunk most

`01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` zarosora:

> *Strategic gap audit (Vault prod, customer→tenant_id rename, coverage 80%,
> observability) → defer, akkor csinaljunk amikor UC1 + UC2 + UC3 +
> doc-recognizer mind szilardan mukodik.*

A Sprint W ezeket pontosan **most kezdte el** (`AIFLOW_ENV=prod` boot guard,
`customer` → `tenant_id` rename, Langfuse listing), miközben:

- UC1 invoice extraction: 85.7% accuracy 10 synthetic fixture-on (nem 25, nem real-corpus)
- UC2 RAG: MRR@5 = 0.55 baseline (nincs hybrid search, nincs semantic chunking)
- UC3 email intent: 4% misclass DE csak attachment-aware (body-only thread-aware nincs)
- DocRecognizer: 5 doctype 100% **synthetic** fixture-on (nincs real-PDF corpus)

**Egyik sem "szilardan mukodik".** A defer-felteteI nem teljesult. A Sprint W
mégis lefutott.

---

## 2. A 4 use-case tenyleges allapota es a "professzionalis" gap

A ket fo felhasznaloi funkcio (operator szandek):
1. **Dok + email tortzs intent + adatpont kinyeres + routing/kategorizalas**
2. **RAG chat — professzionalis chunkolas + vektor DB menedzsment**

### 2.1. UC1 — Magyar szamla extraction (`invoice_processor`)

| Dimenzio | Jelen | "Professzionalis" cel |
|---|---|---|
| Accuracy (10-fixture synthetic) | 85.7% | ≥ 95% |
| `issue_date` kinyeres | <100% (Sprint Q SQ-FU-1 polish utan, de meg nincs ellenorizve real-corpus-on) | ≥ 95% real-corpus-on |
| Corpus | 10 reportlab-generalt synthetic | 25 fixture, kozule 10+ real anonimizalt magyar szamla |
| Cost per call | ~$0.0004 (gpt-4o-mini) | mert + ceiling enforcement |
| Real-corpus measure | nincs | scripts/measure_uc1_golden_path.py futassal |
| Failure mode handling | partial — `route_to_human` nincs UI-ban kotve | UI escalation flow |

**Gap nev:** `valos magyar szamla teszt + escalation flow + SQ-FU-3 corpus extension`.

### 2.2. UC3 — Email intent (`email_intent_processor`)

| Dimenzio | Jelen | "Professzionalis" cel |
|---|---|---|
| Misclass (25-fixture, attachment-aware) | 4% | ≤ 1% |
| Body-only cohort | 6/6 (Sprint P) | csak ezzel a cohorsszal nem ellenorizheto thread-aware viselkedes |
| Mixed cohort | 6/7 — `024_complaint` body-vs-attachment intractable conflict (SP-FU-1) | 7/7 |
| Thread-aware classifier | nincs (SP-FU-3 architektura-sprintre halasztva) | shipped |
| Valos mailbox volume | nem tesztelt | live IMAP/Microsoft Graph fixture set |
| PII redaction (telefonszam/IBAN/email) | regex v0 (Sprint K) | 7-fields tested coverage |

**Gap nev:** `thread-aware + 024_complaint + valos mailbox volume`.

### 2.3. DocRecognizer — UC1-General (`document_recognizer`)

| Dimenzio | Jelen | "Professzionalis" cel |
|---|---|---|
| Doc-type accuracy (8-fixture synthetic) | 100% top-1 | tartani de real-corpus-on |
| Real-PDF corpus | nincs (SW-FU-5 nyitott) | 5 anonimizalt fixture / doctype × 5 doctype = 25 |
| Extraction wire-up | Sprint W SW-1 — `hu_invoice` reuse + `hu_id_card` 2-fixture real-LLM | minden 5 doctype-on real-corpus ≥ 80% |
| Intent routing rule editor UI | nincs (a router accept-eli `?source=`, de nincs UI side-drawer) | UI mintaja UC3 intent-rules editor (S109a) |
| PII redaction layer | descriptor-szinten (`pii_level`), boundary-design — de nincs end-to-end tested PII roundtrip | live test 1 ID-card + 1 passport fixture-on, audit log redacted |
| Override per tenant | YAML editor side-drawer (Sprint V SV-4 textarea) | textarea OK, Monaco SV-FU-5 nice-to-have |

**Gap nev:** `real-corpus + intent-routing UI + PII roundtrip test`.

### 2.4. UC2 — RAG chat (`aszf_rag_chat`)

| Dimenzio | Jelen | "Professzionalis" cel |
|---|---|---|
| Retrieval quality (MRR@5) | 0.55 baseline (Profile A BGE-M3) | ≥ 0.72 |
| Chunker | csak `UnstructuredChunker` (token-window) | semantic + heading-aware + table-preservation, multilingual HU+EN |
| Hybrid search | nincs | BM25 + vector RRF shipped |
| Cross-encoder reranker | OSError fallback path van; production wiring nincs | live wired, ezred-rangban kalkulal |
| Embedder Profile B | Azure OpenAI credit-pending | ha credit beerkezik: live MRR@5 mert |
| Reembedding workflow | nincs | UI + worker, collection re-embed end-to-end |
| Collection-level reorg (split/merge/rename) | nincs | API + UI shipped |
| Per-tenant izolacio E2E test | DB-szintu (Alembic 047 unique constraint) — nincs viselkedes-szintu E2E test | 1 E2E test per tenant collection isolation |
| Ingest UI | aszf_rag_chat Reflex UI `rx.window_alert("Upload - TODO")` (`config_page.py:27`) | UI completion |

**Gap nev:** `semantic chunker + hybrid search + reembed workflow + collection management UI + ingest TODO`.

### 2.5. Aggregalt nyomonkoveto json minta (run_quality_baseline.sh output)

```json
{
  "timestamp": "2026-04-26T00:00:00Z",
  "use_cases": [
    {"name": "UC1_invoice", "metric": "accuracy", "value": 0.857, "target": 0.92, "delta_to_target": -0.063, "gate": "below"},
    {"name": "UC2_rag", "metric": "mrr_at_5_profile_a", "value": 0.55, "target": 0.65, "delta_to_target": -0.10, "gate": "below"},
    {"name": "UC3_email", "metric": "misclass_rate", "value": 0.04, "target": 0.01, "delta_to_target": 0.03, "gate": "below"},
    {"name": "DocRecognizer", "metric": "real_corpus_accuracy_per_doctype_min", "value": null, "target": 0.80, "delta_to_target": null, "gate": "no-corpus"}
  ],
  "verdict": "4 use-case below target — Sprint X scope confirmed"
}
```

---

## 3. Az uj irany — Sprint X-Y-Z

### 3.1. Sprint X — "UC1 + UC3 + DocRecognizer **deep quality push**"

**Theme:** dokumentum + email intent + adatpont kinyeres szilardda tetele.

| Session | Mit szallit | Merheto cel (elott → utan) |
|---|---|---|
| **SX-1** | THIS SESSION — alignment audit + ROADMAP rewrite + CLAUDE slim + new template + run_quality_baseline.sh + 121_*_PLAN.md publish | dokumentacio-csak; baseline mert |
| **SX-2** | UC1 corpus extension 25 anonimizalt+synthetic fixture + `issue_date` deep-fix + measure_uc1_golden_path.py 25-fixture mode | UC1 85.7% → ≥ 92%; `issue_date` ≥ 95% |
| **SX-3** | DocRecognizer **valos anonimizalt** PDF/scan corpus (5 per doctype × 5 = 25) + per-doctype accuracy gate | per-doctype real-corpus ≥ 80% |
| **SX-4** | UC3 thread-aware classifier (SP-FU-3) + `024_complaint` conflict (SP-FU-1) + measure_uc3 → uniform `--output` | misclass 4% → ≤ 1% |
| **SX-5** | DocRecognizer admin UI: intent-routing rule editor (UC3 intent-rules editor mintaja) + PII-redaction live test (1 ID-card + 1 passport fixture E2E redaction roundtrip) | nincs UI → live UI + 1 Playwright spec; PII gate verified |
| **SX-6** | Sprint X close — retro + tag `v1.8.0` + run_quality_baseline.sh PASS gate (mind 4 UC szilard) | DONE |

**Sprint X exit gate:** `bash scripts/run_quality_baseline.sh` minden 4 UC-re
target felett. Ha barmely UC alatti, a sprint NEM zarul.

### 3.2. Sprint Y — "UC2 RAG **depth push**" (Sprint X utan)

**Theme:** professzionalis chunkolas + vektor DB menedzsment.

| Session | Mit szallit | Merheto cel |
|---|---|---|
| SY-1 | Semantic chunker (heading-aware + table-preservation) + multilingual HU+EN ProviderRegistry slot | MRR@5 0.55 → ≥ 0.65 (Profile A BGE-M3) |
| SY-2 | Hybrid search (BM25 + vector RRF) + cross-encoder reranker production wiring | MRR@5 0.65 → ≥ 0.72 |
| SY-3 | Reembedding workflow (collection re-embed UI + worker) + collection split/merge/rename API + UI | nincs → live + 1 Playwright |
| SY-4 | Per-tenant izolacio E2E test + `aszf_rag_chat` Reflex ingest UI completion | gap → closed |
| SY-5 | Sprint Y close — tag `v1.9.0` + run_quality_baseline.sh PASS |

**Sprint Y exit gate:** UC2 MRR@5 ≥ 0.72 Profile A; collection management
Playwright PASS; aszf_rag_chat ingest UI mukodik.

### 3.3. Sprint Z — "Cross-cutting Phase 3 ops + audit" (KONDICIONAL)

**Csak akkor indul,** ha Sprint X+Y mind zold (4 UC szilardan a target felett).
Ekkor a `110_*` szabaly szerint a use-case "rides architecture" mintan az
infra-munka jogos.

Tartalom: OTel/Prometheus integration, Grafana cost panels (SN-FU-3),
audit lineage (Phase 3 N17/N18), coverage uplift 70→80% (SJ-FU-7), Vault
rotation E2E (SM-FU-1).

**Ha Sprint X+Y barmelyik UC nem ert celt:** Sprint Z elhalasztva, helyette
extension sprint az eltero UC-re.

---

## 4. Operacionalizalas — strukturalis vedvonalak

A Sprint M-W drift NEM az operator akarat eltevedeseből szuletett — a
folyamatban hianyoztak az ellenőrzo pontok. Ezek a sprint-tervezesi
folyamat strukturalis valtozasai, amik megakadalyozzak az ujboli driftet:

### 4.1. Uj session-prompt template — kotelezo Quality target fej

`session_prompts/_TEMPLATE.md` (uj, ebben a PR-ben) — minden NEXT.md eleje
KOTELEZO az alabbi szekciot tartalmazza:

```markdown
## Quality target (Sprint <X>)
- Use-case: <UC1 / UC2 / UC3 / DocRecognizer>
- Metric: <specific number, e.g. "UC1 invoice accuracy on 25-fixture corpus">
- Baseline (now): <current measurement, e.g. "85.7% on 10-fixture synthetic">
- Target (after this session): <desired number, e.g. "≥ 92% on 25-fixture mixed">
- Measurement command: <bash one-liner that produces the number>
```

Ha ez a fej hianyzik vagy nem merheto → a session NEM kezdodik. `/next`
skill update-jet (`./.claude/commands/next.md`) ellenorizze ezt a fejlecet.

### 4.2. ROADMAP.md aktivan fenntartott

`01_PLAN/ROADMAP.md` minden sprint-close-on KOTELEZO frissites alatt all.
A Sprint X tervezetben (`121_*`) explicit acceptance criteria:
"ROADMAP.md mondja a tenyleges shipped state-et + a kovetkező sprint-eket".

### 4.3. CLAUDE.md slim — sprint-trajectory kihúzva

A jelenlegi CLAUDE.md banner ~49 KB / 100+ sor sprint-trajectory recap-ot
tartalmazott, ami **maga is osztozott a drift-ben** — pszichológiailag
azt sugallta minden uj sprintnek, hogy "ennyit kell csinalni egy retro
banner-ben". Slim CLAUDE.md (~80 sor) + uj `docs/SPRINT_HISTORY.md` ahova
a regi banner archivalt formaban kerul.

A slim CLAUDE.md **csak**:
- Project overview (1 sor: jelen tag + 4 UC stat snapshot)
- Structure
- Key Numbers (snapshot)
- Build & Test
- Code Conventions
- Git Workflow
- Current Plan (3 sor, mutató 121_*-re)
- Session Workflow
- Slash Commands
- IMPORTANT
- References

### 4.4. run_quality_baseline.sh — egysegletes meres

`scripts/run_quality_baseline.sh` (uj, ebben a PR-ben) bash kompozit
script, ami a 4 UC-re mert vissza:
- UC1: `scripts/measure_uc1_golden_path.py --output json`
- UC2: `scripts/run_nightly_rag_metrics.py --output json`
- UC3: `scripts/measure_uc3_attachment_intent.py` (Sprint X SX-4 alatt
  átírva uniform `--output`-ra)
- DocRecognizer: `scripts/measure_doc_recognizer_accuracy.py --output json`

Output: aggregate JSON + ASCII tabla. Exit code 0 csak akkor, ha mind 4
UC a `--target` felett van (target a CLI flag-ben).

### 4.5. Sprint-close metric gate

`/session-close` skill update — minden sprint-utolso session zarasakor
fut a `run_quality_baseline.sh`. Ha az érintett UC szam **nem javult** a
sprint-baseline-hoz kepest, a close STOP-ol. A session-prompt-ban
megadott baseline + target szempar a `git diff session_prompts/` alapjan
deriválhato.

### 4.6. Carry-forward strict deferral

A Sprint W close otta nyitott follow-up-ok (SW-FU-1..5, SV-FU-2/5,
SS-SKIP-2, stb.) — Sprint X **nem foglalkozik veluk** kivéve, ha kozvetlenul
a 4 UC valamelyikene mélyíti. A `01_PLAN/ROADMAP.md` Cross-cutting
backlog szekcio explicitly listazza, hogy mi maradt halasztva, es miert.

Konkretan **NEM szallit** Sprint X:
- SW-FU-1 Langfuse v4 list-by-prefix SDK helper (SDK-fuggo, infra)
- SW-FU-2 admin UI source-toggle widget (kozvetve UI polish)
- SW-FU-3 audit script kiterjesztese masik tablakra (multi-tenant cleanup folytatas)
- SW-FU-4 Vault AppRole IaC E2E (infra, Sprint Z scope)
- SV-FU-2 UI bundle guardrail (CI polish)
- SV-FU-5 Monaco editor (UI nice-to-have)
- SJ-FU-7 coverage uplift (Sprint Z scope)
- SS-SKIP-2 Profile B Azure live (blocked: credit pending)
- SP-FU-3 thread-aware **EZT VISZONT IGEN — UC3 quality-deepening, SX-4 scope**
- SP-FU-1 `024_complaint` **EZT VISZONT IGEN — SX-4 scope**
- SQ-FU-3 UC1 corpus 25 fixture **EZT VISZONT IGEN — SX-2 scope**
- SW-FU-5 / SV-FU-1 DocRecognizer real-corpus **EZT VISZONT IGEN — SX-3 scope**

---

## 5. STOP feltetelek a folyamatra magara

A Sprint X-Y-Z kovetkezteti folyamatra **HARD STOP** az alabbiak:

1. **Sprint X SX-1 PR meg nem merged** → semmi sem indul a sprint X testebe.
2. **Sprint X-vegi quality baseline** barmelyik UC szam celja alatti → SX-6
   nem zarul, hanem extension-session indul (SX-7).
3. **CLAUDE.md / ROADMAP.md a sprint-close-on nem aktualis** → close STOP-ol.
4. **Olyan session indul, amiben a Quality target fej hianyzik vagy nem
   merheto** — `/next` skill blockol.

**SOFT STOP:**
- Ha SX-3 (DocRecognizer real-corpus) operator-driven anonimizacio nem
  keszul el, az SX-3 elhalasztva SX-7-re; a sprint nem all le, de a
  "DocRecognizer szilard" dimenzio nyitva marad.

---

## 6. Hivatkozasok

- `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` — az alapveto policy ("one use-case per sprint")
- `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` — explicit defer-szabaly
- `01_PLAN/ROADMAP.md` — aktualisitva ennek a PR-nek a kereteben
- `01_PLAN/121_SPRINT_X_QUALITY_PUSH_PLAN.md` — Sprint X kickoff terv
- `docs/SPRINT_HISTORY.md` — Sprint J–W trajectory recap (a regi CLAUDE.md banner)
- `scripts/run_quality_baseline.sh` — 4 UC merhetoseg bash kompozit
- `session_prompts/_TEMPLATE.md` — kotelezo session-prompt fejlec sablon
- `CLAUDE.md` — slim verzio, ~80 sor

---

## 7. Aláírás

Ez a doc a Sprint X kickoff aláírasa. Az operator es az ev jovobeli
session-jei ehhez a iranyhoz kotik magukat. Ha barki — operator vagy
session — ettol elter, a megsertes elobb a `docs/honest_alignment_audit.md`
update-jet **es** a 110_*-policy formal modositasat igenyli.
