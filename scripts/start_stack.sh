#!/usr/bin/env bash
# AIFlow — Full stack startup + validation
#
# Usage:
#   bash scripts/start_stack.sh                # core: PG + Redis + Kroki + migrations + health
#   bash scripts/start_stack.sh --with-api     # + FastAPI on :8102 (background)
#   bash scripts/start_stack.sh --with-ui      # + Vite dev on :5173 (background)
#   bash scripts/start_stack.sh --with-vault   # + Vault dev on :8210
#   bash scripts/start_stack.sh --with-langfuse # + self-hosted Langfuse on :3000
#   bash scripts/start_stack.sh --full         # everything above
#   bash scripts/start_stack.sh --down         # stop everything (keeps volumes)
#   bash scripts/start_stack.sh --validate-only # only run health checks
#
# Logs:
#   Background processes write to .stack_logs/{api,ui}.log
#   PIDs in .stack_logs/{api,ui}.pid

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR=".stack_logs"
mkdir -p "$LOG_DIR"

# ANSI colors (disabled when not a TTY)
if [ -t 1 ]; then
    GREEN="\033[0;32m"; RED="\033[0;31m"; YELLOW="\033[0;33m"; BLUE="\033[0;36m"; RESET="\033[0m"
else
    GREEN=""; RED=""; YELLOW=""; BLUE=""; RESET=""
fi

ok()   { printf '%b[ OK ]%b %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '%b[WARN]%b %s\n' "$YELLOW" "$RESET" "$*"; }
fail() { printf '%b[FAIL]%b %s\n' "$RED" "$RESET" "$*"; }
info() { printf '%b[INFO]%b %s\n' "$BLUE" "$RESET" "$*"; }

# Defaults
WITH_API=0; WITH_UI=0; WITH_VAULT=0; WITH_LANGFUSE=0
DOWN=0; VALIDATE_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --with-api) WITH_API=1 ;;
        --with-ui) WITH_UI=1 ;;
        --with-vault) WITH_VAULT=1 ;;
        --with-langfuse) WITH_LANGFUSE=1 ;;
        --full) WITH_API=1; WITH_UI=1; WITH_VAULT=1; WITH_LANGFUSE=1 ;;
        --down) DOWN=1 ;;
        --validate-only) VALIDATE_ONLY=1 ;;
        -h|--help)
            sed -n '2,18p' "$0"; exit 0 ;;
        *) fail "Unknown flag: $arg"; exit 2 ;;
    esac
done

# Platform-aware Python
if [ -x ".venv/Scripts/python.exe" ]; then
    PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    fail "No .venv found — run: make setup"
    exit 1
fi

##############################################################################
# DOWN: stop everything
##############################################################################
if [ "$DOWN" -eq 1 ]; then
    info "Stopping all stack components..."
    [ -f "$LOG_DIR/api.pid" ] && kill "$(cat "$LOG_DIR/api.pid")" 2>/dev/null && rm "$LOG_DIR/api.pid" && ok "API stopped" || true
    [ -f "$LOG_DIR/ui.pid" ] && kill "$(cat "$LOG_DIR/ui.pid")" 2>/dev/null && rm "$LOG_DIR/ui.pid" && ok "UI stopped" || true
    docker compose down 2>&1 | tail -5
    docker compose -f docker-compose.vault.yml down 2>/dev/null || true
    docker compose -f docker-compose.langfuse.yml down 2>/dev/null || true
    ok "Stack stopped (volumes preserved — use 'make down-volumes' for full reset)"
    exit 0
fi

