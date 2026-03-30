# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeerFlow is a full-stack "super agent harness" built on LangGraph + FastAPI with sandbox execution, memory, subagents, and skills.

- **Backend**: Python 3.12, LangGraph + FastAPI gateway, sandbox/tool system, memory, MCP integration
- **Frontend**: Next.js 16 + React 19 + TypeScript + pnpm
- **Local dev entrypoint**: root `Makefile` starts backend + frontend + nginx on `http://localhost:2026`
- **Docker dev entrypoint**: `make docker-*` commands

## Build & Test Commands

### Full Application (from project root)

```bash
make check      # Verify prerequisites (Node 22+, pnpm, uv, nginx)
make install    # Install all dependencies (backend + frontend)
make dev        # Start all services: LangGraph (2024), Gateway (8001), Frontend (3000), nginx (2026)
make stop       # Stop all services
make config     # Generate local config files (first-time setup only)
```

### Backend (from `backend/`)

```bash
cd backend && make lint   # ruff linting
cd backend && make test   # pytest suite (~277 tests)
```

### Frontend (from `frontend/`)

```bash
cd frontend && pnpm lint       # ESLint
cd frontend && pnpm typecheck # TypeScript check
cd frontend && BETTER_AUTH_SECRET=local-dev-secret pnpm build  # Production build
```

**Important**: `pnpm build` requires `BETTER_AUTH_SECRET` environment variable. CI validates with `BETTER_AUTH_SECRET=... pnpm build`.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
│                    port 3000 → nginx → port 2026                │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌──────────────────┐           ┌──────────────────┐
    │   LangGraph API   │           │   Gateway API     │
    │   (port 2024)     │           │   (port 8001)     │
    └──────────────────┘           └──────────────────┘
              │                               │
              ▼                               ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Harness Package (`deerflow-harness`)           │
    │  • Lead Agent + Middlewares (12 middleware chain)           │
    │  • Sandbox (Local/Docker/K8s providers)                    │
    │  • Subagent System (parallel execution, 3 workers)          │
    │  • Tools (built-in, MCP, community)                        │
    │  • Memory System (persistent, LLM-based updates)            │
    │  • Skills (file-based, .skill archives)                    │
    └─────────────────────────────────────────────────────────────┘
```

### Backend Structure (`backend/`)

- `packages/harness/deerflow/` - Publishable agent framework (`deerflow-harness`)
  - `agents/lead_agent/` - Main agent entry point
  - `agents/memory/` - Memory extraction, queue, updates
  - `sandbox/` - Sandbox provider abstraction
  - `subagents/` - Subagent registry and executor
  - `mcp/` - MCP server integration
  - `models/` - Model factory with thinking/vision support
  - `skills/` - Skills discovery and loading
  - `config/` - Configuration system with env var resolution
  - `community/` - Community tools (tavily, jina_ai, firecrawl, aio_sandbox)
- `app/gateway/` - FastAPI Gateway API
  - `routers/` - models, mcp, skills, memory, uploads, threads, artifacts
- `app/channels/` - IM integrations (Feishu, Slack, Telegram)
- `langgraph.json` - Graph entrypoint: `deerflow.agents:make_lead_agent`

### Frontend Structure (`frontend/src/`)

- `app/` - Next.js App Router (routes: `/` landing, `/workspace/chats/[thread_id]` chat)
- `components/workspace/` - Chat page components (messages, artifacts, settings)
- `core/` - Business logic: threads, API client, artifacts, memory, skills
- `hooks/` - Shared React hooks

### Harness/App Dependency Rule

**Strict**: Harness (`deerflow.*`) never imports from App (`app.*`). This is enforced by `tests/test_harness_boundary.py` in CI.

```
Harness → Harness imports allowed
App → Harness imports allowed
Harness → App imports FORBIDDEN
```

## Key Systems

### Middleware Chain (12 middlewares, strict order)

1. ThreadDataMiddleware - Per-thread directory creation
2. UploadsMiddleware - Track uploaded files
3. SandboxMiddleware - Acquire sandbox
4. DanglingToolCallMiddleware - Handle interrupted tool calls
5. GuardrailMiddleware - Pre-tool-call authorization
6. SummarizationMiddleware - Context reduction
7. TodoListMiddleware - Task tracking (plan mode)
8. TitleMiddleware - Auto-generate thread titles
9. MemoryMiddleware - Queue for async memory updates
10. ViewImageMiddleware - Inject base64 images (vision models)
11. SubagentLimitMiddleware - Enforce MAX_CONCURRENT_SUBAGENTS=3
12. ClarificationMiddleware - Intercept clarification requests

### Sandbox Virtual Paths

Agent sees: `/mnt/user-data/{workspace,uploads,outputs}`, `/mnt/skills`
Physical: `backend/.deer-flow/threads/{thread_id}/user-data/...`

### Configuration

- `config.yaml` - Main app config (models, tools, sandbox, channels, memory)
- `extensions_config.json` - MCP servers and skills state
- Both support runtime updates via Gateway API

## Critical Gotchas

- `BETTER_AUTH_SECRET` required for frontend production build
- `make config` is non-idempotent (aborts if config exists)
- `make dev` includes process cleanup; interrupted runs need `make stop`
- Proxy env vars can break frontend network operations
- Backend lint/tests must pass before PR (CI requirement)
- Harness boundary test (`tests/test_harness_boundary.py`) enforces import rules

## Detailed Documentation

For backend details, see `backend/CLAUDE.md`.
For frontend details, see `frontend/CLAUDE.md`.
For complete setup, see `.github/copilot-instructions.md`.
