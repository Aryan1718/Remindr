# Telegram Conversational Agent Flow

## What was already reused

The existing Telegram implementation in `backend/app/services/telegram_service.py` still owns:

- webhook secret validation
- pending vs confirmed Telegram link state
- `/start` confirmation and onboarding progression
- outbound Telegram API calls
- profile and preference updates during onboarding

This patch does not replace that flow. It extends it only after a chat is already confirmed and no onboarding step is actively consuming the message.

## What is new

After a confirmed Telegram message or callback reaches the backend:

1. `TelegramService.handle_webhook(...)` still validates and logs the raw update.
2. If the message is not part of onboarding, it forwards a normalized payload to `AgentService`.
3. `AgentService` classifies intent with deterministic rules first.
4. The agent calls backend domain services for the real work:
   - `DecisionService` for next-action and planning questions
   - `TaskService` for task capture and completion
   - `FatigueService` for fatigue check-ins
   - `InternalCalendarService` for confirm/move/reject callbacks
5. `TelegramService` sends the final Telegram reply through the existing outbound path.

Telegram remains a communication surface. Tasks, calendar state, fatigue signals, memories, and notifications remain backend-owned operational truth.

## OpenAI-compatible LLM abstraction

The new `backend/app/llm/` package provides an OpenAI-style application boundary:

- `BaseLLMClient` defines `generate_text(...)` and `generate_structured(...)`
- `OpenAICompatibleLLM` talks to `/chat/completions`
- `GeminiOpenAICompatibleLLM` is the initial provider adapter
- `get_llm_client(...)` builds the active provider from environment config

The rest of the backend only depends on the OpenAI-like interface, not Gemini-specific request shapes.

## Gemini today, provider swap later

Current default env shape:

- `LLM_PROVIDER=gemini`
- `LLM_MODEL=gemini-2.5-flash`
- `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`

To switch providers later, keep the same agent/service code and change only provider settings, or add another adapter that still implements `BaseLLMClient`.

## Callback action format

Current Telegram callback payloads are structured as:

- `calendar:confirm:<block_id>`
- `calendar:move:<block_id>`
- `calendar:reject:<block_id>`
- `task:done:<task_id>`
- `fatigue:score:<0-5>`

These callbacks call backend services directly. Route handlers stay thin, and the Telegram layer does not mutate storage on its own.
