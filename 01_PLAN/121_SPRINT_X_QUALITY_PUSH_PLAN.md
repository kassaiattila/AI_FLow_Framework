# AIFlow v1.8.0 Sprint X — UC1 + UC3 + DocRecognizer Quality Push

> **Status:** PUBLISHED 2026-04-26 by SX-1 honest alignment audit session.
> **Branch convention:** `feature/x-sx{N}-*` (each session its own branch → PR → squash-merge).
> **Parent docs:**
> - `docs/honest_alignment_audit.md` — operator-facing drift recap (SOURCE)
> - `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` — binding policy ("one use-case per sprint")
> - `01_PLAN/ROADMAP.md` — forward queue
> - `docs/SPRINT_HISTORY.md` — Sprint J–W trajectory
> **Predecessor:** v1.7.0 Sprint W (multi-tenant cleanup + boot guard, MERGED).
> **Target tag (post-merge):** `v1.8.0`

---

## 1. Goal

Sprint X szallit **merheto minosegi javulast** harom hasznalati esetre:

1. **UC1 magyar szamla extraction** — `invoice_processor`, accuracy 85.7% → ≥ 92%
2. **UC3 email intent** — `email_intent_processor`, misclass 4% → ≤ 1%
3. **DocRecognizer (UC1-General)** — `document_recognizer`, synthetic-only → real-corpus per-doctype ≥ 80%

UC2 (RAG chat) Sprint Y scope — Sprint X-ben **nem erinti**, baseline 0.55
MRR@5 marad mint Sprint Y starting point.

A sprint **NEM** szallit:
- uj feature-t / scaffold-ot / refactor-t
- multi-tenant cleanup folytatast (SW-FU-3)
- infra/observability bovitest (Sprint Z scope)
- UI polish-t (SV-FU-2/5, SW-FU-2)

A sprint **csak** azt tolja, amitol a 4 UC barmelyike kozelebb kerul a
"production-grade" minosegi szinthez.

### Capability cohort delta

| Cohort | Sprint W close | Sprint X close (target) |
|---|---|---|
| UC1 invoice extraction (synthetic 10-fixture) | 85.7% accuracy | ≥ 92% on 25-fixture (10 synthetic + 10 anonimizalt magyar + 5 OCR) |
| UC1 `issue_date` field | 100% synthetic, real-corpus nem mert | ≥ 95% on real-corpus subset |
| UC3 misclass (25-fixture attachment-aware) | 4% (1/25 — `024_complaint`) | ≤ 1% (max 0/25) |
| UC3 thread-aware | nincs (SP-FU-3 nyitott) | shipped + 5-thread fixture mert |
| DocRecognizer real-corpus accuracy | nincs (synthetic-only) | per-doctype ≥ 80% (`hu_invoice` ≥ 90%) |
| DocRecognizer intent-routing UI | nincs | side-drawer rule editor + 1 Playwright spec |
| DocRecognizer PII redaction roundtrip | boundary-design | E2E test 1 ID-card + 1 passport fixture-on |
| run_quality_baseline.sh | nincs | live, 4 UC merhetoseg, exit code gate |
| Session-prompt template | nincs | live, kotelezo Quality target fej |
| ROADMAP.md aktualis | 8 sprintet kihagyott | jelen shipped state |
| CLAUDE.md meret | ~49 KB / 100+ banner-sor | ~80-100 sor / ~6 KB |

---

## 2. Sessions

### SX-1 — Honest alignment audit + ROADMAP + CLAUDE slim + plan publish (THIS SESSION)

**Scope.** Pure docs/process change. Zero code change to product modules.

