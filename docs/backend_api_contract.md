# Backend API Contract - Fatigue-Aware Personal Assistant

Last updated: April 18, 2026

## 1. Purpose

This document defines the first backend API contract for the Fatigue-Aware Personal Assistant.

It is designed to match the current backend structure, product phases, and database schema already defined for the project.

This file focuses on:
- which endpoints exist
- what each endpoint is for
- request and response contract shape
- which service owns the endpoint
- which tables are affected
- what should happen synchronously vs asynchronously

This is an API contract document only. It does not include code.

---

## 2. Guiding API Principles

### Thin API layer
Routes should validate input, call the service layer, and return clean response objects. Routes should not contain scheduling logic, connector logic, or memory reasoning.

### Internal state is the source of truth
The API should treat internal tables such as tasks, internal calendar, fatigue check-ins, notifications, and learned memory as product state. External connectors provide context, not automatic truth.

### Connector payloads must be normalized
Connector APIs should not write random provider payloads into product-facing tables. Provider data should be fetched, normalized, and then either stored as sync metadata or passed into downstream logic.

### Background jobs for heavy or repeated work
Connector sync, fatigue aggregation, memory distillation, watcher scans, and reminder delivery should be queued as worker jobs, not handled inside request threads.

### Contract-first design
All request and response bodies should have stable schemas so the frontend, bot layer, and workers can rely on predictable behavior.

---

## 3. Product Phases Mapped to APIs

## Phase 1 - Future Task Engine
Primary API areas:
- user profile and onboarding
- connectors
- tasks
- internal calendar
- calendar feedback
- notifications

## Phase 2 - In-Prompt Decision Engine
Primary API areas:
- fatigue
- memory retrieval inputs
- decision/orchestration
- interaction logging

---

## 4. API Conventions

### Base path
Recommended base path:

```text
/api/v1
```

### Authentication
Recommended pattern:
- client authenticates with Supabase auth
- backend receives bearer token
- backend resolves internal `users.id` from `auth_user_id`

### Response envelope
Use a consistent response shape:

```json
{
  "success": true,
  "data": {},
  "message": "optional human-readable summary",
  "meta": {}
}
```

### Error envelope

```json
{
  "success": false,
  "error": {
    "code": "string_code",
    "message": "Human readable error",
    "details": {}
  }
}
```

### Pagination
For list endpoints:

```json
{
  "success": true,
  "data": {
    "items": [],
    "next_cursor": "optional_cursor"
  },
  "meta": {
    "count": 20
  }
}
```

### Timestamps
All timestamps should be ISO 8601 UTC in API contracts.

---

## 5. Core Shared Resource Shapes

