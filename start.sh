#!/bin/bash

# ============================================================
# Pixelle-Studio Start Script
# Usage:
#   ./start.sh          Start both frontend & backend (terminal output prefixed with [frontend]/[backend])
#   ./start.sh -f       Start frontend only
#   ./start.sh -b       Start backend only
#   ./start.sh -k       Kill both frontend & backend
#   ./start.sh -kf      Kill frontend only
#   ./start.sh -kb      Kill backend only
#   ./start.sh -d       Start both in background (nohup)
#   ./start.sh -df      Start frontend in background
#   ./start.sh -db      Start backend in background
#   Flags can be combined freely, e.g. -fd, -kfb, -db, etc.
# ============================================================

set -e

# Project root directory (where this script lives)
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_LOG="$ROOT_DIR/frontend.log"
BACKEND_LOG="$ROOT_DIR/backend.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================
# Parse arguments
# ============================================================
FLAG_FRONTEND=false
FLAG_BACKEND=false
FLAG_KILL=false
FLAG_DAEMON=false

while getopts "fbkd" opt; do
    case $opt in
        f) FLAG_FRONTEND=true ;;
        b) FLAG_BACKEND=true ;;
        k) FLAG_KILL=true ;;
        d) FLAG_DAEMON=true ;;
        *) echo "Usage: $0 [-f] [-b] [-k] [-d]"; exit 1 ;;
    esac
done

# If neither -f nor -b is specified, operate on both
if [ "$FLAG_FRONTEND" = false ] && [ "$FLAG_BACKEND" = false ]; then
    FLAG_FRONTEND=true
    FLAG_BACKEND=true
fi

# ============================================================
# Kill functions
# ============================================================
kill_frontend() {
    echo -e "${YELLOW}=== Stopping frontend ===${NC}"
    pkill -f "next dev" 2>/dev/null && echo -e "${GREEN}Frontend process killed${NC}" || echo -e "${CYAN}Frontend not running${NC}"
    pkill -f "next-server" 2>/dev/null || true
    sleep 1
}

kill_backend() {
    echo -e "${YELLOW}=== Stopping backend ===${NC}"
    pkill -f "uvicorn app.main:app" 2>/dev/null && echo -e "${GREEN}Backend process killed${NC}" || echo -e "${CYAN}Backend not running${NC}"
    sleep 1
}

# ============================================================
# Foreground start functions
# ============================================================
start_frontend_foreground() {
    local prefix="$1"
    echo -e "${GREEN}=== Starting frontend ===${NC}"
    echo -e "${CYAN}Log file: $FRONTEND_LOG${NC}"
    cd "$FRONTEND_DIR"
    if [ -n "$prefix" ]; then
        # Prefix mode: prepend [frontend] via sed, tee to log file
        npm run dev 2>&1 | sed -u "s/^/[frontend] /" | tee "$FRONTEND_LOG" &
    else
        # No prefix: just tee to log file
        npm run dev 2>&1 | tee "$FRONTEND_LOG" &
    fi
}

start_backend_foreground() {
    local prefix="$1"
    echo -e "${GREEN}=== Starting backend ===${NC}"
    echo -e "${CYAN}Log file: $BACKEND_LOG${NC}"
    cd "$BACKEND_DIR"

    # Load .env if present
    if [ -f ".env" ]; then
        echo -e "${CYAN}Loading .env variables${NC}"
        export $(grep -v '^#' .env | grep -v '^$' | xargs)
    fi

    if [ -n "$prefix" ]; then
        # Prefix mode: prepend [backend] via sed, tee to log file
        .venv/bin/python3 -m uvicorn app.main:app \
            --reload --reload-dir app --reload-dir skills \
            --reload-exclude "_bootstrap" \
            --host 0.0.0.0 --port 8001 2>&1 | sed -u "s/^/[backend] /" | tee "$BACKEND_LOG" &
    else
        # No prefix: just tee to log file
        .venv/bin/python3 -m uvicorn app.main:app \
            --reload --reload-dir app --reload-dir skills \
            --reload-exclude "_bootstrap" \
            --host 0.0.0.0 --port 8001 2>&1 | tee "$BACKEND_LOG" &
    fi
}

# ============================================================
# Daemon (background) start functions
# ============================================================
start_frontend_daemon() {
    echo -e "${GREEN}=== Starting frontend (daemon) ===${NC}"
    echo -e "${CYAN}Log file: $FRONTEND_LOG${NC}"
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    echo -e "${GREEN}Frontend PID: $!${NC}"
}

start_backend_daemon() {
    echo -e "${GREEN}=== Starting backend (daemon) ===${NC}"
    echo -e "${CYAN}Log file: $BACKEND_LOG${NC}"
    cd "$BACKEND_DIR"

    # Load .env if present
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | grep -v '^$' | xargs)
    fi

    nohup .venv/bin/python3 -m uvicorn app.main:app \
        --reload --reload-dir app --reload-dir skills \
        --reload-exclude "_bootstrap" \
        --host 0.0.0.0 --port 8001 > "$BACKEND_LOG" 2>&1 &
    echo -e "${GREEN}Backend PID: $!${NC}"
}

# ============================================================
# Main logic
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

# Step 3: Start services
if [ "$FLAG_DAEMON" = true ]; then
    # ---- Daemon mode ----
    if [ "$FLAG_FRONTEND" = true ]; then
        start_frontend_daemon
    fi
    if [ "$FLAG_BACKEND" = true ]; then
        start_backend_daemon
    fi
    echo -e "${GREEN}=== Services started in background. Use -k to stop. ===${NC}"
else
    # ---- Foreground mode ----
    # Trap SIGINT/SIGTERM for graceful shutdown
    trap 'echo -e "\n${YELLOW}Stopping all services...${NC}"; kill $(jobs -p) 2>/dev/null; wait; echo -e "${GREEN}All services stopped${NC}"; exit 0' SIGINT SIGTERM

    if [ "$BOTH" = true ]; then
        # Start both with prefix
        start_frontend_foreground "prefix"
        FRONTEND_PID=$!
        start_backend_foreground "prefix"
        BACKEND_PID=$!
        echo ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}  Frontend & Backend started${NC}"
        echo -e "${GREEN}  Frontend: http://localhost:3000${NC}"
        echo -e "${GREEN}  Backend:  http://localhost:8001${NC}"
        echo -e "${GREEN}  Press Ctrl+C to stop all${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo ""
    else
        if [ "$FLAG_FRONTEND" = true ]; then
            start_frontend_foreground ""
            FRONTEND_PID=$!
            echo -e "${GREEN}Frontend: http://localhost:3000  |  Press Ctrl+C to stop${NC}"
        fi
        if [ "$FLAG_BACKEND" = true ]; then
            start_backend_foreground ""
            BACKEND_PID=$!
            echo -e "${GREEN}Backend: http://localhost:8001  |  Press Ctrl+C to stop${NC}"
        fi
    fi

    # Wait for all background child processes
    wait
fi
