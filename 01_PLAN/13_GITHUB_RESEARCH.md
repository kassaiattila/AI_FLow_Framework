# AIFlow - GitHub Kutatasi Eredmenyek (Valos Kodanalzis)

3 framework forraskodjat klónoztuk es elemeztuk melyrehatoan.
Az alabbi tanulsagok a **tenyleges Python implementaciora** epulnek, nem marketing anyagokra.

---

## 1. LangGraph (27.7k stars, MIT)

**Repo:** github.com/langchain-ai/langgraph
**Fo fajl:** `libs/langgraph/langgraph/pregel/main.py` (149KB!)

### Amit Tanultunk a Valos Kodbol

**1.1 NEM DAG, hanem BSP (Bulk Synchronous Parallel)**

A LangGraph NEM hagyomanyos topologiai rendezest hasznal.
Ehelyett **channel-alapu trigger rendszert**:

```python
# Hogyan donti el melyik node fut kovetkezokent:
# 1. Melyik channel-ek frissultek az elozo lepesben?
# 2. Melyik node-ok figyelik ezeket a channel-eket? (trigger_to_nodes mapping)
# 3. Azok a node-ok futnak parhuzamosan
# 4. Kimenetuk atomikusan irodnak a channel-ekbe
# 5. Ismetles amig nincs tobb trigger
```

**Tanulsag az AIFlow szamara:** A mi DAG-alapu tervunk jol mukodik,
de erdemes a channel/trigger mintat is megfontolni a jovo bonyolultabb
workflow-jaihoz (parhuzamos elagazasok, map-reduce).

**1.2 Checkpoint Implementacio (Felbecsulhetetlen)**

```python
# LangGraph checkpoint struktura:
Checkpoint = {
    'v': 4,                          # Checkpoint format verzio
    'id': 'uuid6-timestamp-based',   # Egyedi ID
    'ts': '2026-03-28T10:00:00Z',    # Idopont
    'channel_values': {...},          # Teljes allapot
    'channel_versions': {...},        # Verzioszam per channel (CDC)
    'versions_seen': {...},           # Interrupt tracking
}
```

**Tanulsag:** A mi `step_runs.checkpoint_data` JSONB mezonk hasonlo,
de a `channel_versions` minta (Change Data Capture) hasznos lenne
a parhuzamos step-ek konzisztens kezelesere.

**1.3 Retry Policy (Kozvetlen felhasznalhato minta)**

```python
@dataclass
class RetryPolicy:
    predicate: Callable[[Exception], bool]  # Mikor probaljuk ujra
    max_attempts: int = 3
    initial_interval: float = 1.0           # Kezdo varakozas (mp)
    backoff_factor: float = 2.0             # Szorzo
    max_interval: float = 60.0             # Max varakozas
    jitter: bool = True                     # Random jitter
```

**Tanulsag:** Ez PONTOSAN az, amit az AIFlow `RetryPolicy`-nk tervez.
Validalas: a tervunk helyes, a LangGraph implementacio mintajaval egyezik.

**1.4 Send (Dinamikus Routing) - Uj Otlet**

```python
# Egy node tobb peldanyt indithat egy masik node-bol:
def route(state):
    return [Send("worker", {"doc": doc}) for doc in state["documents"]]
```

**Tanulsag:** Ez a map-reduce minta hasznos lenne az ASZF RAG skill-hez
(tobb chunk feldolgozasa parhuzamosan).

### Mit Hasznaljunk Kozvetlenul

| Minta | Alkalmazas AIFlow-ban |
|-------|----------------------|
| RetryPolicy dataclass | `src/aiflow/engine/policies.py` - szinte 1:1 atvettelel |
| Checkpoint struktura | `step_runs.checkpoint_data` sema bovitese version tracking-gel |
| Streaming modok | `WorkflowRunner` streaming output tamogatas |
| Send/map-reduce | `WorkflowBuilder.parallel_map()` uj metodus (v2-ben) |

---

## 2. CrewAI (47.4k stars, MIT)