## 5.1 User

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Aryan Pandit",
  "timezone": "America/Los_Angeles",
  "created_at": "2026-04-18T18:00:00Z",
  "updated_at": "2026-04-18T18:00:00Z"
}
```

## 5.2 User Preferences

```json
{
  "user_id": "uuid",
  "sleep_time": "23:30:00",
  "wake_time": "07:30:00",
  "work_start_time": "09:00:00",
  "work_end_time": "17:00:00",
  "work_days": [1,2,3,4,5],
  "preferred_response_style": "direct",
  "decision_style_default": "guided",
  "reminder_tolerance": "medium",
  "fatigue_prompt_enabled": true,
  "onboarding_completed": true,
  "profile_json": {}
}
```

## 5.3 Connector

```json
{
  "id": "uuid",
  "provider": "gmail",
  "account_email": "user@example.com",
  "status": "connected",
  "last_sync_at": "2026-04-18T16:00:00Z",
  "token_expires_at": "2026-04-18T20:00:00Z",
  "metadata_json": {}
}
```

## 5.4 Task

```json
{
  "id": "uuid",
  "title": "Finish assignment A",
  "description": "Database schema review",
  "priority": 4,
  "estimated_minutes": 60,
  "actual_minutes": null,
  "energy_required": 4,
  "due_at": "2026-04-19T08:00:00Z",
  "status": "pending",
  "source": "user",
  "metadata_json": {},
  "created_at": "2026-04-18T18:00:00Z",
  "updated_at": "2026-04-18T18:00:00Z",
  "completed_at": null
}
```

## 5.5 Internal Calendar Block

```json
{
  "id": "uuid",
  "task_id": "uuid",
  "title": "Focus - Finish assignment A",
  "block_type": "focus_block",
  "starts_at": "2026-04-19T01:00:00Z",
  "ends_at": "2026-04-19T02:00:00Z",
  "status": "suggested",
  "sync_to_google": false,
  "external_event_id": null,
  "source": "system",
  "reason_summary": "Fits available time window and deadline risk",
  "reschedule_count": 0,
  "priority_snapshot": 4,
  "energy_snapshot": 4,
  "metadata_json": {},
  "confirmed_at": null,
  "rejected_at": null,
  "completed_at": null
}
```

## 5.6 Fatigue Check-in

```json
{
  "id": "uuid",
  "score": 4,
  "source": "user",
  "notes": "Very tired after class",
  "context_json": {},
  "created_at": "2026-04-18T18:00:00Z"
}
```

## 5.7 Fatigue Pattern

```json
{
  "id": "uuid",
  "weekday": 5,
  "time_bucket": "evening",
  "avg_fatigue": 3.8,
  "min_fatigue": 2.0,
  "max_fatigue": 5.0,
  "fatigue_variance": 0.9,
  "sample_count": 10,
  "confidence": 0.82,
  "trend_direction": "stable",
  "last_signal_at": "2026-04-17T19:30:00Z",
  "last_computed_at": "2026-04-18T18:00:00Z",
  "metadata_json": {}
}
```

## 5.8 Notification

```json
{
  "id": "uuid",
  "channel": "telegram",
  "title": "Start now",
  "body": "This is a good time to work on assignment A.",
  "scheduled_for": "2026-04-18T19:00:00Z",
  "sent_at": null,
  "status": "queued",
  "provider_message_id": null,
  "metadata_json": {}
}
```

---

## 6. Auth and User APIs

Owner service:
- `user_service.py`

Tables:
- `users`
- `user_preferences`

## 6.1 Sync session

### `POST /api/v1/auth/session/sync`

Purpose:
- create or update the internal user record after external auth
- map auth identity to product user
- return user + preferences snapshot

Request:

```json
{
  "auth_user_id": "uuid",
  "email": "user@example.com",
  "full_name": "Aryan Pandit",
  "timezone": "America/Los_Angeles"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "user": {},
    "preferences": {}
  }
}
```

Behavior:
- synchronous
- upsert `users`
- create empty `user_preferences` if missing

## 6.2 Get current user

### `GET /api/v1/me`

Purpose:
- return the authenticated user's profile snapshot

Response:

```json
{
  "success": true,
  "data": {
    "user": {},
    "preferences": {}
  }
}
```

## 6.3 Update user preferences

### `PATCH /api/v1/me/preferences`

Purpose:
- update onboarding and stable preference data

Request:

```json
{
  "sleep_time": "23:30:00",
  "wake_time": "07:30:00",
  "work_start_time": "09:00:00",
  "work_end_time": "17:00:00",
  "work_days": [1,2,3,4,5],
  "preferred_response_style": "direct",
  "decision_style_default": "guided",
  "reminder_tolerance": "medium",
  "fatigue_prompt_enabled": true,
  "onboarding_completed": true,
  "profile_json": {
    "student": true,
    "class_days": [1,3,5]
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "preferences": {}
  }
}
```

---

## 7. Connector APIs

Owner service:
- `connector_service.py`

Tables:
- `connectors`
- optionally `interaction_events`

Connectors supported now:
- Gmail
- Google Calendar

## 7.1 List connectors

### `GET /api/v1/connectors`

Purpose:
- return all connector accounts and sync health for the user

Response:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "provider": "gmail",
        "status": "connected"
      }
    ]
  }
}
```

## 7.2 Connect Google Calendar

### `POST /api/v1/connectors/google-calendar/connect`

Purpose:
- register a Google Calendar connector after OAuth completes

Request:

```json
{
  "account_email": "user@example.com",
  "access_token": "encrypted-or-server-side-exchanged-token",
  "refresh_token": "encrypted-or-server-side-exchanged-token",
  "token_expires_at": "2026-04-18T20:00:00Z",
  "metadata_json": {}
}
```

Response:

```json
{
  "success": true,
  "data": {
    "connector": {}
  }
}
```

## 7.3 Connect Gmail

### `POST /api/v1/connectors/gmail/connect`

Purpose:
- register a Gmail connector after OAuth completes

Request shape:
- same structure as Google Calendar connect

Response:
- same structure as Google Calendar connect

## 7.4 Trigger connector sync

### `POST /api/v1/connectors/{connector_id}/sync`

Purpose:
- queue a sync job for a connector
- return accepted job status immediately

Request:

```json
{
  "sync_mode": "incremental",
  "lookahead_days": 14,
  "force": false
}
```

Response:

```json
{
  "success": true,
  "data": {
    "connector_id": "uuid",
    "job_type": "connector_sync",
    "job_status": "queued"
  }
}
```

Behavior:
- asynchronous
- creates worker job
- updates sync metadata later
- should log event to `interaction_events`

## 7.5 Disconnect connector

### `POST /api/v1/connectors/{connector_id}/disconnect`

Purpose:
- revoke connector from product usage
- mark status as revoked or disconnected state

Request:

```json
{
  "reason": "user_requested"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "connector_id": "uuid",
    "status": "revoked"
  }
}
```

---

## 8. Task APIs

Owner service:
- `task_service.py`

Tables:
- `tasks`
- optionally `interaction_events`

## 8.1 Create task

### `POST /api/v1/tasks`

Purpose:
- create a new user task

Request:

```json
{
  "title": "Finish assignment A",
  "description": "Review the backend schema and submit notes",
  "priority": 4,
  "estimated_minutes": 60,
  "energy_required": 4,
  "due_at": "2026-04-19T08:00:00Z",
  "source": "user",
  "metadata_json": {}
}
```

Response:

```json
{
  "success": true,
  "data": {
    "task": {}
  }
}
```

## 8.2 List tasks

### `GET /api/v1/tasks`

Recommended query params:
- `status`
- `due_before`
- `due_after`
- `cursor`
- `limit`

Purpose:
- list tasks for dashboard, planner, or bot flows

Response:

```json
{
  "success": true,
  "data": {
    "items": []
  },
  "meta": {
    "count": 20,
    "next_cursor": null
  }
}
```

## 8.3 Get task detail

### `GET /api/v1/tasks/{task_id}`

Purpose:
- fetch one task and related planning summary

Response:

```json
{
  "success": true,
  "data": {
    "task": {},
    "calendar_blocks": []
  }
}
```

## 8.4 Update task

### `PATCH /api/v1/tasks/{task_id}`

Purpose:
- update task metadata and lifecycle state

Request:

```json
{
  "title": "Finish assignment A",
  "priority": 5,
  "estimated_minutes": 75,
  "due_at": "2026-04-19T09:00:00Z",
  "status": "scheduled"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "task": {}
  }
}
```

## 8.5 Complete task

### `POST /api/v1/tasks/{task_id}/complete`

Purpose:
- mark task as done
- record actual duration if supplied

Request:

```json
{
  "actual_minutes": 55,
  "completed_at": "2026-04-18T21:00:00Z"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "task": {}
  }
}
```

Behavior:
- synchronous update to `tasks`
- should log `task_completed` in `interaction_events`

---

## 9. Internal Calendar APIs

Owner service:
- `internal_calendar_service.py`

Tables:
- `internal_calendar`
- `calendar_feedback`
- `tasks`
- optionally `notifications`
- optionally `interaction_events`

## 9.1 Suggest internal calendar blocks

### `POST /api/v1/internal-calendar/suggest`

Purpose:
- generate assistant-owned schedule suggestions from tasks, availability, fatigue priors, and calendar context

Request:

```json
{
  "task_ids": ["uuid"],
  "window_start": "2026-04-18T18:00:00Z",
  "window_end": "2026-04-25T18:00:00Z",
  "max_suggestions": 5,
  "sync_to_google_default": false
}
```

