# AIFlow v1.4.9 Sprint M — Session 114 Prompt (Sprint M kickoff — Vault hvac + self-hosted Langfuse)

> **Datum:** 2026-04-24 (folytatas Sprint L merge utan)
> **Branch:** `feature/v1.4.9-vault-langfuse` — CUT from `main` after v1.4.8 merge.
> **HEAD prereq:** `main` @ tag `v1.4.8` (Sprint L merged via PR #16).
> **Port:** API 8102 | Frontend Vite 5173 | Vault 8200 | Langfuse 3000
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 — v1.4.9 reshuffled scope (Vault + self-hosted Langfuse pulled from v1.4.5 S94/S95).
> **Session tipus:** KICKOFF + DISCOVERY. Code risk: MEDIUM (secrets surface). Process risk: LOW (branch is fresh).

---

## KONTEXTUS

### Honnan jottunk (Sprint L DONE)
- S111 `0351e6f` — Langfuse drill-down (trace + span-metrics) + TraceTree UI.
- S112 `58251de` — PolicyEngine.cost_cap enforcement + Costs cap banner + Alembic 043.
- S113 `3b86363` — ci-cross-uc profile (42 tests / 19s wall-clock) + regression matrix + PR #16 + tag `v1.4.8`.
- Sprint L exit gate: **PASS** — 3 UCs working + monitored + cost-capped.

### Hova tartunk — Sprint M scope (v1.4.9)
Cel: **Secrets + Observability hardening** — no plaintext secrets, air-gapped Langfuse option.

Per replan §5 "What gets pushed back":
| Item | Was | Now target |
|---|---|---|
| Vault hvac prod impl + token rotation | v1.4.5 S94 | **v1.4.9** (full sprint standalone) |
| Self-hosted Langfuse + Profile A air-gapped E2E | v1.4.5 S95 | **v1.4.9** (with Vault) |

### Proposed session queue (5 sessions, revisit in S114)
| Session | Scope | Acceptance |
|---|---|---|
| **S114 (this)** | Kickoff: branch cut, discovery of existing secrets surface (env vars, `config.py`, `security/secrets`), Vault dev container up, inventory doc `docs/secrets_inventory.md` | Branch live; inventory doc merged; vault dev container reachable on :8200 |
| S115 | `hvac` client wrapper + token rotation scheduler + secrets resolver (env -> Vault fallback) | Unit tests for resolver precedence; integration test against vault dev |
| S116 | Migrate `AIFlowSettings` + `LLM_API_KEY` + DB creds to Vault-backed resolver (Alembic N/A — config-only) | Existing 1995 unit + cost_cap_enforcement GREEN with Vault-backed creds |
| S117 | Self-hosted Langfuse docker-compose + `LANGFUSE_BASE_URL` env switch + Profile A (BGE-M3 local) air-gapped E2E | Air-gapped E2E: no outbound HTTP to cloud except Langfuse local + Vault local |
| S118 | Sprint M close: PR cut + tag `v1.4.9` + secrets rotation runbook in `docs/runbooks/vault_rotation.md` | PR opened; tag queued; runbook merged |

---

## ELOFELTELEK

```bash
# 1. Sprint L merge verification
git fetch origin
git log origin/main --oneline -5                      # expect: v1.4.8 merge commit visible
git tag -l v1.4.8                                     # expect: v1.4.8
gh pr view 16 --json state,mergedAt                   # expect: state=MERGED

# 2. Cut new branch from main
git checkout main
git pull origin main
git checkout -b feature/v1.4.9-vault-langfuse

# 3. Baseline validation on fresh branch
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current                     # expect: 043 (head)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov      # expect: 1995 pass
```

**Ha a PR #16 meg nincs mergelve:** STOP — ez a session csak akkor indul, amikor Sprint L landolt a `main`-en. Jelezd a usernek es varj.

---

## FELADATOK

### LEPES 1 — Sprint L merge verify + branch cut (~5 min)
```bash
gh pr view 16 --json state,mergedAt
# Ha MERGED: folytatas. Ha OPEN: STOP es varj.

git checkout main && git pull origin main
git checkout -b feature/v1.4.9-vault-langfuse
```

### LEPES 2 — Secrets surface discovery (readonly ~15 min)

Sorold fel az osszes helyet ahol titkok vannak ma:
```bash
grep -rn "os.environ\|getenv\|env_var\|AIFLOW_.*_KEY\|API_KEY\|SECRET\|PASSWORD\|TOKEN" \
  src/aiflow/core/config.py \
  src/aiflow/security/secrets/ \
  src/aiflow/ \
  2>&1 | head -60

ls src/aiflow/security/secrets/ 2>&1
cat .env.example 2>&1 | head -30
```

Kerdesek:
- Van-e mar `hvac` dependency a `pyproject.toml`-ban?
- A `security/secrets/` modul milyen backend-eket tamogat most (env / file / vault stub)?
- Van-e `Settings.vault_*` mezo a `AIFlowSettings`-ben?
- Melyik 10-15 kulcsot kell a legelsokent Vault-ositani?

### LEPES 3 — `docs/secrets_inventory.md` megirasa (~20 min)

Tablazatos inventory:
| Secret name | Current source | Consumer | Criticality | Vault path target |
|---|---|---|---|---|
| LLM_API_KEY | env | models.client, services.rag_engine, ... | HIGH | kv/aiflow/llm |
| POSTGRES_PASSWORD | env / docker-compose | state.repository | HIGH | kv/aiflow/db |
| LANGFUSE_SECRET_KEY | env | observability.tracing | MEDIUM | kv/aiflow/langfuse |
| ... | ... | ... | ... | ... |

### LEPES 4 — Vault dev container up

```bash
# docker-compose.vault.yml (uj fajl, dev-only)
# image: hashicorp/vault:1.15
# VAULT_DEV_ROOT_TOKEN_ID=aiflow-dev-root
# port 8200:8200
docker compose -f docker-compose.yml -f docker-compose.vault.yml up -d vault
curl -s http://localhost:8200/v1/sys/health | jq .
```

Acceptance: `sealed=false`, `standby=false`.

### LEPES 5 — Next session queue decision

Miutan kezeben van az inventory + vault dev up:
- Mar most tudod-e fixalni a session queue-t (S115-S118), vagy inkabb adaptive?
- Van-e blokkolo (pl. vault prod infra nem elerheto dev-hez)?

Ezt `docs/sprint_m_plan.md`-be ird le (min. 1 oldal), commitold a branch-re.

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
# CLAUDE.md: bump current branch + sprint M kickoff ref.
/session-close S114
```

---

## STOP FELTETELEK

**HARD:**
1. PR #16 meg nincs mergelve → varj user akciora, ne cuts a branch-et korabban.
2. `docker compose up vault` FAIL → docker-desktop restart, ha az sem segit → user akcio.
3. Discovery alatt talalunk **hardcoded production secret**-et a kodbazisban → azonnali security-reviewer agent, kulon hotfix PR.

**SOFT:**
1. `hvac` nincs a pyproject-ban → adjuk hozza `uv add hvac==2.x`-szel (S115-ben ha most nem).
2. Self-hosted Langfuse kep nincs a registry-ben → halasztjuk S117-re.

---

## SESSION VEGEN

```
/session-close S114
```

Utana S115 inditas Vault wrapper + token rotation fokusszal.
