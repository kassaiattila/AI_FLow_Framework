# AIFlow - ML Modell Integracio

## Fo Dontes: `src/aiflow/llm/` -> `src/aiflow/models/`

Az AIFlow jelenleg LLM-only. Vallalati automatizaciohoz kell:
- **Embedding** modellek (RAG-hoz)
- **Classification** modellek (fine-tuned BERT, routing)
- **Extraction** modellek (NER, szerzodesek)
- **Vision** modellek (szamla OCR, dokumentum layout)
- **Custom** modellek (sklearn, domain-specifikus)

---

## Architektura

```
ModelClient (DI injected faceede)
    |
    +-- generate()    -> TextGenerationProtocol  (LLM chat/completion)
    +-- embed()       -> EmbeddingProtocol       (text -> vector)
    +-- classify()    -> ClassificationProtocol  (text -> label)
    +-- extract()     -> ExtractionProtocol      (document -> entities)
    +-- analyze_image() -> VisionProtocol        (image -> text/structured)
    +-- predict()     -> CustomModelProtocol     (any -> any)
    |
    v
ModelRouter (cost/capability/latency routing + fallback chain)
    |
    v
ModelBackend (adapter pattern, mint MessageBroker)
    +-- LiteLLMBackend      (LLM + embedding, 100+ provider)
    +-- LocalModelBackend   (transformers, sklearn, in-process)
    +-- ServerBackend       (Triton, TorchServe, vLLM, HTTP/gRPC)
    +-- SidecarBackend      (Docker container, HTTP)
```

---

## Tipusos Protokollok (NEM egyseges interface!)

**Miert kulon protokollok?** Tipusbztonsag! Az embedding list[float]-ot ad,
a classification str label-t, a vision bytes-ot vesz. Egyseges `model.call()`
elveszitene minden Pydantic tipusellenorzest.

### Pelda: Embedding

```python
class EmbeddingInput(BaseModel):
    texts: list[str]
    model: str | None = None

class EmbeddingOutput(BaseModel):
    embeddings: list[list[float]]
    dimensions: int
    total_tokens: int = 0

class EmbeddingProtocol(BaseModelProtocol):
    async def embed(self, input_data: EmbeddingInput, ctx: ExecutionContext
    ) -> ModelCallResult[EmbeddingOutput]: ...
```

### Pelda: Classification

```python
class ClassificationInput(BaseModel):
    text: str
    labels: list[str] | None = None   # Zero-shot: jelolt cimkek
    multi_label: bool = False

class ClassificationOutput(BaseModel):
    results: list[ClassificationResult]  # label + confidence + all_scores
```

---

## Model Registry (DB-backed)

```sql
CREATE TABLE model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,      -- "openai/gpt-4o", "local/bert-ner-hu-v2"
    model_type VARCHAR(50) NOT NULL,        -- llm, embedding, classification, extraction, vision
    provider VARCHAR(100) NOT NULL,
    version VARCHAR(100) NOT NULL,
    lifecycle VARCHAR(50) DEFAULT 'registered',  -- registered->tested->staging->production->deprecated
    serving_mode VARCHAR(50) NOT NULL,      -- api, local, server, sidecar
    endpoint_url TEXT,
    model_path TEXT,
    capabilities JSONB DEFAULT '[]',
    pricing_model VARCHAR(50) DEFAULT 'per_token',  -- per_token, per_request, per_second, free
    cost_per_input_token DECIMAL(12,8) DEFAULT 0,
    cost_per_output_token DECIMAL(12,8) DEFAULT 0,
    cost_per_request DECIMAL(10,6) DEFAULT 0,
    priority INT DEFAULT 100,               -- Routing: alacsonyabb = preferalt
    fallback_model VARCHAR(255),
    avg_latency_ms FLOAT,
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Model Routing

```python
class RoutingStrategy(str, Enum):
    COST_OPTIMIZED = "cost_optimized"        # Legolcsobb eloszor
    LATENCY_OPTIMIZED = "latency_optimized"  # Leggyorsabb eloszor
    CAPABILITY_MATCH = "capability_match"    # Legjobb kepesseg-talalat
    FALLBACK_CHAIN = "fallback_chain"        # Prioritas sorrendben probal

# aiflow.yaml-ban konfiguralhato:
models:
  routing:
    - name: "hungarian-classifier"
      model_type: classification
      strategy: capability_match
      conditions: {language: "hu"}
      candidates: ["local/bert-hu-classifier", "openai/gpt-4o-mini"]
      fallback: "openai/gpt-4o-mini"
```

---

## Skill Manifest Bovites

```yaml
# skill.yaml - kibovitett required_models
required_models:
  - name: "openai/gpt-4o"
    type: llm
    usage: "Valasz generalas"
  - name: "openai/text-embedding-3-small"
    type: embedding
    usage: "Dokumentum embedding"
  - name: "local/bert-ner-hu-v1"
    type: extraction
    usage: "Magyar NER"
    optional: true
    fallback: "openai/gpt-4o"    # LLM-re fallback ha nincs NER modell
