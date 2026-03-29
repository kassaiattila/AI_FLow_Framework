# Intent Discovery + Custom ML Training Pipeline

## Context

Az email_intent_processor skill jelenleg **LLM-only** módban fut, mert nincs betanított sklearn modell (`models/intent_model.joblib` nem létezik). A 10 intent előre definiált a `schemas/v1/intents.json`-ban, de ezek nem a valós adatokból származnak. 41 valós .eml fájl áll rendelkezésre a `test_emails/` mappában.

**Meglévő CFPB modell:** `C:\Users\kassaiattila\BestIxCom Kft\Bestix Kft. - Documents\07_Szakmai_Anyagok\AI\Cubix_AI_ML\01_Pilot_ML\01_cfpb_complaints\models\intent_routing_model.joblib` — ezt be kell másolni a projektbe.

**Korábbi commit-ok állapota:**
- `bdb7004` — Audit: agents/ törlés, cfpb összevonás, 20+ terv frissítés ✅
- `04dc103` — aszf_rag_chat 52 unit teszt ✅
- `1ecad4f` — email_intent 54 teszt ✅
- A 01_PLAN/ dokumentumok frissítve és commitálva vannak az audit alapján.
- Az Intent Discovery terv **új fejlesztés** — a projekt terv fájlokba (01_PLAN/) az implementáció után kerül be.

**Cél:** Egy generikus, újrafelhasználható pipeline, ami:
1. Valós emailekből felfedezi a természetes intent kategóriákat (discovery)
2. LLM-mel automatikusan címkézi az emaileket (labeling)
3. Custom sklearn modellt tanít a címkézett adatból (training)
4. A modellt a meglévő HybridClassifier-be integrálja (deployment)
5. Produkciós predikciókból folyamatosan tanul (continuous learning)
6. Claude Code slash command-okkal segíti az ML fejlesztést (LLM-assisted tooling)

**Megközelítés:** Kettős támogatás — determinisztikus kód (sklearn pipeline) + LLM-alapú Claude Code tooling (slash commands, CLAUDE.md kontextus) az egyedi helyzetek és minőségjavítás kezelésére.

---

## Fázis 0: Referencia anyagok elérhetővé tétele

### 0.1 CFPB modell bemásolása + tesztelés
- **Forrás:** `C:\Users\kassaiattila\BestIxCom Kft\...\01_Pilot_ML\01_cfpb_complaints\models\intent_routing_model.joblib`
- **Cél:** `skills/email_intent_processor/models/intent_model.joblib`
- Ez azonnal aktiválja a `sklearn_first` stratégiát (a workflow auto-detect-eli)
- **Teszt:** Futtatjuk a valós emaileken és megnézzük milyen intent-eket ad (baseline)
- A CFPB modell angol/pénzügyi panaszokra tanult → a magyar emailekre valószínűleg nem fog jól működni, de kiindulópont

