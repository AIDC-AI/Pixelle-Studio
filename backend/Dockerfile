# backend/Dockerfile
FROM python:3.11-slim

# 2. Install system dependencies and Node.js (backend scripts need node for PPT generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    git \
    curl \
    # CJK fonts for Chinese/Japanese/Korean text rendering in PDFs and PPTs
    fonts-noto-cjk \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# 3. Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 5. Copy dependency files and install Python dependencies
# Use --frozen to ensure strict installation from lock file
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 6. Copy backend Node dependencies (for pptx scripts) and install
COPY package.json package-lock.json* ./
RUN npm install --prefer-offline --no-audit

# 7. Copy source code
COPY . .

# 8. Install the project itself
RUN uv sync --frozen --no-dev

# 9. Create data directories for volume mounts
RUN mkdir -p /app/data /app/scripts /app/skills /app/logs

# 10. Copy default skills to a backup location (for first-run initialization)
RUN if [ -d /app/skills/default ]; then cp -r /app/skills/default /app/skills_default_backup; fi

# 11. Add entrypoint script
COPY <<'ENTRYPOINT_SCRIPT' /app/entrypoint.sh
#!/bin/bash
set -e

# Initialize default skills if the skills volume is empty
if [ -d /app/skills_default_backup ] && [ ! -d /app/skills/default ]; then
    echo "[Entrypoint] Initializing default skills..."
    cp -r /app/skills_default_backup /app/skills/default
fi

# Start the application
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
ENTRYPOINT_SCRIPT
RUN chmod +x /app/entrypoint.sh

# 12. Expose port
EXPOSE 8001

# 13. Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

# 14. Start command
CMD ["/app/entrypoint.sh"]
