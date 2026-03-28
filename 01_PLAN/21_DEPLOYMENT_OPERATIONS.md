# AIFlow - Deployment & Operations Plan

**Cel:** Production-ready deployment pipeline, zero-downtime releases, megbizhato uzemeltetes.
**Stack:** Python 3.12+, FastAPI, PostgreSQL+pgvector, Redis, arq workers, Kubernetes.

---

## 1. Docker Image Build Pipeline

### Multi-stage Dockerfile

Harom image variant: `api`, `worker`, `rpa-worker`. Kozos base, kicsi vegleges image.

```dockerfile
# === Stage 1: Builder ===
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv pip install --system --no-cache -r pyproject.toml

COPY src/ src/
RUN uv pip install --system --no-cache .

# === Stage 2: Runtime base ===
FROM python:3.12-slim AS runtime-base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl tini \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r aiflow && useradd -r -g aiflow -d /app aiflow
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

RUN chown -R aiflow:aiflow /app
USER aiflow

# === Variant: API ===
FROM runtime-base AS api
EXPOSE 8000
ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "aiflow.api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--loop", "uvloop", "--http", "httptools"]

# === Variant: Worker ===
FROM runtime-base AS worker
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "aiflow.queue.worker"]

# === Variant: RPA Worker (extra deps: playwright, xvfb) ===
FROM runtime-base AS rpa-worker
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install playwright && playwright install chromium --with-deps
USER aiflow
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "aiflow.rpa.worker"]
```

### CI Build (GitHub Actions reszlet)

```yaml
# .github/workflows/build.yml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        variant: [api, worker, rpa-worker]
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/build-push-action@v5
        with:
          context: .
          target: ${{ matrix.variant }}
          push: true
          tags: |
            ghcr.io/bestix/aiflow-${{ matrix.variant }}:${{ github.sha }}
            ghcr.io/bestix/aiflow-${{ matrix.variant }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Layer caching strategia: `pyproject.toml` + `uv.lock` elobb masolodik mint a forras, igy dependency valtozas nelkul a `uv pip install` layer cached marad.

---

## 2. Docker Compose (Dev)

Teljes lokalis fejlesztoi kornyezet egyetlen `docker compose up`-pal.

```yaml
# docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: aiflow
      POSTGRES_USER: aiflow
      POSTGRES_PASSWORD: localdev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aiflow"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy volatile-lru
      --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s

  api:
    build:
      context: .
      target: api
    ports:
      - "8000:8000"
    environment:
      AIFLOW_ENV: development
      AIFLOW_DATABASE__URL: postgresql+asyncpg://aiflow:localdev@postgres:5432/aiflow
      AIFLOW_REDIS__URL: redis://redis:6379/0
      LOG_LEVEL: DEBUG
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src  # Hot-reload dev

  worker:
    build:
      context: .
      target: worker
    environment:
      AIFLOW_ENV: development
      AIFLOW_DATABASE__URL: postgresql+asyncpg://aiflow:localdev@postgres:5432/aiflow
      AIFLOW_REDIS__URL: redis://redis:6379/0
      WORKER_CONCURRENCY: 5
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  kroki:
    image: yuzutech/kroki
    ports:
      - "8010:8000"

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@local.dev
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    profiles: ["tools"]

volumes:
  pgdata:
  redisdata:
```

---

## 3. Kubernetes Architecture

### Namespace es RBAC

```yaml
# k8s/base/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aiflow
  labels:
    app.kubernetes.io/part-of: aiflow
    istio-injection: enabled
```

### API Deployment + HPA

```yaml
# k8s/base/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiflow-api
  namespace: aiflow
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiflow-api
  template:
    metadata:
      labels:
        app: aiflow-api
    spec:
      serviceAccountName: aiflow-api
      terminationGracePeriodSeconds: 30
      containers:
        - name: api
          image: ghcr.io/bestix/aiflow-api:TAG
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          envFrom:
            - configMapRef:
                name: aiflow-config
            - secretRef:
                name: aiflow-secrets
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aiflow-api-hpa
  namespace: aiflow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aiflow-api
  minReplicas: 3
  maxReplicas: 12
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
```

### Worker Deployment + HPA

```yaml
# k8s/base/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiflow-worker
  namespace: aiflow
