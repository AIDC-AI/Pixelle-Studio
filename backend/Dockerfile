# backend/Dockerfile
FROM python:3.11-slim

# 1. Configure mirror source for apt-get (optional, comment out if network is good)
# Using Aliyun Debian mirror source
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 2. Install system dependencies and Node.js (backend scripts need node for PPT generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 4. Configure npm mirror source (optional, comment out if network is good)
RUN npm config set registry https://registry.npmmirror.com || true

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

# 9. Expose port
EXPOSE 8001

# 10. Start command
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