**Repo:** github.com/crewAIInc/crewAI
**Fo fajl:** `lib/crewai/src/crewai/crew.py` (1700+ sor), `flow/flow.py` (2000+ sor)

### Amit Tanultunk a Valos Kodbol

**2.1 Flow System - Event-Driven Workflow Engine**

```python
class MyFlow(Flow[MyState]):
    @start()
    def begin(self):
        return self.state.input

    @listen(begin)                    # Triggerelodik ha begin() befejezodik
    def process(self, result):
        return self.llm.call(result)

    @router(process)                  # Routing a process() eredmenye alapjan
    def route(self, result):
        if result.score > 0.8:
            return "approve"          # String routing constant
        return "review"

    @listen("approve")                # Triggerelodik ha route() "approve"-t ad
    def approve(self):
        ...

    @listen("review")
    def review(self):
        ...
```

**Tanulsag:** A `@start`, `@listen`, `@router` decorator minta
elegansabb mint a mi `WorkflowBuilder.step()` + `branch()` megkozelitesunk.
De kevesbe explicit (nehezebb a DAG-ot vizualizalni).
**Megtartjuk a sajat explicit builder API-nkat**, de erdemes egy
alternatíiv decorator-alapu API-t is kinalní elore haladott fejlesztoknek.

**2.2 Agent Guardrail (Minosegi Ellenorzes)**

```python
class Agent:
    guardrail: Callable | None = None
    # guardrail fuggveny: (output) -> (bool, str)
    # True = elfogadva, False = ujraprobalas feedback-kel
```

**Tanulsag:** Hasonlo a mi QualityGate mintankhoz, de egyszerubb.
A mi score-alapu megkozelitesunk gazdagabb (0.0-1.0 score, tobb metrika).

**2.3 Memory System (Kifinomult)**

```python
class Memory:
    # Kompozit scoring:
    recency_weight: float = 0.3      # Mennyire friss
    semantic_weight: float = 0.5     # Mennyire relevans
    importance_weight: float = 0.2   # Mennyire fontos

    # Automatikus konszolidacio:
    consolidation_threshold: float = 0.85  # Hasonlo emlekek osszevonasa
```

**Tanulsag:** Az ASZF RAG skill-hez ez a memory system hasznos lenne
a multi-turn konverzaciokhoz. A mi tervunkben ez meg nincs reszletezve.
**Boviteni kell** a `skills/aszf_rag_chat/` tervet memory kezeleseel.

**2.4 Skill System (YAML Frontmatter)**

```python
# CrewAI skill-ek SKILL.md fajlban tarolodnak:
# ---
# name: Research Tool
# description: Searches the web
# parameters:
#   - name: query
#     type: string
# ---
# Detailed skill instructions here...
```

**Tanulsag:** A mi `skill.yaml` manifest megkozelitesunk robusztusabb
(kulon fajl, strukturalt YAML, Pydantic validacio). A CrewAI megoldas
egyszerubb de kevesbe validalhato.

### Mit Hasznaljunk Kozvetlenul

| Minta | Alkalmazas AIFlow-ban |
|-------|----------------------|
| Flow @start/@listen/@router | Alternativ decorator API fejlett felhasznaloknak (v2) |
| Memory composite scoring | ASZF RAG skill multi-turn memory |
| Agent guardrail pattern | QualityGate egyszerusitett valtozata egyszeru skill-ekhez |
| Event bus | `src/aiflow/core/events.py` - uj modul globalis esemenyekhez |
| Tool usage tracking | `max_usage_count` per tool - koltseg kontroll |

---

## 3. Haystack (24.6k stars, Apache 2.0)

**Repo:** github.com/deepset-ai/haystack
**Fo fajl:** `haystack/core/pipeline/base.py` (1762 sor), `core/component/component.py` (700+ sor)

### Amit Tanultunk a Valos Kodbol

**3.1 Component System (@component Decorator)**

