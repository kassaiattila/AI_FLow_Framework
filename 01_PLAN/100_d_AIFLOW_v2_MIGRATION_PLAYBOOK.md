# AIFlow v2 — Migration Playbook (Backward Compatibility)

> **Verzio:** 2.0 (FINAL — SIGNED OFF)
> **Datum:** 2026-04-09
> **Statusz:** ELFOGADVA (SIGNED OFF) — `103_*` 2. ciklus + `105_*` P0-P4 hardening utan
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md` (kezdd itt az olvasast!)
> **Szulo:** `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md`
> **Rokon:** `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md`, `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md`
> **Forras:** `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` Section 3.3 (Must fix)
>
> **Valtozas naplo:**
> - **v2.0 (2026-04-09):** Status "AKTIV" → "ELFOGADVA (SIGNED OFF)". Section 12 (Rollback
>   Decision Matrix) P2 hardening alatt hozzaadva (`105_*` Section 3). Sign-off `103_*`
>   + `105_*` utan.
> - **v1.0 (2026-04-08):** Initial draft, backward compat + rolling deploy + customer migration.

> **Cel:** A meglevo customer deployments es pipeline-ok zero-downtime migracioja
> a v1.4.0 (Phase 1) refinement-re. Backward compat shim layer, dual-write,
> rolling deploy, schema evolution, rollback path.

---

## 0. Migracios elvek

1. **Zero downtime** — production rendszer NEM all le
2. **Backward compat shim layer** — meglevo pipeline YAML-ok mukodnek modositas nelkul
3. **Dual-write** — atmeneti ido (1 sprint) ket schema egyutteles
4. **Feature flag** — uj funkciok opt-in, default-disabled
5. **Rollback ready** — minden migration rollback script-tel
6. **Test before prod** — staging environment elotti tesztelés
7. **Customer notification** — minden customer megkapja a migracios tervet 1 sprint elotti

---

## 1. Forditasi tabla — Mit valt ki mit

| Komponens | v1.3.0 (jelenlegi) | v1.4.0 (Phase 1) | Backward compat |
|-----------|-------------------|------------------|------------------|
| Pipeline YAML | `email_adapter` direkt | `intake_normalize` → `email_source` | Adapter shim |
| `services/email_connector` | direkt API | low-level fetcher (R1) | Marad valtozatlanul |
| `services/document_extractor.extract(file)` | single-file | `extract_from_package(package)` | Single-file shim wrapper |
| `services/rag_engine` `text-embedding-3-small` | hardcoded | `embedder=` parameter (R5) | Default `text-embedding-3-small` |
| `instances/{customer}/instance.yaml` | nincs policy | `policy.yaml` opcionalis | Default a profile_b-bol |
| `tools/azure_doc_intelligence.py` direkt | hardcoded fallback | provider registry (R3) | Direkt hivasok marad fallback layer-en at |
| `attachment_processor.py` 3-retegu | hardcoded | routing engine adapter (K3) | Direkt hivasok mukodnek |
| Adapter `__init__` | service-specific | provider parameter (R15) | Default factory |

---

## 2. DB Schema Migration Sorrend

A v1.4.0 ujabb migracios files-okat hoz be (alembic 030+). A sorrend kotelezo:

| # | Migration | Tartalom | Rollback |
|---|-----------|---------|---------|
| 030 | `intake_packages` tabla | IntakePackage CRUD | DROP TABLE |
| 030 | `intake_files` tabla | IntakeFile CRUD | DROP TABLE |
| 030 | `intake_descriptions` tabla | IntakeDescription CRUD | DROP TABLE |
| 030 | `package_associations` tabla | File ↔ description map | DROP TABLE |
| 031 | `policy_overrides` tabla | Per-instance policy override | DROP TABLE |
| 032 | `routing_decisions` tabla | RoutingDecision audit | DROP TABLE |
| 033 | `extraction_results` kibovites | `package_id`, `field_confidences`, `routing_decision_id` mezok hozzaadasa | ALTER TABLE DROP COLUMN |
| 034 | `archival_artifacts` tabla | ArchivalArtifact (Phase 2) | DROP TABLE |
| 034 | `validation_results` tabla | veraPDF (Phase 2) | DROP TABLE |
| 035 | `lineage_events` tabla | LineageRecord (Phase 3) | DROP TABLE |
| 035 | `provenance_links` tabla | ProvenanceMap (Phase 3) | DROP TABLE |
| 036 | `embedding_decisions` tabla | EmbeddingDecision audit (Phase 2) | DROP TABLE |

### 2.1 ExtractionResult tabla kibovites peldaja (alembic 033)

```python
"""033_add_intake_package_to_extractions

Revision ID: 0d3a4b5c6e7f
Revises: 029_session_recall
Create Date: 2026-04-15 ...
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0d3a4b5c6e7f"
down_revision = "029_session_recall"


def upgrade() -> None:
    # NOTE: nullable=True for backward compat — existing rows have no package_id
    op.add_column("extraction_results", sa.Column("package_id", postgresql.UUID(), nullable=True))
    op.add_column(
        "extraction_results",
        sa.Column("field_confidences", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "extraction_results",
        sa.Column("routing_decision_id", postgresql.UUID(), nullable=True),
    )
    op.add_column(
        "extraction_results",
        sa.Column("cross_document_signals", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "extraction_results",
        sa.Column("free_text_extractions", postgresql.JSONB(), nullable=True),
    )
    # FK constraint
    op.create_foreign_key(
        "fk_extraction_results_package",
        "extraction_results",
        "intake_packages",
        ["package_id"],
        ["package_id"],
        ondelete="SET NULL",
    )
    # Index
    op.create_index(
        "idx_extraction_results_package_id",
        "extraction_results",
        ["package_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_extraction_results_package_id", table_name="extraction_results")
    op.drop_constraint("fk_extraction_results_package", "extraction_results", type_="foreignkey")
    op.drop_column("extraction_results", "free_text_extractions")
    op.drop_column("extraction_results", "cross_document_signals")
    op.drop_column("extraction_results", "routing_decision_id")
    op.drop_column("extraction_results", "field_confidences")
    op.drop_column("extraction_results", "package_id")
```

### 2.2 Migracios sorrend dependency

```
029 (jelenlegi) → 030 (intake) → 031 (policy_overrides) → 032 (routing_decisions) → 033 (extraction kibov.)
                                                                                     ↓
                                                                                    034 (archival)
                                                                                     ↓
                                                                                    035 (lineage + provenance)
                                                                                     ↓
                                                                                    036 (embedding decisions)
```

### 2.3 Migrations futtatasa

```bash
# Pre-migration backup
pg_dump -U aiflow -d aiflow > backup_pre_v1.4.0.sql

# Apply migrations
alembic upgrade head

# Verify
alembic current  # should be 036_xxx

# Rollback (ha kell)
alembic downgrade 029  # vagy specific revision
```

---

## 3. Pipeline YAML Backward Compatibility

### 3.1 v1.3.0 pipeline (jelenlegi)

```yaml
# pipeline/builtin_templates/invoice_automation_v2.yaml
name: invoice_automation_v2
steps:
  - name: fetch_emails
    adapter: email_adapter
    method: fetch_emails
    config:
      connector_id: outlook_main
      days: 1

  - name: extract_invoices
    adapter: document_adapter
    method: extract
    depends_on: [fetch_emails]
    for_each: "{{ fetch_emails.output.attachments }}"
    config:
      config_name: invoice_v2
```

### 3.2 v1.4.0 ekvivalens pipeline (uj)

```yaml
name: invoice_automation_v2
version: "2.0"
steps:
  - name: intake
    adapter: intake_normalize
    config:
      source_type: email
      source_config:
        connector_id: outlook_main
        days: 1

  - name: extract_invoices
    adapter: document_adapter
    method: extract_from_package
    depends_on: [intake]
    config:
      config_name: invoice_v2
```

### 3.3 Backward compat shim layer

A `pipeline/compiler.py` automatikusan felimeri a regi pipeline-okat es konvertalja:

```python
# src/aiflow/pipeline/compatibility.py
def detect_pipeline_version(pipeline_yaml: dict) -> Literal["v1.3", "v1.4"]:
    """Detect pipeline schema version."""
    if "version" in pipeline_yaml and pipeline_yaml["version"].startswith("2."):
        return "v1.4"
    # Heuristic: v1.3 has direct adapter calls, no intake_normalize
    has_intake_step = any(
        step.get("adapter") == "intake_normalize"
        for step in pipeline_yaml.get("steps", [])
    )
    return "v1.4" if has_intake_step else "v1.3"


def upgrade_pipeline_v1_3_to_v1_4(pipeline_yaml: dict) -> dict:
    """Auto-upgrade v1.3 pipeline to v1.4 schema (in-memory only)."""
    upgraded = dict(pipeline_yaml)
    upgraded["version"] = "2.0"
    
    new_steps = []
    intake_added = False
    
    for step in pipeline_yaml.get("steps", []):
        # Detect email_adapter as first step → wrap in intake
        if not intake_added and step.get("adapter") == "email_adapter":
            new_steps.append({
                "name": "intake",
                "adapter": "intake_normalize",
                "config": {
                    "source_type": "email",
                    "source_config": step.get("config", {}),
                },
            })
            intake_added = True
            continue
        
        # Translate document_adapter.extract → extract_from_package
        if step.get("adapter") == "document_adapter" and step.get("method") == "extract":
            new_step = dict(step)
            new_step["method"] = "extract_from_package"
            # depends_on/for_each translated
            if "for_each" in step:
                # for_each iterates package files now
                new_step["for_each"] = "{{ intake.output.package }}"
            new_steps.append(new_step)
            continue
        
        # Default: passthrough
        new_steps.append(step)
    
    upgraded["steps"] = new_steps
    return upgraded
```

A `PipelineRunner` automatikusan hivja:

```python
async def run(self, pipeline_yaml: dict, ...):
    version = detect_pipeline_version(pipeline_yaml)
    if version == "v1.3":
        logger.warning("legacy_pipeline_detected", auto_upgrading=True)
        pipeline_yaml = upgrade_pipeline_v1_3_to_v1_4(pipeline_yaml)
    # ... continue normally
```

### 3.4 Strict mode (Phase 2 utan)

Az auto-upgrade csak Phase 1 + Phase 2 idotartamra (~6 honap). Phase 3-tol:

```yaml
# Egyertelmu hibauzenet legacy formatra
ConfigurationError: Pipeline schema v1.3 is deprecated. 
Please run `aiflow pipeline upgrade <pipeline.yaml>` to upgrade to v2.0.
```

A CLI ad upgrade-toolt:

```bash
aiflow pipeline upgrade pipeline.yaml --output pipeline_v2.yaml
```

---

## 4. Service-szintu Backward Compat

### 4.1 `services/document_extractor.extract(file_path)` shim

```python
# src/aiflow/services/document_extractor/service.py
class DocumentExtractorService:
    async def extract(
        self,
        file_path: str | Path,
        config_name: str,
        **kwargs,
    ) -> ExtractionResult:
        """LEGACY shim — single-file extract.
        
        Internally creates a single-file IntakePackage and calls extract_from_package().
        """
        warnings.warn(
            "extract(file_path) is deprecated. Use extract_from_package(package).",
            DeprecationWarning,
            stacklevel=2,
        )
        # Create a single-file package
        package = IntakePackage(
            package_id=uuid4(),
            source_type=IntakeSourceType.API_PUSH,
            tenant_id=kwargs.get("tenant_id", "default"),
            files=[
                IntakeFile(
                    file_path=str(file_path),
                    file_name=Path(file_path).name,
                    mime_type=detect_mime(file_path),
                    size_bytes=Path(file_path).stat().st_size,
                    sha256=compute_sha256(file_path),
                )
            ],
        )
        return await self.extract_from_package(package, config_name=config_name)
```

### 4.2 `services/rag_engine` embedder default

```python
# src/aiflow/services/rag_engine/service.py
class RAGEngineService:
    def __init__(
        self,
        config: RAGEngineConfig,
        embedder: EmbedderProvider | None = None,  # NEW
        ...
    ):
        # Backward compat: default embedder if not provided
        if embedder is None:
            warnings.warn(
                "RAGEngineService without embedder= parameter is deprecated. "
                "Use ProviderRegistry.get_embedder() to inject one.",
                DeprecationWarning,
            )
            from aiflow.embeddings.azure_openai_provider import AzureOpenAIEmbeddingProvider
            embedder = AzureOpenAIEmbeddingProvider(
                model="text-embedding-3-small",
                client=self.llm_client,
            )
        self.embedder = embedder
```

### 4.3 `services/email_connector` direkt hasznalat

A `services/email_connector` MARAD valtozatlanul. Az uj `intake/source_adapters/email_source.py`
csak wrappeli — a meglevo direkt hivasok mind mukodnek.

---

## 5. Embedding Re-Migration (R5)

### 5.1 Probléma

Az `text-embedding-3-small` 1536-dim embedding-eket. A BGE-M3 1024-dim. A meglevo pgvector
collection-ok ezert NEM kompatibilisek.

### 5.2 Dual-collection elv

**Atmeneti:** Phase 2 idotartamra ket parhuzamos collection per logical collection:

```
collection_invoices               (text-embedding-3-small, 1536-dim) — REGI
collection_invoices_bge_m3        (BGE-M3, 1024-dim) — UJ
```

A query layer szet figyel a tenant policy-t:

```python
async def query(self, collection_id: str, query_text: str):
    policy = self.policy_engine.get_for_tenant(self.tenant_id)
    embedder_name = policy.get_default_provider("embedder")
    
    # Map logical collection → physical
    physical_collection = f"{collection_id}_{embedder_name}"
    
    # Query the right physical collection
    return await self._query_physical(physical_collection, query_text)
```

### 5.3 Re-migration script

```python
# scripts/migrate_collection_to_embedder.py
async def migrate_collection(
    collection_id: str,
    target_embedder: str = "bge_m3",
    *,
    batch_size: int = 100,
    dry_run: bool = False,
) -> MigrationReport:
    """Re-embed all chunks in a collection to a new embedder."""
    report = MigrationReport()
    
    # Iterate chunks
    chunks = await db.fetch_chunks(collection_id)
    new_collection_id = f"{collection_id}_{target_embedder}"
    
    if not dry_run:
        await db.create_collection(new_collection_id, dim=embedder.dimensions)
    
    for batch in batched(chunks, batch_size):
        if dry_run:
            report.would_migrate += len(batch)
            continue
        
        # Re-embed
        texts = [chunk.text for chunk in batch]
        embeddings = await target_embedder.embed(texts)
        
        # Insert into new collection
        await db.bulk_insert_chunks(new_collection_id, batch, embeddings)
        report.migrated += len(batch)
    
    return report
```

### 5.4 Customer migration plan

1. **Sprint N**: dual-collection setup (atmeneti)
2. **Sprint N+1**: re-embedding script futtatas (background)
3. **Sprint N+2**: tenant config update — `embedder=bge_m3`
4. **Sprint N+3**: regi collection torles (`text-embedding-3-small`)

Customer notification 1 sprint korrul:

> Subject: AIFlow v1.4.0 — embedding migration plan
>
> Dear Customer,
>
> We are upgrading the embedding model in AIFlow from text-embedding-3-small to BGE-M3.
> Your collections will be re-embedded automatically. Expected downtime: 0.
> Re-embedding cost: ~$X (covered by our team).
> Re-embedding duration: ~Y minutes per 100k chunks.
>
> Action required: none. We will notify you when complete.

---

## 6. Rolling Deploy Strategy

### 6.1 Blue-Green deployment

Two AIFlow instances:
- **Blue** (v1.3.0): jelenlegi production
- **Green** (v1.4.0): uj verzio, 0% traffic

Migration steps:

1. **Day 0**: Green deploy, smoke tests
2. **Day 1**: Green megkapja a 5% traffic
3. **Day 2-3**: monitoring (Langfuse, Prometheus, Sentry)
4. **Day 4**: 25% traffic → Green
5. **Day 5**: 50% traffic
6. **Day 6**: 100% traffic
7. **Day 7-14**: monitoring + Blue rollback ready
8. **Day 14**: Blue decommission

### 6.2 Feature flags

A v1.4.0 uj funkcioi feature flag-eken behind:

```yaml
# config/features.yaml
features:
  intake_package_enabled: true   # Phase 1
  multi_signal_routing: false    # Phase 2 — opt-in
  bge_m3_embedder: false          # Phase 2 — opt-in
  vault_secrets: false            # Phase 1.5 — opt-in
  otel_tracing: false             # Phase 3 — opt-in
```

Customer per-tenant override:

```yaml
# instances/customer_a/policy.yaml
features:
  intake_package_enabled: true
  multi_signal_routing: true     # customer_a opt-in early
```

### 6.3 Rollback procedure

```bash
# Rollback to v1.3.0
git checkout v1.3.0
docker compose -f docker-compose.prod.yml up -d --build
alembic downgrade 029  # rollback DB
# Customer notification
```

---

## 7. Compatibility Matrix (Legacy + New egyutteles)

| Component | v1.3.0 only | v1.4.0 only | Both |
|-----------|-------------|-------------|------|
| Pipeline YAML v1 (email_adapter direct) | YES | YES (auto-upgrade) | YES |
| Pipeline YAML v2 (intake_normalize) | NO | YES | NO |
| `extract(file)` API | YES | YES (deprecation warning) | YES |
| `extract_from_package(package)` API | NO | YES | NO |
| `text-embedding-3-small` collections | YES | YES (default) | YES |
| `bge-m3` collections | NO | YES (opt-in) | NO |
| Per-tenant policy | NO | YES | NO |
| Vault secrets | NO | YES (Phase 1.5) | NO |
| Multi-source intake | NO | YES (Phase 1) | NO |

---

## 8. Customer Deployment Guide

### 8.1 Self-hosted (Profile A)

```bash
# Step 1: Pre-migration backup
docker exec aiflow_postgres pg_dump aiflow > backup_v1.3.0.sql
docker exec aiflow_redis redis-cli SAVE

# Step 2: Pull v1.4.0 image
docker pull aiflow:v1.4.0

# Step 3: Migrate DB
docker run --rm aiflow:v1.4.0 alembic upgrade head

# Step 4: Update docker-compose.prod.yml
# Image change: aiflow:v1.3.0 → aiflow:v1.4.0

# Step 5: Restart services
docker compose -f docker-compose.prod.yml up -d

# Step 6: Verify
curl http://localhost:8102/health
docker logs aiflow_api | grep "version=1.4.0"

# Step 7: Run smoke tests
./scripts/smoke_test_v1_4_0.sh
```

### 8.2 Profile B (Azure-optimized)

Ugyanaz mint Profile A, plusz:

```bash
# Step 1.5: Validate Azure connectivity
curl -H "X-API-Key: $AZURE_DI_API_KEY" $AZURE_DI_ENDPOINT/health
curl -H "Authorization: Bearer $AZURE_OPENAI_KEY" https://$AZURE_OPENAI_ENDPOINT/openai/deployments?api-version=2024-02-01

# Step 8: Tenant policy update
cat > instances/customer_a/policy.yaml << EOF
policy:
  cloud_ai_allowed: true
  azure_di_enabled: true
  azure_search_enabled: false  # Phase 4
  azure_embedding_enabled: true
  default_embedding_provider: azure_openai_3_small
EOF
```

---

## 9. Customer Notification Template

### 9.1 Pre-migration (1 sprint elott)

```
Subject: AIFlow v1.4.0 — Multi-Source Intake Refinement (Migration Notice)

Tisztelt {customer},

A {date} datumon fogjuk migralni az AIFlow rendszeret v1.4.0 verzioba. Ez a refinement
release multi-source intake (email + file + folder + batch + API) tamogatast hoz.

Mit kell tennod:
- SEMMIT — automatikus migracio, zero downtime
- A meglevo pipeline-jaid mukodnek modositas nelkul (auto-upgrade)
- Az uj funkciok feature flag-en, opcionalisak

Mire szamithatsz:
- 5-10 perces kis "warning" log uzenet a deprecation warningok-rol — ez normalis
- Az `extract(file)` API meg mindig mukodik, de Phase 2-tol uj a primary
- A re-embedding (Phase 2) automatikus, koltsegmentes

Kockazat: alacsony — rolling deploy, blue-green, rollback ready.

Kerdes? Email: support@aiflow.io
```

### 9.2 Migration completed

```
Subject: AIFlow v1.4.0 — Migration Complete

Tisztelt {customer},

A migracio sikeres. Az AIFlow v1.4.0 mostantol fut.

Uj funkciok elerhetek (opt-in):
1. Multi-source intake — file upload + folder watcher
2. Per-tenant policy override
3. Provider abstraction (parser/classifier/embedder)

Hogyan kapcsold be? Lasd a `instances/{tenant}/policy.yaml` fajlt.
Dokumentacio: https://docs.aiflow.io/v1.4.0/

Kovetkezo upgrade: v1.5.0 (Phase 2, ~3 honap mulva) — multi-signal routing,
PDF/A archival, BGE-M3 embedding.

Koszonjuk a turelmedet!
```

---

## 10. Migration Test Strategy

### 10.1 Pre-migration tests

```bash
# Egysegtesztek
pytest tests/unit/migration/ -v

# Integration test: backup → migrate → verify
./scripts/test_migration_e2e.sh

# Compatibility test: legacy pipeline auto-upgrade
pytest tests/integration/test_pipeline_compat.py -v
```

### 10.2 Post-migration tests

```bash
# Smoke test
curl http://localhost:8102/health
curl http://localhost:8102/api/v1/pipelines
curl http://localhost:8102/api/v1/intake/upload-package -F "file=@test.pdf"

# Regression suite (lasd 49_STABILITY_REGRESSION.md)
make regression L3
```

### 10.3 Rollback test

Fejlesztesi env:

```bash
# Apply migration
alembic upgrade head

# Rollback
alembic downgrade 029

# Verify state
pg_dump aiflow > after_rollback.sql
diff backup_v1.3.0.sql after_rollback.sql  # should be minimal
```

---

## 11. Phase-szintu rollout

| Phase | v1.x.0 | Customer migracio | Backward compat ablakk |
|-------|--------|-------------------|-----------------------|
| Phase 1a | v1.4.0 | Foundation: alapvero contractok | 6 honap |
| Phase 1b | v1.4.1 | Source adapters | 6 honap |
| Phase 1c | v1.4.2 | Refactor + acceptance | 6 honap |
| Phase 1.5 | v1.4.5 | Vault + self-hosted Langfuse | 6 honap |
| Phase 2a | v1.5.0 | Multi-signal routing | 3 honap |
| Phase 2b | v1.5.1 | VLM stack | 3 honap |
| Phase 2c | v1.5.2 | Embedder providers + re-embed | 3 honap |
| Phase 2d | v1.5.3 | Archival | 3 honap |
| Phase 3 | v1.6.0 | Governance | 3 honap |
| Phase 4 | v2.0.0+ | Optional | NA |

---

## 12. Rollback Decision Matrix (P2 hardening)

> **Hozzaadva:** `105_*` P2 hardening keretin belul (2026-04-09).

Nem minden hiba ugyanazt a rollback strategiat igenyli. Az alabbi decision matrix a
leggyakoribb hibaszituaciokra ad explicit strategiai iranyt.

### 12.1 Decision matrix

| # | Hibaszituacio | Rollback strategia | Write freeze? | Restore? | Indoklas |
|---|--------------|-------------------|--------------|---------|---------|
| 1 | Pipeline auto-upgrade shim hiba | **Forward-fix** | NO | NO | Shim logikai hiba → patch release v1.4.0.1 |
| 2 | Alembic 030-031 migration hiba (staging-ben elkapott) | **Downgrade** | NO | NO | `alembic downgrade 029`, fix, re-run |
| 3 | Alembic 030-031 migration hiba (prod-ban!) | **Downgrade + Write freeze** | YES | NO | `alembic downgrade 029` + `AIFLOW_READ_ONLY=true` atmenetileg |
| 4 | `IntakePackage` Pydantic schema backward-breaking change | **Forward-fix** | NO | NO | Shim pattern szerinti kompatibilitas visszaallitasa |
| 5 | R4 `extract_from_package()` hiba (uj feature NEM mukodik) | **Feature flag OFF** | NO | NO | `AIFLOW_FEATURE_INTAKE_PACKAGE=false`, regi `extract(file)` az alapkut |
| 6 | R5 embedder provider kozpeti hiba (BGE-M3 crash) | **Feature flag OFF** | NO | NO | `AIFLOW_FEATURE_BGE_M3=false`, vissza Azure OpenAI |
| 7 | Re-embedding collection data corruption | **Dual-collection fallback** | NO | NO | Uj collection drop, regi collection marad aktiv |
| 8 | Re-embedding collection data corruption + regi is torolt | **Restore from backup** | YES | YES | Backup restore + re-ingest |
| 9 | Multi-tenant isolation breach (cross-tenant data leak) | **Write freeze + Forward-fix** | YES | NO | Azonnali feature flag OFF + security hotfix release |
| 10 | Multi-tenant isolation breach + data already exfiltrated | **Write freeze + Restore + Incident response** | YES | YES | Incident response playbook, compliance notification |
| 11 | `PolicyEngine` rossz config-ot olvas be (Profile A cloud-t enged) | **Downgrade config** | NO | NO | Config file revert, prompt reload |
| 12 | Vault secret manager hiba (titkok elerhetlen) | **Fallback to env vars** | NO | NO | `EnvSecretProvider` fallback ideiglenesen |
| 13 | Self-hosted Langfuse crash | **Fallback to YAML prompts** | NO | NO | `PromptManager` YAML fallback layer mar van |
| 14 | veraPDF validator rossz verzio (legitim PDF/A-t elutasit) | **Feature flag OFF** | NO | NO | `pdfa_validation_required=false` temporarily, manual review |
| 15 | Gotenberg conversion tomeges hiba | **Feature flag OFF** | NO | NO | `archival_pdfa_required=false`, raw PDF marad |
| 16 | Routing engine rossz provider-t valaszt (pl. Profile A-ban Azure DI-t) | **Write freeze + Forward-fix** | YES | NO | Azonnali compliance risk, policy enforcement hotfix |
| 17 | Performance degradation (>50% lassubb) | **Forward-fix vagy Feature flag OFF** | NO | NO | Attol fuggoen, melyik modul lassabb — profiling + tuning |
| 18 | Uj UI oldal crash (aiflow-admin) | **Forward-fix** | NO | NO | Frontend hotfix, backend nem erintet |

### 12.2 Decision criteria

A rollback strategy kivalasztasa az alabbi kerdesekre valaszol:

1. **Reversible?** — Lehet a hibat forward-fix-szel javitani, vagy kotelezo visszavonas?
2. **Data integrity?** — Megsertesult data integrity? Akkor restore kotelezo.
3. **Security?** — Security breach? Akkor write freeze azonnali + incident response.
4. **Compliance?** — Compliance violation? Akkor write freeze + forward-fix hotfix.
5. **Customer impact?** — Mekkora a customer impact? Downgrade idotartama vs forward-fix gyorsaag.
6. **Backward compat maradt?** — Ha igen, feature flag OFF eleg. Ha nem, downgrade.

### 12.3 Decision tree

```
Incident detected
    │
    ▼
Data integrity compromised?
    │
    ├── YES ─→ Write freeze + Backup restore + Incident response
    │
    └── NO
         │
         ▼
        Security / Compliance breach?
         │
         ├── YES ─→ Write freeze + Forward-fix hotfix
         │
         └── NO
              │
              ▼
             Backward compat maradt?
              │
              ├── YES ─→ Feature flag OFF (no downtime)
              │
              └── NO
                   │
                   ▼
                  Prod downtime megengedett?
                   │
                   ├── YES ─→ Downgrade + fix + re-deploy
                   │
                   └── NO ─→ Forward-fix hotfix (urgent patch)
```

### 12.4 Write freeze procedure

Ha "write freeze" szukseges, a kovetkezo lepesek:

```bash
# Step 1: API write endpoint-ok disable
export AIFLOW_READ_ONLY=true
docker exec aiflow_api kill -SIGHUP 1  # graceful reload

# Step 2: Scheduler leallitas (uj job-ok nem indulnak)
docker exec aiflow_scheduler kill -SIGTERM 1

# Step 3: Worker-ek graceful shutdown (futo job-ok befejezodnek)
docker exec aiflow_worker kill -SIGTERM 1

# Step 4: UI "read-only mode" banner
curl -X POST http://localhost:8102/api/v1/admin/maintenance-mode -d '{"enabled": true}'

# Step 5: Customer notification
# (template: "AIFlow read-only mode: ~30 min maintenance for critical fix")
```

**Read-only mode idotartam**: max **30 perc** (ezen tul customer escalation).

### 12.5 Backup restore procedure

Csak akkor, ha data integrity compromised. **KRITIKUS** — minden restore elott
verify backup integrity.

```bash
# Step 1: Identify last known good backup
ls -lh backups/ | grep "backup_pre_v1.4.0"

# Step 2: Verify backup integrity
pg_restore --list backups/backup_pre_v1.4.0.sql > /dev/null && echo "OK"

# Step 3: Write freeze (Section 12.4)

# Step 4: Stop all services
docker compose -f docker-compose.prod.yml stop

# Step 5: Drop + recreate target DB (VIGYAZZ!)
dropdb -U aiflow aiflow && createdb -U aiflow aiflow

# Step 6: Restore
pg_restore -U aiflow -d aiflow backups/backup_pre_v1.4.0.sql

# Step 7: Run smoke test
./scripts/smoke_test.sh

# Step 8: Lift write freeze + notify customer
```

**Kotelezo**: incident post-mortem 72 oran belul.

### 12.6 Rollback rehearsal (P4 acceptance)

A Phase 1a acceptance elott **kotelezo** rollback rehearsal staging-ben:

- [ ] Downgrade test: `alembic downgrade 029` + smoke
- [ ] Feature flag OFF test: `AIFLOW_FEATURE_INTAKE_PACKAGE=false` + smoke
- [ ] Backup restore rehearsal: staging backup → test DB restore
- [ ] Write freeze rehearsal: 5 perc read-only mode staging-ben
- [ ] Incident response playbook walk-through

Ez a **lista a `103_*` Section 9 acceptance-be** is bekerul (lasd P4 hardening).

---

## 13. Sign-off Checklist

- [ ] Migration script-ek elkeszultek (alembic 030-036)
- [ ] Backward compat shim layer working
- [ ] Pipeline auto-upgrade working
- [ ] Re-embedding script working
- [ ] Customer notification draft kesz
- [ ] Rollback procedure tesztelve (Section 12)
- [ ] Smoke test suite kesz
- [ ] Compatibility matrix elfogadva
- [ ] Rollback decision matrix elfogadva (Section 12.1)
- [ ] Rollback rehearsal staging-ben lefutott (Section 12.6)

---

## 14. Mit NEM tartalmaz ez a dokumentum

- Pydantic schema (lasd `100_b_*.md`)
- State machine (lasd `100_c_*.md`)
- Deployment infra (`62_DEPLOYMENT_ARCHITECTURE.md`)
- Customer onboarding pipeline (Phase 3 jovobeli dokumentum)