spec:
  replicas: 5
  selector:
    matchLabels:
      app: aiflow-worker
  template:
    spec:
      terminationGracePeriodSeconds: 300  # 5 perc a long-running task-ekhez
      containers:
        - name: worker
          image: ghcr.io/bestix/aiflow-worker:TAG
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: "2"
              memory: 4Gi
          envFrom:
            - configMapRef:
                name: aiflow-config
            - secretRef:
                name: aiflow-secrets
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aiflow-worker-hpa
  namespace: aiflow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aiflow-worker
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: External
      external:
        metric:
          name: redis_queue_depth
          selector:
            matchLabels:
              queue: aiflow:queue
        target:
          type: AverageValue
          averageValue: "5"
```

### PodDisruptionBudget

```yaml
# k8s/base/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: aiflow-api-pdb
  namespace: aiflow
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: aiflow-api
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: aiflow-worker-pdb
  namespace: aiflow
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: aiflow-worker
```

---

## 4. Blue-Green Deployment Strategy

Zero-downtime release Kubernetes Service selector valtas alapjan.

```yaml
# k8s/overlays/prod/blue-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiflow-api-blue
  namespace: aiflow
  labels:
    app: aiflow-api
    slot: blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiflow-api
      slot: blue
  template:
    metadata:
      labels:
        app: aiflow-api
        slot: blue
    spec:
      containers:
        - name: api
          image: ghcr.io/bestix/aiflow-api:v2.1.0
---
# Service a traffic iranyitashoz
apiVersion: v1
kind: Service
metadata:
  name: aiflow-api
  namespace: aiflow
spec:
  selector:
    app: aiflow-api
    slot: blue          # <-- itt valtunk green-re
  ports:
    - port: 80
      targetPort: 8000
```

### Deployment script

```bash
#!/bin/bash
# scripts/blue-green-deploy.sh
set -euo pipefail

NEW_VERSION=$1
CURRENT_SLOT=$(kubectl get svc aiflow-api -n aiflow -o jsonpath='{.spec.selector.slot}')
NEW_SLOT=$( [ "$CURRENT_SLOT" = "blue" ] && echo "green" || echo "blue" )

echo "Current: $CURRENT_SLOT -> Deploying to: $NEW_SLOT"

# 1. Deploy uj verzio az inaktiv slot-ra
kubectl set image deployment/aiflow-api-${NEW_SLOT} \
  api=ghcr.io/bestix/aiflow-api:${NEW_VERSION} -n aiflow

# 2. Varakozas amig az uj pod-ok ready allapotba kerulnek
kubectl rollout status deployment/aiflow-api-${NEW_SLOT} -n aiflow --timeout=300s

# 3. Smoke test az uj slot-on (ClusterIP-n belul)
SMOKE_POD=$(kubectl get pod -l slot=${NEW_SLOT},app=aiflow-api -n aiflow -o name | head -1)
kubectl exec -n aiflow ${SMOKE_POD} -- curl -sf http://localhost:8000/health || {
  echo "SMOKE TEST FAILED - aborting"
  exit 1
}

# 4. Traffic atiranyitas
kubectl patch svc aiflow-api -n aiflow -p "{\"spec\":{\"selector\":{\"slot\":\"${NEW_SLOT}\"}}}"
echo "Traffic switched to $NEW_SLOT (version $NEW_VERSION)"

# 5. Rollback lehetoseg 15 percig
echo "Rollback: kubectl patch svc aiflow-api -n aiflow -p '{\"spec\":{\"selector\":{\"slot\":\"${CURRENT_SLOT}\"}}}'"
```

---

## 5. Health Checks

### API Health Probes

```yaml
# API container probe-ok
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 15
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 2

startupProbe:
  httpGet:
    path: /health/startup
    port: 8000
  periodSeconds: 5
  failureThreshold: 30  # max 150s az indulasra
```

### Health endpoint implementacio

```python
# src/aiflow/api/health.py
from fastapi import APIRouter, Response, status
from aiflow.core.config import get_settings
import asyncpg
import redis.asyncio as redis

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
async def liveness():
    """Process el es valaszol - K8s liveness probe."""
    return {"status": "alive"}

