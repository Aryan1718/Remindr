# Backend Workers and Jobs

Last updated: April 18, 2026

## 1. Purpose

This file defines the background worker layer for the fatigue-aware personal assistant backend.

The API layer should not do heavy or delayed work directly. Anything that is slow, repeatable, scheduled, or failure-prone should move into workers.

The worker layer is responsible for:
- connector sync
- normalization pipelines
- internal calendar suggestion generation
- fatigue aggregation
- learned memory distillation
- proactive notifications
- watcher execution
- retry-safe background workflows

This keeps the backend clean and supports the two main product phases:

1. **Phase 1 - Future Task Engine**
   - proactive
   - internal calendar driven
   - watcher and reminder based

2. **Phase 2 - In-Prompt Decision Engine**
   - real-time support for user questions
   - fatigue-aware reasoning
   - long-term memory updates

---

## 2. Worker Design Principles

### 2.1 Keep the API fast

FastAPI endpoints should:
- validate input
- write minimal required operational state
- enqueue background jobs when needed
- return quickly

They should not:
- fetch and process large connector payloads inline
- recompute fatigue patterns inline
- distill memory inline
- run notification delivery loops inline

### 2.2 Make jobs idempotent

A job should be safe to retry.

Examples:
- syncing the same calendar window twice should not create duplicate internal records
- memory distillation should not create repeated memory statements without deduplication
- sending notifications should guard against duplicate sends

### 2.3 Separate raw intake from interpretation

For external systems:
- first fetch raw or semi-raw data
- then normalize it
- then decide what should affect the product state

Do not let connector adapters directly mutate planning state without passing through normalization and service rules.

### 2.4 Keep operational truth separate from learned intelligence

Workers should respect the storage split:
- tasks and internal calendar are operational truth
- fatigue_checkins are raw explicit user signals
- fatigue_patterns are derived summaries
- learned_memories are distilled long-term patterns
- interaction_events are raw history

### 2.5 Design for partial failure

A connector job or watcher may fail without breaking the whole system.

Every important worker flow should support:
- retries
- status tracking
- error logging
- partial completion
- safe re-entry

---

## 3. Recommended Worker Stack

Recommended stack:
- Redis
- RQ workers
- scheduler process for recurring jobs
- Postgres or Supabase as the source of truth for job-related state

Why this fits the MVP:
- simple to reason about
- easy to run during a hackathon
- good enough for connector sync and watchers
- matches the existing backend direction

---

## 4. Recommended Folder Structure

```text
backend/
  app/
    workers/
      rq.py
      scheduler.py
      constants.py
      jobs/
        connector_sync.py
        connector_normalization.py
        internal_calendar_jobs.py
        fatigue_jobs.py
        memory_jobs.py
        notification_jobs.py
        watcher_jobs.py
        cleanup_jobs.py
      watchers/
        deadline_watcher.py
        overload_watcher.py
        inactivity_watcher.py
        connector_health_watcher.py
      utils/
        locks.py
        dedupe.py
        windowing.py
        retry.py
```

---

## 5. What Each Worker File Is About

## 5.1 `workers/rq.py`

Purpose:
- initializes Redis connection
- initializes RQ queues
- exposes queue objects to the rest of the backend

Typical ownership:
- queue names
- enqueue helpers
- shared worker bootstrapping logic

This file should be the entry point for all background job submission.

---

## 5.2 `workers/scheduler.py`

Purpose:
- schedules recurring jobs
- runs periodic watchers
- triggers maintenance and aggregation jobs

Examples of scheduled runs:
- connector sync every X minutes
- deadline watcher every 15 minutes
- overload watcher every hour
- fatigue aggregation every night
- memory distillation every night or every few hours

This file is about timing, not business logic.

---

## 5.3 `workers/constants.py`

Purpose:
- central place for queue names, retry defaults, lock TTLs, and batch sizes

Examples:
- connector queue names
- sync window sizes
- fatigue aggregation thresholds
- notification retry policy
- memory distillation minimum evidence count

This prevents job settings from being spread across many files.

---

## 5.4 `workers/jobs/connector_sync.py`

Purpose:
- fetches data from Gmail and Google Calendar connectors
- coordinates connector sync runs
- writes sync metadata
- hands raw results to the normalization layer

Responsibilities:
- load connector credentials and sync state
- decide sync window
- call provider adapter
- capture job metrics
- enqueue normalization job if needed

This file does not decide final scheduling or memory updates by itself.

It should focus on:
- external fetch
- sync bookkeeping
- safe retry behavior

---

## 5.5 `workers/jobs/connector_normalization.py`

Purpose:
- transforms external provider payloads into internal normalized shapes
- filters noisy or irrelevant payloads
- produces internal candidates for downstream services

