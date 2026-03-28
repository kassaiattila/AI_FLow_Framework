# AIFlow - Security Hardening Plan

**Cel:** Atfogo biztonsagi keretrendszer az AIFlow enterprise AI automation platformhoz.
**Tech stack:** Python 3.12+, FastAPI, PostgreSQL, Redis, LiteLLM, Langfuse
**Referencia:** OWASP Top 10 for LLM Applications (2025), NIST AI RMF, CIS Benchmarks

---

## 1. OWASP Top 10 for LLM Applications - AIFlow Mapping

Az OWASP LLM Top 10 minden kockazatara specifikus AIFlow mitigation strategia:

| # | OWASP LLM Risk | AIFlow Mitigation |
|---|----------------|-------------------|
| LLM01 | **Prompt Injection** | Input sanitization layer + canary token detection (ld. Section 2) |
| LLM02 | **Insecure Output Handling** | Output guardrails + schema validation minden LLM response-ra |
| LLM03 | **Training Data Poisoning** | Nem releváns (nem trainelunk modelt), de RAG source validation |
| LLM04 | **Model Denial of Service** | Per-user/per-team rate limiting + max token cap (ld. Section 6) |
| LLM05 | **Supply Chain Vulnerabilities** | Dependabot + pip-audit + container scanning (ld. Section 9) |
| LLM06 | **Sensitive Information Disclosure** | PII detection + output filtering + audit log (ld. Section 7) |
| LLM07 | **Insecure Plugin Design** | Skill/plugin sandboxing + permission model + input validation |
| LLM08 | **Excessive Agency** | Human-in-the-loop approval flow + action allowlists |
| LLM09 | **Overreliance** | Confidence scoring + mandatory human review high-risk taszkoknal |
| LLM10 | **Model Theft** | API key encryption + network isolation + access logging |

### Implementacios prioritas

```
Phase 1-2: LLM01, LLM04, LLM06, LLM10 (alapveto vedelem)
Phase 3-4: LLM02, LLM07, LLM08 (plugin/output security)
Phase 5-7: LLM05, LLM09 (supply chain, overreliance monitoring)
```

---

## 2. Prompt Injection Protection

### 2.1 Input Sanitization Layer

Minden user input at kell menjen a sanitization pipeline-on mielott LLM-hez kerul:

```python
# aiflow/security/prompt_guard.py
import re
from typing import Optional
from pydantic import BaseModel

class PromptGuardResult(BaseModel):
    is_safe: bool
    risk_score: float  # 0.0 - 1.0
    detected_patterns: list[str]
    sanitized_input: str

class PromptGuard:
    """Prompt injection detection es sanitization."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?(your\s+)?instructions",
        r"you\s+are\s+now\s+(?:a|an)\s+",
        r"system\s*:\s*",
        r"<\|im_start\|>",
        r"\[INST\]",
        r"```\s*system",
        r"IMPORTANT:\s*override",
        r"do\s+not\s+follow\s+(the\s+)?previous",
    ]

    CANARY_TOKEN = "AIFLOW_CANARY_{unique_id}"

    def analyze(self, user_input: str) -> PromptGuardResult:
        detected = []
        risk_score = 0.0

        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                detected.append(pattern)
                risk_score = min(risk_score + 0.3, 1.0)

        # Canary token check - ha visszajon az output-ban, injection tortent
        if self.CANARY_TOKEN in user_input:
            detected.append("canary_token_leak")
            risk_score = 1.0

        sanitized = self._sanitize(user_input) if detected else user_input

        return PromptGuardResult(
            is_safe=risk_score < 0.5,
            risk_score=risk_score,
            detected_patterns=detected,
            sanitized_input=sanitized,
        )

    def _sanitize(self, text: str) -> str:
        """Veszelyes pattern-ek eltavolitasa/neutralizalasa."""
        for pattern in self.INJECTION_PATTERNS:
            text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)
        return text
```

### 2.2 Canary Token Rendszer

A canary token-t bele kell injektalni a system prompt-ba. Ha az LLM output-ban megjelenik, prompt injection tortent:

```python
# aiflow/security/canary.py
import uuid
import hashlib

