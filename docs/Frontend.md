# Fatigue-Aware Personal Assistant - Frontend

Last updated: April 18, 2026

## 1. Purpose

This document defines the frontend scope, page architecture, component system, application flows, and implementation plan for the web application.

The web application is **not** the primary conversational interface. The primary interaction channel for the MVP is Telegram, while the web app acts as the control and visibility layer for onboarding, task and goal management, integrations, and system state review.

This frontend will be built with **React + TypeScript** and will communicate with a **FastAPI backend**.

---

## 2. Frontend Role in the Product

The product is a proactive personal assistant that learns the user's routine, connects to user tools, and delivers well-timed actions through the preferred communication channel. The web app supports that system by giving the user a structured place to:

- complete onboarding
- connect external accounts
- manage tasks and goals
- view recommendations and schedule changes
- adjust preferences and notification behavior
- understand what the assistant is doing

### The web app is responsible for

- onboarding and setup
- control and visibility
- light editing workflows
- viewing tasks, goals, recommendations, and integrations

### The web app is not responsible for

- being the primary chat surface
- replacing Telegram for daily interaction
- acting like a complex productivity suite
- requiring heavy manual planning

---

## 3. Product Constraints That Shape the UI

The frontend must reflect the product principles:

- reduce cognitive load first
- ask fewer questions
- be proactive but not annoying
- explain decisions when needed
- learn from behavior, not just input

The system architecture also defines two client interfaces:

- web dashboard
- Telegram bot as MVP primary communication channel

This means the web experience should behave like a **control panel for the assistant**, not like a chat-heavy workspace.

---

## 4. Chosen Frontend Stack

### Core stack

- **React**
- **TypeScript**
- **Vite** for frontend build tooling
- **React Router** for client-side routing
- **TanStack Query** for server state and caching
- **Zustand** for lightweight client state
- **React Hook Form + Zod** for forms and validation
- **Tailwind CSS** for fast styling implementation with design tokens mapped from the design system

### Why this stack

This stack fits the project because:

- React + TypeScript supports a modular, production-ready frontend
- Vite keeps the setup lighter than Next.js and works well with a separate FastAPI backend
- TanStack Query cleanly handles async data from connectors, tasks, goals, and dashboard views
- Zustand avoids overcomplicating local UI state
- React Hook Form keeps onboarding and settings flows manageable
- Tailwind helps implement the Notion-inspired design consistently and quickly

---

## 5. Design System Usage

The web app should implement the uploaded Notion-inspired design system as the visual foundation.

### Visual direction

- warm neutral palette
- clean white surfaces
- whisper borders
- subtle shadows
- block-based layout
- strong readability
- minimal visual noise

### Key tokens to implement

#### Colors
- Background: `#ffffff`
- Alternate background: `#f6f5f4`
- Primary text: `rgba(0,0,0,0.95)`
- Secondary text: `#615d59`
- Muted text: `#a39e98`
- Primary accent: `#0075de`
- Focus color: `#097fe8`
- Border: `rgba(0,0,0,0.1)`

#### Borders and radius
- Standard border: `1px solid rgba(0,0,0,0.1)`
- Button radius: `4px`
- Standard card radius: `12px`
- Large card radius: `16px`
- Pill radius: `9999px`

#### Shadows
- Soft card shadow for default cards
- Deeper layered shadow for modals and highlighted panels

#### Typography
- Inter / Notion-like type stack
- clear hierarchy
- high readability
- restrained use of accent color

### UI philosophy

The design should feel:

- calm
- structured
- readable
- supportive
- low friction

It should **not** feel like:

- a dense dashboard
- an analytics product
- a chat client
- a power-user project management tool

---

## 6. Information Architecture

### Primary navigation

The sidebar navigation for the web app should contain:

1. Dashboard
2. Tasks
3. Goals
4. Integrations
5. Settings

### Conditional routes

6. Onboarding
7. Connector callback / status pages
8. Error / empty / not found states

### Suggested URL structure

- `/onboarding`
- `/dashboard`
- `/tasks`
- `/tasks/:taskId`
- `/goals`
- `/goals/:goalId`
- `/integrations`
- `/settings`
- `/connectors/:provider/callback`

---

## 7. Pages

## 7.1 Onboarding

### Purpose
Collect only the most reusable information and get the user into the product quickly.

### Goals
- create basic profile
- collect routine information
- capture decision style and fatigue preferences
- optionally capture an initial goal
- connect external tools
- set Telegram as the primary communication channel

### Steps

