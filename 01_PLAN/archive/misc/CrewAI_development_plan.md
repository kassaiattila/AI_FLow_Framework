### 21. Opcionális agentikus reasoning réteg

**Rögzített opcionális technológiai irány:**

- `CrewAI`
- elsődlegesen:
  - `Flows`
  - `Crews`
  - `Tasks`
  - `Tools`
  - opcionálisan `Knowledge`
- strukturált outputtal:
  - `output_json`
  - `output_pydantic`

**Elvárt szerep:**
A CrewAI NEM a teljes dokumentumfeldolgozó platform elsődleges core orchestrátora.
A CrewAI opcionális, bounded agentikus rétegként használható olyan feladatokra, ahol:

- többértelmű intake package értelmezés szükséges
- file-to-description association szükséges
- package-level context interpretation szükséges
- cross-document reasoning szükséges
- low-confidence triage és review-előkészítés szükséges
- operator / reviewer copilot funkció szükséges

**Kifejezetten ajánlott használati területek:**

- intake package interpretation
- source text és fájlok közötti kapcsolat értelmezése
- bizonytalan association esetek kezelése
- cross-document consistency reasoning
- manual review előkészítés
- review summary és recommendation generálás

**Nem elvárt szerep:**
A CrewAI-t ne használd elsődleges végrehajtási motorként az alábbiakra:

- parser provider routing core
- archival conversion core
- PDF/A validation
- policy enforcement core
- tenant boundary enforcement
- storage / metadata DB tranzakciós írás
- idempotens állapotkezelés fő megvalósítása
- compliance-kritikus state transitionök

**Elvárt architekturális pozíció:**

- külön agent service vagy külön bounded module
- provider-szerű adapteren keresztül meghívható
- a fő pipeline happy path-je CrewAI nélkül is működőképes maradjon
- a CrewAI enhancement / reasoning sidecar / exception handling layer legyen

**Elvárt CrewAI komponenshasználat:**

- `Flows`: stateful, event-driven agentikus alfolyamatokhoz
- `Crews`: több szerepre bontott együttműködő agentekhez
- `Tasks`: explicit feladatdefinícióhoz
- `Tools`: kontrollált belső szolgáltatáshívásokhoz
- `output_pydantic` vagy `output_json`: kötelező strukturált kimenethez
- `Knowledge`: csak akkor, ha az összhangban van a meglévő retrieval stratégiával

**Fontos megkötés a Knowledge használatához:**
A CrewAI built-in Knowledge / RAG capability nem válthatja le automatikusan a rögzített

- `PostgreSQL + pgvector`
- vagy `Azure AI Search`
  alapú retrieval / vector architektúrát.
  Ha CrewAI Knowledge használat felmerül, azt csak kiegészítő, adapterezett módon értékeld.

**Elvárt input a CrewAI agentikus alfolyamatokhoz:**

- normalizált intake package
- file lista
- source text lista
- parser / classifier summary-k
- extraction summary-k
- confidence értékek
- tenant policy snapshot
- allowed provider lista
- releváns provenance adatok

**Elvárt output a CrewAI alfolyamatokból:**
mindig strukturált, validálható formában:

- association result
- package interpretation result
- review triage result
- cross-document consistency result
- recommendation summary
- manual review flag
- rationale / evidence summary

**Kötelező szabály:**
A CrewAI outputot mindig validálni kell:

- schema validation
- confidence threshold check
- business rule validation
- policy validation

**Ha a CrewAI output érvénytelen vagy bizonytalan:**

- retry
- fallback
- vagy manual review ág aktiválódjon

**Gap elemzésben külön vizsgálandó pontok:**

- kell-e külön CrewAI agent service boundary
- mely use case-eknél indokolt a CrewAI
- mely use case-eknél nem indokolt
- hogyan illeszthető a meglévő queue-driven és policy-driven architektúrába
- hogyan tartható determinisztikus a fő pipeline CrewAI jelenléte mellett
- hogyan biztosítható az auditálható structured input/output contract



Additional requirement regarding CrewAI:
If CrewAI is included in the refined target architecture, evaluate it only as an optional bounded agentic reasoning layer.
Do not reposition it as the default core orchestrator of the whole platform.
Explicitly define:

- where CrewAI adds value
- where it must not be used
- what structured input/output contracts it must follow
- how it integrates with policy, review, audit, and fallback mechanisms
- how it remains compatible with the single shared codebase and the fixed technology direction
