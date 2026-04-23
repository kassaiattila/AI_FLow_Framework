# AIFlow v1.4.9 Sprint M — Session 119 Prompt (Sprint close: PR + tag + retro + rotation runbook)

> **Datum:** 2026-04-25
> **Branch:** `feature/v1.4.9-vault-langfuse`
> **HEAD:** `1f02d00` (feat(observability): S118 — self-hosted Langfuse compose overlay + air-gap E2E harness)
> **Port:** API 8102 | UI 5173 | Vault dev 8210 | Langfuse dev 3000 | Langfuse Postgres 5434
> **Elozo session:** S118 — `docker-compose.langfuse.yml` + Postgres 16 overlay, `scripts/bootstrap_langfuse.py`, `.env.langfuse.example`, `scripts/seed_vault_dev.py` elsobbseget ad a `LANGFUSE_BOOTSTRAP_*` env valtozoknak, `tests/e2e/test_airgapped_profile_a.py` (2 teszt, skip-by-default), `docs/airgapped_deployment.md` operator runbook. 2073 unit + 4 resolver-live green; e2e collection 420 -> 422.
> **Terv:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 + `docs/sprint_m_plan.md` (S119 sprint-close row)
> **Session tipus:** SPRINT CLOSE — PR cut + retro + rotation runbook + CLAUDE.md + lockfile

---

## KONTEXTUS

### Honnan jottunk (S115 -> S118 osszesen)
- **S115** (`ab63c93`-rol): Vault dev container (`docker-compose.vault.yml`), `SecretManager` ABC, 12 secret inventory.
- **S116**: hvac-backed `VaultSecretProvider`, TTL + token rotation, resolver chain (Vault -> env -> default).
- **S117**: `VaultSettings` on `AIFlowSettings`, `aiflow.security.resolver.get_secret_manager()` singleton, 7 consumer migrations (OpenAI / AzureOpenAI / AzureDI + docling 3-alias / Langfuse / webhook HMAC / JWT PEMs / DB DSN). +13 unit + 4 resolver-live tests.
- **S118**: self-hosted Langfuse v3 stack, bootstrap script, air-gap E2E harness (skip-by-default), operator runbook.

### Hova tartunk (S119 — Sprint M close)
Zard le a v1.4.9 Sprint M sprintet: PR main ellen + `v1.4.9` tag + retro + rotation runbook + CLAUDE.md szamfrissites + pyproject lockfile audit. Semmi production kod valtozas — csak osszegzes, docs, release gombokat nyomjuk.

### Jelenlegi allapot
```
27 service | 189 endpoint | 50 DB tabla | 44 Alembic migration (head: 044)
2073 unit | 422 E2E (S118: +2 airgap, skip-by-default) | 13 vault-related integration
8 skill | 23 UI oldal | hvac 2.4.0 | langfuse 4.3.1 (v4 API)
Vault dev: aiflow-vault-dev@:8210 (unsealed, root aiflow-dev-root)
Langfuse dev: docker-compose.langfuse.yml (3000) + langfuse-postgres (5434)
```

---

## ELOFELTELEK

```bash
git branch --show-current                         # feature/v1.4.9-vault-langfuse
git log --oneline -6                              # HEAD 1f02d00 (S118)
git status --short                                # clean
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2073 pass
gh auth status                                    # gh kliens logged in
gh pr list --base main --head feature/v1.4.9-vault-langfuse --json number,title 2>&1 | head -20
```

---

## FELADATOK

### LEPES 1 — Sprint retro (`docs/sprint_m_retro.md`, ~30 min)

Forma a Sprint J retro mintajara (`docs/sprint_j_retro.md`). Szekciok:

1. **Scope delivered** — S115 .. S118 per-session egy-egy bekezdes, a valodi kimenet (fajlok, teszt delta).
2. **What worked** — resolver chain design letisztult, Vault dev in-memory backend + idempotens seed script gyors volt, Langfuse self-host image-ek docker save/load-dal atruhazhatoak.
3. **What surprised us** — langfuse 4.3.1 SDK eloszor ment volna v3 koze, de a tracer mar v4 API-t hasznal, tehat nem kellett pin. `.env.*` minta miatt `.env.langfuse.example` whitelistet kellett kernunk.
4. **Open follow-ups** — pyproject.toml lockfile refresh, vault AppRole prod profile, Playwright `--network=none` varians, BGE-M3 weight cache CI artifact, Azure OpenAI Profile B live (credits pending), resilience `Clock` seam (quarantine deadline 2026-04-30).
5. **Metrics** — +14 Python file, +1400 LOC, +13 unit test, +4 integration test, +2 airgap e2e test, 0 Alembic migration.

### LEPES 2 — Rotation runbook (`docs/runbooks/vault_rotation.md`, ~40 min)

Operator runbook a Vault secret rotation-rol. Tagolas:

