#!/bin/bash
# Copyright (C) 2026 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# ============================================================
# Pixelle-Studio Start Script
#
# Dev mode (default):
#   ./start.sh          Start both frontend & backend (prefixed with [frontend]/[backend])
#   ./start.sh -f       Start frontend only
#   ./start.sh -b       Start backend only
#   ./start.sh -k       Kill both frontend & backend
#   ./start.sh -kf      Kill frontend only
#   ./start.sh -kb      Kill backend only
#   ./start.sh -d       Start both in background (nohup)
#   ./start.sh -df      Start frontend in background
#   ./start.sh -db      Start backend in background
#
# Production mode (-p):
#   ./start.sh -p       Start both in production (build frontend first, uvicorn with workers)
#   ./start.sh -pf      Start frontend in production only
#   ./start.sh -pb      Start backend in production only
#   ./start.sh -pd      Start both in production, background
#   ./start.sh -pk      Kill production services
#
# Flags can be combined freely, e.g. -fd, -kfb, -pdb, etc.
# ============================================================

set -e

# Project root directory (where this script lives)
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_LOG="$ROOT_DIR/frontend.log"
BACKEND_LOG="$ROOT_DIR/backend.log"

# Production defaults
PROD_WORKERS="${PROD_WORKERS:-4}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-8001}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ============================================================
# Parse arguments
# ============================================================
FLAG_FRONTEND=false
FLAG_BACKEND=false
FLAG_KILL=false
FLAG_DAEMON=false
FLAG_PROD=false

while getopts "fbkdp" opt; do
    case $opt in
        f) FLAG_FRONTEND=true ;;
        b) FLAG_BACKEND=true ;;
        k) FLAG_KILL=true ;;
        d) FLAG_DAEMON=true ;;
        p) FLAG_PROD=true ;;
        *) echo "Usage: $0 [-f] [-b] [-k] [-d] [-p]"; exit 1 ;;
    esac
done

# If neither -f nor -b is specified, operate on both
if [ "$FLAG_FRONTEND" = false ] && [ "$FLAG_BACKEND" = false ]; then
    FLAG_FRONTEND=true
    FLAG_BACKEND=true
fi

# Show mode banner
if [ "$FLAG_PROD" = true ]; then
    echo -e "${MAGENTA}========== PRODUCTION MODE ==========${NC}"
else
    echo -e "${CYAN}========== DEVELOPMENT MODE ==========${NC}"
fi

# ============================================================
# Kill functions
# ============================================================
kill_frontend() {
    echo -e "${YELLOW}=== Stopping frontend ===${NC}"
    if [ "$FLAG_PROD" = true ]; then
        # Production: kill "next start" and standalone server.js
        pkill -f "next start" 2>/dev/null && echo -e "${GREEN}Frontend (prod) process killed${NC}" || true
        pkill -f "node.*server.js" 2>/dev/null || true
    else
        # Dev: kill "next dev"
        pkill -f "next dev" 2>/dev/null && echo -e "${GREEN}Frontend (dev) process killed${NC}" || true
    fi
    pkill -f "next-server" 2>/dev/null || true
    echo -e "${CYAN}Frontend stopped${NC}"
    sleep 1
}

kill_backend() {
    echo -e "${YELLOW}=== Stopping backend ===${NC}"
    pkill -f "uvicorn app.main:app" 2>/dev/null && echo -e "${GREEN}Backend process killed${NC}" || echo -e "${CYAN}Backend not running${NC}"
    sleep 1
}

# ============================================================
# Load .env helper
# Priority: root .env > backend/.env (for backward compatibility)
# ============================================================
load_backend_env() {
    if [ -f "$ROOT_DIR/.env" ]; then
        echo -e "${CYAN}Loading .env from project root${NC}"
        export $(grep -v '^#' "$ROOT_DIR/.env" | grep -v '^$' | xargs)
    elif [ -f "$BACKEND_DIR/.env" ]; then
        echo -e "${CYAN}Loading .env from backend/${NC}"
        export $(grep -v '^#' "$BACKEND_DIR/.env" | grep -v '^$' | xargs)
    fi
}

# ============================================================
# Dependency check & install
# ============================================================
ensure_backend_deps() {
    cd "$BACKEND_DIR"

    # 1. Python dependencies (via uv)
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}=== Backend .venv not found, creating virtual environment ===${NC}"
        if ! command -v uv &> /dev/null; then
            echo -e "${RED}Error: 'uv' is not installed. Install it first: https://docs.astral.sh/uv/getting-started/installation/${NC}"
            exit 1
        fi
        uv sync
        echo -e "${GREEN}Backend Python dependencies installed${NC}"
    fi

    # 2. Node.js dependencies (for PPT/document generation skills)
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}=== Backend node_modules not found, installing Node.js dependencies ===${NC}"
        if ! command -v node &> /dev/null; then
            echo -e "${RED}Warning: Node.js is not installed. PPT generation skills will not work.${NC}"
            echo -e "${RED}Install Node.js 20+: https://nodejs.org/${NC}"
        else
            npm install
            echo -e "${GREEN}Backend Node.js dependencies installed (pptxgenjs, playwright, sharp, etc.)${NC}"
        fi
    fi
}