@router.get("/ready")
async def readiness(response: Response):
    """Kesz forgalmat fogadni - K8s readiness probe."""
    checks = {}

    # HELYES: Meglevo connection pool hasznalata
    async def check_postgres(pool) -> bool:
        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    # DB check (meglevo pool-bol)
    try:
        from aiflow.core.db import get_pool
        pool = get_pool()
        if await check_postgres(pool):
            checks["database"] = "ok"
        else:
            checks["database"] = "error: pool health check failed"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        checks["database"] = f"error: {e}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # Redis check (meglevo pool-bol)
    try:
        from aiflow.core.redis import get_redis_pool
        redis_pool = get_redis_pool()
        await redis_pool.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ready" if response.status_code != 503 else "not_ready", "checks": checks}

@router.get("/startup")
async def startup():
    """Alembic migraciok lefutottak, registry betoltve - K8s startup probe."""
    from aiflow.core.registry import get_registry
    registry = get_registry()
    return {
        "status": "started",
        "workflows_loaded": len(registry.workflows),
        "skills_loaded": len(registry.skills),
    }
```

### Worker Health (TCP socket probe)

```yaml
# Worker nem HTTP, ezert TCP/exec probe
livenessProbe:
  exec:
    command: ["python", "-c", "from aiflow.queue.health import check_worker; check_worker()"]
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  exec:
    command: ["python", "-c", "from aiflow.queue.health import check_queue_connection; check_queue_connection()"]
  periodSeconds: 15
  failureThreshold: 2
```

---

## 6. Graceful Shutdown

### Signal handling es in-flight completion

```python
# src/aiflow/queue/worker.py
import asyncio
import signal
import structlog
from arq import create_pool
from aiflow.core.config import get_settings

logger = structlog.get_logger()

class GracefulWorker:
    def __init__(self):
        self.shutting_down = False
        self.active_tasks: set[asyncio.Task] = set()
        self.drain_timeout = 120  # max 2 perc a leallas elott

    def setup_signal_handlers(self):
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self._shutdown(s)))

    async def _shutdown(self, sig: signal.Signals):
        logger.warning("shutdown_signal_received", signal=sig.name, active_tasks=len(self.active_tasks))
        self.shutting_down = True

        # 1. Ne fogadjon tobb feladatot
        # 2. Varjon az aktiv task-ekre (timeout-tal)
        if self.active_tasks:
            logger.info("waiting_for_active_tasks", count=len(self.active_tasks))
            done, pending = await asyncio.wait(
                self.active_tasks, timeout=self.drain_timeout
            )
            if pending:
                logger.error("force_cancelling_tasks", count=len(pending))
                for task in pending:
                    task.cancel()
                await asyncio.wait(pending, timeout=10)

        # 3. Checkpoint mentes a meg nem befejezett workflow-khoz
        for task in self.active_tasks:
            if not task.done():
                await self._save_checkpoint(task)

        logger.info("graceful_shutdown_complete")

    async def _save_checkpoint(self, task: asyncio.Task):
        """Menti az aktualis workflow allapotat, igy restart utan folytatni tudja."""
        try:
            run_id = getattr(task, "run_id", None)
            if run_id:
                logger.info("saving_checkpoint", run_id=run_id)
                # Checkpoint logika - lasd engine/checkpoint.py
        except Exception as e:
            logger.error("checkpoint_save_failed", error=str(e))
```

---

## 7. Database Operations

### Backup strategia

```yaml
# k8s/base/db-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: aiflow-db-backup
  namespace: aiflow
spec:
  schedule: "0 */6 * * *"  # 6 orankent
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:16
              command:
                - /bin/bash
                - -c
                - |
                  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
                  FILENAME="aiflow_${TIMESTAMP}.sql.gz"
                  pg_dump -h $PGHOST -U $PGUSER -d aiflow \
                    --format=custom --compress=9 \
                    --file=/backup/${FILENAME}
                  # Upload S3-re
                  aws s3 cp /backup/${FILENAME} \
                    s3://aiflow-backups/db/${FILENAME} \
                    --storage-class STANDARD_IA
                  echo "Backup complete: ${FILENAME}"
              envFrom:
                - secretRef:
                    name: aiflow-db-credentials
              volumeMounts:
                - name: backup-vol
                  mountPath: /backup
          volumes:
            - name: backup-vol
              emptyDir:
                sizeLimit: 10Gi
          restartPolicy: OnFailure
