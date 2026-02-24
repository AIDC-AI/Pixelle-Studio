<p align="center">
  <img src="frontend/public/logo.png" alt="Pixelle Studio" width="400">
</p>

<p align="center">
  <strong>🚀 Drive Everything with Natural Language — Your AI-Powered Workspace</strong>
</p>

<p align="center">
  <a href="https://github.com/AIDC-AI/Pixelle-Studio"><img src="https://img.shields.io/github/stars/AIDC-AI/Pixelle-Studio?style=social" alt="GitHub Stars"></a>
  <a href="https://github.com/AIDC-AI/Pixelle-Studio/blob/main/LICENSE"><img src="https://img.shields.io/github/license/AIDC-AI/Pixelle-Studio" alt="License"></a>
  <a href="https://github.com/AIDC-AI/Pixelle-Studio"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
  <a href="https://github.com/AIDC-AI/Pixelle-Studio"><img src="https://img.shields.io/badge/Next.js-16-black.svg" alt="Next.js"></a>
</p>

<p align="center">
  <strong>English</strong> | <a href="README_CN.md">中文</a>
</p>

---

**Pixelle Studio** is an open-source AI Agent workspace. Just describe what you need in natural language — the Agent will automatically invoke tools, execute code, and generate documents to accomplish complex tasks from data analysis to travel planning.

> 💡 **More than a chatbot** — it can truly think, execute, and create.

<p align="center">
  <img src="assets/main.png" alt="Pixelle Studio Main Interface" width="100%">
</p>

---

## ✨ Key Highlights

<table>
<tr>
<td width="33%" align="center">
<h3>📄 Full-Format Document Processing</h3>
<p>PDF, Excel, PPT, Word, Markdown, HTML<br>— Smart generation & live preview</p>
</td>
<td width="33%" align="center">
<h3>🧠 Custom Skills System</h3>
<p>Package your SOPs / expertise into Skills<br>— Dramatically boost task success rates</p>
</td>
<td width="33%" align="center">
<h3>🔌 MCP Tool Integration</h3>
<p>One-click access to search engines, maps,<br>video & more — extend your Agent's reach</p>
</td>
</tr>
</table>

### 🎯 Why Pixelle Studio?

| Feature | Traditional AI Chat Tools | Pixelle Studio |
|---------|:---:|:---:|
| Document Generation (PDF/PPT/Excel) | ❌ Text-only output | ✅ Generate files with live preview |
| Code Execution | ❌ Or plugin-dependent | ✅ Built-in persistent terminal, multi-step |
| Custom Skills | ❌ | ✅ Turn SOPs into executable Skills |
| External Tools (MCP) | ❌ Closed ecosystem | ✅ Open protocol, plug & play |
| Context Management | ❌ Passive truncation | ✅ Smart compression, auto-managed |
| Multi-Model Failover | ❌ Single model | ✅ Three-layer failover mechanism |
| Token Consumption | 🔴 Full context loading | 🟢 Progressive on-demand loading |

---

## 🖼️ Use Cases

### 1️⃣ Road Trip Planning

> 💬 *"I'd like to drive from Seattle Airport to Mount Rainier, could you please help me with my itinerary? I'm leaving tomorrow morning."*

Agent loads map skills → calls map API → plans the route → generates itinerary document with live preview

<p align="center">
  <img src="assets/from Seattle Airport to Mount Rainier.png" alt="Road Trip Planning" width="100%">
</p>

Fully bilingual — the same natural language experience works seamlessly in Chinese too 👇

<p align="center">
  <img src="assets/杭州到北京自驾1.png" alt="杭州到北京自驾行程规划" width="100%">
</p>

### 2️⃣ Deep Research + PPT Generation

> 💬 *"Please help me do some in-depth research on what good food and fun things to do in Zhengzhou. Return the result with a PPT."*

Agent combines multiple Skills → web search → content scraping → structured analysis → auto-generates PPT

<p align="center">
  <img src="assets/deep-research with ppt generation.png" alt="Deep Research + PPT Generation" width="100%">
</p>