ensure_frontend_deps() {
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}=== Frontend node_modules not found, installing dependencies ===${NC}"
        npm install
        echo -e "${GREEN}Frontend dependencies installed${NC}"
    fi
}

# ============================================================
# Dev mode start functions
# ============================================================
start_frontend_dev_fg() {
    local prefix="$1"
    ensure_frontend_deps
    echo -e "${GREEN}=== Starting frontend (dev) ===${NC}"
    echo -e "${CYAN}Log file: $FRONTEND_LOG${NC}"
    cd "$FRONTEND_DIR"
    if [ -n "$prefix" ]; then
        npm run dev 2>&1 | sed -u "s/^/[frontend] /" | tee "$FRONTEND_LOG" &
    else
        npm run dev 2>&1 | tee "$FRONTEND_LOG" &
    fi
}

start_backend_dev_fg() {
    local prefix="$1"
    ensure_backend_deps
    echo -e "${GREEN}=== Starting backend (dev) ===${NC}"
    echo -e "${CYAN}Log file: $BACKEND_LOG${NC}"
    load_backend_env

    local cmd=".venv/bin/python3 -m uvicorn app.main:app --reload --reload-dir app --reload-dir skills --reload-exclude _bootstrap --host 0.0.0.0 --port $BACKEND_PORT"
    if [ -n "$prefix" ]; then
        $cmd 2>&1 | sed -u "s/^/[backend] /" | tee "$BACKEND_LOG" &
    else
        $cmd 2>&1 | tee "$BACKEND_LOG" &
    fi
}

start_frontend_dev_daemon() {
    ensure_frontend_deps
    echo -e "${GREEN}=== Starting frontend (dev, daemon) ===${NC}"
    echo -e "${CYAN}Log file: $FRONTEND_LOG${NC}"
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    echo -e "${GREEN}Frontend PID: $!${NC}"
}

start_backend_dev_daemon() {
    ensure_backend_deps
    echo -e "${GREEN}=== Starting backend (dev, daemon) ===${NC}"
    echo -e "${CYAN}Log file: $BACKEND_LOG${NC}"
    load_backend_env

    nohup .venv/bin/python3 -m uvicorn app.main:app \
        --reload --reload-dir app --reload-dir skills \
        --reload-exclude "_bootstrap" \
        --host 0.0.0.0 --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 &
    echo -e "${GREEN}Backend PID: $!${NC}"
}

# ============================================================
# Production mode start functions
# ============================================================
build_frontend() {
    echo -e "${MAGENTA}=== Building frontend for production ===${NC}"
    cd "$FRONTEND_DIR"
    npm run build
    echo -e "${GREEN}Frontend build completed${NC}"
}

start_frontend_prod_fg() {
    local prefix="$1"
    ensure_frontend_deps
    build_frontend
    echo -e "${GREEN}=== Starting frontend (production) ===${NC}"
    echo -e "${CYAN}Log file: $FRONTEND_LOG${NC}"
    cd "$FRONTEND_DIR"
    if [ -n "$prefix" ]; then
        npm run start -- -p "$FRONTEND_PORT" 2>&1 | sed -u "s/^/[frontend] /" | tee "$FRONTEND_LOG" &
    else
        npm run start -- -p "$FRONTEND_PORT" 2>&1 | tee "$FRONTEND_LOG" &
    fi
}

start_backend_prod_fg() {
    local prefix="$1"
    ensure_backend_deps
    echo -e "${GREEN}=== Starting backend (production) ===${NC}"
    echo -e "${CYAN}Log file: $BACKEND_LOG${NC}"
    echo -e "${CYAN}Workers: $PROD_WORKERS${NC}"
    load_backend_env

    local cmd=".venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --workers $PROD_WORKERS"
    if [ -n "$prefix" ]; then
        $cmd 2>&1 | sed -u "s/^/[backend] /" | tee "$BACKEND_LOG" &
    else
        $cmd 2>&1 | tee "$BACKEND_LOG" &
    fi
}

start_frontend_prod_daemon() {
    ensure_frontend_deps
    build_frontend
    echo -e "${GREEN}=== Starting frontend (production, daemon) ===${NC}"
    echo -e "${CYAN}Log file: $FRONTEND_LOG${NC}"
    cd "$FRONTEND_DIR"
    nohup npm run start -- -p "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
    echo -e "${GREEN}Frontend PID: $!${NC}"
}