1. `docs/honest_alignment_audit.md` (uj) — drift-elemzes + 4-UC baseline + Sprint X/Y/Z direction
2. `01_PLAN/ROADMAP.md` (rewrite) — closed J–W snapshot, active SX, queued SY, conditional SZ
3. `docs/SPRINT_HISTORY.md` (uj) — a regi CLAUDE.md banner athazva
4. `CLAUDE.md` (slim, ~80 sor) — pointer-ek a uj doc-okra
5. `session_prompts/_TEMPLATE.md` (uj) — kotelezo Quality target fej
6. `scripts/run_quality_baseline.sh` (uj) — 4 UC merhetoseg bash kompozit
7. `01_PLAN/121_SPRINT_X_QUALITY_PUSH_PLAN.md` (this file)
8. `session_prompts/NEXT.md` → SX-2 prompt

**Quality target.** Doc-only sprint kickoff; "metric" = doc deliverable
checklist all green. Baseline measure run optionalisan, hogy a Sprint
X-vegi gate-hez referencia legyen.

**Gate.**
- Mind 8 deliverable shipped + commit + PR opened
- `bash scripts/run_quality_baseline.sh --target text` runtime nelkul lefut (ha env nincs, csak interface-validal)
- CLAUDE.md size < 10 KB
- ROADMAP.md `Last refreshed` mezo `2026-04-26`

**Risk.** R-SX1-1: doc-csak sprint nincs sok kozvetlen risk; az egyetlen
csapda, ha a slim CLAUDE.md kihagy egy konvenciot ami session-time-on
fontos. Mitigation: a slim verzio csak rendezett szerkezetu pointer-ekre
csokkent, nem konvencio-tartalom kivagasara.

### SX-2 — UC1 corpus extension + `issue_date` deep-fix

**Scope.** UC1 invoice extraction quality push.

1. **Corpus extension to 25 fixture:**
   - 10 existing synthetic (Sprint Q reportlab-generated) — preserved
   - 10 anonimizalt magyar szamla PDF (operator-driven, `data/fixtures/invoices_sprint_x/anonymized/`)
   - 5 rontott OCR fixture (deliberately blurry / rotated scan, vagy synthetic OCR-noise injekcio) `data/fixtures/invoices_sprint_x/ocr_noise/`
2. **`scripts/measure_uc1_golden_path.py` 25-fixture mode** — `--corpus {synthetic,real,ocr,all}` flag, default `all`
3. **`issue_date` deep-fix** — Sprint Q SQ-FU-1 csak normalize-olt; SX-2 ellenorzi az 25-fixture corpus minden szamlajat es kulonbon-eloldja a hianyokat (lehetséges: alternativ regex-pattern, OCR-confidence-aware fallback, prompt-tuning a `issue_date` extraction step-en)
4. `tests/integration/skills/test_uc1_golden_path.py` — corpus_mode parametrize (synthetic/real/ocr/all)

**Quality target.**
- **Use-case:** UC1 invoice
- **Metric:** accuracy on 25-fixture mixed corpus
- **Baseline:** 85.7% (10-fixture synthetic, Sprint Q)
- **Target:** ≥ 92% on 25-fixture mixed
- **Measurement command:** `bash scripts/run_quality_baseline.sh --uc UC1 --corpus all --output json`

**Gate.**
- 25-fixture corpus accuracy ≥ 92%
- `issue_date` accuracy ≥ 95% on real-corpus subset
- UC1 invoice_processor byte-stable on 10-fixture synthetic (regression check)
- 1 integration test on real OpenAI run (skip-by-default behind `OPENAI_API_KEY`)

**Expected diff.** ~250 LOC + 15 fixture files + ~8 unit + 1 integration. Risk class: medium (real-corpus extraction failure modes hard to predict).

**Risk.**
- R-SX2-1: anonimizalt corpus elerhetlen → SX-2 elhalasztva SX-7-re; SX-3 mehet elobb. Mitigation: operator anonimizalas keszultseg ellenorzes SX-1 PR merge utan.
- R-SX2-2: `issue_date` field fix prompt-tuningot igenyel ami modositja az `invoice_extraction_chain` PromptWorkflow descriptort. Mitigation: byte-stable check a 10-fixture synthetic-on; ha regress, prompt-flag-gel kompromisszum.

