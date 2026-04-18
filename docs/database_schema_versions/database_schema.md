# Database Schema - Fatigue-Aware Personal Assistant

Last updated: April 18, 2026

## Overview

This file defines the recommended MVP database schema for the Fatigue-Aware Personal Assistant.

Stack assumptions:
- Supabase Auth
- Supabase PostgreSQL
- pgvector for learned memory retrieval
- FastAPI backend
- Telegram as primary communication channel
- Web dashboard for onboarding, settings, and visibility

Design principles:
- Structured tables are the source of truth
- Learned memory is stored separately and retrieved semantically with pgvector
- Raw interaction signals are logged and later distilled into reusable memory
- Watchers, reminders, and notifications are first-class operational concepts
- The schema is MVP-first but production-shaped

This schema aligns with the product design where the system needs:
- onboarding and reusable user context
- tasks, goals, reminders, and scheduling
- fatigue-aware decisions
- connectors for email and calendar
- learned memory and personalization
- proactive watcher jobs
- event logging for behavior-based learning

---

## Core Modeling Rules

1. Do not store critical truth only in embeddings.
2. Do not store deadlines, tasks, fatigue scores, reminders, or connector state in free-text memory.
3. Use relational columns for exact facts and pgvector for fuzzy learned memory.
4. Keep behavioral event history separate from memory.
5. Use JSONB only for flexible payloads, not core searchable facts.

---

## Recommended Extensions

```sql
create extension if not exists vector;
create extension if not exists pgcrypto;
```

Notes:
- `vector` is required for pgvector embeddings.
- `pgcrypto` provides `gen_random_uuid()`.

---

## Recommended Enums

Use enums for stable app states.

```sql
create type channel_type as enum ('telegram', 'web', 'whatsapp');

create type integration_provider as enum (
  'google_calendar',
  'gmail',
  'outlook_calendar',
  'outlook_mail'
);

create type integration_status as enum (
  'connected',
  'expired',
  'revoked',
  'error'
);

create type goal_status as enum (
  'active',
  'paused',
  'completed',
  'archived'
);

create type task_status as enum (
  'pending',
  'scheduled',
  'in_progress',
  'done',
  'skipped',
  'archived'
);

create type reminder_status as enum (
  'pending',
  'sent',
  'dismissed',
  'snoozed',
  'cancelled'
);

create type decision_domain as enum (
  'task',
  'planning',
  'job_search',
  'food',
  'clothing',
  'routine',
  'purchase',
  'social',
  'other'
);

create type decision_mode as enum (
  'exploratory',
  'guided',
  'decisive'
);

create type decision_status as enum (
  'pending',
  'answered',
  'cancelled'
);

create type feedback_type as enum (
  'accepted',
  'ignored',
  'rejected',
  'corrected'
);

create type memory_kind as enum (
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

create type watcher_type as enum (
  'deadline_risk',
  'schedule_overload',
  'goal_followup',
  'job_search'
);

create type watcher_status as enum (
  'active',
  'paused',
  'disabled'
);

create type notification_status as enum (
  'queued',
  'sent',
  'failed',
  'dismissed'
);
```

---

## Tables

## 1. users

Application-level user table linked to Supabase Auth.

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid not null unique,
  email text unique,
  full_name text,
  timezone text not null default 'America/Los_Angeles',
  locale text default 'en',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Purpose:
- local app identity
- stable internal foreign-key reference
- decouples app model from Supabase internal auth tables

---

## 2. user_profiles

Stores onboarding profile and stable routine information.

