# MCP Workflow Demo - README

## 项目概述

这是一个基于 **OpenAI Agents SDK + Skills + MCP Tools** 架构的智能工作流系统。系统采用单 Agent 架构，通过标准的 Tool Calling 机制实现多轮对话和代码执行。

### 核心特性

- **标准 Tool Calling**: 使用 OpenAI Agents SDK 的 `@function_tool` 装饰器定义工具，符合 OpenAI 规范
- **渐进式技能加载**: Skills 系统支持按需加载领域知识，避免 Context Window 溢出
- **流式输出**: 使用 `Runner.run_streamed()` 实现实时流式响应
- **代码沙箱执行**: 安全执行 Agent 生成的 Python 代码
- **MCP 工具集成**: 支持连接外部 MCP 服务器调用工具

## 架构设计

### 架构演进

```
v1.0 (旧架构): LLM Response → 正则解析 [LOAD_SKILL:] / ```python``` → 手动分发执行
v2.0 (新架构): LLM with tools → tool_calls 字段 → 自动执行 → tool message → LLM 继续
```

### 核心流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  WebSocket  │────▶│ SkillAgent  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          ▼                          │
                    │              ┌─────────────────────┐                │
                    │              │  OpenAI Agents SDK  │                │
                    │              │  Runner.run_streamed │                │
                    │              └──────────┬──────────┘                │
                    │                         │                           │
                    │         ┌───────────────┼───────────────┐           │
                    │         ▼               ▼               ▼           │
                    │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
                    │  │ load_skill │  │execute_code│  │list_mcp_   │    │
                    │  │            │  │            │  │   tools    │    │
                    │  └────────────┘  └────────────┘  └────────────┘    │
                    │                                                     │
                    │                    5 Tools                          │
                    └─────────────────────────────────────────────────────┘
```

### 后端 (Python + FastAPI + OpenAI Agents SDK)

- **端口**: 8001
- **核心模块**:
  - `app/agent.py` - SkillAgent 使用 OpenAI Agents SDK
  - `app/tools.py` - 5 个 `@function_tool` 定义
  - `app/skills/loader.py` - 渐进式技能加载器
  - `app/execution/runner.py` - 代码沙箱执行引擎
  - `app/mcp_client.py` - MCP 工具客户端

### 前端 (React + TypeScript + Next.js + Tailwind)

- **端口**: 3000
- **核心功能**:
  - 聊天界面支持 Tool Call 可视化
  - 技能管理侧边栏
  - 实时流式响应显示
  - 代码执行结果展示

## Tool Calling 系统

### 5 个核心 Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `load_skill` | 加载技能文档 (SKILL.md) | `skill_name: str` |
| `read_skill_file` | 读取技能目录下的文件 | `skill_name: str, file_path: str` |
| `list_skill_tree` | 列出技能目录结构 | `skill_name: str` |
| `execute_code` | 执行 Python 代码 | `code: str` |
| `list_mcp_tools` | 发现可用 MCP 工具 | 无 |

### Tool 定义示例

```python
from agents import function_tool, RunContextWrapper

@function_tool
async def load_skill(ctx: RunContextWrapper[AgentContext], skill_name: str) -> str:
    """Load skill documentation (SKILL.md) for domain-specific guidance."""
    context = ctx.context
    skill_content = context.skill_loader.read_skill(skill_name, context.user_id)
    return skill_content or f"Skill '{skill_name}' not found"
```

### Agent 执行流程

```python
from agents import Agent, Runner

agent = Agent(
    name="SkillAgent",
    instructions=system_prompt,
    tools=[load_skill, read_skill_file, list_skill_tree, execute_code, list_mcp_tools],
    model="gpt-4o",
)

# 流式执行
result = Runner.run_streamed(agent, input=messages, context=agent_context)

async for event in result.stream_events():
    # 处理 tool_call, tool_result, response 等事件
    yield convert_event(event)
```

## Skills 系统

### 渐进式加载机制

1. **Level 1 (Metadata)**: 扫描 `skills/` 目录，提取 SKILL.md 的 Frontmatter
2. **Level 2 (Documentation)**: Agent 调用 `load_skill` 加载完整文档
3. **Level 3 (Files)**: Agent 调用 `read_skill_file` 读取具体文件

### 技能目录结构

```
skills/
├── default/           # 默认技能
│   ├── xlsx/
│   │   ├── SKILL.md
│   │   └── recalc.py
│   ├── pptx/
│   │   ├── SKILL.md
│   │   ├── html2pptx.md
│   │   └── scripts/
│   └── ...
└── <user_id>/         # 用户自定义技能
    └── ...
```

## 快速开始

### 1. 环境配置

```bash
# 设置环境变量
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
export LLM_MODEL="gpt-4o"  # 可选，默认 gpt-4o
```

### 2. 启动后端

```bash
cd backend
uv sync  # 首次运行安装依赖
./start_server.sh
```

### 3. 启动前端

```bash
cd frontend
npm install  # 首次运行
npm run dev
```

### 4. 访问应用

打开浏览器访问: http://localhost:3000

## 项目结构

```
mcp-workflow/
├── backend/
│   ├── app/
│   │   ├── agent.py           # SkillAgent (OpenAI Agents SDK)
│   │   ├── tools.py           # 5 个 @function_tool 定义
│   │   ├── main.py            # FastAPI 主应用
│   │   ├── mcp_client.py      # MCP 工具客户端
│   │   ├── skills/
│   │   │   └── loader.py      # 渐进式技能加载器
│   │   └── execution/
│   │       └── runner.py      # 代码沙箱执行引擎
│   ├── skills/                # 技能库
│   │   └── default/
│   │       ├── xlsx/
│   │       ├── pptx/
│   │       └── ...
│   └── scripts/               # 生成的脚本和用户文件
├── frontend/
│   ├── components/
│   │   └── layout/
│   │       └── chat/
│   │           ├── index.tsx       # 主聊天组件
│   │           ├── messageList.tsx # 消息列表
│   │           └── items/
│   │               ├── toolCallItem.tsx    # Tool 调用展示
│   │               ├── toolResultItem.tsx  # Tool 结果展示
│   │               └── ...
│   └── types/
│       └── message.tsx        # 消息类型定义
└── files/
    └── Requirement_Spec.md    # 技术规格文档
```

## 技术栈

**后端**:
- Python 3.10+
- FastAPI - Web 框架
- OpenAI Agents SDK - Agent 框架
- Uvicorn - ASGI 服务器
- WebSockets - 实时通信
- SQLAlchemy - 数据库 ORM

**前端**:
- React 19 + TypeScript 5.3
- Next.js 15
- Tailwind CSS
- Ant Design

## WebSocket 事件类型

| 事件类型 | 说明 |
|---------|------|
| `status` | Agent 状态更新 |
| `tool_call` | Tool 调用开始 |
| `tool_result` | Tool 执行完成 |
| `code` | 代码生成 |
| `execution_result` | 代码执行结果 |
| `response` | Agent 文本响应 |
| `skill_loaded` | 技能加载完成 |
| `final_result` | 最终结果 |
| `error` | 错误信息 |

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | 必填 |
| `OPENAI_BASE_URL` | API Base URL | https://api.openai.com/v1 |
| `LLM_MODEL` | 使用的模型 | gpt-4o |
| `LLM_BASE_URL` | LLM Base URL (备用) | - |
| `LLM_API_KEY` | LLM API Key (备用) | - |

## 参考资料

- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## License

Apache-2.0
