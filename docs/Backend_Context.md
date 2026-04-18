# Backend Context - Fatigue-Aware Personal Assistant

Last updated: April 18, 2026

## 1. Purpose

This document defines the backend structure for the Fatigue-Aware Personal Assistant.

The goal of the backend is not only to expose APIs. It is the operational system behind the product. It stores user state, syncs external context, powers the internal planning layer, supports fatigue-aware decisions, runs proactive jobs, and records learning signals over time.

This backend follows the product split already established in the project:

### Phase 1 - Future Task Engine
- internal calendar driven
- proactive
- planner and scheduler based
- reminder and watcher based

### Phase 2 - In-Prompt Decision Engine
- real-time user questions
- uses long-term memory
- uses fatigue layer
- adapts recommendation style based on likely user bandwidth

This file focuses on **what each backend file is for**. It does not include implementation code.

---

## 2. Backend Design Principles

### Keep operational truth separate from reasoning
The database and services store facts such as users, tasks, calendar blocks, feedback, connectors, fatigue inputs, notifications, and learned memories. The reasoning layer uses those facts, but does not replace them.

### Keep connectors separate from internal product state
Google Calendar and Gmail provide external context. They should not directly overwrite internal planning state. Connector data should be fetched, normalized, and then interpreted by the system.

### Keep route handlers thin
API routes should validate requests, call service methods, and return clean responses. Business logic should live in services, not inside route handlers.

### Keep domain logic modular
Each major product area should have its own service and repository so the backend remains understandable and easy to extend.

### Keep background work off the request path
Syncing connectors, aggregating fatigue patterns, memory distillation, notification delivery, and watcher scans should run through workers.

### Keep learning structured
Raw interaction history, explicit fatigue input, and feedback should be stored first. Distilled memory and fatigue summaries should be created from those signals later.

---

## 3. What the Backend Must Do

The backend is responsible for:

- user identity and profile state
- onboarding and stable user preferences
- connector management and sync health
- task creation and lifecycle management
- internal calendar suggestions and confirmations
- feedback capture when users accept, reject, snooze, or move suggestions
- explicit fatigue check-ins and derived fatigue patterns
- long-term learned memory
- decision-time context aggregation
- proactive notifications and reminders
- watcher jobs for deadlines, overload, and future opportunities
- event logging for learning, analytics, and debugging

---

## 4. Recommended Backend Shape

The backend should be organized as a modular FastAPI system with these domains:

- Auth and user context
- Connectors
- Normalization
- Tasks
- Internal calendar
- Fatigue
- Memory
- Notifications
- Decision and orchestration
- Worker jobs

Recommended stack:

- FastAPI
- Supabase PostgreSQL
- pgvector
- SQLAlchemy or SQLModel
- Alembic
- Redis
- RQ workers
- Pydantic schemas

Request flow should follow this path:

**API routes -> services -> repositories and connectors -> database or workers**

Not this:

**API routes -> direct database access + direct LLM calls + direct connector logic**

---

## 5. High-Level Folder Structure

```text
backend/
  app/
    main.py
    core/
      config.py
      security.py
      db.py
      logging.py
    api/
      routes/
        auth.py
        users.py
        connectors.py
        tasks.py
        internal_calendar.py
        fatigue.py
        notifications.py
        decisions.py
    schemas/
      auth.py
      user.py
      connector.py
      task.py
      internal_calendar.py
      fatigue.py
      notification.py
      decision.py
    models/
      user.py
      connector.py
      task.py
      internal_calendar.py
      fatigue.py
      memory.py
      notification.py
    services/
      user_service.py
      connector_service.py
      task_service.py
      internal_calendar_service.py
      fatigue_service.py
      memory_service.py
      notification_service.py
      decision_service.py
    connectors/
      base.py
      gmail_connector.py
      google_calendar_connector.py
      normalizers/
        gmail.py
        google_calendar.py
    repositories/
      users.py
      connectors.py
      tasks.py
      internal_calendar.py
      fatigue.py
      memories.py
      notifications.py
    workers/
      jobs/
        connector_sync.py
        fatigue_aggregation.py
        memory_distillation.py
        scheduling.py
        notifications.py
```

---

## 6. What Each Folder Is About

