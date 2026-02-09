# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RRC Chat UI is a clinical study recruitment chatbot for Rose Research Center. It guides prospective participants through a screening workflow: consent, identity verification, profile collection, pre-screening questions, eligibility evaluation, and scheduling. The app is deployed on Vercel.

## Commands

```bash
npm run dev          # Start Next.js dev server (frontend only)
npm run build        # Production build
npm run lint         # ESLint
```

The Python backend runs as Vercel serverless functions — there is no separate local Python server command. To test the full stack locally, use `vercel dev`.

## Architecture

This is a hybrid Next.js (frontend) + Python (backend) application deployed as a monorepo on Vercel.

### Frontend (Next.js 14 / TypeScript / Tailwind)

- **Single page app**: `src/app/page.tsx` renders `ChatInterface` using the `useChat` hook
- **`src/hooks/useChat.ts`**: Core state management hook. Initializes a session via `POST /api/session`, then sends messages via `POST /api/chat`. Tracks conversation state including `currentStep`, `responseType` (text/form/end), form `fields`, and `options`
- **`src/lib/api.ts`**: Thin fetch wrappers for `/api/session` and `/api/chat`
- **`src/types/chat.ts`**: Shared TypeScript interfaces (`ChatResponse`, `Message`, `FieldDescriptor`)
- **`src/components/`**: Form components are step-driven — `ChatInterface` renders the appropriate form (IdentityForm, ProfileForm, PrescreenForm, SchedulingForm) based on `currentStep`. DataViewPanel shows live lead data for demo purposes
- **Path alias**: `@/*` maps to `./src/*`
- **Brand colors**: Defined as `rrc-*` in `tailwind.config.ts` (e.g., `rrc-primary`, `rrc-accent`)

### Backend (Python serverless functions)

API endpoints in `api/` use Vercel's Python runtime (`BaseHTTPRequestHandler` pattern):

- **`api/session.py`** — `POST /api/session`: Creates a new session (generates UUID, runs greeting node, saves state to PostgreSQL). Also contains shared helpers: `save_session`, `load_session`, `state_to_response`
- **`api/chat.py`** — `POST /api/chat`: Processes a user message. Routes FAQ questions to RAG; otherwise advances the LangGraph state machine
- **`api/lead-data.py`** — `GET /api/lead-data?session_id=`: Returns lead record for the DataView panel
- **`api/rag_utils.py`**: FAQ detection (`is_faq_question`) and RAG initialization/answering

### Agent State Machine (`rrcagent/`)

A LangGraph-based state machine that drives the conversation flow:

- **`state.py`**: `AgentState` TypedDict — the canonical state shape
- **`graph.py`**: `step_graph()` is the main entry point. Runs nodes turn-by-turn, advancing through non-interactive nodes automatically and pausing at nodes that need user input. `build_graph()` creates the LangGraph `StateGraph` for validation
- **`nodes.py`**: Node functions for each conversation step (greeting, consent, identity_collection, lead_lookup, create_lead, pin_auth, profile_collection, prescreen, eligibility, scheduling, handoff/disqualification). Profile fields are collected in groups defined by `PROFILE_FIELD_GROUPS`
- **`routing.py`**: Conditional edge functions that determine the next node based on state
- **`eligibility.py`**: Deterministic rules engine (no LLM) — evaluates profile against inclusion/exclusion criteria from study config
- **`db.py`**: `Database` class (PostgreSQL via psycopg) with `lookup_lead`, `create_lead`, `update_lead`, `create_handoff`. `MockDatabase` for testing
- **`config.py`**: Loads study config from `studies/<study_id>/config.json`. Required sections: `study`, `messaging`, `pre_screen`, `eligibility`

### RAG System (`rrcagent/rag/`)

Handles FAQ questions without advancing the conversation state:

- **`service.py`**: `RagService` — indexes FAQ docs (chunk → embed → store), answers questions with coaching-language guardrails
- **`chunker.py`**: Markdown-aware document chunking
- **`embedder.py`**: Gemini embeddings
- **`llm.py`**: Gemini LLM for answer generation
- **`store.py`**: In-memory vector store (MockVectorStore)

### Data Flow

1. Frontend creates session → backend runs greeting node → returns first message
2. User responds → frontend sends to `/api/chat` → backend checks if FAQ (→ RAG) or workflow (→ `step_graph`)
3. `step_graph` runs the current node with user input, then auto-advances through non-interactive nodes (lead_lookup, eligibility) until hitting a node that needs input
4. `state_to_response` converts agent state to API response, determining `type` (text/form/end) and populating `fields`/`options` based on `current_step`
5. Frontend renders appropriate form component based on `currentStep` string prefix (e.g., `collecting_group:*` → ProfileForm)

### Study Configuration

Study configs live in `studies/<study_id>/config.json` (currently only `zyn`). FAQ documents are `studies/<study_id>/faq.md`.

### Environment Variables

- `DATABASE_URL` — PostgreSQL connection string (required)
- `GOOGLE_API_KEY` — For Gemini embeddings/LLM in RAG (optional, FAQ disabled without it)

### Database

PostgreSQL with two main tables:
- `rrc_sessions` — Session state storage (JSONB) for serverless persistence (see `init.sql`)
- `rrc_leads` — Lead/participant records
- `rrc_handoffs` — Agent-to-human handoff records

### Deployment

Configured via `vercel.json`. Python API routes are built with `@vercel/python`, frontend with `@vercel/next`. Routes map `/api/session`, `/api/chat`, `/api/lead-data` to their respective `.py` files.