##############################################################################
# VALIDATE-ONLY: just run health checks
##############################################################################
validate_health() {
    local errors=0

    # PostgreSQL
    if docker exec 07_ai_flow_framwork-db-1 pg_isready -U aiflow -d aiflow_dev >/dev/null 2>&1; then
        ok "PostgreSQL :5433 — accepting connections"
    else
        fail "PostgreSQL :5433 — not ready"; errors=$((errors+1))
    fi

    # Redis
    if [ "$(docker exec 07_ai_flow_framwork-redis-1 redis-cli ping 2>/dev/null)" = "PONG" ]; then
        ok "Redis :6379 — PONG"
    else
        fail "Redis :6379 — not responding"; errors=$((errors+1))
    fi

    # Kroki
    if curl -sf "http://localhost:8080/health" >/dev/null 2>&1 || curl -sf "http://localhost:8080/" >/dev/null 2>&1; then
        ok "Kroki :8080 — HTTP responsive"
    else
        warn "Kroki :8080 — not responsive (optional for diagrams)"
    fi

    # Vault (optional)
    if [ "$WITH_VAULT" -eq 1 ] || curl -sf "http://localhost:8210/v1/sys/health" >/dev/null 2>&1; then
        if curl -sf "http://localhost:8210/v1/sys/health" >/dev/null 2>&1; then
            ok "Vault :8210 — sealed=false (dev mode)"
        else
            warn "Vault :8210 — not running (use --with-vault)"
        fi
    fi

    # Langfuse (optional)
    if curl -sf "http://localhost:3000/api/public/health" >/dev/null 2>&1; then
        ok "Langfuse :3000 — healthy"
    elif [ "$WITH_LANGFUSE" -eq 1 ]; then
        warn "Langfuse :3000 — not yet healthy (may take ~30s on first start)"
    fi

    # API
    if curl -sf "http://localhost:8102/health" >/dev/null 2>&1; then
        ok "FastAPI :8102 — /health = ready"
    elif [ "$WITH_API" -eq 1 ]; then
        warn "FastAPI :8102 — not yet healthy (check $LOG_DIR/api.log)"
    fi

    # UI
    if curl -sf "http://localhost:5173/" >/dev/null 2>&1; then
        ok "Vite UI :5173 — serving"
    elif [ "$WITH_UI" -eq 1 ]; then
        warn "Vite UI :5173 — not yet serving (check $LOG_DIR/ui.log)"
    fi

    # DB migrations head
    if [ -x "$PY" ]; then
        head_rev="$(PYTHONPATH=src "$PY" -m alembic current 2>&1 | grep -oE '[a-f0-9]{12}' | head -1 || true)"
        if [ -n "$head_rev" ]; then
            ok "Alembic — current revision: $head_rev"
        fi
    fi

    return $errors
}

if [ "$VALIDATE_ONLY" -eq 1 ]; then
    info "Running health checks only..."
    validate_health
    exit $?
fi

##############################################################################
# 1. Prerequisites
##############################################################################
echo ""
info "=== AIFlow Stack Startup ==="
echo ""

command -v docker >/dev/null || { fail "docker not found — install Docker Desktop"; exit 1; }
command -v uv >/dev/null || warn "uv not found — venv must already be ready"
[ -f ".env" ] || { fail ".env missing — run: cp .env.example .env (then edit)"; exit 1; }
[ -f "uv.lock" ] || warn "uv.lock missing"
ok "Prerequisites: docker, uv, .env, uv.lock"

##############################################################################
# 2. Editable install sanity (catches OneDrive→local-style moves)
##############################################################################
if ! "$PY" -c "import aiflow" 2>/dev/null; then
    warn "aiflow editable install broken — running 'uv pip install -e .'"
    UV_LINK_MODE=copy uv pip install -e . --quiet
    "$PY" -c "import aiflow" || { fail "aiflow still not importable"; exit 1; }
fi
ok "Python venv: $PY ($("$PY" --version 2>&1))"
ok "aiflow module: $("$PY" -c 'import aiflow; print(aiflow.__file__)' 2>&1 | head -1)"

##############################################################################
# 3. Core Docker stack
##############################################################################
info "Starting core Docker services (PostgreSQL + Redis)..."
docker compose up -d db redis 2>&1 | tail -5

# Kroki is optional — port 8080 often clashes with other dev stacks
if docker compose up -d kroki 2>&1 | grep -qi "port is already allocated\|bind.*failed"; then
    warn "Kroki :8080 — port already in use by another stack (skipping; diagrams unavailable)"
    docker compose stop kroki >/dev/null 2>&1 || true
elif docker ps --format '{{.Names}}' | grep -q "07_ai_flow_framwork-kroki-1"; then
    ok "Kroki :8080 started"
fi

# Wait for healthy
info "Waiting for PostgreSQL + Redis to become healthy..."
for i in $(seq 1 30); do
    db_ok=$(docker exec 07_ai_flow_framwork-db-1 pg_isready -U aiflow -d aiflow_dev >/dev/null 2>&1 && echo 1 || echo 0)
    redis_ok=$([ "$(docker exec 07_ai_flow_framwork-redis-1 redis-cli ping 2>/dev/null)" = "PONG" ] && echo 1 || echo 0)
    if [ "$db_ok" = "1" ] && [ "$redis_ok" = "1" ]; then
        ok "PostgreSQL + Redis healthy (after ${i}s)"
        break
    fi
    sleep 1
done

##############################################################################
# 4. DB migrations
##############################################################################
info "Running Alembic migrations (upgrade head)..."
PYTHONPATH=src "$PY" -m alembic upgrade head 2>&1 | tail -5
ok "DB migrations applied"