## `app/`
This is the main backend application package. It contains the API, service layer, database-facing components, connector adapters, and worker jobs.

## `app/core/`
Shared application foundations such as configuration, security rules, database setup, and logging behavior.

## `app/api/routes/`
HTTP endpoints exposed by FastAPI. Each file groups routes by domain.

## `app/schemas/`
Request and response shapes used by the API and service layer. These define how data moves through the backend in a validated way.

## `app/models/`
Database entity definitions that map backend concepts to stored tables.

## `app/services/`
Business logic layer. Services coordinate repositories, connectors, and worker triggers.

## `app/connectors/`
Provider-specific adapters for external systems like Gmail and Google Calendar.

## `app/connectors/normalizers/`
Transforms provider-specific payloads into the product’s internal shape before they are used elsewhere.

## `app/repositories/`
Database access layer. Repositories perform reads and writes for each domain and keep SQL and persistence logic out of services.

## `app/workers/jobs/`
Background jobs triggered asynchronously for sync, scheduling, fatigue aggregation, notifications, and memory updates.

---

## 7. What Each Core File Is About

## 7.1 App Entry

### `main.py`
Starts the FastAPI application.

What it is about:
- creating the API app
- loading settings
- registering routes
- wiring middleware
- health check and startup behavior

This file should stay small. It should not contain domain logic.

---

## 7.2 Core Files

### `core/config.py`
Application configuration and environment loading.

What it is about:
- database URL
- Supabase keys
- Redis connection
- connector credentials
- token settings
- environment flags
- feature toggles

### `core/security.py`
Authentication and authorization helpers.

What it is about:
- validating user identity
- session and token handling
- route protection helpers
- role or ownership checks if needed later

### `core/db.py`
Database connection and session management.

What it is about:
- database engine setup
- session creation
- transaction helpers
- shared DB lifecycle wiring

### `core/logging.py`
Central logging behavior.

What it is about:
- structured logs
- request logging
- worker logging format
- error logging conventions
- trace and correlation ids later if needed

---

## 7.3 Route Files

### `api/routes/auth.py`
Authentication-related endpoints.

What it is about:
- syncing authenticated user state into the backend
- creating internal user records after auth
- session-related backend hooks

### `api/routes/users.py`
User profile and preference endpoints.

What it is about:
- reading current user details
- updating preferences
- updating onboarding state
- managing stable profile information

### `api/routes/connectors.py`
Connector lifecycle endpoints.

What it is about:
- connecting Gmail or Google Calendar
- disconnecting connectors
- listing connector status
- triggering sync jobs
- viewing sync health

### `api/routes/tasks.py`
Task endpoints.

What it is about:
- creating tasks
- listing tasks
- reading task details
- updating task attributes
- completing, archiving, or skipping tasks

### `api/routes/internal_calendar.py`
Internal calendar endpoints.

What it is about:
- generating suggested calendar blocks
- listing blocks
- confirming suggestions
- rejecting blocks
- rescheduling blocks
- marking blocks done or missed

### `api/routes/fatigue.py`
Fatigue-related endpoints.

What it is about:
- recording explicit fatigue check-ins
- reading check-in history
- exposing derived fatigue patterns
- optionally letting UI ask for fatigue state when confidence is low

### `api/routes/notifications.py`
Notification endpoints.

What it is about:
- listing notifications
- testing delivery
- dismissing notifications
- reviewing notification state

### `api/routes/decisions.py`
Decision and orchestration endpoints.

What it is about:
- processing real-time user decision questions
- planning a day
- returning next-best-action suggestions
- invoking orchestration with context, fatigue, tasks, and memory

This route group should be added after the operational base is stable.

---

## 7.4 Schema Files

### `schemas/auth.py`
Validated request and response shapes for auth-related flows.

What it is about:
- session sync request
- auth-linked user response
- auth status objects

### `schemas/user.py`
Validated shapes for user profile and preference flows.

What it is about:
- profile response
- update preferences request
- onboarding completion payload

### `schemas/connector.py`
Validated shapes for connector operations.

What it is about:
- connector status response
- connect request metadata
- sync trigger response
- disconnect confirmation

### `schemas/task.py`
Validated shapes for task operations.

What it is about:
- create task request
- update task request
- task list response
- task detail response

