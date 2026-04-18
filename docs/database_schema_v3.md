# Database Schema v3 - Fatigue-Aware Personal Assistant

Last updated: April 18, 2026

## Overview

This schema is the updated MVP database design for the current product direction.

It reflects the latest system split:

1. **Phase 1 - Future Task Engine**
   - internal calendar driven
   - proactive
   - planner and scheduler
   - reminder and watcher based

2. **Phase 2 - In-Prompt Decision Engine**
   - real-time user questions
   - uses long-term memory
   - uses fatigue layer
   - adapts answer style based on likely user bandwidth

This version keeps the schema intentionally small, but adds the latest important concepts:

- internal calendar as the assistant-owned planning layer
- feedback on suggested calendar blocks
- explicit fatigue check-ins
- derived fatigue pattern memory by time bucket
- learned long-term memory
- notification support
- raw interaction history for future learning

---

## Design Principles

- Keep structured tables as the source of truth
- Keep external connector data separate from assistant-owned planning state
- Keep internal scheduling separate from learned memory
- Keep raw user behavior separate from distilled memory
- Keep the fatigue layer structured and confidence-aware
- Use vector memory only for learned patterns, not exact facts
- Avoid too many tables for the MVP
- Support both future-task planning and in-prompt decision support

---

## Recommended Extensions

```sql
create extension if not exists vector;
create extension if not exists pgcrypto;
```

---

## Recommended Enums

```sql
create type connector_provider as enum (
  'gmail',
  'google_calendar',
  'google_notes'
);

create type connector_status as enum (
  'connected',
  'expired',
  'revoked',
  'error'
);

create type task_status as enum (
  'pending',
  'scheduled',
  'in_progress',
  'done',
  'skipped',
  'archived'
);

create type calendar_block_type as enum (
  'suggested_task',
  'focus_block',
  'break_block',
  'deadline_buffer',
  'manual_block',
  'review_block',
  'recovery_block'
);

create type calendar_block_status as enum (
  'suggested',
  'confirmed',
  'rejected',
  'rescheduled',
  'done',
  'missed',
  'cancelled'
);

create type feedback_response_type as enum (
  'accepted',
  'rejected',
  'moved',
  'snoozed',
  'completed',
  'ignored'
);

create type notification_channel as enum (
  'telegram',
  'web',
  'email'
);

create type notification_status as enum (
  'queued',
  'sent',
  'failed',
  'dismissed',
  'clicked'
);

create type memory_type as enum (
  'habit',
  'preference',
  'pattern',
  'constraint'
);

create type memory_source as enum (
  'explicit',
  'behavior',
  'inferred'
);

create type fatigue_time_bucket as enum (
  'morning',
  'afternoon',
  'evening',
  'night'
);

create type fatigue_trend_direction as enum (
  'improving',
  'worsening',
  'stable',
  'unknown'
);
```

---

# Tables

## 1. users

Base application user.

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique,
  email text unique,
  full_name text,
  timezone text not null default 'America/Los_Angeles',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Purpose:
- stable internal user id
- user account identity
- root foreign key for all product data

---

## 2. user_preferences

Stores onboarding data and reusable user preferences.