### 0.2 ML referencia anyagok hozzáadása (TELJES feldolgozott_tananyag/)
A Cubix ML kurzus teljes feldolgozott anyaga bemásolásra kerül:
- **Forrás:** `C:\Users\kassaiattila\BestIxCom Kft\...\03_Cubix_ML\feldolgozott_tananyag\` (teljes mappa)
- **Cél:** `skills/email_intent_processor/reference/ml_methodology/`
- **reference/CLAUDE.md** frissítés az új anyagokkal
- `.gitignore`: a .joblib fájlok és nagy dataset-ek (> 10MB) ne kerüljenek git-be

### 0.3 Test email bővítési lehetőség
- Az IMAP fetch script (`scripts/fetch_emails_imap.py`) paraméterei módosíthatók:
  - Email szám: `--limit N` (jelenleg 15)
  - Időablak: `--since YYYY-MM-DD` (régebbi emailek is lekérhetők)
  - Mappa: `--folder INBOX` (más mappák is elérhetők)
- Több email = jobb intent discovery + több training adat

---

## Fázis A: Alapok (1. nap)

### A1. Training data formátum (`training/schemas.py`)
- `TrainingExample` Pydantic model: id, subject, body, sender, intent, sub_intent, confidence, source (manual/llm_labeled/production/corrected), labeled_by, labeled_at
- `TrainingDataset` model: samples lista, intent_distribution property, validate_intents()
- Load/save YAML + CSV formátum
- merge_datasets(), split_dataset() segédfüggvények
- **Fájl:** `skills/email_intent_processor/training/schemas.py`

### A2. Email loader (`discovery/email_loader.py`)
- `DiscoveryEmail` model: file_path, subject, body, sender, date, language_hint
- `load_emails_from_dir(path)` — rekurzív .eml scan, Python email modul dekódolás
- Újrahasználja: `scripts/eml_viewer.py::decode_eml()` logikát + `aiflow.tools.email_parser.EmailParser`
- **Fájl:** `skills/email_intent_processor/discovery/email_loader.py`

### A3. clean_text() kiemelés
- `SklearnClassifier._clean_text()` — már `@staticmethod`, modul szintű alias hozzáadása
- **KRITIKUS:** `strip_accents=None` a TfidfVectorizer-ben (magyar ékezetek megőrzése!)
- **Fájl:** `skills/email_intent_processor/classifiers/sklearn_classifier.py` (kis módosítás)

---

## Fázis B: Intent Discovery (2. nap)

### B1. Discovery prompt-ok
- `prompts/intent_discovery.yaml` — "Elemezd ezeket az emaileket, fedezd fel milyen kategóriák léteznek"
- `prompts/intent_consolidation.yaml` — "Vonjd össze a talált kategóriákat 5-15 kanonikus intent-be"
- **Nem** adjuk meg az előre definiált kategóriákat — a LLM organikusan fedezi fel

### B2. Intent Discoverer (`discovery/intent_discoverer.py`)
**Két lépéses algoritmus:**
1. **Pass 1 — Egyedi klasszifikáció:** Minden emailt elküld gpt-4o-nak (nem mini!), kér: intent label, leírás, confidence, kulcsszavak. Batch: 5-10 email/hívás.
2. **Pass 2 — Konszolidáció:** Az összes felfedezett label-t elküldi a LLM-nek: "Vonjd össze duplikátumokat, adj kanonikus id-t, display_name-t, description-t, keywords_hu-t"
3. **Schema összehasonlítás:** Betölti `intents.json`-t, összeveti: mely előre definiált intentek validálódtak, melyek hiányoznak, melyek újak

**Output:** `DiscoveryResult` — discovered_intents, email_assignments, comparison_with_schema

### B3. Claude Code command: `/discover-intents`
- **Fájl:** `.claude/commands/discover-intents.md`
- **Funkció:** Claude Code elemzi a test_emails/ mappát, a kódot, és a schema-t, majd:
  - Futtatja a discovery scriptet
  - Értelmezi az eredményeket
  - Javaslatot tesz az intents.json frissítésére
  - Edge case-eknél egyedi elemzést ad (pl. "ez az email complaint vagy feedback?")

---

## Fázis C: LLM-alapú címkézés (3. nap)

### C1. LLM Labeler (`training/llm_labeler.py`)
- `LLMLabeler` osztály: models_client, prompt_manager, schema_intents
- `label_emails(emails, min_confidence)` → TrainingDataset
- gpt-4o használata (nem mini) — magasabb minőség a címkézéshez
- Chain-of-thought: reasoning first, classification second
- Cost tracking: ~$0.01/email, budget limit configolható
- **Prompt:** `prompts/llm_labeler.yaml`

### C2. Label Reviewer (`training/label_reviewer.py`)
- `export_for_review(dataset, path)` — YAML export manuális átnézésre
- `import_corrections(path)` — javított címkék visszaolvasása
- Javított címkék: `source="corrected"`, `confidence=1.0`
- Opcionális: `HumanLoopManager` integráció interaktív review-hoz

### C3. Claude Code command: `/label-emails`
- **Fájl:** `.claude/commands/label-emails.md`
- **Funkció:** Claude Code segít a címkézés review-jában:
  - Megnyitja a generált YAML-t
  - Email-enként elemzi: "Miért kapta ezt a címkét? Egyetértek / Javítom"
  - Ambivalens esetekben többféle interpretációt mutat
  - Véglegesíti a golden datasetet

---

## Fázis D: ML Training Pipeline (4-5. nap)

### D1. Generic Trainer (`training/trainer.py`)
**A központi deliverable.** A CFPB reference pipeline generalizálása:

```python
TrainerConfig:
  max_features: 30000
  min_df: 2             # (nem 5 mint CFPB — kevesebb mintánk van)
  max_df: 0.95
  ngram_range: (1, 2)
  sublinear_tf: True
  strip_accents: None   # KRITIKUS: magyar ékezetek!
  calibrate: True
  cv_folds: 3           # (auto: 2 ha <100 minta)
  class_weight: "balanced"