class CanaryTokenManager:
    def generate(self, workflow_run_id: str) -> str:
        """Egyedi canary token generalas workflow run-onkent."""
        raw = f"AIFLOW_CANARY_{workflow_run_id}_{uuid.uuid4().hex[:8]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def inject_into_prompt(self, system_prompt: str, canary: str) -> str:
        """Canary token hozzaadasa a system prompt-hoz (lathatatlanul)."""
        marker = f"\n[Internal tracking: {canary}]\n"
        return system_prompt + marker

    def check_output(self, output: str, canary: str) -> bool:
        """True ha canary leak-et detektal (= injection)."""
        return canary in output
```

### 2.3 SSRF (Server-Side Request Forgery) Vedelem

Webhook URL-ek es kulso integraciok eseten:

```python
import ipaddress

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
]

async def validate_url(url: str) -> bool:
    """Block SSRF by rejecting internal network URLs."""
    hostname = urlparse(url).hostname
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        return not any(ip in net for net in BLOCKED_NETWORKS)
    except (socket.gaierror, ValueError):
        return False
```

### 2.4 Output Guardrails

```python
# HELYES minta: response body olvasasa middleware-ben
async def output_guardrail_middleware(request: Request, call_next):
    response = await call_next(request)
    # Read body without consuming the stream
    body_bytes = b""
    async for chunk in response.body_iterator:
        body_bytes += chunk
    # Check guardrails
    if contains_pii(body_bytes):
        logger.warning("pii_detected_in_output", path=request.url.path)
    # Return new response with the same body
    return Response(
        content=body_bytes,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )
```

---

## 3. Authentication Security

### 3.1 JWT Best Practices

```python
# aiflow/auth/jwt_config.py
from datetime import timedelta

JWT_CONFIG = {
    "algorithm": "RS256",          # RSA asymmetric - NE HS256!
    "access_token_ttl": timedelta(minutes=15),   # Rovid eletciklus
    "refresh_token_ttl": timedelta(days=7),
    "issuer": "aiflow-auth-service",
    "audience": "aiflow-api",
    "require_claims": ["sub", "team_id", "role", "exp", "iat", "jti"],
    "key_rotation_days": 90,       # Kulcs rotacio 90 naponta
}
```

**Kotelezo JWT szabalyok:**
- RS256 (asymmetric) hasznalata, SOHA NE HS256 production-ben
- Access token max 15 perc TTL
- Refresh token max 7 nap, single-use (rotation utan ervenytelen)
- `jti` (JWT ID) claim a replay attack vedelem miatt
- Token blacklist Redis-ben logout/revoke eseten

### 3.2 API Key Lifecycle

```python
# API key generalas es tarolasi flow
class APIKeyManager:
    KEY_PREFIX = "aiflow_"
    KEY_LENGTH = 48  # 384 bit entropy

    async def create_key(self, user_id: str, team_id: str,
                         scopes: list[str], expires_days: int = 365) -> dict:
        raw_key = self.KEY_PREFIX + secrets.token_urlsafe(self.KEY_LENGTH)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        await db.execute("""
            INSERT INTO api_keys (id, user_id, team_id, key_hash,
                                  scopes, expires_at, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW() + $6::interval, NOW())
        """, uuid4(), user_id, team_id, key_hash,
             scopes, f"{expires_days} days")

        return {"key": raw_key, "note": "Csak egyszer jelenik meg!"}

    async def rotate_key(self, old_key_id: str) -> dict:
        """Regi key deaktivalas + uj generalas grace period-dal."""
        await db.execute("""
            UPDATE api_keys SET status = 'rotating',
            grace_period_until = NOW() + INTERVAL '24 hours'
            WHERE id = $1
        """, old_key_id)
        # Uj key generalas ugyanazokkal a scope-okkal
        return await self.create_key(...)
```

### 3.3 Token Rotation Policy

| Token Tipus | TTL | Rotation | Tarolasi hely |
|-------------|-----|----------|---------------|
| Access Token (JWT) | 15 min | Automatic via refresh | Memory only (NE localStorage) |
| Refresh Token | 7 nap | Single-use rotation | HttpOnly Secure cookie |
| API Key | 365 nap | Manual + reminder 30 nappal elotte | Hashed in PostgreSQL |
| Service Token | 24 ora | Automatic via Vault | Vault dynamic secrets |

### 3.4 CSRF Vedelem

Az AIFlow API Bearer token (JWT/API key) alapu - a bongeszok nem kuldik
automatikusan, igy a klasszikus CSRF tamadas nem alkalmazhato.

**Kivetel:** Ha a Reflex UI HttpOnly cookie-t hasznal session-hoz,
CSRF token KOTELEZO minden state-modosito POST/PUT/DELETE kereshez.
Reflex framework beepitett CSRF vedelmet biztosit.

---

## 4. Data Encryption

### 4.1 At-Rest Encryption (PostgreSQL TDE)

```sql
-- PostgreSQL 16+ Transparent Data Encryption setup
-- postgresql.conf konfiguracio:
-- encryption_key_command = 'vault kv get -field=key secret/aiflow/pg-encryption'