### `schemas/internal_calendar.py`
Validated shapes for internal calendar operations.

What it is about:
- suggested block response
- confirm or reject request
- reschedule request
- internal calendar listing model

### `schemas/fatigue.py`
Validated shapes for fatigue flows.

What it is about:
- check-in create request
- check-in history response
- fatigue pattern response

### `schemas/notification.py`
Validated shapes for notification flows.

What it is about:
- notification listing
- dismiss action response
- delivery status payload

### `schemas/decision.py`
Validated shapes for decision outputs.

What it is about:
- decision query request
- decision response
- recommendation payload
- alternatives and confidence fields
- schedule change suggestions

---

## 7.5 Model Files

### `models/user.py`
Database entities for user identity and preferences.

What it is about:
- `users`
- `user_preferences`

### `models/connector.py`
Database entities for connector state.

What it is about:
- `connectors`
- later possibly connector sync run tables or external item tracking

### `models/task.py`
Database entities for user tasks.

What it is about:
- `tasks`

### `models/internal_calendar.py`
Database entities for assistant-owned planning state.

What it is about:
- `internal_calendar`
- `calendar_feedback`

### `models/fatigue.py`
Database entities for raw and derived fatigue state.

What it is about:
- `fatigue_checkins`
- `fatigue_patterns`

### `models/memory.py`
Database entities for learning state.

What it is about:
- `learned_memories`
- `interaction_events`

### `models/notification.py`
Database entities for reminder and delivery state.

What it is about:
- `notifications`

---

## 7.6 Service Files

### `services/user_service.py`
Owns user profile and preference logic.

What it is about:
- creating internal user state
- reading profile information
- updating onboarding preferences
- exposing reusable user context to other services

### `services/connector_service.py`
Owns connector lifecycle and sync coordination.

What it is about:
- saving connector account state
- starting sync jobs
- handling token refresh needs
- reporting sync health
- routing provider-specific operations to the correct connector adapter

### `services/task_service.py`
Owns task logic.

What it is about:
- task CRUD
- priority updates
- due date management
- status transitions
- preparing task context for scheduling and decisioning

### `services/internal_calendar_service.py`
Owns assistant scheduling logic.

What it is about:
- suggesting work blocks
- confirming and rejecting blocks
- rescheduling blocks
- updating planning state when a task is completed or missed
- keeping internal planning separate from external calendar data

This is one of the most important services in the backend.

### `services/fatigue_service.py`
Owns explicit and derived fatigue state.

What it is about:
- saving fatigue check-ins
- retrieving recent fatigue signals
- exposing fatigue priors by time bucket
- helping the decision layer choose whether to ask the user for fresh fatigue input

### `services/memory_service.py`
Owns long-term learning state.

What it is about:
- storing distilled memories
- retrieving relevant memories for planning and decisioning
- deciding when a pattern is strong enough to persist
- keeping raw events separate from durable memory

### `services/notification_service.py`
Owns proactive communication state.

What it is about:
- scheduling reminders
- preparing outgoing notification records
- marking notifications sent, failed, clicked, or dismissed
- supporting Telegram and future channels

### `services/decision_service.py`
Owns the in-prompt decision workflow.

What it is about:
- collecting structured context
- loading fatigue signals
- loading relevant memories
- combining tasks, deadlines, and calendar context
- generating next-step recommendations
- returning outputs in the right style based on bandwidth and confidence

This service should reason over facts. It should not be the source of truth itself.

---

## 7.7 Connector Files

### `connectors/base.py`
Shared interface and rules for all connector adapters.

What it is about:
- common connector contract
- shared sync behavior shape
- provider-independent helper behavior

### `connectors/gmail_connector.py`
Gmail adapter.

What it is about:
- fetching relevant email data
- reading message-level context needed by the system
- returning raw or semi-structured email signals for normalization

Important note:
This connector should provide context. It should not directly create product tasks without service-layer interpretation.

### `connectors/google_calendar_connector.py`
Google Calendar adapter.

What it is about:
- fetching upcoming calendar events
- reading availability windows
- reading external event data needed for planning
- optionally syncing confirmed internal blocks outward later

---

## 7.8 Normalizer Files