```python
@component
class MyRetriever:
    def __init__(self, document_store, top_k: int = 10):
        self.document_store = document_store
        self.top_k = top_k

    @component.output_types(documents=list[Document])
    def run(self, query: str, filters: dict | None = None) -> dict[str, list[Document]]:
        docs = self.document_store.search(query, top_k=self.top_k)
        return {"documents": docs}
```

**Tanulsag:** A `@component.output_types()` decorator minta NAGYON hasznos!
A mi `@step` decorator-unk hasonlo, de a Haystack megkozelites
explicit output tipusokat deklaral a `run()` metodus felett.
**Adoptalni kell** ezt a mintat: a step output tipusok legyenek
a decorator-ban deklaralva, ne csak a return type hint-ben.

**3.2 Socket-Based Connection System**

```python
class InputSocket:
    name: str
    type: type
    default_value: Any
    is_lazy_variadic: bool    # Var az osszes sender-re
    is_greedy: bool           # Fut az elso input-ra
    senders: list[str]

class OutputSocket:
    name: str
    type: type
    receivers: list[str]
```

**Tanulsag:** A socket rendszer elegansabb tipusellenorzest tesz lehetove
a pipeline epiteskor. A mi rendszerunkben a `StepInput`/`StepOutput`
Pydantic modellek hasonlo szerepet toltenek be, de a Haystack socket
rendszere finomabb granularitast ad (per-mezo tipusellenorzes).

**3.3 Priority Queue Execution**

```python
class ComponentPriority(IntEnum):
    HIGHEST = 1    # Azonnali vegrehajtast igenyel
    READY = 2      # Minden input elerheto
    DEFER = 3      # Variadic inputok fuggoben
    BLOCKED = 5    # Hianyzó kotelezo inputok
```

**Tanulsag:** A mi WorkflowRunner-unk topologiai rendezest hasznal.
A Haystack priority queue megkozelitese rugalmasabb (kulonosen
variadic inputoknal es parhuzamos vegrehajtasnal).
**Megfontalando** a priority queue beepitese a WorkflowRunner-be.

**3.4 Pipeline Szerializacio (YAML)**

```yaml
# Haystack pipeline YAML:
components:
  retriever:
    type: haystack.components.retrievers.InMemoryEmbeddingRetriever
    init_parameters:
      document_store: my_store
      top_k: 10
  generator:
    type: haystack.components.generators.openai.OpenAIChatGenerator
    init_parameters:
      model: gpt-4o

connections:
  - sender: retriever.documents
    receiver: generator.documents
```

**Tanulsag:** A pipeline YAML szerializacio lehetove teszi a
workflow-k menteset es betolteset config fajlbol. Ez hasznos lenne
az AIFlow-ban: `aiflow workflow export --name process-doc --format yaml`
es `aiflow workflow import pipeline.yaml`.

**3.5 Variadic Inputok (Lazy vs Greedy)**

```python
# Lazy variadic: var az OSSZES sender-re
@component
class DocumentJoiner:
    @component.output_types(documents=list[Document])
    def run(self, documents: Variadic[list[Document]]):
        # documents = [[docs_from_retriever1], [docs_from_retriever2], ...]
        return {"documents": [d for docs in documents for d in docs]}

# Greedy variadic: fut BARMELYIK sender eredmenyere
@component
class StreamProcessor:
    @component.output_types(result=str)
    def run(self, chunks: GreedyVariadic[str]):
        # Fut amint barmelyik chunk megjon
        ...
```

**Tanulsag:** A `Variadic` es `GreedyVariadic` tipusok NAGYON hasznosak
lennenek az AIFlow-ban a parhuzamos step-ek eredmenyeinek osszegyujtesere.
Peldaul a `join()` muveletnk a WorkflowBuilder-ben hasonlo, de
a Haystack tipusrendszere gazdagabb.

**3.6 Breakpoints (Debug)**

```python
class PipelineSnapshot:
    pipeline_state: dict      # Inputok es component visit szamlalok
    break_point: Breakpoint   # Hol allt meg
```

