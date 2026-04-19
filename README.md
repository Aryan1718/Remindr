# Remindr

Remindr is a context-aware personal assistant that helps users follow through on tasks, deadlines, and goals without relying on static reminders. It combines a web control surface, a FastAPI backend, background workers, external connectors, and a Telegram delivery channel to decide when an action should happen and surface it at the right time.

> [!NOTE]
> The repository path may still use older internal names, but the product name for this project is **Remindr**.

## Overview

Traditional reminder tools assume the user already knows when to act. Remindr is built around a different assumption: timing is part of the problem.

Instead of only storing tasks, the system is designed to:

- learn routine and fatigue patterns
- ingest context from connected tools such as Google Calendar
- maintain an internal planning calendar
- score urgency, energy fit, and deadline risk
- deliver proactive nudges through Telegram and the web app

The current codebase already includes the main product layers:

- a **React + TypeScript + Vite** frontend for onboarding, integrations, channel setup, authentication, and dashboard surfaces
- a **FastAPI** backend for auth, users, tasks, connectors, decisions, notifications, fatigue, internal calendar, and Telegram flows
- a **Postgres / Supabase-ready** schema with vector memory support
- worker jobs and watchers for sync, notifications, deadline monitoring, and memory distillation

## What It Does

- **Onboarding flow** for routine, preferences, and setup
- **Task management APIs** with scheduling-oriented metadata such as deadlines, effort, and energy
- **Connector support** centered on Google Calendar, with normalization and sync jobs
- **Internal calendar blocks** for suggested work, review blocks, recovery blocks, and deadline buffers
- **Fatigue tracking** and pattern aggregation to influence timing decisions
- **Notification pipeline** for proactive delivery
- **Telegram integration** as the MVP communication channel
- **Memory and learning primitives** for storing patterns, preferences, and inferred behavior

## Architecture

Remindr is split into focused layers so the planning logic can evolve independently from the UI and delivery channels.

1. **Frontend**
   React app used for onboarding, connector setup, authentication, dashboard views, and account management.
2. **Backend API**
   FastAPI service exposing `/api/v1` routes for auth, users, connectors, internal calendar, tasks, fatigue, notifications, decisions, and Telegram.
3. **Decision and service layer**
   Application services combine user state, deadlines, calendar context, and fatigue signals into recommendations.
4. **Data layer**
   Postgres/Supabase-backed schema for users, preferences, tasks, connectors, internal calendar blocks, fatigue records, notifications, and learned memories.
5. **Workers and watchers**
   Background jobs handle connector sync, notification dispatch, fatigue aggregation, memory distillation, and deadline monitoring.

## Repository Layout

```text
.
├── backend/        FastAPI app, services, routes, workers, tests, env example
├── frontend/       React + Vite application and UI components
├── db/             SQL bootstrap for a fresh database
├── docs/           Product, architecture, API, connector, and implementation docs
├── CONTRIBUTING.md
└── README.md
```

## Getting Started

### Prerequisites

Install the following locally:

- **Node.js 18+** for the frontend
- **Python 3.11+** for the backend
- **PostgreSQL** or a **Supabase** project
- Optional: **Redis** if you want to run background workers in a non-eager mode later
- Optional: **Google OAuth credentials** for Calendar integration
- Optional: **Telegram bot token / webhook setup** for channel delivery

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd FUK
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The backend runs on `http://127.0.0.1:8000` by default.

### 3. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend runs on `http://127.0.0.1:5173` by default.

### 4. Initialize the database

Apply the bootstrap schema from [`db/init.sql`](/Users/csuftitan/Desktop/FUK/db/init.sql).

Example:

```bash
psql "$DATABASE_URL" -f db/init.sql
```

If you are using Supabase, you can apply the same SQL through the SQL editor or your preferred migration workflow.

## Configuration

The project ships with environment templates in [`backend/.env.example`](/Users/csuftitan/Desktop/FUK/backend/.env.example) and [`frontend/.env.example`](/Users/csuftitan/Desktop/FUK/frontend/.env.example).

### Backend highlights

- `API_PREFIX`
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_JWT_SECRET`
- `FRONTEND_BASE_URL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL`
- `TELEGRAM_DEFAULT_WEBHOOK_BASE_URL`

### Frontend highlights

- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

> [!IMPORTANT]
> The app can boot locally with minimal configuration, but Google Calendar auth, Supabase-backed auth, Telegram delivery, and LLM-driven behavior require valid credentials before those flows work end to end.

## Running Tests

Backend tests are located in [`backend/tests`](/Users/csuftitan/Desktop/FUK/backend/tests).

```bash
cd backend
source .venv/bin/activate
pytest
```

## Current Product Surface

The repository already contains strong backend coverage and product scaffolding, but some frontend areas are intentionally still placeholders during the redesign pass.

At the moment, the most active surfaces in code are:

- authentication and onboarding
- dashboard and integrations pages
- Google Calendar connection flow
- backend APIs and scheduling-related domain models
- workers, watchers, and decision-support services

## Documentation

The `docs/` directory contains the product and engineering context behind the current implementation. Useful starting points:

- [`docs/PRD.md`](/Users/csuftitan/Desktop/FUK/docs/PRD.md)
- [`docs/Architecture.md`](/Users/csuftitan/Desktop/FUK/docs/Architecture.md)
- [`docs/Frontend.md`](/Users/csuftitan/Desktop/FUK/docs/Frontend.md)
- [`docs/backend_api_contract.md`](/Users/csuftitan/Desktop/FUK/docs/backend_api_contract.md)
- [`docs/telegram_agent_flow.md`](/Users/csuftitan/Desktop/FUK/docs/telegram_agent_flow.md)

## Why Remindr

Remindr is aimed at users who do not need another static checklist. They need a system that understands context, notices pressure before it becomes a missed deadline, and helps them act when the timing is actually workable.

That is the core direction of this repository: a proactive assistant that turns context into timely action.