-- Sensitive column-level encryption ha TDE nem elerheto:
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- API key hash-eles (egyiranyú)
ALTER TABLE api_keys ADD COLUMN key_hash_v2 BYTEA;

-- PII mezok titkositasa (ketiranyú, szukseges a visszafejtes)
CREATE OR REPLACE FUNCTION encrypt_pii(data TEXT, key TEXT)
RETURNS BYTEA AS $$
    SELECT pgp_sym_encrypt(data, key, 'cipher-algo=aes256');
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION decrypt_pii(data BYTEA, key TEXT)
RETURNS TEXT AS $$
    SELECT pgp_sym_decrypt(data, key);
$$ LANGUAGE sql IMMUTABLE;
```

### 4.2 In-Transit TLS

```yaml
# Minden belso kommunikacio TLS 1.3+
# docker-compose.security.yml
services:
  postgres:
    command: >
      -c ssl=on
      -c ssl_cert_file=/certs/server.crt
      -c ssl_key_file=/certs/server.key
      -c ssl_min_protocol_version=TLSv1.3
      -c ssl_ciphers=TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256

  redis:
    command: >
      redis-server
      --tls-port 6380
      --port 0
      --tls-cert-file /certs/redis.crt
      --tls-key-file /certs/redis.key
      --tls-ca-cert-file /certs/ca.crt
      --tls-protocols "TLSv1.3"
```

### 4.3 Redis Encryption

```python
# aiflow/core/redis_config.py
import redis

def get_secure_redis() -> redis.Redis:
    return redis.Redis(
        host="redis",
        port=6380,
        ssl=True,
        ssl_certfile="/certs/client.crt",
        ssl_keyfile="/certs/client.key",
        ssl_ca_certs="/certs/ca.crt",
        ssl_cert_reqs="required",
        decode_responses=True,
    )
```

### 4.4 Secret Management - Vault Integracio

```python
# aiflow/security/vault_client.py
import hvac

class VaultClient:
    def __init__(self):
        self.client = hvac.Client(
            url=os.getenv("VAULT_ADDR", "https://vault:8200"),
            token=os.getenv("VAULT_TOKEN"),  # Vagy Kubernetes auth
        )

    def get_secret(self, path: str) -> dict:
        """Secret olvasas Vault KV v2-bol."""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response["data"]["data"]

    def get_db_credentials(self) -> dict:
        """Dynamic database credentials (auto-rotate)."""
        response = self.client.secrets.database.generate_credentials(
            name="aiflow-db-role"
        )
        return {
            "username": response["data"]["username"],
            "password": response["data"]["password"],
            "ttl": response["lease_duration"],
        }
```

---

## 5. Network Security

### 5.1 Kubernetes Network Policies

```yaml
# k8s/network-policies/aiflow-api-netpol.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: aiflow-api-policy
  namespace: aiflow
spec:
  podSelector:
    matchLabels:
      app: aiflow-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
        - podSelector:
            matchLabels:
              app: aiflow-worker
      ports:
        - port: 8000
          protocol: TCP
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - port: 5432
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - port: 6380
    # LLM provider API access (kulso)
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - port: 443
          protocol: TCP
```

### 5.2 Pod Security Standards

```yaml
# k8s/pod-security/aiflow-deployment.yaml (reszlet)
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: aiflow-api
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            limits:
              memory: "1Gi"
              cpu: "500m"
            requests:
              memory: "256Mi"
              cpu: "100m"
