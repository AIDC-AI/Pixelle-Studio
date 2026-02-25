<p align="center">
  <img src="frontend/public/logo.png" alt="Pixelle Studio" width="400">
</p>

<p align="center">
  <strong>🚀 用自然语言驱动一切 —— 您的 AI 智能工作台</strong>
</p>

<p align="center">
  <a href="https://github.com/AIDC-AI/Pixelle-Studio"><img src="https://img.shields.io/github/stars/AIDC-AI/Pixelle-Studio?style=social" alt="GitHub Stars"></a>
  <a href="https://github.com/AIDC-AI/Pixelle-Studio/blob/main/LICENSE"><img src="https://img.shields.io/github/license/AIDC-AI/Pixelle-Studio" alt="License"></a>
  <a href="https://github.com/AIDC-AI/Pixelle-Studio"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
  <a href="https://github.com/AIDC-AI/Pixelle-Studio"><img src="https://img.shields.io/badge/Next.js-16-black.svg" alt="Next.js"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>中文</strong>
</p>

---

**Pixelle Studio** 是一个开源的 AI Agent 智能工作台。只需用自然语言描述你的需求，Agent 就能自动调用工具、执行代码、生成文档，帮你完成从数据分析到旅行规划的各种复杂任务。

> 💡 **不只是聊天机器人** —— 它能真正地思考、执行、创造。

<p align="center">
  <img src="assets/main.png" alt="Pixelle Studio 主界面" width="100%">
</p>

---

## ✨ 核心亮点

<table>
<tr>
<td width="33%" align="center">
<h3>📄 全格式文档处理</h3>
<p>PDF、Excel、PPT、Word、Markdown、HTML<br>—— 智能生成 & 实时预览</p>
</td>
<td width="33%" align="center">
<h3>🧠 自定义技能系统</h3>
<p>将你的 SOP / 经验封装成 Skill<br>大幅提升任务成功率</p>
</td>
<td width="33%" align="center">
<h3>🔌 MCP 外部工具集成</h3>
<p>一键接入搜索引擎、地图、视频等<br>外部能力，拓展 Agent 边界</p>
</td>
</tr>
</table>

### 🎯 为什么选择 Pixelle Studio？

| 特性 | 传统 AI 聊天工具 | Pixelle Studio |
|------|:---:|:---:|
| 文档生成 (PDF/PPT/Excel) | ❌ 仅生成文本 | ✅ 直接生成文件并预览 |
| 代码执行 | ❌ 或需要插件 | ✅ 内置持久化终端，多步执行 |
| 自定义技能 | ❌ | ✅ 将 SOP 封装为可执行 Skill |
| 外部工具 (MCP) | ❌ 封闭生态 | ✅ 开放协议，按需接入 |
| 上下文管理 | ❌ 被动截断 | ✅ 智能压缩，自动管理 |
| 多模型容错 | ❌ 单模型 | ✅ 三层 Failover 机制 |
| Token 消耗 | 🔴 全量加载 | 🟢 渐进式按需加载 |

---

## 🖼️ 使用案例

### 1️⃣ 自驾行程规划

> 💬 *"我想从杭州自驾到北京，请你帮我规划一下行程，我想要2月26日出发。"*

Agent 自动加载地图技能 → 调用高德/Bing 地图 API → 规划路线 → 生成行程文档

<p align="center">
  <img src="assets/杭州到北京自驾1.png" alt="自驾行程规划" width="100%">
  <img src="assets/杭州到北京自驾2.png" alt="自驾行程规划" width="100%">
</p>

支持中英文双语：同样的自然语言体验，对英文用户同样友好 👇

<p align="center">
  <img src="assets/from Seattle Airport to Mount Rainier.png" alt="Seattle to Mount Rainier" width="100%">
</p>

### 2️⃣ 深度研究 + PPT 生成