### 3️⃣ HTML Games & Interactive Content

> 💬 *"Build me a Snake game"*

Agent writes HTML/CSS/JS → generates a runnable game file → built-in preview for instant play

<p align="center">
  <img src="assets/files-html.png" alt="HTML Snake Game" width="100%">
</p>

### 4️⃣ Create Your Own Skills

Don't just use built-in skills — create your own to teach the Agent your unique workflows:

<p align="center">
  <img src="assets/skill-edit.png" alt="Skill Editor" width="100%">
</p>

---

## 🏗️ Architecture

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
      │  9 Built-in ││ PTY      ││  Skill   ││ MCP      ││ Context  │
      │  Tools      ││ Terminal ││  System  ││ Tools    ││ Manager  │
      │ read/write  ││Persistent││Progressive││External ││  Auto    │
      │ exec/shell  ││ Sessions ││ Loading  ││Integration│ Compaction│
      └────────────┘└──────────┘└──────────┘└──────────┘└──────────┘
```

### Technical Deep Dive

<details>
<summary><b>🔋 Progressive Skill Loading — The Secret to Token Efficiency</b></summary>

<br>

Unlike traditional approaches that stuff all skills into the System Prompt, we use **three-level progressive loading**:

| Level | Content | Token Cost | When Loaded |
|-------|---------|-----------|-------------|
| Level 1 | Skill metadata (name + description) | ~50 tokens/skill | Every conversation |
| Level 2 | Full SKILL.md documentation | ~500-2000 tokens | On-demand by Agent |
| Level 3 | Auxiliary files (scripts/references) | Variable | On-demand by Agent |

**Result**: 12 built-in Skills consume only ~600 tokens of metadata, while traditional approaches might require 20,000+ tokens.

</details>

<details>
<summary><b>🖥️ Persistent Pseudo-Terminal (PTY) — Beyond Code Execution</b></summary>

<br>

Built on `pexpect`, our persistent Shell Sessions go beyond one-shot code execution:

```python
# Variables persist across multiple calls!
shell_exec("import pandas as pd", shell_type="python")
shell_exec("df = pd.DataFrame({'a': [1,2,3]})", shell_type="python")
shell_exec("print(df.describe())", shell_type="python")  # df still exists!
```

**Advantages**:
- ✅ Variable Persistence — State maintained across calls
- ✅ Multi-language — Bash / Python / IPython
- ✅ Auto-recovery — Automatic restart on session crash
- ✅ Auto-cleanup — Idle sessions automatically recycled

</details>

<details>
<summary><b>🛡️ Three-Layer Failover — Service That Never Stops</b></summary>

<br>

```
Request failed?
  ├─ Layer 1: Auth Failover     → Switch API Key / Base URL
  ├─ Layer 2: Model Failover    → Switch to fallback model (gpt-4o → gpt-4o-mini → ...)
  └─ Layer 3: Thinking Failover → Downgrade thinking depth
```

Even if the primary model faces rate limits, timeouts, or quota exhaustion, the system automatically switches to backup plans, keeping tasks uninterrupted.

</details>

<details>
<summary><b>📐 Smart Context Management — Never Overflow</b></summary>

<br>

- **Context Window Guard** — Real-time token usage monitoring with automatic threshold alerts
- **Auto-Compaction** — When context reaches ~70% usage, automatically generates a summary to compress history
- **Multi-model Aware** — Auto-detects model context window sizes (GPT-4o 128K / Claude 200K / Gemini 1M)

</details>

---

## 🔌 MCP External Tool Integration

Seamlessly connect external tools via the [Model Context Protocol](https://modelcontextprotocol.io/) open standard:

<p align="center">
  <img src="assets/mcp-add.png" alt="MCP Configuration" width="100%">
</p>

**Built-in Skills already support these MCP tools**:

| Tool | Function | Use Case |
|------|----------|----------|
| 🔍 Exa Search | AI-native search engine | Deep research, info gathering |
| 🔍 Bing Search | General web search | Real-time information queries |
| 🗺️ AMap (Gaode) | Route planning, POI search | Travel planning |
| 🌐 Web Fetch | Web content scraping | Data collection |
| 🎬 Social Media Video | Video content parsing | Content creation |

> You can also integrate any MCP-compatible tool service!

---

## 🚀 Quick Start

### Option 1: Development Mode

```bash
# 1. Clone the repo
git clone https://github.com/AIDC-AI/Pixelle-Studio.git
cd Pixelle-Studio

