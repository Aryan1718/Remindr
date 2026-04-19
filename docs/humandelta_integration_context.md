# HumanDelta Integration Context
*Fatigue-Aware Personal Assistant*

Last updated: April 19, 2026

## 1. Purpose

This document defines how HumanDelta should be integrated into the Fatigue-Aware Personal Assistant based on the currently available HumanDelta API.

The goal is to use HumanDelta as a **managed knowledge ingestion and retrieval layer** for external websites and uploaded documents.

HumanDelta should help the system:

- index external knowledge sources without running our own retrieval infra
- upload user-relevant documents into one searchable knowledge pool
- retrieve semantically relevant context when the assistant needs supporting information
- keep knowledge retrieval separate from product state, scheduling, and fatigue logic

This integration must respect the current architecture:

- Supabase remains the source of truth for product data
- backend services remain the operational owner
- internal calendar remains the assistant-owned planning layer
- fatigue layer remains the system's bandwidth estimation layer
- HumanDelta remains a retrieval layer, not a planner or database replacement

---

## 2. Core Decision

We are **not** using HumanDelta:

- as the primary AI agent
- as the database
- as the scheduler
- as the fatigue estimator
- as the real-time decision engine
- as the final authority for task creation or memory writes

We **are** using HumanDelta:

- to crawl relevant websites into a managed index
- to upload markdown, PDF, CSV, image, and text documents into a searchable library
- to run semantic search across indexed websites and uploaded documents
- to expose file-style inspection tools over indexed knowledge when helpful

### One-line definition

> HumanDelta is the system's managed external knowledge and document retrieval layer.

---

## 3. Verified HumanDelta API Surface

The current HumanDelta API capabilities available to this project are:

- `POST /v1/indexes`
  - create and start a website crawl job
- `GET /v1/indexes`
  - list index jobs
- `GET /v1/indexes/{id}`
  - poll index job status and stage progress
- `POST /v1/indexes/{id}/cancel`
  - cancel a running crawl job
- `POST /v1/search`
  - semantic vector search across indexed web content and uploaded documents
- `POST /v1/documents`
  - upload files into the org document library
- `GET /v1/documents`
  - list uploaded documents
- `GET /v1/documents/{id}/preview`
  - retrieve extracted text for a document
- `DELETE /v1/documents/{id}`
  - delete an uploaded document
- `POST /v1/fs`
  - shell-style inspection of indexed knowledge base contents

### Important interpretation

This API provides:

- ingestion
- indexing
- semantic retrieval
- content inspection

This API does **not** by itself provide:

- accept/reject validation judgments
- decision scoring
- memory approval logic
- scheduling recommendations

So HumanDelta should be integrated as retrieval infrastructure, not as a trust-evaluator engine.

---

## 4. Relationship with Existing Architecture

## 4.1 What stays the same

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
- connector sync
- fatigue estimation
- task creation
- watcher execution
- notification delivery
- deciding what becomes product state

### Internal Calendar
The internal calendar remains the assistant-owned planning layer.

### Fatigue Layer
The fatigue layer remains the structured estimator of user bandwidth.

---

## 4.2 What HumanDelta adds

HumanDelta adds a new supporting layer:

- crawled website knowledge
- uploaded document knowledge
- semantic retrieval over both in one embedding space
- content preview and inspection tools for debugging and prompt construction

---

## 5. High-Level Placement

## 5.1 Website knowledge path

```text
User intent or watcher need -> choose website source -> HumanDelta crawl job -> poll until completed -> searchable web knowledge
```

## 5.2 Document knowledge path

```text
Connector output or user upload -> transform into document if needed -> upload to HumanDelta -> searchable document knowledge
```

## 5.3 Retrieval path

```text
Assistant workflow -> semantic search -> retrieved context -> backend interprets context -> product action or response
```

---

## 6. Main Integration Areas

## 6.1 Job Search Knowledge

This is the best first use case.

### Why

The project already includes the idea of a job search watcher, and HumanDelta can support that without changing core planning ownership.

### Proposed flow

1. user indicates they are searching for jobs
2. intent matcher identifies job-search mode
3. system asks for target roles
4. backend uses the target roles to collect job-related source material
5. source material is assembled into a document or indexed source set
6. HumanDelta stores that knowledge
7. search retrieves relevant job context later for watcher logic, summaries, or recommendations

### Example

If the user targets:

- product manager
- data analyst
- machine learning engineer

Then the system can:

- collect role-relevant job data from approved sources
- package it into a structured markdown or text document
- upload it to HumanDelta
- search that knowledge base later for matching opportunities, repeated requirements, location trends, or preparation guidance

### Product effect

HumanDelta helps the assistant:

- search across collected job market context
- summarize role patterns
- support future job-related watcher outputs

The backend still decides:

- whether to create tasks
- whether to notify the user
- whether to update goals or watchers

---

## 6.2 Gmail-Derived Document Library

This is the second strong use case once Gmail connector flow exists.

### Why

The project already wants Gmail as a context source, but raw emails should not directly become product state.

### Proposed flow

1. Gmail connector syncs and normalizes messages
2. relevant email content is converted into markdown documents
3. markdown is uploaded to HumanDelta
4. HumanDelta indexes the uploaded documents
5. semantic search later retrieves useful evidence from the user's email-derived knowledge base

### Example document types

- email obligation digest
- deadline digest
- recruiter conversation summary
- project communication digest
- weekly inbox summary

### Product effect

HumanDelta helps retrieve:

- likely obligations
- supporting context for a task
- repeated themes across email history
- relevant snippets for future assistant workflows

The backend still decides:

- whether something should become a task
- whether something should become a reminder
- whether something should enter learned memory

---

## 6.3 User Uploads and Personal Knowledge

Users may also upload their own documents.

### Examples

- resume
- syllabus
- assignment PDF
- project brief
- planning notes
- onboarding docs
- policy docs
- CSV exports

### Product effect

These documents can later support:

- goal planning
- job search assistance
- assignment guidance
- summarization
- contextual decision support

This is a strong fit for HumanDelta because it turns scattered user materials into one searchable corpus without building our own embedding pipeline first.

---

## 7. Where HumanDelta Should NOT Be Used

## 7.1 Not as a database replacement

HumanDelta is not the system of record.

It should not replace Supabase or pgvector-backed product storage.

Supabase remains responsible for:

- persistence
- relational querying
- product state
- audit trails
- scheduling state
- fatigue records

---

## 7.2 Not as a scheduler replacement

HumanDelta should not decide:

- which task block gets scheduled where
- how internal calendar conflicts are resolved
- how fatigue scores are computed
- how recommendation ranking works

Those remain inside:

- internal calendar service
- decision service
- fatigue service
- watcher logic

---

## 7.3 Not directly in the real-time critical path unless retrieval is optional

Do not make HumanDelta a hard dependency for:

- `/decision/query`
- Telegram reply generation
- fatigue estimation
- immediate scheduling

### Why

These flows should remain:

- fast
- debuggable
- resilient to provider outages

HumanDelta retrieval should be:

- optional
- timeout-bounded
- additive, not blocking

---

## 8. Recommended Integration Model

## 8.1 HumanDelta as an internal retrieval service dependency

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
- authentication
- polling index jobs
- multipart document uploads
- search requests
- fs requests
- timeout and retry-safe request handling

#### `humandelta_mapper.py`
Responsible for:

- mapping internal data into HumanDelta upload/search/index payloads
- converting Gmail or other internal content into markdown-friendly upload shapes
- mapping HumanDelta responses into internal retrieval shapes

#### `humandelta_service.py`
Responsible for:

- deciding when HumanDelta should be called
- exposing helper methods for:
  - website indexing
  - document upload
  - semantic search
  - document preview
  - knowledge inspection
- shielding the rest of the backend from provider-specific details

---

## 8.2 Worker-first execution

HumanDelta should mainly be used through workers for ingestion tasks.

Recommended worker additions:

```text
backend/
  app/
    workers/
      jobs/
        humandelta_index_website.py
        humandelta_upload_document.py
```

### Why workers

This keeps:

- API latency low
- crawl polling off the request path
- retries safer
- ingestion optional and non-blocking

Search can still be called synchronously in bounded, low-latency contexts if needed, but indexing and large uploads should prefer workers.

---

## 9. Detailed Flow Design

## 9.1 Website indexing flow

### Step-by-step

1. backend chooses a website to index
2. backend creates a HumanDelta index job
3. worker polls `GET /v1/indexes/{id}`
4. when status becomes `completed`, the index is available for search
5. backend stores local metadata about that source if needed
6. future workflows run semantic search against that index

### Example sources

- job boards
- documentation sites
- university portals
- company career pages

---

## 9.2 Document upload flow

### Step-by-step

1. backend receives or generates a document
2. if needed, internal content is converted into markdown or text
3. backend uploads file to `POST /v1/documents`
4. HumanDelta extracts, chunks, and embeds content
5. document becomes searchable through `POST /v1/search`

### Example documents

- Gmail-derived markdown summaries
- resume
- syllabus
- assignment brief
- notes
- role research digest

---

## 9.3 Retrieval flow

### Step-by-step

1. workflow needs background context
2. backend formulates a natural-language query
3. backend calls `POST /v1/search`
4. HumanDelta returns ranked chunks with source context
5. backend uses those results for summaries, watcher reasoning, or assistant support

### Example retrieval use cases