> 💬 *"请帮我做一个关于郑州美食和好玩的地方的深度研究，结果用 PPT 呈现。"*

Agent 自动组合多个 Skill → 网络搜索 → 内容抓取 → 结构化分析 → 自动生成 PPT

<p align="center">
  <img src="assets/deep-research with ppt generation.png" alt="深度研究 + PPT 生成" width="100%">
</p>

### 3️⃣ HTML 小游戏 & 互动内容

> 💬 *"帮我写一个贪吃蛇小游戏"*

Agent 直接编写 HTML/CSS/JS → 生成可运行的游戏文件 → 内置预览实时体验

<p align="center">
  <img src="assets/files-html.png" alt="HTML 小游戏" width="100%">
</p>

### 4️⃣ 自定义你自己的 Skill

不只是使用预置技能 —— 你可以创建自己的 Skill，让 Agent 掌握你特有的工作流：

<p align="center">
  <img src="assets/skill-edit.png" alt="技能编辑" width="100%">
</p>

---

## 🏗️ 架构设计

```
                          ┌──────────────────────────┐
                          │     Frontend (Next.js)    │
                          │  Chat + Skills + Preview  │
                          └────────────┬─────────────┘
                                       │ WebSocket
                          ┌────────────▼─────────────┐
                          │    Backend (FastAPI)       │
                          │      SkillAgent Core       │
                          └────────────┬─────────────┘
                                       │
             ┌────────────┬────────────┼────────────┬────────────┐
             ▼            ▼            ▼            ▼            ▼
      ┌────────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐
      │  9 内置工具 ││ PTY 终端  ││ 技能系统  ││ MCP 工具 ││ 上下文    │
      │ read/write ││持久化会话 ││ 渐进加载  ││ 外部集成 ││ 智能管理  │
      │ exec/shell ││变量保持   ││ 按需发现  ││ 搜索/地图 ││ 自动压缩  │
      └────────────┘└──────────┘└──────────┘└──────────┘└──────────┘
```

### 技术深潜

<details>
<summary><b>🔋 渐进式技能加载 — Token 节约的秘密武器</b></summary>

<br>

不同于传统方案将所有 Skill 一股脑塞进 System Prompt，我们采用 **三级渐进式加载**：

| 层级 | 内容 | Token 消耗 | 加载时机 |
|------|------|-----------|---------|
| Level 1 | Skill 元数据 (名称+描述) | ~50 tokens/skill | 每次对话 |
| Level 2 | 完整 SKILL.md 文档 | ~500-2000 tokens | Agent 按需加载 |
| Level 3 | 辅助文件 (脚本/参考) | 按需 | Agent 按需加载 |

**效果**：12 个预置 Skill 仅消耗 ~600 tokens 元数据，传统方案可能需要 20,000+ tokens。

</details>

<details>
<summary><b>🖥️ 持久化伪终端 (PTY) — 不只是执行代码</b></summary>

<br>

基于 `pexpect` 实现的持久化 Shell Session，不同于一次性代码执行：

```python
# 变量在多次调用间保持！
shell_exec("import pandas as pd", shell_type="python")
shell_exec("df = pd.DataFrame({'a': [1,2,3]})", shell_type="python")
shell_exec("print(df.describe())", shell_type="python")  # df 仍然存在！
```

**优势**：
- ✅ 变量持久化 — 跨调用保持状态
- ✅ 多语言支持 — Bash / Python / IPython
- ✅ 错误自恢复 — 会话崩溃自动重启
- ✅ 自动清理 — 空闲超时自动回收

</details>

<details>
<summary><b>🛡️ 三层容错机制 — 永不中断的服务</b></summary>

<br>

```
请求失败？
  ├─ 第 1 层: Auth Failover    → 切换 API Key / Base URL
  ├─ 第 2 层: Model Failover   → 切换备用模型 (gpt-4o → gpt-4o-mini → ...)
  └─ 第 3 层: Thinking Failover → 降级思维深度
```