start_backend_prod_daemon() {
    ensure_backend_deps
    echo -e "${GREEN}=== Starting backend (production, daemon) ===${NC}"
    echo -e "${CYAN}Log file: $BACKEND_LOG${NC}"
    echo -e "${CYAN}Workers: $PROD_WORKERS${NC}"
    load_backend_env

    nohup .venv/bin/python3 -m uvicorn app.main:app \
        --host 0.0.0.0 --port "$BACKEND_PORT" \
        --workers "$PROD_WORKERS" > "$BACKEND_LOG" 2>&1 &
    echo -e "${GREEN}Backend PID: $!${NC}"
}

# ============================================================
# Main logic (dev / production)
# ============================================================

# Step 1: Kill targeted services first
if [ "$FLAG_FRONTEND" = true ]; then
    kill_frontend
fi
if [ "$FLAG_BACKEND" = true ]; then
    kill_backend
fi

# If kill-only mode, exit here
if [ "$FLAG_KILL" = true ]; then
    echo -e "${GREEN}=== Done ===${NC}"
    exit 0
fi

# Step 2: Determine if both services are starting (to decide on prefix)
BOTH=false
if [ "$FLAG_FRONTEND" = true ] && [ "$FLAG_BACKEND" = true ]; then
    BOTH=true
fi

# Step 3: Choose start functions based on mode
if [ "$FLAG_PROD" = true ]; then
    # ==================== Production mode ====================
    if [ "$FLAG_DAEMON" = true ]; then
        # ---- Production + Daemon ----
        if [ "$FLAG_FRONTEND" = true ]; then
            start_frontend_prod_daemon
        fi
        if [ "$FLAG_BACKEND" = true ]; then
            start_backend_prod_daemon
        fi
        echo -e "${GREEN}=== Production services started in background. Use -pk to stop. ===${NC}"
    else
        # ---- Production + Foreground ----
        trap 'echo -e "\n${YELLOW}Stopping all services...${NC}"; kill $(jobs -p) 2>/dev/null; wait; echo -e "${GREEN}All services stopped${NC}"; exit 0' SIGINT SIGTERM

        if [ "$BOTH" = true ]; then
            start_frontend_prod_fg "prefix"
            start_backend_prod_fg "prefix"
        else
            [ "$FLAG_FRONTEND" = true ] && start_frontend_prod_fg ""
            [ "$FLAG_BACKEND" = true ] && start_backend_prod_fg ""
        fi

        echo ""
        echo -e "${MAGENTA}============================================${NC}"
        echo -e "${MAGENTA}  PRODUCTION services running${NC}"
        [ "$FLAG_FRONTEND" = true ] && echo -e "${MAGENTA}  Frontend: http://localhost:${FRONTEND_PORT}${NC}"
        [ "$FLAG_BACKEND" = true ]  && echo -e "${MAGENTA}  Backend:  http://localhost:${BACKEND_PORT}  (workers: ${PROD_WORKERS})${NC}"
        echo -e "${MAGENTA}  Press Ctrl+C to stop all${NC}"
        echo -e "${MAGENTA}============================================${NC}"
        echo ""
        wait
    fi
else
    # ==================== Development mode ====================
    if [ "$FLAG_DAEMON" = true ]; then
        # ---- Dev + Daemon ----
        if [ "$FLAG_FRONTEND" = true ]; then
            start_frontend_dev_daemon
        fi
        if [ "$FLAG_BACKEND" = true ]; then
            start_backend_dev_daemon
        fi
        echo -e "${GREEN}=== Services started in background. Use -k to stop. ===${NC}"
    else
        # ---- Dev + Foreground ----
        trap 'echo -e "\n${YELLOW}Stopping all services...${NC}"; kill $(jobs -p) 2>/dev/null; wait; echo -e "${GREEN}All services stopped${NC}"; exit 0' SIGINT SIGTERM

        if [ "$BOTH" = true ]; then
            start_frontend_dev_fg "prefix"
            start_backend_dev_fg "prefix"
        else
            [ "$FLAG_FRONTEND" = true ] && start_frontend_dev_fg ""
            [ "$FLAG_BACKEND" = true ] && start_backend_dev_fg ""
        fi

        echo ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}  DEV services running${NC}"
        [ "$FLAG_FRONTEND" = true ] && echo -e "${GREEN}  Frontend: http://localhost:${FRONTEND_PORT}${NC}"
        [ "$FLAG_BACKEND" = true ]  && echo -e "${GREEN}  Backend:  http://localhost:${BACKEND_PORT}${NC}"
        echo -e "${GREEN}  Press Ctrl+C to stop all${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo ""
        wait
    fi
fi
