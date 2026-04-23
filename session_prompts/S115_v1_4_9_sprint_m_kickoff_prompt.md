# AIFlow v1.4.9 Sprint M — Session 115 Prompt (Sprint M kickoff — Vault hvac + self-hosted Langfuse)

> **Datum:** 2026-04-24 (folytatas Sprint L merge + hotfix utan)
> **Branch:** `feature/v1.4.9-vault-langfuse` — CUT from `main` (v1.4.8 MERGED @ `ab63c93`).
> **HEAD prereq:** `main` @ tag `v1.4.8` pushed, squash merge commit `ab63c93`.
> **Port:** API 8102 | Frontend Vite 5173 | Vault 8200 | Langfuse 3000
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 — v1.4.9 reshuffled scope (Vault + self-hosted Langfuse pulled from v1.4.5 S94/S95).
> **Session tipus:** KICKOFF + DISCOVERY. Code risk: MEDIUM (secrets surface). Process risk: LOW (branch is fresh).

---

## KONTEXTUS

### Honnan jottunk
- S113 `3b86363` — ci-cross-uc regression pack (42 tests / 19s wall-clock), PR #16 + tag `v1.4.8`.
- S114 `0d0f7ce` + `7929d81` (Sprint L hotfix merged via squash): S112 `cost_records.workflow_run_id` NOT NULL bug fix via Alembic 044 (now nullable), coverage gate recovery 64.9% → 65.22% via 25 new unit tests for `cost_repository` + `policy.engine.enforce_cost_cap` + `api.v1.costs.cost_cap_status`.
- PR #16 **MERGED** 2026-04-23 as squash `ab63c93`; `v1.4.8` tag relocated to merge commit on origin.
- Sprint L exit gate: **PASS** — 3 UCs working + monitored + cost-capped + all CI green.

### Hova tartunk — Sprint M scope (v1.4.9)
Cel: **Secrets + Observability hardening** — no plaintext secrets, air-gapped Langfuse option.

Per replan §5 "What gets pushed back":
| Item | Was | Now target |
|---|---|---|
| Vault hvac prod impl + token rotation | v1.4.5 S94 | **v1.4.9** (full sprint standalone) |
| Self-hosted Langfuse + Profile A air-gapped E2E | v1.4.5 S95 | **v1.4.9** (with Vault) |

### Jelenlegi allapot
```
27 service | 189 endpoint | 50 DB tabla | 44 Alembic migration (head: 044)
2020 unit tesztek | 420 E2E | 8 skill | 23 UI oldal
```

### Proposed session queue (5 sessions, revisit in S115)
| Session | Scope | Acceptance |
|---|---|---|
| **S115 (this)** | Kickoff: branch cut, discovery of existing secrets surface (env vars, `config.py`, `security/secrets`), Vault dev container up, inventory doc `docs/secrets_inventory.md` | Branch live; inventory doc merged; vault dev container reachable on :8200 |
| S116 | `hvac` client wrapper + token rotation scheduler + secrets resolver (env -> Vault fallback) | Unit tests for resolver precedence; integration test against vault dev |
| S117 | Migrate `AIFlowSettings` + `LLM_API_KEY` + DB creds to Vault-backed resolver (Alembic N/A — config-only) | Existing 2020 unit + cost_cap_enforcement GREEN with Vault-backed creds |
| S118 | Self-hosted Langfuse docker-compose + `LANGFUSE_BASE_URL` env switch + Profile A (BGE-M3 local) air-gapped E2E | Air-gapped E2E: no outbound HTTP to cloud except Langfuse local + Vault local |
| S119 | Sprint M close: PR cut + tag `v1.4.9` + secrets rotation runbook in `docs/runbooks/vault_rotation.md` | PR opened; tag queued; runbook merged |

---

## ELOFELTELEK

```bash
# 1. Sprint L merge verification (should ALL pass — Sprint L is already shipped)
git fetch origin
git log origin/main --oneline -3                      # expect: ab63c93 visible as HEAD
gh pr view 16 --json state,mergedAt                   # expect: state=MERGED
git ls-remote origin refs/tags/v1.4.8                 # expect: tag present

# 2. Cut new branch from main
git checkout main
git pull origin main
git checkout -b feature/v1.4.9-vault-langfuse

# 3. Baseline validation on fresh branch
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current                     # expect: 044 (head)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov      # expect: 2020 pass
```

---

## FELADATOK

### LEPES 1 — Branch cut (~2 min)
```bash
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
- Mar most tudod-e fixalni a session queue-t (S116-S119), vagy inkabb adaptive?
- Van-e blokkolo (pl. vault prod infra nem elerheto dev-hez)?

Ezt `docs/sprint_m_plan.md`-be ird le (min. 1 oldal), commitold a branch-re.

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
# CLAUDE.md: bump current branch + sprint M kickoff ref.
/session-close S115
```

---

## STOP FELTETELEK

**HARD:**
1. `main` nem tartalmazza az `ab63c93` commitot → `git fetch` es `git pull origin main` elotti allapot; ne cuts a branch-et.
2. `docker compose up vault` FAIL → docker-desktop restart, ha az sem segit → user akcio.
3. Discovery alatt talalunk **hardcoded production secret**-et a kodbazisban → azonnali security-reviewer agent, kulon hotfix PR.

**SOFT:**
1. `hvac` nincs a pyproject-ban → adjuk hozza `uv add hvac==2.x`-szel (S116-ban ha most nem).
2. Self-hosted Langfuse kep nincs a registry-ben → halasztjuk S118-ra.

---

## NYITOTT (Sprint L ora maradt)
- `config/policies/intent_routing/acme.yaml` untracked — runtime-generated tenant config, `.gitignore` rule kellene (Sprint M housekeeping, kis scope).

---

## SESSION VEGEN

```
/session-close S115
```

Utana S116 inditas Vault wrapper + token rotation fokusszal.