### SX-3 — DocRecognizer real-doc corpus + ci-cross-uc slot

**Scope.** DocRecognizer real-corpus quality push.

1. **Real-doc anonimizalt fixture corpus** (operator-driven):
   - `data/fixtures/doc_recognizer/hu_invoice/real_*.pdf` (5 file)
   - `data/fixtures/doc_recognizer/hu_id_card/real_*.png` (5 file, anonimizalt mock-ID)
   - `data/fixtures/doc_recognizer/hu_address_card/real_*.png` (5 file)
   - `data/fixtures/doc_recognizer/eu_passport/real_*.png` (5 file)
   - `data/fixtures/doc_recognizer/pdf_contract/real_*.pdf` (5 file)
2. **`scripts/measure_doc_recognizer_accuracy.py --corpus real`** — uj flag, real-only run
3. **CI integration** — `ci.yml` `doc-recognizer-accuracy` job kibovitese real-corpus 3-doctype slice-szal (skip-by-default, gated by `secrets.OPENAI_API_KEY`)
4. **`nightly-regression.yml` `doc-recognizer-weekly-matrix`** — kibovitve real-corpus minden 5 doctype-on (skip ha `secrets.OPENAI_API_KEY` nincs)
5. **ci-cross-uc UC1-General slot** — Sprint L S113 `ci-cross-uc` suite kapja a DocRecognizer 3-fixture slice-at (synthetic, gyors, < 5 sec)

**Quality target.**
- **Use-case:** DocRecognizer (UC1-General)
- **Metric:** per-doctype real-corpus accuracy (min)
- **Baseline:** N/A (synthetic-only mert eddig)
- **Target:** per-doctype ≥ 80% (`hu_invoice` ≥ 90%, `hu_id_card`/`hu_address_card`/`eu_passport`/`pdf_contract` ≥ 70-80%)
- **Measurement command:** `bash scripts/run_quality_baseline.sh --uc DocRecognizer --corpus real --output json`

**Gate.**
- Mind 5 doctype real-corpus accuracy ≥ 80% (kivéve `eu_passport` ahol ≥ 70% acceptable, ha kevés HU-related fixture)
- ci-cross-uc 42-test → 45-test (3 uj DocRecognizer slice-szal)
- Synthetic 8-fixture top-1 unchanged (regression check)

**Expected diff.** ~150 LOC + 25 fixture file + ~6 unit. Risk: operator-driven anonimizacio (R-SX3-1).

**Risk.**
- R-SX3-1: anonimizalt fixture corpus operator-feedolas — ha nem keszul el kelloеn elobb az SX-3-ig, az SX-3 elhalasztva SX-7-re. Mitigation: SX-1 PR merge utan operator confirmal a corpus-keszultseget.
- R-SX3-2: real-corpus accuracy gap — ha valamely doctype < 80%, az NEM Sprint X bug, hanem a rule-engine inadekvat. Akkor open ML-classifier discussion (DocRecognizer ML — Sprint X scope-on kivul, foljegyez Sprint Z+ candidate).

### SX-4 — UC3 thread-aware classifier + 024_complaint conflict

**Scope.** UC3 email intent quality push — close out the 4% misclass.

1. **Thread-aware classifier (SP-FU-3):**
   - `EmailThread` Pydantic contract (uj, `src/aiflow/contracts/email_thread.py`)
   - `ThreadAwareIntentResolver` — fetched messages-list (`prev_message_ids`) figyelembe vetelevel klasszifikal; default thread_size=5 (max), `AIFLOW_UC3_THREAD_AWARE__ENABLED` flag (default false)
   - `ClassifierService.classify(... thread=None)` extension (additive, byte-stable on flag-off)
   - 5-thread fixture corpus `data/fixtures/emails_sprint_x_threads/`
