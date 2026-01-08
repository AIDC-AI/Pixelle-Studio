# MCP Workflow Demo - README

## 项目概述

这是一个基于 Agent + MCP Tools 架构的工作流演示系统。该系统通过生成 Python 脚本的方式，解决了以下问题：
- 工具数量过多时，Prompt 无法枚举所有工具
- 需要按顺序调用多个工具，并在工具之间传参
- 工具可动态加载，无法预先离线处理

## 架构设计

### 后端 (Python + FastAPI + uv)
- **端口**: 8001
- **核心功能**:
  - REST API 用于工具发现和会话创建
  - WebSocket 实时流式传输执行日志
  - 异步脚本执行引擎
  - LLM 脚本生成（当前为 Mock 实现）

### 前端 (React + TypeScript + Next.js + Tailwind)
- **端口**: 3000
- **核心功能**:
  - 聊天界面用于自然语言交互
  - 工具选择侧边栏
  - 实时日志显示
  - 脚本预览和结果展示

## 快速开始

### 1. 启动后端

```bash
cd backend
uv sync # 首次运行安装依赖
./start_server.sh # 启动后端
```
由于pptx依赖于nodejs，所以需要先安装nodejs。
```bash
brew install node
```
然后安装依赖
```bash
cd backend
npm install
```

### 2. 启动前端

```bash
cd frontend
npm install  # 首次运行
npm run dev # 启动前端
```

### 3. 访问应用

打开浏览器访问: http://localhost:3000

## 使用方法

1. 在左侧边栏选择要使用的工具（例如 `google_drive`）
2. 在输入框中输入自然语言请求（例如："列出我的文件"）
3. 点击"Send"按钮
4. 查看生成的工作流脚本
5. 实时观察执行日志
6. 查看最终执行结果

## 核心功能验证

### Runner 测试

```bash
python test_runner.py
```

该测试验证了脚本执行引擎可以：
- ✅ 正确执行 Python 脚本
- ✅ 捕获所有 stdout/stderr 输出
- ✅ 实时流式传输日志
- ✅ 返回最终执行结果

## 项目结构

```
mcp-workflow/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 主应用
│   │   ├── llm_adapter.py       # LLM 脚本生成（当前 Mock）
│   │   ├── mcp_client.py        # MCP 工具客户端（Mock）
│   │   └── execution/
│   │       └── runner.py        # 脚本执行引擎
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # 主聊天界面
│   │   ├── api.ts               # 后端通信层
│   │   └── App.css              # 样式
│   └── package.json
├── scripts/                     # 生成的工作流脚本存储
└── test_runner.py              # Runner 单元测试
```

## 技术栈

**后端**:
- Python 3.10+
- FastAPI - Web 框架
- Uvicorn - ASGI 服务器
- WebSockets - 实时通信

**前端**:
- React 19
- TypeScript 5.3
- Next.js 15

## 当前状态

### ✅ 已完成
- 完整的前后端架构
- WebSocket 实时通信
- 脚本生成系统
- 异步执行引擎
- 工具选择和管理
- 日志流式传输

### 🔄 待优化
- 集成真实 LLM API
- 完善错误处理
- 添加 Docker 沙箱隔离
- 实现工具检索系统

## 下一步改进

1. **集成真实 LLM**: 连接 OpenAI/Anthropic API 生成工作流脚本
2. **工具检索**: 从向量数据库中检索相关工具（目前返回所有工具）
3. **沙箱执行**: 使用 Docker 容器隔离脚本执行环境
4. **结果存储**: 实现大型结果的持久化存储
5. **认证授权**: 添加用户认证和权限管理

## 参考资料

- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- 技术架构文档: 见项目根目录的设计文档

## License

MIT
