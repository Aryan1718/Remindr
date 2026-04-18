# Internal Calendar - Implementation Context

Last updated: April 18, 2026

## 1. Purpose

The Internal Calendar is the system-owned scheduling layer used by the Future Task Engine.

Its purpose is not to replace Google Calendar or Outlook as the user's personal event calendar.

Its purpose is:

- act as the source of truth for system-planned work
- hold task blocks, focus sessions, recovery windows, and reminder timing
- support proactive scheduling and replanning
- separate assistant-managed plans from external calendar events
- provide a reliable planning layer for watchers, reminders, and scheduling logic

This is a core operational layer for Phase 1 of the product.

---

## 2. Why This Layer Exists

The assistant has two major modes:

### Phase 1 - Future Task Engine
This mode plans future work using:
- tasks
- internal scheduling
- reminders
- watchers
- proactive replanning

### Phase 2 - In-Prompt Decision Engine
This mode answers user questions in the moment using:
- memory
- fatigue layer
- current context

The Internal Calendar mainly supports Phase 1.

Without an Internal Calendar, the system has major limitations:

1. It cannot safely plan work independent of external connector APIs
2. It cannot maintain system-owned task blocks as durable state
3. It cannot replan confidently when tasks are missed or priorities change
4. It cannot support watchers and reminders with a consistent scheduling source
5. It becomes too dependent on external calendars for operational control

So this layer exists to give the assistant its own planning surface.

---

## 3. Product Definition

A clean product definition is:

> The Internal Calendar is the assistant's structured scheduling layer that stores system-planned work blocks, reminder timing, and replanning results, so the Future Task Engine can proactively organize user work without relying only on external calendars.

This means the Internal Calendar acts as:

- the system's planning calendar
- the source of truth for assistant-generated work blocks
- the target for schedule updates and replanning
- the operational context for watchers and reminders

---

## 4. Core Design Principle

The system should not schedule future work only inside free-text memory or inside external connectors.

Instead, future-task planning should use a dedicated structured layer.

Use three levels of calendar context:

### 1. External calendar context
This comes from Google Calendar, Outlook, or other providers.

Examples:
- meetings
- appointments
- class schedules
- travel blocks
- all-day events

This is input context.

### 2. Internal calendar plans
This is the assistant-owned schedule.

Examples:
- focus block for assignment
- recovery buffer
- interview prep block
- review session
- catch-up block
- fallback reschedule block

This is operational state.

### 3. Actual outcome signals
This shows what happened after planning.

Examples:
- task completed on time
- task delayed
- block skipped
- reminder snoozed
- plan overridden by user

This is learning and feedback.

The Internal Calendar sits in the middle of these three and allows the system to continuously plan and adapt.

---

## 5. Scope of the Internal Calendar

This layer should support:

- system-generated work blocks
- block updates and rescheduling
- conflict-aware planning
- reminder coordination
- watcher-driven schedule changes
- future proactive execution support

This layer should not do:

- replace the user's external calendar UI
- become a full collaborative meeting platform
- store connector OAuth state
- hold free-text learned memory as its primary function

It is a planning and execution layer, not a personal productivity app clone.

---

## 6. What the Layer Produces

The output of the Internal Calendar is not one single object. It produces durable scheduling state.

Examples of what it should contain:

- planned focus blocks
- task time allocations
- rescheduled work blocks
- protected break windows
- urgency-driven recovery slots
- links between tasks and their calendar placements
- statuses that show whether blocks are planned, started, missed, completed, or moved

Example internal block shape:

```json
{
  "block_id": "uuid",
  "user_id": "uuid",
  "task_id": "uuid",
  "block_type": "focus",
  "scheduled_start": "2026-04-19T08:00:00-07:00",
  "scheduled_end": "2026-04-19T09:30:00-07:00",
  "status": "planned",
  "generated_by": "scheduler",
  "reason_summary": "Best available focus window before deadline risk increases"
}
```

This state should then be used by reminders, watchers, and future scheduling logic.

---

## 7. High-Level Architecture

The Internal Calendar should contain five major parts:

1. Calendar event model
2. Scheduling and slot allocation logic
3. Conflict detection and resolution
4. Replanning and update logic
5. Reminder and watcher coordination