2. **`024_complaint` conflict resolution (SP-FU-1):**
   - Body-vs-attachment conflict: body says "panasz", attachment is invoice — current LLM-fallback misclassifies as `complaint` instead of correct `payment_dispute`
   - Megoldasi opciok: (a) finomabb prompt explicitly mentions body-vs-attachment dimension, (b) escalation rule "if body sentiment + attachment financial → manual_review", (c) thread-aware (vegigjar a thread elozo email-jein, latva azt a context-et)
   - Selected: opcio (b) — explicit escalation rule because intractable single-conflict; SX-4 valid response is `manual_review` + `reason: "body-vs-attachment conflict, requires human"`
3. **measure_uc3 scriptek migracio uniform `--output`:**
   - `scripts/measure_uc3_baseline.py` + `scripts/measure_uc3_attachment_intent.py` + `scripts/measure_uc3_attachment_extract_cost.py` + `scripts/measure_uc3_llm_context.py` mind kapja az `argparse_output()` helper-t (S156 minta)
   - `run_quality_baseline.sh --uc UC3` mostantol `measure_uc3_attachment_intent.py --output json`-t hivja

**Quality target.**
- **Use-case:** UC3 email
- **Metric:** misclass rate on 25-fixture attachment-aware corpus
- **Baseline:** 4% (1/25 — `024_complaint`)
- **Target:** ≤ 1% (max 0/25 → 0% on Sprint P corpus; thread-fixture corpus separate metric)
- **Measurement command:** `bash scripts/run_quality_baseline.sh --uc UC3 --output json`

**Gate.**
- 25-fixture attachment-aware corpus misclass = 0/25 (or `024_complaint` → `manual_review` accepted)
- 5-thread fixture corpus thread-aware accuracy ≥ 90% (flag-on)
- UC3 byte-stable on flag-off (default)
- All 4 UC3 measure scripts use uniform `--output {text,json,jsonl}`

**Expected diff.** ~400 LOC + 5 thread fixture + ~12 unit + 1 integration. Risk: medium (thread-aware introduces new state surface).

**Risk.**
- R-SX4-1: thread-aware integration cost — fetch prev_message_ids requires additional source adapter call. Mitigation: thread-aware default-off behind `AIFLOW_UC3_THREAD_AWARE__ENABLED=false`.
- R-SX4-2: `024_complaint` resolution `manual_review` not "fix" hanem "escalate" — operator may not consider this misclass-fix. Mitigation: doc-olni a retro-ban + clear gate: `024_complaint` → `manual_review` accepted.

### SX-5 — DocRecognizer admin UI: intent-routing rule editor + PII roundtrip

**Scope.** DocRecognizer operator-facing UI completion + PII safety verification.

1. **Intent-routing rule editor (UC3 intent-rules editor mintaja):**
   - `aiflow-admin/src/pages-new/DocumentRecognizer/IntentRoutingDrawer.tsx` (uj)
   - YAML-editor side-drawer (textarea, mint Sprint V SV-4 — Monaco SV-FU-5 nice-to-have)
   - `intent_routing.conditions` szerkesztheto safe-eval expressionekkel
   - Save → tenant-override YAML (mint a doctype override)
   - Nav: `/document-recognizer/doctypes/{name}` detail page → "Edit intent routing" gomb
2. **PII redaction roundtrip live test:**
   - `tests/ui-live/document-recognizer-pii.md` (uj, markdown journey spec)
   - 1 fixture: `data/fixtures/doc_recognizer/hu_id_card/test_pii_redaction.txt` (synthetic, NEVER use real ID data)
   - 1 fixture: `data/fixtures/doc_recognizer/eu_passport/test_pii_redaction.txt`
   - Journey: upload → recognize → check `extracted_fields` JSONB encrypted at rest (or `pii_redacted=true` tag) → check audit log row contains hash + tag, NEM raw PII → check Langfuse trace span input/output redacted
3. **`tests/integration/services/document_recognizer/test_pii_roundtrip.py`** (uj) — PII boundary unit test (DocRecognitionRepository write redacts; audit log only stores hash; Langfuse trace input redacted)
4. **`/document-recognizer/intent-rules` admin route** + sidebar nav entry