```

### Point-in-Time Recovery (WAL archivalas)

```
# postgresql.conf (prod)
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://aiflow-backups/wal/%f'
archive_timeout = 60
```

### Alembic migration a CI/CD-ben

```yaml
# .github/workflows/deploy.yml - migration step
- name: Run Alembic migrations
  run: |
    kubectl run aiflow-migrate \
      --image=ghcr.io/bestix/aiflow-api:${{ github.sha }} \
      --restart=Never \
      --namespace=aiflow \
      --env="DATABASE_URL=${{ secrets.DATABASE_URL }}" \
      --command -- alembic upgrade head
    kubectl wait --for=condition=complete job/aiflow-migrate \
      --namespace=aiflow --timeout=120s
```

### Connection Pooling (PgBouncer)

K8s-ben tobb API/Worker replika eseten a kozvetlen connection pool
tullepi a PostgreSQL max_connections limitet:
- 4 API (pool=20) + 10 Worker (pool=10) = 180 connection > default 100

**Megoldas:** PgBouncer transaction-mode pooling:

```yaml
# k8s/base/pgbouncer.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: pgbouncer
        image: edoburu/pgbouncer:1.22
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef: {name: aiflow-secrets, key: database-url}
        - name: POOL_MODE
          value: "transaction"
        - name: MAX_CLIENT_CONN
          value: "500"
        - name: DEFAULT_POOL_SIZE
          value: "50"
```

---

## 8. Redis Operations

### Persistence es memory config

```
# redis.conf (prod)
maxmemory 2gb
maxmemory-policy volatile-lru

# AOF persistence (queue megbizhatosag)
appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# RDB snapshot (backup)
save 900 1
save 300 10
save 60 10000
```

### Key expiry strategia

```python
# src/aiflow/queue/redis_keys.py
"""Redis key namespace-ek es TTL-ek."""

REDIS_KEY_CONFIG = {
    # Queue task-ek: nincs TTL, arq kezeli
    "aiflow:queue:*": None,

    # Workflow execution cache: 24 ora
    "aiflow:cache:workflow:{run_id}": 86400,

    # Rate limiter: 1 ora
    "aiflow:ratelimit:{api_key}:{window}": 3600,

    # Distributed lock: 5 perc
    "aiflow:lock:{resource}": 300,

    # Session / ephemeral: 1 ora
    "aiflow:session:{session_id}": 3600,
}
```

### Redis Sentinel (HA)

```yaml
# k8s/base/redis-sentinel.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: aiflow
spec:
  serviceName: redis
  replicas: 3
  template:
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command: ["redis-server", "/etc/redis/redis.conf"]
          ports:
            - containerPort: 6379
          volumeMounts:
            - name: redis-config
              mountPath: /etc/redis
            - name: redis-data
              mountPath: /data
        - name: sentinel
          image: redis:7-alpine
          command: ["redis-sentinel", "/etc/redis/sentinel.conf"]
          ports:
            - containerPort: 26379
  volumeClaimTemplates:
    - metadata:
        name: redis-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

---

## 9. Monitoring & Alerting Setup

### Prometheus metrics (app szintu)