---

## 8. Component 1 - Calendar Event Model

The system needs a consistent internal representation for assistant-managed time blocks.

These should include:

### A. Focus blocks
Primary work sessions for tasks.

Examples:
- 90-minute writing block
- 45-minute job application session
- 30-minute revision block

### B. Break or recovery blocks
These protect user energy.

Examples:
- 15-minute buffer after class
- 30-minute recovery window after intense work
- overflow margin before important deadline work

### C. Review or checkpoint blocks
These support progress verification.

Examples:
- review resume changes
- validate assignment submission checklist
- confirm job application materials

### D. Reschedule placeholders
Used when a task cannot be completed in the current slot.

Examples:
- fallback block for tomorrow morning
- catch-up window before final deadline

The key idea is that the Internal Calendar stores assistant-generated operational blocks, not just copied external events.

---

## 9. Component 2 - Scheduling and Slot Allocation

This is the heart of the Future Task Engine.

The scheduler should take:

- active tasks
- deadlines
- estimated effort
- priority
- urgency
- energy requirement
- available windows
- external calendar constraints
- internal calendar occupancy
- fatigue-aware preferences later

Then it should produce one or more calendar blocks.

### Scheduler responsibilities

- find open windows
- score candidate windows
- assign best-fit slot
- split large tasks if needed
- avoid overload
- preserve slack
- replan when conflicts arise

### Basic scheduling logic

At a high level:

1. pull active tasks needing placement
2. pull external calendar events
3. pull existing internal blocks
4. compute free windows
5. score windows
6. create task blocks
7. store blocks in internal calendar
8. trigger reminders if needed

The scheduler should be deterministic enough to debug, even if later it uses learned scoring.

---

## 10. Component 3 - Conflict Detection and Resolution

The Internal Calendar needs to detect conflicts against both internal and external schedules.

### Types of conflicts

#### A. Hard conflicts
Examples:
- overlaps with external meeting
- overlaps with another internal task block
- scheduled outside allowed hours

These blocks should not be placed.

#### B. Soft conflicts
Examples:
- high-effort task placed late at night
- too many intense blocks in a row
- no recovery buffer after demanding session
- schedule becomes too dense

These may be allowed but should reduce window score.

### Conflict resolution options

- shift to next best slot
- split task into smaller blocks
- downgrade optional blocks
- create reminder-only plan if no slot fits
- escalate deadline risk to watcher system

This is one reason the Internal Calendar must be system-owned. The assistant needs a place where it can safely make these decisions.

---

## 11. Component 4 - Replanning and Update Logic

The Internal Calendar is not static. It must support continuous adjustment.

### Replanning triggers

- new task added
- deadline changed
- user rejects a recommendation
- task block missed
- task took longer than expected
- reminder ignored repeatedly
- watcher detects overload
- user explicitly says "move this"

### Replanning actions

- move future blocks
- split remaining work
- create recovery slots
- raise reminder priority
- reduce block size
- create catch-up plan

### Important principle

Replanning should not rewrite history.

Past blocks should remain recorded with their actual outcome status.
Future blocks can be updated.

This is important for explainability and learning.

---

## 12. Component 5 - Reminder and Watcher Coordination

The Internal Calendar is tightly connected to reminders and watchers.

### Reminder coordination

For each internal block, the system may generate:
- pre-block reminder
- high-priority reminder for risky tasks
- fallback reminder if previous reminder was ignored

Reminder behavior should depend on:
- urgency
- user preference
- historical follow-through
- task importance

### Watcher coordination

Watchers should observe internal calendar state and trigger actions.

Examples:
- deadline risk watcher checks if enough time is allocated before due date
- schedule overload watcher checks density and stress risk
- inactivity watcher checks if planned blocks are repeatedly skipped

The Internal Calendar provides the structured timeline they need to operate.

---

## 13. Recommended Data Model

The current schema already has a good base with `task_blocks`, but the Internal Calendar should be thought of as a calendar layer made from multiple tables working together.

Core related tables:

- `tasks`
- `task_blocks`
- `reminders`
- `watchers`
- `watcher_runs`
- `notifications`
- `calendar_events` for external context

