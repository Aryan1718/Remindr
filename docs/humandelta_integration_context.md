# HumanDelta Integration Context
*Fatigue-Aware Personal Assistant*

Last updated: April 18, 2026

## 1. Purpose

This document defines how HumanDelta should be integrated into the Fatigue-Aware Personal Assistant.

The goal is to use HumanDelta as a **quality and validation layer** around the system, not as the main reasoning engine and not as the database.

HumanDelta should help improve:

- connector-derived signal quality
- reliability of learned memory
- long-term decision improvement
- trust in what the system stores and uses

This integration must respect the current architecture:

- Supabase remains the source of truth
- backend services remain the operational owner
- internal calendar remains the assistant-owned planning layer
- fatigue layer remains the system's bandwidth estimation layer
- HumanDelta remains a validation and evaluation layer

---

## 2. Core Decision

We are **not** using HumanDelta:

- as the primary AI agent
- as the database
- as the scheduler
- as the fatigue estimator
- as the real-time decision engine

We **are** using HumanDelta:

- after connector normalization
- before certain important records are persisted
- after memory candidates are generated
- after decisions are made, for async evaluation

### One-line definition

> HumanDelta is a trust and knowledge-quality layer that helps the system decide whether connector signals, memory candidates, and past decisions are good enough to use.

---

## 3. Relationship with Existing Architecture

## 3.1 What stays the same

### Supabase
Supabase remains the main system of record for:

- users
- user preferences
- connectors
- tasks
- internal calendar
- fatigue check-ins
- fatigue patterns
- learned memories
- notifications
- interaction events

### Backend
The backend remains responsible for:

- APIs
- orchestration
- scheduling
- memory distillation
- fatigue estimation
- worker execution
- notification delivery

### Internal Calendar
The internal calendar remains the assistant-owned operational planning layer.

### Fatigue Layer
The fatigue layer remains the main structured estimator of user bandwidth.

---

## 3.2 What HumanDelta adds

HumanDelta adds a new supporting layer:

- validates connector-derived signals
- validates memory candidates before durable storage
- evaluates decision quality after user outcomes are observed
- helps reduce low-quality or premature learned behavior

---

## 4. High-Level Placement

## 4.1 Connector path

```text
Connectors -> Normalize -> HumanDelta validation -> Product signals -> Supabase
```

## 4.2 Memory path

```text
Interaction events + feedback -> Memory candidate generation -> HumanDelta validation -> learned_memories
```

## 4.3 Decision feedback path

```text
Decision created -> User outcome observed -> HumanDelta evaluation -> Improvement signals stored
```

---

## 5. Main Integration Areas

## 5.1 Connector Validation Layer

This is the most important place to use HumanDelta first.

### Why
Raw connector data is noisy.
Even normalized connector data may still contain weak, ambiguous, or non-actionable information.

Examples:
- an email that sounds important but has no real obligation
- a calendar event that should not become a planning constraint
- a message that should not become a task

### What HumanDelta should do here
After Gmail or Google Calendar data is normalized, HumanDelta should help answer:

- is this signal actionable?
- is this signal strong enough to create a task?
- is this signal only background context?
- is this signal too weak or ambiguous to persist into core product state?

### Example
Normalized email candidate:

```json
{
  "type": "email_obligation_candidate",
  "subject": "Reminder",
  "snippet": "Let's catch up sometime next week.",
  "due_at": null
}
```

Possible HumanDelta output:

```json
{
  "is_actionable": false,
  "confidence": 0.32,
  "reason": "No clear action, no deadline, no explicit obligation"
}
```

### Product effect
Only validated signals should become:

- tasks
- high-priority reminders
- internal calendar suggestion inputs
- memory evidence candidates

### Important rule
HumanDelta should not directly write to the database.
The backend service layer still decides what gets stored.

---

## 5.2 Memory Validation Layer

This is the second most important place to use HumanDelta.

### Why
Learned memory is powerful but risky.
If weak patterns are stored too early, the assistant starts learning the wrong things.

Examples of risky memory:
- "User hates working at night" after only one rejection
- "User prefers direct answers" after one short reply
- "User is always overloaded on Wednesdays" from sparse evidence

### What HumanDelta should do here
Before a memory candidate becomes a durable learned memory, HumanDelta should help answer:

- is there enough evidence?
- is the evidence consistent?
- is the pattern recent enough?
- is the pattern too broad or too weak?
- is the evidence conflicting?

### Example
Candidate memory:

```json
{
  "statement": "User prefers morning work",
  "evidence_count": 2,
  "domains": ["task", "calendar"],
  "source": "behavior"
}
```

Possible HumanDelta output:

```json
{
  "status": "reject",
  "confidence": 0.41,
  "reason": "Insufficient repeated evidence"
}
```

### Product effect
Only validated memory candidates should be written into `learned_memories`.

This improves:
- personalization quality
- fatigue-aware recommendations
- trust in behavioral learning

---

## 5.3 Decision Evaluation Layer

This is a useful later-stage integration.

### Why
After a recommendation is made, the system can learn from what happened next.

Examples:
- user accepted suggestion
- user rejected suggestion
- user ignored suggestion
- task was completed successfully
- task was delayed again

HumanDelta can evaluate whether the original decision was likely good or poor.

### What HumanDelta should do here
It should help answer:

- was the recommendation aligned with available evidence?
- was the recommendation too aggressive?
- was the suggestion inconsistent with fatigue or recent behavior?
- should a negative outcome become a learning signal?

### Example
Original decision:
- "Do a 2-hour deep work block at 10 PM"

Observed outcome:
- user rejected
- fatigue score = 4
- similar late-night blocks rejected before

Possible HumanDelta output:

```json
{
  "decision_quality": "poor",
  "confidence": 0.84,
  "reason": "Recommendation conflicts with repeated late-night rejection pattern"
}
```

### Product effect
This evaluation can be stored and later used for:
- decision engine tuning
- scheduling improvements
- memory distillation support
- trust analytics

---

## 6. Where HumanDelta Should NOT Be Used

## 6.1 Not in real-time user response path

Do not call HumanDelta directly inside:

- `/decision/query`
- Telegram message reply generation
- fatigue estimation request path
- immediate internal calendar scoring path

### Why
These flows must stay:
- fast
- deterministic enough to debug
- resilient to external dependency failure

HumanDelta should remain async wherever possible.

---

## 6.2 Not as database replacement

HumanDelta is not a database.
It should not replace Supabase or pgvector.

Supabase remains responsible for:
- persistence
- querying
- structured product state
- vector memory storage

---

## 6.3 Not as scheduler replacement

HumanDelta should not decide:
- which block gets scheduled where
- how the internal calendar resolves conflicts
- how fatigue scores are computed

Those remain inside:
- scheduling workers
- internal calendar service
- fatigue layer
- decision service

---

## 7. Recommended Integration Model

## 7.1 HumanDelta as an internal service dependency

Create a dedicated service layer:

```text
backend/
  app/
    services/
      humandelta/
        humandelta_client.py
        humandelta_mapper.py
        humandelta_service.py
```

### File purposes

#### `humandelta_client.py`
Responsible for:
- outbound API calls to HumanDelta
- authentication and request handling
- timeout and retry-safe request patterns

#### `humandelta_mapper.py`
Responsible for:
- mapping internal objects into HumanDelta request payloads
- mapping HumanDelta responses into internal validation shapes

#### `humandelta_service.py`
Responsible for:
- deciding when HumanDelta should be called
- exposing helper methods for connector validation, memory validation, and decision evaluation
- shielding the rest of the backend from provider-specific details

---

## 7.2 Worker-first execution

HumanDelta should mainly be used through workers, not directly from routes.

Recommended worker additions:

```text
backend/
  app/
    workers/
      jobs/
        humandelta_connector_validation.py
        humandelta_memory_validation.py
        humandelta_decision_evaluation.py
```

### Why workers
This keeps:
- API latency low
- error handling cleaner
- retries safer
- integration optional and non-blocking

---

## 8. Detailed Flow Design

## 8.1 Connector validation flow

### Step-by-step
1. connector sync job fetches provider data
2. normalization job converts provider payloads into internal shapes
3. backend produces candidate signals
4. HumanDelta validation job checks candidate quality
5. accepted signals are passed to service layer
6. service layer writes final product records into Supabase

### Candidate examples
- email_obligation_candidate
- email_deadline_candidate
- calendar_constraint_candidate
- calendar_busy_window_candidate

### Final records that may be created
- `tasks`
- internal calendar planning inputs
- `notifications`
- `interaction_events`

### Important rule
HumanDelta should influence whether the signal is trusted, but the backend still owns final write decisions.

---

## 8.2 Memory validation flow

### Step-by-step
1. interaction events and feedback accumulate
2. memory distillation job creates candidate memory
3. HumanDelta validation job checks pattern quality
4. accepted memory is persisted into `learned_memories`
5. rejected memory is dropped or stored as weak evidence only

### Candidate examples
- user rejects long evening work blocks
- user prefers decisive recommendations when tired
- user accepts short review blocks on weekdays

### Persistence rule
Only validated, high-confidence memory should enter `learned_memories`.

---

## 8.3 Decision evaluation flow

