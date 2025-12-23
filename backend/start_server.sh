#!/bin/bash

# 停止当前 uvicorn 进程（使用系统 Python）
echo "=== 停止当前 uvicorn 进程 ==="
pkill -f "uvicorn app.main:app"
sleep 2

echo ""
echo "=== 使用 .venv 中的 Python 启动 uvicorn ==="
echo "Python 版本: $(.venv/bin/python3 --version)"
echo "Python 路径: $(.venv/bin/python3 -c 'import sys; print(sys.executable)')"
echo ""

# 使用 .venv 中的 Python 启动 uvicorn
# --reload-exclude scripts 排除脚本目录，防止生成脚本时触发服务器重启
.venv/bin/python3 -m uvicorn app.main:app --reload --reload-exclude scripts --host 0.0.0.0 --port 8001

