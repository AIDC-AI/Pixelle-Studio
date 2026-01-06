# 产品诉求
手工实现的skills client，可以实现对skills的渐进式加载、脚本的生成和执行、是以agentic agent的方式来实现的。

# 技术架构

本系统采用单 Agent 架构（`SkillAgent`），围绕“渐进式技能加载”和“沙箱代码执行”两大核心能力构建。系统通过 FastAPI 提供 RESTful API 和 WebSocket 接口，与前端进行交互。

## 核心模块分解

### 1. Agent Core (`backend/app/agent.py`)
这是系统的大脑，负责维护对话状态并驱动执行循环。
*   **SkillAgent**: 核心类，维护 `history_messages` 和 `loaded_skills`。
*   **Agent Loop**: 采用 "Think-Act-Observe" 循环。
    *   **Think**: 构建包含 System Prompt（含 Skills XML 定义）、历史消息和用户输入的 Prompt，调用 LLM。
    *   **Act**: 解析 LLM 的响应，识别 Action：
        *   `[LOAD_SKILL: name]`: 加载技能文档。
        *   `[READ_SKILL_FILE: name, path]`: 读取技能的具体文件。
        *   `[LIST_SKILL_TREE: name]`: 查看技能目录结构。
        *   ` ```python ... ``` `: 生成并请求执行代码。
        *   直接回复: 结束当前 Turn。
    *   **Observe**: 执行 Action 并获取结果（如技能内容、文件内容、代码执行结果），将结果回填到对话历史中，继续下一轮 Loop。
*   **Session Management**: 基于 SQLite 持久化会话（Session）、轮次（Turn）和步骤（Step），支持历史回溯和状态恢复。

### 2. Skills System (`backend/app/skills/loader.py`)
系统的“图书馆管理员”，实现了 **Progressive Disclosure（渐进式披露）** 机制，避免一次性将所有技能上下文填入 Context Window。
*   **Level 1 (Metadata)**: 扫描 `skills/` 目录，提取 `SKILL.md` 的 Frontmatter（名称、描述）。仅将这些摘要信息放入 System Prompt。
*   **Level 2 (Documentation)**: 当 Agent 决定 `[LOAD_SKILL]` 时，加载完整的 `SKILL.md` 内容。
*   **Level 3 (Files)**: 当 Agent 需要更细节的代码片段或模板时，通过 `[READ_SKILL_FILE]` 读取技能目录下的具体文件（如 `.py` 脚本, `.json` 模版）。
*   **Skill Context Injection**: 加载的技能内容会被动态注入到 System Prompt 的 `<loaded_skills_context>` 中。

### 3. Execution Environment (`backend/app/execution/runner.py`)
负责安全地运行 Agent 生成的代码。
*   **Code Runner**: 在独立的子进程中执行 Python 脚本。
*   **Helper Injection**: 在执行环境中自动注入辅助函数，打通代码与 Skills 资源的路径：
    *   `skill_path(skill_name, ...)`: 定位技能目录下的资源。
    *   `script_path(...)`: 定位用户工作区的文件。
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
      Loop:
      1. Build Prompt (Sys + Hist)
      2. Call LLM
      3. Parse Action
      4. Execute Action
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
Agent --> Loader : [LOAD_SKILL]\n[READ_SKILL_FILE]
Loader --> Repo : Read content
Agent --> Runner : Execute Python
Agent --> MCP : Call Tools
MCP <--> MCPS : JSON-RPC
Runner --> WorkDir : R/W Files
Runner --> Repo : Read Helpers
Runner --> Agent : Result/Stdout

@enduml
```
