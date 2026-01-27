# 产品诉求
手工实现的skills client，可以实现对skills的渐进式加载、脚本的生成和执行、是以agentic agent的方式来实现的。

# 技术架构

本系统采用单 Agent 架构（`SkillAgent`），围绕“渐进式技能加载”和“沙箱代码执行”两大核心能力构建。系统通过 FastAPI 提供 RESTful API 和 WebSocket 接口，与前端进行交互。

## 核心模块分解

### 1. Agent Core (`backend/app/agent.py`)
这是系统的大脑，负责维护对话状态并驱动执行循环。

*   **SkillAgent**: 核心类，基于 OpenAI Agents SDK 构建，维护 `history_messages` 和 `AgentContext`。
*   **Agent Loop**: 基于 **Tool Calling** 机制的流式执行循环（摒弃了正则匹配方案）。
    *   **Tool Calling 机制**: 通过 OpenAI Agents SDK 的原生 Tool Calling 能力调用以下工具：
        *   `load_skill(skill_name)`: 加载技能文档。
        *   `read_skill_file(skill_name, path)`: 读取技能的具体文件。
        *   `list_skill_tree(skill_name)`: 查看技能目录结构。
        *   `execute_code()`: 执行 Python 代码（详见下方 Execute 块机制）。
        *   `list_mcp_tools()`: 列出可用的 MCP 工具。
    *   **Execute 块机制（核心设计）**: 
        *   **背景问题**: `execute_code` 如果通过 tool call 参数传入代码，无法处理长代码片段（参数长度受限，且影响 token 效率）。
        *   **解决方案**: LLM 在响应正文中使用 `<execute lang="python">...</execute>` 标签包裹代码，与 tool call 分离。
        *   **执行流程**: 
            1. Agent 流式接收 LLM 响应时，`_extract_execute_blocks()` 实时解析并提取代码块。
            2. 提取的代码块被加入 `AgentContext.pending_code_queue` 队列。
            3. LLM 调用 `execute_code()` 工具时（**无需传参**），工具从队列中取出最新代码块执行。
        *   **输出清理**: `_clean_response_text()` 从最终响应中移除 `<execute>` 块，保持用户可读性。
    *   **结构化返回**: 工具返回 JSON 格式数据（包含 `__tool__` 字段标识工具类型），无需正则解析结果。
*   **Session Management**: 基于 SQLite 持久化会话（Session）、轮次（Turn）和步骤（Step），支持历史回溯和状态恢复。

### 2. Skills System (`backend/app/skills/loader.py`)
系统的“图书馆管理员”，实现了 **Progressive Disclosure（渐进式披露）** 机制，避免一次性将所有技能上下文填入 Context Window。
*   **Level 1 (Metadata)**: 扫描 `skills/` 目录，提取 `SKILL.md` 的 Frontmatter（名称、描述）。仅将这些摘要信息放入 System Prompt。
*   **Level 2 (Documentation)**: 当 Agent 调用 `load_skill()` 工具时，加载完整的 `SKILL.md` 内容。
*   **Level 3 (Files)**: 当 Agent 需要更细节的代码片段或模板时，通过 `read_skill_file()` 工具读取技能目录下的具体文件（如 `.py` 脚本, `.json` 模版）。
*   **Skill Context Injection**: 加载的技能内容会被动态注入到 System Prompt 的 `<loaded_skills_context>` 中。

### 3. Execution Environment (`backend/app/execution/runner.py`)
负责安全地运行 Agent 生成的代码。
*   **Code Runner**: 在独立的子进程中执行 Python 脚本。
*   **Helper Injection**: 在执行环境中自动注入辅助函数，打通代码与 Skills 资源的路径：
    *   `skill_path(skill_name, ...)`: 定位技能目录下的资源。
    *   `user_file(...)`: 定位用户工作区的文件（上传的输入和生成的输出）。
    *   `call_tool(name, args)`: 异步调用外部 MCP 工具。
*   **Workspace**: 代码运行在 `backend/` 根目录，但主要读写操作被引导至 `scripts/` 目录。

### 4. MCP Client & Aggregator (`backend/app/mcp_client.py`)
负责连接和管理外部 MCP (Model Context Protocol) 服务器。
*   **MCP Aggregator**: 聚合多个 MCP Server 的工具。
*   **Tool Registration**: 动态注册和发现工具。
*   **Transport**: 支持 SSE 和 Stdio 等多种传输协议。

### 5. API Layer (`backend/app/main.py` & `backend/app/routes/`)
对外暴露的接口层。
*   **Websocket (`/ws/chat/{chat_id}`)**: 实时推送 Agent 的思考过程、状态更新和执行结果。
*   **REST API**:
    *   `mcp_servers`: 管理 MCP 服务器配置。
    *   `users`: 用户认证和管理。
    *   `skills`: 技能的增删改查。
    *   `upload`: 文件上传处理。

## 架构图

```plantUML
@startuml
skinparam componentStyle uml2
skinparam backgroundColor white

package "Frontend" {
  [React/Next.js App] as UI
}

package "Backend Services" {
  
  package "API Layer" {
    [FastAPI Router] as API
    [WebSocket Handler] as WS
  }

  package "Agent Core" {
    [SkillAgent] as Agent
    note right of Agent
      Tool Calling Loop:
      1. Build Prompt (Sys + Hist)
      2. Call LLM (Streaming)
      3. Extract <execute> blocks
      4. Handle Tool Calls
    end note
    
    [Session Manager] as Session
  }
  
  package "Skills System" {
    [SkillLoader] as Loader
    note bottom of Loader
      Progressive Disclosure:
      L1: Metadata (Scan)
      L2: Full Doc (Load)
      L3: Files (Read)
    end note
    
    database "Skills Repository" as Repo {
        folder "skills/" {
            [pptx/SKILL.md]
            [xlsx/SKILL.md]
            [...scripts & docs]
        }
    }
  }

  package "Execution Environment" {
    [Code Runner] as Runner
    folder "scripts/" as WorkDir {
        [User Files]
        [Generated Scripts]
        [Output Files]
    }
  }

  package "External Integrations" {
    [MCP Client] as MCP
  }
}

cloud "LLM Provider" as LLM {
  [Claude / GPT-4]
}

cloud "MCP Servers" as MCPS {
  [Brave Search]
  [Filesystem]
}

UI <--> API : REST
UI <--> WS : Real-time Events
WS --> Agent : User Message
Agent --> Session : Persist State
Agent <--> LLM : Completion
Agent --> Loader : load_skill()\nread_skill_file()
Loader --> Repo : Read content
Agent --> Runner : execute_code()\n+ <execute> blocks
Agent --> MCP : Call Tools
MCP <--> MCPS : JSON-RPC
Runner --> WorkDir : R/W Files
Runner --> Repo : Read Helpers
Runner --> Agent : Result/Stdout

@enduml
```
