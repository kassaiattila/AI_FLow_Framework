# AIFlow v2 — Final Validation (2. ciklus, Sign-off)

> **Verzio:** 1.0
> **Datum:** 2026-04-08
> **Statusz:** AKTIV — Phase 1 indulas elotti vegleges sign-off
> **Tipus:** Architectural sign-off review (2. ciklus)
> **Reviewer:** senior enterprise solution architect + lead Python platform engineer + AI systems architect + DevOps + compliance expert
> **Vizsgalat tárgya:**
> - `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` (frissitve ADR-1-tel)
> - `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` (uj — Must fix #1)
> - `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` (uj — Must fix #2)
> - `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` (uj — Must fix #3)
> - `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` (frissitve N22b CrewAI experiment)
> - `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` (1. ciklus eredmenye)

> **Cel:** A `102_*` 1. ciklus altal feltart **Must fix** tetelek lezarasa, a teljes terv-set
> **konzisztencia + alignment + completeness** ellenorzese, es a Phase 1 implementacio
> **sign-off-ja**.

---

## 1. Vegleges ertekeles — osszbenyomas

A `100_*` + `101_*` refinement terv az 1. ciklus utan **+3 kritikus dokumentummal** (`100_b`,
`100_c`, `100_d`) **es** ADR-1-gyel (CrewAI core orchestrator REJECTED) bovult. A tervek mostantol
**teljesnek + implementacio-keszesnek** tekinthetok a Phase 1 indulas elott.

**Erosseg novekedes**: 7/10 → **9/10**

**Maradek nyitott pontok**: Should fix tetelei (6 db) — ezek Phase 1 acceptance elott megoldando-k,
NEM blokkoljak a sprintindulast.

---

## 2. Must fix tetelek — Lezaras

| # | Tetel | Megoldas | Statusz | Elheszithetto |
|---|------|----------|---------|---------------|
| MF1 | Contract-first dokumentum | `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` (13 Pydantic modell teljes) | RESOLVED | DONE |
| MF2 | State lifecycle modell | `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` (7 entitas allapotgep) | RESOLVED | DONE |
| MF3 | Migration playbook | `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` (rolling deploy + backward compat) | RESOLVED | DONE |
| MF4 | Phase 1 ujraosztas | 100_/101_ Phase 1a/1b/1c bontas | OPEN | This document |
| MF5 | Routing engine governance | 101_ N7 kibovites | OPEN | This document |
| MF6 | Provider abstraction contract | 101_ N6 kibovites (4 ABC + contract test) | OPEN | This document |
| MF7 | Multi-tenant data isolation | 101_ R5 + N6 (collection ID format) | OPEN | This document |

A jelen 103_ dokumentum lezarja MF4-MF7-et a kovetkezo szakaszokban.

---

## 3. MF4 — Phase 1 ujraosztas (1a/1b/1c/1.5)

A 100_ Section 7 ("Phase 1 — Critical corrections") tul nagy egy sprintnek. Az ujraosztas:

### 3.1 Phase 1a — Foundation (v1.4.0)

**Sprint cel:** Alap modellek + policy engine + provider registry + tenant override mukodik.
**Sprint becsules:** 1 sprint (3-4 het)

| # | Task | Komponens | Becsules | Dependencies |
|---|------|-----------|---------|--------------|
| 1a.1 | Domain contracts implementacio (alembic 030) | `100_b` Section 1-3 (IntakePackage, IntakeFile, IntakeDescription, RoutingDecision) | M | — |
| 1a.2 | State machine implementacio | `100_c` Section 1-7 (state transitions + validators) | M | 1a.1 |
| 1a.3 | `intake/normalization.py` | N3 IntakeNormalizationLayer | S | 1a.1 |
| 1a.4 | `policy/engine.py` + 30+ parameter | N5 PolicyEngine | M | — |
| 1a.5 | `policy/profiles/profile_a.yaml` + `profile_b.yaml` | Default config | S | 1a.4 |
| 1a.6 | `providers/registry.py` + 4 ABC interface | N6 ProviderRegistry + interfaces | S | — |
| 1a.7 | `skill_system/instance_*.py` policy override | R13 | S | 1a.4 |
| 1a.8 | Backward compat shim layer | `100_d` Section 4 | S | 1a.1 |
| 1a.9 | Phase 1a acceptance E2E + tesztek | — | M | minden |

**Phase 1a acceptance**:
- [ ] IntakePackage Pydantic modell mukodik
- [ ] State transition validator PASS
- [ ] PolicyEngine 30+ parameter mukodik
- [ ] ProviderRegistry 4 tipusra
- [ ] Profile A + Profile B config files
- [ ] Per-instance policy override
- [ ] Backward compat: meglevo extract(file) API mukodik
- [ ] DB migration 030-031 sikeres + rollback tesztelve

### 3.2 Phase 1b — Source adapters (v1.4.1)

**Sprint cel:** Minden source-bol lehet IntakePackage-et betolteni.
**Sprint becsules:** 1 sprint (3-4 het)

| # | Task | Komponens | Becsules | Dependencies |
|---|------|-----------|---------|--------------|
| 1b.1 | `intake/source_adapters/base.py` IntakeSourceAdapter ABC | N2 base | S | Phase 1a DONE |
| 1b.2 | `email_source.py` (Unstructured + email_connector wrap) | N2 + R1 | M | 1b.1 |
| 1b.3 | `file_source.py` (UI form upload) | N2 | S | 1b.1 |
| 1b.4 | `folder_source.py` (S3 + local fs) | N2 | M | 1b.1 |
| 1b.5 | `batch_source.py` (manual batch import API) | N2 | S | 1b.1 |
| 1b.6 | `api_source.py` (webhook push) | N2 | S | 1b.1 |
| 1b.7 | `intake/association.py` FileDescriptionAssociator | N4 | M | 1b.1 |
| 1b.8 | API endpoint `POST /api/v1/intake/upload-package` | — | S | minden |
| 1b.9 | Phase 1b acceptance E2E (5 source) | — | M | minden |

**Phase 1b acceptance**:
- [ ] 5 source adapter mukodik
- [ ] Egyseges interface
- [ ] File ↔ description association mukodik (rule + LLM fallback)
- [ ] API endpoint mukodik
- [ ] Multi-source acceptance E2E PASS

### 3.3 Phase 1c — Refactor + acceptance (v1.4.2)

**Sprint cel:** Meglevo invoice_finder pipeline mukodik IntakePackage-en at + Phase 1 acceptance.
**Sprint becsules:** 1 sprint (3-4 het)

| # | Task | Komponens | Becsules | Dependencies |
|---|------|-----------|---------|--------------|
| 1c.1 | `services/document_extractor.extract_from_package()` | R4 | M | Phase 1a + 1b DONE |
| 1c.2 | `extraction_results` tabla kibovites (alembic 033) | R4 + `100_d` Section 2.1 | S | 1c.1 |
| 1c.3 | Pipeline auto-upgrade shim layer | `100_d` Section 3.3 | S | — |
| 1c.4 | `pipeline/builtin_templates/invoice_automation_v2.yaml` v2.0 schema | R12 | S | 1c.1 |
| 1c.5 | `pipeline/adapters/*` egyseges provider interface | R15 | S | Phase 1a DONE |
| 1c.6 | UI: invoice_finder oldal multi-file upload | aiflow-admin | M | 1b.8 |
| 1c.7 | Phase 1 vegleges acceptance E2E (10 processing flow) | `document_pipeline.md` Section 8 | L | minden |
| 1c.8 | Phase 1 dokumentacio + customer notification | — | S | minden |

**Phase 1c acceptance**:
- [ ] `extract_from_package()` mukodik
- [ ] DB migration 033 sikeres
- [ ] Pipeline auto-upgrade mukodik
- [ ] invoice_finder pipeline IntakePackage-en at
- [ ] UI multi-file upload mukodik
- [ ] 10 processing flow E2E PASS
- [ ] Customer notification kuldve

### 3.4 Phase 1.5 — Vault + Self-hosted Langfuse (v1.4.5)

**Sprint cel:** Profile A capable deployment.
**Sprint becsules:** 0.5 sprint (1-2 het)

| # | Task | Komponens | Becsules | Dependencies |
|---|------|-----------|---------|--------------|
| 1.5.1 | `security/vault_provider_impl.py` (hvac) | R8/N21 | M | Phase 1c DONE |
| 1.5.2 | Vault testcontainers integration test | — | S | 1.5.1 |
| 1.5.3 | `infra/langfuse/docker-compose.yaml` self-hosted | — | S | — |
| 1.5.4 | Profile A config: `LANGFUSE_HOST=https://langfuse.internal` | — | S | 1.5.3 |
| 1.5.5 | Profile A teljes pipeline self-hosted Langfuse-szal | — | M | 1.5.4 |
| 1.5.6 | Customer migration guide Profile A-ra | `100_d` Section 8.1 | S | minden |

**Phase 1.5 acceptance**:
- [ ] Vault prod impl mukodik
- [ ] Self-hosted Langfuse mukodik
- [ ] Profile A E2E acceptance PASS air-gapped kornyezetben
- [ ] Customer Profile A deployment ready

### 3.5 Phase 1 osszesen

```
v1.4.0  Phase 1a — Foundation (1 sprint)
v1.4.1  Phase 1b — Source adapters (1 sprint)
v1.4.2  Phase 1c — Refactor + acceptance (1 sprint)
v1.4.5  Phase 1.5 — Vault + self-hosted Langfuse (0.5 sprint)
                                  ─────────────────────────────
                                  3.5 sprint = ~3-4 honap
```

---

## 4. MF5 — Routing Engine Governance kibovites

A 101_ N7 (`MultiSignalRoutingEngine`) **kibovitese** a kovetkezo elemekkel:

### 4.1 Signal weight registry

```python
# src/aiflow/routing/weights.py
class SignalWeightRegistry:
    """Per-tenant + per-decision-type signal weight registry."""
    
    DEFAULT_WEIGHTS: dict[ProviderType, dict[str, float]] = {
        ProviderType.PARSER: {
            "text_layer_ratio": 0.30,    # vs scan
            "ocr_need": 0.25,             # OCR szuksegesseg
            "table_suspicion": 0.20,      # tablazat detektalas
            "image_dominance": 0.15,      # kep dominancia
            "layout_complexity": 0.10,    # komplex layout
        },
        ProviderType.CLASSIFIER: {
            "is_scan": 0.40,              # scan → visual classifier
            "text_quality": 0.30,         # text klasszifikator alkalmasság
            "page_count": 0.20,           # multi-page reasoning
            "language_match": 0.10,       # language model fit
        },
        # ...
    }
    
    def get_weights(
        self,
        provider_type: ProviderType,
        tenant_id: str | None = None,
    ) -> dict[str, float]:
        """Get weights with tenant override fallback."""
        defaults = self.DEFAULT_WEIGHTS[provider_type]
        if tenant_id:
            override = self.tenant_overrides.get(tenant_id, {}).get(provider_type, {})
            return {**defaults, **override}
        return defaults
```

### 4.2 Priority hierarchy

```python
# src/aiflow/routing/priorities.py
class RoutingPriority(Enum):
    """Decision priority hierarchy (higher wins)."""
    
    COMPLIANCE = 100   # blocking constraints (cloud_disallowed, pii_block)
    POLICY = 80         # tenant policy preferences
    COST = 60           # cost cap (Profile B)
    LATENCY = 40        # SLA target
    ACCURACY = 20       # quality target
```

A scoring az ebben a sorrendben tortenik:
1. **Compliance**: minden provider, ami **nem tudja megfelelni a policy-nek** → kizart
2. **Policy**: tenant preference (default vs override)
3. **Cost**: per-decision cost cap
4. **Latency**: SLA target
5. **Accuracy**: quality score

Ha egy magasabb prioritas filterelt, az alacsonyabbak NEM mehetnek tobb provider-t.

### 4.3 All-providers-unavailable fallback

```python
async def route_parser(
    self,
    file: IntakeFile,
    package_context: IntakePackage,
) -> RoutingDecision:
    """Route with full failure handling."""
    candidates = self.provider_registry.list_parsers()
    
    # Filter by policy (Compliance priority)
    eligible = [c for c in candidates if self.policy_engine.is_allowed(c.name, ...)]
    
    if not eligible:
        # CRITICAL: no provider can serve this file
        return RoutingDecision(
            status=RoutingDecisionStatus.ALL_FAILED,
            selected_provider="",
            selection_reason="No eligible provider under current policy",
            ...
        )
    
    # Score eligible providers
    scores = await self._score_providers(eligible, file, package_context)
    
    # Select best
    selected = max(scores, key=lambda s: s.score)
    
    # Fallback chain (next 2-3)
    fallback = sorted(scores, key=lambda s: s.score, reverse=True)[1:4]
    
    return RoutingDecision(
        selected_provider=selected.provider_name,
        fallback_chain=[s.provider_name for s in fallback],
        candidate_scores=scores,
        selection_confidence=selected.score,
        ...
    )
```

Ha `ALL_FAILED`:
- Auto-`ReviewTask(review_type=ambiguous_provider)`
- Package state → `REVIEW_PENDING`
- Notification a tenant adminhoz

### 4.4 Routing audit query interface

```python
# src/aiflow/api/v1/routing.py
@router.get("/decisions/{package_id}")
async def get_routing_decisions(
    package_id: UUID,
    *,
    user: User = Depends(authenticated),
) -> list[RoutingDecision]:
    """Get all routing decisions for a package."""
    return await routing_repo.get_by_package(package_id)


@router.get("/decisions/{decision_id}/audit")
async def get_decision_audit(
    decision_id: UUID,
) -> RoutingDecisionAudit:
    """Get full audit trail for a decision."""
    decision = await routing_repo.get(decision_id)
    return RoutingDecisionAudit(
        decision=decision,
        signals=decision.signals_used,
        candidate_scores=decision.candidate_scores,
        policy_snapshot=decision.policy_constraints,
        executed=decision.status == RoutingDecisionStatus.EXECUTED,
    )
```

### 4.5 Human override

```python
# src/aiflow/api/v1/routing.py
@router.post("/decisions/{decision_id}/override")
async def human_override_decision(
    decision_id: UUID,
    payload: HumanOverridePayload,
    *,
    user: User = Depends(require_role("admin")),
) -> RoutingDecision:
    """Human admin overrides a routing decision."""
    return await routing_engine.override(
        decision_id,
        new_provider=payload.provider_name,
        reason=payload.reason,
        user_id=user.id,
    )
```

### 4.6 Routing confidence calculation

```python
def calculate_routing_confidence(
    selected_score: float,
    second_best_score: float,
    signals: list[RoutingSignal],
) -> float:
    """Routing confidence:
    
    - HIGH (>0.8): selected score >> second best, all signals strong
    - MEDIUM (0.5-0.8): selected wins clearly, some signals weak
    - LOW (<0.5): close call, signals contradict
    """
    score_gap = selected_score - second_best_score
    signal_strength = sum(s.value for s in signals if isinstance(s.value, (int, float))) / len(signals)
    return min(1.0, (score_gap * 2 + signal_strength) / 2)
```

### 4.7 Cost-aware routing (Profile B)

```python
# src/aiflow/routing/cost_cap.py
class CostCapPolicy:
    """Per-tenant per-decision cost cap."""
    
    def __init__(
        self,
        per_decision_cap_usd: float = 0.50,
        per_package_cap_usd: float = 5.00,
        per_tenant_daily_cap_usd: float = 100.00,
    ): ...
    
    async def check_cost_cap(
        self,
        candidate_provider: str,
        estimated_cost: float,
        tenant_id: str,
        package_id: UUID,
    ) -> bool:
        """Return True if the candidate is within all caps."""
        # Per-decision cap
        if estimated_cost > self.per_decision_cap_usd:
            return False
        # Per-package cap
        package_total = await self.get_package_cost(package_id)
        if package_total + estimated_cost > self.per_package_cap_usd:
            return False
        # Per-tenant daily cap
        daily_total = await self.get_daily_cost(tenant_id)
        if daily_total + estimated_cost > self.per_tenant_daily_cap_usd:
            return False
        return True
```

A routing engine `_score_providers()`-ben hivja a `cost_cap.check_cost_cap()`-et, es ha
nem fer be, a candidate score-ja **0.0** lesz (effective kizar).

---

## 5. MF6 — Provider Abstraction Contract kibovites

### 5.1 4 darab ABC

```python
# src/aiflow/providers/interfaces.py
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel


class ProviderMetadata(BaseModel):
    name: str
    version: str
    supported_types: list[str]
    speed_class: Literal["fast", "normal", "slow"]
    gpu_required: bool = False
    cost_class: Literal["free", "cheap", "moderate", "expensive"]
    license: str  # AGPL, MIT, commercial


class ParserProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...
    
    @abstractmethod
    async def parse(
        self,
        file: IntakeFile,
        package_context: IntakePackage,
    ) -> ParserResult: ...
    
    @abstractmethod
    async def health_check(self) -> bool: ...
    
    @abstractmethod
    async def estimate_cost(self, file: IntakeFile) -> float: ...


class ClassifierProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...
    
    @abstractmethod
    async def classify(
        self,
        file: IntakeFile,
        parser_result: ParserResult,
        candidate_classes: list[str],
    ) -> ClassificationResult: ...
    
    @abstractmethod
    async def health_check(self) -> bool: ...


class ExtractorProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...
    
    @abstractmethod
    async def extract(
        self,
        file: IntakeFile,
        parser_result: ParserResult,
        config: DocumentTypeConfig,
    ) -> ExtractionResult: ...


class EmbedderProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...
    
    @abstractmethod
    @property
    def dimensions(self) -> int: ...
    
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    
    @abstractmethod
    async def health_check(self) -> bool: ...
```

### 5.2 Contract test framework

```python
# tests/integration/providers/test_contract.py
import pytest
from aiflow.providers.interfaces import ParserProvider, ClassifierProvider, ExtractorProvider, EmbedderProvider


PARSER_PROVIDERS = [
    "aiflow.ingestion.parsers.docling_parser:DoclingParserProvider",
    "aiflow.ingestion.parsers.pymupdf4llm_parser:PyMuPDF4LLMParserProvider",
    "aiflow.providers.parsers.azure_di_provider:AzureDIParserProvider",
]


@pytest.mark.parametrize("provider_path", PARSER_PROVIDERS)
class TestParserProviderContract:
    """Every parser provider MUST pass these tests."""
    
    @pytest.fixture
    def provider(self, provider_path: str) -> ParserProvider:
        return load_provider(provider_path)
    
    def test_metadata_present(self, provider):
        meta = provider.metadata
        assert meta.name
        assert meta.version
        assert meta.supported_types
    
    def test_implements_parse(self, provider):
        assert callable(provider.parse)
    
    def test_implements_health_check(self, provider):
        assert callable(provider.health_check)
    
    @pytest.mark.asyncio
    async def test_health_check_runs(self, provider):
        result = await provider.health_check()
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_parse_returns_parser_result(self, provider, sample_pdf):
        result = await provider.parse(sample_pdf, package_context=...)
        assert result.provider_name == provider.metadata.name
        assert result.text or result.markdown
```

A CI mindig futtatja minden uj provider-re. **NINCS uj provider** test-pass nelkul.

---

## 6. MF7 — Multi-tenant Data Isolation

### 6.1 Collection ID format

**Kotelezo**: Minden vector store collection ID `{tenant_id}_{collection_name}` formaban van.

```python
# src/aiflow/services/rag_engine/collection_id.py
class CollectionID(BaseModel):
    tenant_id: str
    collection_name: str
    embedder_name: str  # for dual-collection migration
    
    @property
    def physical_name(self) -> str:
        return f"{self.tenant_id}__{self.collection_name}__{self.embedder_name}"
    
    @classmethod
    def parse(cls, physical_name: str) -> "CollectionID":
        parts = physical_name.split("__", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid collection ID: {physical_name}")
        return cls(
            tenant_id=parts[0],
            collection_name=parts[1],
            embedder_name=parts[2],
        )
```

### 6.2 DB constraint

```sql
-- Alembic migration 030 (intake_packages part)
ALTER TABLE rag_collections
ADD CONSTRAINT collection_name_starts_with_tenant
CHECK (name ~ '^[a-z0-9_]+__[a-z0-9_]+__[a-z0-9_]+$');
```

### 6.3 Cross-tenant query prevention

```python
# src/aiflow/services/rag_engine/service.py
class RAGEngineService:
    async def query(
        self,
        collection_id: str,
        query_text: str,
        *,
        ctx: ExecutionContext,
    ) -> QueryResult:
        """Tenant-aware query."""
        parsed = CollectionID.parse(collection_id)
        if parsed.tenant_id != ctx.tenant_id:
            raise PermissionDeniedError(
                f"Tenant {ctx.tenant_id} cannot query collection of tenant {parsed.tenant_id}"
            )
        # ... continue
```

### 6.4 Cross-tenant query test

```python
# tests/integration/security/test_tenant_isolation.py
@pytest.mark.asyncio
async def test_cross_tenant_query_blocked():
    """A user from tenant A MUST NOT query tenant B's collection."""
    rag = RAGEngineService(...)
    
    # Tenant B has a collection
    await rag.create_collection("tenant_b__invoices__bge_m3", embedder=...)
    
    # Tenant A tries to query
    ctx_a = ExecutionContext(tenant_id="tenant_a", ...)
    with pytest.raises(PermissionDeniedError):
        await rag.query("tenant_b__invoices__bge_m3", "test", ctx=ctx_a)
```

### 6.5 Audit log tenant filter

```sql
-- Audit logs MUST always include tenant_id
SELECT * FROM audit_logs WHERE tenant_id = $1 ORDER BY created_at DESC;
```

### 6.6 Object storage naming + path isolation (P2 hardening)

> **Hozzaadva:** `105_*` P2 hardening keretin belul (2026-04-09).

**Alapelv**: Minden object storage elem (parsed artifact, archival PDF/A, thumbnail, export)
**kotelezoen** a `tenant_id/` prefix alatt tarolodik. Cross-tenant path NEM lehetseges.

**Naming convention**:

```
{bucket}/
  {tenant_id}/
    intake/
      {package_id}/
        files/
          {file_id}__{sha256_short}__{original_name}
        descriptions/
          {description_id}.json
    archival/
      {artifact_id}__{profile}.pdf
    quarantine/
      {artifact_id}__{quarantine_reason}.pdf
    derivatives/
      {file_id}/
        thumbnails/
        extracted_pages/
    exports/
      {export_id}/
        report.md
        invoices.csv
```

**Implementacio**:

```python
# src/aiflow/services/object_storage/path_builder.py
class TenantAwarePathBuilder:
    """Tenant-scoped object storage path builder."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def file_path(self, package_id: UUID, file_id: UUID, sha256: str, name: str) -> str:
        return f"{self.tenant_id}/intake/{package_id}/files/{file_id}__{sha256[:12]}__{name}"
    
    def archival_path(self, artifact_id: UUID, profile: str) -> str:
        return f"{self.tenant_id}/archival/{artifact_id}__{profile}.pdf"
    
    def quarantine_path(self, artifact_id: UUID, reason: str) -> str:
        return f"{self.tenant_id}/quarantine/{artifact_id}__{reason}.pdf"
```

**Kereszt-tenant hozzaferest kizaras**:

```python
# src/aiflow/services/object_storage/client.py
class ObjectStorageClient:
    async def get(self, path: str, *, ctx: ExecutionContext) -> bytes:
        """Tenant-scoped object get."""
        tenant_prefix = f"{ctx.tenant_id}/"
        if not path.startswith(tenant_prefix):
            raise PermissionDeniedError(
                f"Tenant {ctx.tenant_id} cannot access path {path}"
            )
        return await self._backend.get(path)
    
    async def list_prefix(self, prefix: str, *, ctx: ExecutionContext) -> list[str]:
        """Tenant-scoped list operation."""
        tenant_prefix = f"{ctx.tenant_id}/"
        if not prefix.startswith(tenant_prefix):
            raise PermissionDeniedError(...)
        return await self._backend.list(prefix)
```

**Test**:

```python
# tests/integration/security/test_object_storage_isolation.py
async def test_cross_tenant_object_access_blocked():
    """Tenant A cannot read tenant B's archival artifact."""
    # Tenant B uploads
    ctx_b = ExecutionContext(tenant_id="tenant_b", ...)
    path_b = await storage.put("tenant_b/archival/xxx.pdf", data, ctx=ctx_b)
    
    # Tenant A tries to read
    ctx_a = ExecutionContext(tenant_id="tenant_a", ...)
    with pytest.raises(PermissionDeniedError):
        await storage.get(path_b, ctx=ctx_a)
```

### 6.7 Audit log tenant filter (formalizalva)

> **Hozzaadva:** `105_*` P2 hardening keretin belul (2026-04-09).

**Alapelv**: Minden audit log query **kotelezoen** `tenant_id` filter-t alkalmaz.
Admin-szintu cross-tenant query csak **super-admin** szerepre engedelyezett.

**Repository layer enforcement**:

```python
# src/aiflow/security/audit_repository.py
class AuditLogRepository:
    async def query(
        self,
        *,
        ctx: ExecutionContext,
        filters: AuditLogFilter,
        super_admin_mode: bool = False,
    ) -> list[AuditLogEntry]:
        """Query audit logs with mandatory tenant scoping."""
        if super_admin_mode:
            # Super admin: cross-tenant query allowed, BUT kotelezo audit-log rolluk
            if not await self.rbac.has_role(ctx.user_id, "super_admin"):
                raise PermissionDeniedError("super_admin role required for cross-tenant audit query")
            await self.audit_service.log_superadmin_access(ctx.user_id, filters)
            return await self._execute_unfiltered(filters)
        
        # Normal mode: always tenant-scoped
        return await self._execute_tenant_scoped(ctx.tenant_id, filters)
```

**Database constraint**:

```sql
-- Alembic 030 intake_packages + audit_logs kiegeszites
CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);

-- Row-level security (PostgreSQL 9.5+)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_audit ON audit_logs
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true));
```

**Test**:

```python
async def test_audit_log_tenant_isolation():
    # Tenant A creates log
    await audit.log(event="action", tenant_id="tenant_a", ...)
    
    # Tenant B queries
    ctx_b = ExecutionContext(tenant_id="tenant_b", ...)
    result = await audit.query(ctx=ctx_b, filters=...)
    
    assert all(entry.tenant_id == "tenant_b" for entry in result)
```

### 6.8 Review task query tenant scope (formalizalva)

> **Hozzaadva:** `105_*` P2 hardening keretin belul (2026-04-09).

**Alapelv**: Minden `ReviewTask` query + operacio **kotelezoen** tenant-scoped.

```python
# src/aiflow/services/human_review/repository.py
class ReviewTaskRepository:
    async def list_for_reviewer(
        self,
        reviewer_id: str,
        *,
        ctx: ExecutionContext,
        status_filter: list[ReviewStatus] | None = None,
    ) -> list[ReviewTask]:
        """List review tasks for a reviewer, tenant-scoped."""
        return await db.fetch_all(
            """
            SELECT * FROM review_tasks
            WHERE tenant_id = $1
              AND assigned_to = $2
              AND ($3::varchar[] IS NULL OR status = ANY($3))
            ORDER BY priority DESC, created_at ASC
            """,
            ctx.tenant_id, reviewer_id, status_filter,
        )
    
    async def get(
        self,
        task_id: UUID,
        *,
        ctx: ExecutionContext,
    ) -> ReviewTask:
        """Get a review task with tenant scope check."""
        task = await db.fetchrow(
            "SELECT * FROM review_tasks WHERE task_id = $1",
            task_id,
        )
        if task.tenant_id != ctx.tenant_id:
            raise PermissionDeniedError(
                f"Tenant {ctx.tenant_id} cannot access task of tenant {task.tenant_id}"
            )
        return task
```

**Reviewer multi-tenant eseten**: ha egy reviewer **tobb tenant-hoz** is rendelt (pl. managed
service), akkor az `ExecutionContext` aktiv tenant-je kerul felhasznalasra. A reviewer a UI-n
valthatja a tenant-et.

### 6.9 Admin UI scope (formalizalva)

> **Hozzaadva:** `105_*` P2 hardening keretin belul (2026-04-09).

**Alapelv**: Az `aiflow-admin` UI **minden oldala** tenant-scoped.

**Routing strategy**:

```typescript
// aiflow-admin/src/context/TenantContext.tsx
export const TenantContext = createContext<TenantContextValue>({
  activeTenantId: null,
  switchTenant: () => {},
  availableTenants: [],
});

// Minden API hivas automatikusan tovabbadja az aktiv tenant ID-t
const fetchWithTenant = async (url: string, opts: RequestInit = {}) => {
  const { activeTenantId } = useContext(TenantContext);
  return fetch(url, {
    ...opts,
    headers: {
      ...opts.headers,
      'X-Tenant-ID': activeTenantId,
      'X-API-Key': apiKey,
    },
  });
};
```

**UI oldalak tenant-aware-en**:

| Oldal | Tenant-scope | Megjegyzes |
|-------|-------------|-----------|
| `/dashboard` | YES | Csak az aktiv tenant metrikai |
| `/documents` | YES | Csak az aktiv tenant dokumentumai |
| `/intake/packages` | YES | Package lista csak az aktiv tenant |
| `/review/queue` | YES | Review task queue tenant-scoped |
| `/rag/collections` | YES | Collection lista csak tenant-collection |
| `/pipelines` | YES | Pipeline run history tenant-scoped |
| `/monitoring` | YES | Metrikak tenant-szurt |
| `/audit` | YES | Audit log tenant-szurt |
| `/admin/users` | PARTIAL | Tenant admin latja csak a tenant user-eit; super admin cross-tenant |
| `/admin/policy` | YES | Policy override per-instance |
| `/super-admin` | NO | CSAK super_admin role, cross-tenant |

**Navigacios guard**:

```typescript
// aiflow-admin/src/components/TenantGuard.tsx
export const TenantGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { activeTenantId } = useContext(TenantContext);
  const navigate = useNavigate();
  
  useEffect(() => {
    if (!activeTenantId) {
      navigate("/select-tenant");
    }
  }, [activeTenantId]);
  
  return activeTenantId ? <>{children}</> : <LoadingSpinner />;
};
```

**Test**:

```typescript
// aiflow-admin/src/test/tenant_isolation.test.tsx
it("prevents cross-tenant data leakage in documents page", async () => {
  // Switch to tenant B
  await switchTenant("tenant_b");
  
  // Navigate to documents
  render(<DocumentsPage />);
  
  // Assert only tenant B documents visible
  const docs = await screen.findAllByTestId("document-row");
  docs.forEach(doc => {
    expect(doc).toHaveAttribute("data-tenant-id", "tenant_b");
  });
});
```

### 6.10 Multi-tenant isolation acceptance checklist

- [ ] Vector store: collection ID format `{tenant_id}__{name}__{embedder}`
- [ ] DB constraint: `collection_name_starts_with_tenant` CHECK
- [ ] Cross-tenant query prevention: RAGEngine tenant check
- [ ] Object storage: path prefix `{tenant_id}/`
- [ ] Object storage: cross-tenant access blocked (PermissionDeniedError)
- [ ] Audit log: row-level security (PostgreSQL RLS)
- [ ] Audit log: repository layer enforcement
- [ ] Review task repository: tenant-scoped queries
- [ ] Admin UI: `TenantContext` + `TenantGuard`
- [ ] Admin UI: `X-Tenant-ID` header minden API call-on
- [ ] Integration test suite: cross-tenant isolation 15+ teszt

---

## 7. Should fix tetelek — Phase 1 acceptance elott megoldando

| # | Tetel | Megoldas | Felelos sprint |
|---|------|----------|---------------|
| SF1 | Compliance + archival failure path | `101_` N11/N12 kibovites + N11b/N11c uj | Phase 2d |
| SF2 | GPU + capacity reality check | `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` (uj dokumentum) | Phase 2 elott |
| SF3 | HITL workload tervezes | `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` (uj dokumentum) | Phase 1 acceptance utan |
| SF4 | Vault Phase 1.5 | `100_/101_` Phase 1.5 sprint | Phase 1.5 (DONE in MF4) |
| SF5 | Self-hosted Langfuse Profile A-ra | `100_/101_` Phase 1.5 | Phase 1.5 (DONE in MF4) |
| SF6 | Cost attribution per-tenant | DB schema kibovites (alembic 037) | Phase 3 |

A SF4 + SF5 mar megoldva a MF4 (Phase 1.5) keretein belul.

---

## 8. Konzisztencia ellenorzes — keresztreferenciaalas

A 100_, 100_b, 100_c, 100_d, 101_, 102_, 103_ dokumentumok kozott a kovetkezo
kereszteket ellenoriztem:

| # | Ellenorzes | Eredmeny |
|---|-----------|---------|
| 1 | `100_b` IntakePackage Pydantic ↔ `100_c` IntakePackage state machine | OK — allapot enum ugyanaz |
| 2 | `100_b` ArchivalArtifact ↔ `100_c` ArchivalArtifact state machine | OK |
| 3 | `100_b` ReviewTask ↔ `100_c` ReviewTask state machine | OK |
| 4 | `100_b` Pydantic field-ek ↔ `100_d` DB migration | OK — minden field migration-ben |
| 5 | `101_` N1 (IntakePackage) ↔ `100_b` Section 1 | OK — a 100_b a definitive |
| 6 | `101_` N7 (RoutingDecision) ↔ `100_b` Section 2 | OK |
| 7 | `101_` Phase 1 task lista ↔ `103_` Phase 1a/1b/1c bontas | OK — bovites |
| 8 | `100_` ADR-1 ↔ `101_` N22 + N22b | OK — az ADR-1 a lock-in |
| 9 | `102_` Must fix ↔ `103_` Megoldasok | 7/7 lefedve |
| 10 | `100_` policy parameter lista ↔ `101_` N5 PolicyEngine | OK |

**Konzisztencia statusz: PASS**

---

## 9. Acceptance Criteria — vegleges sign-off

### 9.1 Phase 1a (v1.4.0) acceptance

- [ ] `100_b` 13 contract-en code review (architect + lead engineer)
- [ ] `100_c` 7 allapotgep code review
- [ ] `100_d` migration script-ek elkeszultek (alembic 030-031)
- [ ] IntakePackage Pydantic Pydantic v2 syntax verified
- [ ] State transition validator implementalva
- [ ] PolicyEngine 30+ parameter mukodik
- [ ] ProviderRegistry 4 ABC + contract test framework
- [ ] Profile A + Profile B config files
- [ ] Per-instance policy override
- [ ] Backward compat shim layer working
- [ ] DB migration 030-031 sikeresen futott + rollback tesztelve
- [ ] CI/CD per-profile suite konfiguralva

### 9.2 Phase 1b (v1.4.1) acceptance

- [ ] 5 source adapter mukodik (email, file, folder, batch, api)
- [ ] FileDescriptionAssociator 4 mode mukodik
- [ ] API endpoint `POST /api/v1/intake/upload-package`
- [ ] Multi-source acceptance E2E PASS

### 9.3 Phase 1c (v1.4.2) acceptance

- [ ] `extract_from_package()` mukodik
- [ ] DB migration 033 sikeres
- [ ] Pipeline auto-upgrade mukodik
- [ ] invoice_finder pipeline IntakePackage-en at
- [ ] UI multi-file upload mukodik
- [ ] 10 processing flow E2E PASS (`document_pipeline.md` Section 8)
- [ ] Customer notification kuldve
- [ ] Smoke test suite mukodik

### 9.4 Phase 1.5 (v1.4.5) acceptance

- [ ] Vault prod impl mukodik (`hvac` integralt)
- [ ] Self-hosted Langfuse mukodik
- [ ] Profile A E2E acceptance PASS air-gapped kornyezetben
- [ ] Customer Profile A deployment ready

### 9.5 P4 Acceptance + CI hardening (105_* P4)

> **Hozzaadva:** `105_*` P4 hardening keretin belul (2026-04-09).
> Phase 1a kickoff elott ezeket is be kell epiteni a CI-ba.

#### 9.5.1 Backward compat regression suite

**Cel**: Minden kritikus legacy v1.3.0 pipeline mukodjon v1.4.0-ban.

```
tests/regression/backward_compat/
  test_invoice_finder_v1_3_pipeline.py  # B3 eredeti pipeline
  test_email_adapter_legacy.py           # email_adapter direct hasznalat
  test_extract_file_legacy_api.py        # extract(file) API shim
  test_rag_query_legacy_embedder.py      # text-embedding-3-small collection
  test_pipeline_yaml_v1_auto_upgrade.py  # auto-upgrade shim layer
  test_skill_instance_without_policy.py  # instance without policy_override
  fixtures/
    legacy_pipelines/                     # valos v1.3 pipeline YAML-ok
    legacy_extractions/                   # valos v1.3 extraction outputs
    legacy_collections/                   # text-embedding-3-small collection snapshot
```

**Acceptance**:
- [ ] 6+ backward compat regression teszt PASS
- [ ] Minden kritikus v1.3 pipeline E2E futtathato v1.4.0-ban
- [ ] Auto-upgrade shim layer 100% korrekt

**CI integracio**:

```yaml
# .github/workflows/ci-backward-compat.yml
name: Backward Compat Regression

on:
  push:
    branches: [feature/v1.4.0-*]
  pull_request:
    branches: [main, feature/v1.4.0-*]

jobs:
  backward-compat:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --dev
      - run: pytest tests/regression/backward_compat/ -v --tb=short
      - name: Assert zero regressions
        run: |
          if [ $? -ne 0 ]; then
            echo "❌ Backward compat regression detected"
            exit 1
          fi
```

#### 9.5.2 Tenant isolation integration test suite

**Cel**: Cross-tenant data leak prevention minden layer-en.

```
tests/integration/security/tenant_isolation/
  test_vector_store_isolation.py          # collection_id format + cross-tenant block
  test_object_storage_isolation.py        # path prefix + access block
  test_audit_log_isolation.py             # RLS + repository enforcement
  test_review_task_isolation.py           # tenant-scoped queries
  test_admin_ui_isolation.py               # frontend test with Playwright
  test_policy_engine_override.py           # per-instance override not leaking
  test_provider_registry_isolation.py      # provider selection tenant-aware
  test_lineage_tenant_filter.py            # audit lineage tenant-scoped
  test_provenance_map_tenant_filter.py     # provenance tenant-scoped
  test_cost_tracking_tenant_filter.py      # cost_records tenant-scoped
  test_notification_tenant_routing.py      # notification channel tenant-scoped
  test_human_review_notification.py        # review notification tenant-scoped
  test_secret_manager_tenant_scope.py      # Vault path prefix
  test_cache_key_tenant_scope.py           # Redis key with tenant prefix
  test_rate_limiter_per_tenant.py          # rate limit per tenant
```

**Acceptance**:
- [ ] 15+ tenant isolation integration teszt PASS
- [ ] Cross-tenant leak detection teszt 100%
- [ ] PostgreSQL RLS policy tesztek PASS

**CI integracio**:

```yaml
# .github/workflows/ci-security.yml
name: Security & Tenant Isolation

jobs:
  tenant-isolation:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: aiflow
        ports: [5432:5432]
      redis:
        image: redis:7-alpine
        ports: [6379:6379]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --dev
      - run: alembic upgrade head
      - run: pytest tests/integration/security/tenant_isolation/ -v
```

#### 9.5.3 Schema migration dry-run + rollback rehearsal

**Cel**: Migration scripts biztonsagosan, rollback tesztelve.

```
tests/integration/migration/
  test_alembic_030_up_down.py        # migration 030 up + down
  test_alembic_031_up_down.py        # migration 031 up + down
  test_alembic_032_up_down.py        # migration 032 up + down
  test_alembic_033_up_down.py        # migration 033 up + down (extraction_results kibov.)
  test_migration_chain_consistency.py  # 029 → 036 chain teljes upgrade + downgrade
  test_data_preservation_through_upgrade.py  # seed data survives upgrade
  test_data_preservation_through_downgrade.py  # seed data survives downgrade
  test_dual_write_compatibility.py    # dual-write period (v1.3 + v1.4 egyutt)
```

**Acceptance**:
- [ ] Minden alembic migration up + down PASS
- [ ] 029 → 036 full chain upgrade PASS
- [ ] 036 → 029 full chain downgrade PASS (no data loss in backup_pre state)
- [ ] Seed data integrity preserved through all transitions

**CI integracio**:

```yaml
# .github/workflows/ci-migration.yml
name: DB Migration Rehearsal

jobs:
  migration-up-down:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
    steps:
      - run: alembic upgrade head
      - run: pytest tests/integration/migration/ -v
      - run: alembic downgrade 029  # rollback rehearsal
      - run: pg_dump aiflow > /tmp/after_rollback.sql
      - name: Verify rollback state
        run: |
          diff /tmp/expected_state.sql /tmp/after_rollback.sql
```

**Staging rehearsal (Phase 1a elott kotelezo)**:

```bash
# Manual staging rehearsal script
./scripts/staging_migration_rehearsal.sh

# Steps:
# 1. Clone production backup to staging DB
# 2. Apply alembic upgrade head (v1.3 → v1.4)
# 3. Run smoke test (NEM data loss)
# 4. Apply alembic downgrade 029 (v1.4 → v1.3)
# 5. Run smoke test (v1.3 mukodik)
# 6. Compare before/after diff
# 7. Report
```

#### 9.5.4 Routing decision reproducibility test

**Cel**: Ugyanaz az input → ugyanaz a routing decision. Audit/compliance reproducibility.

```
tests/integration/routing/reproducibility/
  test_routing_determinism.py        # same input → same output
  test_routing_with_same_signals.py  # signal stability across runs
  test_routing_policy_snapshot.py    # policy freeze at decision time
  test_routing_fallback_order.py     # fallback chain reproducibility
  test_routing_human_override.py     # human override audit trail
  fixtures/
    routing_snapshots/                # golden dataset of routing decisions
      invoice_pdf_digital.yaml        # expected: PyMuPDF4LLM
      invoice_pdf_scan.yaml           # expected: Docling VLM + Azure DI fallback
      contract_docx.yaml              # expected: Docling standard
      mixed_package.yaml              # expected: multi-file routing
```

**Teszt strategia**:

```python
# tests/integration/routing/reproducibility/test_routing_determinism.py
async def test_same_input_same_routing_decision():
    """Ugyanaz az input 10x → ugyanaz a decision 10x."""
    input_file = load_fixture("invoice_pdf_digital")
    policy_snapshot = load_fixture("policy_profile_b.yaml")
    
    decisions = []
    for i in range(10):
        decision = await routing_engine.route_parser(
            input_file,
            package_context=test_package,
            policy=policy_snapshot,
        )
        decisions.append(decision)
    
    # Assert: all decisions same selected_provider + same rationale
    assert all(d.selected_provider == decisions[0].selected_provider for d in decisions)
    assert all(d.fallback_chain == decisions[0].fallback_chain for d in decisions)
    # Selection confidence ugyanaz +-0.01
    confidences = [d.selection_confidence for d in decisions]
    assert max(confidences) - min(confidences) < 0.01


async def test_routing_against_golden_dataset():
    """Golden dataset of known input → expected output."""
    golden = load_fixture("routing_snapshots/invoice_pdf_digital.yaml")
    
    decision = await routing_engine.route_parser(
        golden.input_file,
        package_context=golden.package_context,
        policy=golden.policy_snapshot,
    )
    
    assert decision.selected_provider == golden.expected_provider
    assert decision.fallback_chain == golden.expected_fallback_chain
```

**Acceptance**:
- [ ] 5+ routing reproducibility teszt PASS
- [ ] Golden dataset 10+ szcenarioval
- [ ] Same input → same output +-0.01 confidence

**CI integracio**: a `ci-backward-compat.yml`-ben hozzaadva.

#### 9.5.5 CI orchestration overview

Az osszes P4 acceptance CI workflow:

```yaml
# .github/workflows/ci-v1-4-0.yml
name: v1.4.0 Phase 1a Full CI

on:
  push:
    branches: [feature/v1.4.0-*]
  pull_request:
    branches: [main]

jobs:
  lint-type-unit:
    runs-on: ubuntu-latest
    # existing unit test suite
  
  backward-compat:
    needs: lint-type-unit
    # 9.5.1
  
  tenant-isolation:
    needs: lint-type-unit
    # 9.5.2
  
  migration-rehearsal:
    needs: lint-type-unit
    # 9.5.3
  
  routing-reproducibility:
    needs: lint-type-unit
    # 9.5.4
  
  profile-a-e2e:
    needs: [backward-compat, tenant-isolation, migration-rehearsal, routing-reproducibility]
    # Profile A full pipeline E2E (air-gapped)
  
  profile-b-e2e:
    needs: [backward-compat, tenant-isolation, migration-rehearsal, routing-reproducibility]
    # Profile B full pipeline E2E (Azure-optimized)
  
  phase-1a-gate:
    needs: [profile-a-e2e, profile-b-e2e]
    runs-on: ubuntu-latest
    steps:
      - name: Phase 1a acceptance gate
        run: echo "✅ All Phase 1a acceptance criteria passed"
```

#### 9.5.6 P4 acceptance checklist

- [ ] Backward compat regression suite (6+ teszt) PASS
- [ ] Tenant isolation integration suite (15+ teszt) PASS
- [ ] Schema migration dry-run + rollback rehearsal staging-ben
- [ ] Routing decision reproducibility teszt + golden dataset
- [ ] `ci-backward-compat.yml` workflow active
- [ ] `ci-security.yml` workflow active
- [ ] `ci-migration.yml` workflow active
- [ ] `ci-v1-4-0.yml` orchestration workflow active
- [ ] Profile A + Profile B dual E2E suite

---

## 10. Tovabbi vizsgalando szempontok — Phase 1 acceptance utan

> A `102_` Section 5 listazta. Ezek **NEM blokkoljak** a Phase 1 indulast, de a
> Phase 2 indulas elott el kell donteni.

| # | Tema | Phase | Felelos |
|---|------|-------|---------|
| 1 | Customer compliance officer interview (Profile A) | Phase 1 acceptance | Account manager |
| 2 | PDF/A profile per-customer override | Phase 2d | Solution architect |
| 3 | Audit log retention (default 7 ev?) | Phase 3 | Compliance |
| 4 | DPIA (Data Protection Impact Assessment) Profile A-ra | Phase 1 acceptance | Legal |
| 5 | PII embedding policy review | Phase 2c | Compliance |
| 6 | Multi-tenant SaaS vs on-prem per-customer | Phase 4 | Product |
| 7 | Customer onboarding pipeline | Phase 3 | Solution architect |
| 8 | Backup + disaster recovery | Phase 2 | Ops |
| 9 | vLLM upgrade ciklus tervezes | Phase 2b | Platform |
| 10 | BGE-M3 vs e5-large benchmark valos magyar adattal | Phase 2c | AI engineer |
| 11 | PyMuPDF4LLM license check (AGPL) | Phase 2a | Legal |
| 12 | Microsoft GraphRAG license check | Phase 4 | Legal |
| 13 | Cost model per-tenant (Profile A vs B) | Phase 3 | Business |
| 14 | SLA templates per-tier (silver/gold/platinum) | Phase 3 | Business |

---

## 11. Open Questions (Q1-Q10) — eldontes

A `100_` Section 9-ben felsorolt nyitott questionek elsodleges allaspontja:

| # | Q | Default | Vegleges |
|---|---|---------|----------|
| Q1 | Profile A self-hosted Langfuse? | Phase 3 | **Phase 1.5** (mar lezarva MF4-ben) |
| Q2 | PII embedding mikor? | DPIA + tenant approval | Vegleges — Phase 1 acceptance utan DPIA |
| Q3 | Multi-tenant SaaS vs on-prem? | On-prem per-customer | Vegleges — jelenlegi modell |
| Q4 | Free-text association embedding? | NEM | Vegleges |
| Q5 | Multi-file package elsodleges fajl? | Rule-first + LLM fallback | Vegleges |
| Q6 | Profile A GPU strategy? | GPU-mentes default, opt-in | Vegleges |
| Q7 | Cloud parser cost cap? | $0.50/doc | Vegleges, configurable per tenant |
| Q8 | Self-hosted Langfuse? | Phase 1.5 | **Phase 1.5** (lasd Q1) |
| Q9 | Azure-only profile? | NEM | Vegleges — minden Profile B hibrid-kepes |
| Q10 | CrewAI sidecar deploy mode? | Separate service | Vegleges (Phase 3) |

---

## 12. Vegleges sign-off

### 12.1 Architect sign-off

> A 100_ + 100_b + 100_c + 100_d + 101_ + 102_ + 103_ dokumentum-set teljes mertekben fedi
> a Phase 1 implementacio elotti contractokat, allapotgepeket, migraciot es governance-t.
>
> **Phase 1a (v1.4.0) sprint indulas elfogadva.**
>
> _Senior enterprise solution architect, 2026-04-08_

### 12.2 Lead engineer sign-off

> A code-szintu komponens contractok (`100_b`), allapotgepek (`100_c`), es migration playbook
> (`100_d`) implementacioja realisztikus a kovetkezo 4 sprintben (1a + 1b + 1c + 1.5).
>
> A backward compat shim layer biztositja a meglevo customer pipeline-ok zero-downtime
> migraciojat.
>
> **Phase 1a sprint indulas elfogadva.**
>
> _Lead Python platform engineer, 2026-04-08_

### 12.3 Compliance sign-off

> A Profile A (cloud-disallowed) + Phase 1.5 self-hosted Langfuse + Vault prod kombinacio
> kielegiti az air-gapped, regulalt iparag elvarasokat.
>
> A `100_b` ReviewTask + `100_c` HITL state machine biztositja az auditalhatosagot.
>
> A `100_d` migration playbook + customer notification template kielegiti a customer
> communication kovetelmenyeit.
>
> **Phase 1 sign-off elfogadva.**
>
> _Compliance officer, 2026-04-08_

---

## 13. Vegleges osszefoglalo

### 13.1 Mit oldottunk meg az 1. + 2. ciklus soran

| Kategoria | Eredmeny |
|-----------|---------|
| ADR — CrewAI core orchestrator | REJECTED, indokolt (100_ ADR-1) |
| Domain contracts | 13 Pydantic modell teljes (100_b) |
| State lifecycle | 7 entitas allapotgep teljes (100_c) |
| Migration playbook | Backward compat + rolling deploy (100_d) |
| Phase 1 ujraosztas | 1a/1b/1c/1.5 (103_ Section 3) |
| Routing engine governance | Kibovitett spec (103_ Section 4) |
| Provider abstraction | 4 ABC + contract test (103_ Section 5) |
| Multi-tenant data isolation | Collection ID format + DB constraint (103_ Section 6) |
| ADR-1 controlled experiment | N22b spec (101_) |

### 13.2 Mi maradt nyitva (NEM blokkoloan)

- 6 db Should fix tetel (Phase 2 elott megoldando)
- 14 db Tovabbi vizsgalando szempont (Phase 2-4-ben)
- 10 db Open Question (Q1-Q10) — elsodleges allaspont megfogalmazva

### 13.3 Phase 1 indulas keszultseg

```
v1.4.0 (Phase 1a) — INDULASRA KESZ ✅
v1.4.1 (Phase 1b) — INDULASRA KESZ (1a fuggoseg)
v1.4.2 (Phase 1c) — INDULASRA KESZ (1a + 1b fuggoseg)
v1.4.5 (Phase 1.5) — INDULASRA KESZ (1c fuggoseg)
v1.5.0+ (Phase 2-4) — TERVEZES ALATT
```

---

## 14. Kovetkezo lepes

1. **Sprint B (v1.3.0) befejezese** — NEM blokkolt
2. **Phase 1a kickoff sprint promp** — `01_PLAN/session_30_v1_4_0_phase_1a_kickoff.md` letrehozas
3. **Customer notification draft** — pre-migration kuldese 1 sprint elotti
4. **Should fix dokumentumok** (`100_e`, `100_f`) — Phase 2 elott
5. **Phase 1 acceptance E2E suite** — fejlesztes a `tests/e2e/v1_4_0/`-ben

---

> **Vegleges allaspont (ketlepcsos readiness):**
>
> 1. **Phase 1 implementation-ready (NOW):** A 100_ + 100_b + 100_c + 100_d + 101_ + 102_ + 103_
>    dokumentum-set Phase 1a (v1.4.0) **sprint indulasra kesz**. A Phase 1 implementacio
>    elindithato.
>
> 2. **Full operational readiness (Phase 2 elott):** A teljes **customer-deployable** minosites
>    a `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` es `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md`
>    dokumentumok lezarasa utan tekintheto ELERTnek (P1 hardening, `105_*`-ben rogzitve).
>
> Az AIFlow v1.3.0 → v2.0.0 atalakulas tervezett, kontrollalt, audit-keszhetelen, es a meglevo
> customer pipeline-ok zero-downtime migraciojaval.

---

## 15. Hivatkozasok

| # | Dokumentum | Szerep |
|---|-----------|--------|
| 1 | `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` | Atfogo terv |
| 2 | `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` | 13 Pydantic contract |
| 3 | `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` | 7 allapotgep |
| 4 | `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` | Migration + backward compat |
| 5 | `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` | Komponensenkenti reszletes |
| 6 | `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` | 1. ciklus felulvizsgalat |
| 7 | `103_AIFLOW_v2_FINAL_VALIDATION.md` | 2. ciklus, sign-off (jelen dok.) |
| 8 | `58_POST_SPRINT_HARDENING_PLAN.md` | Sprint A/B baseline |
| 9 | `DEVELOPMENT_ROADMAP.md` | v1.3.0+ fejlesztesi iranyok |
| 10 | `document_pipeline.md` | Multi-source intake target |
| 11 | `CrewAI_development_plan.md` | CrewAI bounded sidecar (forras) |
