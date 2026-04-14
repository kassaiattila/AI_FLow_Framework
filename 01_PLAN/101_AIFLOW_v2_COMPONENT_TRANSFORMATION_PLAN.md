# AIFlow v2 — Component Transformation Plan (Reszletes)

> **Verzio:** 2.0 (FINAL — ELFOGADVA)
> **Datum:** 2026-04-09
> **Statusz:** ELFOGADVA (SIGNED OFF) — `103_*` 2. ciklus utan
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
> **Szulo:** `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md`
> **Kotelezo kiegeszito:** `100_b_*` (contracts) + `100_c_*` (state) + `100_d_*` (migration)
> **Felulvizsgalatok:** `102_*` (1. ciklus) → `103_*` (2. ciklus + sign-off + kibovitesek)
>
> **Valtozas naplo:**
> - **v2.0 (2026-04-09):** Status "TERVEZET" → "ELFOGADVA". A 102_* Must fix tetelek
>   (MF5 routing governance, MF6 provider ABC, MF7 multi-tenant isolation) kibovitesei
>   a `103_*` Section 4-6-ban találhatok; innen hivatkozott. Phase 1 bontas 1a/1b/1c/1.5
>   a `103_*` Section 3-ban.
> - **v1.0 (2026-04-08):** initial draft, N22b CrewAI experiment hozzaadva ADR-1 alapjan.

> **Forma:** Komponensenkent egyseges szerkezet:
> 1. Komponens azonosito (`R1`, `N1`, `K1`, ...)
> 2. Jelenlegi allapot (file path, sor, mit csinal)
> 3. Cel allapot
> 4. Technologiai indoklas
> 5. Funkcionalis indoklas
> 6. Lepesenkenti vegrehajtasi terv
> 7. Dependencies (mas komponens fuggosegei)
> 8. Risk
> 9. Acceptance criteria
>
> **FONTOS:** A 101_ a komponensenkenti **implementacios reszletek** forrasa. A `103_*`
> Section 4-6 kibovitesei **ITT hivatkozottak**, es az ottani reszletek definitive-ek
> a governance / contract / isolation kerdesekben.

---

## REFINEMENT KOMPONENSEK (R-szeria)

---

### R1 — `services/email_connector` → IntakeSourceAdapter wrapping

**Komponens azonosito:** R1
**Phase:** 1
**Komplexitas:** S (kicsi-kozepes)
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/services/email_connector/service.py` (1271 sor)
- **Funkcio:** IMAP + Outlook COM kapcsolat, email fetch, csatolmany kivonas
- **Hasznalat:** kozvetlenul a `pipeline/adapters/email_adapter.py`-bol hivva
- **Korlat:** csak email source. Nincs unified intake, file upload / folder / batch nem on this path

#### Cel allapot

- A `services/email_connector` MARAD low-level fetcher (IMAP/COM/Graph API jovobeli protokol)
- A `pipeline/adapters/email_adapter.py` MARAD pipeline-step adapter
- UJ wrapper: `src/aiflow/intake/source_adapters/email_source.py`
  - `IntakeSourceAdapter` interface implementacio
  - Wrappeli a `services/email_connector` low-level fetcher-t
  - Vissza `IntakePackage` objektumokat ad (NEM `FetchedEmail`)
  - Az **Unstructured OSS** parser-t hasznalja a body + EML/MSG + csatolmany egyseges parsolasara
- Jovoben (Phase 2+): tobb source adapter ugyanaz interface-en keresztul (`file_source.py`, `folder_source.py`, `batch_source.py`, `api_source.py`)

#### Technologiai indoklas

- A `document_pipeline.md` rogzitett iranya: **Unstructured OSS** az email intake-re
- A jelenlegi `email_parser.py` (`tools/email_parser.py`) ad-hoc — Unstructured egysegesen kezeli az EML/MSG/HTML body-t
- A wrapper minta NEM toroli a meglevot, csak provider-szeruen kapcsolja
- Az Unstructured a meglevo `pyproject.toml`-ban opcionalis dep, mar elerheto (`rag-ocr` extra)

#### Funkcionalis indoklas

- A multi-source intake elve nem teszi lehetove, hogy a pipeline-okban kulonbozo source-okra (email, file, folder) **kulonbozo step-eket** kelljen irni
- IntakePackage egyseges DOM modell — minden downstream step (parser routing, classifier, extractor) a package-en dolgozik
- Email body context propagacio: a body szovege **forrasszovegkent** atmegy a parser routing es a downstream extraction-ra (pl. szamla email body altal kontextusban)

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/intake/__init__.py` + `intake/source_adapters/__init__.py`
2. **Definialj**: `intake/source_adapters/base.py:IntakeSourceAdapter` ABC
   - Metodusok: `discover() → list[IntakeSourceItem]`, `fetch(item) → IntakePackage`, `health_check()`
3. **Implementald**: `intake/source_adapters/email_source.py:EmailIntakeSourceAdapter`
   - Konstruktor: `(email_connector_service: EmailConnectorService, unstructured_parser: UnstructuredEmailParser)`
   - `fetch()` hivja a `email_connector.fetch_email()`-t, majd `unstructured_parser.parse_eml()`-t
   - Vissza `IntakePackage(source="email", files=[...], free_text=email_body, metadata={from, subject, date, ...})`
4. **Bovitsd ki**: `tools/email_parser.py` -> ujraindit Unstructured-tel (`from unstructured.partition.email import partition_email`)
5. **Tesztels**: `tests/unit/intake/test_email_source.py` — 5+ teszt:
   - happy path EML parsolas
   - csatolmany kivonas
   - body context megjelenes az IntakePackage-ben
   - error handling (invalid EML)
   - Outlook COM fallback meg mukodik
6. **Refaktor**: `pipeline/adapters/email_adapter.py` hasznaja az uj `EmailIntakeSourceAdapter`-t (NEM kozvetlenul az email_connector-t)
7. **Migration helper**: `scripts/migrate_email_pipeline_to_intake.py` a meglevo pipeline YAML-ek kompatibilitasi check-ja
8. **Dokumentacio**: `intake/README.md` az adapter pattern-rol

#### Dependencies

- `intake/package.py` (N1) — IntakePackage modell letre kell letre **elotte**
- `intake/normalization.py` (N3) — Az email source kimeneten kell normalize-olni
- `tools/email_parser.py` — Unstructured-re cserelve

#### Risk

- **Outlook COM kompatibilitas:** Az Unstructured az MSG-t parsolja, de a COM-alapu fetch megmaradhat csak a Sprint B B3-ban hardenizalt formaban
- **Body kodolas:** Magyar UTF-8 encoding edge-cases — Unstructured nem mindig perfect → fallback `tools/email_parser.py`-ra
- **Performance:** Unstructured lassabb az ad-hoc parsernel — meresre szuksegunk van

#### Acceptance criteria

- [ ] `IntakeSourceAdapter` interface definialva, ABC-vel
- [ ] `EmailIntakeSourceAdapter` mukodik (5+ unit teszt PASS)
- [ ] Pipeline `email_adapter.py` hasznaja az uj wrappert
- [ ] Existing E2E (B3 Invoice Finder) NEM regreszal
- [ ] IntakePackage tartalmazza body + csatolmanyok + metadata-t

---

### R2 — `ingestion/parsers/docling_parser.py` mint multi-parser routing 1 reteg

