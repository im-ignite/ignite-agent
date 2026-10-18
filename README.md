# 🔥 IGNITE V3 PRO — Autonomous AI DevOps & Engineering Agent

> **Enterprise-Grade Autonomous AI Software Engineer & DevOps Partner.**  
> Multi-Model Failover · Multi-Agent Swarm Orchestrator · GitShield Sandboxing · Semantic BM25+AST Codebase Indexer · Model Context Protocol (MCP) · Live Web Dashboard · Self-Healing Test Runner.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Architecture: Multi--Agent Swarm](https://img.shields.io/badge/Architecture-Multi--Agent%20Swarm-green.svg)](#-multi-agent-swarm-orchestrator)
[![Zero External Dependencies](https://img.shields.io/badge/Dependencies-Zero%20Mandatory-brightgreen.svg)](#-quickstart)

---

## 📑 Table of Contents
- [✨ Key Architectural Highlights](#-key-architectural-highlights)
- [🔑 API Keys Setup (PowerShell Persistent Method)](#-api-keys-setup-powershell-persistent-method)
  - [Every Supported API Key Command](#every-supported-api-key-command)
  - [Verifying Configured Keys](#verifying-configured-keys)
  - [Alternative: .env File](#alternative-env-file)
- [🚀 Quickstart](#-quickstart)
- [🤖 Multi-Agent Swarm Mode (`/plan`, `/swarm`)](#-multi-agent-swarm-mode-plan-swarm)
- [🛡️ GitShield & Autonomous Rollbacks (`/undo`, `/diff`)](#️-gitshield--autonomous-rollbacks-undo-diff)
- [🔍 Semantic Codebase Indexer & Search (`/index`, `/search`)](#-semantic-codebase-indexer--search-index-search)
- [🔌 Model Context Protocol (MCP) Integration (`/mcp`)](#-model-context-protocol-mcp-integration-mcp)
- [🌐 Live Web Dashboard (`/dashboard`)](#-live-web-dashboard-dashboard)
- [🛠 Available Slash Commands](#-available-slash-commands)
- [🧰 18 Autonomous Agent Tools](#-18-autonomous-agent-tools)
- [📄 License](#-license)

---

## ✨ Key Architectural Highlights

* **Multi-Model Priority Routing & Session Quota Guard:**  
  Dynamically balances across Gemini, Groq, Mistral, Cohere, and OpenRouter. When a provider encounters quota exhaustion (`429`), it is automatically blocked for the active session, instantly failing over to the next healthiest provider with zero user interruption.
* **Multi-Agent Swarm (`SwarmOrchestrator`):**  
  Decomposes large goals into Milestone DAGs. Orchestrates **The Architect** (strategic planner), **The Engineer** (focused coder), and **The Critic** (AST & verification gatekeeper) with real-time visual kanban boards.
* **GitShield Safety & Instant Rollback:**  
  Automatically takes shadow snapshots before any task executes. One-command rollback (`/undo`) reverts destructive code edits cleanly.
* **AST Pre-Flight Syntax Gatekeeper:**  
  Every file write or patch is validated against the Python AST parser before touching disk. Syntax errors are rejected at the gate.
* **Self-Healing Verification Loop:**  
  Detects and executes test suites (`pytest`, `unittest`, `npm test`, compiler checks). If tests fail, it automatically captures the traceback, patches the bugs, and re-verifies.
* **Zero-Dependency Semantic Codebase Indexer & Hybrid RAG:**  
  Powered by SQLite FTS5 BM25 search and Python AST symbol extraction (classes, methods, docstrings). Search millions of lines in milliseconds without external vector databases.
* **Model Context Protocol (MCP) stdio Client:**  
  Connects directly to external MCP servers (filesystem, sqlite, github, puppeteer, etc.) over JSON-RPC 2.0.
* **Direct Answer Auto-Coercion:**  
  Never rejects conversational or Markdown completions as invalid JSON.

---

## 🔑 API Keys Setup (PowerShell Persistent Method)

On Windows PowerShell, the safest, most professional way to store your API keys is using **`[Environment]::SetEnvironmentVariable(key, value, "User")`**.

### Why this method is recommended:
1. **Permanence:** Stored in your Windows User Registry. Keys survive system restarts, terminal closures, and IDE reloads.
2. **Security:** No plain text API keys are saved inside repository files or `.env` files that could be accidentally committed to GitHub.
3. **Instant Loading:** IGNITE automatically reads these variables on startup without needing extra configuration.

---

### Every Supported API Key Command

Open PowerShell and run the commands for the providers you wish to activate:

#### 1. 🌟 Google Gemini (Primary — Highly Recommended)
Get your free API key at [Google AI Studio](https://aistudio.google.com/):
```powershell
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your_gemini_api_key_here", "User")
```

#### 2. ⚡ Google Gemini Secondary Accounts (High-Volume Quota Fallback)
If you have additional Gemini API keys to bypass daily free tier rate limits:
```powershell
# Account 2
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY_2", "your_gemini_key_2_here", "User")

# Account 3
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY_3", "your_gemini_key_3_here", "User")
```

#### 3. 🚀 Groq Cloud (Ultra-Fast Inference — Free Tier)
Get your free key at [Groq Console](https://console.groq.com/):
```powershell
[Environment]::SetEnvironmentVariable("GROQ_API_KEY", "your_groq_api_key_here", "User")
```
Optional Groq secondary account:
```powershell
[Environment]::SetEnvironmentVariable("GROQ_API_KEY_2", "your_groq_key_2_here", "User")
```

#### 4. 🧠 Mistral AI (Codestral & Mistral Small)
Get your key at [Mistral AI Console](https://console.mistral.ai/):
```powershell
[Environment]::SetEnvironmentVariable("MISTRAL_API_KEY", "your_mistral_api_key_here", "User")
```

#### 5. 🌐 Cohere (Command R+)
Get your key at [Cohere Dashboard](https://dashboard.cohere.com/):
```powershell
[Environment]::SetEnvironmentVariable("COHERE_API_KEY", "your_cohere_api_key_here", "User")
```

#### 6. 🔀 OpenRouter (100+ Free & Paid Models)
Get your key at [OpenRouter](https://openrouter.ai/):
```powershell
[Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY", "your_openrouter_api_key_here", "User")
```

---

### Verifying Configured Keys

After running the `SetEnvironmentVariable` commands, restart your terminal or verify that the keys are active:

```powershell
# Check individual key
[Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")

# Or check in current session
$env:GEMINI_API_KEY
```

---

### Alternative: `.env` File

If you prefer using a local `.env` file instead of Windows registry variables, copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```
Open `.env` and fill in your keys. *(Note: `.env` is already listed in `.gitignore` to prevent accidental commits).*

---

## 🚀 Quickstart

### Prerequisites
- Python **3.10** or higher
- Windows 10/11 (PowerShell)

### Installation
Clone the repository:
```powershell
git clone https://github.com/im-ignite/ignite-agent.git
cd ignite-agent
```

*(Optional but recommended)* Install `rich` for the visual terminal interface and tables:
```powershell
pip install -r requirements.txt
```

### Launch IGNITE
```powershell
python ignite_agent.py
```

---

## 🤖 Multi-Agent Swarm Mode (`/plan`, `/swarm`)

When facing complex engineering goals, IGNITE activates its internal multi-agent swarm:

1. **🏛 The Architect:** Breaks down high-level objectives into 3–6 verifiable milestones with clear acceptance criteria.
2. **👷 The Engineer:** Executes code, writes files, compiles assets, and runs tests.
3. **🕵️ The Critic:** Performs code review, audits diffs, runs test suites, and enforces self-healing fixes before approving milestones.

```text
IGNITE> /plan build full-stack authentication system with JWT and SQLite
```

Toggle direct execution vs swarm mode anytime:
```text
IGNITE> /swarm on
IGNITE> /swarm off
```

---

## 🛡️ GitShield & Autonomous Rollbacks (`/undo`, `/diff`)

Never worry about AI breaking your codebase:
- **Automatic Pre-Task Checkpointing:** Every file modification is saved into a shadow snapshot before editing.
- **Instant Rollback:** Revert changes with one command:
  ```text
  IGNITE> /undo
  ```
- **Inspect Diffs:** Colorized unified git diffs of uncommitted changes:
  ```text
  IGNITE> /diff
  ```
- **Self-Healing Test Runner:**
  ```text
  IGNITE> /verify
  ```

---

## 🔍 Semantic Codebase Indexer & Search (`/index`, `/search`)

Built-in zero-dependency semantic code search:
- Indexes all project files (`.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.yaml`, etc.) using **SQLite FTS5 BM25** ranking.
- Extracts AST definitions (classes, functions, methods, docstrings).
- Incremental updates in under `0.1s`.

```text
IGNITE> /index           # Incremental sync
IGNITE> /index rebuild   # Complete re-indexing
IGNITE> /search verify_token
```

---

## 🔌 Model Context Protocol (MCP) Integration (`/mcp`)

Connects to standard Model Context Protocol servers over stdio:
- Discover external tools from filesystem servers, database servers, and APIs.
- Configure via `.ignite_mcp.json`.

```text
IGNITE> /mcp init        # Create starter .ignite_mcp.json
IGNITE> /mcp list        # List available tools across all MCP servers
IGNITE> /mcp status      # Check connectivity of background servers
```

---

## 🌐 Live Web Dashboard (`/dashboard`)

IGNITE includes a built-in real-time HTTP server and web dashboard:
```text
IGNITE> /dashboard
```
Opens `http://localhost:7860` in your default browser, providing:
- Real-time token consumption & estimated cost metrics.
- Active background process status & log streams.
- Live session history and memory inspection.

---

## 🛠 Available Slash Commands

| Command | Action |
|---|---|
| `/plan [goal]` | Multi-Agent Swarm (Architect ➔ Engineer ➔ Critic) |
| `/swarm [on\|off]` | Toggle Multi-Agent Swarm Mode |
| `/index [rebuild]` | Incremental or full codebase semantic indexing |
| `/search <query>` | Search functions, classes, and code chunks across codebase |
| `/mcp [list\|init]` | Manage Model Context Protocol servers and tools |
| `/undo`, `/rollback` | Revert codebase to pre-task safety checkpoint |
| `/diff [file]` | Show colorized git diff of working tree changes |
| `/verify [cmd]` | Run self-healing test runner / code checks |
| `/commit [msg]` | Stage and commit all uncommitted changes |
| `/checkpoint` | Create a manual safety restore snapshot |
| `/dashboard`, `/ui` | Launch live Web UI on `localhost:7860` |
| `/model [num]` | Interactive model selector (Arrow keys / 1-9) |
| `/deploy [target]` | Automated cloud deployment (Railway, Fly, Docker, Render) |
| `/memory` | Inspect episodic memory & context tokens |
| `/ps`, `/kill <pid>` | Monitor and manage background subprocesses and windows |
| `/tools` | Display all 18 available autonomous agent tools |
| `/clear` | Clear conversation history while preserving learned episodes |

---

## 🧰 18 Autonomous Agent Tools

1. `terminal`: Execute PowerShell commands with live streaming output.
2. `file_read`: Read files with line ranges and bounds.
3. `file_write`: Write/create files with **AST syntax pre-flight gatekeeping**.
4. `file_patch`: Apply surgical unified diffs.
5. `git`: Full git repository management.
6. `git_diff`: Inspect working tree modifications.
7. `verify_code`: Self-healing automated test runner.
8. `python_eval`: In-memory isolated Python evaluation.
9. `spawn`: Open detached visible terminal windows or background workers.
10. `kill`: Safely terminate processes by PID or name.
11. `process_status`: Inspect process health and memory.
12. `read_log`: Stream live stdout/stderr from background processes.
13. `search`: Web search (DuckDuckGo & Bing fallback).
14. `code_search`: Semantic hybrid BM25 + AST symbol search across project.
15. `mcp_call`: Invoke external Model Context Protocol tools.
16. `deploy`: Autonomous scaffolding & cloud deployment.
17. `ask`: Pause and request decisions/credentials from user.
18. `done`: Complete task or answer directly.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