#### Step 1: Welcome
- product overview
- what data is collected
- why Telegram is used
- CTA to begin

#### Step 2: Basic profile
- name
- timezone
- role / context (student, job seeker, professional, other)

#### Step 3: Routine
- wake time
- sleep time
- work / class hours
- recurring commitments
- best focus window

#### Step 4: Decision preferences
- preferred style: direct recommendation vs ranked options
- reminder tolerance
- fatigue check-in preference

#### Step 5: Initial goal (optional)
- goal title
- time horizon
- importance
- optional notes

#### Step 6: Connectors
- Google Calendar
- Gmail
- connector permissions and explanation

#### Step 7: Telegram setup
- explain why Telegram is the main interaction channel
- show linking steps
- confirm channel connected

#### Step 8: Finish
- onboarding summary
- next actions
- redirect to dashboard

### Required components
- OnboardingLayout
- StepProgress
- StepCard
- FormField
- TimeInput
- PreferenceSelector
- ConnectorCard
- ChannelSetupCard
- OnboardingSummary

---

## 7.2 Dashboard

### Purpose
Provide the user with a calm overview of what matters now.

### Dashboard sections

#### 1. Today Focus
A compact list of the most important items for today.

Includes:
- top recommended tasks
- deadlines today or tomorrow
- direct next actions

#### 2. Suggestions
This is a core product block.

Examples:
- This is a good time to start your report
- You should review jobs today
- Your schedule is overloaded tomorrow

Each suggestion should show:
- primary recommendation
- short reason
- confidence / urgency indicator
- optional action buttons

#### 3. Upcoming Deadlines
- next upcoming tasks and goals
- time remaining
- risk state

#### 4. Recent Schedule Changes
- recommendations that changed task order
- shifted work blocks
- updated reminder timing

#### 5. Connector Status
- calendar connected or not
- email connected or not
- last sync indicator

### Dashboard behavior
- keep visible items limited
- avoid clutter
- prioritize clarity over density
- show empty states clearly

### Required components
- DashboardHeader
- FocusCard
- SuggestionCard
- DeadlineList
- ScheduleChangeList
- ConnectorStatusCard
- EmptyState
- LoadingSkeleton

---

## 7.3 Tasks

### Purpose
Allow the user to view, create, edit, and manage structured tasks.

### Views

#### Default list view
Each task card or row should show:
- title
- deadline
- estimated effort
- priority / urgency
- status
- energy requirement

#### Optional detail drawer / detail page
Show:
- description
- linked goal
- suggested execution window
- recommendation history
- status changes

### Key actions
- create task
- edit task
- mark complete
- snooze / defer
- change deadline
- change estimated effort

### Required components
- TaskList
- TaskCard
- TaskRow
- TaskFilters
- TaskEditorModal
- StatusBadge
- PriorityBadge
- EnergyTag

---

## 7.4 Goals

### Purpose
Support longer-term goals that the system can break into tasks and track over time.

### Goal list view
Each goal should show:
- title
- target timeline
- status
- linked task count
- progress indicator

### Goal detail view
Should display:
- goal summary
- timeline
- generated tasks
- watcher state
- recent related suggestions

### Key actions
- create goal
- edit goal
- archive goal
- view generated tasks

### Required components
- GoalList
- GoalCard
- GoalProgressBar
- GoalEditorModal
- GoalTaskSection
- WatcherStatusPanel

---

## 7.5 Integrations

### Purpose
Let the user connect, disconnect, and review data sources.

### MVP integrations
- Google Calendar
- Gmail

### Integration card content
- provider name
- status
- last sync time
- short explanation of what data is used
- connect / reconnect / disconnect actions

### Required components
- IntegrationsList
- IntegrationCard
- PermissionSummary
- SyncStatusBadge
- CallbackStatusView

---

## 7.6 Settings

### Purpose
Allow the user to control preferences without forcing them into a complex admin UI.

### Settings sections

#### Profile
- name
- timezone
- work mode / role

#### Decision preferences
- direct answers vs options
- fatigue prompt preference
- explanation depth

#### Notifications
- proactive suggestion frequency
- reminder style
- quiet hours

#### Data and privacy
- connector permissions
- delete data controls
- memory visibility / management later

### Required components
- SettingsSection
- ToggleRow
- PreferenceDropdown
- QuietHoursPicker
- DangerZoneCard

---

## 8. Shared Component System

## 8.1 Layout components

### `AppLayout`
- sidebar navigation
- top header area
- responsive collapse behavior

### `PageContainer`
- consistent max width
- vertical spacing
- page title + description slot

