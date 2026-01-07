# backend/Dockerfile
FROM python:3.11-slim

# 1. 安装系统依赖和 Node.js (因为你的后端脚本需要 node 环境生成 PPT)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 uv 包管理器
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 3. 复制依赖文件并安装 Python 依赖
# 使用 --frozen 确保严格按照 lock 文件安装
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 4. 复制后端 Node 依赖 (用于 pptx 脚本) 并安装
COPY package.json package-lock.json* ./
RUN npm install

# 5. 复制源代码
COPY . .

# 6. 安装项目本身
RUN uv sync --frozen --no-dev

# 7. 暴露端口
EXPOSE 8001

# 8. 启动命令
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