1. **Rotation classes** — token rotacio (AppRole) vs. secret rotation (LLM API key / DB DSN / Langfuse keypair / JWT keypair).
2. **Dev procedure** — `scripts/seed_vault_dev.py` ujrafuttatas, tokent uj env valtozokkal.
3. **Prod procedure** — AppRole role_id / secret_id swap, 3-step blue/green pattern (ujat ir -> consumer restart -> regit torol), TTL watch.
4. **LLM key rotation** — Azure/OpenAI dashboard muvelet, Vault rewrite, consumer restart, smoke query.
5. **Langfuse keypair** — S118 bootstrap script + `.env.langfuse` `LANGFUSE_INIT_PROJECT_*_KEY` pin, resolver cache invalidate (`SecretManager.clear()`).
6. **Emergency revoke** — token compromise playbook: `vault token revoke`, consumer alert, re-bootstrap, audit log export.
7. **Observability** — mely Langfuse trace nev / log event erinti a rotation-t, milyen metric watch kell (`resolver.vault.miss`, `resolver.vault.auth_failed`).

### LEPES 3 — Lockfile + pyproject audit (~20 min)

```bash
.venv/Scripts/python.exe -c "import hvac, langfuse, requests; print(hvac.__version__, langfuse.__version__, requests.__version__)"
grep -E '^hvac|^langfuse|^requests' pyproject.toml
uv lock --check
```

- Ha `uv lock --check` diff-et jelez -> `uv lock` + commit. `requests` legyen a test-extras-ban ha nem volt.
- Ha langfuse v4 API tovabbra is stabil, **ne pin**-eld `<3.2`-re (ellentmondana a kodnak). Kommenteld a sprint retro-ban.
- Ha hvac verzio novekmeny kell a prod AppRole meg jobb supporthoz, jegyezd fel a retro open follow-upjai koze.

### LEPES 4 — CLAUDE.md szamfrissites (~15 min)

A "Key Numbers" sorban:
- Unit: `2073 unit tests` -> `2073 unit tests (Sprint M S117: +13 Vault/resolver)`.
- E2E: `420 E2E tests (... + 3 Sprint L S111 Monitoring)` -> `422 E2E tests (... + 2 Sprint M S118 air-gap, skip-by-default)`.
- Migrations: maradt 44 (head 044).
- Skill block var valtozatlan.

Current plan szekcio elejen hozz letre egy **Sprint M — DONE 2026-04-25** bekezdest a Sprint J mintajara: roviden listazd S115/S116/S117/S118 kimenetet, nyitott follow-upokat, tag `v1.4.9` (queued), PR `main` ellen.

Ha `Overview` sor `v1.4.9 Sprint M — Vault hvac + self-hosted Langfuse` mar ott van, frissitsd DONE-ra a datumot es a HEAD-et.

### LEPES 5 — PR description + cut (~30 min)

`docs/sprint_m_pr_description.md` (Sprint J mintara):
- Summary (mit hoz ez a PR)
- Scope delivered S115..S118
- Teszt summary
- Breaking changes (nincsenek — additive resolver + opcionalis Langfuse host flip)
- Deployment notes (`.env.langfuse` generalas, `scripts/seed_vault_dev.py` ujrafuttatas, resolver aktivalas)
- Follow-ups

```bash
gh pr create --base main --head feature/v1.4.9-vault-langfuse \
  --title "Sprint M (v1.4.9): Vault hvac + self-hosted Langfuse + air-gap Profile A" \
  --body-file docs/sprint_m_pr_description.md
```

Ne mergeld. Cimkezz `sprint-close` + `security` + `observability`.

### LEPES 6 — Tag (queued, merge utan a tag)

NE futtasd most — a tag csak a squash-merge utan mehet. Dokumentald a PR description alajan:

```
Post-merge:
  git fetch origin && git checkout main && git pull
  git tag v1.4.9 -a -m "Sprint M: Vault hvac + self-hosted Langfuse + air-gap Profile A"
  git push origin v1.4.9
```

### LEPES 7 — Validacio + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ scripts/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/ scripts/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
gh pr view --json number,state,mergeable 2>&1 | tail -5
/session-close S119
```

---

## STOP FELTETELEK

**HARD (hand back to user):**
1. `gh pr create` 4xx — branch protection vagy permission; kerd a user authorizaciojat.
2. `uv lock --check` dep conflictot jelez langfuse v4 es egy downstream csomag kozott — kerd meg, melyik verziot pineljuk.
3. CLAUDE.md merge conflict — valaki mas modositotta kozben; human review szukseges.

**SOFT (proceed with note):**
1. GitHub Actions CI nem fut a branch-en (ha a repo nem allit be CI-t) — jegyezd fel a retroba, ne blokkolj.
2. `v1.4.9` tag kesobb mehet (merge utan). Ne taggelj moment, csak a runbookban dokumentald.

---

## NYITOTT (Sprint M utan)

- **Sprint N kickoff**: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §6 — LLM cost guardrail + per-tenant budget rollout (tervezett `v1.4.10`).
- **BGE-M3 weight CI artifact** — akkor piros zaszlo ha a S103 TODO-ben mar rogzitve lett.
- **Playwright `--network=none`** — a `/live-test` variansa air-gap E2E-re; post-Sprint M.

---

## SESSION VEGEN

```
/session-close S119
```

Utana: `/clear` -> uj sprint (`Sprint N` kickoff) prompt kerese a plan §6 alapjan.
