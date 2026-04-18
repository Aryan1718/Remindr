# Fatigue Layer - Implementation Context

Last updated: April 18, 2026

## 1. Purpose

The Fatigue Layer is a dedicated system layer that helps the assistant estimate the user's likely mental bandwidth at the moment a decision is needed.

Its main purpose is not generic wellness tracking and not only survey collection.

Its purpose is:

- improve in-prompt decision quality
- increase confidence when answering real-time questions
- reduce the need to ask the user for fatigue every time
- adapt response style to likely cognitive state
- provide a structured fatigue prior for the decision engine

This layer is especially important for questions like:

- "Should I do this now?"
- "What should I focus on first?"
- "Can I handle this tonight?"
- "Should I postpone this?"
- "Give me the best option right now"

In these cases, the assistant should not answer as if the user has the same energy at all times. It should use learned fatigue patterns, recent signals, and current context to estimate how much complexity the user can handle.

---

## 2. Why This Layer Exists

The system has two major operating modes:

### Phase 1 - Future Task Engine
This mode is planner-oriented:
- internal calendar
- scheduler
- reminders
- watchers
- proactive task timing

### Phase 2 - In-Prompt Decision Engine
This mode is decision-oriented:
- user asks a question now
- system must answer now
- answer should fit the user's likely current bandwidth

The Fatigue Layer mainly supports Phase 2, but it can also improve Phase 1 later by helping the scheduler place demanding work into stronger energy windows.

Without a Fatigue Layer, the assistant has three problems:

1. It guesses too much about current user capacity
2. It may suggest high-effort actions at low-energy times
3. It cannot confidently choose between exploratory, guided, or decisive response styles

So this layer exists to give the rest of the system a structured estimate of likely fatigue at decision time.

---

## 3. Product Definition

A clean product definition is:

> The Fatigue Layer is a structured inference and memory layer that estimates a user's likely mental bandwidth for the current timeframe using historical patterns, recent signals, and optional live check-ins, so the assistant can make better in-the-moment decisions.

This means the layer should act as:

- a memory-backed fatigue prior
- a fallback when no live fatigue input exists
- a confidence signal for the decision engine
- a response-mode selector

---

## 4. Core Design Principle

The system should not depend on only one type of fatigue signal.

Instead, fatigue estimation should be hybrid.

Use three levels:

### 1. Live fatigue
What the user explicitly says right now.

Example:
- user says fatigue is 4
- user says "I am exhausted"
- user says "I have no energy right now"

This is highest-value input when available.

### 2. Recent fatigue state
What the system can infer from short-term signals.

Example:
- user ignored reminders all evening
- user delayed multiple tasks
- user responded slowly
- schedule has been overloaded today

This is a useful secondary signal.

### 3. Historical fatigue pattern
What the system knows about this user's usual energy in the current time window.

Example:
- mornings are usually strong
- late evenings are usually weak
- Sunday nights are consistently low-bandwidth
- Tuesdays after class are usually depleted

This is the long-term fatigue memory.

The Fatigue Layer combines these signals into one fatigue estimate.

---

## 5. Scope of the Fatigue Layer

This layer should support:

- time-aware fatigue estimation
- response-style adaptation
- decision confidence scoring
- long-term personalization
- future scheduling enhancement

This layer should not do:

- clinical mental health diagnosis
- therapy or emotional counseling
- health-risk analysis beyond basic caution
- final truth storage for non-fatigue operational data

It is a decision-support layer, not a medical layer.

---

## 6. What the Layer Produces

The output of the Fatigue Layer should be a structured fatigue state object.

Example:

```json
{
  "estimated_fatigue_score": 4,
  "source_mix": {
    "live_checkin": false,
    "recent_signals": true,
    "historical_pattern": true
  },
  "time_bucket": "night",
  "pattern_confidence": 0.84,
  "estimation_confidence": 0.78,
  "mode_recommendation": "decisive",
  "reason_summary": [
    "User is usually high-fatigue at night",
    "Two tasks were postponed today",
    "No live check-in is available"
  ]
}
```

This output should then be consumed by the In-Prompt Decision Engine.

---

## 7. High-Level Architecture

The Fatigue Layer should contain five major parts:

1. Fatigue signal collection
2. Fatigue memory and pattern store
3. Fatigue inference engine
4. Response-mode mapping
5. Feedback and learning loop

---

## 8. Component 1 - Fatigue Signal Collection

