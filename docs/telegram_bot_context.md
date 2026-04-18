# Telegram Bot Context - Fatigue-Aware Personal Assistant

Last updated: April 18, 2026

## 1. Purpose

This file defines how the system connects to a Telegram bot so the assistant and the user can communicate through Telegram.

Telegram is the MVP communication channel. It is the fastest way to deliver:

- user messages to the assistant
- assistant replies back to the user
- proactive reminders
- suggested task blocks
- confirmations, rejections, and quick feedback
- lightweight onboarding follow-ups

This channel is not the source of truth for planning or memory.

Telegram is only the communication surface.

The source of truth remains:

- backend API
- internal calendar
- tasks
- learned memory
- fatigue signals
- notifications
- connector-backed context

---

## 2. Why Telegram for MVP

Telegram is a good first channel because:

- simple bot setup
- reliable messaging API
- easy webhook support
- supports buttons and quick replies
- good for reminders and short interactions
- works well for both reactive chat and proactive nudges

For this product, Telegram is useful because the assistant does not need a full custom mobile app for the first version. The user can immediately chat with the assistant in a familiar interface.

---

## 3. Role of Telegram in the Full System

Telegram belongs to the Communication Layer.

It sits on top of the rest of the system and should only do these jobs:

- receive messages from the user
- deliver assistant messages to the user
- collect lightweight interaction signals
- support quick actions through inline buttons
- trigger backend workflows

Telegram should not own business logic.

The real logic must remain in:

- Orchestration Layer
- Decision Engine
- Internal Calendar Engine
- Connector Sync Layer
- Memory Layer
- Notification Engine

---

## 4. High-Level Architecture

## 4.1 Main flow

1. User sends a message in Telegram.
2. Telegram sends the update to our backend webhook.
3. Backend verifies the request source.
4. Backend maps the Telegram user to the application user.
5. Backend stores the incoming interaction.
6. Orchestrator detects intent.
7. System fetches context:
   - tasks
   - internal calendar
   - fatigue signals
   - learned memories
   - connectors
8. Decision engine or scheduler produces the response.
9. Backend sends the response back through Telegram Bot API.
10. System stores the response and any resulting actions.

---

## 4.2 Communication directions

### Reactive communication
User starts the interaction.

Examples:
- "What should I work on tonight?"
- "Remind me to apply to this job tomorrow"
- "I am too tired to study. What should I do?"
- "Move my focus block to the evening"

### Proactive communication
System starts the interaction.

Examples:
- "You have a 90-minute free window at 4 PM. This is a good time to start Assignment A."
- "You rejected two late-night work blocks this week. Would you like me to avoid scheduling study sessions after 9 PM?"
- "Tomorrow looks overloaded. I recommend moving Task B to Thursday."
- "You have not replied to the suggested focus block. Do you want to confirm, move, or skip it?"

---

## 5. Telegram Integration Model

## 5.1 Recommended approach

Use the Telegram Bot API with webhook delivery.

Webhook is better than polling for this system because:

- lower latency
- cleaner production architecture
- better for proactive notifications
- easier to connect with backend workflows
- lower waste than constant polling

### Development option
For local development, polling can be used temporarily if needed.

### Production default
Use webhooks in production.

---

## 5.2 Core integration pieces

You need these pieces:

### Telegram Bot
Created through BotFather.

Needed outputs:
- bot token
- bot username
- bot metadata

### Backend webhook endpoint
Receives Telegram updates.

Example responsibility:
- parse incoming update
- handle message or callback query
- enqueue processing if needed
- respond quickly to Telegram

### Telegram service module
Handles outbound calls to Telegram.

Responsibilities:
- send message
- send inline keyboard
- edit message
- answer callback query
- send reminder or notification
- optionally send formatted summaries

### User mapping layer
Maps Telegram chat identity to internal application user identity.

### Notification dispatcher
Allows proactive backend jobs to send Telegram messages later.

---

## 6. User Identity Mapping

Telegram users must be linked to internal users.

Recommended approach:

- during onboarding, user selects Telegram as communication channel
- system generates a secure one-time linking token
- user starts the bot and submits the token
- backend links:
  - internal user_id
  - telegram_user_id
  - telegram_chat_id

This prevents random Telegram users from being attached to the wrong account.

### What should be stored

Recommended Telegram-specific metadata in a communication-specific record or in connector metadata:

- telegram_user_id
- telegram_chat_id
- telegram_username
- telegram_first_name
- linked_at
- link_status
- last_message_at
- last_delivery_at

For the current schema, this can be stored first in:
- `connectors.metadata_json`
or in a future dedicated table such as:
- `communication_channels`

For MVP, storing this under Telegram connector metadata is acceptable.

---