即使主模型遇到限流/超时/配额耗尽，系统也能自动切换备用方案，确保任务不中断。

</details>

<details>
<summary><b>📐 智能上下文管理 — 永远不会溢出</b></summary>

<br>

- **Context Window Guard** — 实时监控 token 使用率，预警阈值自动触发
- **Auto-Compaction** — 当上下文接近 70% 使用率时，自动生成摘要压缩历史消息
- **多模型适配** — 自动识别模型上下文窗口大小 (GPT-4o 128K / Claude 200K / Gemini 1M)

</details>

---

## 🔌 MCP 外部工具集成

通过 [Model Context Protocol](https://modelcontextprotocol.io/) 开放标准，轻松接入外部工具：

<p align="center">
  <img src="assets/mcp-add.png" alt="MCP 配置" width="100%">
</p>

**预置 Skill 已支持的 MCP 工具**：

| 工具 | 功能 | 使用场景 |
|------|------|---------|
| 🔍 Exa Search | AI 原生搜索引擎 | 深度研究、信息收集 |
| 🔍 Bing Search | 通用网络搜索 | 实时信息查询 |
| 🗺️ 高德地图 | 路线规划、POI搜索 | 旅行规划 |
| 🌐 Web Fetch | 网页内容抓取 | 数据采集 |
| 🎬 社交媒体视频 | 视频内容解析 | 内容创作 |

> 你还可以接入任何兼容 MCP 协议的工具服务！

---

## 🚀 快速开始

### 环境要求

- **Python 3.10+** 以及 [uv](https://docs.astral.sh/uv/getting-started/installation/)（Python 包管理器）
- **Node.js 20+** 以及 npm
- **Docker & Docker Compose**（可选，用于容器化部署）

### 方式一：一键启动

```bash
# 1. 克隆项目
git clone https://github.com/AIDC-AI/Pixelle-Studio.git
cd Pixelle-Studio

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的 API Key：
# OPENAI_API_KEY=your-api-key

# 3. 一键启动（首次运行会自动安装依赖）
./start.sh
```

### 方式二：Docker Compose 部署（推荐用于生产环境）

```bash
# 1. 克隆项目
git clone https://github.com/AIDC-AI/Pixelle-Studio.git
cd Pixelle-Studio

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key：
# OPENAI_API_KEY=your-api-key

# 3. 构建并启动所有服务
docker compose up -d

# 4. 查看日志（可选）
docker compose logs -f
```

启动后访问 👉 **http://localhost:3000**

<details>
<summary><b>📦 Docker Compose 常用命令</b></summary>

<br>

```bash
docker compose up -d            # 后台启动所有服务
docker compose up               # 前台启动（直接查看日志）
docker compose down             # 停止所有服务
docker compose logs -f          # 查看所有日志
docker compose logs -f backend  # 仅查看后端日志
docker compose up --build       # 重新构建镜像并启动
docker compose ps               # 查看运行中的服务状态
```

**数据持久化**：以下数据通过 Docker Volume 持久化存储：
- `backend-data` — SQLite 数据库
- `backend-scripts` — 生成的文件（PDF/PPT/Excel/HTML 等）
- `backend-skills` — 用户自定义技能
- `backend-logs` — 应用日志

清除所有数据：`docker compose down -v`

</details>

### 方式三：分步启动

```bash
# 后端
cd backend
uv sync              # 安装 Python 依赖（自动创建 .venv）
npm install          # 安装 Node.js 依赖（用于 PPT/文档生成技能）
cp .env.example .env  # 配置环境变量
.venv/bin/python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# 前端（新终端）
cd frontend
npm install           # 安装 Node.js 依赖
npm run dev           # 启动开发服务器（端口 3000）
```

启动后访问 👉 **http://localhost:3000**

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | 必填 |
| `OPENAI_BASE_URL` | API 地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 使用的模型 | `gpt-4o` |
| `FRONTEND_PORT` | 前端端口 | `3000` |
| `BACKEND_PORT` | 后端端口 | `8001` |
| `NEXT_PUBLIC_API_BASE` | 前端连接后端 API 地址 | `http://localhost:8001/api` |
| `NEXT_PUBLIC_WS_BASE` | 前端连接后端 WebSocket 地址 | `ws://localhost:8001/ws` |
| `JWT_SECRET` | JWT 签名密钥 | 自动生成 |

> 💡 完整的可配置环境变量列表请参考 `.env.example` 文件。

---

## 🛠️ 内置工具一览

Pixelle Studio 为 Agent 提供了 **9 个开箱即用的工具**：

| 工具 | 功能 | 说明 |
|------|------|------|
| `shell_exec` | 持久化终端 | 变量保持的多步执行 |
| `exec` | 命令执行 | 一次性命令 / 后台任务 |
| `read_file` | 读取文件 | 支持技能文件和用户文件 |
| `write_file` | 写入文件 | 创建脚本 / 配置文件 |
| `edit_file` | 编辑文件 | 精确字符串替换 |
| `grep` | 搜索内容 | 支持正则表达式 |
| `find` | 查找文件 | 支持 glob 模式 |
| `ls` | 列出目录 | 智能限制，防溢出 |
| `process` | 进程管理 | 后台任务的查看/终止 |

---

## 📁 项目结构

```
Pixelle-Studio/
├── frontend/                  # 前端 (Next.js 16 + React 19)
│   ├── app/                   # App Router 页面
│   ├── components/            # UI 组件
│   │   ├── layout/chat/       # 聊天界面
│   │   ├── layout/leftPanel/  # 侧边栏 (会话 + 技能)
│   │   └── ui/                # 通用 UI 组件
│   ├── hooks/                 # React Hooks
│   ├── lib/                   # API 客户端
│   ├── types/                 # TypeScript 类型定义
│   └── Dockerfile             # 前端容器镜像
│
├── backend/                   # 后端 (Python + FastAPI)
│   ├── app/
│   │   ├── agent.py           # SkillAgent 核心引擎
│   │   ├── tools/             # 9 大内置工具
│   │   ├── context/           # 上下文管理 (Guard + Compaction)
│   │   ├── skills/            # 技能加载器
│   │   ├── config/            # 容错配置
│   │   └── routes/            # REST API 路由
│   ├── skills/                # 技能库
│   │   ├── default/           # 预置技能 (PDF/PPT/Excel/搜索...)
│   │   └── <user_id>/         # 用户自定义技能
│   ├── scripts/               # 生成的文件存储
│   └── Dockerfile             # 后端容器镜像
│
├── docker-compose.yml         # Docker Compose 编排配置
├── .env.example               # 环境变量模板
├── assets/                    # README 素材
└── start.sh                   # 一键启动脚本
```

---

## 🧰 技术栈

**后端**：Python 3.10+ · FastAPI · OpenAI API · WebSocket · SQLAlchemy · pexpect

**前端**：Next.js 16 · React 19 · TypeScript · Tailwind CSS

**基础设施**：SQLite · MCP Protocol · Docker Compose

---

## 🤝 贡献

我们欢迎所有形式的贡献！无论是 Bug 报告、功能建议，还是代码提交。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

---

## 📄 License

本项目采用 [Apache License 2.0](LICENSE) 开源。

---

<p align="center">
  <b>⭐ 如果这个项目对你有帮助，请给我们一个 Star！</b>
</p>

<p align="center">
  <a href="https://github.com/AIDC-AI/Pixelle-Studio">GitHub</a> ·
  <a href="https://github.com/AIDC-AI/Pixelle-Studio/issues">报告问题</a> ·
  <a href="https://github.com/AIDC-AI/Pixelle-Studio/issues">功能建议</a>
</p>