```python
# src/aiflow/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info

# Workflow metriak
WORKFLOW_RUNS_TOTAL = Counter(
    "aiflow_workflow_runs_total",
    "Osszes workflow futtatas",
    ["workflow_name", "status"]
)
WORKFLOW_DURATION = Histogram(
    "aiflow_workflow_duration_seconds",
    "Workflow futasi ido",
    ["workflow_name"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)

# LLM metriak
LLM_REQUESTS_TOTAL = Counter(
    "aiflow_llm_requests_total",
    "LLM API hivasok",
    ["provider", "model", "status"]
)
LLM_TOKEN_USAGE = Counter(
    "aiflow_llm_tokens_total",
    "Felhasznalt tokenek",
    ["provider", "model", "type"]  # type: prompt/completion
)
LLM_COST_USD = Counter(
    "aiflow_llm_cost_usd_total",
    "LLM koltseg USD-ben",
    ["provider", "model"]
)

# Queue metriak
QUEUE_DEPTH = Gauge(
    "aiflow_queue_depth",
    "Varakozo feladatok szama",
    ["queue_name"]
)
WORKER_ACTIVE_TASKS = Gauge(
    "aiflow_worker_active_tasks",
    "Aktiv task-ek worker-enkent",
    ["worker_id"]
)
```

### Grafana dashboard config (fo dashboard)

```json
{
  "title": "AIFlow Production Overview",
  "panels": [
    {"title": "Workflow Success Rate",        "expr": "rate(aiflow_workflow_runs_total{status='completed'}[5m]) / rate(aiflow_workflow_runs_total[5m]) * 100"},
    {"title": "P95 Workflow Duration",         "expr": "histogram_quantile(0.95, rate(aiflow_workflow_duration_seconds_bucket[5m]))"},
    {"title": "LLM Cost / Hour",              "expr": "increase(aiflow_llm_cost_usd_total[1h])"},
    {"title": "Queue Depth",                  "expr": "aiflow_queue_depth"},
    {"title": "Active Workers",               "expr": "count(aiflow_worker_active_tasks > 0)"},
    {"title": "API Request Rate",             "expr": "rate(http_requests_total{app='aiflow-api'}[1m])"},
    {"title": "API Error Rate (5xx)",         "expr": "rate(http_requests_total{app='aiflow-api', status=~'5..'}[5m])"},
    {"title": "DB Connection Pool Usage",     "expr": "aiflow_db_pool_used / aiflow_db_pool_size * 100"},
    {"title": "Redis Memory Usage",           "expr": "redis_memory_used_bytes / redis_memory_max_bytes * 100"}
  ]
}
```

### Alert rules

```yaml
# k8s/monitoring/alerting-rules.yaml
groups:
  - name: aiflow.rules
    rules:
      - alert: HighWorkflowFailureRate
        expr: rate(aiflow_workflow_runs_total{status="failed"}[10m]) / rate(aiflow_workflow_runs_total[10m]) > 0.1
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Workflow failure rate > 10% az elmult 10 percben"
          runbook: "https://wiki.internal/runbooks/aiflow-high-failure-rate"

      - alert: QueueBacklogHigh
        expr: aiflow_queue_depth > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Queue melyseg > 100 tobb mint 10 perce, worker scaling szukseges"

      - alert: LLMCostSpike
        expr: increase(aiflow_llm_cost_usd_total[1h]) > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM koltseg > $50/ora - ellenorizni kell a token hasznalat"

      - alert: APIHighLatency
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{app="aiflow-api"}[5m])) > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API P99 latency > 5s"
```

### PagerDuty / Slack integracio

Alertmanager config-ban `critical` -> PagerDuty, `warning` -> Slack channel.

```yaml
# alertmanager.yml
receivers:
  - name: pagerduty-critical
    pagerduty_configs:
      - service_key_file: /etc/alertmanager/secrets/pagerduty-key
        severity: critical

  - name: slack-warnings
    slack_configs:
      - api_url_file: /etc/alertmanager/secrets/slack-webhook
        channel: "#aiflow-alerts"
        title: '{{ .CommonLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}'

route:
  receiver: slack-warnings
  routes:
    - match:
        severity: critical
      receiver: pagerduty-critical
```

---

## 10. Log Management

### Structlog JSON config

```python
# src/aiflow/observability/logging.py
import structlog

def configure_logging(env: str = "production"):
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if env == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO+
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Correlation run_id-vel

```python
# src/aiflow/api/middleware.py
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        run_id = request.headers.get("X-Run-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            run_id=run_id,
            path=request.url.path,
            method=request.method,
        )
        response = await call_next(request)
        response.headers["X-Run-ID"] = run_id
        return response
