# Internal Calendar Design (MVP)

## Overview

The internal calendar is the assistant-owned planning layer. It
generates dynamic schedules based on tasks, fatigue, and external
calendar constraints.

External calendar = fixed commitments\
Internal calendar = assistant-generated execution plan

------------------------------------------------------------------------

## Core Responsibilities

-   Plan user work blocks
-   Allocate breaks and recovery
-   Adjust schedule dynamically
-   Learn from user behavior (accept/reject)

------------------------------------------------------------------------

## Data Model

### Table: internal_calendar_entries

Fields: - id (uuid) - user_id (uuid) - task_id (uuid, optional) -
goal_id (uuid, optional) - entry_type (focus, break, prep, buffer,
etc.) - status (suggested, confirmed, completed, missed) - source
(scheduler, watcher, user) - title - description - starts_at - ends_at -
energy_level_required - priority - flexibility - confidence -
reasoning_summary - external_sync_enabled - external_event_id -
created_at - updated_at

------------------------------------------------------------------------

## Scheduling Flow

1.  Fetch external events
2.  Identify free time windows
3.  Score each window:
    -   fatigue
    -   task urgency
    -   energy requirement
4.  Allocate blocks:
    -   high priority tasks first
    -   breaks between work
5.  Store as suggested entries

------------------------------------------------------------------------

## User Interaction

-   User receives suggestion
-   Accept → status = confirmed
-   Reject → status = cancelled + store reason
-   Missed → status = missed → trigger replanning

------------------------------------------------------------------------

## Replanning Triggers

-   User rejects suggestion
-   Task missed
-   New task added
-   Calendar updated
-   Fatigue change

------------------------------------------------------------------------

## API Endpoints

-   GET /internal-calendar/day
-   GET /internal-calendar/week
-   POST /internal-calendar/generate
-   POST /internal-calendar/{id}/confirm
-   POST /internal-calendar/{id}/reject
-   POST /internal-calendar/{id}/complete

------------------------------------------------------------------------

## Worker Design

-   Scheduler Worker
-   Conflict Checker
-   Replanner Worker
-   Reminder Dispatcher

------------------------------------------------------------------------

## UI Representation

Two layers: 1. External calendar (fixed) 2. Internal calendar (assistant
plan)

Each block shows: - Title - Type - Confidence - Reasoning - Actions
(accept/reject)

------------------------------------------------------------------------

## MVP Scope

Include: - Basic scheduling - Suggestions - Accept/reject flow - Simple
replanning

Exclude: - Complex recurrence - Full calendar sync - Multi-calendar
merging

------------------------------------------------------------------------

## Key Principle

The system should reduce cognitive load by deciding *when* the user
should act, not just reminding them.
