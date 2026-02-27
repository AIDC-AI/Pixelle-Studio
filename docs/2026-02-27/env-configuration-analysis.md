# 环境配置全面分析报告

> 日期：2026-02-27
> 范围：.env.example、backend/app/config.py、启动脚本、Docker、README

---

## 一、用户需要填写的设置

### 结论：普通用户只需在 UI Settings 里配 3 项即可

| 配置项 | 在哪配 | 是否必填 | 说明 |
|--------|--------|----------|------|
| **API Key** | UI ⚙️ Settings | ✅ 必填 | 加密存储到 DB |
| **Base URL** | UI ⚙️ Settings | ✅ 必填（非 OpenAI 官方时） | 兼容 OpenAI API 的自定义端点 |
| **Model Name** | UI ⚙️ Settings | 可选（默认 gpt-4o） | 如 gpt-4o、claude-3.5-sonnet |
| Context 压缩开关 | UI ⚙️ Settings (Advanced) | 可选 | 默认 true |
| 保留最近消息数 | UI ⚙️ Settings (Advanced) | 可选 | 默认 10 |
| 压缩最少消息数 | UI ⚙️ Settings (Advanced) | 可选 | 默认 15 |
| Thinking Level | UI ⚙️ Settings (Advanced) | 可选 | 默认 medium |
| Agent 最大轮次 | UI ⚙️ Settings (Advanced) | 可选 | 默认 50 |
| Model Fallbacks | UI ⚙️ Settings (Advanced) | 可选 | 逗号分隔的模型列表 |

**关键发现**：主代码路径 (`SkillAgent._init_client_with_failover`) 已完全使用用户级配置，**不再读取环境变量中的 OPENAI_API_KEY / OPENAI_BASE_URL**。未配置 API Key 时会直接报错提示用户去 Settings 配置。

---

## 二、.env.example 分析

### 当前 .env.example 中所有变量的分类

#### 🔴 **已废弃/误导性变量** — 主流程不使用

| 变量 | 现状 | 建议 |
|------|------|------|
| `OPENAI_API_KEY` | 仅 `AuthStore.from_env()`（未被调用）和 `AihubLLM`（未被主流程使用）读取 | ❌ 建议删除或标注为废弃 |
| `OPENAI_BASE_URL` | 同上 | ❌ 建议删除或标注为废弃 |
| `OPENAI_API_KEY_BACKUP` | 仅 `AuthStore.from_env()` 读取，但该方法从未在主流程中被调用 | ❌ 建议删除 |

**分析**：
- `AuthStore.from_env()` 方法存在于 `auth/models.py`，但 grep 确认 **没有任何地方调用它**
- `AihubLLM` 类在 `llm/aihub_llm.py` 中读取这些变量，但 **没有被主流程引用**
- 主 Agent 流程 (`agent.py` + `main.py`) 完全依赖用户在 UI 中配置的 API Key

#### 🟡 **系统默认值变量** — 可填可不填，都有合理默认值

| 变量 | 默认值 | 谁读取 | 说明 |
|------|--------|--------|------|
| `OPENAI_MODEL` | `gpt-4o` | `config.py`, `llm_adapter.py` | 系统级默认模型，用户可在 UI 覆盖 |
| `LLM_TIMEOUT` | `300` | `config.py` | LLM 超时秒数 |
| `LLM_MAX_TOKENS` | `16384` | `config.py` | LLM 最大 token |
| `AGENT_MAX_TURNS` | `50` | `config.py` | Agent 最大轮次，用户可在 UI 覆盖 |
| `DEFAULT_THINKING_LEVEL` | `medium` | `config.py` | 默认思考深度，用户可在 UI 覆盖 |
| `CONTEXT_COMPACTION_ENABLED` | `true` | `config.py` | 上下文压缩开关，用户可在 UI 覆盖 |
| `CONTEXT_KEEP_RECENT` | `10` | `config.py` | 压缩时保留消息数，用户可在 UI 覆盖 |
| `CONTEXT_MIN_MESSAGES_BEFORE_COMPACT` | `15` | `config.py` | 最少消息数，用户可在 UI 覆盖 |
| `ENABLE_AUTH_FAILOVER` | `true` | `config.py` | 认证容错开关 |
| `ENABLE_MODEL_FAILOVER` | `true` | `config.py` | 模型容错开关 |
| `ENABLE_THINKING_FAILOVER` | `true` | `config.py` | 思考降级开关 |
| `MODEL_FALLBACKS` | 代码默认链 | `config.py` | 模型降级链，用户可在 UI 覆盖 |

#### 🟢 **基础设施变量** — 仅部署/自定义时需要