```sql
create table user_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references users(id) on delete cascade,
  sleep_time time,
  wake_time time,
  work_start_time time,
  work_end_time time,
  work_days int[] default '{1,2,3,4,5}',
  reminder_tolerance text,
  decision_style_default text,
  fatigue_prompt_enabled boolean not null default true,
  preferred_response_style text,
  onboarding_completed boolean not null default false,
  profile_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Example data:
- sleep/wake pattern
- work or class routine
- default guidance style
- reminder sensitivity

---

## 3. user_preferences

Stores explicit preferences as structured truth.

```sql
create table user_preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  category text not null,
  pref_key text not null,
  pref_value jsonb not null,
  source memory_source not null default 'explicit',
  confidence numeric(4,3) default 1.000,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, category, pref_key)
);
```

Examples:
- category = 'communication', pref_key = 'preferred_channel'
- category = 'job_search', pref_key = 'target_roles'
- category = 'routine', pref_key = 'best_focus_window'

---

## 4. communication_channels

Supports Telegram now and future channels later.

```sql
create table communication_channels (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  channel channel_type not null,
  external_user_id text,
  external_chat_id text,
  is_primary boolean not null default false,
  is_active boolean not null default true,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, channel, external_chat_id)
);
```

Use this table to store:
- Telegram chat ID
- web channel identity
- future WhatsApp mapping

---

## 5. integration_accounts

Stores connector account state and tokens.

```sql
create table integration_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  provider integration_provider not null,
  account_email text,
  status integration_status not null default 'connected',
  scopes_json jsonb not null default '[]'::jsonb,
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

Notes:
- token fields should store encrypted values
- connector sync health belongs here

---

## 6. goals

Long-term objectives like switching jobs or preparing for exams.

```sql
create table goals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  title text not null,
  description text,
  domain decision_domain not null default 'other',
  target_date timestamptz,
  priority smallint default 3,
  status goal_status not null default 'active',
  success_definition text,
  created_from text default 'user',
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz
);
```

---

## 7. tasks

Structured operational tasks are one of the most important tables.

```sql
create table tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  goal_id uuid references goals(id) on delete set null,
  title text not null,
  description text,
  domain decision_domain not null default 'task',
  priority smallint default 3,
  importance smallint default 3,
  urgency smallint default 3,
  estimated_minutes integer,
  actual_minutes integer,
  energy_required smallint,
  due_at timestamptz,
  start_after timestamptz,
  status task_status not null default 'pending',
  source text default 'user',
  context_tags jsonb not null default '[]'::jsonb,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  archived_at timestamptz
);
```

This table should store:
- user-created tasks
- goal-derived tasks
- system-created subtasks if needed later

---

## 8. task_blocks

Represents scheduled work blocks created by the scheduler.

```sql
create table task_blocks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  task_id uuid not null references tasks(id) on delete cascade,
  scheduled_start timestamptz not null,
  scheduled_end timestamptz not null,
  block_type text default 'focus',
  status text default 'planned',
  generated_by text default 'system',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Use cases:
- planned focus blocks
- recovery or break windows
- future replanning results

---

## 9. reminders

Adaptive reminders for tasks and goals.

```sql
create table reminders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  task_id uuid references tasks(id) on delete cascade,
  goal_id uuid references goals(id) on delete cascade,
  title text not null,
  message text,
  remind_at timestamptz not null,
  delivery_channel channel_type,
  priority smallint default 3,
  status reminder_status not null default 'pending',
  snoozed_until timestamptz,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  sent_at timestamptz
);
```

---

## 10. fatigue_checkins

Core table for fatigue-aware behavior.

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

This should be queried often:
- latest check-in
- recent trend
- decision-time context

---

## 11. decision_requests

Stores each decision request made by the user.

```sql
create table decision_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  domain decision_domain not null,
  query text not null,
  fatigue_score smallint check (fatigue_score between 0 and 5),
  urgency smallint default 3,
  stakes smallint default 2,
  reversibility smallint default 2,
  time_available_minutes integer,
  due_at timestamptz,
  confidence numeric(4,3),
  status decision_status not null default 'pending',
  input_context_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

---

## 12. decision_recommendations

Stores the answer, alternatives, and schedule changes.

```sql
create table decision_recommendations (
  id uuid primary key default gen_random_uuid(),
  decision_request_id uuid not null references decision_requests(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  mode decision_mode not null,
  primary_recommendation text not null,
  alternatives_json jsonb not null default '[]'::jsonb,
  reasoning_summary text,
  schedule_changes_json jsonb not null default '[]'::jsonb,
  follow_up_questions_json jsonb not null default '[]'::jsonb,
  memory_updates_json jsonb not null default '[]'::jsonb,
  confidence numeric(4,3),
  created_at timestamptz not null default now()
);
```