- "Find software engineer roles mentioning Python and remote work"
- "What did the user's uploaded resume emphasize?"
- "What deadlines appear in the uploaded course documents?"
- "Find recruiter replies mentioning interview scheduling"

---

## 10. Suggested Local Metadata Support

HumanDelta does not replace product tables, but we may eventually want local metadata tables to track what we uploaded or indexed.

Examples of useful future metadata:

- indexed source registry
- uploaded document registry
- sync status for generated markdown uploads
- document-to-user mapping for uploaded artifacts

These local tables are optional for the first implementation if HumanDelta IDs can be stored inside existing metadata fields, but they may become useful later.

---

## 11. Relationship to Existing Tables

## 11.1 `connectors`

Connector account metadata remains here.

HumanDelta should not replace connector ownership.

---

## 11.2 `external_calendar_events`

Calendar records remain normalized external truth.

HumanDelta may later store supporting documents derived from other sources, but calendar sync itself does not require HumanDelta.

---

## 11.3 `external_email_items`

This is the strongest future source for HumanDelta document generation.

Email records can later be transformed into markdown documents and uploaded to HumanDelta.

---

## 11.4 `tasks`

Tasks remain assistant-owned operational state.

HumanDelta may provide supporting retrieval context, but does not own task creation.

---

## 11.5 `internal_calendar`

Internal calendar remains assistant-owned planning state.

HumanDelta may provide supporting context for planning-oriented workflows, but does not own scheduling.

---

## 11.6 `learned_memories`

Learned memory remains owned by our database and backend logic.

HumanDelta may provide supporting retrieved evidence, but is not the memory store itself.

---

## 11.7 `interaction_events`

This remains a useful source for future document generation or summarization jobs.

But interaction events should not be bulk-pushed into HumanDelta without a clear use case.

---

## 12. Recommended Usage Rules

## Rule 1

Use HumanDelta for **external knowledge and uploaded document retrieval**, not for core operational truth.

## Rule 2

Prefer HumanDelta for workflows where retrieval quality matters more than strict determinism.

## Rule 3

Keep HumanDelta off critical planning and fatigue paths unless retrieval is optional and timeout-bounded.

## Rule 4

Do not let HumanDelta directly mutate tasks, scheduling, fatigue, or durable product state.

## Rule 5

Use HumanDelta first where the project already needs outside knowledge:

- job search
- uploaded user docs
- Gmail-derived digests

---

## 13. MVP Integration Scope

## Include in MVP

- HumanDelta client support for indexes, documents, search, and preview/list/delete flows
- website indexing for job-search-related sources
- document upload for generated markdown and user-provided files
- search over indexed sources and uploaded documents

## Exclude from MVP

- making HumanDelta the final validation engine
- real-time hard dependency in decision routes
- scheduling dependency
- fatigue estimation dependency
- automatic direct writes from HumanDelta to product tables

---

## 14. Rollout Plan

## Phase 1 - Website indexing for job search

First implement HumanDelta for:

- website indexing
- crawl status polling
- search over indexed job-related sources

### Goal

Support job-search workflows and watchers with retrieval over approved external sources.

---

## Phase 2 - Document uploads

Then implement HumanDelta for:

- user-uploaded files
- generated markdown documents
- Gmail-derived markdown once Gmail connector flow exists

### Goal

Create a reusable, searchable personal knowledge layer for the assistant.

---

## Phase 3 - Retrieval-powered assistant support

Then implement HumanDelta for:

- retrieval support in selected watcher and assistant flows
- prompt/context enrichment where useful

### Goal

Improve the assistant's context access without moving product truth or scheduling logic outside the backend.

---

## 15. Benefits

If integrated correctly, HumanDelta can improve:

- knowledge retrieval quality
- support for job search workflows
- usefulness of uploaded user documents
- ability to search Gmail-derived summaries later
- speed of shipping retrieval features without standing up custom infra

---

## 16. Risks and Mitigations

## Risk 1 - Overusing HumanDelta for logic it does not own

### Mitigation

Keep HumanDelta as retrieval infrastructure only.

## Risk 2 - Latency creep in user-facing decision flows

### Mitigation

Use workers for ingestion and keep synchronous retrieval optional and bounded.

## Risk 3 - Mixing retrieved context with operational truth

### Mitigation

Keep HumanDelta outputs advisory and separate from direct product-state writes.

## Risk 4 - Uploading too much low-value content

### Mitigation

Start with curated sources and high-value document generation paths.

---

## 17. Final Recommendation

The best way to integrate HumanDelta into this product is:

- not as the brain
- not as the database
- not as the scheduler

But as a **managed retrieval layer** for:

- crawled websites
- uploaded user files
- generated markdown knowledge artifacts

### Final one-line summary

> Supabase stores the product truth, the backend runs the assistant, and HumanDelta provides searchable external and document knowledge.