Examples:
- Google Calendar event -> normalized event context object
- Gmail message -> obligation candidate or task signal

Responsibilities:
- normalize fields
- apply deduplication
- record skipped items
- produce structured candidate objects

This is the bridge between connectors and the product data model.

---

## 5.6 `workers/jobs/internal_calendar_jobs.py`

Purpose:
- generates suggested calendar blocks
- reschedules missed or rejected blocks
- creates recovery and review blocks when needed

Responsibilities:
- inspect tasks and deadlines
- inspect current internal calendar state
- respect fatigue patterns and user preferences
- suggest best-fit work windows
- avoid collisions with known external calendar commitments

This file powers the assistant-owned planning layer.

It is one of the core worker files for Phase 1.

---

## 5.7 `workers/jobs/fatigue_jobs.py`

Purpose:
- aggregates fatigue check-ins
- computes derived fatigue patterns by weekday and time bucket
- updates fatigue priors for decision-time reasoning

Responsibilities:
- read from `fatigue_checkins`
- optionally incorporate soft signals from `interaction_events`
- compute averages, ranges, variance, and confidence
- update `fatigue_patterns`

Important rule:
- explicit fatigue check-ins remain the strongest signal
- inferred behavior should not silently override explicit user input

---

## 5.8 `workers/jobs/memory_jobs.py`

Purpose:
- distills raw history into long-term learned memory
- updates confidence and recency
- archives or deactivates stale memories when needed

Responsibilities:
- scan repeated behavior
- detect patterns from acceptance, rejection, completion, and timing
- create compact memory objects
- deduplicate overlapping statements
- update embeddings if vector search is used

Examples of memories it may generate:
- user rejects long evening blocks on weekdays
- user accepts short focus sessions after 6 PM
- user prefers direct suggestions when fatigue is high

This is the core learning loop for personalization.

---

## 5.9 `workers/jobs/notification_jobs.py`

Purpose:
- delivers notifications to supported channels
- retries failed sends
- updates delivery state

Responsibilities:
- load queued notifications
- send to Telegram or web channel
- mark sent, failed, dismissed, or clicked states
- avoid duplicate sends

This file should only handle delivery behavior.

It should not decide which messages should exist. That decision belongs to services or watcher logic.

---

## 5.10 `workers/jobs/watcher_jobs.py`

Purpose:
- executes watcher evaluations on a schedule
- coordinates proactive system behavior

Responsibilities:
- run specific watcher modules
- collect results
- enqueue follow-up jobs
- write interaction logs

This file acts as a thin coordinator over the specialized watcher files.

---

## 5.11 `workers/jobs/cleanup_jobs.py`

Purpose:
- handles background cleanup and maintenance

Examples:
- expire old sync cursors
- archive stale notifications
- prune temporary job artifacts
- mark dead sync attempts
- compact stale worker metadata

This file keeps the system healthy without mixing maintenance into business logic.

---

## 5.12 `workers/watchers/deadline_watcher.py`

Purpose:
- finds tasks approaching deadline risk
- checks whether enough time remains
- triggers suggestions, reschedules, or reminder escalation

What it looks at:
- due dates
- task status
- estimated effort
- internal calendar coverage
- missed blocks

Typical actions:
- create high-priority internal calendar suggestion
- enqueue proactive reminder
- increase scheduling urgency

This is a core watcher for Phase 1.

---

## 5.13 `workers/watchers/overload_watcher.py`

Purpose:
- detects when the user’s upcoming schedule is too dense
- reduces overload before the user falls behind

What it looks at:
- task volume
- upcoming calendar density
- fatigue patterns
- missed or rejected suggestions
- available free windows

Typical actions:
- reduce plan complexity
- move lower-priority work forward or backward
- add buffer or recovery blocks
- send overload warning

---

## 5.14 `workers/watchers/inactivity_watcher.py`

Purpose:
- detects stale tasks, ignored suggestions, or silent drift

What it looks at:
- task inactivity
- unfinished internal calendar blocks
- ignored notifications
- lack of updates on active goals

Typical actions:
- send a low-friction nudge
- request a simple check-in
- trigger lightweight replan

---

## 5.15 `workers/watchers/connector_health_watcher.py`

Purpose:
- monitors connector reliability and token health

What it looks at:
- connector status
- token expiry windows
- repeated sync failures
- stale sync timestamps

Typical actions:
- flag connector as degraded
- enqueue reconnect prompt
- suppress connector-dependent workflows until healthy again

---

## 5.16 `workers/utils/locks.py`

Purpose:
- prevents duplicate or overlapping execution for sensitive jobs

