# Connectors Context - Google Calendar and Gmail

Last updated: April 18, 2026

## 1. Purpose

This file defines how the connector layer should work for the MVP using:
- Google Calendar
- Gmail

The goal of the connector layer is not only to sync external data.
It should make external context usable for:
- internal calendar planning
- task creation
- reminder and watcher logic
- memory creation
- future decision support

This design follows the current architecture where connectors fetch external context, normalize it, and provide structured inputs to the rest of the system rather than acting as the decision layer themselves.

---

## 2. Core Principle

Connector data is external truth.

It should be treated differently from:
- assistant-owned planning state
- learned memory
- derived fatigue patterns

### Separation of layers

#### A. External truth layer
This is raw or normalized connector data.
Examples:
- Google Calendar event from Tuesday 10 AM to 11 AM
- Gmail message asking the user to submit an assignment by Friday

#### B. Operational planning layer
This is what the assistant creates internally.
Examples:
- a suggested focus block in the internal calendar
- a reminder scheduled for tomorrow morning
- a generated task from an email obligation

#### C. Learned memory layer
This is what the system learns over time.
Examples:
- user usually has heavy calendar load on Wednesdays
- user often receives deadlines by email on weekday evenings
- user tends to reject focus blocks after late meetings

This separation is required because the schema explicitly says to keep external connector data separate from assistant-owned planning state, and to keep internal scheduling separate from learned memory. fileciteturn2file0

---

## 3. Mandatory Connector Flow

Every connector must follow this exact flow:

1. authenticate connector
2. fetch raw provider data
3. normalize provider data into product schema
4. upsert normalized records into dedicated connector tables
5. derive product signals from normalized records
6. create operational outputs like tasks, internal calendar blocks, and notifications
7. write learned memory only from repeated stable patterns

### Critical rule
Do not write raw API responses directly into core product tables.

That means:
- do not put raw Google Calendar events directly into `internal_calendar`
- do not put raw Gmail messages directly into `tasks`
- do not write raw connector facts directly into `learned_memories`

Connector data must be normalized first, then stored, then used by downstream workers.

### Practical pipeline

```text
Raw API Data -> Normalize -> Store in connector tables -> Derive signals -> Create tasks/calendar/notifications -> Distill memory
```

---

## 4. What normalization means

Normalization means converting provider-specific payloads into a clean internal shape before saving them.

### Normalization is required because:
- Google APIs return large provider-specific payloads
- fields are inconsistent across endpoints
- downstream workers need predictable column names and types
- memory and planning logic should operate on structured facts, not raw blobs

### Normalization is not enrichment
Normalization should only:
- standardize fields
- parse dates and ids
- map enums and statuses
- preserve raw payload for traceability

Normalization should not:
- create tasks
- infer fatigue
- decide priorities
- create learned memory
- generate long-term goals

Those steps happen after storage in separate workers.

---

## 5. Normalization Rule for Database Writes

For every synced record, store both:
- normalized structured fields used by the product
- `raw_payload_json` for debugging, traceability, and future reprocessing

### Database write rule
The connector layer should write to:
- `connectors` for account and sync metadata
- `external_calendar_events` for normalized Google Calendar records
- `external_email_items` for normalized Gmail records

This fits the schema direction where `connectors` stores connector account details and sync state, while operational tables like `tasks`, `internal_calendar`, `notifications`, and `learned_memories` remain separate. fileciteturn2file0

---

## 6. Google Calendar - fetch and normalize

## 6.1 Primary role
Google Calendar gives the system a reliable view of:
- upcoming commitments
- free time windows
- recurring routines
- busy or overloaded days
- meeting density
- possible recovery windows

## 6.2 Raw fields to fetch
For MVP, fetch:
- external event id
- calendar id
- title or summary
- description
- location
- start
- end
- all-day information
- status
- created time
- updated time
- organizer if useful
- attendees count if useful later
- raw payload JSON

## 6.3 Normalized shape
Normalize each event into:
- `user_id`
- `connector_id`
- `external_event_id`
- `calendar_id`
- `title`
- `description`
- `location`
- `starts_at`
- `ends_at`
- `is_all_day`
- `status`
- `raw_payload_json`
- `last_synced_at`
- `created_at`
- `updated_at`

### Normalization notes
- parse Google start and end fields into consistent `timestamptz`
- convert all-day events into a boolean `is_all_day`
- map provider status values into a stable internal text value
- keep the original payload in `raw_payload_json`
- do not create planning blocks here

## 6.4 Example normalization

