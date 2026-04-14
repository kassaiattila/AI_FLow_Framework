---
name: review
description: Kod review — correctness, security, i18n, DB, performance, testing
allowed-tools: Read, Grep, Glob, Bash
---

# Code Review

## Argumentum
$ARGUMENTS — Branch, fajl, vagy feature leirasa (pl. "intake_normalize service", "last 3 commits")

## Review Szempontok

### 1. Correctness
- Logikai hibak, edge case-ek
- Tipusok helyessege (Pydantic modellek, return type)
- Async/await konzisztencia (minden I/O async?)
- Error handling (AIFlowError with is_transient?)

### 2. Security (→ security-reviewer agent ha melyseg kell)
- SQL injection (raw query, parameter binding)
- XSS (React dangerouslySetInnerHTML)
- Hardcoded credentials
- PII a logokban
- JWT RS256 (nem HS256)
- API key prefix `aiflow_sk_`

### 3. i18n
- `useTranslate()` minden lathato szovegre
- Uj kulcsok `en.json` + `hu.json`-ban is
- Nincs hardcoded string a UI-ban

### 4. Database
- Schema valtozas → Alembic migration van?
- Uj oszlopok `nullable=True` vagy `server_default`?
- Query performance (N+1, missing index)

### 5. Performance
- Felesleges DB query (N+1 problema)
- Nagy payload (pagination?)
- Blokkolo I/O asyncio-ban (→ to_thread)

### 6. Testing
- Uj kod → van uj teszt?
- Edge case-ek lefedve?
- Mock hasznalat → TILTOTT (valos DB/Redis/LLM)

### 7. v2 Architecture Fit
- Domain contract illesztes (100_b)
- State machine konzisztencia (100_c)
- Multi-tenant isolation betartas
- Provider abstraction kovetett

## Output

```
## Code Review: $ARGUMENTS

### Summary
[1-2 mondat]

### Findings
| # | Severity | File:Line | Finding | Recommendation |
|---|----------|-----------|---------|----------------|

### Verdict: APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
```