**Quality target.**
- **Use-case:** DocRecognizer
- **Metric:** UI live spec PASS + PII roundtrip test PASS
- **Baseline:** UI nincs; PII redaction csak boundary-design
- **Target:** Playwright PASS + 3 PII roundtrip integration tests PASS
- **Measurement command:** `pytest tests/integration/services/document_recognizer/test_pii_roundtrip.py + bash scripts/start_stack.sh + manual run tests/ui-live/document-recognizer-pii.md`

**Gate.**
- 1 Playwright spec PASS on live admin stack
- 3 PII integration tests PASS (recognize → DB redacted, recognize → audit log redacted, recognize → Langfuse trace redacted)
- intent-routing rule editor save → re-recognize uses new rule (live verification)

**Expected diff.** ~400 LOC TS + ~150 LOC Python + 2 fixture + 3 integration test + 1 Playwright spec.

**Risk.**
- R-SX5-1: PII redaction sub-system incompletely shipped — Sprint V boundary-design szerint csak hash + tag, encrypted JSONB column nem shipped. Mitigation: SX-5 expliciten `extracted_fields_encrypted` Alembic column kerul **csak akkor**, ha az operator opt-in-jet kapunk. Default-rendszer csak hash + tag boundary minden iranyban.
- R-SX5-2: synthetic PII fixture ≠ real PII — a test demonstral, NEM mer real PII roundtrip-et. Mitigation: explicit warning a PR-ben + audit doc.

### SX-6 — Sprint X close + tag v1.8.0

**Scope.** Standard close session + quality baseline gate.

1. `docs/sprint_x_retro.md` — retro (decisions log SX-1..SX-5, what worked / what hurt, follow-ups)
2. `docs/sprint_x_pr_description.md` — cumulative PR description
3. `CLAUDE.md` — Sprint X DONE banner (slim, 1 sor) + key numbers update
4. `01_PLAN/ROADMAP.md` — Sprint X DONE row + Sprint Y status update
5. `session_prompts/NEXT.md` → SY-1 prompt (Sprint Y first execution session)
6. **Sprint X exit gate:** `bash scripts/run_quality_baseline.sh --strict` mind UC1 + UC3 + DocRecognizer target felett. Ha barmely UC alatti, SX-6 NEM zarul; SX-7 extension-session indul.
7. PR opened against `main`, tag `v1.8.0` queued

**Quality target.**
- All 4 UC szam target felett (UC2 erintetlen elfogadott)
- run_quality_baseline.sh exit 0

**Expected diff.** ~80 LOC docs. 0 code change.

**Risk.** R-SX6-1: Sprint X scope creep into SX-6 (operator should freeze scope at SX-5 close). Mitigation: SX-6 csak doc.

---

## 3. Plan, gate matrix

| Session | Use-case | Quality target metric | Threshold | Rollback path |
|---|---|---|---|---|
| SX-1 | (process) | doc deliverable checklist | 8 deliverable shipped | Revert squash; doc-only |
| SX-2 | UC1 invoice | accuracy on 25-fixture | ≥ 92%; `issue_date` ≥ 95% | Revert squash; corpus is additive, prompt-tuning behind flag |
| SX-3 | DocRecognizer | per-doctype real-corpus accuracy | min ≥ 80% (`hu_invoice` ≥ 90%) | Revert squash; corpus + CI additive |
| SX-4 | UC3 email | misclass on 25-fixture | ≤ 1% (max 0/25) | Thread-aware behind flag, default off |
| SX-5 | DocRecognizer | UI live spec + PII roundtrip | Playwright + 3 integ PASS | Revert squash; UI + tests additive |
| SX-6 | (close) | run_quality_baseline.sh PASS | exit 0 | If gate fails → SX-7 extension |

**Threshold column blocks merge.** Any session that fails its gate halts;
the operator either rolls forward (debug) or reverts the session and
reschedules.

---

## 4. Risk register