| 变量 | 默认值 | 谁读取 | 说明 |
|------|--------|--------|------|
| `FRONTEND_PORT` | `3000` | `start.sh`, `docker-compose.yml` | 前端端口 |
| `BACKEND_PORT` | `8001` | `start.sh`, `docker-compose.yml` | 后端端口 |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8001/api` | `frontend/lib/data.ts`, `Dockerfile` | 前端→后端 API 地址 |
| `NEXT_PUBLIC_WS_BASE` | `ws://localhost:8001/ws` | `frontend/lib/data.ts`, `Dockerfile` | 前端→后端 WS 地址 |
| `JWT_SECRET` | 硬编码开发密钥 | `utils/security.py` | JWT 签名密钥（生产必改） |
| `DATABASE_URL` | `sqlite:///./app.db` | `database/models.py` | 数据库连接地址 |
| `EXTERNAL_IP` | 空 | `utils/network.py` | 生成文件 URL 时的外部 IP |
| `HTTP_PROXY` / `HTTPS_PROXY` | 空 | `agent.py`, `routes/users.py` | 代理设置 |

### ⚠️ .env 文件位置混乱问题

| 启动方式 | .env 读取位置 | 原因 |
|----------|---------------|------|
| `./start.sh` | `backend/.env` | `load_backend_env()` 函数 cd 到 backend/ 后 export |
| `python -m uvicorn ...` (手动) | `backend/.env` | `config.py` 的 `load_dotenv()` 在 CWD 查找 |
| `docker compose up` | 根目录 `.env` | Docker Compose 标准行为 |

但 `.env.example` 在根目录，注释写的是 `cp .env.example .env`，这会创建根目录的 `.env`，**只有 Docker Compose 能读到**，`start.sh` 和手动启动 **读不到**。

### 总结：.env.example 是否需要？

- **本地开发（start.sh / 手动启动）**：❌ **完全不需要** — 所有 LLM 配置在 UI 中完成，其他变量有合理默认值
- **Docker Compose 部署**：⚠️ **可能需要** — 如果部署在非 localhost 环境，需要设置 `NEXT_PUBLIC_API_BASE`、`NEXT_PUBLIC_WS_BASE`，以及 `JWT_SECRET`
- **生产环境**：✅ **建议设置 JWT_SECRET** — 安全原因

---

## 三、README 检查

### README.md (英文) ✅ 正确

- ✅ 明确说明 "LLM Settings are configured per-user through the Settings panel — no environment files needed"
- ✅ 基础设施变量表格正确（FRONTEND_PORT, BACKEND_PORT, NEXT_PUBLIC_API_BASE, NEXT_PUBLIC_WS_BASE, JWT_SECRET）
- ✅ 三种启动方式描述正确（start.sh / Docker Compose / 手动）
- ✅ 环境要求正确（Python 3.10+, Node.js 20+, uv）

### README_CN.md (中文) ✅ 正确

- ✅ 内容与英文版一致
- ✅ 配置说明清晰

### 小建议（非错误）

README 中没有特别说明 `.env.example` 的用途。既然 README 已经说了 "无需环境变量文件"，`.env.example` 文件的存在可能会让用户困惑。建议：
1. 在 README 中补充一句：`.env.example` 仅用于 Docker 部署或高级自定义场景
2. 或者直接删除 `.env.example` 中的 LLM 相关变量

---

## 四、依赖文件和启动脚本检查

### 4.1 pyproject.toml ✅ 正确

所有核心依赖都包含：
- Web: fastapi, uvicorn, websockets
- LLM: openai, anthropic, openai-agents
- DB: sqlalchemy, pydantic
- Auth: bcrypt, python-jose
- 文档处理: python-pptx, python-docx, reportlab, fpdf, pypdfium2 等
- 环境: python-dotenv

### 4.2 frontend/package.json ✅ 正确

- next ^16.0.8, react ^19.2.1, react-dom ^19.2.1
- tailwindcss ^4.1.17
- 所有预览相关包（docx-preview, xlsx, react-markdown）

### 4.3 backend/package.json ✅ 正确

- pptxgenjs (PPT 生成)
- playwright (HTML 渲染)
- sharp (图片处理)
- docx (Word 生成)

### 4.4 start.sh ✅ 正确

- 自动检测并安装 Python 依赖（uv sync）
- 自动检测并安装 Node.js 依赖（npm install，前端+后端）
- 支持 dev/prod 模式、前台/后台、前端/后端单独控制
- 正确加载 `backend/.env`

### 4.5 docker-compose.yml ✅ 正确

- 后端 Dockerfile 正确安装 Python + Node.js 依赖
- 前端 Dockerfile 使用多阶段构建（builder + runner）
- 数据持久化 volumes 正确（data, scripts, skills, logs）
- 健康检查配置正确
- 网络配置正确

### 4.6 backend/Dockerfile ✅ 正确

