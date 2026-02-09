#!/bin/bash

# Load all environment variables from .env
if [ -f ".env" ]; then
  echo "=== Loading environment variables from .env ==="
  export $(grep -v '^#' .env | xargs)
fi

# Stop current uvicorn process
echo "=== Stopping current uvicorn process ==="
pkill -f "uvicorn app.main:app"
sleep 2

echo ""
echo "=== Starting uvicorn with .venv Python ==="
echo "Python version: $(.venv/bin/python3 --version)"
echo "Python Path: $(.venv/bin/python3 -c 'import sys; print(sys.executable)')"
echo ""

# Start uvicorn using .venv Python
# --reload-dir app only watches app directory, avoiding restarts from scripts directory changes
.venv/bin/python3 -m uvicorn app.main:app --reload --reload-dir app --reload-dir skills --host 0.0.0.0 --port 8001