### Raw Google Calendar payload
```json
{
  "id": "abc123",
  "summary": "Team Meeting",
  "description": "Weekly sync",
  "location": "Zoom",
  "start": {"dateTime": "2026-04-21T10:00:00-07:00"},
  "end": {"dateTime": "2026-04-21T11:00:00-07:00"},
  "status": "confirmed",
  "updated": "2026-04-18T08:30:00Z"
}
```

### Normalized record
```json
{
  "external_event_id": "abc123",
  "title": "Team Meeting",
  "description": "Weekly sync",
  "location": "Zoom",
  "starts_at": "2026-04-21T10:00:00-07:00",
  "ends_at": "2026-04-21T11:00:00-07:00",
  "is_all_day": false,
  "status": "confirmed"
}
```

---

## 7. Gmail - fetch and normalize

## 7.1 Primary role
Gmail gives the system a reliable view of incoming obligations and soft commitments that are not always present in the calendar.

Examples:
- interview requests
- assignments and deadlines
- billing or admin tasks
- event confirmations
- follow-up requests
- job search updates

## 7.2 Raw fields to fetch
For MVP, fetch:
- external message id
- thread id
- subject
- sender name
- sender email
- snippet
- internal date or received time
- label ids or labels
- message body text or cleaned text for later summarization
- raw payload JSON

## 7.3 Normalized shape
Normalize each message into:
- `user_id`
- `connector_id`
- `external_message_id`
- `external_thread_id`
- `subject`
- `sender_name`
- `sender_email`
- `snippet`
- `body_summary`
- `received_at`
- `labels_json`
- `obligation_type`
- `due_at`
- `importance_score`
- `raw_payload_json`
- `last_synced_at`
- `created_at`
- `updated_at`

### Normalization notes
- flatten Gmail headers into consistent sender and subject fields
- parse Gmail internal date into `received_at`
- store raw labels in `labels_json`
- `body_summary`, `obligation_type`, `due_at`, and `importance_score` can be null at first sync if you want a later extraction worker to fill them
- do not create tasks here

## 7.4 Example normalization

### Raw Gmail payload
```json
{
  "id": "msg_123",
  "threadId": "thread_55",
  "snippet": "Please submit your assignment by Friday.",
  "internalDate": "1776499200000",
  "payload": {
    "headers": [
      {"name": "Subject", "value": "Assignment Reminder"},
      {"name": "From", "value": "Professor X <prof@example.edu>"}
    ]
  },
  "labelIds": ["INBOX", "IMPORTANT"]
}
```

### Normalized record
```json
{
  "external_message_id": "msg_123",
  "external_thread_id": "thread_55",
  "subject": "Assignment Reminder",
  "sender_name": "Professor X",
  "sender_email": "prof@example.edu",
  "snippet": "Please submit your assignment by Friday.",
  "received_at": "2026-04-18T00:00:00Z",
  "labels_json": ["INBOX", "IMPORTANT"],
  "body_summary": null,
  "obligation_type": null,
  "due_at": null,
  "importance_score": null
}
```

---

## 8. Recommended connector tables

The current `database_schema_v3` gives us:
- `connectors`
- `tasks`
- `internal_calendar`
- `calendar_feedback`
- `fatigue_checkins`
- `fatigue_patterns`
- `interaction_events`
- `learned_memories`
- `notifications` fileciteturn2file0

That is enough for the planning and memory layer, but not enough for normalized connector content itself.

### Recommended addition
Add two new tables:
- `external_calendar_events`
- `external_email_items`

Reason:
The schema principles already say external connector data should be kept separate from assistant-owned planning state and learned memory. So storing raw or normalized connector rows directly in `internal_calendar` or `learned_memories` would mix layers incorrectly. fileciteturn2file0

### Suggested table: external_calendar_events
Recommended fields:
- `id`
- `user_id`
- `connector_id`
- `external_event_id`
- `calendar_id`
- `title`
- `description`
- `location`
- `starts_at`
- `ends_at`
- `is_all_day`
- `status`
- `raw_payload_json`
- `last_synced_at`
- `created_at`
- `updated_at`

### Suggested table: external_email_items
Recommended fields:
- `id`
- `user_id`
- `connector_id`
- `external_message_id`
- `external_thread_id`
- `subject`
- `sender_name`
- `sender_email`
- `snippet`
- `body_summary`
- `received_at`
- `labels_json`
- `obligation_type`
- `due_at`
- `importance_score`
- `raw_payload_json`
- `last_synced_at`
- `created_at`
- `updated_at`

---

## 9. How connector data should flow into the product

## 9.1 Step 1 - Add connector account
When the user connects Google Calendar or Gmail:
- create or update row in `connectors`
- store provider
- store account email
- store connector status
- store encrypted tokens
- store token expiry
- set `last_sync_at` when first sync finishes

This matches the purpose of the `connectors` table in the schema. fileciteturn2file0