**Tanulsag:** A `breakpoint` minta hasznos debugging-hoz.
Az AIFlow-ban a mi checkpoint rendszerunk hasonlo, de
explicit debug breakpoint tamogatas (pl. "allj meg az extract lepes elott")
hasznos lenne.

### Mit Hasznaljunk Kozvetlenul

| Minta | Alkalmazas AIFlow-ban |
|-------|----------------------|
| @component.output_types() | `@step` decorator bovitese explicit output tipus deklaracioval |
| Socket tipusellenorzes | Step I/O validacio pipeline epiteskor (nem csak futaskor) |
| Variadic/GreedyVariadic | WorkflowBuilder.join() tipusrendszer gazdagitasa |
| Pipeline YAML serialize | `aiflow workflow export/import` (uj CLI parancs) |
| ComponentPriority queue | WorkflowRunner alternativ ütemezo (v2-ben) |
| Breakpoint/Snapshot | Debug breakpoint tamogatas (`aiflow workflow debug`) |
| Component registry | `component.registry` minta a skill component-ekhez |

---

## 4. Szintezis: Mit Adoptlunk az AIFlow-ba

### 4.1 Azonnali Adoptalas (Phase 1-3)

| Framework | Minta | AIFlow Fajl | Prioritas |
|-----------|-------|-------------|-----------|
| LangGraph | RetryPolicy dataclass | engine/policies.py | KRITIKUS |
| LangGraph | Checkpoint version tracking | state/models.py | MAGAS |
| Haystack | @component.output_types() | engine/step.py | MAGAS |
| Haystack | Pipeline YAML serialize | engine/workflow.py | KOZEPES |
| CrewAI | Event bus | core/events.py | KOZEPES |

### 4.2 Kesobb Adoptalas (Phase 4-7)

| Framework | Minta | AIFlow Fajl | Prioritas |
|-----------|-------|-------------|-----------|
| LangGraph | Send/map-reduce | engine/dag.py | KOZEPES |
| CrewAI | Memory composite scoring | Skill-szintu | KOZEPES |
| Haystack | Variadic inputok | engine/step.py | ALACSONY |
| Haystack | Debug breakpoints | engine/runner.py | ALACSONY |
| CrewAI | Flow decorator API | engine/decorators.py | ALACSONY |

### 4.3 Amit NEM Adoptlunk

| Framework | Minta | Miert nem |
|-----------|-------|-----------|
| LangGraph | BSP execution model | Tulkomplex a mi celjainkhoz, DAG eleg |
| LangGraph | Channel-alapu state | Nehezebb debugolni mint explicit state |
| CrewAI | YAML agent config | Mi Python-first vagyunk, nem YAML-first |
| CrewAI | Role-playing agents | Technikai workflow-khoz nem passzol |
| Haystack | NetworkX fuggoseg | Sajat DAG implementacio konnnyebb es kisebb |

---

## 5. Tervmodosiasok a Kutatas Alapjan

A kovetkezo tervdokumentumokat kell frissiteni:

### 5.1 `01_ARCHITECTURE.md` bovitesek:
- Step decorator: `@step` kap `output_types` parametert (Haystack minta)
- Uj szekico: Event Bus (CrewAI minta) - globalis esemenyek
- Checkpoint bovites: version tracking (LangGraph minta)
- Uj szekico: Pipeline serialization (YAML export/import)

### 5.2 `02_DIRECTORY_STRUCTURE.md` bovitesek:
- `src/aiflow/core/events.py` - Event bus
- `src/aiflow/engine/serialization.py` - Workflow YAML export/import

### 5.3 `04_IMPLEMENTATION_PHASES.md` bovitesek:
- Phase 2 (Engine): output_types dekorator hozzaadasa
- Phase 3 (Agents): Event bus implementacio
- Phase 6 (CLI): `aiflow workflow export/import` parancsok

### 5.4 `11_REAL_WORLD_SKILLS_WALKTHROUGH.md` bovitesek:
- ASZF RAG Skill: Memory system hozzaadasa (CrewAI minta)