Examples:
- only one sync job per connector account at a time
- only one nightly fatigue aggregation per user at a time
- only one reschedule computation per task window at a time

---

## 5.17 `workers/utils/dedupe.py`

Purpose:
- shared helper logic for duplicate detection

Examples:
- same Gmail message processed twice
- same memory statement produced from repeated scans
- same notification being enqueued more than once

---

## 5.18 `workers/utils/windowing.py`

Purpose:
- defines time windows used by jobs

Examples:
- next 14 days for calendar scan
- next 24 hours for deadline watcher
- previous 30 days for memory distillation evidence
- weekday and time-bucket grouping for fatigue aggregation

---

## 5.19 `workers/utils/retry.py`

Purpose:
- shared retry policy helpers
- centralized backoff settings
- job classification by retry safety

This helps keep failure handling consistent.

---

## 6. Queue Design

Recommended queues:

### 6.1 `connector_sync`

Used for:
- Gmail sync
- Google Calendar sync
- token-aware refresh jobs

Why separate:
- connector fetches may be slow or rate-limited
- failures should not block reminders or memory jobs

### 6.2 `normalization`

Used for:
- external data normalization
- candidate generation
- deduplication passes

Why separate:
- normalization is distinct from raw fetching
- easier to monitor conversion quality and failures

### 6.3 `planning`

Used for:
- internal calendar generation
- reschedule jobs
- suggestion generation

Why separate:
- planning jobs are central to product behavior
- may run frequently based on user actions and watchers

### 6.4 `fatigue`

Used for:
- fatigue pattern aggregation
- fatigue confidence updates

Why separate:
- predictable periodic jobs
- should not contend with connector throughput

### 6.5 `memory`

Used for:
- memory distillation
- embedding updates
- memory cleanup and confidence decay

Why separate:
- learning jobs are batch-like and can run off-peak

### 6.6 `notifications`

Used for:
- outbound notification delivery
- retry sends
- dismissal or click event processing if needed

Why separate:
- user-visible latency matters
- should stay responsive even when sync jobs are busy

### 6.7 `watchers`

Used for:
- deadline watcher
- overload watcher
- inactivity watcher
- connector health watcher

Why separate:
- recurring evaluation jobs are conceptually different from execution jobs

---

## 7. Main Job Flows

## 7.1 Google Calendar Sync Flow

1. scheduler triggers connector sync job
2. `connector_sync.py` loads connector and sync window
3. Google Calendar adapter fetches raw events
4. raw results are handed to normalization job
5. normalization maps events to internal event context objects
6. sync metadata is updated
7. planning jobs may be enqueued if schedule context changed
8. interaction event is written for audit and analytics

Operational effect:
- improves calendar awareness
- informs planning and overload detection
- does not directly create learned memory by itself

---

## 7.2 Gmail Sync Flow

1. scheduler or manual sync triggers Gmail sync job
2. `connector_sync.py` fetches messages in the target window
3. normalization extracts obligation or task-like signals
4. dedupe logic checks if signals were already processed
5. downstream service may create candidates or suggested actions
6. watcher or planning jobs may be triggered if deadlines or obligations are detected

Operational effect:
- Gmail becomes context for planning
- email should not create user tasks blindly without product rules

---

## 7.3 Internal Calendar Suggestion Flow

1. task is created or updated, or watcher identifies a risk
2. planning job is enqueued
3. `internal_calendar_jobs.py` inspects open tasks, current blocks, preferences, and fatigue patterns
4. job selects best execution windows
5. suggested blocks are written to `internal_calendar`
6. interaction event is stored
7. notification job may be enqueued

Operational effect:
- creates the assistant-owned schedule layer
- powers future task engine behavior

---

## 7.4 Fatigue Aggregation Flow

1. scheduler triggers aggregation job nightly or periodically
2. `fatigue_jobs.py` reads recent `fatigue_checkins`
3. groups data by weekday and time bucket
4. computes averages, ranges, variance, sample count, and confidence
5. updates `fatigue_patterns`
6. writes interaction event or metrics record

Operational effect:
- provides fatigue prior for in-prompt decisions
- improves future scheduling quality

---

## 7.5 Memory Distillation Flow

1. scheduler triggers memory job or event threshold triggers it
2. `memory_jobs.py` reads `interaction_events`, `calendar_feedback`, task outcomes, and fatigue signals
3. identifies repeated patterns
4. drafts compact memory statements
5. deduplicates against existing memories
6. updates `learned_memories`
7. optionally refreshes embeddings

Operational effect:
- converts noisy history into reusable personalization
- supports both planning and in-prompt decisions

---

## 7.6 Notification Delivery Flow

