# AIFlow v2 — Capacity Planning (Hardware + Cost Model)

> **Verzio:** 1.0 (FINAL — SIGNED OFF)
> **Datum:** 2026-04-09
> **Statusz:** ELFOGADVA (SIGNED OFF) — P1 hardening (`102_*` Section 3.8, SF2)
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
> **Rokon:** `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` (P1 parja)
> **Forras:** `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` Section 3.8 (Should fix SF2)

> **Cel:** A Phase 2 elotti **full operational readiness** kialakitasa: hardware profilok,
> benchmark target-ek, Profile A GPU-mentes maximum volumen, Profile A/B koltsegmodell.

---

## 0. Scope es megkozelites

Ez a dokumentum **NEM** uj implementacios terv, hanem **kapacitas + koltseg tervezo anyag**.
A celja, hogy:

1. A Phase 2 indulas elott a customer deployment keszultseget **hardware szinten** is tervezheto legyen
2. A Profile A (cloud-disallowed) + Profile B (cloud-allowed) koltsegmodell **transzparens** legyen
3. A benchmark target-ek explicit meghatarozottak legyenek a Phase 2 elfogadasi kriteriumokhoz
4. A customer hardware procurement **bizonytalansag nelkul** tervezheto legyen

**NEM** tartalmazza:
- Final benchmark eredmenyeket — azokat Phase 2c E2E mérés adja
- Konkret cloud szerzodest — az customer-specifikus
- K8s deployment manifestet — az a `62_DEPLOYMENT_ARCHITECTURE.md` dolga

---

## 1. Hardware profil kategoriak

### 1.1 Profile A GPU-mentes (CPU-only, on-prem)

**Cel-use-case:** Kizarolag text-only born-digital PDF + DOCX + XLSX feldolgozas.
Kis-kozepes volumen (napi < 500 dokumentum). NINCS VLM, NINCS self-hosted vision model.

| Komponens | Min spec | Ajanlott | Megjegyzes |
|-----------|---------|---------|------------|
| CPU | 8 vCPU | 16 vCPU | Docling parser CPU-intensive |
| RAM | 32 GB | 64 GB | PostgreSQL + Redis + Docling working set |
| SSD | 500 GB NVMe | 1 TB NVMe | data/uploads/ + postgres data + artifact |
| Network | 1 Gbps | 10 Gbps | local only, NINCS cloud |
| GPU | — | — | NINCS (fast path: PyMuPDF4LLM + Docling standard) |

**Deploy:** Docker Compose egyetlen host-on, vagy kis K8s cluster (1-2 node).

### 1.2 Profile A GPU-val (on-prem, teljes functionality)

**Cel-use-case:** Teljes szines (scan + handwriting + visual classifier + VLM parser + BGE-M3 embedding).
Kozepes-nagy volumen (napi 1000-5000 dokumentum). Profile A air-gapped.

| Komponens | Min spec | Ajanlott | Megjegyzes |
|-----------|---------|---------|------------|
| CPU | 16 vCPU | 32 vCPU | orchestration + non-VLM services |
| RAM | 64 GB | 128 GB | vLLM working set + BGE-M3 model + pg |
| SSD | 1 TB NVMe | 2 TB NVMe | artifacts + model cache |
| GPU | NVIDIA T4 (16GB) | NVIDIA A10 (24GB) | Qwen2.5-VL INT4 / FP16 + BGE-M3 + Docling VLM |
| Network | 1 Gbps | 10 Gbps | local only |

**GPU VRAM budget:**

| Modell | VRAM (FP16) | VRAM (INT4) | Ajanlott kontekszt |
|--------|------------|-------------|-------------------|
| Qwen2.5-VL-7B | ~14 GB | ~7 GB | page-level classification + boundary |
| BGE-M3 | ~2 GB | — | embedding (dense 1024) |
| Docling VLM | ~8-10 GB | — | hard-case parser |

**Deployment strategia:**
- **Single GPU (A10 24GB)**: Qwen2.5-VL INT4 (7GB) + BGE-M3 (2GB) + ~15GB free Docling VLM-re batch alapon
- **Dual GPU (2x T4 16GB)**: GPU0 = Qwen2.5-VL FP16 (14GB); GPU1 = BGE-M3 + Docling VLM

### 1.3 Profile B (cloud-allowed, Azure-optimized)

**Cel-use-case:** Azure-tenant customer, Azure DI + Azure OpenAI embedding, hybrid lehetoseg.

