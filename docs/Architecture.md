# Fatigue-Aware Personal Assistant - Architecture

Last updated: April 18, 2026

## 1. High-Level Overview

System layers:

1. Client Layer
2. API / Backend
3. Orchestration Layer
4. Decision Engine
5. Data Layer
6. Connectors
7. Communication Layer
8. Background Workers

---

## 2. System Components

## 2.1 Client Layer

Interfaces:
- Web dashboard (Next.js)
- Telegram bot (MVP primary)

Responsibilities:
- onboarding UI
- viewing goals/tasks
- user interaction

---

## 2.2 Backend API

Recommended: FastAPI

Responsibilities:
- authentication
- user profile management
- task & goal CRUD
- connector management
- decision request handling
- storing structured data

---

## 2.3 Orchestration Layer

Core coordinator of the system.

Responsibilities:
- fetch context (calendar, email, tasks)
- detect intent
- call decision engine
- trigger follow-up actions
- manage workflows

---

## 2.4 Decision Engine

Core intelligence layer.

Inputs:
- user state
- fatigue level
- tasks and deadlines
- calendar context
- learned patterns

Outputs:
- recommendation
- timing decision
- follow-up questions
- schedule updates

Approach:
- hybrid (rules + scoring + LLM)

---

## 2.5 Data Layer

### Structured Database (PostgreSQL / Supabase)

Tables:
- users
- profiles
- tasks
- goals
- decision_requests
- recommendations
- fatigue_checkins
- connectors
- reminders

### Memory Store

Stores:
- habits
- preferences
- patterns
- inferred behaviors

---

## 2.6 Connectors Layer

### Core connectors
- Google Calendar API
- Gmail API

### Responsibilities
- fetch events
- fetch emails
- normalize data
- provide context to system

---

## 2.7 Communication Layer

### Telegram Bot (MVP)

Responsibilities:
- receive messages
- send proactive notifications
- handle conversations

Future:
- WhatsApp
- mobile push notifications

---

## 2.8 Background Workers

Recommended: Redis + RQ

Responsibilities:
- run watchers
- monitor deadlines
- check job opportunities
- trigger proactive actions
- schedule tasks

---

## 3. Key System Flows

## 3.1 Onboarding Flow

1. User enters profile info
2. Connects calendar/email
3. Selects Telegram
4. Data stored in DB
5. Initial model created

---

## 3.2 Message Handling Flow

1. User sends message (Telegram)
2. API receives message
3. Orchestrator parses intent
4. Fetch context (calendar, tasks, memory)
5. Call decision engine
6. Return response
7. Store interaction

---

## 3.3 Proactive Suggestion Flow

1. Worker scans active tasks/goals
2. Scores execution windows
3. Detects opportunity
4. Generates recommendation
5. Sends via Telegram

---

## 3.4 Goal Management Flow

1. User defines goal
2. System asks follow-ups
3. Creates structured goal
4. Generates sub-tasks
5. Creates watcher jobs

---

## 4. Decision Engine Design

### Inputs
- fatigue score
- urgency
- deadlines
- available time
- user patterns

### Logic
- rule filtering (constraints)
- scoring (fit, urgency, risk)
- LLM reasoning

### Output schema
- primary action
- alternatives
- reasoning
- confidence
- schedule changes

---

## 5. Data Model (Simplified)

## Users
- id
- name
- preferences

## Tasks
- id
- user_id
- title
- deadline
- estimated_time
- status

## Goals
- id
- user_id
- description
- timeline
- status

## Memory
- id
- user_id
- type
- statement
- confidence

---

## 6. Watchers (Core Concept)

Watchers are background jobs.

Examples:
- deadline watcher
- job search watcher
- schedule overload watcher

Each watcher:
- runs periodically
- evaluates conditions
- triggers actions

---

## 7. Technology Stack

### Frontend
- Next.js (web dashboard)

### Backend
- FastAPI

### Database
- PostgreSQL (Supabase)

### Queue / Workers
- Redis + RQ

### LLM
- OpenAI (Responses API)

### Communication
- Telegram Bot API

---

## 8. Deployment

- Frontend → Vercel
- Backend → Railway / Render
- DB → Supabase
- Redis → managed Redis

---

## 9. Scaling Considerations

- separate workers for watchers
- cache frequent queries
- batch connector sync
- async processing for heavy tasks

---

## 10. Future Extensions

- voice interface
- mobile app
- more connectors
- advanced personalization
- agent-based workflows

---

## 11. Guiding Principle

System is not:
- a chatbot
- a reminder app

System is:
- a decision engine + context engine + timing engine
- delivered through a conversational interface