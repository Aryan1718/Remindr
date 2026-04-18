# Fatigue-Aware Personal Assistant - PRD

Last updated: April 18, 2026

## 1. Product Overview

### One-line summary
A proactive personal assistant that learns a user’s routine, connects to their tools, and delivers well-timed actions through their preferred communication channel.

### Core idea
Instead of static reminders, the system:
- learns how the user actually works
- understands real-world context (calendar, email, tasks)
- predicts the best time to act
- proactively guides the user

---

## 2. Problem Statement

Current tools fail because:
- reminders are static and poorly timed
- users forget to track tasks manually
- tools do not adapt to fatigue or real-life context
- long-term goals are not actively managed

Result:
Users miss deadlines, procrastinate, and feel overwhelmed.

---

## 3. Goals

### Primary goals
- Reduce missed deadlines
- Reduce cognitive load
- Improve follow-through on tasks and goals
- Deliver the right action at the right time

### Secondary goals
- Learn user behavior over time
- Provide proactive suggestions (not just reactive replies)
- Integrate seamlessly into user’s existing workflow

---

## 4. Target Users

- Students managing assignments and deadlines
- Job seekers preparing applications
- Professionals managing tasks and meetings
- Anyone overwhelmed with planning and execution

---

## 5. Core Features

## 5.1 Onboarding

Collect:
- daily routine (sleep, work, classes)
- preferred communication channel
- fatigue/decision style
- initial goals
- connector setup

Connect:
- Google Calendar / Outlook
- Gmail / Outlook Mail
- Optional: task tools

Output:
- user profile
- initial context model

---

## 5.2 Connectors

### Core connectors (MVP)
- Calendar → availability and schedule
- Email → incoming obligations
- Internal task system → structured control

### Optional (later)
- Slack / Teams
- Location
- Health / sleep
- Notes

---

## 5.3 Communication Layer

User selects:
- Telegram (MVP recommended)
- WhatsApp (later)
- Web dashboard (control + visibility)

Assistant behavior:
- conversational interface
- proactive nudges
- minimal friction interaction

---

## 5.4 Goal System

User can define:
- long-term goals (e.g., “switch jobs in 2 months”)

System:
- asks follow-up questions
- structures the goal
- breaks it into tasks
- creates ongoing monitoring jobs

---

## 5.5 Task & Planning System

Each task includes:
- deadline
- estimated effort
- importance
- energy requirement
- status

System:
- recommends execution timing
- splits tasks if needed
- adjusts plans dynamically

---

## 5.6 Proactive Intelligence

Instead of reminders:
- detects best execution windows
- monitors deadline risk
- suggests actions at the right time

Examples:
- “This is a good time to start your report”
- “You should review jobs today”
- “Your schedule is overloaded tomorrow”

---

## 5.7 Memory & Learning

System learns:
- user productivity patterns
- preferred work hours
- response to suggestions
- completion behavior

Stores:
- structured preferences
- behavioral patterns
- interaction outcomes

---

## 5.8 Watchers (Background Jobs)

Examples:
- job search monitor
- deadline risk tracker
- schedule overload detector

These run continuously and trigger actions.

---

## 6. User Flow

### Step 1 - Onboarding
User:
- inputs routine
- connects apps
- selects Telegram

### Step 2 - Initial goal
User:
“I want to switch jobs in 2 months”

System:
- asks clarifying questions
- creates structured goal
- sets up watchers

### Step 3 - Daily operation
System:
- reads calendar/email
- tracks tasks
- detects opportunities
- sends proactive suggestions

### Step 4 - Learning loop
System:
- observes behavior
- updates model
- improves timing and suggestions

---

## 7. Success Metrics

### Product metrics
- daily active usage
- retention
- interaction frequency

### Outcome metrics
- task completion rate
- deadline adherence
- recommendation acceptance rate

### Quality metrics
- user corrections
- ignored suggestions
- timing accuracy

---

## 8. MVP Scope

### Must have
- onboarding (basic)
- calendar integration
- Telegram bot
- goal creation
- task system
- simple proactive suggestion logic

### Nice to have
- email integration
- basic memory
- simple watcher (job search or deadlines)

---

## 9. Non-Goals (for hackathon)

- full mobile app
- complex multi-agent orchestration
- full health integration
- enterprise-grade integrations

---

## 10. Risks

- privacy concerns → mitigate with transparency
- poor timing suggestions → start simple
- over-notification → adaptive frequency
- too complex onboarding → keep minimal

---

## 11. Product Principles

- reduce cognitive load first
- ask fewer questions
- be proactive but not annoying
- explain decisions when needed
- learn from behavior, not just input