```sql
create table user_preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references users(id) on delete cascade,
  sleep_time time,
  wake_time time,
  work_start_time time,
  work_end_time time,
  work_days int[] default '{1,2,3,4,5}',
  preferred_response_style text,
  decision_style_default text,
  reminder_tolerance text,
  fatigue_prompt_enabled boolean not null default true,
  onboarding_completed boolean not null default false,
  profile_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Examples:
- morning or evening preference
- direct or options-based assistant style
- class/work schedule
- general onboarding answers
- whether the system can occasionally ask fatigue questions

---

## 3. connectors

Stores connector account details and sync state.

```sql
create table connectors (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  provider connector_provider not null,
  account_email text,
  status connector_status not null default 'connected',
  access_token_encrypted text,
  refresh_token_encrypted text,
  token_expires_at timestamptz,
  last_sync_at timestamptz,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, provider, account_email)
);
```

Purpose:
- Gmail connection
- Google Calendar connection
- Google Notes connection
- sync metadata and token storage

---

## 4. tasks

Stores the actual tasks the user needs to do.

```sql
create table tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  title text not null,
  description text,
  priority smallint default 3,
  estimated_minutes integer,
  actual_minutes integer,
  energy_required smallint,
  due_at timestamptz,
  status task_status not null default 'pending',
  source text default 'user',
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);
```

Purpose:
- user-created tasks
- connector-derived tasks later if needed
- source of truth for work to be done

---

## 5. internal_calendar

Stores the assistant's internal calendar blocks.

```sql
create table internal_calendar (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  task_id uuid references tasks(id) on delete set null,
  title text not null,
  block_type calendar_block_type not null default 'suggested_task',
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  status calendar_block_status not null default 'suggested',
  sync_to_google boolean not null default false,
  external_event_id text,
  source text default 'system',
  reason_summary text,
  reschedule_count integer not null default 0,
  priority_snapshot smallint,
  energy_snapshot smallint,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  confirmed_at timestamptz,
  rejected_at timestamptz,
  completed_at timestamptz
);
```

Purpose:
- internal suggested task blocks
- confirmed work blocks
- break, recovery, review, and buffer blocks
- optional sync link to Google Calendar

Important rule:
- this is the internal planning layer
- this is not the learned memory layer
- this is the operational state for Phase 1

---

## 6. calendar_feedback

Stores how the user responded to internal calendar suggestions.

```sql
create table calendar_feedback (
  id uuid primary key default gen_random_uuid(),
  calendar_block_id uuid not null references internal_calendar(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  response_type feedback_response_type not null,
  reason_code text,
  reason_text text,
  fatigue_score smallint check (fatigue_score between 0 and 5),
  created_at timestamptz not null default now()
);
```

Example reason codes:
- too_tired
- busy_at_that_time
- wrong_priority
- too_long
- different_time
- already_planned
- not_urgent

Purpose:
- record acceptance and rejection
- capture why the user said no
- support future learning safely

---

## 7. fatigue_checkins

Stores explicit fatigue input from the user.

```sql
create table fatigue_checkins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  score smallint not null check (score between 0 and 5),
  source text default 'user',
  notes text,
  context_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Purpose:
- explicit fatigue check-ins
- optional inline fatigue input when confidence is low
- user-provided fatigue history
- strongest direct fatigue signal when available

Important rule:
- this is raw explicit fatigue input
- it should not be replaced by only inferred memory

---

## 8. fatigue_patterns

Stores derived fatigue patterns by time bucket.

```sql
create table fatigue_patterns (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  weekday smallint,
  time_bucket fatigue_time_bucket not null,
  avg_fatigue numeric(4,2),
  min_fatigue numeric(4,2),
  max_fatigue numeric(4,2),
  fatigue_variance numeric(6,3),
  sample_count integer not null default 0,
  confidence numeric(4,3) not null default 0.500,
  trend_direction fatigue_trend_direction not null default 'unknown',
  last_signal_at timestamptz,
  last_computed_at timestamptz not null default now(),
  metadata_json jsonb not null default '{}'::jsonb,
  unique(user_id, weekday, time_bucket)
);
```

Purpose:
- derived fatigue memory by time window
- decision-time fatigue prior for in-prompt questions
- fallback when no live fatigue input exists
- reusable signal for future fatigue-aware scheduling

Examples:
- user usually has high fatigue at night
- weekday mornings are strong
- Sunday evenings are unstable but usually medium fatigue

Important rule:
- this table stores derived summaries, not raw events
- update this through workers or aggregation jobs

---

## 9. interaction_events

Raw event log for learning and analytics.

```sql
create table interaction_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  event_type text not null,
  entity_type text,
  entity_id uuid,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Examples:
- suggestion_shown
- suggestion_accepted
- suggestion_rejected
- task_completed
- chat_message_received
- connector_synced
- notification_clicked
- fatigue_prompt_shown
- fatigue_checkin_submitted

Purpose:
- raw behavioral history
- audit trail
- analytics source
- memory distillation input
- soft fatigue signal source later

---

## 10. learned_memories

Stores distilled memory and behavior patterns using vector search.

```sql
create table learned_memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  memory_type memory_type not null,
  domain text not null default 'planning',
  statement text not null,
  source memory_source not null default 'inferred',
  confidence numeric(4,3) not null default 0.500,
  last_confirmed_at timestamptz,
  metadata_json jsonb not null default '{}'::jsonb,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  is_active boolean not null default true
);
```

Examples:
- User often rejects long work blocks after 9 PM
- User prefers direct suggestions when tired
- User accepts short focus blocks on weekday evenings
- User struggles with long tasks after late classes

Important rule:
- store learned patterns here
- do not store every raw rejection event here
- do not store exact operational truth only here

---

## 11. notifications

Stores proactive messages, reminders, and notification delivery state.

```sql
create table notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  task_id uuid references tasks(id) on delete set null,
  calendar_block_id uuid references internal_calendar(id) on delete set null,
  channel notification_channel not null,
  title text,
  body text not null,
  scheduled_for timestamptz,
  sent_at timestamptz,
  status notification_status not null default 'queued',
  provider_message_id text,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Purpose:
