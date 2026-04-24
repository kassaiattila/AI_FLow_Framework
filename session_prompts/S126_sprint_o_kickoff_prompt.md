# AIFlow — Session 126 Prompt (Sprint O kickoff — UC3 attachment-aware intent)

> **Datum:** 2026-04-30
> **Branch:** `feature/v1.4.11-uc3-attachment-intent` (cut from `main` @ `13a2f08`, Sprint N squash-merge).
> **HEAD (parent):** TBD (this session's kickoff commit).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S125 — Lane A merge coordination + Lane B kickoff triage. #17 (Sprint M v1.4.9) + #18 (Sprint N v1.4.10) squash-merged, tags `v1.4.9` + `v1.4.10` pushed. Issue #7 coverage uplift landed mid-session (+83 unit tests under `tests/unit/tools/`, 65.6% → 68.5% local). `email_parser.py` Linux-OSError fix landed (long-string `Path.exists()` guard). Lane B theme: **UC3 attachment-aware intent signals** (user pick option 1).
> **Terv:** `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` + `docs/sprint_o_plan.md`.
> **Session tipus:** Kickoff + discovery — build the 25-email fixture, measure baseline, land S127 NEXT.md.

---

## 1. MISSION

Sprint K (v1.4.7) shipped UC3 classifier on email **body** only. Invoice-PDF and
contract-DOCX attachments with thin bodies misclassify. Sprint O teaches the
classifier to see inside attachments via `AttachmentProcessor` (Sprint K
infrastructure) + derived `AttachmentFeatures`.

**S126 scope is DISCOVERY:** prove the problem exists, quantify it, and land
the plan docs. No classifier change this session.

---

## 2. KONTEXTUS

### Honnan jottunk (S125)
Lane A: Sprint M PR #17 squash-merged → `94750d9`. Sprint N PR #18 rebased
onto fresh main (Sprint M's 11 commits auto-dropped as already-upstream post
squash), squash-merged → `13a2f08`. Tags `v1.4.9` + `v1.4.10` pushed. Lane B
kickoff: sprint K verified as already-DONE (tag `v1.4.7`, PR #15 merged), UC3
theme re-confirmed with user as **attachment-aware intent signals**.

### Jelenlegi allapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2196 unit PASS / 1 skip / 1 xpass (resilience quarantine) — S125 +83 tools tests
~96 integration | 424 E2E collected | 8 skill | 24 UI page
Branch: feature/v1.4.11-uc3-attachment-intent (fresh, off `main` @ 13a2f08)
Feature flag (S128+): AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false (default)
```

### Hova tartunk
S130 end-of-sprint state:
- Classifier reads attachments when flag ON.
- Fixture misclass rate drops ≥ 50% vs S126 baseline.
- Sprint K UC3 golden-path E2E green (regression gate).
- Admin UI "Attachment signals" card on EmailDetail.tsx.
- PR opened against `main`, tag `v1.4.11` queued post-merge.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                      # feature/v1.4.11-uc3-attachment-intent
git log --oneline -3                           # S126 kickoff commit on top of 13a2f08
ls docs/sprint_o_plan.md 01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1  # 2196 passed
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
alembic current                                # head 045
docker compose ps                              # postgres + redis up
```

---

## 4. FELADATOK

### LEPES 1 — Fixture fölkutatás + válogatás
- Gyűjts ~30 jelölt email-fixturet (szintetikus + anonimizált valós minták). Forrás:
  - `data/samples/emails/` (ha létezik) + `tests/e2e/fixtures/emails/`.
  - Ha nincs elég invoice-PDF-csatolt minta, szintetizálj Docling-barát egyszerű PDF-eket inline (reportlab vagy egy `make_fixture_pdf.py` helper + 5 mintatartalom).
- Válogass 25-öt: 6 invoice-attachment, 6 contract-DOCX-attachment, 6 body-only, 7 mixed/ambiguous. Mindegyik 4 intent kategória (EXTRACT / INFORMATION_REQUEST / SUPPORT / SPAM) lefedve.
- Fixture hely: `data/fixtures/emails_sprint_o/`. Minden email: 1 .eml + attached binaries.
- Írj `tests/fixtures/emails_sprint_o/README.md`-t: mi mi, milyen várt intent, miért.

### LEPES 2 — Baseline mérőszkript
- `scripts/measure_uc3_baseline.py` — argumentum nélkül fut, beolvassa a fixture könyvtárat, lefuttatja a jelenlegi `scan_and_classify` végigvitt pipeline-t minden emailen, és kiír egy `docs/uc3_attachment_baseline.md` riportot:
  - per-email: várt intent, kapott intent, helyes/helytelen, szkenn latency.
  - összesen: misclass rate %, p50/p95 latency, mime-type eloszlás, `MANUAL_REVIEW` ráta.
- A szkript valós Docker Postgres ellen fut (`AIFLOW_DATABASE_URL` ENV-ből). NE MOCK.

### LEPES 3 — Baseline riport
- Futtasd `scripts/measure_uc3_baseline.py`-t.
- Ellenőrizd: misclass rate ≥ 15% (STOP küszöb a tervben). Ha alatta, HALT + user visszaigazolás.
- Commit-old a riportot + a szkriptet.

### LEPES 4 — Plan-validator check
- Futtasd a `plan-validator` agentet a `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` + `docs/sprint_o_plan.md` + `CLAUDE.md` konzisztenciájára. Javíts ha talál drift-et.

### LEPES 5 — NEXT.md + kickoff commit
- Írd át `session_prompts/NEXT.md`-t S127-re (AttachmentFeatureExtractor fejlesztés).
- Commit-old minden S126 eredményt: `chore(sprint-o): S126 kickoff — UC3 attachment-aware intent plan + baseline (misclass X%) + S127 NEXT.md`.
- Push.

---

## 5. STOP FELTETELEK

**HARD (hand back to user):**
1. Fixture misclass rate < 15% → sprint value unproven, halt + rescope.
2. Fixture építés > 90 perc → jelezd és vagy szintetikus PDF-et hagyj el (beérve szöveges .eml-vel) vagy hand back.
3. `scripts/measure_uc3_baseline.py` a valós docker PG ellen > 3 percig fut a 25 emailre → baseline nem használható (latency-gyanús); halt.
4. Sprint M / Sprint N tag revert/rollback — bármi ilyen esetén halt (integritás).

**SOFT (proceed with note):**
- Ha `ClassifierInput.context` kiegészítés nem backward-compat nélkül adható, írd a retro-ba és vizsgáld meg S128-ban.
- Ha a fixture mérete > 100 MB, gitignore-olj és egy `docs/fixture_seed.md`-ben írd le a seed generálás menetét.

---

## 6. NYITOTT (carried)

Lásd `docs/sprint_n_retro.md` §"Follow-up issues" és a Sprint M + J carry listákat. Sprint O NEM veszi át őket hacsak STOP feltétel nem indokolja.

**Határidős:** Resilience `Clock` seam — 2026-04-30 (mai session!) — ha időben belefér, tedd be Lane C módon piggyback-commit-ként. Ha nem, dokumentáld a döntést Sprint O retro-ban.

---

## 7. SESSION VEGEN

```
/session-close S126
```

Utana: `/clear` -> `/next` -> S127 (AttachmentFeatureExtractor).