### Existing `task_blocks` concept
This is the strongest base for the Internal Calendar.

It already captures:
- user
- task
- scheduled start
- scheduled end
- block type
- status
- generated_by

That is the right direction.

### Recommended enhancement to `task_blocks`

If you want a more explicit Internal Calendar model later, extend it with fields like:

```sql
alter table task_blocks
add column reason_summary text,
add column reschedule_count integer not null default 0,
add column source_calendar text default 'internal',
add column priority_snapshot smallint,
add column energy_snapshot smallint,
add column metadata_json jsonb not null default '{}'::jsonb;
```

This is optional, but useful.

---

## 14. Should There Be a Separate internal_calendar Table?

For MVP, you probably do not need a separate `internal_calendar` table if:

- `task_blocks` already represents calendar placements
- `calendar_events` stores normalized external events
- reminders and watcher tables are already linked

In that model:

- `task_blocks` = internal calendar entries
- `calendar_events` = external calendar entries

That is a clean and simple architecture.

However, if later you want:
- multiple internal calendars
- named planning views
- category-based scheduling calendars
- more advanced calendar metadata

then you can introduce a true `internal_calendars` table.

### Suggested MVP recommendation

Do not over-model this initially.

Use:
- `task_blocks` as the internal calendar event table
- external `calendar_events` as context input
- scheduler + watchers as logic layer

This is simpler and likely enough for hackathon and MVP.

---

## 15. Scheduling Inputs

The Internal Calendar scheduling logic should consider:

### Required inputs
- active tasks
- due dates
- estimated duration
- task priority
- user timezone
- external calendar occupancy
- existing internal block occupancy

### High-value optional inputs
- task energy requirement
- preferred work hours
- reminder tolerance
- fatigue patterns
- past completion behavior
- block size preference

### Future inputs
- sleep signals
- commute windows
- wearable signals
- location changes
- dynamic calendar importance classification

MVP should focus on required inputs first.

---

## 16. Suggested Window Scoring Model

The scheduler should use a hybrid scoring model.

### Hard filters
Remove windows that:
- overlap external events
- overlap internal blocks
- are too short
- violate explicit user constraints

### Soft scoring factors
Score remaining windows using:
- deadline fit
- urgency fit
- effort fit
- energy fit
- schedule density penalty
- lateness penalty
- buffer preservation
- learned preference alignment later

Example conceptual score:

```text
window_score =
  deadline_fit
  + urgency_fit
  + effort_fit
  + energy_fit
  - overload_penalty
  - late_night_penalty
  - fragmentation_penalty
```

This does not need to be ML-heavy for MVP. A transparent heuristic is better first.

---

## 17. How the Internal Calendar Supports the User Experience

Example:

User adds:
- "Finish operating systems assignment"
- estimated time = 3 hours
- due tomorrow night

System flow:

1. scheduler detects only 90 minutes free tonight and 2 hours free tomorrow morning
2. scheduler creates:
   - tonight 8:00 PM to 9:30 PM focus block
   - tomorrow 8:00 AM to 9:30 AM focus block
   - tomorrow 9:45 AM to 10:15 AM final review block
3. reminders are created for each block
4. deadline watcher confirms enough planned time exists

This is much better than storing a task without operational placement.

---

## 18. How It Uses External Calendar Data

The Internal Calendar should not blindly mirror external events.

Instead, external calendars are used as constraints and context.

Use external `calendar_events` to answer:
- when is the user busy?
- where are free windows?
- are there high-stress adjacent events?
- should a work block be avoided before or after a meeting?

External calendar data is input.
Internal calendar state is output.

That separation is important.

---

## 19. Worker Design

The Internal Calendar needs background workers.

Recommended workers:

### A. scheduler_worker
Responsibilities:
- place new tasks into task blocks
- update schedule when tasks change
- find best windows
- create internal calendar entries

### B. replanning_worker
Responsibilities:
- respond to missed blocks
- update downstream task placements
- re-balance future schedule

### C. reminder_dispatch_worker
Responsibilities:
- check upcoming internal blocks
- send reminders through preferred channel
- escalate if needed