```

### 5.3 Ingress TLS Konfiguracio

```yaml
# k8s/ingress/aiflow-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aiflow-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/hsts: "true"
    nginx.ingress.kubernetes.io/hsts-max-age: "31536000"
    nginx.ingress.kubernetes.io/hsts-include-subdomains: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - api.aiflow.example.com
      secretName: aiflow-tls-cert
  rules:
    - host: api.aiflow.example.com
      http:
        paths:
          - path: /api/
            pathType: Prefix
            backend:
              service:
                name: aiflow-api
                port:
                  number: 8000
```

### 5.4 Service Mesh (Opcionalis - Istio)

Production kornyezetben Istio service mesh ajanlott az mTLS, traffic management es observability miatt. Implementacio Phase 6-7-ben tervezett, ha a complexity/benefit arany indokolja.

---

## 6. API Rate Limiting

### 6.1 Redis-based Distributed Rate Limiter

```python
# aiflow/security/rate_limiter.py
from datetime import datetime
import redis.asyncio as redis

class DistributedRateLimiter:
    """Sliding window rate limiter Redis-szel."""

    # Konfiguralhato limitek szintenkent
    LIMITS = {
        "per_user":     {"requests": 100,  "window_seconds": 60},
        "per_team":     {"requests": 500,  "window_seconds": 60},
        "per_endpoint": {"requests": 30,   "window_seconds": 60},
        "llm_calls":    {"requests": 20,   "window_seconds": 60},
    }

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self, identifier: str, limit_type: str
    ) -> tuple[bool, dict]:
        config = self.LIMITS[limit_type]
        key = f"ratelimit:{limit_type}:{identifier}"
        now = datetime.utcnow().timestamp()
        window = config["window_seconds"]

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)  # Regi bejegyzesek torlese
        pipe.zadd(key, {str(now): now})               # Uj request hozzaadasa
        pipe.zcard(key)                                # Szamlalo
        pipe.expire(key, window)                       # TTL beallitas
        _, _, count, _ = await pipe.execute()

        allowed = count <= config["requests"]
        return allowed, {
            "limit": config["requests"],
            "remaining": max(0, config["requests"] - count),
            "reset_at": int(now + window),
        }
```

### 6.2 FastAPI Rate Limit Middleware

```python
# aiflow/middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user_id = request.state.user_id  # Auth middleware-bol
        team_id = request.state.team_id
        endpoint = request.url.path

        # Tobbszintu rate limit check
        for limit_type, identifier in [
            ("per_user", user_id),
            ("per_team", team_id),
            ("per_endpoint", f"{user_id}:{endpoint}"),
        ]:
            allowed, info = await limiter.check_rate_limit(identifier, limit_type)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded ({limit_type})",
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_at"]),
                        "Retry-After": str(info["reset_at"] - int(time.time())),
                    },
                )
        return await call_next(request)
```

---

## 7. Input/Output Guardrails

### 7.1 PII Detection

```python
# aiflow/security/pii_detector.py
import re
from enum import Enum

class PIIType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    HUNGARIAN_TAX_ID = "hungarian_tax_id"
    HUNGARIAN_ID_CARD = "hungarian_id_card"

PII_PATTERNS = {
    PIIType.EMAIL: r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    PIIType.PHONE: r"(?:\+36|06)[\s-]?\d{1,2}[\s-]?\d{3}[\s-]?\d{4}",
    PIIType.SSN: r"\b\d{3}-\d{2}-\d{4}\b",
    PIIType.CREDIT_CARD: r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
    PIIType.HUNGARIAN_TAX_ID: r"\b\d{10}\b",
    PIIType.HUNGARIAN_ID_CARD: r"\b\d{6}[A-Z]{2}\b",
}

class PIIDetector:
    def scan(self, text: str) -> list[dict]:
        findings = []
        for pii_type, pattern in PII_PATTERNS.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                findings.append({
                    "type": pii_type,
                    "position": match.span(),
                    "masked": self._mask(match.group()),
                })
        return findings

    def redact(self, text: str) -> str:
        """PII csereje [REDACTED] placeholder-re."""
        for pattern in PII_PATTERNS.values():
            text = re.sub(pattern, "[REDACTED]", text)
        return text

    def _mask(self, value: str) -> str:
        if len(value) <= 4:
            return "****"
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
```

### 7.2 Content Filtering es Token Limitek

```python
# aiflow/security/content_filter.py
from pydantic import BaseModel, field_validator

