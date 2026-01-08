# backend/Dockerfile
FROM python:3.11-slim

# 1. 配置国内镜像源加速 apt-get（可选，如果网络好可以注释掉）
# 使用阿里云 Debian 镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 2. 安装系统依赖和 Node.js (因为你的后端脚本需要 node 环境生成 PPT)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. 安装 uv 包管理器
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 4. 配置 npm 使用国内镜像源（可选，如果网络好可以注释掉）
RUN npm config set registry https://registry.npmmirror.com || true

# 5. 复制依赖文件并安装 Python 依赖
# 使用 --frozen 确保严格按照 lock 文件安装
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 6. 复制后端 Node 依赖 (用于 pptx 脚本) 并安装
COPY package.json package-lock.json* ./
RUN npm install --prefer-offline --no-audit

# 7. 复制源代码
COPY . .

# 8. 安装项目本身
RUN uv sync --frozen --no-dev

# 9. 暴露端口
EXPOSE 8001

# 10. 启动命令
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