##############################################################################
# 5. Optional: Vault
##############################################################################
if [ "$WITH_VAULT" -eq 1 ]; then
    info "Starting Vault dev container (port 8210)..."
    docker compose -f docker-compose.yml -f docker-compose.vault.yml up -d vault 2>&1 | tail -3
    for i in $(seq 1 20); do
        if curl -sf "http://localhost:8210/v1/sys/health" >/dev/null 2>&1; then
            ok "Vault :8210 ready (root token: aiflow-dev-root)"
            break
        fi
        sleep 1
    done
    if [ -x "$PY" ] && [ -f "scripts/seed_vault_dev.py" ]; then
        info "Seeding Vault dev secrets..."
        "$PY" scripts/seed_vault_dev.py 2>&1 | tail -3 || warn "seed_vault_dev.py reported issues"
    fi
fi

##############################################################################
# 6. Optional: Langfuse
##############################################################################
if [ "$WITH_LANGFUSE" -eq 1 ]; then
    info "Starting self-hosted Langfuse (web :3000, postgres :5434)..."
    docker compose -f docker-compose.langfuse.yml up -d langfuse-postgres langfuse-web 2>&1 | tail -5
    info "Langfuse first-start can take ~30s. Bootstrap project keys: scripts/bootstrap_langfuse.py"
fi

##############################################################################
# 7. Optional: FastAPI on :8102
##############################################################################
if [ "$WITH_API" -eq 1 ]; then
    if [ -f "$LOG_DIR/api.pid" ] && kill -0 "$(cat "$LOG_DIR/api.pid")" 2>/dev/null; then
        warn "FastAPI already running (PID $(cat "$LOG_DIR/api.pid")) — skipping"
    else
        info "Starting FastAPI on :8102 (logs → $LOG_DIR/api.log)..."
        # Disable Langfuse cloud flush hang during dev unless user explicitly enabled it
        ( PYTHONUNBUFFERED=1 PYTHONPATH="src;." "$PY" -u -m uvicorn aiflow.api.app:create_app \
              --factory --port 8102 --host 127.0.0.1 \
              >"$LOG_DIR/api.log" 2>&1 ) &
        echo $! > "$LOG_DIR/api.pid"
        for i in $(seq 1 30); do
            if curl -sf "http://localhost:8102/health" >/dev/null 2>&1; then
                ok "FastAPI :8102 healthy (PID $(cat "$LOG_DIR/api.pid"))"
                break
            fi
            sleep 1
        done
        if ! curl -sf "http://localhost:8102/health" >/dev/null 2>&1; then
            fail "FastAPI failed to become healthy in 30s — see $LOG_DIR/api.log"
        fi
    fi
fi

##############################################################################
# 8. Optional: Vite UI on :5173
##############################################################################
if [ "$WITH_UI" -eq 1 ]; then
    if [ -f "$LOG_DIR/ui.pid" ] && kill -0 "$(cat "$LOG_DIR/ui.pid")" 2>/dev/null; then
        warn "Vite UI already running (PID $(cat "$LOG_DIR/ui.pid")) — skipping"
    else
        info "Starting Vite dev on :5173 (logs → $LOG_DIR/ui.log)..."
        if [ ! -d "aiflow-admin/node_modules" ]; then
            info "node_modules missing — running 'npm install'..."
            ( cd aiflow-admin && npm install --silent 2>&1 | tail -5 )
        fi
        ( cd aiflow-admin && npm run dev >"../$LOG_DIR/ui.log" 2>&1 ) &
        echo $! > "$LOG_DIR/ui.pid"
        for i in $(seq 1 30); do
            if curl -sf "http://localhost:5173/" >/dev/null 2>&1; then
                ok "Vite UI :5173 serving (PID $(cat "$LOG_DIR/ui.pid"))"
                break
            fi
            sleep 1
        done
    fi
fi

##############################################################################
# 9. Final validation table
##############################################################################
echo ""
info "=== Stack health summary ==="
validate_health || true

echo ""
info "Useful URLs:"
echo "  API health:   http://localhost:8102/health"
echo "  API docs:     http://localhost:8102/docs"
echo "  Admin UI:     http://localhost:5173"
[ "$WITH_VAULT" -eq 1 ] && echo "  Vault UI:     http://localhost:8210/ui (token: aiflow-dev-root)"
[ "$WITH_LANGFUSE" -eq 1 ] && echo "  Langfuse:     http://localhost:3000"

echo ""
info "To stop: bash scripts/start_stack.sh --down"
info "Logs:    tail -f $LOG_DIR/{api,ui}.log"
