# Project Timeline (Epics & Stories)

## Overview
This document breaks the project into Epics and Stories for structured development.
Aligned with:
- Backend architecture
- API contract
- Workers & jobs
- Connectors and normalization
- Fatigue-aware decision system

---

# Epic 1: Core Backend Foundation

## Goal
Set up base backend structure and infrastructure.

### Stories
- Setup FastAPI project structure
- Setup environment config (.env, settings)
- Setup database (Supabase + PostgreSQL)
- Create base models and schema
- Setup Redis + RQ workers
- Setup logging and error handling

---

# Epic 2: Authentication & User Management

## Goal
Handle onboarding and user identity.

### Stories
- Implement Supabase Auth integration
- Create user profile table
- Build onboarding API
- Store user preferences (routine, goals)
- Setup secure token validation

---

# Epic 3: Task & Internal Calendar System

## Goal
Build internal planning system.

### Stories
- Create task model and CRUD APIs
- Build internal calendar table
- Implement scheduling logic
- Handle task acceptance/rejection
- Store rejection reasons

---

# Epic 4: Connectors & Data Ingestion

## Goal
Fetch and normalize external data.

### Stories
- Google Calendar connector
- Gmail connector
- Data normalization pipeline
- Store events and emails in DB
- Sync scheduler (background job)

---

# Epic 5: Memory & Learning System

## Goal
Store user behavior and patterns.

### Stories
- Setup vector store (pgvector)
- Store user interactions
- Store rejection patterns
- Build memory retrieval API
- Implement memory update jobs

---

# Epic 6: Fatigue Layer

## Goal
Model user fatigue and energy.

### Stories
- Create fatigue schema
- Weekly fatigue check-in system
- Time-block fatigue scoring
- Store fatigue history
- API to fetch fatigue state

---

# Epic 7: Decision Engine

## Goal
Core intelligence for recommendations.

### Stories
- Define decision input schema
- Implement rule-based filtering
- Add scoring system (urgency, fatigue)
- Integrate LLM reasoning
- Generate recommendations

---

# Epic 8: Orchestration Layer

## Goal
Coordinate system flow.

### Stories
- Build orchestrator service
- Context aggregation (tasks, calendar, memory)
- Intent detection
- Decision engine integration
- Response formatting

---

# Epic 9: Workers & Watchers

## Goal
Enable proactive system behavior.

### Stories
- Deadline watcher
- Schedule overload watcher
- Job/goal watcher
- Fatigue aggregation job
- Notification trigger jobs

---

# Epic 10: Notification & Communication Layer

## Goal
User interaction via external channels.

### Stories
- Telegram bot setup
- Message receive/send API
- Notification system
- Reminder system
- Retry/failure handling

---

# Epic 11: API Layer Completion

## Goal
Expose all backend capabilities.

### Stories
- Task APIs
- Connector APIs
- Decision APIs
- Memory APIs
- Fatigue APIs

---

# Epic 12: End-to-End Flow Integration

## Goal
Make system fully functional.

### Stories
- Onboarding → data storage flow
- Connector sync → DB → memory flow
- Message → orchestrator → decision flow
- Worker → notification flow
- Full system testing

---

# Epic 13: Optimization & Scaling

## Goal
Improve performance and reliability.

### Stories
- Add caching (Redis)
- Optimize DB queries
- Batch connector sync
- Improve worker parallelism
- Add monitoring (logs, metrics)

---

# Suggested Execution Order

1. Epic 1 → Foundation
2. Epic 2 → Auth
3. Epic 3 → Tasks & Calendar
4. Epic 4 → Connectors
5. Epic 5 → Memory
6. Epic 6 → Fatigue
7. Epic 7 → Decision Engine
8. Epic 8 → Orchestrator
9. Epic 9 → Workers
10. Epic 10 → Communication
11. Epic 11 → API Completion
12. Epic 12 → Integration
13. Epic 13 → Optimization

---

# MVP Cut (Hackathon)

Focus on:
- Epic 1, 2, 3, 4
- Basic Epic 7 (Decision)
- Basic Epic 9 (1 watcher)
- Epic 10 (Telegram only)