### `SectionBlock`
- reusable content section
- title
- description
- right-side action slot

### `SplitPanel`
- optional two-column layout for dashboard or settings areas

---

## 8.2 Base UI components

### `Button`
Variants:
- primary
- secondary
- ghost
- danger

### `Card`
Variants:
- standard
- elevated
- warm
- clickable

### `Badge`
Variants:
- status
- urgency
- sync
- suggestion type

### `Input`
### `Textarea`
### `Select`
### `Checkbox`
### `RadioGroup`
### `Toggle`
### `Tabs`
### `Modal`
### `Drawer`
### `DropdownMenu`
### `Tooltip`
### `Toast`

---

## 8.3 Product-specific components

### `SuggestionCard`
Most important product-specific component.

Fields:
- title
- short recommendation
- reason summary
- urgency / confidence badge
- action buttons

Actions:
- accept
- dismiss
- edit related task

### `RecommendationBlock`
Used where the system explains a recommendation.

Includes:
- primary recommendation
- alternatives if available
- short reasoning
- optional schedule change summary

### `FatigueSelector`
- simple 0-5 scale
- visually calm
- easy to submit quickly

### `TaskItem`
- compact task representation
- status and due date visible at a glance

### `GoalCard`
- title
- timeline
- progress
- watcher state

### `IntegrationCard`
- provider icon
- connection status
- description
- action buttons

### `TimelineList`
- today tasks
- upcoming events
- schedule change summaries

### `SyncIndicator`
- syncing
- synced
- failed

---

## 9. Application Flows

## 9.1 Onboarding flow

### Step-by-step flow
1. User lands on onboarding
2. User enters profile and routine
3. User chooses decision preferences
4. User optionally adds first goal
5. User connects calendar and email
6. User links Telegram
7. Frontend submits onboarding completion
8. User is redirected to dashboard

### Frontend responsibilities
- validate each step
- allow save and continue
- preserve partial progress locally if needed
- show connector states clearly
- show final completion state

---

## 9.2 Daily dashboard flow

1. User opens dashboard
2. Frontend fetches:
   - today tasks
   - recommendations
   - upcoming deadlines
   - connector statuses
3. User reviews current state
4. User may edit tasks or goals
5. Most daily interaction still happens via Telegram

### Important rule
The dashboard should **reflect assistant state**, not replace the assistant conversation channel.

---

## 9.3 Goal creation flow

1. User creates a goal
2. Frontend submits goal to backend
3. Backend structures the goal and may create sub-tasks
4. Frontend shows goal creation success state
5. Goal appears in goals list and dashboard context

---

## 9.4 Task management flow

1. User creates or edits a task
2. Frontend validates input
3. Task is saved through API
4. Task list updates optimistically or after refetch
5. If scheduling changes happen later, dashboard reflects them

---

## 9.5 Connector flow

1. User clicks connect on provider
2. Frontend redirects to provider auth flow
3. Provider returns to callback route
4. Frontend confirms connection result
5. Integration page updates status

---

## 9.6 Settings update flow

1. User changes preference
2. Frontend validates and submits patch request
3. Local UI updates
4. Success or error toast shown

---

## 10. State Management Plan

## 10.1 Server state with TanStack Query

Use TanStack Query for:
- dashboard data
- tasks
- goals
- integrations
- settings
- onboarding progress if fetched from backend

### Example query domains
- `dashboard`
- `tasks`
- `taskDetail`
- `goals`
- `goalDetail`
- `integrations`
- `settings`

## 10.2 Client state with Zustand

Use Zustand only for lightweight UI state such as:
- sidebar collapsed state
- onboarding current step
- active modal or drawer
- temporary filters and view preferences

Do not use Zustand as a replacement for server state.

---

## 11. API Integration Layer

The frontend should consume a FastAPI backend.

### Suggested frontend API organization

```text
src/
  api/
    client.ts
    auth.ts
    onboarding.ts
    dashboard.ts
    tasks.ts
    goals.ts
    integrations.ts
    settings.ts
```

### API concerns
- consistent error handling
- typed request and response models
- auth token injection
- retry logic only where appropriate
- cancellation support for route changes

### Expected API domains
- auth
- onboarding
- profile
- tasks
- goals
- integrations
- dashboard
- recommendations
- settings

---

## 12. Suggested Frontend Folder Structure