### `connectors/normalizers/gmail.py`
Normalization rules for Gmail data.

What it is about:
- mapping email payloads into internal candidate shapes
- extracting signals that may later become obligations, reminders, or task candidates
- standardizing fields before they reach services

### `connectors/normalizers/google_calendar.py`
Normalization rules for Google Calendar data.

What it is about:
- mapping provider event data into the internal event shape
- standardizing timestamps, participants, titles, and metadata
- preparing availability context for the planning layer

Normalization should happen before connector data is used by the rest of the system.

---

## 7.9 Repository Files

### `repositories/users.py`
Database access for user and preference state.

What it is about:
- create, read, and update user records
- fetch stable profile context

### `repositories/connectors.py`
Database access for connector records.

What it is about:
- save connector metadata
- update token expiry or sync timestamps
- read connector status by provider

### `repositories/tasks.py`
Database access for tasks.

What it is about:
- create and query tasks
- list active and overdue tasks
- update task status and schedule-related metadata

### `repositories/internal_calendar.py`
Database access for internal planning state.

What it is about:
- store blocks
- fetch future blocks
- update block status
- save feedback against suggestions

### `repositories/fatigue.py`
Database access for fatigue state.

What it is about:
- insert fatigue check-ins
- fetch recent check-ins
- read and write aggregated fatigue patterns

### `repositories/memories.py`
Database access for learning state.

What it is about:
- insert learned memories
- query relevant memories
- store raw interaction events
- later support vector search and filtering

### `repositories/notifications.py`
Database access for notifications.

What it is about:
- create queued notifications
- fetch pending reminders
- update delivery status

---

## 7.10 Worker Job Files

### `workers/jobs/connector_sync.py`
Background connector sync jobs.

What it is about:
- pulling external data from Gmail and Google Calendar
- saving sync state
- handing normalized results to the right service path
- keeping connector work off the request path

### `workers/jobs/fatigue_aggregation.py`
Background fatigue summary jobs.

What it is about:
- aggregating explicit fatigue check-ins into time-bucket patterns
- updating `fatigue_patterns`
- refreshing confidence and trend direction

### `workers/jobs/memory_distillation.py`
Background learning jobs.

What it is about:
- reading raw behavior and feedback signals
- identifying repeated patterns
- writing durable learned memories only when confidence is strong enough

### `workers/jobs/scheduling.py`
Background scheduling and watcher jobs.

What it is about:
- scanning future tasks
- detecting deadline risk
- identifying overload windows
- generating suggested internal calendar blocks
- supporting proactive recommendation flow

### `workers/jobs/notifications.py`
Background notification delivery jobs.

What it is about:
- sending queued reminders
- retrying failures if needed
- updating delivery state
- supporting channel-specific delivery behavior

---

## 8. Domain-by-Domain Backend Meaning

## Auth and User Context
This domain establishes the internal user record and stores stable preferences collected during onboarding. It supports timezone, routine, work windows, style preferences, reminder tolerance, and fatigue prompt settings.

Main files:
- `api/routes/auth.py`
- `api/routes/users.py`
- `schemas/auth.py`
- `schemas/user.py`
- `models/user.py`
- `services/user_service.py`
- `repositories/users.py`

## Connectors
This domain manages Gmail and Google Calendar connections, tracks connector health, refresh state, and last sync behavior, and routes provider-specific work to the correct adapter.

Main files:
- `api/routes/connectors.py`
- `schemas/connector.py`
- `models/connector.py`
- `services/connector_service.py`
- `connectors/base.py`
- `connectors/gmail_connector.py`
- `connectors/google_calendar_connector.py`
- `connectors/normalizers/gmail.py`
- `connectors/normalizers/google_calendar.py`
- `repositories/connectors.py`
- `workers/jobs/connector_sync.py`

## Tasks
This domain manages the actual work the user needs to do. Tasks are the source of truth for obligations, deadlines, priorities, and effort estimates.

Main files:
- `api/routes/tasks.py`
- `schemas/task.py`
- `models/task.py`
- `services/task_service.py`
- `repositories/tasks.py`

## Internal Calendar
This domain is the assistant-owned planning layer. It holds suggested and confirmed schedule blocks. It is separate from external calendar data and is one of the core product layers.