```

### ELK / Loki gyujtes

```yaml
# Promtail config - JSON logok gyujtese stdout-rol
scrape_configs:
  - job_name: aiflow
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_namespace]
        regex: aiflow
        action: keep
    pipeline_stages:
      - json:
          expressions:
            level: level
            run_id: run_id
            workflow: workflow_name
            timestamp: timestamp
      - labels:
          level:
          workflow:
      - timestamp:
          source: timestamp
          format: RFC3339
```

**Log retention:** hot 7 nap, warm 30 nap, archive 90 nap (S3 Glacier).

---

## 11. Disaster Recovery

### RPO / RTO celok

| Tier | Komponens | RPO | RTO | Strategia |
|------|-----------|-----|-----|-----------|
| 1 | PostgreSQL | 1 perc | 15 perc | WAL streaming + PITR |
| 2 | Redis queue | 1 masodperc | 5 perc | AOF + Sentinel failover |
| 3 | API service | N/A | 2 perc | K8s auto-restart + HPA |
| 4 | Worker | N/A | 5 perc | Checkpoint + auto-recovery |

### Backup restore procedure

```bash
#!/bin/bash
# scripts/disaster-recovery.sh
set -euo pipefail

echo "=== AIFlow Disaster Recovery ==="

# 1. Legutobbi backup megtalalasa
LATEST=$(aws s3 ls s3://aiflow-backups/db/ --recursive | sort | tail -1 | awk '{print $4}')
echo "Restoring from: ${LATEST}"

# 2. Download es restore
aws s3 cp "s3://aiflow-backups/db/${LATEST}" /tmp/restore.sql.gz

# 3. Uj DB letrehozasa
createdb -h $PGHOST -U $PGUSER aiflow_restored

# 4. Restore
pg_restore -h $PGHOST -U $PGUSER -d aiflow_restored \
  --jobs=4 --verbose /tmp/restore.sql.gz

# 5. PITR: WAL replay egy adott idopontig
# recovery.conf-ban:
#   restore_command = 'aws s3 cp s3://aiflow-backups/wal/%f %p'
#   recovery_target_time = '2026-03-28 10:00:00 UTC'
#   recovery_target_action = 'promote'

# 6. App atiranyitas az uj DB-re
kubectl set env deployment/aiflow-api \
  DATABASE_URL=postgresql+asyncpg://aiflow:pass@restored-db:5432/aiflow_restored \
  -n aiflow

echo "Recovery complete - verify data integrity!"
```

### Backup Verifikacio

**Utemterv:**
- Heti: Automatikus backup integrity check (pg_verifybackup)
- Havi: Teljes restore teszt staging kornyezetbe
- Negyedevente: DR drill (teljes rendszer helyreallitas)

**Retention policy:**
- Napi backup: 30 napig
- Heti backup: 6 honapig
- Havi backup: 2 evig

**Monitoring:**
- Alert ha backup job sikertelen
- Alert ha backup meret jelentosen valtozik (>20%)
- Havi riport backup statuszrol

### Multi-region megjegyzesek

- Primary region: EU-West-1, DR region: EU-Central-1
- PostgreSQL logical replication a DR region-be (async, ~5s lag)
- Redis: kulon cluster region-onkent, queue state nem replikalt (ujrakezdheto)
- DNS failover: Route53 health check alapu, 60s TTL

---

## 12. Runbook Templates

### 12.1 Worker scaling (manualis)

```bash
# Azonnali worker scale-up
kubectl scale deployment aiflow-worker -n aiflow --replicas=15

# Ellenorzes
kubectl get pods -n aiflow -l app=aiflow-worker
kubectl top pods -n aiflow -l app=aiflow-worker

# Queue melyseg ellenorzese
redis-cli -h redis.aiflow.svc.cluster.local LLEN aiflow:queue
```

### 12.2 Secret rotation

```bash
# 1. Uj secret generalas
NEW_DB_PASS=$(openssl rand -base64 32)

# 2. DB password frissites
psql -h $PGHOST -U postgres -c "ALTER USER aiflow PASSWORD '${NEW_DB_PASS}';"

# 3. K8s secret update
kubectl create secret generic aiflow-secrets \
  --from-literal=DATABASE_URL="postgresql+asyncpg://aiflow:${NEW_DB_PASS}@pgbouncer:6432/aiflow" \
  --dry-run=client -o yaml | kubectl apply -n aiflow -f -

# 4. Rolling restart (zero-downtime)
kubectl rollout restart deployment/aiflow-api -n aiflow
kubectl rollout restart deployment/aiflow-worker -n aiflow
kubectl rollout status deployment/aiflow-api -n aiflow --timeout=120s
```

### 12.3 Deployment rollback

```bash
# Automatikus rollback az elozo verzio-ra
kubectl rollout undo deployment/aiflow-api -n aiflow

# Blue-green rollback (azonnali traffic switch)
CURRENT_SLOT=$(kubectl get svc aiflow-api -n aiflow -o jsonpath='{.spec.selector.slot}')
PREV_SLOT=$( [ "$CURRENT_SLOT" = "blue" ] && echo "green" || echo "blue" )
kubectl patch svc aiflow-api -n aiflow -p "{\"spec\":{\"selector\":{\"slot\":\"${PREV_SLOT}\"}}}"

# Ellenorzes
kubectl get svc aiflow-api -n aiflow -o jsonpath='{.spec.selector.slot}'
curl -sf https://api.aiflow.internal/health/ready
```

### 12.4 Dead Letter Queue (DLQ) urites

```bash
# DLQ tartalma
redis-cli -h redis.aiflow.svc.cluster.local LRANGE aiflow:dlq 0 -1

# Ujra-feldolgozas (visszarakni a fo queue-ba)
redis-cli -h redis.aiflow.svc.cluster.local --pipe <<'CMDS'
RPOPLPUSH aiflow:dlq aiflow:queue
RPOPLPUSH aiflow:dlq aiflow:queue
RPOPLPUSH aiflow:dlq aiflow:queue
CMDS

# Vagy osszes ujrafeldolgozas Python-bol
python -c "
import redis
r = redis.Redis(host='redis.aiflow.svc.cluster.local')
count = 0
while r.rpoplpush('aiflow:dlq', 'aiflow:queue'):
    count += 1
print(f'Requeued {count} tasks')
"

# Teljes DLQ torles (ha nem kell ujrafeldolgozni)
redis-cli -h redis.aiflow.svc.cluster.local DEL aiflow:dlq
```

---

## 13. Cost Optimization

### Worker right-sizing

```yaml
# Harom worker tier koltseghatekonysagra optimalizalva
# Tier 1: Konnyu feladatok (text extraction, validation)
aiflow-worker-light:
  resources:
    requests: {cpu: 250m, memory: 256Mi}
    limits:   {cpu: 500m, memory: 512Mi}
  replicas: 3-10
  node_selector: spot-pool

# Tier 2: Standard (LLM pipeline, RAG)
aiflow-worker-standard:
  resources:
    requests: {cpu: 500m, memory: 1Gi}
    limits:   {cpu: "1", memory: 2Gi}
  replicas: 3-15
  node_selector: on-demand-pool

# Tier 3: Heavy (RPA, batch processing, ML)
aiflow-worker-heavy:
  resources:
    requests: {cpu: "1", memory: 2Gi}
    limits:   {cpu: "2", memory: 4Gi}
  replicas: 1-8
  node_selector: spot-pool  # Batch tolerans a spot preemption-ra
```

### Spot instance strategia (batch worker-ekhez)

```yaml
# k8s/overlays/prod/spot-nodepool.yaml
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: aiflow-spot-workers
spec:
  requirements:
    - key: karpenter.sh/capacity-type
      operator: In
      values: ["spot"]
    - key: node.kubernetes.io/instance-type
      operator: In
      values: ["m6i.xlarge", "m6a.xlarge", "m5.xlarge"]  # Tobbfele tipus a spot availability-ert
  limits:
    resources:
      cpu: "64"
      memory: 256Gi
  ttlSecondsAfterEmpty: 60
  ttlSecondsUntilExpired: 604800  # 7 nap
```

### Redis memory optimalizacio

```python
# src/aiflow/queue/redis_optimization.py
"""Redis memory hasznalat optimalizacio."""

# 1. Hasznalj MessagePack-ot JSON helyett a queue payload-okhoz
import msgpack

async def enqueue_task(redis_pool, task_data: dict):
    packed = msgpack.packb(task_data, use_bin_type=True)
    await redis_pool.lpush("aiflow:queue", packed)
    # ~40% memory megtakaritas nagy payload-oknal

# 2. Pipeline hasznalat tobb muvelethez
async def bulk_update_metrics(redis_pool, metrics: list[tuple[str, float]]):
    async with redis_pool.pipeline(transaction=False) as pipe:
        for key, value in metrics:
            pipe.set(key, value, ex=3600)
        await pipe.execute()

# 3. Redis memory monitoring
async def check_memory_usage(redis_pool) -> dict:
    info = await redis_pool.info("memory")
    return {
        "used_mb": info["used_memory"] / 1024 / 1024,
        "peak_mb": info["used_memory_peak"] / 1024 / 1024,
        "fragmentation_ratio": info["mem_fragmentation_ratio"],
        "evicted_keys": info.get("evicted_keys", 0),
    }
```

### Havidijas koltseg becslese (referenciak)

| Komponens | Specifikacio | Becsult koltseg/ho |
|-----------|-------------|-------------------|
| K8s cluster (EKS) | 3 node on-demand | ~$300 |
| API pods (3x) | 1 vCPU, 1GB | ~$90 |
| Worker pods (5-15x) | mix spot/on-demand | ~$200-500 |
| PostgreSQL (RDS) | db.r6g.xlarge, 500GB | ~$450 |
| Redis (ElastiCache) | cache.r6g.large, HA | ~$200 |
| S3 (backups, logs) | ~500GB | ~$15 |
| LLM API calls | fugg a volumen-tol | $500-5000+ |
| **Ossz. (infra, LLM nelkul)** | | **~$1,300-1,600** |

> **Tipp:** A legnagyobb megtakaritas a worker tier-ezesbol es a spot instance-ok hasznalatbol jon. A batch feldolgozo worker-ek 60-70%-kal olcsobbak spot-on.

### Kapacitas Tervezes

**Meretezesi formula:**
workers_needed = (workflows_per_hour * avg_duration_seconds) / 3600

| Deployment meret | Workflows/nap | API replika | Worker replika | PostgreSQL | Redis |
|-----------------|--------------|-------------|----------------|------------|-------|
| Small (dev) | <100 | 1 | 1-2 | 1 (Docker) | 1 (Docker) |
| Medium (staging) | 100-1000 | 2 | 3-5 | 1 (managed) | 1 (Sentinel) |
| Large (prod) | 1000-5000 | 3-4 | 5-15 | 1 (managed, HA) | 3 (cluster) |
| Enterprise | 5000+ | 4-8 | 10-30 | 2+ (read replicas) | 6 (cluster) |

---

## 14. Dockerfile HEALTHCHECK

> **Megjegyzes:** A Dockerfile-ban a `HEALTHCHECK` instrukcioval definialhatjuk
> a container-szintu health check-et Docker Compose es standalone futatas eseten.
> K8s kornyezetben a K8s probe-ok felulirjak, de Docker Compose-ban (dev)
> a beepitett HEALTHCHECK hasznos:
>
> ```dockerfile
> # API variant-ban
> HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
>   CMD curl -sf http://localhost:8000/health/live || exit 1
> ```

---

## Osszefoglalas

| Terulet | Fo dontes | Indoklas |
|---------|-----------|----------|
| Build | Multi-stage, 3 image variant | Kicsi image, gyors deploy |
| Orchestration | Kubernetes + Karpenter | Auto-scaling, spot support |
| Deploy | Blue-green | Zero-downtime, azonnali rollback |
| DB HA | PgBouncer + WAL streaming | Connection pooling + PITR |
| Redis HA | Sentinel + AOF | Queue megbizhatosag |
| Monitoring | Prometheus + Grafana + Alertmanager | Full-stack lathatosag |
| Logging | structlog JSON -> Loki | Strukturalt, korrelalt logok |
| DR | RPO 1 perc, RTO 15 perc | Uzleti elvarasoknak megfelelo |