# 2. Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env and add your API key:
# OPENAI_API_KEY=your-api-key

# 3. One-command start (both frontend & backend)
./start.sh
```

### Option 2: Docker Deployment

```bash
# One-command start
./start.sh -D

# Or use docker compose directly
docker compose up --build
```

### Option 3: Manual Start

```bash
# Backend
cd backend
uv sync             # Install dependencies
./start_server.sh   # Start server (port 8001)

# Frontend (new terminal)
cd frontend
npm install          # Install dependencies
npm run dev          # Start dev server (port 3000)
```

Then visit 👉 **http://localhost:3000**

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API Key | Required |
| `OPENAI_BASE_URL` | API Base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model to use | `gpt-4o` |
| `FRONTEND_PORT` | Frontend port | `3000` |
| `BACKEND_PORT` | Backend port | `8001` |

---

## 🛠️ Built-in Tools

Pixelle Studio provides the Agent with **9 ready-to-use tools**:

| Tool | Function | Description |
|------|----------|-------------|
| `shell_exec` | Persistent terminal | Multi-step execution with variable persistence |
| `exec` | Command execution | One-shot commands / background tasks |
| `read_file` | Read files | Supports skill files and user files |
| `write_file` | Write files | Create scripts / config files |
| `edit_file` | Edit files | Precise string replacement |
| `grep` | Search content | Regex support |
| `find` | Find files | Glob pattern matching |
| `ls` | List directory | Smart limiting to prevent overflow |
| `process` | Process management | Monitor / terminate background tasks |

---

## 📁 Project Structure

```
Pixelle-Studio/
├── frontend/                  # Frontend (Next.js 16 + React 19)
│   ├── app/                   # App Router pages
│   ├── components/            # UI Components
│   │   ├── layout/chat/       # Chat interface
│   │   ├── layout/leftPanel/  # Sidebar (Sessions + Skills)
│   │   └── ui/                # Shared UI components
│   ├── hooks/                 # React Hooks
│   ├── lib/                   # API clients
│   └── types/                 # TypeScript type definitions
│
├── backend/                   # Backend (Python + FastAPI)
│   ├── app/
│   │   ├── agent.py           # SkillAgent core engine
│   │   ├── tools/             # 9 built-in tools
│   │   ├── context/           # Context management (Guard + Compaction)
│   │   ├── skills/            # Skill loader
│   │   ├── config/            # Failover configuration
│   │   └── routes/            # REST API routes
│   ├── skills/                # Skills library
│   │   ├── default/           # Built-in skills (PDF/PPT/Excel/Search...)
│   │   └── <user_id>/         # User-defined skills
│   └── scripts/               # Generated file storage
│
├── assets/                    # README assets
├── docker-compose.yml         # Docker orchestration
└── start.sh                   # One-command start script
```

---

## 🧰 Tech Stack

**Backend**: Python 3.10+ · FastAPI · OpenAI API · WebSocket · SQLAlchemy · pexpect

**Frontend**: Next.js 16 · React 19 · TypeScript · Tailwind CSS · Ant Design

**Infrastructure**: Docker · SQLite · MCP Protocol

---

## 🤝 Contributing

We welcome all contributions! Whether it's bug reports, feature suggestions, or code submissions.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

---

<p align="center">
  <b>⭐ If this project helps you, please give us a Star!</b>
</p>

<p align="center">
  <a href="https://github.com/AIDC-AI/Pixelle-Studio">GitHub</a> ·
  <a href="https://github.com/AIDC-AI/Pixelle-Studio/issues">Report Bug</a> ·
  <a href="https://github.com/AIDC-AI/Pixelle-Studio/issues">Request Feature</a>
</p>
