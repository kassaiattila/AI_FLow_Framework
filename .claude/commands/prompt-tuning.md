Run the 6-step Prompt Lifecycle cycle for an AIFlow skill prompt.

Arguments: $ARGUMENTS
(Required: skill name, e.g. "aszf_rag_chat", "email_intent", "invoice_processor")

## 6-Step Prompt Lifecycle

### STEP 1: DIAGNOZIS
- Olvasd el a skill aktualis prompt YAML-jait: `skills/{name}/prompts/*.yaml`
- Ha Langfuse elerheto: exportald a gyenge trace-eket
- Azonositsd: melyik prompt, melyik input tipusnal romlik?
- Root cause: szoveg? modell? temperature? context hossz?
- **OUTPUT:** diagnozis riport (mit kell javitani, miert)

### STEP 2: FEJLESZTES
- Ird at/finomitsd a prompt YAML-t
- Uj verzio: valtozatlan fajlnev, de YAML-ban version mezo novelese
- Langfuse-ba feltoltes "dev" label-lel (ha elerheto)
- Git: a prompt YAML valtozas kulon commitolhato
- **OUTPUT:** uj prompt YAML + Langfuse "dev" label

### STEP 3: TESZTELES (Promptfoo — VALOS LLM!)
- Futtasd: `npx promptfoo eval -c skills/{name}/tests/promptfooconfig.yaml`
- Regi vs uj osszehasonlitas (A/B ha lehetseges)
- Golden dataset: known-good + known-bad + edge case
- **GATE: >= 95% pass rate ES nem rosszabb a reginél**
- Ha < 95% → vissza STEP 2 (max 3 iteracio)
- **OUTPUT:** eval riport (pass rate, diff, regresszio)

### STEP 4: VALIDACIO
- General osszehasonlito riportot (regi vs uj)
- Edge case-ek kezi atnezes
- Dontes: APPROVE / REJECT / ITERATE
- **OUTPUT:** jovahagyott prompt verzio

### STEP 5: ELESITES (Langfuse label swap — NEM kell deploy!)
- Ha Langfuse elerheto:
  - Uj verzio: label "dev" → "prod"
  - Regi verzio: label "prod" → "previous" (rollback!)
  - PromptManager cache invalidacio: `POST /api/v1/prompts/{name}/invalidate`
- Ha Langfuse NEM elerheto:
  - Git commit a prompt YAML valtozassal
  - Manualis service ujrainditas a cache frissiteshez
- **OUTPUT:** production prompt frissitve

### STEP 6: MONITORING
- Ha Langfuse elerheto: uj trace-ek az uj prompt verzioval
- Elotte vs utana metrikak osszehasonlitasa
- Ha romlott → rollback: "previous" → "prod"
- **OUTPUT:** before/after metrika riport

## Meglevo Infrastruktura (NEM kell epiteni!)

- **PromptManager** (`src/aiflow/prompts/manager.py`):
  Resolution: cache → Langfuse (v4 SDK) → YAML fallback
  Cache TTL: 300s (konfiguralhato), invalidate() metodus
- **Langfuse:** AIFLOW_LANGFUSE__ENABLED=true (.env)
- **Promptfoo:** 54 test case 6 skill-re (mar konfiguralt)

## Output Formatum

```
=== PROMPT TUNING: {skill_name} ===

Step 1 — Diagnozis:
  Prompt: {prompt_name}
  Problema: {leiras}

Step 2 — Fejlesztes:
  Valtozas: {mit valtoztattunk}
  Fajl: skills/{name}/prompts/{prompt}.yaml

Step 3 — Teszteles:
  Pass rate: XX% (regi: YY%)
  Regresszio: NINCS / {reszletek}
  GATE: PASS / FAIL

Step 4 — Validacio:
  Dontes: APPROVE / REJECT / ITERATE

Step 5 — Elesites:
  Langfuse: label swap KESZ / N/A
  Cache: invalidalva / N/A

VERDICT: IMPROVED (XX% → YY%) / NO CHANGE / REGRESSED
```