## 7. Suggested Data Handling

The current schema already supports the important product behavior. Telegram mainly interacts with these tables:

## 7.1 `connectors`
Use this to store the Telegram communication connection state if you treat Telegram as a communication connector.

Suggested metadata:
- chat id
- telegram user id
- username
- link status
- last webhook receipt time

## 7.2 `interaction_events`
Store all Telegram interaction events here.

Examples:
- telegram_message_received
- telegram_message_sent
- telegram_button_clicked
- telegram_link_completed
- telegram_delivery_failed

This is important because Telegram interactions become learning signals.

## 7.3 `notifications`
Use this for proactive Telegram messages.

Examples:
- reminder queued for Telegram
- internal calendar suggestion sent via Telegram
- deadline warning sent via Telegram

## 7.4 `internal_calendar`
Telegram should allow the user to:
- confirm a block
- reject a block
- move a block
- mark a block done

## 7.5 `calendar_feedback`
When the user taps:
- Accept
- Reject
- Move
- Snooze

store the decision here.

## 7.6 `fatigue_checkins`
Telegram is a good place to ask lightweight fatigue prompts such as:
- "How is your energy right now? 0 to 5"

## 7.7 `learned_memories`
Repeated Telegram responses can later become learned memory.

Example:
- user often rejects late-night suggestions from Telegram
- user prefers short direct replies during weekday mornings

---

## 8. Telegram Conversation Types

The bot should support a small set of conversation types first.

## 8.1 General assistant chat
Free-form user messages.

Examples:
- "What should I do next?"
- "I need to decide between two tasks"
- "I am tired"
- "Should I study tonight or tomorrow morning?"

This goes through the normal orchestrator and decision engine.

## 8.2 Task capture
User quickly creates tasks by message.

Examples:
- "Remind me to submit the assignment by Friday"
- "I need to prepare for the interview this week"

The system extracts task structure and stores it in `tasks`.

## 8.3 Internal calendar confirmations
The system sends a suggested block with quick actions:

- Confirm
- Move
- Reject
- Done
- Snooze

This should update:
- `internal_calendar`
- `calendar_feedback`
- `interaction_events`

## 8.4 Fatigue prompt
The bot asks short fatigue questions when confidence is low or when the system wants a stronger signal.

Example:
- "Before I suggest a plan, how tired are you right now from 0 to 5?"

This should write to:
- `fatigue_checkins`
- `interaction_events`

## 8.5 Goal and watcher nudges
For proactive use cases.

Examples:
- "You said you want to switch jobs in 2 months. This week is a good time to update your resume."
- "You have not made progress on your application goal this week."

---

## 9. Message Design Principles

Telegram messages must be short, actionable, and easy to process.

Rules:
- keep messages concise
- reduce cognitive load
- avoid large paragraphs
- use direct next steps
- use buttons when possible
- adapt reply style to fatigue and context

### Example styles

#### Low fatigue
"You have two good options for tonight:
1. Finish Assignment A because it is due tomorrow.
2. Start Interview Prep because you have a free 90-minute block.

I recommend Assignment A first."

#### High fatigue
"Do Assignment A now. It fits tonight and lowers the most urgent risk."

#### Proactive suggestion
"You have a free window from 4:00 PM to 5:30 PM. I suggest using it for Assignment A."

Buttons:
- Confirm
- Move
- Skip

---

## 10. Suggested Telegram Commands

Keep commands minimal.

Recommended:

- `/start` - start and link the bot
- `/help` - show how to use the bot
- `/status` - quick summary of today
- `/tasks` - current important tasks
- `/plan` - suggested plan for today
- `/fatigue` - submit current fatigue score
- `/disconnect` - unlink Telegram

Commands should not replace free-form chat. They only provide shortcuts.

---

## 11. Inline Button Strategy

Telegram inline buttons are very important for reducing friction.

Recommended button patterns:

### For internal calendar suggestions
- Confirm
- Move
- Reject
- Done
- Snooze

### For fatigue prompts
- 0
- 1
- 2
- 3
- 4
- 5

### For explanation follow-up
- Why this?
- Show options
- Reschedule

### For notifications
- Open plan
- Mark done
- Remind later

Important rule:
button clicks should always be sent to backend and translated into structured product events, not treated as only UI interactions.

---

## 12. Recommended Backend Modules

A clean backend structure for Telegram should look like this:

```text
backend/
  app/
    api/
      routes/
        telegram_webhook.py
    services/
      telegram/
        telegram_client.py
        telegram_parser.py
        telegram_formatter.py
        telegram_linking.py
        telegram_callbacks.py
      notifications/
        telegram_dispatcher.py
    orchestrators/
      chat_orchestrator.py
      planning_orchestrator.py
    workers/
      send_telegram_notification.py
      process_telegram_update.py
```