| Komponens | Min spec | Ajanlott | Megjegyzes |
|-----------|---------|---------|------------|
| CPU | 8 vCPU | 16 vCPU | orchestration csak, parser → Azure DI |
| RAM | 32 GB | 64 GB | kisebb szukseglet cloud parser miatt |
| SSD | 500 GB | 1 TB | tranziens artifacts |
| GPU | — | opcionalis | ha self-hosted BGE-M3 is, akkor T4 |
| Network | 10 Gbps (Azure tenant) | 10 Gbps | Azure DI / OpenAI API |

**Deployment strategia:**
- **Fully cloud**: minden parser + embedding cloud, on-prem minimalis (csak DB + orchestration)
- **Hybrid**: parser cloud (Azure DI), embedding self-hosted (BGE-M3 → T4 GPU szukseges)

---

## 2. Benchmark target matrix

### 2.1 Parser throughput

| Parser | Hardware | Document type | Throughput target | Latency target (p95) |
|--------|----------|--------------|------------------|---------------------|
| PyMuPDF4LLM | CPU (8 vCPU) | Born-digital PDF, 1-10 pages | **~20-30 docs/sec** | <500 ms/doc |
| PyMuPDF4LLM | CPU (8 vCPU) | Born-digital PDF, 50+ pages | **~2-5 docs/sec** | <5 s/doc |
| Docling standard | CPU (16 vCPU) | Mixed PDF/DOCX/XLSX | **~0.5-2 docs/sec** | <15 s/doc |
| Docling VLM | GPU (A10) | Scan PDF, handwriting | **~0.3-0.5 docs/sec** | <30 s/doc |
| Azure DI | Cloud | Scan + handwriting | **~0.5-1 docs/sec** | <20 s/doc |
| Qwen2.5-VL | GPU (A10) | Page-level classif. | **~3-5 pages/sec** | <3 s/page |

> **Note:** a fenti szamok iparagi viszonyitasok (`PyMuPDF4LLM 2024 benchmarks`, `Docling 2.0 paper`,
> `Azure DI Read model SLA`). Konkret Phase 2c E2E meres kotelezo, **ELFOGADHATO eltérés ±30%**.

### 2.2 Embedder throughput

| Embedder | Hardware | Chunk size | Throughput target | Cost/1M chunks |
|----------|----------|------------|-------------------|---------------|
| BGE-M3 (CPU) | 16 vCPU | 512 tokens | **~10-20 chunks/sec** | $0 (self-hosted) |
| BGE-M3 (GPU T4) | NVIDIA T4 | 512 tokens | **~100-200 chunks/sec** | $0 (self-hosted, GPU amort.) |
| BGE-M3 (GPU A10) | NVIDIA A10 | 512 tokens | **~300-500 chunks/sec** | $0 (self-hosted, GPU amort.) |
| e5-large | GPU T4 | 512 tokens | **~200-300 chunks/sec** | $0 |
| Azure OpenAI 3-small | Cloud API | 512 tokens | **~1000-2000 chunks/sec** | ~$0.02/1M tokens |
| Azure OpenAI 3-large | Cloud API | 512 tokens | **~500-1000 chunks/sec** | ~$0.13/1M tokens |

### 2.3 End-to-end pipeline target

| Pipeline | Profile | Target throughput | Target latency (p95) |
|---------|--------|-------------------|---------------------|
| invoice_finder | A CPU-only | 10 szamla/perc | <30s/szamla |
| invoice_finder | A GPU | 30 szamla/perc | <10s/szamla |
| invoice_finder | B (Azure DI) | 20 szamla/perc | <15s/szamla |
| advanced_rag_ingest | A CPU-only | 5 dok/perc | <60s/dok |
| advanced_rag_ingest | A GPU | 15 dok/perc | <20s/dok |
| advanced_rag_ingest | B (Azure OpenAI) | 25 dok/perc | <10s/dok |

---

## 3. Profile A GPU-mentes maximum volumen

Kritikus kerdes: HOL huzzuk meg a GPU-mentes deployment maximum volumenet?

### 3.1 Szamitas

**Feltevesek** (konzervativ):
- 8 vCPU, 64GB RAM
- Docling standard avg ~8 sec/dok (szmagyar PDF, 10 oldal)
- Background scheduler 30% CPU headroom
- 8 munkaoraban napi feldolgozas

**Napi max throughput:**
```
8 hour * 3600 sec/hour / 8 sec/doc = 3600 docs/8-hour-shift
```

**Konzervativ operation headroom (50%):**
```
3600 * 0.5 = 1800 docs/day maximum
```

