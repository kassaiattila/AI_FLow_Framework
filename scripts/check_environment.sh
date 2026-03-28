#!/bin/bash
# AIFlow Development Environment Check
# Usage: bash scripts/check_environment.sh

echo "=== AIFlow Development Environment Check ==="
echo ""

errors=0

check_cmd() {
    if command -v "$1" &> /dev/null; then
        version=$(eval "$2" 2>&1 | head -1)
        echo "  [OK]   $1: $version"
    else
        echo "  [FAIL] $1: NOT FOUND - $3"
        errors=$((errors + 1))
    fi
}

echo "Required tools:"
check_cmd "python" "python --version" "Install Python 3.12+ from python.org"
check_cmd "uv" "uv --version" "Install: pip install uv"
check_cmd "git" "git --version" "Install: git-scm.com"
check_cmd "docker" "docker --version" "Install: Docker Desktop"
check_cmd "make" "make --version" "Install: winget install GnuWin32.Make (Windows)"

echo ""
echo "Optional tools:"
check_cmd "node" "node --version" "Needed for Promptfoo tests"

echo ""
echo "Project files:"

if [ -d ".venv" ]; then
    echo "  [OK]   .venv/ exists"
else
    echo "  [WARN] .venv/ missing (run: make setup)"
fi

if [ -f ".env" ]; then
    echo "  [OK]   .env exists"
else
    echo "  [WARN] .env missing (run: cp .env.example .env)"
fi

if [ -f "uv.lock" ]; then
    echo "  [OK]   uv.lock exists"
else
    echo "  [WARN] uv.lock missing (run: make lock)"
fi

echo ""
echo "Docker services:"
if docker compose ps --status running 2>/dev/null | grep -q "db"; then
    echo "  [OK]   PostgreSQL running"
else
    echo "  [INFO] PostgreSQL not running (run: make dev)"
fi

if docker compose ps --status running 2>/dev/null | grep -q "redis"; then
    echo "  [OK]   Redis running"
else
    echo "  [INFO] Redis not running (run: make dev)"
fi

echo ""
if [ $errors -eq 0 ]; then
    echo "=== ALL REQUIRED TOOLS FOUND ==="
    exit 0
else
    echo "=== $errors REQUIRED TOOL(S) MISSING ==="
    exit 1
fi