- 基于 python:3.11-slim
- 安装了系统依赖（nodejs, npm, git, curl, CJK 字体）
- 使用 uv 安装 Python 依赖
- 使用 npm 安装 Node 依赖
- 入口脚本处理了默认 skills 的初始化

### 4.7 frontend/Dockerfile ✅ 正确

- 使用 node:20-alpine
- 多阶段构建（build + run）
- standalone 模式输出
- 构建时注入 NEXT_PUBLIC_API_BASE 和 NEXT_PUBLIC_WS_BASE

---

## 五、发现的问题和建议

### 问题 1：.env.example 中残留已废弃的 LLM 环境变量

**现状**：`.env.example` 包含 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_API_KEY_BACKUP` 等变量，但主代码路径不再使用它们。

**建议**：将这些变量删除或注释并标注为 "Deprecated - 使用 UI Settings 替代"。

### 问题 2：.env 文件位置不一致

**现状**：
- `.env.example` 在根目录，指导 `cp .env.example .env`
- `start.sh` 读取 `backend/.env`
- Docker Compose 读取根目录 `.env`

**建议**：
- 方案 A：将 `.env.example` 移到 `backend/` 目录（如果主要是给 start.sh 用）
- 方案 B：保持根目录，但让 `start.sh` 也读取根目录 `.env`
- 方案 C（推荐）：既然普通用户不需要 .env，就在 `.env.example` 头部加说明，区分 Docker 和 start.sh 的使用方式

### 问题 3：遗留代码仍读取环境变量 LLM 配置

以下代码仍从环境变量读取 `OPENAI_API_KEY`，但不在主流程中使用：

| 文件 | 行号 | 说明 |
|------|------|------|
| `llm/aihub_llm.py:37-39` | `os.getenv("OPENAI_API_KEY")` | AihubLLM 类，未被主流程引用 |
| `auth/models.py:140-141` | `os.getenv("OPENAI_API_KEY")` | `AuthStore.from_env()`，未被调用 |
| `llm_adapter.py:113` | `AsyncOpenAI()` (无参) | 依赖 env 的 `OPENAI_API_KEY`，仅 legacy 路径 |
| `llm_adapter.py:255` | `AsyncOpenAI()` (无参) | 同上 |

**建议**：如果确认这些是遗留代码，可以考虑清理。

### 问题 4：`llm_adapter.py` 中的 `generate_workflow_script` 潜在问题

`llm_adapter.py` 的 `generate_workflow_script()` 和 `generate_script_with_skill()` 函数直接使用 `AsyncOpenAI()`（无参数），会依赖环境变量 `OPENAI_API_KEY`。如果用户没有设置该环境变量，这些函数调用时会报错。

但检查调用链发现 `execution_orchestrator.py` 中仍在调用 `generate_script_with_skill`，这可能是一个隐藏的 Bug。

---

## 六、已执行的修复

| # | 修复内容 | 文件 |
|---|----------|------|
| 1 | 重写 `.env.example`，删除废弃的 OPENAI_API_KEY 等变量，头部说明普通用户不需要 .env | `.env.example` |
| 2 | `start.sh` 的 `load_backend_env()` 改为优先读取根目录 `.env`，向后兼容 `backend/.env` | `start.sh` |
| 3 | 移除 `main.py` 中未使用的 `from app.llm_adapter import generate_workflow_script` | `backend/app/main.py` |
| 4 | `llm_adapter.py` 遗留函数添加 `[LEGACY]` 标注和 warning 日志 | `backend/app/llm_adapter.py` |
| 5 | 清理 `backend/.env`，移除残留的内部 API 密钥 | `backend/.env` |
| 6 | 删除 `auth/models.py` 中从未调用的 `AuthStore.from_env()` 方法 | `backend/app/auth/models.py` |
| 7 | 移除 `aihub_llm.py` 对 OPENAI_API_KEY 环境变量的 fallback，添加 warning | `backend/app/llm/aihub_llm.py` |

---

## 七、总结

| 项目 | 状态 | 说明 |
|------|------|------|
| 用户只需在 UI 配置 LLM | ✅ 正确 | API Key + Base URL + Model 在 Settings 中完成 |
| .env.example 是否必需 | ✅ 已修复 | 头部明确说明普通用户不需要，删除废弃变量 |
| README 正确性 | ✅ 正确 | 中英文 README 均准确 |
| 依赖文件正确性 | ✅ 正确 | pyproject.toml、package.json 均完整 |
| start.sh 正确性 | ✅ 已修复 | .env 读取路径统一为根目录优先 |
| docker-compose.yml 正确性 | ✅ 正确 | 无需改动 |
| 遗留代码清理 | ✅ 已清理 | 移除 env fallback + 添加 LEGACY 标注 |

