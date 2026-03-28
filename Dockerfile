# === BUILD STAGE ===
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml README.md ./
# Install dependencies only (no source code yet = better layer caching)
RUN uv pip install --system --no-cache -e "."

# === API ===
FROM python:3.12-slim AS api

RUN useradd -m -s /bin/bash aiflow
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

USER aiflow
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health/live', timeout=3).raise_for_status()" || exit 1

CMD ["uvicorn", "aiflow.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# === WORKER ===
FROM api AS worker
CMD ["python", "-m", "aiflow.execution.worker"]

# === RPA WORKER (Playwright + ffmpeg) ===
FROM mcr.microsoft.com/playwright/python:v1.40.0 AS rpa-worker

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY src/ ./src/
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e ".[rpa]"
RUN playwright install chromium

CMD ["python", "-m", "aiflow.execution.worker"]