class LLMRequestGuardrails(BaseModel):
    """Minden LLM request-re vonatkozo guardrails."""
    max_input_tokens: int = 8_000
    max_output_tokens: int = 4_000
    max_total_cost_usd: float = 5.00        # Per-request cost cap
    blocked_topics: list[str] = [
        "generate_malware", "create_exploit", "bypass_security"
    ]
    require_structured_output: bool = True   # JSON schema kenyszerites

    @field_validator("max_input_tokens")
    @classmethod
    def validate_input_tokens(cls, v):
        if v > 32_000:
            raise ValueError("Max input tokens nem lehet tobb mint 32000")
        return v

class ContentFilter:
    async def filter_request(self, prompt: str, config: LLMRequestGuardrails) -> str:
        # Token szam ellenorzes (tiktoken-nel)
        token_count = self._count_tokens(prompt)
        if token_count > config.max_input_tokens:
            raise ValueError(
                f"Input token limit tullepve: {token_count}/{config.max_input_tokens}"
            )
        # Tiltott tema detektalo
        for topic in config.blocked_topics:
            if topic.lower() in prompt.lower():
                raise ValueError(f"Blokkolt tema detektalva: {topic}")
        return prompt
```

### 7.3 Schema Validation az LLM Output-ra

```python
# Structured output kenyszerites Pydantic-kel
from pydantic import BaseModel

class ValidatedLLMResponse(BaseModel):
    """Minden LLM valasz ezen megy keresztul."""
    content: str
    confidence: float  # 0.0-1.0
    sources: list[str] = []
    pii_detected: bool = False
    filtered: bool = False

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence 0-1 kozott kell legyen")
        return v
```

---

## 8. Secret Management

### 8.1 Kornyezetenkenti Secret Strategia

| Kornyezet | Megoldas | Reszletek |
|-----------|----------|-----------|
| **Local dev** | `.env` file + `python-dotenv` | `.gitignore`-ban! Template: `.env.example` |
| **CI/CD** | GitHub Secrets / GitLab CI Variables | Encrypted at rest, masked in logs |
| **Staging** | Kubernetes Secrets (encrypted etcd) | `EncryptionConfiguration` kotelezo |
| **Production** | HashiCorp Vault | Dynamic secrets, auto-rotation, audit log |

### 8.2 Vault Policy AIFlow-hoz

```hcl
# vault/policies/aiflow-api.hcl
path "secret/data/aiflow/*" {
  capabilities = ["read"]
}

path "database/creds/aiflow-db-role" {
  capabilities = ["read"]
}

path "transit/encrypt/aiflow-pii" {
  capabilities = ["update"]
}

path "transit/decrypt/aiflow-pii" {
  capabilities = ["update"]
}

# TILOS: admin muveletek
path "sys/*" {
  capabilities = ["deny"]
}
```

### 8.3 Secret Rotation Policy

```yaml
# Rotation schedule konfiguracio
rotation_policy:
  database_password:
    method: vault_dynamic
    ttl: 24h
    max_ttl: 72h

  llm_api_keys:
    method: manual_with_reminder
    rotation_interval: 90d
    alert_before_expiry: 14d

  jwt_signing_key:
    method: automated
    rotation_interval: 90d
    overlap_period: 24h    # Mindket kulcs ervenyes atmeneti idoszakban

  tls_certificates:
    method: cert_manager
    renewal_before_expiry: 30d

  redis_password:
    method: vault_dynamic
    ttl: 48h
```

---

## 9. Dependency Security

### 9.1 Automatizalt Vulnerability Scanning

```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on:
  push:
    branches: [main, develop]
  pull_request:
  schedule:
    - cron: '0 6 * * 1'  # Hetfon reggel 6-kor

jobs:
  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: |
          pip install pip-audit
          pip-audit --requirement requirements.txt --strict --desc

  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'aiflow-api:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  sbom-generation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          pip install cyclonedx-bom
          cyclonedx-py requirements \
            --input requirements.txt \
            --output sbom.json \
            --format json \
            --schema-version 1.5
      - uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.json
```

### 9.2 Dependabot Konfiguracio

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    reviewers:
      - "security-team"
    labels:
      - "dependencies"
      - "security"
    # Csak security update-ek automatikusan
    allow:
      - dependency-type: "direct"

  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    reviewers:
      - "security-team"
```

### 9.3 Pre-commit Security Hooks