```text
src/
  app/
    router.tsx
    providers.tsx
  api/
    client.ts
    dashboard.ts
    tasks.ts
    goals.ts
    integrations.ts
    onboarding.ts
    settings.ts
  components/
    layout/
      AppLayout.tsx
      Sidebar.tsx
      TopBar.tsx
      PageContainer.tsx
      SectionBlock.tsx
    ui/
      Button.tsx
      Card.tsx
      Badge.tsx
      Input.tsx
      Select.tsx
      Modal.tsx
      Drawer.tsx
      Tabs.tsx
      EmptyState.tsx
      LoadingSkeleton.tsx
    onboarding/
      OnboardingLayout.tsx
      StepProgress.tsx
      RoutineStep.tsx
      PreferencesStep.tsx
      ConnectorsStep.tsx
      TelegramStep.tsx
    dashboard/
      FocusCard.tsx
      SuggestionCard.tsx
      DeadlineList.tsx
      ScheduleChangeList.tsx
      ConnectorStatusCard.tsx
    tasks/
      TaskList.tsx
      TaskCard.tsx
      TaskEditorModal.tsx
      TaskFilters.tsx
    goals/
      GoalList.tsx
      GoalCard.tsx
      GoalEditorModal.tsx
      WatcherStatusPanel.tsx
    integrations/
      IntegrationCard.tsx
      IntegrationsList.tsx
    settings/
      SettingsSection.tsx
      NotificationSettings.tsx
      DecisionPreferences.tsx
  features/
    dashboard/
      queries.ts
      types.ts
    tasks/
      queries.ts
      mutations.ts
      types.ts
    goals/
      queries.ts
      mutations.ts
      types.ts
    integrations/
      queries.ts
      mutations.ts
      types.ts
    onboarding/
      mutations.ts
      types.ts
  hooks/
    useSidebar.ts
    useToast.ts
  lib/
    utils.ts
    cn.ts
    constants.ts
  pages/
    OnboardingPage.tsx
    DashboardPage.tsx
    TasksPage.tsx
    TaskDetailPage.tsx
    GoalsPage.tsx
    GoalDetailPage.tsx
    IntegrationsPage.tsx
    SettingsPage.tsx
    ConnectorCallbackPage.tsx
  stores/
    uiStore.ts
  styles/
    globals.css
    tokens.css
  types/
    api.ts
    domain.ts
```

---

## 13. Responsive Behavior

The app must remain usable on smaller screens, but the first build is web-first.

### Desktop-first priorities
- clean sidebar navigation
- wide dashboard sections
- visible task and goal overviews

### Tablet behavior
- narrower sidebar
- stacked dashboard cards where needed

### Mobile behavior
- sidebar becomes drawer
- dashboard becomes single-column
- forms stay simple and readable
- no dense multi-column layouts

---

## 14. Accessibility Requirements

The design system already emphasizes strong contrast and visible focus states. The frontend implementation must preserve that.

### Must-have accessibility requirements
- keyboard navigable sidebar and forms
- visible focus rings
- semantic form labels
- aria labels for icon-only actions
- color not used as the only status signal
- readable contrast on all text and badges

---

## 15. Empty, Loading, and Error States

### Empty states
Must exist for:
- no tasks
- no goals
- no recommendations
- no integrations connected

### Loading states
Use lightweight skeletons for:
- dashboard cards
- list pages
- connector status

### Error states
Show:
- clear human-readable message
- retry action if appropriate
- limited technical detail in UI

---

## 16. Frontend Milestones

## Milestone 1 - Foundation
- project setup with React + TypeScript + Vite
- routing
- design tokens
- layout shell
- base UI components

## Milestone 2 - Onboarding
- onboarding flow
- routine and preference forms
- connector setup UI
- Telegram setup step

## Milestone 3 - Dashboard
- dashboard data queries
- Today Focus block
- Suggestions block
- upcoming deadlines
- connector status block

## Milestone 4 - Tasks and Goals
- tasks CRUD UI
- goals CRUD UI
- task and goal detail views

## Milestone 5 - Settings and polish
- settings page
- loading and error states
- responsive refinement
- accessibility pass

---

## 17. Non-Goals for Frontend MVP

Do not build these in the first frontend version:

- full chat interface in web
- advanced calendar drag-and-drop planner
- dense analytics dashboard
- complicated kanban workflows
- multi-user collaboration features
- voice UI inside the web app

---

## 18. Final Frontend Principle

The frontend should feel like:

- a calm control panel
- a lightweight planning companion
- a clear view into what the assistant knows and recommends

It should not feel like:

- a chat product
- a heavy planning suite
- a noisy dashboard
- a system the user must constantly manage manually

The assistant does the proactive work. The web app helps the user set it up, inspect it, and guide it.