### R1 — Operator-driven anonimizalt corpus elerhetlen
SX-2 (anonimizalt magyar szamla) + SX-3 (real-PDF doctype corpus)
operator-feedolas. Mitigation: SX-1 PR merge utan operator confirmal a
corpus-keszultseget; ha nem keszul, SX-2/3 elhalasztva SX-7-re; UC1
real-corpus + DocRecognizer real-corpus dimenzio nyitva marad.

### R2 — Prompt-tuning regression a synthetic corpus-on
SX-2 `issue_date` deep-fix + SX-4 UC3 prompt-tuning kockaztat synthetic
regression. Mitigation: byte-stable check minden Sprint X session-ben a
ket synthetic corpus-on (Sprint Q UC1 10-fixture + Sprint P UC3
25-fixture).

### R3 — Thread-aware UC3 introduces new state surface
SX-4 thread-aware classifier additional source adapter call surface.
Mitigation: default-off behind `AIFLOW_UC3_THREAD_AWARE__ENABLED=false`;
flag-off byte-stable.

### R4 — DocRecognizer rule-engine inadekvat real-corpus-on
SX-3 real-corpus accuracy < 80% per-doctype lehet, ha rule-engine
synthetic-only optimalizalt. Mitigation: ha mert eredmeny < 80%,
discussion-mode: ML-classifier (Sprint Z+ candidate); SX-3 nem akadalyoz
sprint-zarast, hanem dokumentaltan jelez. (Modositott gate: per-doctype
≥ 70% = SX-3 PASS; ≥ 80% = ideal.)

### R5 — PII redaction sub-system incompletely shipped
SX-5 a meglevo boundary-design-on epit; nem shipping uj encrypted JSONB.
Mitigation: synthetic fixture-en demonstral, real PII soha NEM kerul a
fixture-be; PR-ben explicit warning.

### R6 — Sprint X scope creep
Sprint M-W mintajaban a sprint kozepen szilettek "kicsit ide csempesszunk
egy kis polish-t" javaslatok. Mitigation: a session-prompt template
expliciten Quality target-et igenyel; ha session-be polish kerul, az
nincs Quality targethez kotve es blockalja az indulast.

---

## 5. Definition of done

- [ ] All 6 sessions (SX-1..SX-6) merged on `main` with green CI
- [ ] UC1 invoice_processor 25-fixture accuracy ≥ 92%
- [ ] UC1 `issue_date` ≥ 95% on real-corpus subset
- [ ] UC3 email_intent_processor 25-fixture misclass ≤ 1%
- [ ] UC3 thread-aware classifier shipped (flag-on test PASS)
- [ ] DocRecognizer per-doctype real-corpus accuracy ≥ 80% (≥ 70% acceptable for `eu_passport`)
- [ ] DocRecognizer admin UI intent-routing rule editor live + 1 Playwright PASS
- [ ] DocRecognizer PII roundtrip test PASS (3 integration)
- [ ] `run_quality_baseline.sh` script live + exit 0 on Sprint X close
- [ ] `session_prompts/_TEMPLATE.md` referenced by all SX-2..SX-5 NEXT.md
- [ ] `01_PLAN/ROADMAP.md` reflects Sprint X DONE + Sprint Y QUEUED
- [ ] `CLAUDE.md` ~80-100 sor, < 10 KB
- [ ] `docs/SPRINT_HISTORY.md` includes Sprint X retro
- [ ] `tag v1.8.0` queued for post-merge
- [ ] `docs/sprint_x_retro.md` + `docs/sprint_x_pr_description.md` published

---

## 6. Out of scope (deferred to Sprint Y or Z)

