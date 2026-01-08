# MCP Workflow Demo

这是一个使用 **Next.js 16 + React 19 + TypeScript** 构建的 MCP（Model Context Protocol）工作流演示应用。

## 技术栈

- **Next.js 16** - 使用 App Router 和 Turbopack
- **React 19** - 最新的 React 版本
- **TypeScript** - 类型安全的 JavaScript
- **WebSocket** - 实时通信
- **localStorage** - 本地配置存储
- **Tailwind CSS** - 现代化的 CSS 框架

## 功能特性

- 📡 **实时聊天界面** - 通过 WebSocket 与 MCP 服务器交互
- ⚙️ **MCP 服务器配置** - 支持多种连接类型（HTTP、SSE、stdio）
- 🔧 **工具管理** - 自动检测和显示 MCP 服务器提供的工具
- 💾 **配置持久化** - 使用 localStorage 保存服务器配置
- 🎨 **渐变主题** - 美观的紫色渐变界面设计

## 项目结构

```
frontend/
├── app/                    # Next.js App Router 目录
│   ├── layout.tsx         # 根布局
│   ├── page.tsx           # 主页面（聊天界面）
│   └── globals.css        # 全局样式
├── components/            # React 组件
│   ├── MCPConfigModal.tsx # MCP 配置模态框
│   └── MCPConfigModal.css # 模态框样式
├── lib/                   # 工具库
│   ├── api.ts            # API 客户端
│   └── mcpConfig.ts      # MCP 配置管理
├── public/               # 静态资源
├── .env.local           # 环境变量配置
├── next.config.mjs      # Next.js 配置
├── tsconfig.json        # TypeScript 配置
└── package.json         # 项目依赖

```

## 环境变量

在 `.env.local` 文件中配置以下环境变量：

```env
NEXT_PUBLIC_API_BASE=http://localhost:8001/api
NEXT_PUBLIC_WS_BASE=ws://localhost:8001/ws
```

> **注意**: 这些环境变量指向后端 MCP 服务器。请确保后端服务运行在 `localhost:8001`。

## 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

应用将在 [http://localhost:3000](http://localhost:3000) 启动。

### 构建生产版本

```bash
npm run build
```

### 运行生产服务器

```bash
npm run start
```

### 代码检查

```bash
npm run lint
```

## 使用说明

### 1. 配置 MCP 服务器

1. 点击右上角的 "⚙️ Configure MCP Servers" 按钮
2. 点击 "+ Add MCP Server" 添加新服务器
3. 填写服务器信息：
   - **Server Name**: 服务器名称
   - **Connection Type**: 选择 HTTP、SSE 或 stdio
   - **Endpoint URL/SSE URL**: 服务器地址
   - **Headers**: （可选）JSON 格式的请求头，如 API key
4. 保存配置

### 2. 使用工作流

1. 在输入框中描述您的任务
2. 点击 "Send" 发送消息
3. 系统将通过 WebSocket 与后端通信
4. 实时查看工作流执行日志和结果

## MCP 服务器类型

应用支持三种 MCP 服务器连接类型：

- **HTTP (Streamable)**: 基于 HTTP 的可流式传输连接
- **SSE (Server-Sent Events)**: 服务器推送事件
- **stdio**: 标准输入输出连接

## 开发指南

### 目录说明

- **`app/`**: Next.js App Router 页面和布局
- **`components/`**: 可复用的 React 组件
- **`lib/`**: 工具函数和 API 客户端

## 故障排查

### 连接错误

如果遇到 WebSocket 连接错误：

1. 确保后端服务运行在 `http://localhost:8001`
2. 检查 `.env.local` 文件中的环境变量配置
3. 确认 MCP 服务器配置正确

### 工具未显示

如果 MCP 服务器的工具未显示：

1. 确保服务器已启用（勾选复选框）
2. 检查服务器端点 URL 是否正确
3. 查看浏览器控制台的错误信息

## Learn More

要了解更多关于 Next.js 的信息：

- [Next.js Documentation](https://nextjs.org/docs) - Next.js 功能和 API
- [Learn Next.js](https://nextjs.org/learn) - Next.js 交互式教程
- [Next.js GitHub](https://github.com/vercel/next.js) - 欢迎反馈和贡献！

## 许可证

本项目使用 MIT 许可证。