- reminders for tasks
- nudges for suggested calendar blocks
- proactive assistant messages
- notification tracking and analytics

---

# Recommended Indexes

```sql
create index idx_tasks_user_status_due
  on tasks(user_id, status, due_at);

create index idx_internal_calendar_user_time
  on internal_calendar(user_id, starts_at, ends_at);

create index idx_internal_calendar_task
  on internal_calendar(task_id);

create index idx_calendar_feedback_block_created
  on calendar_feedback(calendar_block_id, created_at desc);

create index idx_fatigue_checkins_user_created
  on fatigue_checkins(user_id, created_at desc);

create index idx_fatigue_patterns_user_bucket
  on fatigue_patterns(user_id, weekday, time_bucket);

create index idx_interaction_events_user_created
  on interaction_events(user_id, created_at desc);

create index idx_notifications_user_status_time
  on notifications(user_id, status, scheduled_for);

create index idx_learned_memories_user_active
  on learned_memories(user_id, is_active);
```

For vector search:

```sql
create index idx_learned_memories_embedding
on learned_memories
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
```

---

# Relationship Summary

- one `users` -> one `user_preferences`
- one `users` -> many `connectors`
- one `users` -> many `tasks`
- one `users` -> many `internal_calendar` blocks
- one `tasks` -> many `internal_calendar` blocks
- one `internal_calendar` block -> many `calendar_feedback` rows
- one `users` -> many `fatigue_checkins`
- one `users` -> many `fatigue_patterns`
- one `users` -> many `interaction_events`
- one `users` -> many `learned_memories`
- one `users` -> many `notifications`

---

# What Each Table Means in Simple Terms

- `users` -> who the user is
- `user_preferences` -> onboarding and stable preferences
- `connectors` -> Gmail, Calendar, Notes connection info
- `tasks` -> real work user needs to do
- `internal_calendar` -> suggested and confirmed schedule blocks
- `calendar_feedback` -> how user responded and why
- `fatigue_checkins` -> explicit fatigue entries from the user
- `fatigue_patterns` -> learned fatigue profile by time window
- `interaction_events` -> raw action history
- `learned_memories` -> long-term learned patterns
- `notifications` -> proactive reminders and messages

---

# Suggested MVP Flow Mapped to Tables

## 1. User finishes onboarding
Store in:
- `users`
- `user_preferences`

## 2. User connects Google apps
Store in:
- `connectors`

## 3. User creates or imports task
Store in:
- `tasks`

## 4. System suggests best work slot
Store in:
- `internal_calendar` with status = `suggested`
- `interaction_events`

## 5. User accepts or rejects
Store in:
- `calendar_feedback`
- update `internal_calendar.status`
- `interaction_events`

## 6. System sends reminder or proactive nudge
Store in:
- `notifications`

## 7. User submits fatigue when asked or available
Store in:
- `fatigue_checkins`
- `interaction_events`

## 8. System computes fatigue patterns over time
Store in:
- `fatigue_patterns`

## 9. Repeated behavior becomes memory
Store in:
- `learned_memories`

---

# How This Supports the Two-Phase Architecture

## Phase 1 - Future Task Engine
Main tables:
- `tasks`
- `internal_calendar`
- `calendar_feedback`
- `notifications`

This phase uses:
- assistant-owned scheduling blocks
- proactive reminders
- feedback on suggestions
- future extensibility for watchers and replanning

## Phase 2 - In-Prompt Decision Engine
Main tables:
- `fatigue_checkins`
- `fatigue_patterns`
- `learned_memories`
- `interaction_events`
- optionally `tasks`

This phase uses:
- explicit fatigue when available
- historical fatigue priors by time bucket
- long-term memory
- real-time behavioral context

---

# What Changed from v2

This updated version adds the latest system changes:

1. **Fatigue layer support**
   - added `fatigue_checkins`
   - added `fatigue_patterns`
   - added fatigue-specific enums

2. **Internal calendar improvements**
   - added richer block types
   - added `reschedule_count`
   - added snapshot and metadata fields

3. **User preference refinement**
   - added `fatigue_prompt_enabled`

4. **Architecture alignment**
   - schema now explicitly supports both:
     - future-task planning
     - in-prompt fatigue-aware decisions

---

# Final Recommendation

For the current build, this schema is a strong updated MVP.

It is still intentionally small, but now it properly supports:

- internal planning state
- user feedback loops
- explicit fatigue capture
- derived fatigue priors
- long-term learned memory
- proactive notifications
- raw event history

That separation keeps the system much easier to extend later while supporting the latest product direction.
