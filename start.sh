#!/bin/bash

# 遇到错误立即退出
set -e

echo "=== MCP Workflow 服务启动 ==="

# 1. 检查必要工具
if ! command -v docker &> /dev/null; then
    echo "错误: 未找到 docker 命令"
    exit 1
fi

# 自动检测 docker-compose 命令
if command -v docker-compose &> /dev/null; then
    DC_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DC_CMD="docker compose"
else
    echo "错误: 未找到 docker-compose 或 docker compose 命令"
    exit 1
fi

# 2. 准备目录
echo "正在创建必要目录..."
mkdir -p backend/logs backend/scripts backend/storage/contexts backend/storage/files

# 3. 清理旧进程 (端口 3000 和 8001)
echo "检查并清理旧进程..."
for port in 3000 8001; do
    # 查找占用端口的 PID
    pids=$(lsof -ti :$port 2>/dev/null || true)
    if [ ! -z "$pids" ]; then
        echo "清理端口 $port 的进程: $pids"
        kill -9 $pids 2>/dev/null || true
    fi
done

# 4. 停止旧容器
echo "停止旧的 Docker 服务..."
$DC_CMD down --remove-orphans 2>/dev/null || true

# 5. 启动服务
echo "构建并启动服务..."
# 增加 --build 确保代码变更生效
$DC_CMD up -d --build

# 6. 显示状态
echo "=== 服务已启动 ==="
$DC_CMD ps

echo ""
echo "前端地址: http://localhost:3000"
echo "后端地址: http://localhost:8001"
echo "查看日志: $DC_CMD logs -f"