```yaml
# .pre-commit-config.yaml (biztonsagi kiegeszites)
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.7
    hooks:
      - id: bandit
        args: ['-r', 'aiflow/', '-ll']
```

---

## 10. Incident Response

### 10.1 Security Incident Classification

| Severity | Leiras | Pelda | Response Time |
|----------|--------|-------|---------------|
| **P0 - Critical** | Aktiv adatszivargas, rendszer kompromittalas | LLM API key kiszivarog, DB breach | < 15 perc |
| **P1 - High** | Potencialis vulnerability kihasznalasa | Prompt injection sikeres, auth bypass | < 1 ora |
| **P2 - Medium** | Vulnerability felfedezve, nem kihasznalva | Dependency CVE (CRITICAL), config hiba | < 4 ora |
| **P3 - Low** | Minor security issue, nincs kozvetlen hatas | Dependency CVE (LOW), log hygiene | < 24 ora |

### 10.2 Response Playbook

```
P0/P1 Incident Response Flow:

1. DETEKTALAS (0-5 perc)
   - Alert beerkezett (Langfuse anomaly / Grafana alert / manual report)
   - On-call engineer ertesitese (PagerDuty/Opsgenie)

2. CONTAINMENT (5-30 perc)
   - Erintett API key-ek azonnali revoke-olasa
   - Erintett service izolalasa (network policy update)
   - Rate limiting szigoritasa / endpoint lekapcsolasa
   - Parancs: kubectl scale deployment aiflow-api --replicas=0

3. INVESTIGATION (30-120 perc)
   - Audit log elemzes (Langfuse traces + app logs)
   - Erintett user/team scope megallapitasa
   - Root cause azonositasa
   - SQL: SELECT * FROM audit_log WHERE timestamp > [incident_start]
          AND event_type IN ('auth_failure', 'injection_detected');

4. ERADICATION (valtozo)
   - Vulnerability patch deploy
   - Credentials rotation (minden erintett secret)
   - Konfiguracio javitas

5. RECOVERY (valtozo)
   - Service ujrainditasa monitoring-gal
   - Gradual traffic visszakapcsolasa
   - Stakeholder ertesites

6. POST-MORTEM (48 oran belul)
   - Blameless post-mortem dokumentum
   - Action items jira ticket-ekbe
   - Security runbook frissites
```

### 10.3 Kommunikacios Protokoll

| Cel | P0 | P1 | P2 | P3 |
|-----|----|----|----|----|
| Security Team | Azonnali | Azonnali | 1 oran belul | Napi standup |
| Engineering Lead | 15 percen belul | 1 oran belul | Napi riport | Heti riport |
| Management | 30 percen belul | 4 oran belul | Heti riport | Havi riport |
| Ugyfelek (ha erintettek) | 24 oran belul | 48 oran belul | Nem szukseges | Nem szukseges |
| Hatosag (GDPR eseten) | 72 oran belul | 72 oran belul | Merlegeles | Nem szukseges |

---

## 11. Compliance Checklist

### 11.1 SOC 2 Type II Mapping

| SOC 2 Criteria | AIFlow Control | Implementacio |
|----------------|----------------|---------------|
| CC6.1 - Logical Access | RBAC + JWT auth | Phase 2 |
| CC6.2 - Auth Mechanisms | MFA + API key management | Phase 3 |
| CC6.3 - Registration/Authorization | User/team provisioning API | Phase 2 |
| CC6.6 - Encryption in Transit | TLS 1.3 minden connection-on | Phase 1 |
| CC6.7 - Encryption at Rest | PostgreSQL TDE + Vault | Phase 3 |
| CC7.1 - Vulnerability Management | Dependabot + pip-audit + Trivy | Phase 4 |
| CC7.2 - Activity Monitoring | Langfuse + Grafana + audit log | Phase 2 |
| CC8.1 - Change Management | Git-based CI/CD + approval flow | Phase 1 |

### 11.2 GDPR Megfelelosseg