```

---

## Fine-Tuning Integracio

```python
class FineTuneManager:
    async def collect_training_data(self, workflow_name, step_name,
                                     min_quality_score=0.8, limit=1000) -> list[dict]:
        """Gyujt input/output parokat sikeres workflow futatasokbol."""

    async def create_finetune_job(self, base_model, training_data, provider="openai") -> str:
        """Indit fine-tuning job-ot (OpenAI, HuggingFace, lokal)."""

    async def start_ab_test(self, base_model, finetuned_model,
                            traffic_split={"base": 0.9, "finetuned": 0.1}) -> str:
        """A/B teszt fine-tuned vs alap modell."""
```

---

## LLM Provider Failover Protokoll

### Detektalas

| Trigger | Eszleles | Valasz |
|---------|----------|--------|
| HTTP 500/502/503 | Azonnali | Retry (max 2x), majd failover |
| HTTP 429 (rate limit) | Azonnali | Backoff, majd failover |
| Timeout (>30s) | 30s utan | Failover |
| Ismetlodo hiba (5x/perc) | Circuit breaker | Osszes hivas failover |

### Failover Chain Pelda

```yaml
# Generacio (LLM)
primary: openai/gpt-4o
fallback_1: anthropic/claude-sonnet-4-20250514
fallback_2: openai/gpt-4o-mini  # Degraded quality, lower cost

# Embedding
primary: openai/text-embedding-3-small
fallback_1: openai/text-embedding-3-large  # Costlier but available
# NINCS lokalis fallback - embedding modell nem cserelheto (dimenzio!)
```

### Circuit Breaker Allapotok (Redis-ben tarolva)

- CLOSED (normal): Minden hivas a primary-ra megy
- OPEN (5 hiba/perc utan): Minden hivas a fallback-re megy, 60s recovery
- HALF-OPEN (60s utan): 3 teszt hivas a primary-ra, ha OK -> CLOSED

### Koltseg Hatas

| Szcenario | Koltseg valtozas |
|-----------|-----------------|
| GPT-4o -> Claude Sonnet | ~1.5x dragabb |
| GPT-4o -> GPT-4o-mini | ~10x olcsobb, de minoseg csokken |

### Failover Teszteles

- Negyedevente: Chaos engineering (primary provider blokkolasa 1 orara)
- CI-ban: Mock failover teszt (circuit breaker mukodik-e)

---

## Konyvtar Struktura

```
src/aiflow/models/                    # LECSERELI src/aiflow/llm/-t
    __init__.py
    registry.py                       # ModelRegistry (DB-backed, lifecycle)
    metadata.py                       # ModelMetadata, ModelType, ModelLifecycle enum-ok
    client.py                         # ModelClient facade (generate, embed, classify, extract, vision)
    router.py                         # ModelRouter (cost/capability/fallback routing)
    cost.py                           # ModelCostCalculator
    protocols/
        base.py                       # BaseModelProtocol, ModelCallResult
        generation.py                 # TextGenerationProtocol (LLM)
        embedding.py                  # EmbeddingProtocol
        classification.py             # ClassificationProtocol
        extraction.py                 # ExtractionProtocol (NER)
        vision.py                     # VisionProtocol (OCR)
        custom.py                     # CustomModelProtocol
    backends/
        base.py                       # ModelBackend ABC
        litellm_backend.py            # LiteLLM (LLM + embedding, default)
        local_backend.py              # In-process (transformers, sklearn)
        server_backend.py             # Triton, TorchServe, vLLM
        sidecar_backend.py            # Docker container HTTP
    finetuning/
        manager.py                    # FineTuneManager
        data_collector.py             # Training data gyujtes workflow output-okbol
        ab_testing.py                 # A/B teszt fine-tuned vs base
```

## Backward Kompatibilitas

```python
# src/aiflow/models/client.py
LLMClient = ModelClient  # Alias - meglevo kod valtozatlanul mukodik
# model_client.generate() == llm_client.generate() - ugyanaz
```

## Implementacios Fazisok

| Fazis | Tartalom |
|-------|----------|
| Phase 2A (4-5 het) | ModelMetadata, ModelRegistry, TextGenerationProtocol, LiteLLMBackend |
| Phase 3A (8 het) | EmbeddingProtocol (RAG-hoz), cost_records bovites |
| Phase 4A (11 het) | ClassificationProtocol, ExtractionProtocol, LocalModelBackend |
| Phase 5A (14 het) | ModelRouter, ServerBackend (Triton/vLLM) |
| Phase 7A (20 het) | VisionProtocol, FineTuneManager, SidecarBackend |