**Ajanlott cap Profile A GPU-mentes deployment-re:**
- **Kis customer**: napi < 500 dokumentum → CPU-only OK
- **Kozepes customer**: napi 500-1800 dokumentum → CPU-only meg elfogadhato (de surveillance)
- **Nagy customer**: napi > 1800 dokumentum → **GPU KOTELEZO** (Qwen2.5-VL + Docling VLM)

### 3.2 Hogyan allitsuk be?

A `config/profiles/profile_a.yaml`-ben:

```yaml
policy:
  # Profile A default (CPU-only)
  docling_vlm_enabled: false
  qwen_vllm_enabled: false
  self_hosted_embedding_model: BAAI/bge-m3  # CPU lassabb, de mukodik
  daily_document_cap: 500  # soft warning threshold
  daily_document_hard_cap: 1800  # hard stop (DLQ)
```

Ha a customer GPU-val bovit, akkor `instances/{customer}/policy.yaml` felulirja:

```yaml
policy:
  docling_vlm_enabled: true
  qwen_vllm_enabled: true
  daily_document_cap: 5000
  daily_document_hard_cap: 15000
```

---

## 4. Koltsegmodell

### 4.1 Profile A (on-prem, CAPEX-drivoru)

**One-time costs**:

| Komponens | Min (Starter) | Ajanlott (Standard) | Max (Enterprise) |
|-----------|---------------|---------------------|-----------------|
| Server (CPU-only) | $3,000 | $5,000 | — |
| Server (GPU single A10) | — | $8,000-12,000 | $15,000 |
| Server (GPU dual A10) | — | — | $25,000-30,000 |
| Backup storage | $1,000 | $2,000 | $5,000 |
| Network infra | $500 | $1,500 | $5,000 |
| **Total CAPEX** | **~$4,500** | **~$12,500-20,000** | **~$50,000+** |

**Monthly OPEX**:
- Sajat datacenter: ~$200-500/month (energia + cooling + space)
- Private cloud: ~$500-2000/month (depends on vendor)

**Per-document cost (Starter, 500 docs/day)**:
```
CAPEX amortization (3 year) + OPEX ≈ $300/month
500 docs/day × 30 days = 15,000 docs/month
Cost per doc ≈ $300 / 15,000 = $0.02/doc
```

### 4.2 Profile B (cloud-allowed, OPEX-drivoru)

**Per-document cost (Azure-optimized)**:

| Komponens | Cost/doc | Megjegyzes |
|-----------|---------|-----------|
| Azure DI (Read) | $0.001-0.005 | per page |
| Azure DI (Layout) | $0.01-0.05 | per page |
| Azure OpenAI embedding (text-3-small) | $0.0001-0.001 | per doc (1000 token avg) |
| Azure OpenAI embedding (text-3-large) | $0.001-0.01 | per doc |
| Azure OpenAI GPT-4o-mini | $0.0003-0.003 | per doc (classification + extraction) |
| Azure OpenAI GPT-4o | $0.005-0.05 | per doc (hard cases) |

**Osszesen per document (tipikus invoice, 2-3 oldal)**:
```
Layout parser: $0.02-0.10
Embedding (2 chunks): $0.0002
Classifier (GPT-4o-mini): $0.001
Extraction (GPT-4o-mini): $0.003
-----------------------------------
Total: ~$0.03-0.15/doc
```

**Compare vs Profile A:**
- Profile A (amort): $0.02/doc
- Profile B (cloud): $0.03-0.15/doc
- **Break-even**: ~200-500 docs/day → ebove Profile A CAPEX cheaper

### 4.3 Cost cap policy (Profile B)

A `policy/cost_cap.yaml`:

```yaml
cost_cap:
  per_decision_cap_usd: 0.50      # single routing decision
  per_package_cap_usd: 5.00        # single package
  per_tenant_daily_cap_usd: 100.00 # tenant daily hard stop
  alert_threshold_pct: 80          # alert at 80% of daily cap
```

A `routing/cost_cap.py` (`103_*` Section 4.7) ezt a config-ot hasznalja.

---

## 5. Benchmark target — Phase 2 acceptance

A Phase 2c (`v1.5.2`) sprint **kotelezoen** futtat:

### 5.1 Parser benchmark

- **Dataset**: 100 HU invoice PDF (kulonbozo formatumok: digital/scan/mixed)
- **Metrics**: throughput (docs/sec), latency (p50/p95/p99), accuracy (vs ground truth), cost per doc
- **Acceptance**: mindegyik parser elerje a Section 2.1 target-ek ±30%-at