Main files:
- `api/routes/internal_calendar.py`
- `schemas/internal_calendar.py`
- `models/internal_calendar.py`
- `services/internal_calendar_service.py`
- `repositories/internal_calendar.py`
- `workers/jobs/scheduling.py`

## Fatigue
This domain stores explicit fatigue check-ins and derived fatigue patterns by time bucket. It supports both future planning and in-prompt decisioning.

Main files:
- `api/routes/fatigue.py`
- `schemas/fatigue.py`
- `models/fatigue.py`
- `services/fatigue_service.py`
- `repositories/fatigue.py`
- `workers/jobs/fatigue_aggregation.py`

## Memory
This domain stores long-term learned patterns and the raw interaction events that power future learning.

Main files:
- `models/memory.py`
- `services/memory_service.py`
- `repositories/memories.py`
- `workers/jobs/memory_distillation.py`

## Notifications
This domain stores proactive messages, reminders, and delivery state. It supports Telegram first and can later support web and email.

Main files:
- `api/routes/notifications.py`
- `schemas/notification.py`
- `models/notification.py`
- `services/notification_service.py`
- `repositories/notifications.py`
- `workers/jobs/notifications.py`

## Decisions and Orchestration
This domain answers in-prompt user questions using tasks, fatigue, calendar context, memory, and rules. It should sit on top of stable operational state.

Main files:
- `api/routes/decisions.py`
- `schemas/decision.py`
- `services/decision_service.py`

---

## 9. How Data Should Flow Through the Backend

## Google Calendar flow
1. Connector reads upcoming events and availability.
2. Normalizer maps provider payload into the internal event shape.
3. Service decides how that context is used.
4. Internal planning uses this data to avoid conflicts and score suggested task blocks.
5. Confirmed internal blocks may later be synced outward if the product supports it.

## Gmail flow
1. Connector reads relevant email signals.
2. Normalizer transforms them into internal candidate objects.
3. Service evaluates whether they represent obligations, deadlines, or useful context.
4. The system may create task candidates or pass them into orchestration.
5. Raw external data should not directly become product truth without interpretation.

## Planning flow
1. Task state is read.
2. External availability is checked.
3. Fatigue and learned memory are applied.
4. Scheduling worker proposes internal calendar blocks.
5. User confirms, rejects, moves, or ignores suggestions.
6. Feedback is stored for future learning.

## In-prompt decision flow
1. User asks a real-time question.
2. Decision service loads user profile, tasks, internal calendar, fatigue signals, and learned memories.
3. Missing critical fields are identified.
4. Recommendation is generated in the right style for the user’s likely bandwidth.
5. If needed, schedule changes or reminders are triggered.
6. Interaction is logged for future learning.

---

## 10. API Areas to Build First

Build the backend in this order:

### First group - operational base
- auth and user sync
- preferences and onboarding state
- connectors and sync triggers
- task CRUD
- internal calendar CRUD and feedback
- notifications

### Second group - intelligence support
- fatigue check-ins
- fatigue pattern reading
- memory retrieval and distillation pipeline

### Third group - orchestration
- decision query
- plan-day flow
- next-best-action flow

This order matters because the system needs clean operational state before it can make reliable intelligent decisions.

---

## 11. Recommended Later Additions

Two additional backend file areas will likely be useful later:

### Connector sync audit support
Potential files:
- `models/connector_sync.py`
- `repositories/connector_sync.py`

What they would be about:
- sync runs
- status per fetch cycle
- success and failure visibility
- duplicate handling and idempotency

### External item storage
Potential files:
- `models/external_items.py`
- `repositories/external_items.py`

What they would be about:
- storing normalized external records separately from product truth
- deduplication
- replayable processing
- debugging normalization outcomes

These are useful when connector complexity grows.

---

## 12. Final Backend Mental Model

This backend is not just an API server.

It is:

- a source of truth for user state
- a connector ingestion system
- an assistant-owned planning system
- a fatigue-aware context engine
- a memory and learning system
- a proactive notification engine
- a worker-based orchestration system

That is the correct backend shape for this product.

It matches the PRD, the architecture, the fatigue-aware decision model, and the current database design. It also keeps the product extensible without turning the backend into one large and hard-to-maintain agent service.