## 9.2 Step 2 - Fetch raw provider data
Use incremental sync wherever possible.

### Calendar sync scope
- next 14 days of events
- optionally recent past 7 days for pattern context

### Gmail sync scope
- recent inbox emails
- unread emails
- important emails
- recent 14 to 30 days depending on sync budget

## 9.3 Step 3 - Normalize before database write
For every fetched record:
- parse provider payload
- map provider fields into normalized columns
- validate required fields
- attach `user_id` and `connector_id`
- preserve original payload in `raw_payload_json`
- upsert into connector tables

### Rule
Normalization must happen before data is added to the product database beyond the `connectors` row.

## 9.4 Step 4 - Derive product signals
Workers derive product signals from normalized connector records.

Examples:
- calendar shows no free space tomorrow afternoon
- email contains a due date this Friday
- user has three meetings before noon every Tuesday

## 9.5 Step 5 - Create operational outputs
Derived signals can produce operational objects.

Examples:
- create a `task`
- create an `internal_calendar` suggestion
- queue a `notification`
- write an `interaction_event`

This is consistent with the schema where `tasks` are the source of truth for work, `internal_calendar` is the assistant-owned planning layer, and `notifications` support proactive nudges. fileciteturn2file0

## 9.6 Step 6 - Distill into learned memory
Only repeated or meaningful patterns should be stored in `learned_memories` or in derived fatigue-related tables.

Examples:
- user’s Wednesdays are usually fragmented by short meetings
- user often has dense calendar load in the afternoon
- user tends to accept short work blocks after morning meetings

This matches the schema rule that learned memory should store patterns, not every raw event, and that derived summaries should be updated through workers or aggregation jobs. fileciteturn2file0

---

## 10. Two-week planning horizon

The next two weeks are useful mainly for planning, not for permanent memory.

### Recommended use
Each sync cycle:
1. fetch or refresh the next 14 days of calendar
2. fetch recent important Gmail items
3. normalize and upsert connector rows
4. compute free windows and obligation windows
5. rank upcoming workload pressure
6. create or update task suggestions
7. create or update internal calendar suggestions
8. generate a rolling weekly summary

### Example outputs
- next Tuesday is overloaded, avoid scheduling long tasks there
- Thursday morning is the best open window for focused work
- user has two email-derived deadlines in the next six days
- next week has low flexibility because of recurring morning meetings

These outputs should feed the scheduler and watcher system, not go directly into memory as facts.

---

## 11. Relation to fatigue layer

Connector data should support the fatigue-aware system, but indirectly.

Examples:
- meeting-heavy days can increase expected fatigue risk
- late-evening deadlines can increase overload probability
- fragmented schedules can reduce focus quality

This should influence:
- internal calendar suggestions
- reminder aggressiveness
- recommendation style
- whether to ask for an explicit fatigue check-in

The schema already separates explicit fatigue check-ins from derived fatigue patterns, which is the right design. Connector signals should contribute evidence, but they should not replace direct fatigue input. fileciteturn2file0

---

## 12. Recommended worker jobs around connectors

### 12.1 calendar_sync_worker
Responsibilities:
- fetch upcoming Google Calendar events
- normalize records
- update `external_calendar_events`
- compute free and busy windows
- emit `interaction_events`

### 12.2 gmail_sync_worker
Responsibilities:
- fetch recent Gmail messages
- normalize records
- update `external_email_items`
- extract obligations and deadlines in a later pass
- emit task candidates
- emit `interaction_events`

### 12.3 connector_signal_worker
Responsibilities:
- combine calendar and email signals
- produce schedule pressure summary
- detect task opportunities
- detect overload risk

### 12.4 weekly_pattern_worker
Responsibilities:
- summarize the next 7 to 14 days for planning
- summarize repeated weekly structure from past data
- update `learned_memories` only when the evidence is stable

### 12.5 task_generation_worker
Responsibilities:
- convert extracted obligations into `tasks`
- suggest related `internal_calendar` blocks
- schedule `notifications` where useful

---

## 13. Final recommendation

Yes, your overall idea is correct.

### Correct interpretation
Google Calendar and Gmail data should be stored and then used to:
- understand the user’s next two weeks
- detect obligations and workload
- create or update tasks
- guide internal calendar scheduling
- generate weekly planning summaries
- create learned memory from repeated patterns

### Important refinement
Do not treat raw connector data itself as memory.
Instead:
- connector data = external truth
- normalized connector tables = reliable structured external context
- internal calendar and tasks = operational layer
- learned memory = repeated stable patterns distilled from connector-backed behavior

### Most important rule
Before adding connector records to the database, normalize them into a product-defined schema.
Only the normalized records should be used by the planner, task generator, watcher jobs, and memory system.