```

**Pipeline:** `TfidfVectorizer → CalibratedClassifierCV(LinearSVC)`
- Ugyanaz a formátum amit `SklearnClassifier` vár (predict_proba + classes_)
- `_clean_text()` importálva a sklearn_classifier-ből (train = inference preprocesszálás!)
- Auto-adjust: ha dataset < 100 minta → cv=2 vagy skip calibration
- **Output:** `models/intent_model.joblib` + `models/model_metadata.json`

**TrainingReport:** accuracy, macro_f1, weighted_f1, per_class_f1, confusion_matrix, classification_report

### D2. Evaluator (`training/evaluator.py`)
- `ClassifierEvaluator` — összehasonlítja sklearn vs LLM vs hybrid
- Per-class metrics: precision, recall, F1, support
- Confusion matrix
- Latency és cost összehasonlítás
- Agreement matrix: milyen arányban egyezik sklearn és LLM

### D3. Claude Code command: `/train-model`
- **Fájl:** `.claude/commands/train-model.md`
- **Funkció:**
  - Ellenőrzi a training data minőségét (class balance, minta szám, hiányzó intentek)
  - Futtatja a training pipeline-t
  - Értelmezi a metrikákat: "A macro F1 0.72 — ez jó. A 'notification' intent F1-je csak 0.45 — kevés training adat van hozzá."
  - Javaslatokat tesz: "Adj hozzá 10+ 'notification' példát és tanítsd újra"
  - Összehasonlítja az LLM-es eredményekkel

### D4. Claude Code command: `/evaluate-model`
- **Fájl:** `.claude/commands/evaluate-model.md`
- **Funkció:**
  - Futtatja az evaluációt sklearn + LLM + hybrid módban
  - Vizuálisan elemzi a confusion matrix-ot
  - Azonosítja a problémás intent párokat (pl. "complaint és feedback összekeveredik")
  - Javasol megoldást: "Adj hozzá differenciáló kulcsszavakat az intents.json-ba"

---

## Fázis E: Continuous Learning + Integration (6. nap)

### E1. Prediction Collector (`training/collector.py`)
- Produkciós futás során magas-confidence predikciók gyűjtése
- Konfig: `min_confidence: 0.85`, `require_agreement: true` (sklearn + LLM egyezés)
- JSONL append-only storage
- Export TrainingDataset formátumba → retraining

### E2. skill_config.yaml bővítés
```yaml
continuous_learning:
  enabled: false
  collection_path: ./training_data/collected/
  min_confidence: 0.85
  require_agreement: true