### What each part does

#### `telegram_webhook.py`
Receives incoming Telegram updates.

#### `telegram_client.py`
Wraps Telegram Bot API send/edit/answer methods.

#### `telegram_parser.py`
Normalizes Telegram payloads into internal message events.

#### `telegram_formatter.py`
Formats assistant output into Telegram-friendly messages and button layouts.

#### `telegram_linking.py`
Handles secure account linking and unlinking.

#### `telegram_callbacks.py`
Parses inline button actions and routes them to the right workflow.

#### `telegram_dispatcher.py`
Used by notifications and workers to send proactive messages.

#### `process_telegram_update.py`
Background-safe handler for heavier message processing.

---

## 13. Webhook Design

## 13.1 Inbound endpoint

Recommended endpoint:

`POST /api/v1/telegram/webhook`

Responsibilities:
- receive Telegram update
- verify webhook secret if configured
- parse update type
- persist raw interaction event
- quickly acknowledge request
- enqueue heavier processing if needed

### Supported Telegram update types for MVP
- message
- callback_query

You can ignore more advanced update types for now unless needed.

---

## 13.2 Outbound API usage

Backend should call Telegram Bot API for:

- sendMessage
- editMessageText
- answerCallbackQuery
- setWebhook
- deleteWebhook

Optional later:
- sendPhoto
- sendDocument
- sendChatAction

For MVP, text plus inline keyboard is enough.

---

## 14. Account Linking Flow

Recommended linking flow:

1. User signs into web app.
2. User chooses Telegram as communication channel.
3. Backend generates a short-lived link token.
4. UI shows:
   - bot link
   - one-time code or deep link
5. User opens Telegram bot and starts it.
6. User sends the one-time code or uses a deep-link start parameter.
7. Backend validates token.
8. Backend stores chat id and Telegram user id.
9. Bot confirms successful connection.

### Result
Now the assistant can send proactive messages to the correct Telegram chat.

---

## 15. Message Processing Flow

## 15.1 User-to-system flow

1. Telegram sends update.
2. Backend parses message.
3. Identify linked user.
4. Store `interaction_events` record.
5. Run intent detection:
   - planning request
   - decision request
   - task capture
   - fatigue input
   - command
   - calendar action
6. Fetch relevant context.
7. Generate response.
8. Send response.
9. Persist output event and any data changes.

---

## 15.2 System-to-user proactive flow

1. Worker decides a notification should be sent.
2. Notification is created in `notifications`.
3. Telegram dispatcher formats message.
4. Backend sends message to Telegram chat.
5. Update `notifications.status`.
6. Store delivery event in `interaction_events`.

Examples:
- reminder
- suggested work block
- overload warning
- goal progress nudge

---

## 16. Relationship with Internal Calendar

Telegram is one of the most important surfaces for the internal calendar.

Recommended behavior:

### When the system creates a suggested block
Send a Telegram message like:

"I reserved 4:00 PM to 5:00 PM for Assignment A because this is your best open window before the deadline."

Buttons:
- Confirm
- Move
- Reject

### When user confirms
Update:
- `internal_calendar.status = confirmed`
- maybe `sync_to_google = true` later if user allows
- add `calendar_feedback`
- add `interaction_events`

### When user rejects
Update:
- `internal_calendar.status = rejected`
- add `calendar_feedback.reason`
- use this later for memory learning

### When user moves
The system should ask:
- "When would you prefer to do it?"
or suggest 2 to 3 alternative slots.

---

## 17. Relationship with Fatigue Layer

Telegram is a very good place to collect fatigue data because it is lightweight and immediate.

Examples:

### Inline prompt before answering
"How is your energy right now?"

Buttons:
- 0
- 1
- 2
- 3
- 4
- 5

### Scheduled check-in
"Quick check-in. How tired are you this evening?"

Use this carefully to avoid annoyance.

### Usage rule
Ask fatigue only when:
- current confidence is low
- a better answer depends on it
- system is calibrating a time window
- user has enabled fatigue prompts

This should store data in:
- `fatigue_checkins`
- `interaction_events`

Repeated signals later update:
- `fatigue_patterns`
- `learned_memories`

---

## 18. Security and Privacy

Telegram integration must be treated carefully because it is an external messaging channel.

## 18.1 Basic security rules

- never expose bot token on frontend
- store token securely in backend secrets
- verify account linking with one-time tokens
- do not trust raw Telegram user identity without linking
- log failures and suspicious link attempts
- use least-privilege storage for secrets

## 18.2 Privacy rules

Do not send overly sensitive information in Telegram by default.

Examples to avoid in plain notifications unless user clearly expects it:
- full private email contents
- sensitive personal notes
- highly detailed life summaries
- confidential documents