1. service or watcher creates notification row
2. notification delivery job is enqueued
3. `notification_jobs.py` sends to target channel
4. send result is recorded in `notifications`
5. failures retry with backoff

Operational effect:
- ensures reminders and proactive messages are reliable

---

## 8. Watcher Definitions

## 8.1 Deadline Watcher

Goal:
- prevent missed deadlines

Checks:
- tasks due soon
- insufficient planned work time
- repeated misses or reschedules

Can trigger:
- urgent suggestion block
- more direct notification
- replanning job

---

## 8.2 Overload Watcher

Goal:
- reduce near-term overload

Checks:
- too many high-effort tasks in same day
- low free-time coverage
- fatigue-prone windows overloaded

Can trigger:
- plan simplification
- buffer block creation
- lower-priority work movement

---

## 8.3 Inactivity Watcher

Goal:
- avoid silent drift and abandoned tasks

Checks:
- no activity on important tasks
- ignored suggestions
- no recent updates on live goals

Can trigger:
- small nudge
- quick check-in
- recovery suggestion

---

## 8.4 Connector Health Watcher

Goal:
- keep external data reliable

Checks:
- connector expiry
- stale sync state
- repeated fetch failures

Can trigger:
- reconnect prompt
- connector state downgrade
- sync suppression

---

## 9. Table Mapping for Worker Jobs

### Connector jobs mainly use
- `connectors`
- `interaction_events`
- connector-specific metadata storage if added later

### Planning jobs mainly use
- `tasks`
- `internal_calendar`
- `calendar_feedback`
- `user_preferences`
- `fatigue_patterns`

### Fatigue jobs mainly use
- `fatigue_checkins`
- `fatigue_patterns`
- `interaction_events`

### Memory jobs mainly use
- `interaction_events`
- `calendar_feedback`
- `fatigue_checkins`
- `fatigue_patterns`
- `learned_memories`

### Notification jobs mainly use
- `notifications`
- `tasks`
- `internal_calendar`

---

## 10. Sync vs Async Guidance

### Should happen synchronously in API
- create task row
- accept or reject a calendar block
- create fatigue check-in row
- create connector record after OAuth success
- create notification row if immediate acknowledgment is needed

### Should happen asynchronously in workers
- connector fetch and normalization
- fatigue pattern recomputation
- memory distillation
- planning and replanning scans
- notification delivery
- watcher evaluations

Rule:
- write operational truth first
- compute slow intelligence second

---

## 11. Failure Handling Rules

### Connector jobs
- retry for temporary network failures
- stop and mark degraded for auth failures
- do not duplicate normalized outputs on retry

### Planning jobs
- retry if transient DB or lock issues occur
- never create duplicate overlapping blocks from one trigger without dedupe

### Fatigue jobs
- safe to rerun for same aggregation window
- should update existing summaries rather than insert uncontrolled duplicates

### Memory jobs
- should use confidence updates and dedupe rules
- should avoid generating many near-identical memories

### Notification jobs
- must protect against duplicate sends
- should track provider message id when available

---

## 12. Build Order Recommendation

### Step 1
Build the worker foundation:
- `workers/rq.py`
- `workers/constants.py`
- `workers/scheduler.py`
- queue registration and local worker boot

### Step 2
Build connector background flows:
- `connector_sync.py`
- `connector_normalization.py`
- Gmail and Google Calendar sync paths

### Step 3
Build planning workers:
- `internal_calendar_jobs.py`
- deadline watcher
- overload watcher

### Step 4
Build fatigue intelligence:
- `fatigue_jobs.py`
- fatigue pattern aggregation schedule

### Step 5
Build learning loop:
- `memory_jobs.py`
- dedupe and confidence rules

### Step 6
Build delivery layer:
- `notification_jobs.py`
- channel adapters for Telegram and web

### Step 7
Build cleanup and health monitoring:
- `cleanup_jobs.py`
- connector health watcher
- inactivity watcher

---

## 13. Simple Mental Model

The API layer stores truth.

The worker layer:
- fetches external context
- transforms raw signals
- computes scheduling suggestions
- learns behavior over time
- sends proactive outputs
- keeps the system alive in the background

That means the backend is not just CRUD.
It is:
- an operational system of record
- a connector ingestion pipeline
- a planning engine
- a fatigue aggregation engine
- a long-term learning loop
- a watcher-based proactive assistant

---

## 14. Final Recommendation

For the current MVP, the worker layer should stay modular and predictable.

Use separate job files for:
- connector sync
- normalization
- internal planning
- fatigue aggregation
- memory distillation
- notifications
- watchers

This structure matches the product architecture, keeps the backend easy to extend, and supports both:
- Phase 1 proactive scheduling
- Phase 2 fatigue-aware in-prompt support