- UC2 RAG depth — semantic chunker, hybrid search, reembed workflow → Sprint Y
- OTel + Prometheus + Grafana cost panels → Sprint Z
- Coverage uplift 70% → 80% → Sprint Z
- Vault rotation E2E + AppRole IaC → Sprint Z
- SW-FU-1 Langfuse v4 SDK helper → Sprint Z (SDK-fuggo)
- SW-FU-2 admin UI source-toggle widget → Sprint Z
- SW-FU-3 audit script kiterjesztes masik tablakra → Sprint Z
- SV-FU-2/5 UI bundle guardrail / Monaco editor → Sprint Z
- SS-SKIP-2 Profile B Azure live → blocked credit-pending
- DocRecognizer ML classifier → conditional, csak ha SX-3 real-corpus < 80% per-doctype

---

## 7. Skipped items tracker (initial)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SX-SKIP-1 (planned, SX-2) | `tests/integration/skills/test_uc1_25fixture_corpus.py` | UC1 25-fixture corpus run real-OpenAI | `secrets.OPENAI_API_KEY` |
| SX-SKIP-2 (planned, SX-3) | `tests/integration/services/document_recognizer/test_real_corpus.py` | DocRecognizer real-corpus run | `secrets.OPENAI_API_KEY` + operator-anonimizalt fixture |
| SX-SKIP-3 (planned, SX-4) | `tests/integration/skills/test_uc3_thread_aware.py` | UC3 thread-aware integration | `AIFLOW_UC3_THREAD_AWARE__ENABLED=true` + `secrets.OPENAI_API_KEY` |
| SX-SKIP-4 (planned, SX-5) | `tests/ui-live/document-recognizer-pii.md` | PII roundtrip live spec | Live admin stack (`bash scripts/start_stack.sh --full`) |

Sprint W carry-forwards (SW-SKIP-1..4) inherit unchanged into Sprint Y/Z.

---

## 8. STOP conditions

**HARD:**
1. UC1 25-fixture corpus accuracy < 92% on SX-2 → halt; investigate `issue_date` deep-fix or prompt-tuning regression.
2. DocRecognizer real-corpus < 70% per-doctype on SX-3 → halt; ML-classifier discussion (Sprint Z+ candidate).
3. UC3 misclass > 1% on SX-4 → halt; thread-aware regression or `024_complaint` resolution rejected.
4. PII roundtrip test FAIL on SX-5 → halt; PII boundary regression.
5. `run_quality_baseline.sh --strict` exit nonzero on SX-6 → halt; SX-7 extension-session indul.

**SOFT:**
- SX-2 anonimizalt corpus operator-feedolas keses → SX-2 elhalasztva SX-7-re; SX-3 elobb mehet.
- SX-3 real-PDF corpus operator-feedolas keses → SX-3 elhalasztva SX-7-re; SX-4 elobb mehet.

---

## 9. Sprint Y heads-up (kickoff in SX-6)

Sprint X close session (SX-6) deliver-eli a Sprint Y kickoff prompt-jat
(SY-1 first execution session). Sprint Y theme: UC2 RAG depth push
(semantic chunker + hybrid search + reembed workflow + collection
management UI + ingest UI completion). Cel UC2 MRR@5 0.55 → ≥ 0.72.

---

## 10. References

- Honest alignment audit: `docs/honest_alignment_audit.md`
- Use-case-first replan (binding policy): `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
- ROADMAP forward queue: `01_PLAN/ROADMAP.md`
- Sprint history (J–W): `docs/SPRINT_HISTORY.md`
- Sprint W kickoff plan: `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md`
- Session-prompt template: `session_prompts/_TEMPLATE.md`
- Quality baseline script: `scripts/run_quality_baseline.sh`
- DocRecognizer service: `src/aiflow/services/document_recognizer/`
- DocRecognizer admin UI: `aiflow-admin/src/pages-new/DocumentRecognizer/`
- Doctype descriptors: `data/doctypes/`
- PromptWorkflow descriptors: `prompts/workflows/`
- UC1 measure: `scripts/measure_uc1_golden_path.py`
- UC2 measure: `scripts/run_nightly_rag_metrics.py`
- UC3 measures: `scripts/measure_uc3_*.py` (4 db)
- DocRecognizer measure: `scripts/measure_doc_recognizer_accuracy.py`