Response:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "Focus - Finish assignment A",
        "status": "suggested"
      }
    ]
  }
}
```

Behavior:
- can be synchronous for simple MVP suggestion generation
- may later queue heavier planning jobs

## 9.2 List internal calendar blocks

### `GET /api/v1/internal-calendar`

Recommended query params:
- `start`
- `end`
- `status`
- `task_id`

Purpose:
- return the assistant-owned schedule view

Response:

```json
{
  "success": true,
  "data": {
    "items": []
  }
}
```

## 9.3 Get calendar block detail

### `GET /api/v1/internal-calendar/{block_id}`

Purpose:
- fetch one block and its feedback history

Response:

```json
{
  "success": true,
  "data": {
    "block": {},
    "feedback": []
  }
}
```

## 9.4 Confirm calendar block

### `POST /api/v1/internal-calendar/{block_id}/confirm`

Purpose:
- mark suggested block as accepted by the user
- optionally mark for Google sync

Request:

```json
{
  "sync_to_google": true,
  "fatigue_score": 2,
  "reason_text": "This time works"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "block": {},
    "feedback_recorded": true
  }
}
```

Behavior:
- update `internal_calendar.status` to `confirmed`
- write `calendar_feedback` with `accepted`
- optionally queue Google sync job
- log interaction event

## 9.5 Reject calendar block

### `POST /api/v1/internal-calendar/{block_id}/reject`

Purpose:
- record rejection and reason

Request:

```json
{
  "reason_code": "too_tired",
  "reason_text": "I cannot do deep work at that time",
  "fatigue_score": 4
}
```

Response:

```json
{
  "success": true,
  "data": {
    "block": {},
    "feedback_recorded": true
  }
}
```

Behavior:
- update `internal_calendar.status` to `rejected`
- insert `calendar_feedback`
- log interaction event
- later becomes input for memory distillation

## 9.6 Reschedule calendar block

### `POST /api/v1/internal-calendar/{block_id}/reschedule`

Purpose:
- move a block to a different time or ask system to find another slot

Request:

```json
{
  "new_starts_at": "2026-04-19T03:00:00Z",
  "new_ends_at": "2026-04-19T04:00:00Z",
  "reason_code": "busy_at_that_time",
  "reason_text": "Class conflict"
}
```

Alternative request for system-driven reschedule:

```json
{
  "auto_find_new_slot": true,
  "reason_code": "different_time",
  "fatigue_score": 3
}
```

Response:

```json
{
  "success": true,
  "data": {
    "block": {}
  }
}
```

## 9.7 Mark block complete

### `POST /api/v1/internal-calendar/{block_id}/complete`

Purpose:
- mark a work block as done
- optionally also complete task if fully finished

Request:

```json
{
  "task_completed": false,
  "notes": "Finished first half"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "block": {},
    "task": null
  }
}
```

---

## 10. Calendar Feedback API

Owner service:
- `internal_calendar_service.py`

Tables:
- `calendar_feedback`

This can be covered by the confirm, reject, and reschedule endpoints above. A standalone endpoint is still useful when feedback is submitted separately.

## 10.1 Create feedback record

### `POST /api/v1/calendar-feedback`

Purpose:
- store calendar suggestion feedback independently of status transitions when needed

Request:

```json
{
  "calendar_block_id": "uuid",
  "response_type": "snoozed",
  "reason_code": "too_long",
  "reason_text": "Need a shorter block",
  "fatigue_score": 3
}
```

Response:

```json
{
  "success": true,
  "data": {
    "feedback": {}
  }
}
```

---

## 11. Fatigue APIs

Owner service:
- `fatigue_service.py`

Tables:
- `fatigue_checkins`
- `fatigue_patterns`
- optionally `interaction_events`

## 11.1 Create fatigue check-in

### `POST /api/v1/fatigue/checkins`

Purpose:
- store explicit fatigue input from the user

Request:

```json
{
  "score": 4,
  "source": "user",
  "notes": "Very tired after class",
  "context_json": {
    "trigger": "decision_query"
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "checkin": {}
  }
}
```

Behavior:
- synchronous insert
- should log an interaction event
- can optionally queue aggregation refresh

## 11.2 List fatigue check-ins

### `GET /api/v1/fatigue/checkins`

Recommended query params:
- `start`
- `end`
- `limit`

Response:

```json
{
  "success": true,
  "data": {
    "items": []
  }
}
```

## 11.3 Get fatigue patterns

### `GET /api/v1/fatigue/patterns`

Recommended query params:
- `weekday`
- `time_bucket`

Purpose:
- return derived fatigue priors by time bucket

Response:

```json
{
  "success": true,
  "data": {
    "items": []
  }
}
```

## 11.4 Recompute fatigue patterns

### `POST /api/v1/fatigue/patterns/recompute`

Purpose:
- queue pattern aggregation job

Request:

```json
{
  "force": false
}
```

Response:

```json
{
  "success": true,
  "data": {
    "job_type": "fatigue_aggregation",
    "job_status": "queued"
  }
}
```

---

## 12. Notification APIs

Owner service:
- `notification_service.py`

Tables:
- `notifications`
- optionally `interaction_events`

## 12.1 List notifications

### `GET /api/v1/notifications`

Recommended query params:
- `status`
- `channel`
- `scheduled_before`
- `scheduled_after`

Purpose:
- power notification inbox and dashboard history

Response:

```json
{
  "success": true,
  "data": {
    "items": []
  }
}
```

## 12.2 Send test notification

### `POST /api/v1/notifications/test`

Purpose:
- verify channel delivery for Telegram or web

Request:

```json
{
  "channel": "telegram",
  "title": "Test",
  "body": "This is a test notification"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "notification": {},
    "delivery_status": "queued"
  }
}
```

## 12.3 Dismiss notification

### `POST /api/v1/notifications/{notification_id}/dismiss`

Purpose:
- mark a notification as dismissed

Request:

```json
{}
```

Response:

```json
{
  "success": true,
  "data": {
    "notification_id": "uuid",
    "status": "dismissed"
  }
}
```

---

## 13. Decision and Orchestration APIs

Owner service:
- `decision_service.py`

Tables used as read context:
- `tasks`
- `internal_calendar`
- `fatigue_checkins`
- `fatigue_patterns`
- `learned_memories`
- `user_preferences`
- `connectors`

Tables optionally written:
- `interaction_events`
- `notifications`
- `internal_calendar`
- `tasks`

## 13.1 Decision query

### `POST /api/v1/decision/query`

Purpose:
- answer a real-time user question using fatigue, memory, tasks, and calendar context

Request:

```json
{
  "query": "What should I do first tonight?",
  "domain_hint": "task",
  "fatigue_score": null,
  "context_overrides": {
    "time_available_minutes": 90
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "decision_id": "uuid",
    "mode": "guided",
    "primary_recommendation": "Work on Assignment A first",
    "alternatives": [
      {
        "option": "Start Assignment B",
        "rank": 2,
        "reason": "Longer and less likely to fit tonight"
      }
    ],
    "reasoning_summary": "Assignment A fits the time window and lowers the highest deadline risk.",
    "confidence": 0.88,
    "follow_up_questions": [],
    "suggested_actions": [
      "create_focus_block"
    ]
  }
}
```

Behavior:
- synchronous decision response
- may internally fetch connector context
- may ask for missing fatigue if confidence is low
- should log interaction event

## 13.2 Plan day

### `POST /api/v1/decision/plan-day`

Purpose:
- produce a plan for the current or requested day
- optionally create internal calendar blocks

Request:

```json
{
  "date": "2026-04-19",
  "fatigue_score": 3,
  "auto_create_blocks": false
}
```

Response:

```json
{
  "success": true,
  "data": {
    "date": "2026-04-19",
    "summary": "Morning is best for deep work. Keep evening light.",
    "recommended_blocks": [],
    "notifications_to_schedule": []
  }
}
```

## 13.3 Next best action

### `POST /api/v1/decision/next-best-action`

Purpose:
- return one strong action recommendation with minimal friction
- especially useful for high fatigue or quick bot interactions

Request:

```json
{
  "fatigue_score": 4,
  "time_available_minutes": 45
}
```

Response:

```json
{
  "success": true,
  "data": {
    "primary_recommendation": "Spend 30 minutes on Assignment A now",
    "reasoning_summary": "This is the highest-risk short task that still fits your energy level.",
    "confidence": 0.91
  }
}
```

---

## 14. Memory APIs

Owner service:
- `memory_service.py`

Tables:
- `learned_memories`

These are useful for admin, debugging, and user transparency.

## 14.1 List learned memories

### `GET /api/v1/memories`

Recommended query params:
- `domain`
- `memory_type`
- `is_active`

Response:

```json
{
  "success": true,
  "data": {
    "items": []
  }
}
```

## 14.2 Update memory state

### `PATCH /api/v1/memories/{memory_id}`

Purpose:
- allow activation, deactivation, or confidence adjustment for user control or admin workflows

Request:

```json
{
  "is_active": false,
  "confidence": 0.3
}
```

Response:

```json
{
  "success": true,
  "data": {
    "memory": {}
  }
}
```

---

## 15. Interaction Event API

Owner service:
- usually cross-domain, can be thin event ingestion helper

Tables:
- `interaction_events`

This may remain internal-only in the MVP. It can still be useful as a contract.

## 15.1 Log interaction event

### `POST /api/v1/events`

Purpose:
- record frontend or bot interaction events that are not already captured by domain services

Request:

```json
{
  "event_type": "chat_message_received",
  "entity_type": "task",
  "entity_id": "uuid",
  "payload_json": {
    "source": "telegram"
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "event_logged": true
  }
}
```

---

## 16. Sync and Worker Trigger Endpoints

These endpoints are optional but useful for admin tools or manual operations.

## 16.1 Trigger scheduling scan

### `POST /api/v1/jobs/scheduling/scan`

Purpose:
- queue a scheduling pass for future task suggestions

Request:

```json
{
  "window_days": 7,
  "force": false
}
```

Response:

```json
{
  "success": true,
  "data": {
    "job_type": "scheduling_scan",
    "job_status": "queued"
  }
}
```

## 16.2 Trigger memory distillation

### `POST /api/v1/jobs/memory/distill`

Purpose:
- queue learned memory creation from raw events and feedback

Request:

```json
{
  "force": false
}
```

Response:

```json
{
  "success": true,
  "data": {
    "job_type": "memory_distillation",
    "job_status": "queued"
  }
}
```

---

## 17. Endpoint Ownership by File

## `api/routes/auth.py`
- `POST /api/v1/auth/session/sync`

## `api/routes/users.py`
- `GET /api/v1/me`
- `PATCH /api/v1/me/preferences`

## `api/routes/connectors.py`
- `GET /api/v1/connectors`
- `POST /api/v1/connectors/google-calendar/connect`
- `POST /api/v1/connectors/gmail/connect`
- `POST /api/v1/connectors/{connector_id}/sync`
- `POST /api/v1/connectors/{connector_id}/disconnect`

## `api/routes/tasks.py`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `PATCH /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/complete`

## `api/routes/internal_calendar.py`
- `POST /api/v1/internal-calendar/suggest`
- `GET /api/v1/internal-calendar`
- `GET /api/v1/internal-calendar/{block_id}`
- `POST /api/v1/internal-calendar/{block_id}/confirm`
- `POST /api/v1/internal-calendar/{block_id}/reject`
- `POST /api/v1/internal-calendar/{block_id}/reschedule`
- `POST /api/v1/internal-calendar/{block_id}/complete`
- `POST /api/v1/calendar-feedback`

## `api/routes/fatigue.py`
- `POST /api/v1/fatigue/checkins`
- `GET /api/v1/fatigue/checkins`
- `GET /api/v1/fatigue/patterns`
- `POST /api/v1/fatigue/patterns/recompute`

## `api/routes/notifications.py`
- `GET /api/v1/notifications`
- `POST /api/v1/notifications/test`
- `POST /api/v1/notifications/{notification_id}/dismiss`

## `api/routes/decisions.py`
- `POST /api/v1/decision/query`
- `POST /api/v1/decision/plan-day`
- `POST /api/v1/decision/next-best-action`

## `api/routes/memories.py`
- `GET /api/v1/memories`
- `PATCH /api/v1/memories/{memory_id}`

## `api/routes/events.py`
- `POST /api/v1/events`

## `api/routes/jobs.py`
- `POST /api/v1/jobs/scheduling/scan`
- `POST /api/v1/jobs/memory/distill`

---

## 18. Suggested Build Order

Build these first:

### Step 1
- `POST /auth/session/sync`
- `GET /me`
- `PATCH /me/preferences`
- `POST /tasks`
- `GET /tasks`
- `PATCH /tasks/{id}`

### Step 2
- `GET /connectors`
- `POST /connectors/google-calendar/connect`
- `POST /connectors/gmail/connect`
- `POST /connectors/{id}/sync`

### Step 3
- `POST /internal-calendar/suggest`
- `GET /internal-calendar`
- `POST /internal-calendar/{id}/confirm`
- `POST /internal-calendar/{id}/reject`
- `POST /internal-calendar/{id}/reschedule`

### Step 4
- `POST /fatigue/checkins`
- `GET /fatigue/patterns`
- `GET /notifications`

### Step 5
- `POST /decision/query`
- `POST /decision/next-best-action`
- `POST /decision/plan-day`

### Step 6
- memory and job trigger endpoints
- internal transparency endpoints for debugging and admin

---

## 19. What Must Stay Out of the First API Version

Avoid adding these too early:
- full multi-agent routing endpoints
- raw connector payload browsing endpoints for end users
- direct LLM completion passthrough endpoints
- too many analytics endpoints before core state is stable
- uncontrolled write access to learned memory without guardrails

---

## 20. Bottom Line

This API contract gives the backend a clean first version that matches the current system design:

- internal state is explicit
- connectors are managed separately
- planning is centered on the internal calendar
- fatigue is stored both as raw check-ins and derived patterns
- learning comes from behavior and feedback
- orchestration sits above clean operational APIs

This is the right contract shape for the current hackathon build because it keeps the system simple enough to implement, while still preserving the core product idea of a proactive, fatigue-aware, memory-backed assistant.