**Komponens azonosito:** R2
**Phase:** 2
**Komplexitas:** S (interface adaptacio)
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/ingestion/parsers/docling_parser.py` (366 sor)
- **Funkcio:** Univerzalis dokumentum parser (PDF/DOCX/PPTX/XLSX/HTML/images)
- **Hasznalat:** Hardcoded a `services/document_extractor`, `services/advanced_parser` keruleteben
- **Korlat:** Egyetlen parser, nem optimalis fast / hard / scan path-ra

#### Cel allapot

- DoclingParser MARAD valtozatlanul — egyik **reteg** a routing engine alatt
- Refaktor: `parser_factory.py` (N6 provider registry-vel egyutt) regisztralja a `docling_standard` providert
- A meghivasi pont a `routing/multi_signal_router.py`-bol jon, NEM kozvetlenul `services/*`-bol
- A jelenlegi 3-retegu fallback (Docling → Azure DI → pypdfium2) a routing engine konfiguracios policy-jeban kerul

#### Technologiai indoklas

- DoclingParser kompetens a `document_pipeline.md`-ben rogzitett "Docling standard pipeline" szerepre
- NEM kell csere — csak a `default_parser` szerepe nincs hardcoded-olva
- A multi-signal routing engine donti el, melyik path: `pymupdf4llm_fast`, `docling_standard`, `docling_vlm`, `azure_di`, `qwen25_vl`

#### Funkcionalis indoklas

- Single parser nem optimalis: born-digital PDF gyors path-on (PyMuPDF4LLM), scan + handwriting Azure DI / Docling VLM, complex layout Docling standard
- Audit-trail: minden parser dontes tanusit (ki dontotte, miert)

#### Lepesenkenti vegrehajtas

1. **Bovits**: `ingestion/parsers/docling_parser.py:DoclingParser` egy `Provider` osztaly metodusait kapja meg:
   - `name = "docling_standard"`
   - `supported_types = ["pdf", "docx", "pptx", "xlsx", "html", "image"]`
   - `signals_priority = {"text_layer": 0.5, "table_susp": 1.0, "ocr_need": 0.7, ...}`
2. **Regisztracio**: `providers/registry.py:ProviderRegistry.register_parser("docling_standard", DoclingParserProvider)`
3. **Routing engine integracio**: `routing/multi_signal_router.py` lekeri a `provider_registry.list_parsers()`-t
4. **Tests**: `tests/unit/ingestion/test_docling_parser_provider.py` regisztracio + invokacios teszt
5. **Backwards compat**: a meglevo `services/document_extractor` modositott `parser_provider="docling_standard"` config-gal hivja, NEM kozvetlenul `DoclingParser()`-rel

#### Dependencies

- `providers/registry.py` (N6) elso
- `routing/multi_signal_router.py` (N7) elso

#### Risk

- **Backwards compat:** a meglevo kod direkt `DoclingParser()` hivasokra epul — refaktor szuksegen, de kicsi
- **Test coverage**: meglevo Docling tesztek nem szakadnak meg

#### Acceptance criteria

- [ ] DoclingParser `Provider` interface-t implementalja
- [ ] `provider_registry.get_parser("docling_standard")` mukodik
- [ ] `routing/multi_signal_router.py` valaszthatja
- [ ] Existing tests PASS

---

### R3 — `tools/azure_doc_intelligence.py` mint generic ParserProvider

**Komponens azonosito:** R3
**Phase:** 2
**Komplexitas:** S
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/tools/azure_doc_intelligence.py`
- **Funkcio:** Async REST kliens Azure Document Intelligence-hez
- **Hasznalat:** `tools/attachment_processor.py:77-187` minoseg-alapu routing-bol hivva, hardcoded fallback
- **Korlat:** NEM provider registry resze, hardcoded a Docling utan kovetkezo lepesnek

#### Cel allapot

- Wrappolas: `providers/parsers/azure_di_provider.py:AzureDIParserProvider`
- Implementalja a `Provider` interface-t (R2 minta)
- Csak akkor lett available, ha `policy.azure_di_enabled = true` (PolicyEngine donti el)
- A routing engine valasztja, NEM az `attachment_processor.py`

#### Technologiai indoklas

- A `document_pipeline.md` rogzitett iranya: Azure DI mint **provider, NEM domain modell** vagy hardcoded path
- Profile A-ban TILOS hasznalni — a PolicyEngine kizarja
- Profile B-ben opcionalis (tenant override eldonti)

#### Funkcionalis indoklas

- Tenant override: egy ugyfél engedelyezheti, mas nem
- Audit: minden Azure DI hivas RoutingDecision rekorddal jar

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/providers/parsers/__init__.py`
2. **Implementald**: `providers/parsers/azure_di_provider.py:AzureDIParserProvider`
   - Konstruktor: `(client: AzureDIClient, policy_engine: PolicyEngine)`
   - `parse(file_path, intake_context)` ellenorzi a policy-t **mielott** hivna
3. **Regisztracio**: `providers/registry.py` regisztralja `parser=azure_di` neven
4. **Refaktor**: `tools/attachment_processor.py` ne hivja kozvetlenul, csak a routing engine-en keresztul
5. **Test**: 5+ teszt, beleertve a policy `azure_di_enabled=false` blokkolas eseteit
6. **Audit hook**: minden hivas `RoutingDecision(provider="azure_di", reason="signal X", policy_check=PASS)`-t logol

#### Dependencies

- `providers/registry.py` (N6)
- `policy/engine.py` (N5)
- `routing/multi_signal_router.py` (N7)

#### Risk

- **Existing pipeline-ok**: az `azure_enabled=true` config-os pipeline-ok meg mindig hivjak az `attachment_processor`-t kozvetlenul — refactor szukseges, de a config feltétel marad
- **Cost cap**: Azure DI hivas dollar — Phase 2 acceptance-ben max-cost-per-pipeline policy

#### Acceptance criteria

- [ ] `AzureDIParserProvider` regisztralva
- [ ] Profile A futtatasban Azure DI **NEM hivodik soha** (policy block)
- [ ] Profile B-ben tenant override mukodik
- [ ] Audit log teljes

---

### R4 — `services/document_extractor` → IntakePackage centric

**Komponens azonosito:** R4
**Phase:** 1
**Komplexitas:** M (kozepes)
**Risk:** Kozepes

#### Jelenlegi allapot

- **Path:** `src/aiflow/services/document_extractor/service.py` (542 sor)
- **Funkcio:** Document type config alapu mezo extrakcio (LLM + ML)
- **Hasznalat:** `pipeline/adapters/document_adapter.py`-bol hivva
- **Korlat:** Document-centric — egyszerre 1 fajl egyszerre, nincs cross-document context, nincs free-text ingestion

#### Cel allapot

- IntakePackage-bol dolgozik (N1 modell)
- Cross-document context propagacio (`package.context`)
- Free-text association integracio (`package.descriptions`)
- Per-document type config marad (jelenlegi DocumentTypeConfig megorzendo)
- Confidence scoring per-field (B3.5 minta altalanositas — K12)

#### Technologiai indoklas

- A `51_DOCUMENT_EXTRACTION_INTENT.md` mar meghatarozta a parameterezett extraction-t — csak a package context kell hozza
- A B3.5 confidence scoring mintat ki kell terjeszteni: `extracted_fields` mellett `field_confidences` map

#### Funkcionalis indoklas

- Multi-file package: pl. szamla + szallitolevel + szerzodes egyutt jon — a kontextus erteket ad az extrakcionak
- Free-text + file: pl. "ezek a szamlak a 2026 januari riporthoz tartoznak" — a riport intent ezt kontextusba helyezi

#### Lepesenkenti vegrehajtas

1. **Bovits**: `services/document_extractor/service.py` uj metodus:
   ```python
   async def extract_from_package(
       package: IntakePackage,
       config_name: str,
       *,
       cross_document_context: bool = True,
       per_field_confidence: bool = True,
   ) -> ExtractionResult
   ```
2. **Modositsd**: `ExtractionResult` Pydantic modell — uj mezok:
   - `package_id: str`
   - `field_confidences: dict[str, float]`
   - `cross_document_signals: list[str]`
   - `routing_decision: RoutingDecision` (audit)
3. **Refaktor**: `pipeline/adapters/document_adapter.py` hasznaja az uj metodust
4. **Backward compat**: A regi `extract(file_path)` metodus marad, internally hivja az uj `extract_from_package()`-et single-file package-dzsel
5. **Test**: 10+ teszt:
   - single file package extraction
   - multi-file package extraction
   - free-text + file context
   - cross-document context propagacio
   - per-field confidence
6. **Migration**: existing pipeline YAML-ekben a `document_adapter` config bovites — jovobeli backward compat plan
7. **Schema migration**: `extraction_history` tabla kibovitese (alembic 030):
   - `package_id` UUID
   - `field_confidences` JSONB
   - `routing_decision` JSONB

#### Dependencies

- `intake/package.py` (N1) elso
- `intake/association.py` (N4) — free-text linker
- `services/quality/confidence_calibration.py` (K12) per-field confidence
- `routing/multi_signal_router.py` (N7) — RoutingDecision

#### Risk

- **Backward compat**: a 17 endpointot hasznalo UI tobb helyen `extract(file)`-t hiv → SHIM marad
- **Per-field confidence**: az LLM-bol megbizhatoan kihozni nehez — kalibralasi munka kell

#### Acceptance criteria

- [ ] `extract_from_package()` metodus implementalva
- [ ] `field_confidences` map mukodik
- [ ] Multi-file package E2E teszt PASS
- [ ] Existing tests NEM regreszalnak
- [ ] DB migration 030 sikeresen futott

---

### R5 — `services/rag_engine` embedding hardcoded → provider abstraction

**Komponens azonosito:** R5
**Phase:** 2c
**Komplexitas:** M
**Risk:** Kozepes

> **FINAL KIEGESZITES (103_ Section 6):** A `services/rag_engine` kotelezoen implementalja
> a **multi-tenant data isolation**-t:
> - **Collection ID format:** `{tenant_id}__{collection_name}__{embedder_name}` (ketszeres alulvonas elvalasztoval)
> - **DB constraint** (alembic 030): `collection_name_starts_with_tenant` CHECK
> - **Cross-tenant query prevention** — `ctx.tenant_id != parsed.tenant_id` → `PermissionDeniedError`
> - **Dual-collection migration** (`100_d_*` Section 5.2) a BGE-M3 atallashoz
> Reszletes kod: `103_*` Section 6.1-6.5.

#### Jelenlegi allapot

- **Path:** `src/aiflow/services/rag_engine/service.py` (681 sor)
- **Funkcio:** RAG ingest + query (hybrid HNSW + BM25 + RRF)
- **Korlat:** Embedding hardcoded `text-embedding-3-small` (cloud-only). Profile A-ban hasznalhatatlan.

#### Cel allapot

- Embedder az `EmbedderProvider` interface-en keresztul jon (`embeddings/`)
- Konfig: `embedder_provider="bge_m3"` vagy `"azure_openai_3_small"` vagy `"e5_large"`
- PolicyEngine donti el a default-et a profile alapjan
- Embedding elott PII redaction gate (N16) hivva

#### Technologiai indoklas

- A `document_pipeline.md` rogzitett iranya: BGE-M3 (primary), e5-large-instruct (fallback)
- Profile A-ban CSAK self-hosted embedder mukodhet
- BGE-M3 multilingual + dense + sparse + ColBERT — a magyarra is jol kalibralt

#### Funkcionalis indoklas

- Profile A on-prem deployment kotelezo a regulalt iparagakban
- A jelenlegi rendszer `text-embedding-3-small`-t hasznal mindenutt — a Profile A nem futtathato

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/embeddings/__init__.py`
2. **Definialj**: `embeddings/base.py:EmbedderProvider` ABC
   - `name: str`
   - `dimensions: int`
   - `async embed(texts: list[str]) -> list[list[float]]`
   - `async health_check() -> bool`
3. **Implementald**: `embeddings/bge_m3_provider.py:BGEM3EmbeddingProvider`
   - Konstruktor: `(model_path: str, device: str = "cuda" or "cpu", batch_size: int = 32)`
   - `sentence-transformers`-rel betoltott BGE-M3 modell
4. **Implementald**: `embeddings/e5_large_provider.py:E5LargeEmbeddingProvider` (analog)
5. **Implementald**: `embeddings/azure_openai_provider.py:AzureOpenAIEmbeddingProvider`
   - Wrappeli a `LLMClient.embed()`-et — visszhasznalja a meglevot
6. **Refaktor**: `services/rag_engine/service.py` `__init__`-ben uj parameter `embedder: EmbedderProvider`, NEM hardcoded
7. **Refaktor**: `services/rag_engine/ingest.py` az `embedder.embed()`-et hivja
8. **Refaktor**: `services/rag_engine/query.py` hasonloan
9. **Provider registry**: `providers/registry.py:ProviderRegistry.register_embedder()`
10. **Policy integration**: `policy/engine.py:PolicyEngine.get_embedder_provider()` valaszt
11. **PII gate integracio**: ingest elott `RedactionGate.process(texts)` (N16)
12. **DB migration**: `pgvector` collection-okat tagolja `embedder_name` mezovel (alembic 031)
13. **Test**: 15+ teszt:
    - BGE-M3 ingest + query
    - Azure OpenAI ingest + query
    - Provider switch (collection-onkent)
    - PII redaction az embedding elott
    - Profile A blokkolja az Azure provider-t
14. **Migration script**: `scripts/migrate_embeddings_to_provider.py` — re-embed mukodo collection-okkal

#### Dependencies

- `embeddings/redaction_gate.py` (N16)
- `policy/engine.py` (N5)
- `providers/registry.py` (N6)

#### Risk

- **Re-embedding cost**: a meglevo collection-ok `text-embedding-3-small` embedded → BGE-M3 atallasnal RE-EMBEDDING szukseges (vagy parhuzamosan a ket index)
- **Vektor dimenzio:** BGE-M3 = 1024, text-embedding-3-small = 1536 — pgvector tabla schema modositas
- **Performance**: BGE-M3 lassabb mint a cloud API a CPU-n — GPU javaslat

#### Acceptance criteria

- [ ] `EmbedderProvider` interface definialva
- [ ] BGE-M3, e5, Azure OpenAI provider-ek mukodnek
- [ ] PolicyEngine valaszt
- [ ] PII redaction gate aktiv
- [ ] Existing collection-ok migracio nelkul mukodnek (backward compat)
- [ ] Re-embedding script mukodik

---

### R6 — `services/classifier` (ML+LLM) + Qwen2.5-VL opcio

**Komponens azonosito:** R6
**Phase:** 2
**Komplexitas:** M
**Risk:** Kozepes

#### Jelenlegi allapot

- **Path:** `src/aiflow/services/classifier/service.py` (493 sor)
- **Funkcio:** Hibrid ML (TF-IDF + LinearSVC) + LLM (gpt-4o-mini) klasszifikacio
- **Korlat:** Csak text alapon — scan / kep dokumentumokon NEM mukodik

#### Cel allapot

- Megorzendo a hibrid text-alapu klasszifikacio (mukodik!)
- UJ kiegeszites: `services/visual_classifier/qwen25_vl_classifier.py` — VLM-alapu visual classification
- A multi-signal routing engine valaszthat: text-alapu ill. visual klasszifier
- Document boundary detection + page grouping a VLM tudasaval

#### Technologiai indoklas

- A `document_pipeline.md` rogzitett iranya: **Qwen2.5-VL-7B-Instruct** via vLLM
- Page-level visual classification, boundary detection, page grouping support
- Self-hosted (Profile A capable)

#### Funkcionalis indoklas

- Sok dokumentum scan/kep — text klasszifier 0% pontossagu
- Multi-page documentum: kell page-onkenti boundary detection
- Mixed bundle: pl. PDF-ben tobb dokumentum egymas utan — page grouping kell

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/services/visual_classifier/__init__.py`
2. **Implementald**: `visual_classifier/qwen25_vl_classifier.py:Qwen25VLClassifier`
   - Konstruktor: `(vllm_endpoint: str, model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct")`
   - Metodusok:
     - `classify_page(image: PIL.Image, candidate_types: list[str]) → ClassificationResult`
     - `detect_boundaries(images: list[PIL.Image]) → list[BoundaryMarker]`
     - `group_pages(images: list[PIL.Image]) → list[PageGroup]`
3. **vLLM serving**: `infra/vllm/Dockerfile` — Qwen2.5-VL serving
4. **Provider registry**: `providers/registry.py:register_classifier("qwen25_vl", Qwen25VLClassifier)`
5. **Routing**: `routing/multi_signal_router.py` jelekkel donti el (image_dom, scan_likely, page_var)
6. **Test**: 8+ teszt:
   - PDF scan klasszifikacio
   - Boundary detection multi-doc PDF-en
   - Page grouping bundle-on
   - Profile A self-hosted mukodik
7. **Cost / latency monitoring**: GPU eseten 200-500ms/page — meresre szukseg

#### Dependencies

- `routing/multi_signal_router.py` (N7)
- vLLM infra (Docker compose extension)

#### Risk

- **GPU dependency**: Qwen2.5-VL CPU-n nagyon lassu — Profile A kotelezo GPU
- **Memory**: 7B modell ~14GB VRAM (FP16) vagy 7GB (INT4) — hardver tervezes
- **Maintenance**: vLLM upgrade ciklusok

#### Acceptance criteria

- [ ] Qwen2.5-VL-7B vLLM-en futtatva (`infra/vllm/`)
- [ ] `Qwen25VLClassifier` szolgalatkesz
- [ ] Page boundary detection PDF-en mukodik
- [ ] Profile A E2E pipeline visual klasszifikacioval

---

### R7 — `services/data_router` cross-document context

**Komponens azonosito:** R7
**Phase:** 2
**Komplexitas:** S
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/services/data_router/`
- **Funkcio:** Pipeline output filter + routing rules + file move
- **Korlat:** Csak fajlonkenti routing, nincs intake package context

#### Cel allapot

- A `data_router` package-szintu routing-ot ad: az IntakePackage cross-document szignalok alapjan donti el a routing-ot
- Pl. ha a package mind invoice + szallitolevel + szerzodes → triggereli a `purchase_order_consolidation` flow-t

#### Technologiai indoklas

- A jelenlegi Jinja2 conditional eleg, csak az IntakePackage context-et kell expose-olni

#### Funkcionalis indoklas

- Cross-document scenario-k igen gyakoriak (multi-file upload package, batch import)
- Automatic flow trigger package level-en

#### Lepesenkenti vegrehajtas

1. **Bovits**: `data_router` rules engine `package_context: IntakePackageContext` parameter
2. **Routing rules YAML**: `condition: "{{ package.has_invoice and package.has_delivery_note }}"`
3. **Test**: 5+ teszt cross-document conditional rules

#### Dependencies

- `intake/package.py` (N1)

#### Risk

- Alacsony

#### Acceptance criteria

- [ ] Routing rules elerik a package context-et
- [ ] 5 cross-document scenario PASS

---

### R8 — `security/secrets.py:VaultSecretProvider` STUB → production

**Komponens azonosito:** R8 / K5
**Phase:** 3
**Komplexitas:** M
**Risk:** Kozepes (titok kezeles)

#### Jelenlegi allapot

- **Path:** `src/aiflow/security/secrets.py:107-125`
- **Funkcio:** STUB — minden metodus `NotImplementedError`
- **Korlat:** Production-ban CSAK env vars, nincs rotation, nincs lease, nincs audit

#### Cel allapot

- `VaultSecretProviderImpl` (`security/vault_provider_impl.py`)
- `hvac` Python client AppRole authentikacioval
- Token lease + auto-renew
- Mode: KV v2 backend
- Audit log minden hozzaferest

#### Technologiai indoklas

- DEVELOPMENT_ROADMAP rogzit `hvac` library-t v1.3.0+
- AppRole auth: production-grade

#### Funkcionalis indoklas

- Multi-env deployment, secret rotation, audit log
- Compliance (regulalt iparag)

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/security/vault_provider_impl.py`
2. **Implementald**: `VaultSecretProviderImpl(SecretProvider)`
   - Konstruktor: `(vault_url, role_id, secret_id, mount_point="secret")`
   - `_authenticate()` AppRole
   - `_renew_token()` background task
   - `get_secret(key) → str | None`
   - `set_secret(key, value)` (audit)
   - `delete_secret(key)`
   - `list_keys() → list[str]`
3. **Cleanup**: `security/secrets.py:VaultSecretProvider` STUB toroles (vagy alias)
4. **Tests**: `tests/integration/security/test_vault_provider.py` — 8+ teszt VALOS Vault-tal (Docker testcontainers)
5. **Docker compose**: `docker-compose.dev.yml` Vault dev mode container hozzaadasa
6. **Documentation**: `docs/security/vault_setup.md`
7. **Backward compat**: env var fallback ha vault unhealthy

#### Dependencies

- DEVELOPMENT_ROADMAP `hvac` dep-tel
- Docker compose extension

#### Risk

- **Vault unavailability**: prod-ban kritikus dependency — fallback strategia kell
- **Token rotation**: lease expiry kezeles
- **Test infrastructure**: testcontainers Vault dev mode

#### Acceptance criteria

- [ ] `VaultSecretProviderImpl` mukodo
- [ ] STUB torolve
- [ ] 8+ integration test PASS valos Vault-tal
- [ ] Vault healthcheck endpoint
- [ ] Auto token renewal mukodik

---

### R9 — `observability/cost_tracker.py` + Prometheus / OTel

**Komponens azonosito:** R9 / K8
**Phase:** 3
**Komplexitas:** M
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/observability/cost_tracker.py`
- **Funkcio:** Per-step LLM cost (Langfuse-bol)
- **Korlat:** Nincs infra metrika, nincs latency histogram, nincs throughput counter

#### Cel allapot

- `observability/prometheus_metrics.py` — counter + histogram exposre
- `/metrics` endpoint (FastAPI)
- Standard metricok:
  - `aiflow_pipeline_runs_total{status,pipeline_name}`
  - `aiflow_step_duration_seconds_bucket{step_name,le}`
  - `aiflow_llm_cost_usd_total{model,team_id}`
  - `aiflow_guardrail_blocks_total{guard_name,reason}`
  - `aiflow_intake_packages_total{source}`

#### Technologiai indoklas

- `prometheus-client` mar dep-deklaralt (05_TECH_STACK.md)
- DEVELOPMENT_ROADMAP rogzit v1.3.0+

#### Funkcionalis indoklas

- Production observability nelkul nem kovet ondik az SLA
- Grafana dashboard kotelezo

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/observability/prometheus_metrics.py`
2. **Definialj**: 8-10 alap metric (counter + histogram + gauge)
3. **Endpoint**: `api/v1/metrics.py` FastAPI route → `/metrics`
4. **Decorator**: `@track_step_metrics` minden Step-re
5. **Pipeline runner integration**: WorkflowRunner emit-eli a metricaket
6. **Grafana dashboard JSON**: `infra/grafana/dashboards/aiflow.json`
7. **Test**: 5+ teszt
8. **Doc**: `docs/observability/prometheus_setup.md`

#### Dependencies

- `prometheus-client` (mar dep-en)

#### Risk

- Alacsony

#### Acceptance criteria

- [ ] `/metrics` endpoint
- [ ] 8+ standard metric exportalva
- [ ] Grafana dashboard mukodik
- [ ] Per-step latency histogram

---

### R10 — `observability/tracing.py` + OTel distributed tracing

**Komponens azonosito:** R10 / K9
**Phase:** 3
**Komplexitas:** M
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/observability/tracing.py`
- **Funkcio:** Langfuse trace (LLM-specific)
- **Korlat:** Nincs distributed tracing, nincs cross-service span

#### Cel allapot

- `observability/otel_tracer.py` — OpenTelemetry SDK + OTLP exporter
- Auto-instrumentacio: FastAPI, asyncpg, redis, httpx
- Manual span: minden Step + Pipeline + Service
- Span attributes: `pipeline_id`, `step_name`, `tenant_id`, `provider_name`, `routing_decision`

#### Technologiai indoklas

- `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp` mar dep
- DEVELOPMENT_ROADMAP rogzit v1.3.0+

#### Funkcionalis indoklas

- Multi-service deployment debugging
- Performance hotspot kepes
- Compliance audit (lineage)

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/observability/otel_tracer.py`
2. **Auto-instrumentacio**: `opentelemetry.instrumentation.{fastapi,asyncpg,redis,httpx}`
3. **Manual spans**: WorkflowRunner, Step, Pipeline emit
4. **Config**: `OTEL_EXPORTER_OTLP_ENDPOINT` env var
5. **Test**: 5+ teszt mock OTLP collector-rel
6. **Doc**: `docs/observability/otel_setup.md`

#### Dependencies

- `opentelemetry-*` (mar dep)

#### Risk

- Alacsony

#### Acceptance criteria

- [ ] OTLP collector-be exportal
- [ ] Auto + manual span-ok
- [ ] Pipeline → Step → LLM call hierarchia
- [ ] Span attributes minden konfigtertelt

---

### R11 — `services/quality` + Confidence Calibration Layer

**Komponens azonosito:** R11 / K12
**Phase:** 3
**Komplexitas:** M
**Risk:** Kozepes

#### Jelenlegi allapot

- **Path:** `src/aiflow/services/quality/`
- **Funkcio:** Eval metrics gyujtese (pass rate, score, threshold)
- **Korlat:** A confidence scoring nincs egysegesitve. B3.5 mar megerositette a problemat:
  - LLM self-report `0.9` valos `60%` lehet
  - Nincs per-field confidence
  - Nincs kalibracio

#### Cel allapot

- `services/quality/confidence_calibration.py:ConfidenceCalibrationLayer`
- 3-retegu modell (B3.5 minta altalanositas):
  - **Reteg 1**: Rule-based (5-faktor minta — `AttachmentProcessor`-bol)
  - **Reteg 2**: Sklearn `CalibratedClassifierCV` (text classifier)
  - **Reteg 3**: LLM-as-judge with calibration (per-field)
- Per-field confidence (NEM csak overall)
- Per-skill calibration data store (SQLite-ben vagy DB-ben)

#### Technologiai indoklas

- B3.5 megerositette: az ad-hoc confidence megbizhatatlan
- `CalibratedClassifierCV` mar bevalt (`AttachmentProcessor`)
- Per-field strukturalt confidence kell az UI verification-hez (B7 follow-up)

#### Funkcionalis indoklas

- A user-experience hatara: ha a confidence megbizhatatlan, a user nem bizik a rendszerben
- Per-field confidence megengedi a verification UI-nak, hogy a piros mezok kerülenek figyelembe vehetok

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `services/quality/confidence_calibration.py`
2. **Definialj**: `ConfidenceCalibrationLayer`
   - `calibrate_rule_based(features: dict) → float` (AttachmentProcessor minta)
   - `calibrate_ml(classifier, features: dict) → float` (sklearn predict_proba)
   - `calibrate_llm(prompt, response, sources) → float` (judge LLM)
   - `combine(rule, ml, llm, weights) → float` (sulyozott atlag)
3. **Per-field**: `CalibratedFieldExtraction` Pydantic
4. **Per-skill data**: `confidence_calibration_data` tabla (alembic 032)
5. **Routing integration**: `confidence → routing` mukodik (>=0.9 auto, 0.7-0.9 review, <0.7 reject)
6. **HumanReviewService integration**: low-confidence eredmenyek auto-route review queue-ba
7. **Test**: 15+ teszt:
   - Rule-based 5-faktor scoring
   - Sklearn calibration
   - LLM judge calibration
   - Per-field confidence
   - Routing trigger
8. **Migration**: minden AI service-be (`document_extractor`, `classifier`, `entity_extractor`) integrálni

#### Dependencies

- B3.5 minta
- `services/human_review` integration

#### Risk

- **Calibration data**: kell golden dataset minden skill-re — Phase 3 munka
- **Migration kockaza**: backward-incompatible konfidencia formatum a meglevo extrakciokban — adat migration script

#### Acceptance criteria

- [ ] `ConfidenceCalibrationLayer` mukodik
- [ ] Per-field confidence MINDEN AI service-ben
- [ ] Routing automatic trigger
- [ ] Calibration golden dataset 5 skill-re
- [ ] DB migration 032 sikeresen futott

---

### R12 — `pipeline/builtin_templates/invoice_automation_v2.yaml` mint multi-source pelda

**Komponens azonosito:** R12
**Phase:** 1 (acceptance test)
**Komplexitas:** S
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/pipeline/builtin_templates/invoice_automation_v2.yaml`
- **Funkcio:** Email → szamla extract pipeline
- **Korlat:** Egyetlen source (email)

#### Cel allapot

- Multi-source intake pipeline pelda:
  - Source 1: Email connector (B3 mar mukodik)
  - Source 2: File upload (UI-bol)
  - Source 3: Folder/S3 batch import
- Mindharom egy IntakePackage modellbe normalizalva
- A pipeline NEM tudja, melyik source-bol jott

#### Technologiai indoklas

- A multi-source elve a fazis 1 acceptance teszt resze

#### Funkcionalis indoklas

- A user batch-ben tud feltolteni szamlakat a UI-bol
- Folder watcher batch-import scenarios

#### Lepesenkenti vegrehajtas

1. **Modositsd**: `invoice_automation_v2.yaml` — `intake_source` step
2. **Steps**:
   ```yaml
   - name: intake
     adapter: intake_normalize
     config:
       source_type: "{{ input.source_type }}"  # email | file | folder | api
       source_config: "{{ input.source_config }}"
   - name: extract
     adapter: document_extractor
     method: extract_from_package
     config:
       config_name: invoice_v2
   ```
3. **API endpoint**: `POST /api/v1/intake/upload-package` (multi-file form)
4. **UI**: aiflow-admin Invoice Finder oldal — drag-drop multi-file
5. **E2E test**: Playwright — file upload package + email package + folder package PASS

#### Dependencies

- `intake/` modul (Phase 1)

#### Risk

- Alacsony

#### Acceptance criteria

- [ ] Pipeline mukodik 3 source-bol
- [ ] UI multi-file upload
- [ ] E2E PASS

---

### R13 — `skill_system/instance_*.py` policy override

**Komponens azonosito:** R13
**Phase:** 1
**Komplexitas:** S
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/skill_system/instance.py`, `instance_loader.py`, `instance_registry.py`
- **Funkcio:** Multi-instance per skill (28_MODULAR_DEPLOYMENT alap)
- **Korlat:** Tenant override nem tartalmaz policy parametereket

#### Cel allapot

- `SkillInstanceConfig` Pydantic modell uj `policy_override: dict | None` mezo
- A `PolicyEngine.get_for_instance(instance_id)` jelenlegi tenant config + instance override-ot kombinalja
- `instances/{customer}/policy.yaml` per-instance policy file

#### Technologiai indoklas

- A 28-as Modular Deployment mar elkezdte a multi-instance modellt
- Csak ki kell terjeszteni policy override-tal

#### Funkcionalis indoklas

- Egy customer-en belul lehet "AS Mary" (cloud-allowed) es "AS John" (cloud-disallowed) instance
- Profile A vs B per-instance, NEM globalis

#### Lepesenkenti vegrehajtas

1. **Bovits**: `SkillInstanceConfig` Pydantic — `policy_override: dict[str, Any] | None = None`
2. **Loader**: `instance_loader.py` betolti a `instances/{customer}/policy.yaml`-t
3. **Policy lookup**: `PolicyEngine.get_for_instance(instance_id)` returns merged config
4. **Test**: 5+ teszt
5. **Doc**: `instances/README.md` policy override pelda

#### Dependencies

- `policy/engine.py` (N5)

#### Risk

- Alacsony

#### Acceptance criteria

- [ ] Per-instance policy override mukodik
- [ ] Tenant 1 instance Profile A, masik Profile B
- [ ] 5+ unit test PASS

---

### R14 — `guardrails/` + PII redaction gate

**Komponens azonosito:** R14
**Phase:** 2
**Komplexitas:** S
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/guardrails/`
- **Funkcio:** Input/Output/Scope guard + LLM guards (B1-bol)
- **Korlat:** A PII detection mukodik, de NINCS strukturalt embedding-elotti redaction gate

#### Cel allapot

- `embeddings/redaction_gate.py:RedactionGate`
- A guardrails meglevo PII detector-jet hivja
- Modes: `mask` (default), `block`, `allow_with_audit`
- Policy-driven: `pii_embedding_allowed=false` → mode=mask, true → mode=allow_with_audit

#### Technologiai indoklas

- A guardrails framework mar mukodik (A5 + B1)
- Csak az embedding pipeline-on belul kell egy kotelezo lepest

#### Funkcionalis indoklas

- PII az embedding-ben = lekes az LLM training-be (compliance kockazat)
- Most a `text-embedding-3-small` cloud-on torzentik az embedding-elt szovegeket — kotelezo redact

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/embeddings/redaction_gate.py:RedactionGate`
2. **Konstruktor**: `(pii_detector, mode: RedactionMode)`
3. **Metodusok**: `process(texts: list[str]) → list[str]` (in-place mask vagy block)
4. **Audit**: minden mask `RedactionEvent` rekord
5. **Integration**: `services/rag_engine` ingest elott KOTELEZO hivas
6. **Test**: 10+ teszt:
   - PII mask (email, telefon, adoszam)
   - Block mode (raise exception)
   - Audit log
   - Profile A `pii_embedding_allowed=false` mukodik
7. **Doc**: `docs/embeddings/pii_redaction.md`

#### Dependencies

- `guardrails/` (mar mukodo)
- `services/rag_engine` integracio (R5)

#### Risk

- Alacsony

#### Acceptance criteria

- [ ] `RedactionGate` mukodik
- [ ] Embedding pipeline-bol kotelezo
- [ ] Audit log
- [ ] Profile A blokk

---

### R15 — `pipeline/adapters/*` egyseges provider interface

**Komponens azonosito:** R15
**Phase:** 1
**Komplexitas:** S (refactor)
**Risk:** Alacsony

#### Jelenlegi allapot

- **Path:** `src/aiflow/pipeline/adapters/` (21 fajl)
- **Funkcio:** Adapter per service (email, doc, classifier, ...)
- **Korlat:** Mindegyik adapter sajat module / service-rel hivja, NEM provider registry-bol

#### Cel allapot

- Egyseges provider interface contract: `BaseAdapter` ABC
- Adapter `__init__` parameter: `provider: ProviderInterface`
- A `provider` a `ProviderRegistry`-bol jon
- Konfig YAML: `provider_name: "docling_standard"` vagy `"azure_di"`

#### Technologiai indoklas

- A jelenlegi adapter struktura mar nagyon kozeli a provider absztrakcio elveire
- Csak meg kell valositani a `ProviderInterface` ABC-t

#### Funkcionalis indoklas

- Provider switching NEM igenyel kod modositast
- Tenant override mukodik

#### Lepesenkenti vegrehajtas

1. **Definialj**: `pipeline/adapters/base.py:ProviderInterface` (ha mar nincs)
2. **Refactor**: minden adapter `__init__`-ben provider parameter
3. **Compiler integration**: `pipeline/compiler.py` `provider_name` config alapjan injectel
4. **Test**: 21 adapter regression
5. **Doc**: `pipeline/adapters/README.md` provider pattern

#### Dependencies

- `providers/registry.py` (N6)

#### Risk

- **Backwards compat**: meglevo pipeline YAML-ek
- Megoldas: `provider_name` opcionalis, default a regi service-bol jon

#### Acceptance criteria

- [ ] Minden adapter `provider` parameter-rel
- [ ] Existing pipelines NEM regreszalnak
- [ ] Tenant override mukodik

---

## UJ KOMPONENSEK (N-szeria)

---

### N1 — `intake/package.py:IntakePackage` model

**Komponens azonosito:** N1
**Phase:** 1
**Komplexitas:** S
**Risk:** Alacsony

#### Cel allapot

```python
# src/aiflow/intake/package.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class IntakeFile(BaseModel):
    file_id: str
    file_path: str
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    source_metadata: dict = Field(default_factory=dict)

class IntakeDescription(BaseModel):
    description_id: str
    text: str
    language: str | None = None
    role: Literal["case_note", "user_note", "form_input", "package_context", "free_text"] = "free_text"
    associated_file_ids: list[str] = Field(default_factory=list)  # filled by association layer

class IntakePackage(BaseModel):
    package_id: str
    source_type: Literal["email", "file_upload", "folder_import", "batch_import", "api_push"]
    tenant_id: str
    source_metadata: dict = Field(default_factory=dict)  # email_from, email_subject, folder_path, ...
    files: list[IntakeFile] = Field(default_factory=list)
    descriptions: list[IntakeDescription] = Field(default_factory=list)
    package_context: dict = Field(default_factory=dict)  # case_id, request_id, ...
    cross_document_signals: dict = Field(default_factory=dict)  # filled by classifier+routing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    provenance_chain: list[str] = Field(default_factory=list)  # audit chain
```

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/intake/__init__.py`
2. **Modell**: `intake/package.py` (above)
3. **DB migration 029** (B0-ban mar 029 a max, ezek a kovetkezok 030+):
   - `intake_packages` tabla
   - `intake_files`
   - `intake_descriptions`
   - `package_associations`
4. **Test**: 10+ teszt (Pydantic validation, serialization)

#### Acceptance criteria

- [ ] `IntakePackage` Pydantic modell
- [ ] DB migration 030
- [ ] 10+ unit test

---

### N2 — `intake/source_adapters/` + IntakeSourceAdapter

**Komponens azonosito:** N2
**Phase:** 1
**Komplexitas:** M
**Risk:** Alacsony

#### Cel allapot

```python
# src/aiflow/intake/source_adapters/base.py
from abc import ABC, abstractmethod

class IntakeSourceAdapter(ABC):
    @property
    @abstractmethod
    def source_type(self) -> str: ...

    @abstractmethod
    async def discover(self) -> list[IntakeSourceItem]: ...

    @abstractmethod
    async def fetch(self, item: IntakeSourceItem) -> IntakePackage: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

# Implementaciok:
# - email_source.py: EmailIntakeSourceAdapter (Unstructured + email_connector)
# - file_source.py: FileUploadIntakeSourceAdapter (UI form)
# - folder_source.py: FolderIntakeSourceAdapter (folder watcher / S3)
# - batch_source.py: BatchIntakeSourceAdapter (manual batch import API)
# - api_source.py: APIPushIntakeSourceAdapter (webhook)
```

#### Lepesenkenti vegrehajtas

1. **Definialj**: `IntakeSourceAdapter` ABC
2. **Implementald**: `EmailIntakeSourceAdapter` (R1 alatt mar reszben)
3. **Implementald**: `FileUploadIntakeSourceAdapter`
4. **Implementald**: `FolderIntakeSourceAdapter` (S3-compatible vagy local fs)
5. **Implementald**: `BatchIntakeSourceAdapter`
6. **Implementald**: `APIPushIntakeSourceAdapter`
7. **Registry**: `intake/source_adapters/registry.py:SourceAdapterRegistry`
8. **API endpoint**: `POST /api/v1/intake/upload`
9. **Test**: 10+ teszt per adapter

#### Acceptance criteria

- [ ] 5 source adapter mukodik
- [ ] Egyseges interface
- [ ] API endpoint
- [ ] 50+ unit teszt

---

### N3 — `intake/normalization.py:IntakeNormalizationLayer`

**Komponens azonosito:** N3
**Phase:** 1
**Komplexitas:** S
**Risk:** Alacsony

#### Cel allapot

```python
# src/aiflow/intake/normalization.py
class IntakeNormalizationLayer:
    """Normalize raw source data to canonical IntakePackage."""

    def normalize_email(self, email_msg: EmailMessage) -> IntakePackage: ...
    def normalize_file_upload(self, files: list[UploadFile], descriptions: list[str]) -> IntakePackage: ...
    def normalize_folder(self, folder_path: Path, manifest: dict | None) -> IntakePackage: ...
    def normalize_batch(self, items: list[dict]) -> list[IntakePackage]: ...
    def normalize_api(self, payload: dict) -> IntakePackage: ...

    def detect_mime(self, file_path: Path) -> str: ...
    def compute_sha256(self, file_path: Path) -> str: ...
```

#### Lepesenkenti vegrehajtas

1. Letrehoz `IntakeNormalizationLayer`
2. Mime detection: `python-magic` vagy `mimetypes`
3. SHA256 hash computation
4. Test 15+

#### Acceptance criteria

- [ ] 5 normalize metodus
- [ ] MIME detection
- [ ] Hash computation
- [ ] 15+ test

---

### N4 — `intake/association.py:FileDescriptionAssociator`

**Komponens azonosito:** N4
**Phase:** 1
**Komplexitas:** M
**Risk:** Kozepes

#### Cel allapot

```python
# src/aiflow/intake/association.py
class FileDescriptionAssociator:
    """Link free-text descriptions to files within an IntakePackage."""

    def __init__(
        self,
        rule_engine: AssociationRuleEngine,
        llm_fallback: LLMAssociator | None = None,
        confidence_threshold: float = 0.7,
    ): ...

    async def associate(self, package: IntakePackage) -> IntakePackage:
        """Returns package with descriptions[].associated_file_ids filled."""
        # 1. Rule-based: filename mention, regex, position
        # 2. If ambiguous → LLM fallback
        # 3. If still low confidence → manual review flag
```

**Modes** (`policy.file_description_association_mode`):
- `rule_only`: csak rule, ambiguous→manual
- `rule_first_llm_fallback` (default): rule, ha alacsony→LLM
- `llm_only`: csak LLM
- `manual_only`: minden manual review

#### Lepesenkenti vegrehajtas

1. Letrehoz `AssociationRuleEngine` + `LLMAssociator`
2. `FileDescriptionAssociator` orkesztracio
3. Test 15+ szcenariok (egyertelmu, ambiguous, multi-file, irreleváns description)

#### Risk

- LLM-alapu association draga + lassu — rule-first elv kotelezo
- Manual review fallback fontos

#### Acceptance criteria

- [ ] 4 mode mukodik
- [ ] Ambiguous case → manual review flag
- [ ] 15+ test

---

### N5 — `policy/engine.py:PolicyEngine`

**Komponens azonosito:** N5
**Phase:** 1
**Komplexitas:** M
**Risk:** Kozepes

#### Cel allapot

```python
# src/aiflow/policy/engine.py
class PolicyEngine:
    def __init__(self, profile_config: dict, tenant_overrides: dict | None = None): ...

    def is_allowed(self, capability: str, context: dict | None = None) -> bool:
        """Check if capability is allowed under current policy + context."""

    def get_default_provider(self, provider_type: str) -> str:
        """Return default provider name for type (parser, classifier, embedder, ...)."""

    def get_for_instance(self, instance_id: str) -> "PolicyEngine":
        """Return PolicyEngine merged with instance overrides."""

    def evaluate(self, parameter: str) -> Any:
        """Get parameter value (with override chain)."""
```

A `Phase 1` minimum policy parameterek (lasd `100_*.md` Section 6).

#### Lepesenkenti vegrehajtas

1. **Definialj**: `PolicyEngine`
2. **Loader**: `config/profiles/profile_a.yaml`, `profile_b.yaml`
3. **Parameter validation**: Pydantic schema
4. **Test**: 25+ test (mind a 30+ parameter)
5. **Doc**: `docs/policy/engine.md`

#### Risk

- Hibas policy konfig **silenter** rossz cele lehet
- Megoldas: schema validation + hibaa-friendly hibauzenetek

#### Acceptance criteria

- [ ] PolicyEngine osszes parameterre
- [ ] Profile A + B alap config
- [ ] Tenant override
- [ ] 25+ test

---

### N6 — `providers/registry.py:ProviderRegistry`

**Komponens azonosito:** N6
**Phase:** 1a
**Komplexitas:** S
**Risk:** Alacsony

> **FINAL KIEGESZITES (103_ Section 5):** A provider abstraction **4 darab Python ABC**
> szinten formalizalva van (ParserProvider, ClassifierProvider, ExtractorProvider,
> EmbedderProvider), minden provider kotelezoen `ProviderMetadata` objektumot ad vissza
> (`name`, `version`, `supported_types`, `speed_class`, `gpu_required`, `cost_class`,
> `license`). A **contract test framework** (`tests/integration/providers/test_contract.py`)
> biztositja, hogy minden uj provider csak akkor kerul be, ha atment a kotelezo teszteken.
> Reszletes kod: `103_*` Section 5.1-5.2.

#### Cel allapot

```python
# src/aiflow/providers/registry.py
class ProviderRegistry:
    """Central registry for all pluggable providers (parser, classifier, extractor, embedder, ...)."""

    def register_parser(self, name: str, provider_cls: type) -> None: ...
    def register_classifier(self, name: str, provider_cls: type) -> None: ...
    def register_extractor(self, name: str, provider_cls: type) -> None: ...
    def register_embedder(self, name: str, provider_cls: type) -> None: ...

    def get_parser(self, name: str) -> ParserProvider: ...
    def get_classifier(self, name: str) -> ClassifierProvider: ...
    # ...

    def list_parsers(self) -> list[str]: ...
    # ...
```

#### Lepesenkenti vegrehajtas

1. **Definialj**: `ProviderRegistry`
2. **Interfaces**: `providers/interfaces.py`
3. **Test**: 10+ test
4. **Doc**: provider pattern guide

#### Acceptance criteria

- [ ] Registry mukodik 4+ provider tipusra
- [ ] Auto-discovery (entry points)
- [ ] 10+ test

---

### N7 — `routing/multi_signal_router.py:MultiSignalRoutingEngine`

**Komponens azonosito:** N7
**Phase:** 2a
**Komplexitas:** L (nagy, KRITIKUS)
**Risk:** Magas (komplexitas)

> **FINAL KIEGESZITES (103_ Section 4):** A routing engine governance teljes mertekben
> specifikalva:
> - **Signal weight registry** (`routing/weights.py`) per-tenant override-tal
> - **Priority hierarchy** (Compliance > Policy > Cost > Latency > Accuracy)
> - **All-providers-unavailable fallback** → auto ReviewTask + package REVIEW_PENDING
> - **Audit query interface** (`GET /api/v1/routing/decisions/{package_id}`)
> - **Human override** (`POST /api/v1/routing/decisions/{id}/override`)
> - **Routing confidence calculation** (score_gap + signal_strength)
> - **Cost-aware routing** (`routing/cost_cap.py` per-decision/package/daily cap)
> Reszletes kod: `103_*` Section 4.1-4.7.

#### Cel allapot

```python
# src/aiflow/routing/multi_signal_router.py
class RoutingDecision(BaseModel):
    selected_provider: str
    fallback_chain: list[str]
    signals_used: dict[str, Any]
    reason: str
    confidence: float
    policy_constraints: dict
    timestamp: datetime

class MultiSignalRoutingEngine:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        policy_engine: PolicyEngine,
        signals_extractor: DocumentSignalsExtractor,
    ): ...

    async def route_parser(
        self,
        file: IntakeFile,
        package_context: IntakePackage,
        provider_type: Literal["parser", "classifier", "extractor"],
    ) -> RoutingDecision:
        """Multi-signal routing decision with audit trail."""
        # 1. Extract signals (file_type, text_layer, ocr_need, image_dom, ...)
        # 2. Get policy constraints (cloud_allowed, pii_embedding, ...)
        # 3. Score each available provider
        # 4. Select best match
        # 5. Return RoutingDecision
```

**Signals**:
- `file_type`: pdf, docx, image, ...
- `text_layer_ratio`: 0..1 (PDF szoveg vs kep)
- `ocr_need`: bool
- `image_dominance`: 0..1
- `table_suspicion`: 0..1
- `layout_complexity`: 0..1
- `page_variance`: 0..1
- `source_text_relevance`: 0..1 (intake context)
- `tenant_policy`: dict (from policy engine)
- `provider_availability`: dict (health check)

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `routing/__init__.py`
2. **Definialj**: `RoutingDecision` Pydantic
3. **Definialj**: `DocumentSignalsExtractor` — file-bol szignal extraction
4. **Implementald**: `MultiSignalRoutingEngine`
5. **Scoring**: per-provider scoring function
6. **Audit**: minden RoutingDecision DB-be log (`routing_decisions` tabla, alembic 033)
7. **Test**: 30+ test (signal kombinaciok)
8. **Doc**: `docs/routing/multi_signal.md`

#### Dependencies

- `providers/registry.py` (N6)
- `policy/engine.py` (N5)
- `intake/package.py` (N1)

#### Risk

- **Komplexitas**: 30+ signal kombinacio
- **Test coverage**: kell extensive teszt
- **Tuning**: signal sulyok kalibralasa empirikus

#### Acceptance criteria

- [ ] `MultiSignalRoutingEngine` mukodik
- [ ] 10+ signal extraction
- [ ] Audit trail teljes (RoutingDecision DB)
- [ ] 30+ test
- [ ] 10 processing flow E2E (`document_pipeline.md` Section 8)

---

### N8 — `ingestion/parsers/pymupdf4llm_parser.py:PyMuPDF4LLMParser`

**Komponens azonosito:** N8
**Phase:** 2
**Komplexitas:** S
**Risk:** Alacsony

#### Cel allapot

```python
# src/aiflow/ingestion/parsers/pymupdf4llm_parser.py
import pymupdf4llm

class PyMuPDF4LLMParser(ParserProvider):
    name = "pymupdf4llm_fast"
    supported_types = ["pdf"]  # CSAK PDF
    speed_class = "fast"  # GPU-mentes, gyors

    async def parse(self, file_path: Path) -> ParsedDocument:
        """Fast-path for born-digital PDFs."""
        md_text = pymupdf4llm.to_markdown(file_path)
        return ParsedDocument(
            text=md_text,
            markdown=md_text,
            ...
        )
```

#### Lepesenkenti vegrehajtas

1. **Add dep**: `pymupdf4llm>=0.0.20` → `pyproject.toml` `[parsers-fast]` extra
2. **Implementald**: `PyMuPDF4LLMParser`
3. **Provider registry**: regisztracio
4. **Test**: 8+ test (born-digital PDF, scan PDF — visszadob, image-only PDF — visszadob)
5. **Routing integracio**: routing engine `pymupdf4llm_fast` valasztja ha `text_layer_ratio > 0.8`

#### Acceptance criteria

- [ ] `PyMuPDF4LLMParser` mukodik
- [ ] Routing valasztja born-digital PDF-re
- [ ] 8+ test

---

### N9 — `ingestion/parsers/docling_vlm_parser.py:DoclingVLMParser`

**Komponens azonosito:** N9
**Phase:** 2
**Komplexitas:** M
**Risk:** Kozepes (vLLM dependency)

#### Cel allapot

```python
# src/aiflow/ingestion/parsers/docling_vlm_parser.py
class DoclingVLMParser(ParserProvider):
    name = "docling_vlm"
    supported_types = ["pdf", "image"]
    speed_class = "slow"  # GPU
    use_cases = ["scan", "handwriting", "complex_layout"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        """Hard-case path: Docling VLM pipeline + vLLM runtime."""
        # Setup Docling with VLM pipeline option
        # Returns ParsedDocument
```

#### Lepesenkenti vegrehajtas

1. **vLLM infra**: `infra/vllm/docker-compose.yaml` Docling-compatible VLM modellel
2. **Implementald**: `DoclingVLMParser` (Docling VLM pipeline option-nel)
3. **Provider registry**: regisztracio
4. **Test**: 5+ test scan/handwriting esetekkel
5. **Routing integracio**

#### Risk

- vLLM serving setup
- GPU dependency

#### Acceptance criteria

- [ ] DoclingVLMParser mukodik
- [ ] Scan PDF E2E PASS
- [ ] vLLM container futtatva
- [ ] 5+ test

---

### N10 — `services/visual_classifier/qwen25_vl_classifier.py:Qwen25VLClassifier`

> Lasd R6 — ott reszletezve.

---

### N11 — `archival/gotenberg_adapter.py:GotenbergArchivalAdapter`

**Komponens azonosito:** N11
**Phase:** 2
**Komplexitas:** S
**Risk:** Alacsony

#### Cel allapot

```python
# src/aiflow/archival/gotenberg_adapter.py
class GotenbergArchivalAdapter:
    """Convert source documents to PDF/A using Gotenberg service."""

    def __init__(self, gotenberg_url: str = "http://gotenberg:3000"): ...

    async def convert_to_pdfa(
        self,
        source_file: Path,
        pdfa_format: Literal["PDF/A-1a", "PDF/A-2b", "PDF/A-3b"] = "PDF/A-2b",
    ) -> Path:
        """POST source to Gotenberg, return PDF/A file path."""
```

#### Lepesenkenti vegrehajtas

1. **Docker**: `gotenberg/gotenberg:7` to docker-compose
2. **Implementald**: HTTP client httpx-szel
3. **Pipeline integracio**: `pipeline/adapters/archival_adapter.py`
4. **Test**: 5+ test (DOCX→PDF/A, PNG→PDF/A, PDF→PDF/A)

#### Acceptance criteria

- [ ] Gotenberg container fut
- [ ] PDF/A generalas mukodik
- [ ] 5+ test

---

### N12 — `archival/verapdf_validator.py:VeraPDFValidator`

**Komponens azonosito:** N12
**Phase:** 2
**Komplexitas:** S
**Risk:** Alacsony

#### Cel allapot

```python
# src/aiflow/archival/verapdf_validator.py
class VeraPDFValidator:
    """Validate PDF/A files using veraPDF (separate explicit step)."""

    def __init__(self, verapdf_path: str = "/usr/local/bin/verapdf"): ...

    async def validate(
        self,
        pdf_file: Path,
        profile: Literal["PDF/A-1a", "PDF/A-2b", "PDF/A-3b"],
    ) -> ValidationResult:
        """Run veraPDF, parse XML report, return ValidationResult."""

class ValidationResult(BaseModel):
    is_valid: bool
    profile: str
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    raw_report: str
```

#### Lepesenkenti vegrehajtas

1. **Docker**: veraPDF binary in container OR sidecar
2. **Implementald**: subprocess + XML parse
3. **Test**: 8+ test (valid PDF/A, invalid, broken)
4. **Pipeline**: archival pipeline a Gotenberg utan KOTELEZOEN hivja
5. **Doc**: `docs/archival/verapdf.md`

#### Acceptance criteria

- [ ] VeraPDF mukodik
- [ ] PDF/A status CSAK validation utan
- [ ] 8+ test

---

### N11b — `archival/quarantine.py:QuarantineManager` (P3 hardening)

**Komponens azonosito:** N11b
**Phase:** 2d
**Komplexitas:** S
**Risk:** Alacsony
**Forras:** `102_*` Section 3.7 SF1 — P3 hardening

> **P3 HARDENING (105_*):** A `102_*` Section 3.7 azonositotta, hogy az archival failure path
> NEM reszletezett. Ez a komponens lezarja a **quarantine workflow** hianyat a veraPDF FAIL,
> Gotenberg crash es compliance violation eseteire.

#### Cel allapot

```python
# src/aiflow/archival/quarantine.py
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

class QuarantineReason(str, Enum):
    VERAPDF_VALIDATION_FAIL = "verapdf_validation_fail"
    GOTENBERG_CONVERSION_FAIL = "gotenberg_conversion_fail"
    POLICY_VIOLATION = "policy_violation"
    CORRUPTED_SOURCE = "corrupted_source"
    UNKNOWN_FORMAT = "unknown_format"
    COMPLIANCE_BLOCK = "compliance_block"


class QuarantineRecord(BaseModel):
    record_id: UUID = Field(default_factory=uuid4)
    artifact_id: UUID
    source_file_id: UUID
    package_id: UUID
    tenant_id: str
    
    reason: QuarantineReason
    reason_details: str
    
    quarantine_path: str  # tenant_id/quarantine/{artifact_id}__{reason}.pdf
    original_path: str | None = None
    
    verapdf_report_path: str | None = None  # validation XML report
    conversion_error_log: str | None = None
    
    review_task_id: UUID | None = None  # auto-created ReviewTask
    
    quarantined_at: datetime = Field(default_factory=datetime.utcnow)
    released_at: datetime | None = None
    released_by: str | None = None
    release_action: str | None = None  # "manual_fix", "ignore", "delete"
    
    retention_until: datetime  # compliance retention


class QuarantineManager:
    """Manages quarantined archival artifacts."""
    
    def __init__(
        self,
        object_storage: ObjectStorageClient,
        review_service: HumanReviewService,
        notification: NotificationService,
    ): ...
    
    async def quarantine(
        self,
        artifact: ArchivalArtifact,
        reason: QuarantineReason,
        details: str,
        *,
        ctx: ExecutionContext,
    ) -> QuarantineRecord:
        """Move artifact to quarantine + create ReviewTask."""
        # 1. Move to quarantine path
        quarantine_path = self.path_builder.quarantine_path(artifact.artifact_id, reason.value)
        await self.object_storage.move(artifact.artifact_path, quarantine_path, ctx=ctx)
        
        # 2. Update artifact status
        await self.archival_repo.update_status(
            artifact.artifact_id,
            status=ArchivalStatus.QUARANTINED,
            quarantine_reason=reason.value,
            quarantine_path=quarantine_path,
        )
        
        # 3. Create review task
        task = await self.review_service.create_task(
            review_type=ReviewType.QUARANTINE,
            priority=ReviewPriority.CRITICAL if reason in [QuarantineReason.POLICY_VIOLATION, QuarantineReason.COMPLIANCE_BLOCK] else ReviewPriority.HIGH,
            package_id=artifact.package_id,
            title=f"Quarantine: {reason.value}",
            description=details,
            context_snapshot={
                "artifact_id": str(artifact.artifact_id),
                "quarantine_path": quarantine_path,
                "reason": reason.value,
            },
        )
        
        # 4. Store record
        record = QuarantineRecord(
            artifact_id=artifact.artifact_id,
            source_file_id=artifact.source_file_id,
            package_id=artifact.package_id,
            tenant_id=ctx.tenant_id,
            reason=reason,
            reason_details=details,
            quarantine_path=quarantine_path,
            review_task_id=task.task_id,
            retention_until=datetime.utcnow() + self._get_retention_period(reason),
        )
        await self.quarantine_repo.insert(record)
        
        # 5. Notify compliance officer
        if reason in [QuarantineReason.POLICY_VIOLATION, QuarantineReason.COMPLIANCE_BLOCK]:
            await self.notification.notify_compliance_officer(record)
        
        return record
    
    async def release(
        self,
        record_id: UUID,
        action: str,  # "manual_fix", "ignore", "delete"
        *,
        ctx: ExecutionContext,
    ) -> None:
        """Release from quarantine with explicit action."""
        # Only admin / compliance role
        if not await self.rbac.has_role(ctx.user_id, ["admin", "compliance_officer"]):
            raise PermissionDeniedError(...)
        
        record = await self.quarantine_repo.get(record_id)
        
        if action == "manual_fix":
            # Re-convert + re-validate
            await self.archival_service.re_convert(record.artifact_id)
        elif action == "ignore":
            # Mark as reviewed, artifact stays in quarantine
            await self.quarantine_repo.update(record_id, release_action="ignore", released_by=ctx.user_id)
        elif action == "delete":
            # Compliance-approved permanent delete
            await self.object_storage.delete(record.quarantine_path, ctx=ctx)
            await self.archival_repo.delete(record.artifact_id)
    
    def _get_retention_period(self, reason: QuarantineReason) -> timedelta:
        """Retention period per reason."""
        return {
            QuarantineReason.POLICY_VIOLATION: timedelta(days=365 * 7),  # 7 years compliance
            QuarantineReason.COMPLIANCE_BLOCK: timedelta(days=365 * 7),
            QuarantineReason.VERAPDF_VALIDATION_FAIL: timedelta(days=90),
            QuarantineReason.GOTENBERG_CONVERSION_FAIL: timedelta(days=30),
            QuarantineReason.CORRUPTED_SOURCE: timedelta(days=30),
            QuarantineReason.UNKNOWN_FORMAT: timedelta(days=30),
        }[reason]
```

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/archival/quarantine.py`
2. **DB migration 034b**: `quarantine_records` tabla
3. **Integracio**: N11 GotenbergArchivalAdapter + N12 VeraPDFValidator hivjak quarantine() hibaeseten
4. **API endpoint**: `GET /api/v1/quarantine/records?tenant_id=...` (compliance dashboard)
5. **API endpoint**: `POST /api/v1/quarantine/{record_id}/release` (admin action)
6. **UI**: aiflow-admin Audit/Compliance oldalon quarantine records list + release UI
7. **Test**: 10+ test (quarantine + release path + retention)
8. **Notification template**: `compliance_officer_quarantine.yaml`

#### Acceptance criteria

- [ ] `QuarantineManager` mukodik
- [ ] Auto-quarantine veraPDF FAIL eseten
- [ ] Auto-quarantine Gotenberg FAIL eseten
- [ ] Auto ReviewTask letrehozas
- [ ] Compliance officer notifikacio
- [ ] Release procedure (3 action)
- [ ] Retention period enforcement
- [ ] 10+ test

---

### N11c — `archival/retention_policy.py:RetentionPolicy` (P3 hardening)

**Komponens azonosito:** N11c
**Phase:** 2d
**Komplexitas:** S
**Risk:** Alacsony
**Forras:** `102_*` Section 3.7 SF1 — P3 hardening

> **P3 HARDENING (105_*):** Az archival retention policy explicit rendszer, per-tenant
> overrideolhat, compliance-aware.

#### Cel allapot

```python
# src/aiflow/archival/retention_policy.py
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

class RetentionTier(str, Enum):
    SHORT = "short"        # 30 nap (transient artifacts)
    STANDARD = "standard"  # 1 ev (normal business)
    LONG = "long"          # 7 ev (tax compliance HU)
    PERMANENT = "permanent"  # No auto-delete


class RetentionRule(BaseModel):
    rule_id: str
    document_type: str | None = None  # invoice, contract, ...
    tenant_id: str | None = None       # per-tenant override
    tier: RetentionTier
    duration: timedelta
    legal_basis: str                    # "HU Tax Act 2003 §169", "GDPR Art 5(1)(e)"
    deletion_mode: str = "auto"         # auto | manual_approval | never


class RetentionPolicy:
    """Per-tenant + per-doc-type retention policy."""
    
    DEFAULT_RULES: list[RetentionRule] = [
        RetentionRule(
            rule_id="default_invoice_hu",
            document_type="invoice",
            tier=RetentionTier.LONG,
            duration=timedelta(days=365 * 8),  # 8 ev HU tax
            legal_basis="HU Tax Act 2003 §169 (8 year retention for invoices)",
        ),
        RetentionRule(
            rule_id="default_contract",
            document_type="contract",
            tier=RetentionTier.LONG,
            duration=timedelta(days=365 * 5),  # 5 ev
            legal_basis="HU Civil Code contract retention",
        ),
        RetentionRule(
            rule_id="default_general",
            document_type=None,  # fallback
            tier=RetentionTier.STANDARD,
            duration=timedelta(days=365),
            legal_basis="Default business retention",
        ),
        RetentionRule(
            rule_id="policy_violation_quarantine",
            document_type=None,
            tier=RetentionTier.LONG,
            duration=timedelta(days=365 * 7),
            legal_basis="Compliance audit trail (7 years)",
            deletion_mode="manual_approval",  # kotelezo jovahagyas
        ),
    ]
    
    def get_retention(
        self,
        document_type: str,
        tenant_id: str,
    ) -> RetentionRule:
        """Get retention rule with tenant + doc-type override."""
        # 1. Try tenant + doc_type override
        override = self.tenant_overrides.get((tenant_id, document_type))
        if override:
            return override
        
        # 2. Try tenant default
        tenant_default = self.tenant_overrides.get((tenant_id, None))
        if tenant_default:
            return tenant_default
        
        # 3. Try doc_type default
        for rule in self.DEFAULT_RULES:
            if rule.document_type == document_type:
                return rule
        
        # 4. Fallback
        return next(r for r in self.DEFAULT_RULES if r.rule_id == "default_general")


@scheduled(cron="0 2 * * *")  # every day at 2 AM
async def retention_enforcement_job():
    """Background job to enforce retention policy."""
    expired_artifacts = await archival_repo.find_expired_retention()
    
    for artifact in expired_artifacts:
        rule = retention_policy.get_retention(
            artifact.document_type,
            artifact.tenant_id,
        )
        
        if rule.deletion_mode == "auto":
            await archival_service.safe_delete(artifact)
            await audit.log_retention_delete(artifact, rule)
        elif rule.deletion_mode == "manual_approval":
            # Create review task
            await review_service.create_task(
                review_type=ReviewType.QUARANTINE,
                title=f"Retention expired: {artifact.artifact_id}",
                description=f"Manual approval required for deletion. Rule: {rule.rule_id}, Legal: {rule.legal_basis}",
            )
```

#### PDF/A profile override per-tenant

Kiegeszitve a `RetentionPolicy`-hez hasonloan, a PDF/A profile per-tenant override:

```python
# src/aiflow/archival/profile_selector.py
class PDFAProfileSelector:
    """Select PDF/A profile per tenant + document type."""
    
    def get_profile(
        self,
        tenant_id: str,
        document_type: str,
    ) -> PDFAProfile:
        """Tenant + doc type override, fallback to global."""
        override = self.tenant_profiles.get((tenant_id, document_type))
        if override:
            return override
        return self.tenant_profiles.get((tenant_id, None), PDFAProfile.A_2B)
```

Config:

```yaml
# instances/{customer}/archival_policy.yaml
archival:
  default_pdfa_profile: PDF/A-2b
  
  per_document_type:
    invoice: PDF/A-2b      # kisebb, standard invoice use case
    contract: PDF/A-1a     # legacy compatibility, szigorubb
    scan: PDF/A-3b         # embedded files support
```

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/archival/retention_policy.py`
2. **Letrehoz**: `src/aiflow/archival/profile_selector.py`
3. **DB migration 034c**: `retention_rules` tabla (per-tenant overrides)
4. **Background job**: `retention_enforcement_job` (APScheduler)
5. **API endpoint**: `GET /api/v1/retention/rules?tenant_id=...`
6. **API endpoint**: `PUT /api/v1/retention/rules/{rule_id}` (tenant override)
7. **Test**: 10+ test (default rules + override + expiration + manual approval)
8. **Doc**: `docs/archival/retention_policy.md` (legal basis per country)

#### Intermediate artifact kezeles

A Gotenberg konvertalas kozben keletkezo intermediate artifact-ok (tmp fajlok):

```python
# src/aiflow/archival/gotenberg_adapter.py (N11 kibovites)
class GotenbergArchivalAdapter:
    async def convert_to_pdfa(self, source_file: Path, ...) -> Path:
        """Convert source to PDF/A with cleanup of intermediates."""
        intermediate_path = None
        try:
            # Upload to Gotenberg
            response = await self.client.post("/forms/chromium/convert/url", ...)
            intermediate_path = Path(f"/tmp/{uuid4()}.pdf")
            intermediate_path.write_bytes(response.content)
            
            # Move to persistent storage
            final_path = await self.object_storage.put_from_path(
                intermediate_path,
                self.path_builder.archival_path(artifact_id, profile.value),
            )
            return final_path
        finally:
            # ALWAYS cleanup intermediate
            if intermediate_path and intermediate_path.exists():
                intermediate_path.unlink()
```

#### Acceptance criteria

- [ ] `RetentionPolicy` + default rules mukodik
- [ ] Per-tenant override
- [ ] Per-document-type override
- [ ] Background retention_enforcement_job
- [ ] `PDFAProfileSelector` per-tenant + per-doc-type
- [ ] Intermediate artifact cleanup (Gotenberg)
- [ ] 10+ test
- [ ] Legal basis docs per country (`docs/archival/retention_hu.md`)

---

### N13/N14/N15 — Embedding providers

> Lasd R5 — ott reszletezve. N13 = BGE-M3, N14 = e5-large, N15 = Azure OpenAI.

---

### N16 — `embeddings/redaction_gate.py:RedactionGate`

> Lasd R14 — ott reszletezve.

---

### N17 — `audit/lineage.py:LineageTracker`

**Komponens azonosito:** N17
**Phase:** 3
**Komplexitas:** M
**Risk:** Alacsony

#### Cel allapot

```python
# src/aiflow/audit/lineage.py
class LineageEvent(BaseModel):
    event_id: str
    event_type: Literal["intake", "parse", "extract", "embed", "store", "review", "archive"]
    parent_event_id: str | None
    file_id: str | None
    package_id: str | None
    provider: str | None
    routing_decision_id: str | None
    timestamp: datetime
    metadata: dict

class LineageTracker:
    """Track file → derivative → extraction → embedding lineage."""

    async def track(self, event: LineageEvent) -> None: ...
    async def get_lineage_for_file(self, file_id: str) -> list[LineageEvent]: ...
    async def get_lineage_for_package(self, package_id: str) -> list[LineageEvent]: ...
```

#### Lepesenkenti vegrehajtas

1. **DB migration 034**: `lineage_events` tabla
2. **Implementald**: `LineageTracker`
3. **Integration**: minden Step + Pipeline + Service emit-eli
4. **API endpoint**: `GET /api/v1/lineage/{package_id}`
5. **UI viewer**: aiflow-admin Audit page
6. **Test**: 15+ test

#### Acceptance criteria

- [ ] LineageTracker mukodik
- [ ] Minden szignifikans muvelet lineage event-tel
- [ ] API endpoint
- [ ] UI viewer
- [ ] 15+ test

---

### N18 — `provenance/map.py:ProvenanceMap`

**Komponens azonosito:** N18
**Phase:** 3
**Komplexitas:** S
**Risk:** Alacsony

#### Cel allapot

- file ↔ description ↔ package ↔ tenant mapping
- Searchable: "milyen file-ok kotodnek a kovetkezo case-hez?"

#### Lepesenkenti vegrehajtas

1. **DB**: `provenance_map` tabla (alembic 035)
2. **Implementald**: `ProvenanceMap` service
3. **Test**: 10+ test

#### Acceptance criteria

- [ ] Bidirectional searchable
- [ ] 10+ test

---

### N19/N20 — OTel + Prometheus

> Lasd R10/R9 — ott reszletezve.

---

### N21 — Vault prod impl

> Lasd R8 — ott reszletezve.

---

### N22 — `agents/crewai_sidecar/CrewAIBoundedReasoningService`

**Komponens azonosito:** N22
**Phase:** 3
**Komplexitas:** L
**Risk:** Kozepes

> **FONTOS:** Ez a komponens a `100_*.md` **ADR-1** dontes alapjan **bounded sidecar**
> formaban kerul be, **NEM core orchestrator**. Az ADR-1 reszletes szakmai elemzese
> 18 ervet (15 architekturalis + 3 uzleti) sorol fel, amiert a CrewAI nem lehet a
> teljes AIFlow vegrehajtasi motorja. A jelenlegi N22 a **Hybrid (A+C)** alternativa
> implementacioja. A Phase 3-ban indul egy **controlled experiment** (D alternativa
> step-opt-in adapter) 2 specialist-en, melynek metrikai dontik el, hogy a CrewAI
> step-szintu adapter szelesebb hasznalatra javasolhato-e.

#### Cel allapot

```python
# src/aiflow/agents/crewai_sidecar/service.py
class CrewAIBoundedReasoningService:
    """Optional bounded agentic reasoning sidecar.

    USE CASES:
    - intake package interpretation (multi-file ambiguity)
    - file-to-description association (LLM fallback)
    - cross-document consistency reasoning
    - low-confidence triage / review preparation
    - operator copilot

    NOT FOR:
    - parser routing core
    - archival / PDF-A
    - policy enforcement
    - tenant boundary
    - idempotent state
    - compliance state transitions
    """

    def __init__(
        self,
        flows: dict[str, CrewAIFlow],
        crews: dict[str, Crew],
        policy_engine: PolicyEngine,
        validator: StructuredOutputValidator,
    ): ...

    async def run(
        self,
        flow_name: str,
        input_data: BaseModel,
    ) -> BaseModel:
        """Run a CrewAI flow with structured input/output validation."""
        # 1. Validate input schema
        # 2. Execute flow with retry/fallback
        # 3. Validate output schema (Pydantic)
        # 4. Confidence threshold check
        # 5. Business rule validation
        # 6. If invalid → retry / fallback / manual review
```

**Tipikus flow-k**:
- `intake_package_interpretation_flow`
- `file_description_association_flow`
- `cross_document_consistency_flow`
- `low_confidence_triage_flow`
- `operator_copilot_flow`

#### Lepesenkenti vegrehajtas

1. **Add dep**: `crewai>=0.40` → `pyproject.toml` `[agentic]` extra
2. **Definialj**: `CrewAIFlow`, `Crew`, `Task`, `Tool` Pydantic adapterek
3. **Implementald**: `CrewAIBoundedReasoningService`
4. **Validator**: `StructuredOutputValidator` — Pydantic + business rules
5. **Flow #1**: `intake_package_interpretation_flow` (Phase 3 first delivery)
6. **Test**: 15+ test
7. **Doc**: `docs/agents/crewai_sidecar.md`
8. **Fail-safe**: ha CrewAI exception → fallback rule-based + manual review flag

#### Risk

- **Determinizmus**: CrewAI nem determinisztikus → strict validacios layer kotelezo
- **Latency**: agentikus reasoning lassu → opcionalis sidecar, NEM happy path
- **Cost**: LLM hivasok dragak → confidence-driven trigger

#### Acceptance criteria

- [ ] CrewAI sidecar opcionalis (default disabled)
- [ ] Strukturalt I/O validacio kotelezo
- [ ] Fail-safe: hibas output → fallback
- [ ] 15+ test
- [ ] Phase 3 acceptance: intake package interpretation flow

---

### N22b — `agents/crewai_step_adapter/` Step-szintu opt-in CrewAI adapter (CONTROLLED EXPERIMENT)

**Komponens azonosito:** N22b
**Phase:** 3 (controlled experiment)
**Komplexitas:** M
**Risk:** Kozepes
**Dontesi forras:** ADR-1 (`100_*.md`), D alternativa

#### Cel allapot

```python
# src/aiflow/agents/crewai_step_adapter/adapter.py
class CrewAIStepAdapter:
    """Optional CrewAI Crew adapter for AIFlow Specialist Agents.

    Allows ONE specialist to be REPLACED with a CrewAI Crew implementation
    while keeping the same input/output Pydantic contract. This is a CONTROLLED
    EXPERIMENT in Phase 3 — NOT a generic CrewAI core orchestrator.

    See ADR-1 in 100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md
    """

    def __init__(
        self,
        crew_definition: CrewDefinition,
        input_schema: type[BaseModel],
        output_schema: type[BaseModel],
        timeout_seconds: int = 60,
        max_retries: int = 2,
    ): ...

    async def execute(
        self,
        input_data: BaseModel,
        ctx: ExecutionContext,
    ) -> BaseModel:
        """Run CrewAI Crew with validated input/output."""
        # 1. Validate input schema
        # 2. Initialize Crew (cached)
        # 3. Run Crew with timeout
        # 4. Validate output Pydantic
        # 5. If invalid → retry / fallback to native specialist
```

#### Controlled Experiment Setup (Phase 3)

**Hipotezis**: A CrewAI Crew-alapu specialist >= 10%-kal jobb minoseggel
mukodik mint az AIFlow native specialist, **es** legfeljebb 50%-kal dragabb
latency / cost-tal.

**Variansok** (2 specialist):

| Specialist | Control (A) | Treatment (B) |
|-----------|-------------|---------------|
| `ClassifierAgent` | jelenlegi (ML+LLM hybrid) | CrewAI Crew (3 agent: feature_extractor, ml_predictor, llm_validator) |
| `ExtractorAgent` | jelenlegi (LLM+schema) | CrewAI Crew (3 agent: section_finder, field_extractor, validator) |

**Metrikak**:

| Metrika | Mero | Threshold |
|---------|------|----------|
| Accuracy (vs golden dataset) | Promptfoo eval | >= 10% jobb |
| Latency p50 | Langfuse | <= 50% lassabb |
| Latency p95 | Langfuse | <= 100% lassabb |
| Cost per call | cost_records | <= 50% dragabb |
| Hallucinacio rate | Hallucination evaluator | <= 5% |
| Confidence calibration | B3.5 framework | >= jelenlegi |

**Idotartam**: 2 ho live A/B teszt, 50/50 split, valos production traffic.

**Dontesi mate**:
- HA mind a 2 specialist-nel a treatment szignifikansan jobb (statisztikai teszt) → CrewAI step-szintu adapter elfogadva, opcio kibovitese egyebb specialist-ekre v2.0.0-ban
- HA reszben jobb (1/2) → tovabbi A/B teszt v1.7.0-ig
- HA egyik sem szignifikansan jobb → ADR-1 marad, CrewAI csak bounded sidecar (N22)

#### Lepesenkenti vegrehajtas

1. **Letrehoz**: `src/aiflow/agents/crewai_step_adapter/__init__.py`
2. **Implementald**: `CrewAIStepAdapter`
3. **Crew definitions**: `agents/crewai_step_adapter/crews/{classifier,extractor}_crew.yaml`
4. **A/B framework**: `services/quality/ab_test.py` integrate
5. **Feature flag**: `AIFLOW_FEATURE_CREWAI_STEP_ADAPTER=true/false`
6. **Routing**: `WorkflowRunner` flag-alapjan valaszt control / treatment
7. **Metrika gyujtes**: Langfuse trace-ben markup
8. **Test**: 15+ unit teszt + 5 integration teszt
9. **Doc**: `docs/agents/crewai_step_adapter_experiment.md`
10. **Phase 3 reportnal**: `103_*.md` ciklusban experiment eredmeny dokumentalva

#### Risk

- **Csak ket specialist az experiment-ben**: az eredmény nem feltetlenul altalanosithato
- **Nem-determinisztikus**: a CrewAI valasz NEM reproducible 100%-ban
- **Maintenance**: ket implementacio fenntartasa
- **Cost**: A/B teszt 2x cost rovid tavon

#### Acceptance criteria

- [ ] `CrewAIStepAdapter` mukodik 2 specialist-en
- [ ] Feature flag enable/disable
- [ ] A/B framework gyujti a metrikakat
- [ ] 2 ho lefutotta utan dontes-tabla a `103_*.md`-ben
- [ ] Fail-safe: control mindig elerheto

---

### N23 — `cli/aiflow.py` typer CLI bovites

**Komponens azonosito:** N23 / K11
**Phase:** 3
**Komplexitas:** M
**Risk:** Alacsony

#### Cel allapot

```bash
aiflow prompt sync --skill aszf_rag_chat
aiflow prompt diff --skill aszf_rag_chat --from prod --to dev
aiflow prompt promote --skill aszf_rag_chat --from dev --to prod

aiflow workflow run invoice_finder --input '{"connector_id": "outlook"}'
aiflow workflow inspect <run_id>
aiflow workflow docs invoice_finder

aiflow eval run --skill aszf_rag_chat
aiflow eval report --skill aszf_rag_chat --output html
```

#### Lepesenkenti vegrehajtas

1. **Bovits**: `src/aiflow/cli/main.py` typer commands
2. **Modularizacio**: `cli/commands/{prompt,workflow,eval}.py`
3. **Test**: 15+ test (typer CliRunner)
4. **Doc**: `docs/cli/usage.md`

#### Acceptance criteria

- [ ] 9 CLI command mukodik
- [ ] Output format: rich table / JSON
- [ ] 15+ test

---

### N24 — `services/graph_rag/microsoft_lazygraphrag.py`

**Komponens azonosito:** N24 / K10
**Phase:** 4
**Komplexitas:** L
**Risk:** Magas

#### Cel allapot

- Microsoft `graphrag` Python csomag integracio
- LazyGraphRAG mode (NEM build full graph upfront)
- Provider integration via embedding registry (N13-N15)

#### Lepesenkenti vegrehajtas

1. Lasd `50_RAG_VECTOR_CONTEXT_SERVICE.md` Phase 7E
2. Phase 4 deferred — opcionalis

---

### N25 — `messaging/kafka_adapter.py`

**Komponens azonosito:** N25
**Phase:** 4
**Komplexitas:** M
**Risk:** Kozepes

#### Cel allapot

- `aiokafka` async client
- Topic-based event publishing
- Consumer group management

#### Lepesenkenti vegrehajtas

1. Lasd `DEVELOPMENT_ROADMAP.md` Apache Kafka
2. Phase 4 deferred — opcionalis

---

## KIVALTANDO ELEMEK (K-szeria)

> Reszletek a R/N komponens szekciokban. Itt csak osszefoglalo.

| # | Kivaltando | Leiras | Helye | Phase |
|---|-----------|--------|-------|-------|
| K1 | `email_connector` direkt pipeline hasznalat | Email source adapter wrappel | R1 | 1 |
| K2 | `DoclingParser` mint default univerzalis | Multi-signal routing engine valaszt | R2/N7 | 2 |
| K3 | `attachment_processor.py` hardcoded routing | Multi-signal routing engine refaktor | R3/N7 | 2 |
| K4 | `text-embedding-3-small` hardcoded | Embedder provider abstraction | R5/N13-15 | 2 |
| K5 | `VaultSecretProvider` STUB | hvac prod impl | R8 | 3 |
| K6 | Manualis "auto" parser dontes | RoutingDecision audit trail | N7 | 2 |
| K7 | Hardcoded `azure_enabled` per template | Policy engine + tenant override | R3/N5 | 1-2 |
| K8 | `prometheus-client` deklaralt, kod nincs | Prometheus metrics impl | R9/N20 | 3 |
| K9 | `opentelemetry-sdk` deklaralt, kod nincs | OTel tracer impl | R10/N19 | 3 |
| K10 | `services/graph_rag/` STUB | Phase 4 dontes (impl vagy ledobas) | N24 | 4 |
| K11 | `cli/` szubmodul stub-jai | Tenyleges typer CLI | N23 | 3 |
| K12 | Hardcoded confidence kuszobok | Confidence Calibration Layer | R11 | 3 |
| K13 | `pdf_parser.py`, `docx_parser.py` (mar torolt) | DoclingParser + uj parserek | mar tortent | 0 |

---

## Fazis Osszefoglalo (Phase 1-4 task-listak)

> **FONTOS:** A Phase 1 1a/1b/1c/1.5-re bontva a `103_*` Section 3-ban. Az alabbi osszefoglalo
> a bontott forma — **a 103_ a definitive** az acceptance criteria reszleteiben.

### Phase 1a — Foundation (v1.4.0)

| Task | Komponens | Szint |
|------|-----------|-------|
| 1a.1 | `100_b` 13 Pydantic contract implementacio + alembic 030 | M |
| 1a.2 | `100_c` 7 entitas state machine + state transition validator | M |
| 1a.3 | N3 IntakeNormalizationLayer | S |
| 1a.4 | N5 PolicyEngine + 30+ parameter | M |
| 1a.5 | `config/profiles/profile_a.yaml` + `profile_b.yaml` | S |
| 1a.6 | N6 ProviderRegistry + 4 ABC + contract test framework | S |
| 1a.7 | R13 SkillInstance policy override | S |
| 1a.8 | `100_d` backward compat shim layer | S |
| 1a.9 | Phase 1a acceptance E2E + tesztek | M |

### Phase 1b — Source adapters (v1.4.1)

| Task | Komponens | Szint |
|------|-----------|-------|
| 1b.1 | N2 `IntakeSourceAdapter` ABC | S |
| 1b.2 | R1 `email_source.py` (Unstructured + email_connector wrap) | M |
| 1b.3 | N2 `file_source.py` (UI upload) | S |
| 1b.4 | N2 `folder_source.py` (S3 + local fs) | M |
| 1b.5 | N2 `batch_source.py` (manual batch API) | S |
| 1b.6 | N2 `api_source.py` (webhook) | S |
| 1b.7 | N4 FileDescriptionAssociator (4 mode) | M |
| 1b.8 | API endpoint `POST /api/v1/intake/upload-package` | S |
| 1b.9 | Phase 1b acceptance E2E (5 source) | M |

### Phase 1c — Refactor + acceptance (v1.4.2)

| Task | Komponens | Szint |
|------|-----------|-------|
| 1c.1 | R4 document_extractor `extract_from_package()` | M |
| 1c.2 | `extraction_results` tabla kibovites (alembic 033) | S |
| 1c.3 | Pipeline auto-upgrade shim | S |
| 1c.4 | R12 `invoice_automation_v2.yaml` multi-source pelda | S |
| 1c.5 | R15 `pipeline/adapters/*` egyseges provider interface | S |
| 1c.6 | UI: invoice_finder oldal multi-file upload | M |
| 1c.7 | Phase 1 vegleges acceptance E2E (10 processing flow) | L |
| 1c.8 | Customer notification + dokumentacio | S |

### Phase 1.5 — Vault + Self-hosted Langfuse (v1.4.5)

| Task | Komponens | Szint |
|------|-----------|-------|
| 1.5.1 | R8/N21 `VaultSecretProviderImpl` (hvac) | M |
| 1.5.2 | Vault testcontainers integration test | S |
| 1.5.3 | `infra/langfuse/docker-compose.yaml` self-hosted | S |
| 1.5.4 | Profile A config: `LANGFUSE_HOST=https://langfuse.internal` | S |
| 1.5.5 | Profile A E2E acceptance air-gapped kornyezetben | M |
| 1.5.6 | Customer migration guide Profile A-ra | S |

### Phase 2 — Architectural refinements (v1.5.0 - v1.5.4)

| Sprint | Verzio | Task | Komponens | Szint |
|--------|--------|------|-----------|-------|
| **2a** | v1.5.0 | Multi-signal routing engine | N7 (+ 103_* Section 4 governance) | L |
| 2a | v1.5.0 | PyMuPDF4LLMParser fast-path | N8 | S |
| 2a | v1.5.0 | DoclingParser provider adapter | R2 | S |
| **2b** | v1.5.1 | DoclingVLMParser (VLM + vLLM) | N9 | M |
| 2b | v1.5.1 | Qwen25VLClassifier visual | R6 + N10 | M |
| 2b | v1.5.1 | vLLM infra setup | — | M |
| **2c** | v1.5.2 | Embedder provider abstraction | R5 + N13/N14/N15 | M |
| 2c | v1.5.2 | PII RedactionGate | N16 | S |
| 2c | v1.5.2 | Multi-tenant collection ID (103_* Section 6) | R5 isolation | S |
| 2c | v1.5.2 | Re-embedding migration script | `100_d` Section 5 | S |
| **2d** | v1.5.3 | Gotenberg archival adapter | N11 | S |
| 2d | v1.5.3 | veraPDF validator | N12 | S |
| 2d | v1.5.3 | Archival quarantine + retention (Should fix SF1) | N11b + N11c | S |
| 2d | v1.5.3 | Azure DI provider refactor | R3 | S |
| 2d | v1.5.3 | data_router cross-document context | R7 | S |
| **2e** | v1.5.4 | Phase 2 acceptance: 10 processing flow E2E | — | M |
| 2e | v1.5.4 | Phase 2 Profile A + Profile B teljes | — | M |

### Phase 3 (v1.6.0) — 10 task

| Task | Komponens | Szint |
|------|-----------|-------|
| P3.1 | N17 LineageTracker | M |
| P3.2 | N18 ProvenanceMap | S |
| P3.3 | R10 + N19 OTel tracer | M |
| P3.4 | R9 + N20 Prometheus metrics | M |
| P3.5 | R8 + N21 Vault prod impl | S |
| P3.6 | N23 typer CLI bovites | M |
| P3.7 | R11 Confidence Calibration Layer | M |
| P3.8 | N22 CrewAI sidecar | L |
| P3.9 | LangGraph state machine adapter (opt) | M |
| P3.X | Phase 3 audit + sign-off | M |

### Phase 4 (v2.0.0+) — 5 opcionalis task

| Task | Komponens | Szint |
|------|-----------|-------|
| P4.1 | N24 Microsoft GraphRAG | L |
| P4.2 | N25 Kafka event bus | M |
| P4.3 | Multi-tenant SaaS hardening | L |
| P4.4 | Azure AI Search vector store | M |
| P4.5 | n8n editor integracio | M |

---

## Kovetkezo lepes

A terv **ELFOGADVA** (103_* 2. ciklus sign-off utan). A kovetkezo lepesek:

1. **`104_AIFLOW_v2_FINAL_MASTER_INDEX.md`** — egyseges belepesi pont a teljes dokumentum-setben
2. **Phase 1a kickoff** (v1.4.0 sprint):
   - `100_b` contractok implementacio (alembic 030-031)
   - `100_c` state machine validator
   - N5 PolicyEngine
   - N6 ProviderRegistry + 4 ABC (103_* Section 5)
3. **Phase 1a acceptance** — `103_*` Section 9.1 checklist kovetese

### Historikus ciklusok (referencia)

- `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` — 1. enterprise review (Must/Should fix)
- `103_AIFLOW_v2_FINAL_VALIDATION.md` — 2. ciklus + sign-off + Phase 1/2 bontas