### 5.2 Embedder benchmark

- **Dataset**: 10,000 HU chunks (szerzodes, szamla, szabalyzat)
- **Metrics**: throughput, recall@10, nDCG@10, cost per 1M chunks
- **Acceptance**: BGE-M3 recall@10 >= 0.85; Azure OpenAI 3-small recall@10 >= 0.90

### 5.3 End-to-end pipeline

- **Dataset**: 1000 valos package (email + file + folder mix)
- **Metrics**: throughput (docs/min), total cost, HITL arány
- **Acceptance**: Profile A GPU >= 15 szamla/perc, Profile B >= 20 szamla/perc

---

## 6. Capacity monitoring

A Phase 3 `observability/prometheus_metrics.py` (`101_*` R9/N20) expose-olja:

```
aiflow_capacity_docs_per_day{tenant_id,profile}
aiflow_capacity_gpu_vram_used_gb{gpu_id}
aiflow_capacity_cpu_usage_pct{host}
aiflow_capacity_queue_depth{queue_name}
aiflow_cost_usd_total{tenant_id,provider}
```

Grafana dashboard (`infra/grafana/dashboards/capacity.json`) monitoring:
- Daily doc throughput vs cap
- GPU VRAM usage
- CPU / RAM saturation
- Queue depth (warning at 80% cap)
- Cost burn rate

---

## 7. Scale-out guidance

### 7.1 Horizontal scaling (when GPU-bound)

```
Single GPU (A10)   → 30-50 docs/min maximum
Dual GPU (2x T4)   → 60-100 docs/min
K8s GPU node pool (4x A10) → 120-200 docs/min
```

### 7.2 Horizontal scaling (when CPU-bound)

```
Worker replicas × parser throughput = total
4 workers × 20 docs/min (PyMuPDF4LLM) = 80 docs/min
```

A `WorkflowRunner` + `JobQueue` mar tamogatja a multi-worker deployment-et.

---

## 8. Risk items (capacity-related)

| # | Kockazat | Hatas | Mitigation |
|---|---------|-------|------------|
| C1 | Qwen2.5-VL GPU VRAM elegtelen single GPU (16GB T4) | Hard fail VLM path | INT4 quantization kotelezo T4-en |
| C2 | BGE-M3 CPU-only magyarra tul lassu | Ingest backlog | Phase 2c benchmark + GPU ajanlas |
| C3 | Azure DI cost explosion (Profile B) | Budget overflow | cost_cap policy (Section 4.3) |
| C4 | Profile A CPU-only > 1800 docs/day | Queue backlog, SLA breach | Hard cap + HITL overflow |
| C5 | vLLM restart recovery idotartam | Transient SLA breach | Graceful restart + healthcheck |

---

## 9. Sign-off checklist

- [ ] Hardware profilok szakmai review (architect + ops)
- [ ] Phase 2c benchmark teszt terv elfogadva
- [ ] Profile A GPU-mentes hard cap konfiguracio elfogadva
- [ ] Profile B cost cap policy elfogadva
- [ ] Customer hardware procurement template elkeszult
- [ ] Grafana capacity dashboard scaffolding kesz

---

## 10. Open items (Phase 2 elott kell dontes)

| # | Tema | Kerdes | Default |
|---|------|--------|--------|
| C-Q1 | GPU vs cloud trade-off (napi 500-2000 dok) | Melyik optimal? | Customer-spec, cost analysis |
| C-Q2 | Qwen2.5-VL INT4 vs FP16 | Vesztesseg vs VRAM? | Phase 2b valos meres |
| C-Q3 | Azure DI tier (Free vs S0) | Volume threshold? | >100 pages/month → S0 |
| C-Q4 | vLLM vs alternative (SGLang, LM Deploy) | Performance? | vLLM default, alt. Phase 3 review |

---

## 11. Hivatkozasok

- `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` Section 7 — Phase 2 ordering
- `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` N8/N9/N10/R5 — parser/embedder komponensek
- `103_AIFLOW_v2_FINAL_VALIDATION.md` Section 4.7 — cost-aware routing
- `62_DEPLOYMENT_ARCHITECTURE.md` — Docker compose + K8s overlay

---

> **Vegleges:** Ez a dokumentum lezarja a capacity + cost tervezes gap-et (P1 SF2). A Phase 2
> indulas (v1.5.0) elott ez a dokumentum **sign-off-olt kell legyen** az architect + ops altal.
> A `100_f_*` HITL Workload Model parja, egyutt adjak a full operational readiness-t.