---

## 13. decision_feedback

Stores whether recommendations were accepted, ignored, rejected, or corrected.

```sql
create table decision_feedback (
  id uuid primary key default gen_random_uuid(),
  decision_request_id uuid not null references decision_requests(id) on delete cascade,
  recommendation_id uuid references decision_recommendations(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  feedback feedback_type not null,
  rating smallint check (rating between 1 and 5),
  comment text,
  created_at timestamptz not null default now()
);
```

This table helps the system learn from real outcomes.

---

## 14. interaction_events

Raw behavioral event log used to create memory and measure usage.

```sql
create table interaction_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  session_id uuid,
  channel channel_type,
  event_type text not null,
  entity_type text,
  entity_id uuid,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Examples:
- message_received
- recommendation_shown
- recommendation_accepted
- reminder_dismissed
- task_completed
- fatigue_submitted

---

## 15. learned_memories

This is the main learned-memory table and should use pgvector.

```sql
create table learned_memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  memory_type memory_kind not null,
  domain decision_domain not null default 'other',
  statement text not null,
  source memory_source not null default 'inferred',
  confidence numeric(4,3) not null default 0.500,
  importance smallint not null default 3,
  last_confirmed_at timestamptz,
  last_used_at timestamptz,
  usage_count integer not null default 0,
  is_active boolean not null default true,
  metadata_json jsonb not null default '{}'::jsonb,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz
);
```

Examples of statements:
- User struggles with long tasks after 9 PM
- User prefers direct recommendations when fatigue is 4 or higher
- User responds better to reminders before 8 AM
- User often underestimates writing task duration

Recommended practice:
- store readable statement text
- store structured metadata
- store embedding for semantic retrieval

---

## 16. memory_feedback

Allows memory confirmation, correction, or deactivation.

```sql
create table memory_feedback (
  id uuid primary key default gen_random_uuid(),
  memory_id uuid not null references learned_memories(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  feedback_type text not null,
  note text,
  created_at timestamptz not null default now()
);
```

Examples:
- confirmed
- corrected
- deactivated

---

## 17. watchers

Watchers are background jobs that proactively monitor conditions.

```sql
create table watchers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  goal_id uuid references goals(id) on delete set null,
  task_id uuid references tasks(id) on delete set null,
  watcher_type watcher_type not null,
  status watcher_status not null default 'active',
  schedule_cron text,
  config_json jsonb not null default '{}'::jsonb,
  last_run_at timestamptz,
  next_run_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Examples:
- deadline risk watcher
- schedule overload watcher
- goal follow-up watcher
- job search watcher

---

## 18. watcher_runs

Tracks each execution of a watcher.

```sql
create table watcher_runs (
  id uuid primary key default gen_random_uuid(),
  watcher_id uuid not null references watchers(id) on delete cascade,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null,
  result_summary text,
  result_json jsonb not null default '{}'::jsonb,
  triggered_action_count integer not null default 0,
  error_message text
);
```

---

## 19. notifications

All outbound proactive messages and reminder sends should be logged here.

```sql
create table notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  reminder_id uuid references reminders(id) on delete set null,
  watcher_run_id uuid references watcher_runs(id) on delete set null,
  channel_id uuid references communication_channels(id) on delete set null,
  status notification_status not null default 'queued',
  title text,
  body text not null,
  scheduled_for timestamptz,
  sent_at timestamptz,
  provider_message_id text,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

---

## 20. calendar_events

Normalized calendar events for availability and context.

```sql
create table calendar_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  integration_account_id uuid references integration_accounts(id) on delete cascade,
  external_event_id text not null,
  title text,
  description text,
  location text,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  is_all_day boolean not null default false,
  source_calendar text,
  raw_payload_json jsonb not null default '{}'::jsonb,
  last_synced_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(integration_account_id, external_event_id)
);
```

---

## 21. email_items

Normalized email records or extracted obligations from email.

```sql
create table email_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  integration_account_id uuid references integration_accounts(id) on delete cascade,
  external_message_id text not null,
  external_thread_id text,
  subject text,
  sender_email text,
  sender_name text,
  snippet text,
  summary text,
  obligation_type text,
  due_at timestamptz,
  importance_score numeric(4,3),
  raw_payload_json jsonb not null default '{}'::jsonb,
  last_synced_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(integration_account_id, external_message_id)
);
```

---

## Recommended Indexes

```sql
create index idx_tasks_user_status_due
  on tasks(user_id, status, due_at);