The layer needs input data from multiple sources.

### A. Explicit user check-ins
This is the cleanest signal.

Examples:
- quick 0-5 fatigue check
- user-entered notes
- optional weekly summary
- inline prompt when decision confidence is low

Use this sparingly. The product should not annoy the user by asking too often.

### B. Conversational signals
These come from message content.

Examples:
- "I am tired"
- "I cannot think right now"
- "I am overwhelmed"
- "I do not want too many options"

These can be turned into soft fatigue evidence.

### C. Interaction behavior
These come from system behavior logs.

Examples:
- recommendation accepted quickly
- recommendation ignored repeatedly
- reminders snoozed several times
- user postpones tasks at certain times
- user abandons long tasks after 9 PM

These are very important because the system should learn from actions, not only words.

### D. Time and routine context
Examples:
- time of day
- day of week
- workday vs weekend
- before class or after class
- post-meeting windows
- known commute windows

This provides context for historical pattern retrieval.

### E. Future optional signals
These can be added later:
- sleep integration
- wearable data
- screen time
- step count
- calendar density
- location patterns

These are not required for MVP.

---

## 9. Component 2 - Fatigue Memory and Pattern Store

The Fatigue Layer needs both raw data and derived data.

### Raw data
This should capture actual fatigue-related events and evidence:
- explicit fatigue check-ins
- inferred fatigue signals
- interaction logs
- message evidence

### Derived data
This should store aggregated fatigue patterns the system can use quickly at decision time.

The main idea is:

- raw data is messy and event-based
- derived data is stable and decision-ready

### Recommended memory structure

Use three storage levels:

#### 1. `fatigue_checkins`
Stores explicit fatigue scores.

This already fits the current schema direction.

#### 2. `interaction_events`
Stores raw behavioral evidence.

This already fits the current schema direction.

#### 3. `fatigue_patterns`
New derived table for time-bucket fatigue summaries.

This new table is the most important addition.

---

## 10. Proposed Time Buckets

For MVP, use simple fixed time buckets.

Recommended:

- morning = 05:00 to 11:59
- afternoon = 12:00 to 16:59
- evening = 17:00 to 20:59
- night = 21:00 to 04:59

Why this works:
- simple
- interpretable
- good enough for decision mode selection
- easy to explain and debug

Later, the system can move to more adaptive buckets if needed.

Examples:
- weekday morning vs weekend morning
- post-class depletion window
- pre-meeting tension window

But MVP should start simple.

---

## 11. Proposed Database Additions

## 11.1 fatigue_patterns

This is a derived table that stores the user's learned fatigue profile by time bucket.

```sql
create table fatigue_patterns (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  weekday smallint,
  time_bucket text not null,
  avg_fatigue numeric(4,2),
  min_fatigue numeric(4,2),
  max_fatigue numeric(4,2),
  fatigue_variance numeric(6,3),
  sample_count integer not null default 0,
  confidence numeric(4,3) not null default 0.500,
  trend_direction text,
  last_signal_at timestamptz,
  last_computed_at timestamptz not null default now(),
  metadata_json jsonb not null default '{}'::jsonb,
  unique(user_id, weekday, time_bucket)
);
```

### Purpose of key fields

- `weekday`: optional dimension for weekday-specific patterns
- `time_bucket`: morning, afternoon, evening, night
- `avg_fatigue`: central estimate for this bucket
- `fatigue_variance`: stability of the pattern
- `sample_count`: amount of evidence
- `confidence`: how much the system trusts this pattern
- `trend_direction`: improving, worsening, stable
- `last_signal_at`: freshness of evidence

---

## 11.2 fatigue_signal_events

Optional but recommended if you want a cleaner separation between generic interaction events and fatigue-specific evidence.

