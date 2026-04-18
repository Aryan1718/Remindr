# Agent Guide

This repository contains product and implementation context for the Fatigue-Aware Personal Assistant.

The main documentation lives in `docs/`. Use this file as the root entrypoint for understanding the project and deciding which document to read first.

## Primary Starting Points

- `docs/PRD.md`: product definition, core idea, and problem statement
- `docs/Architecture.md`: high-level system architecture and major layers
- `docs/Frontend.md`: frontend scope, pages, flows, and implementation direction
- `docs/Backend_Context.md`: backend responsibilities and system behavior
- `docs/backend_api_contract.md`: backend endpoints and contract expectations
- `docs/database_schema_v3.md`: latest database schema direction for the MVP

## Supporting Context

- `docs/Auth-Context.md`: authentication and authorization model
- `docs/connectors_context_v2.md`: Google Calendar and Gmail connector design
- `docs/backend_workers_and_jobs.md`: worker responsibilities and async processing
- `docs/internal_calendar_implementation_context.md`: internal scheduling layer behavior
- `docs/fatigue_layer_implementation_context.md`: fatigue estimation and decision support
- `docs/telegram_bot_context.md`: Telegram as the MVP communication surface
- `docs/project_timeline.md`: epics and stories for execution planning
- `docs/DESIGN.md`: visual and design-system direction

## Older Or Supplemental Schema Docs

- `docs/database_schema_versions/database_schema.md`: earlier schema version
- `docs/database_schema_versions/database_schema_v2.md`: second schema version
- `docs/internal_calendar.md`: earlier internal calendar design notes

## Practical Reading Order

If you are new to the project, read in this order:

1. `docs/PRD.md`
2. `docs/Architecture.md`
3. `docs/Frontend.md`
4. `docs/Backend_Context.md`
5. `docs/backend_api_contract.md`
6. `docs/database_schema_v3.md`

Then read the specialized docs that match the task:

- auth work: `docs/Auth-Context.md`
- connector work: `docs/connectors_context_v2.md`
- background job work: `docs/backend_workers_and_jobs.md`
- scheduling work: `docs/internal_calendar_implementation_context.md`
- fatigue-aware logic: `docs/fatigue_layer_implementation_context.md`
- Telegram integration: `docs/telegram_bot_context.md`
- UI or branding work: `docs/DESIGN.md`

## Current Repository Note

Although the documentation is concentrated in `docs/`, the repository also contains implementation code under `frontend/`.

When documentation conflicts with code, treat the latest implementation and the newest versioned docs as the source to verify before making changes.
