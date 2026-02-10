#!/bin/bash

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
# Docker mode (-D):
#   ./start.sh -D       Build & start both via docker compose (foreground)
#   ./start.sh -Dd      Build & start both via docker compose (detached)
#   ./start.sh -Df      Build & start frontend container only
#   ./start.sh -Db      Build & start backend container only
#   ./start.sh -Dk      Stop & remove containers
#   ./start.sh -Dkf     Stop frontend container only
#   ./start.sh -Dkb     Stop backend container only
#
# Flags can be combined freely, e.g. -fd, -kfb, -pdb, -Ddf, etc.
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

# Docker compose project name
COMPOSE_PROJECT="${COMPOSE_PROJECT:-pixelle}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================
# Parse arguments
# ============================================================
FLAG_FRONTEND=false
FLAG_BACKEND=false
FLAG_KILL=false
FLAG_DAEMON=false
FLAG_PROD=false
FLAG_DOCKER=false

while getopts "fbkdpD" opt; do
    case $opt in
        f) FLAG_FRONTEND=true ;;
        b) FLAG_BACKEND=true ;;
        k) FLAG_KILL=true ;;
        d) FLAG_DAEMON=true ;;
        p) FLAG_PROD=true ;;
        D) FLAG_DOCKER=true ;;
        *) echo "Usage: $0 [-f] [-b] [-k] [-d] [-p] [-D]"; exit 1 ;;
    esac
done

# If neither -f nor -b is specified, operate on both
if [ "$FLAG_FRONTEND" = false ] && [ "$FLAG_BACKEND" = false ]; then
    FLAG_FRONTEND=true
    FLAG_BACKEND=true
fi

# ============================================================
# Docker mode
# ============================================================
if [ "$FLAG_DOCKER" = true ]; then
    echo -e "${BLUE}========== DOCKER MODE ==========${NC}"
    cd "$ROOT_DIR"

    # Check docker compose is available
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: docker is not installed${NC}"
        exit 1
    fi

    # Determine which services to operate on
    SERVICES=""
    [ "$FLAG_FRONTEND" = true ] && SERVICES="$SERVICES frontend"
    [ "$FLAG_BACKEND" = true ]  && SERVICES="$SERVICES backend"

    if [ "$FLAG_KILL" = true ]; then
        # ---- Docker kill/stop ----
        echo -e "${YELLOW}=== Stopping Docker containers ===${NC}"
        if [ "$FLAG_FRONTEND" = true ] && [ "$FLAG_BACKEND" = true ]; then
            docker compose -p "$COMPOSE_PROJECT" down
        else
            docker compose -p "$COMPOSE_PROJECT" stop $SERVICES
            docker compose -p "$COMPOSE_PROJECT" rm -f $SERVICES
        fi
        echo -e "${GREEN}=== Docker containers stopped ===${NC}"
        exit 0
    fi

    # ---- Docker build & start ----
    echo -e "${BLUE}=== Building & starting Docker containers ===${NC}"
    echo -e "${CYAN}Services: $SERVICES${NC}"

    if [ "$FLAG_DAEMON" = true ]; then
        # Detached mode
        docker compose -p "$COMPOSE_PROJECT" up --build -d $SERVICES
        echo ""
        echo -e "${BLUE}============================================${NC}"
        echo -e "${BLUE}  Docker services started (detached)${NC}"
        [ "$FLAG_FRONTEND" = true ] && echo -e "${BLUE}  Frontend: http://localhost:${FRONTEND_PORT}${NC}"
        [ "$FLAG_BACKEND" = true ]  && echo -e "${BLUE}  Backend:  http://localhost:${BACKEND_PORT}${NC}"
        echo -e "${BLUE}  Stop with: ./start.sh -Dk${NC}"
        echo -e "${BLUE}  Logs:      docker compose -p $COMPOSE_PROJECT logs -f${NC}"
        echo -e "${BLUE}============================================${NC}"
    else
        # Foreground mode (docker compose up with --build, shows logs)
        echo ""
        echo -e "${BLUE}============================================${NC}"
        echo -e "${BLUE}  Building & starting Docker containers${NC}"
        [ "$FLAG_FRONTEND" = true ] && echo -e "${BLUE}  Frontend: http://localhost:${FRONTEND_PORT}${NC}"
        [ "$FLAG_BACKEND" = true ]  && echo -e "${BLUE}  Backend:  http://localhost:${BACKEND_PORT}${NC}"
        echo -e "${BLUE}  Press Ctrl+C to stop${NC}"
        echo -e "${BLUE}============================================${NC}"
        echo ""
        docker compose -p "$COMPOSE_PROJECT" up --build $SERVICES
    fi
    exit 0
fi

# ============================================================
# Non-Docker modes below (dev / production)
# ============================================================

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
# Load backend .env helper
# ============================================================
load_backend_env() {
    cd "$BACKEND_DIR"
    if [ -f ".env" ]; then
        echo -e "${CYAN}Loading .env variables${NC}"
        export $(grep -v '^#' .env | grep -v '^$' | xargs)
    fi
}

# ============================================================
# Dev mode start functions
# ============================================================
start_frontend_dev_fg() {
    local prefix="$1"
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
    echo -e "${GREEN}=== Starting frontend (dev, daemon) ===${NC}"
    echo -e "${CYAN}Log file: $FRONTEND_LOG${NC}"
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    echo -e "${GREEN}Frontend PID: $!${NC}"
}

start_backend_dev_daemon() {
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
    build_frontend
    echo -e "${GREEN}=== Starting frontend (production, daemon) ===${NC}"
    echo -e "${CYAN}Log file: $FRONTEND_LOG${NC}"
    cd "$FRONTEND_DIR"
    nohup npm run start -- -p "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
    echo -e "${GREEN}Frontend PID: $!${NC}"
}

start_backend_prod_daemon() {
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
