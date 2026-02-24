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
# --reload-exclude "_bootstrap" prevents reload when exec creates mcp_bootstrap.py
.venv/bin/python3 -m uvicorn app.main:app --reload --reload-dir app --reload-dir skills --reload-exclude "_bootstrap" --host 0.0.0.0 --port 8001