| GDPR Kovetelmeny | AIFlow Megvalositas |
|-------------------|---------------------|
| Art. 5 - Data Minimization | Csak szukseges adatok tarolasa, TTL policy minden collection-on |
| Art. 6 - Lawful Basis | Consent management UI + audit trail |
| Art. 17 - Right to Erasure | `DELETE /api/v1/users/{id}/data` - cascade torles |
| Art. 20 - Data Portability | `GET /api/v1/users/{id}/export` - JSON export |
| Art. 25 - Privacy by Design | PII detection + encryption by default |
| Art. 32 - Security Measures | Teljes Section 1-10 implementacio |
| Art. 33 - Breach Notification | Incident Response playbook (Section 10), 72 oras hatosagi ertesites |
| Art. 35 - DPIA | AI specifikus DPIA template keszitese Phase 5-ben |

### 11.3 ISO 27001 Mapping (Annex A Highlights)

| ISO 27001 Control | AIFlow Implementacio | Phase |
|--------------------|---------------------|-------|
| A.8.2 - Privileged Access | RBAC role hierarchy, admin MFA | 2 |
| A.8.5 - Secure Authentication | RS256 JWT, API key hashing | 2 |
| A.8.9 - Configuration Management | IaC (Terraform/Pulumi), GitOps | 4 |
| A.8.20 - Network Security | K8s network policies, ingress TLS | 3 |
| A.8.24 - Cryptography | TLS 1.3, AES-256, Vault KMS | 3 |
| A.8.28 - Secure Coding | Bandit, pre-commit hooks, code review | 1 |

---

## 12. Implementation Phases

Az alabbi tablazat mutatja, hogy melyik security feature melyik framework Phase-ben kerul implementalasra:

### Phase 1 - Foundation (Core Security)

```
[x] TLS 1.3 minden connection-on (API, DB, Redis)
[x] .env-based secret management (dev kornyezet)
[x] .gitignore + detect-secrets pre-commit hook
[x] Bandit static analysis a CI pipeline-ban
[x] Alapveto input validation (Pydantic models)
[x] CORS konfiguracio (strict origin list)
```

### Phase 2 - Auth & Access Control

```
[x] JWT authentication (RS256, 15 min TTL)
[x] RBAC implementacio (admin, team_lead, member, viewer)
[x] API key management (create, revoke, hash storage)
[x] Audit logging (minden auth event)
[x] Rate limiting alapok (per-user)
[x] Langfuse trace-based monitoring
```

### Phase 3 - Data Protection

```
[x] PostgreSQL column-level encryption (PII mezok)
[x] Redis TLS + authentication
[x] Vault integracio (staging/production secrets)
[x] PII detection es redaction pipeline
[x] Kubernetes Secrets (encrypted etcd)
[x] Network policies (namespace isolation)
```

### Phase 4 - CI/CD Security

```
[x] pip-audit a CI pipeline-ban
[x] Container image scanning (Trivy)
[x] SBOM generalas (CycloneDX)
[x] Dependabot konfiguracio
[x] Signed container images (cosign)
[x] IaC security scanning (checkov)
```

### Phase 5 - Advanced LLM Security

```
[x] Prompt injection detection (PromptGuard)
[x] Canary token rendszer
[x] Output guardrails (content filtering)
[x] Per-team token/cost budgetek
[x] LLM-specifikus rate limiting
[x] DPIA (Data Protection Impact Assessment)
```

### Phase 6 - Enterprise Hardening

```
[x] Vault dynamic credentials (DB, Redis)
[x] JWT key rotation automation
[x] Full SOC 2 control evidence collection
[x] Incident response playbook veglegesites
[x] Security awareness training docs
[x] Penetration testing (kulso audit)
```

### Phase 7 - Continuous Security

```
[x] Service mesh (Istio) merlegeles/bevezetes
[x] Runtime security monitoring (Falco)
[x] Automated compliance reporting
[x] Bug bounty program inditasa
[x] ISO 27001 certification elokezites
[x] Red team exercise (LLM-specifikus)
```

---

## Osszefoglalas

A security hardening plan 7 fazisban, fokozatosan epiti ki az AIFlow vedelmeit. Minden fazis az elozo eredmenyeire epit, es a legkritikusabb vedelmek (TLS, auth, input validation) mar Phase 1-2-ben implementalodnak. Az LLM-specifikus biztonsagi megoldasok (prompt injection, canary tokens, output guardrails) Phase 5-ben kerulnek bevezetesre, miutan az alap infrastruktura stabil.

**Fontos:** Ez a dokumentum elo dokumentum - minden security incident utan felulvizsgalando es frissitendo.
