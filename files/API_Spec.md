# API Specification

后端服务基于 FastAPI 构建，提供 RESTful API 和 WebSocket 接口。
Base URL: `http://localhost:8001` (默认)

## 1. Chat & Agent Interaction

### 创建对话会话
初始化一个新的对话 Session 或在现有 Session 下开启新的 Turn。

*   **Endpoint**: `POST /api/chat`
*   **Request Body**:
    ```json
    {
      "message": "用户输入的消息",
      "file_urls": ["http://...", ...], // 可选
      "file_names": ["data.xlsx", ...], // 可选，上传后的文件名
      "session_id": "optional-uuid"     // 可选，提供则延续历史会话
    }
    ```
*   **Response**:
    ```json
    {
      "chat_id": "new-turn-uuid",
      "session_id": "session-uuid"
    }
    ```

### WebSocket 实时交互
连接 WebSocket 以接收 Agent 的实时流式响应。

*   **Endpoint**: `WS /ws/chat/{chat_id}`
*   **Messages (Server -> Client)**:
    *   Status Update: `{"type": "status", "content": "正在思考..."}`
    *   Code Execution: `{"type": "code", "content": "print('hello')", "execution_count": 1}`
    *   Execution Result: `{"type": "execution_result", "status": "success", "stdout": "...", "result": {...}}`
    *   Final Response: `{"type": "response", "content": "最终回复内容..."}`
    *   Error: `{"type": "error", "content": "错误信息"}`

## 2. Skills Management

### 获取所有技能列表
获取系统中所有可用技能的元数据（Metadata）。

*   **Endpoint**: `GET /api/skills`
*   **Response**:
    ```json
    {
      "skills": [
        {
          "name": "xlsx",
          "description": "Excel处理技能...",
          "path": "skills/xlsx/SKILL.md",
          ...
        }
      ]
    }
    ```

### 获取技能详情
获取特定技能的完整内容和文件列表。

*   **Endpoint**: `GET /api/skills/{skill_name}`
*   **Response**:
    ```json
    {
      "name": "xlsx",
      "metadata": {...},
      "content": "Full Markdown Content...",
      "files": [
        {"name": "recalc.py", "size": 1024, "path": "..."}
      ]
    }
    ```

### 创建新技能
*   **Endpoint**: `POST /api/skills`
*   **Request Body**:
    ```json
    {
      "name": "new-skill",
      "content": "---\nname: ...\n---\n..."
    }
    ```

### 更新技能
*   **Endpoint**: `PUT /api/skills/{skill_name}`
*   **Request Body**:
    ```json
    {
      "new_name": "renamed-skill", // 可选
      "content": "Updated content..."
    }
    ```

### 删除技能
*   **Endpoint**: `DELETE /api/skills/{skill_name}`

## 3. MCP Servers Management

管理外部 Model Context Protocol 服务器的配置。

### 获取服务器列表
*   **Endpoint**: `GET /api/mcp-servers`
*   **Query Params**: `check_status=true|false` (是否实时检查连接状态)
*   **Response**: List of servers with connection status.

### 获取单个服务器
*   **Endpoint**: `GET /api/mcp-servers/{server_id}`

### 检查服务器状态
*   **Endpoint**: `GET /api/mcp-servers/{server_id}/status`
*   **Response**: 包含连接状态、延迟和可用工具列表。

### 添加服务器
*   **Endpoint**: `POST /api/mcp-servers`
*   **Request Body**:
    ```json
    {
      "name": "Brave Search",
      "transport": "sse", // 或 "streamable-http", "stdio"
      "url": "http://localhost:8080/sse",
      "command": null,
      "args": null
    }
    ```

### 更新服务器
*   **Endpoint**: `PUT /api/mcp-servers/{server_id}`

### 删除服务器
*   **Endpoint**: `DELETE /api/mcp-servers/{server_id}`

## 4. User Management

### 用户登录
*   **Endpoint**: `POST /api/users/login`
*   **Request Body**: `{"email": "...", "password": "..."}`
*   **Response**: `{"token": {"access_token": "...", ...}, "user": {...}}`

### 注册用户
*   **Endpoint**: `POST /api/users`
*   **Request Body**: `{"username": "...", "email": "...", "password": "..."}`

### 获取当前用户信息
*   **Endpoint**: `GET /api/users/me`

## 5. File Operations

### 上传文件
上传文件供 Agent 在对话中使用。

*   **Endpoint**: `POST /api/upload`
*   **Content-Type**: `multipart/form-data`
*   **Response**:
    ```json
    {
      "success": true,
      "url": "http://.../f/uuid.ext",
      "file_name": "uuid.ext",
      "original_name": "data.xlsx"
    }
    ```

### 获取文件
下载或预览文件（包括上传的文件和 Agent 生成的文件）。

*   **Endpoint**: `GET /f/{filename}`

## 6. System

### 健康检查
*   **Endpoint**: `GET /api/health`
*   **Response**:
    ```json
    {
      "status": "healthy",
      "version": "2.0.0",
      "skills_loaded": 5
    }
    ```