### D. schedule_health_watcher
Responsibilities:
- inspect internal calendar for overload or under-allocation
- trigger interventions when risk rises

These workers should be separated enough to keep the system understandable.

---

## 20. Retrieval Pattern at Runtime

When the Future Task Engine needs to schedule or replan, it should do:

1. fetch active tasks
2. fetch relevant external calendar events
3. fetch future internal blocks
4. compute open windows
5. score candidate slots
6. write updated task blocks
7. adjust reminders
8. notify watchers if risk remains

This should be the core runtime planning loop.

---

## 21. Example API Contract

Internal service request:

```json
{
  "user_id": "uuid",
  "trigger_type": "task_created",
  "task_id": "uuid",
  "request_time": "2026-04-18T14:00:00-07:00"
}
```

Response:

```json
{
  "result": "scheduled",
  "blocks_created": [
    {
      "task_id": "uuid",
      "scheduled_start": "2026-04-18T20:00:00-07:00",
      "scheduled_end": "2026-04-18T21:30:00-07:00",
      "block_type": "focus"
    }
  ],
  "reminders_created": 1,
  "risk_flags": []
}
```

This response should then feed reminders and notifications.

---

## 22. Prompting and LLM Usage

Do not use an LLM as the primary scheduler.

Use deterministic scheduling first:
- window finding
- conflict detection
- scoring
- block placement
- replanning logic

Use LLMs only where they add value:

- summarizing the plan to the user
- explaining why a block was placed
- helping convert vague goals into structured tasks
- optionally suggesting fallback strategies when schedule risk is high

The Internal Calendar itself should remain structured and deterministic.

---

## 23. MVP Implementation Plan

### Step 1
Use `tasks` as the source of work items.

### Step 2
Use `calendar_events` as normalized external busy-time input.

### Step 3
Use `task_blocks` as internal calendar entries.

### Step 4
Build a scheduler worker that creates blocks from tasks.

### Step 5
Build a reminder worker linked to upcoming task blocks.

### Step 6
Build a basic overload and deadline watcher.

### Step 7
Add replanning when blocks are missed or tasks change.

### Step 8
Later, add fatigue-aware slot scoring.

This gives a realistic MVP with strong future extensibility.

---

## 24. Metrics to Track

The Internal Calendar should be evaluated as an execution capability.

### Planning quality metrics
- percentage of tasks that receive valid placements
- average time from task creation to scheduled placement
- scheduling conflict rate
- percentage of tasks with enough planned time before due date

### Execution metrics
- block completion rate
- reminder follow-through rate
- missed-block rate
- reschedule frequency
- deadline success rate

### Experience metrics
- user override rate
- perceived usefulness of scheduled plan
- notification annoyance rate
- correction rate for bad placements

These metrics will show whether the calendar layer is truly helping.

---

## 25. Risks and Mitigations

### Risk 1 - Over-scheduling
Mitigation:
- preserve slack
- avoid filling every free minute
- apply density penalties

### Risk 2 - Bad placements
Mitigation:
- use hard constraints first
- keep scoring explainable
- support easy replanning

### Risk 3 - External dependency problems
Mitigation:
- keep internal calendar independent
- treat connector data as input, not ownership layer

### Risk 4 - Too much complexity for MVP
Mitigation:
- start with `task_blocks`
- avoid extra tables unless needed
- keep the scheduler heuristic-based first

### Risk 5 - User distrust
Mitigation:
- show why tasks were scheduled
- allow override
- keep history of changes
- make reminders adaptive, not noisy

---

## 26. Final Recommendation

Build the Internal Calendar as the backbone of Phase 1.

At MVP, it should include:

- structured task blocks as internal calendar entries
- external calendar normalization as input context
- deterministic scheduler logic
- reminders linked to blocks
- watcher-driven replanning
- durable operational state for future work execution

The most important architectural decision is this:

> treat the Internal Calendar as the assistant's own planning and execution surface, not as a mirror of external calendars and not as a free-text planning memory.

That gives the system:
- reliable scheduling state
- proactive planning ability
- clear reminder coordination
- durable replanning support
- a strong foundation for later fatigue-aware scheduling