create index idx_tasks_goal
  on tasks(goal_id);

create index idx_reminders_user_time_status
  on reminders(user_id, remind_at, status);

create index idx_fatigue_user_created
  on fatigue_checkins(user_id, created_at desc);

create index idx_decision_requests_user_created
  on decision_requests(user_id, created_at desc);

create index idx_decision_recommendations_request
  on decision_recommendations(decision_request_id);

create index idx_interaction_events_user_created
  on interaction_events(user_id, created_at desc);

create index idx_watchers_user_status_next
  on watchers(user_id, status, next_run_at);

create index idx_notifications_user_status_time
  on notifications(user_id, status, scheduled_for);

create index idx_calendar_events_user_time
  on calendar_events(user_id, starts_at, ends_at);

create index idx_email_items_user_due
  on email_items(user_id, due_at);

create index idx_learned_memories_user_domain_active
  on learned_memories(user_id, domain, is_active);
```

For vector search, create the index after you have enough memory rows:

```sql
create index idx_learned_memories_embedding
on learned_memories
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
```

---

## Recommended Retrieval Pattern

When a decision request arrives:

1. Fetch structured context:
   - latest fatigue score
   - active tasks
   - due tasks
   - reminders
   - goals
   - upcoming calendar events

2. Fetch relevant learned memories:
   - filter by `user_id`
   - filter by `domain`
   - filter by `is_active = true`
   - rank by vector similarity

3. Combine both sets of data in the decision engine prompt.

Example query:

```sql
select id, statement, confidence, importance, metadata_json
from learned_memories
where user_id = $1
  and is_active = true
  and domain in ('task', 'planning', 'routine')
order by embedding <=> $2
limit 8;
```

---

## Relationship Summary

- one `users` -> one `user_profiles`
- one `users` -> many `user_preferences`
- one `users` -> many `communication_channels`
- one `users` -> many `integration_accounts`
- one `users` -> many `goals`
- one `goals` -> many `tasks`
- one `tasks` -> many `task_blocks`
- one `users` -> many `reminders`
- one `users` -> many `fatigue_checkins`
- one `users` -> many `decision_requests`
- one `decision_requests` -> many `decision_recommendations`
- one `decision_requests` -> many `decision_feedback`
- one `users` -> many `interaction_events`
- one `users` -> many `learned_memories`
- one `learned_memories` -> many `memory_feedback`
- one `users` -> many `watchers`
- one `watchers` -> many `watcher_runs`
- one `users` -> many `notifications`
- one `users` -> many `calendar_events`
- one `users` -> many `email_items`

---

## What Is Required Right Now

For the current MVP, these tables are required immediately:

- users
- user_profiles
- user_preferences
- communication_channels
- integration_accounts
- goals
- tasks
- reminders
- fatigue_checkins
- decision_requests
- decision_recommendations
- interaction_events
- learned_memories
- watchers
- notifications

These are useful but can be added slightly later if needed:
- task_blocks
- decision_feedback
- memory_feedback
- watcher_runs
- calendar_events
- email_items

---

## Final Recommendation

Use:
- PostgreSQL tables for truth and operational state
- pgvector only for learned memory retrieval
- interaction event logs as the raw learning signal
- watcher tables as durable automation state

This schema is designed so the assistant becomes:
- useful on day one because structured data exists
- more accurate over time because learned memory compounds
- proactive because reminders, watchers, and notifications are modeled directly