```sql
create table fatigue_signal_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  signal_type text not null,
  signal_source text not null,
  inferred_score numeric(4,2),
  confidence numeric(4,3) not null default 0.500,
  related_entity_type text,
  related_entity_id uuid,
  evidence_text text,
  context_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

This is optional because some teams may prefer to store all signal evidence in `interaction_events`.

---

## 12. Confidence Model

Confidence is critical. The system should not act equally sure in all situations.

The Fatigue Layer should output two kinds of confidence:

### A. Pattern confidence
How stable the long-term time-bucket pattern is.

Example:
- 40 nights with similar fatigue scores -> high confidence
- only 2 afternoon signals -> low confidence

### B. Estimation confidence
How confident the system is in the current fatigue estimate.

This depends on:
- whether live fatigue exists
- amount of recent evidence
- stability of historical pattern
- freshness of data
- whether different signals agree

Example:
- live check-in + stable pattern + matching recent behavior -> very high confidence
- no check-in + sparse history + conflicting recent behavior -> low confidence

### Suggested confidence inputs

Pattern confidence can combine:
- sample_count
- variance
- recency
- consistency

Estimation confidence can combine:
- live signal weight
- recent signal agreement
- historical confidence
- contradiction penalties

---

## 13. Inference Logic

The Fatigue Layer should not be a pure LLM call.

It should be a hybrid system:

- rule-based evidence handling
- lightweight scoring
- optional LLM interpretation for conversational fatigue cues

### Step-by-step inference flow

1. Determine current local timestamp
2. Map timestamp to time bucket
3. Retrieve latest explicit fatigue check-in if recent enough
4. Retrieve recent fatigue-relevant signals
5. Retrieve historical fatigue pattern for current bucket
6. Compute combined fatigue estimate
7. Compute confidence
8. Map fatigue to response mode
9. Return fatigue state object

### Priority order

#### Highest priority
Live explicit fatigue

#### Medium priority
Recent short-term behavioral evidence

#### Baseline prior
Historical time-bucket pattern

This means historical fatigue should not override a fresh explicit user signal.

---

## 14. Suggested Weighting Strategy

A simple MVP weighting model:

### If live fatigue exists and is recent
- live fatigue = 0.60
- recent signals = 0.20
- historical pattern = 0.20

### If no live fatigue exists
- recent signals = 0.40
- historical pattern = 0.60

### If no recent signals and no live fatigue
- historical pattern = 1.00

This should be treated as a heuristic, not a fixed scientific truth.

The system can later learn better weights from data.

---

## 15. Mapping Fatigue to Response Mode

The output of the Fatigue Layer should directly influence how the assistant answers.

Use the same 0-5 logic already aligned with the broader product.

### Score 0-1
Mode: exploratory
- more options
- more tradeoffs
- more explanation

### Score 2-3
Mode: guided
- two or three options
- clear ranking
- concise explanation

### Score 4-5
Mode: decisive
- one clear recommendation
- short reasoning
- minimal cognitive burden

This is one of the main reasons the Fatigue Layer exists.

It does not only estimate fatigue. It changes how help is delivered.

---

## 16. How It Supports In-Prompt Questions

Example question:
> "Should I work on the report tonight?"

System flow:

1. detect current time bucket = night
2. fetch fatigue pattern for user at night
3. find that user average night fatigue is 4.3
4. recent behavior shows two postponed cognitive tasks today
5. no live fatigue score exists
6. estimation confidence = medium-high
7. system answers decisively:
   - "Do not start the full report tonight. Spend 20 minutes outlining it and schedule the main writing for tomorrow morning."

This is better than a generic productivity answer because it is personalized to likely current bandwidth.

---

## 17. How It Can Support Future Task Scheduling Later

Even though the main purpose is in-prompt decision support, the same fatigue pattern data can improve Phase 1 later.

Examples:
- place writing tasks in strong energy windows
- avoid scheduling high-effort work in weak windows
- increase reminder directness during historically low-bandwidth periods
- reserve recovery buffers after consistently draining periods

So the Fatigue Layer should be implemented in a reusable way, even if Phase 2 is its first main customer.

---

## 18. Worker Design

The Fatigue Layer needs background computation.

Recommended workers:

### A. fatigue_pattern_updater
Runs on a schedule and updates `fatigue_patterns`.

Responsibilities:
- aggregate explicit check-ins
- aggregate inferred fatigue events
- calculate time-bucket averages
- update variance and confidence
- refresh trend direction

Recommended frequency:
- daily for MVP
- more frequently later if needed

### B. fatigue_signal_extractor
Processes recent interaction events and derives fatigue-related soft signals.

Examples:
- repeated snoozes at night
- low response speed
- multiple postponements after 8 PM
- direct fatigue phrases in chat

This worker can be simple for MVP and become smarter later.

### C. fatigue_memory_summarizer
Optional later-stage worker.

Responsibilities:
- convert recurring fatigue patterns into readable learned memories
- example: "User usually struggles with long tasks after 9 PM"

This helps explain recommendations and improves human-readable personalization.

---

## 19. Retrieval Pattern at Decision Time

When an in-prompt request arrives, the system should do:

1. identify domain and current timestamp
2. compute current time bucket
3. fetch latest explicit fatigue if recent
4. fetch matching `fatigue_patterns`
5. fetch recent fatigue-related interaction events
6. compute fatigue estimate
7. pass result into Decision Engine

### Retrieval should be lightweight
Do not make this a huge pipeline per message.

Keep it fast:
- one recent fatigue query
- one time-bucket pattern query
- one recent events query
- one estimation function

This layer should help the assistant answer quickly.

---

## 20. Example API Contract

Internal service example:

```json
{
  "user_id": "uuid",
  "request_time": "2026-04-18T21:30:00-07:00",
  "query_type": "task_decision",
  "context": {
    "task_id": "optional",
    "domain": "task"
  }
}
```

Response:

```json
{
  "estimated_fatigue_score": 4,
  "time_bucket": "night",
  "pattern_confidence": 0.83,
  "estimation_confidence": 0.76,
  "mode_recommendation": "decisive",
  "reasons": [
    "Historical fatigue is high at this time",
    "Recent task postponements suggest low current bandwidth"
  ],
  "source_mix": {
    "live": false,
    "recent": true,
    "historical": true
  }
}
```

This response should be passed into the Decision Engine, not shown directly to the user.

---

## 21. Prompting and LLM Usage

Do not use an LLM to guess raw fatigue every time.

Use LLMs only where they are strong:

- interpreting conversational fatigue cues
- extracting fatigue evidence from text
- summarizing human-readable fatigue memories
- optionally explaining why a recommendation style was chosen

Do not use LLMs as the main fatigue source of truth.

The core fatigue estimate should be computed from structured signals and rules.

---

## 22. MVP Implementation Plan

### Step 1
Keep current explicit fatigue check-in support.

### Step 2
Add time-bucket classification logic.

### Step 3
Create `fatigue_patterns` table.

### Step 4
Build `fatigue_pattern_updater` worker.

### Step 5
Create a simple fatigue estimation service that merges:
- latest explicit check-in
- historical bucket pattern
- recent event heuristics

### Step 6
Connect output to In-Prompt Decision Engine mode selection.

### Step 7
Log outcomes and measure whether recommendations improve.

This gives a realistic MVP without over-engineering.

---

## 23. Metrics to Track

The Fatigue Layer should be evaluated as a product capability, not only a technical feature.

### Quality metrics
- fatigue estimate agreement with later user feedback
- recommendation acceptance rate by fatigue mode
- decision regret rate
- response correction rate
- low-confidence fallback rate

### Learning metrics
- number of usable fatigue pattern buckets formed
- average pattern confidence over time
- stability of fatigue pattern estimates
- number of live check-ins required over time

### Product outcome metrics
- reduced overloaded recommendations
- better timing for difficult tasks
- improved task follow-through in strong windows
- lower reminder annoyance in weak windows

---

## 24. Risks and Mitigations

### Risk 1 - Wrong fatigue inference
Mitigation:
- confidence-aware usage
- ask a quick question when confidence is low
- never overstate certainty

### Risk 2 - Too many fatigue prompts
Mitigation:
- use fatigue as a prior
- ask only when necessary
- decay prompt frequency as history improves

### Risk 3 - Overfitting weak signals
Mitigation:
- separate hard and soft evidence
- cap influence of weak inferred signals
- require sample thresholds for high confidence

### Risk 4 - Poor explainability
Mitigation:
- keep reasons human-readable
- store readable summaries
- let users correct patterns later

### Risk 5 - Schema complexity
Mitigation:
- start with one derived table
- avoid too many fatigue-specific tables at MVP
- reuse existing event logs where possible

---

## 25. Final Recommendation

Build the Fatigue Layer as a first-class system layer for Phase 2.

At MVP, it should include:

- explicit fatigue check-ins
- time-bucket fatigue patterns
- recent signal heuristics
- a hybrid fatigue estimator
- response-mode mapping
- a daily pattern updater worker

The most important architectural decision is this:

> treat fatigue as a structured, confidence-aware prior for in-the-moment decisions, not only as an occasional user survey and not only as a free-text memory.

That gives the system:
- better personalization
- better real-time recommendations
- less user friction
- stronger long-term learning
- a reusable signal for future scheduling improvements