Instead send short, action-focused summaries.

Example:
Good:
"You have an important deadline tomorrow."

Less ideal:
"Your professor emailed saying your academic issue is urgent and here is the full text..."

## 18.3 Safe content defaults

Telegram should mostly send:
- summaries
- reminders
- suggestions
- confirmations
- follow-up questions

Detailed context can stay inside the web dashboard when needed.

---

## 19. Failure Handling

Telegram delivery can fail. Plan for this.

Common failure cases:
- user blocked bot
- chat id invalid
- webhook misconfigured
- expired linking state
- Telegram API temporary failure

Recommended behavior:
- mark `notifications.status = failed`
- store provider error metadata
- write `interaction_events`
- retry only when safe
- surface reconnect action in dashboard

---

## 20. Formatting Strategy

Telegram supports basic formatting, but keep it simple.

Recommended:
- short title line
- one concise explanation
- optional buttons
- avoid overly dense markdown

Example:

**Good**
Task suggestion:
Assignment A
4:00 PM to 5:00 PM
Best open window before tomorrow's deadline.

Buttons:
Confirm | Move | Reject

---

## 21. Recommended Environment Variables

Example variables:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_WEBHOOK_URL=
```

Optional:
```env
TELEGRAM_LINK_TOKEN_TTL_MINUTES=15
TELEGRAM_SEND_RETRY_LIMIT=3
```

---

## 22. Suggested API and Worker Responsibilities

## API routes

```text
POST /api/v1/telegram/webhook
POST /api/v1/telegram/link/start
POST /api/v1/telegram/link/complete
POST /api/v1/telegram/disconnect
POST /api/v1/telegram/send-test
```

## Worker jobs

```text
process_telegram_update
send_telegram_notification
send_calendar_block_to_telegram
send_fatigue_prompt_to_telegram
retry_failed_telegram_delivery
```

---

## 23. Suggested MVP Scope

The Telegram MVP should support only the most useful capabilities first.

## Must have
- bot setup and webhook
- account linking
- inbound text message handling
- outbound reply sending
- proactive reminder sending
- internal calendar suggestion messages
- inline buttons for confirm/reject/move
- fatigue prompt buttons
- interaction logging

## Nice to have
- `/status` summary
- `/plan` command
- reconnect flow
- markdown formatting helper
- message editing for cleaner UX

## Not needed yet
- voice notes
- file upload parsing
- advanced menus
- group chat support
- multilingual workflows

---

## 24. Recommended Build Order

1. Create Telegram bot with BotFather.
2. Build secure linking flow from web app to Telegram.
3. Create webhook endpoint.
4. Store inbound Telegram events in `interaction_events`.
5. Build Telegram client for outbound messages.
6. Support basic free-form chat replies.
7. Add proactive notification sending.
8. Add internal calendar suggestion actions.
9. Add fatigue prompt actions.
10. Add retry, monitoring, and reconnect handling.

---

## 25. Example Telegram UX Flows

## 25.1 Linking flow
User in web app:
- selects Telegram
- gets connect link

User in Telegram:
- starts bot
- sends code

Bot:
- "Your assistant is now connected."

## 25.2 Planning question
User:
- "What should I do tonight?"

System:
- fetches tasks, calendar, fatigue prior, memory
- returns ranked or direct recommendation
- optionally asks one fatigue question first

## 25.3 Proactive suggestion
Bot:
- "You have a free window from 6 PM to 7 PM. I suggest using it for resume work."

Buttons:
- Confirm
- Move
- Skip

## 25.4 Fatigue check-in
Bot:
- "Quick check-in. How is your energy right now?"

Buttons:
- 0
- 1
- 2
- 3
- 4
- 5

## 25.5 Rejection learning
Bot:
- sends suggestion
User:
- taps Reject
Bot:
- "What is the main reason?"
Buttons:
- Too tired
- Busy
- Wrong time
- Not urgent

This becomes a strong future learning signal.

---

## 26. Future Extensions

Later, Telegram can support:

- richer daily summaries
- weekly planning prompts
- voice notes
- better inline rescheduling
- deeper goal progress updates
- multiple communication channels with shared backend logic

But the main principle should remain the same:

Telegram is the interface layer, not the decision-making core.

---

## 27. Final Recommendation

For the current product direction, Telegram should be implemented as the MVP communication layer with webhook-based delivery, secure account linking, structured event logging, and strong support for proactive task suggestions and fatigue-aware interactions.

The best design is:

- Telegram for communication
- backend for orchestration
- internal calendar for planning
- database for truth
- memory and fatigue layers for personalization

That separation keeps the system simple, extensible, and aligned with the current architecture.