```

### E3. CLI subcommandok (`__main__.py` bővítés)
```
python -m skills.email_intent_processor discover --emails ./test_emails/
python -m skills.email_intent_processor label --emails ./test_emails/ --output labeled.yaml
python -m skills.email_intent_processor review --data labeled.yaml
python -m skills.email_intent_processor train --data labeled.yaml --output ./models/
python -m skills.email_intent_processor evaluate --data test.yaml --model ./models/intent_model.joblib
```

---

## Fázis F: Claude Code ML Tooling (párhuzamosan)

### F1. CLAUDE.md frissítés: ML kontextus
- `skills/email_intent_processor/CLAUDE.md` bővítés: ML pipeline dokumentáció, training workflow, slash command-ok listája
- Tartalom: hogyan működik a hybrid classifier, mikor kell újratanítani, hogyan értelmezze a metrikákat

### F2. Slash command-ok összefoglalása

| Command | Fájl | Funkció |
|---------|------|---------|
| `/discover-intents` | `.claude/commands/discover-intents.md` | Valós emailekből intent kategóriák felfedezése |
| `/label-emails` | `.claude/commands/label-emails.md` | LLM címkézés + humán review asszisztálás |
| `/train-model` | `.claude/commands/train-model.md` | Training futtatás + eredmény értelmezés |
| `/evaluate-model` | `.claude/commands/evaluate-model.md` | Modell kiértékelés + javítási javaslatok |

### F3. A slash command-ok értéke
A determinisztikus kód (sklearn pipeline, metrics) adja az alapot, de a Claude Code LLM:
- **Értelmezi** a számokat: "A 0.45 F1 gyenge, de csak 3 mintából tanult"
- **Javasol** konkrét lépéseket: "Adj hozzá X típusú emaileket"
- **Edge case-eket** kezel: "Ez az email complaint VAGY feedback? Kontextus alapján..."
- **Minőséget** ellenőriz: "A training data kiegyensúlyozott? Van bias?"
- **Iterál:** Segít a discover → label → train → evaluate → improve ciklusban

---

## Új fájlok összefoglalása

```
skills/email_intent_processor/
  discovery/
    __init__.py
    email_loader.py              # .eml fájlok betöltése
    intent_discoverer.py         # 2-pass LLM discovery
  training/
    __init__.py
    schemas.py                   # TrainingExample, TrainingDataset
    llm_labeler.py               # LLM auto-labeling
    label_reviewer.py            # Human review
    trainer.py                   # Generic sklearn training
    evaluator.py                 # Metrics, confusion matrix
    collector.py                 # Production prediction gyűjtés
  prompts/
    intent_discovery.yaml        # Discovery prompt
    intent_consolidation.yaml    # Consolidation prompt
    llm_labeler.yaml             # Labeling prompt
  __main__.py                   # MÓDOSÍTÁS: +5 subcommand

.claude/commands/
  discover-intents.md            # Claude Code intent discovery
  label-emails.md                # Claude Code label review
  train-model.md                 # Claude Code training assist
  evaluate-model.md              # Claude Code evaluation assist
```

---

## Verifikáció

### Discovery után:
```bash
python -m skills.email_intent_processor discover --emails ./test_emails/
# Output: discovered_intents.json + comparison report
```

### Training után:
```bash
python -m skills.email_intent_processor train --data training_data/labeled.yaml
# Output: models/intent_model.joblib + TrainingReport
pytest skills/email_intent_processor/tests/ -v  # 54+ teszt PASS
```

### Evaluation:
```bash
python -m skills.email_intent_processor evaluate --data training_data/test.yaml
# Output: per-class F1, confusion matrix, sklearn vs LLM comparison
```

### Hybrid mód aktiválás:
```bash
# Ha models/intent_model.joblib létezik → automatikusan sklearn_first stratégia
python -m skills.email_intent_processor classify --input test_emails/test_complaint.eml
# IntentResult: method="sklearn" (confidence > 0.6) VAGY "hybrid_llm" (escalation)
```

---

## Kockázatok

| Kockázat | Hatás | Mitigáció |
|----------|-------|-----------|
| 41 email kevés ML-hez | Gyenge sklearn teljesítmény | LLM augmentáció + 5-7 összevont intent (nem 10) |
| clean_text() eltérés train/inference | Rossz predikciók | Ugyanaz a függvény importálva + unit teszt |
| strip_accents='unicode' (CFPB) vs None (magyar) | Ékezetek elvesznek | TrainerConfig: strip_accents=None explicit |
| Kis dataset → overfitting CalibratedClassifierCV-vel | Instabil confidence | Auto cv=2 ha <100 minta, skip calibration ha <50 |
| LLM labeling költség nagy email set-nél | Budget túllépés | Cost tracking + configurable budget limit |
