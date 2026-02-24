# Pixelle-Studio Demo

This is an MCP (Model Context Protocol) workflow demo application built with **Next.js 16 + React 19 + TypeScript**.

## Tech Stack

- **Next.js 16** - Using App Router and Turbopack
- **React 19** - Latest React version
- **TypeScript** - Type-safe JavaScript
- **WebSocket** - Real-time communication
- **localStorage** - Local configuration storage
- **Tailwind CSS** - Modern CSS framework

## Features

- 📡 **Real-time Chat Interface** - Interact with MCP server via WebSocket
- ⚙️ **MCP Server Configuration** - Support multiple connection types (HTTP, SSE, stdio)
- 🔧 **Tool Management** - Auto-detect and display tools provided by MCP servers
- 💾 **Configuration Persistence** - Save server configurations using localStorage
- 🎨 **Gradient Theme** - Beautiful purple gradient UI design

## Project Structure

```
frontend/
├── app/                    # Next.js App Router directory
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Main page (chat interface)
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── MCPConfigModal.tsx # MCP config modal
│   └── MCPConfigModal.css # Modal styles
├── lib/                   # Utility library
│   ├── api.ts            # API client
│   └── mcpConfig.ts      # MCP configuration management
├── public/               # Static assets
├── .env.local           # Environment variable config
├── next.config.mjs      # Next.js configuration
├── tsconfig.json        # TypeScript configuration
└── package.json         # Project dependencies

```

## Environment Variables

Configure the following environment variables in the `.env.local` file:

```env
NEXT_PUBLIC_API_BASE=http://localhost:8001/api
NEXT_PUBLIC_WS_BASE=ws://localhost:8001/ws
```

> **Note**: These environment variables point to the backend MCP server. Ensure the backend service is running on `localhost:8001`.

## Quick Start

### Install Dependencies

```bash
npm install
```

### Start Development Server

```bash
npm run dev
```

The app will start at [http://localhost:3000](http://localhost:3000).

### Build Production Version

```bash
npm run build
```

### Run Production Server

```bash
npm run start
```

### Code Linting

```bash
npm run lint
```

## Usage Guide

### 1. Configure MCP Servers

1. Click the "⚙️ Configure MCP Servers" button in the top-right corner
2. Click "+ Add MCP Server" to add a new server
3. Fill in server details:
   - **Server Name**: Server name
   - **Connection Type**: Choose HTTP, SSE, or stdio
   - **Endpoint URL/SSE URL**: Server address
   - **Headers**: (Optional) JSON format request headers, e.g. API key
4. Save configuration

### 2. Use Workflow

1. Describe your task in the input box
2. Click "Send" to send the message
3. The system will communicate with the backend via WebSocket
4. View workflow execution logs and results in real-time

## MCP Server Types

The application supports three MCP server connection types:

- **HTTP (Streamable)**: HTTP-based streamable transport connection
- **SSE (Server-Sent Events)**: Server-pushed events
- **stdio**: Standard input/output connection

## Development Guide

### Directory Overview

- **`app/`**: Next.js App Router pages and layouts
- **`components/`**: Reusable React components
- **`lib/`**: Utility functions and API clients

## Troubleshooting

### Connection Errors

If you encounter WebSocket connection errors:

1. Ensure the backend service is running on `http://localhost:8001`
2. Check the environment variable configuration in `.env.local`
3. Confirm MCP server configuration is correct

### Tools Not Showing

If MCP server tools are not displayed:

1. Ensure the server is enabled (checkbox checked)
2. Check if the server endpoint URL is correct
3. View error messages in the browser console

## Learn More

To learn more about Next.js:

- [Next.js Documentation](https://nextjs.org/docs) - Next.js features and API
- [Learn Next.js](https://nextjs.org/learn) - Next.js interactive tutorial
- [Next.js GitHub](https://github.com/vercel/next.js) - Feedback and contributions welcome!

## License

This project uses the MIT License.
