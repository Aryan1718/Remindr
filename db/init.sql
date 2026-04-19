-- Fresh database bootstrap for the Fatigue-Aware Personal Assistant.
-- Intended for a new empty database. This file is not guaranteed to be safe
-- to rerun on a populated database unless additional object guards are added.

-- ============================================================================
-- Extensions
-- ============================================================================

create extension if not exists pgcrypto;
create extension if not exists vector;

-- ============================================================================
-- Enums
-- ============================================================================

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

-- ============================================================================
-- Core tables
-- ============================================================================

create table users (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique,
  email text unique,
  full_name text,
  timezone text not null default 'America/Los_Angeles',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

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
  unique (user_id, provider, account_email)
);

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

create table fatigue_checkins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  score smallint not null check (score between 0 and 5),
  source text default 'user',
  notes text,
  context_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

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
  unique (user_id, weekday, time_bucket)
);

create table interaction_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  event_type text not null,
  entity_type text,
  entity_id uuid,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

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

-- ============================================================================
-- Connector normalization tables
-- ============================================================================

create table external_calendar_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  connector_id uuid not null references connectors(id) on delete cascade,
  external_event_id text not null,
  calendar_id text,
  title text,
  description text,
  location text,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  is_all_day boolean not null default false,
  status text,
  raw_payload_json jsonb not null default '{}'::jsonb,
  last_synced_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (connector_id, external_event_id)
);

create table external_email_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  connector_id uuid not null references connectors(id) on delete cascade,
  external_message_id text not null,
  external_thread_id text,
  subject text,
  sender_name text,
  sender_email text,
  snippet text,
  body_summary text,
  received_at timestamptz,
  labels_json jsonb not null default '[]'::jsonb,
  obligation_type text,
  due_at timestamptz,
  importance_score numeric(6,3),
  raw_payload_json jsonb not null default '{}'::jsonb,
  last_synced_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (connector_id, external_message_id)
);

-- ============================================================================
-- Indexes
-- ============================================================================

create index idx_connectors_user_id
  on connectors(user_id);

create index idx_tasks_user_status_due
  on tasks(user_id, status, due_at);

create index idx_internal_calendar_user_time
  on internal_calendar(user_id, starts_at, ends_at);

create index idx_internal_calendar_task
  on internal_calendar(task_id);

create index idx_calendar_feedback_block_created
  on calendar_feedback(calendar_block_id, created_at desc);

create index idx_calendar_feedback_user_id
  on calendar_feedback(user_id);

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

create index idx_external_calendar_events_user_time
  on external_calendar_events(user_id, starts_at, ends_at);

create index idx_external_calendar_events_connector_synced
  on external_calendar_events(connector_id, last_synced_at desc);

create index idx_external_email_items_user_received
  on external_email_items(user_id, received_at desc);

create index idx_external_email_items_connector_synced
  on external_email_items(connector_id, last_synced_at desc);

create index idx_external_email_items_user_due_at
  on external_email_items(user_id, due_at);

create index idx_learned_memories_embedding
  on learned_memories
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);