### Step-by-step
1. decision engine returns recommendation
2. system stores decision event
3. user behavior produces outcome signal
4. evaluation job packages original decision + outcome
5. HumanDelta evaluates quality
6. evaluation record is stored
7. future learning jobs use this evidence

### Outcome examples
- accepted and completed
- rejected with fatigue reason
- ignored
- rescheduled
- failed follow-through

---

## 9. Suggested Database Support

HumanDelta does not replace existing tables.
But we should add one support table to keep evaluation output structured.

## 9.1 Recommended table: `humandelta_evaluations`

```sql
create table humandelta_evaluations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  evaluation_type text not null,
  reference_type text not null,
  reference_id uuid,
  status text not null,
  confidence numeric(4,3) not null default 0.500,
  reason text,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

### Purpose
Store HumanDelta results for:
- connector validation
- memory validation
- decision evaluation

### Example values

#### Connector validation
- `evaluation_type = 'connector_validation'`
- `reference_type = 'email_candidate'`

#### Memory validation
- `evaluation_type = 'memory_validation'`
- `reference_type = 'memory_candidate'`

#### Decision evaluation
- `evaluation_type = 'decision_evaluation'`
- `reference_type = 'decision_request'`

---

## 10. Relationship to Existing Tables

## 10.1 `connectors`
No change in core ownership.
Connector account metadata remains here.

## 10.2 External normalized connector tables
HumanDelta should validate normalized records before they produce product actions.

Recommended relevant tables:
- `external_calendar_events`
- `external_email_items`

### Role
HumanDelta helps classify whether normalized external rows should become stronger product signals.

## 10.3 `tasks`
HumanDelta may influence whether a candidate becomes a task.
It does not own task writes.

## 10.4 `internal_calendar`
HumanDelta should not own scheduling logic.
But validated connector signals may influence scheduling inputs.

## 10.5 `learned_memories`
HumanDelta is very useful before new memory is written here.

## 10.6 `interaction_events`
This remains a major source for:
- memory candidate generation
- decision evaluation evidence

## 10.7 `fatigue_checkins` and `fatigue_patterns`
These remain owned by the fatigue layer.
HumanDelta should not replace fatigue estimation.

---

## 11. Recommended Usage Rules

## Rule 1
Use HumanDelta only for **high-value validation points**, not for every minor event.

## Rule 2
Keep HumanDelta **off the critical request path**.

## Rule 3
Treat HumanDelta as **advisory validation**, not the final source of truth.

## Rule 4
Persist HumanDelta outcomes in your own database for auditability.

## Rule 5
Do not let HumanDelta directly mutate scheduling, fatigue, or database state.

---

## 12. MVP Integration Scope

## Include in MVP
- connector signal validation for Gmail and Google Calendar
- memory candidate validation before `learned_memories`
- optional simple decision evaluation logging

## Exclude from MVP
- real-time decision dependency
- scheduling dependency
- fatigue estimation dependency
- automatic direct writes from HumanDelta to product tables
- broad validation of every interaction event

---

## 13. Rollout Plan

## Phase 1 - Connector validation
First implement HumanDelta for:
- normalized Gmail obligation candidates
- normalized calendar planning candidates

### Goal
Prevent weak or noisy external data from creating low-quality product state.

---

## Phase 2 - Memory validation
Then implement HumanDelta for:
- distilled memory candidate validation

### Goal
Ensure only strong behavioral patterns become durable memory.

---

## Phase 3 - Decision evaluation
Then implement HumanDelta for:
- post-decision evaluation

### Goal
Improve long-term system judgment without slowing real-time flows.

---

## 14. Benefits

If integrated correctly, HumanDelta can improve:

- connector signal quality
- quality of created tasks
- trust in learned memory
- explainability of why something was stored or rejected
- long-term decision quality
- confidence in personalization

---

## 15. Risks and Mitigations

## Risk 1 - Too much dependency on external service
### Mitigation
Keep HumanDelta async and advisory only.

## Risk 2 - Added complexity too early
### Mitigation
Start only with connector validation.

## Risk 3 - Duplicate logic with backend rules
### Mitigation
Keep deterministic backend rules for hard checks and use HumanDelta only for gray-area validation.

## Risk 4 - Latency creep
### Mitigation
Never place HumanDelta in the real-time decision path for MVP.

---

## 16. Final Recommendation

The best way to integrate HumanDelta into this product is:

- not as the brain
- not as the database
- not as the scheduler

But as a **knowledge quality and trust layer** that validates:
- external connector signals
- long-term memory candidates
- past decision quality

### Final one-line summary

> Supabase stores the truth, the backend runs the product, and HumanDelta checks whether important signals are trustworthy enough to use.
