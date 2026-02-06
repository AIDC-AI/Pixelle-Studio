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


# 加载 .env 配置的所有环境变量
if [ -f ".env" ]; then
  echo "=== 加载 .env 文件中的环境变量 ==="
  export $(grep -v '^#' .env | xargs)
fi

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
# --reload-dir app 只监视 app 目录，避免 scripts 目录变化触发重启
.venv/bin/python3 -m uvicorn app.main:app --reload --reload-dir app --reload-dir skills --host 0.0.0.0 --port 8001

