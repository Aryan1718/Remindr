# Authentication and Authorization Context

Last updated: April 18, 2026

## 1. Purpose

This file defines how authentication and authorization should work for the Fatigue-Aware Personal Assistant using:

- **Frontend:** React + TypeScript
- **Backend:** FastAPI
- **Auth Provider:** Supabase Auth
- **Database:** Supabase Postgres

The goal is to keep authentication simple for the hackathon, while making the system secure enough to support:

- onboarding and login
- protected dashboard access
- connector setup
- Telegram or other communication-channel linking
- user-specific tasks, goals, reminders, and memories
- backend APIs that act only on behalf of the authenticated user

---

## 2. Core Decision

We will use **Supabase Auth as the source of identity**.

That means:

- Supabase handles sign up, sign in, sign out, session refresh, and user identity
- the React app uses the Supabase client for auth state
- the FastAPI backend verifies Supabase JWTs on protected routes
- all user-owned records are scoped by `user_id`
- authorization is enforced in the backend and database access patterns, not only in the UI

This gives us a clean setup with minimal custom auth logic.

---

## 3. Goals

### Authentication goals
- support email/password login for MVP
- support persistent sessions in the web app
- keep onboarding tied to the authenticated user
- allow secure logout and session expiration handling

### Authorization goals
- users can only access their own data
- connectors are only visible and manageable by the owner
- backend endpoints reject missing or invalid tokens
- future admin or support roles can be added without redesigning the whole system

### Product alignment
This matches the product direction in the PRD and architecture, where the backend owns structured user data and connector relationships, while the web dashboard is the control surface for onboarding, settings, and visibility into tasks and goals. fileciteturn0file1 fileciteturn0file2

---

## 4. Scope for MVP

## Included
- sign up
- sign in
- sign out
- session persistence
- protected routes in React
- protected FastAPI endpoints
- user profile creation after sign up
- per-user access to tasks, goals, reminders, memories, and connectors

## Not included yet
- enterprise SSO
- organization workspaces
- fine-grained RBAC for teams
- delegated access
- audit console for admins
- complex permission builder UI

---

## 5. Identity Model

Supabase Auth provides the primary identity.

### Primary identity fields
- `auth.users.id` -> canonical user id
- `auth.users.email`
- `auth.users.created_at`

### App-level profile table
Create an app table such as `profiles` or `user_profiles`.

Recommended fields:
- `id` (UUID, same as Supabase user id)
- `full_name`
- `timezone`
- `fatigue_preference_mode`
- `decision_style`
- `communication_channel`
- `onboarding_completed`
- `created_at`
- `updated_at`

Rule:
- Supabase Auth stores identity
- app tables store product-specific profile and settings

---

## 6. Authorization Model

For MVP, use **owner-based authorization**.

Every important record belongs to exactly one user.

Examples:
- `tasks.user_id`
- `goals.user_id`
- `reminders.user_id`
- `decision_requests.user_id`
- `fatigue_checkins.user_id`
- `learned_memories.user_id`
- `connectors.user_id`

### Authorization rule
A user can:
- create their own records
- read their own records
- update their own records
- delete their own records

A user cannot:
- access another user’s records
- link or manage another user’s connector
- trigger actions for another user

### Future-ready role field
Even though MVP is owner-only, we should still keep a lightweight role field for future use.

Recommended values:
- `user`
- `admin` later if needed

This role can live in:
- `profiles.role`, or
- Supabase user metadata

For hackathon simplicity, `profiles.role = 'user'` is enough.

---

## 7. High-Level Auth Flow

## 7.1 Sign up flow
1. User opens web app.
2. User signs up with email and password.
3. Supabase creates auth user.
4. Frontend receives session.
5. Backend or post-signup logic creates `profiles` row.
6. User is redirected into onboarding.

## 7.2 Sign in flow
1. User enters email and password.
2. Supabase validates credentials.
3. Frontend stores session through Supabase client.
4. Protected UI becomes available.
5. API calls include access token in `Authorization: Bearer <token>`.

## 7.3 Protected API flow
1. React app calls FastAPI endpoint.
2. JWT is sent in Authorization header.
3. FastAPI verifies token against Supabase JWT settings or JWKS.
4. Backend extracts authenticated user id.
5. Backend queries only rows owned by that user.
6. Response returns only authorized data.

## 7.4 Sign out flow
1. User clicks sign out.
2. Frontend calls `supabase.auth.signOut()`.
3. Local session is cleared.
4. User is redirected to login page.

---

## 8. React Frontend Auth Context Design

Create a frontend auth context responsible for exposing auth state across the app.

Recommended file name:

- `src/context/AuthContext.tsx`

Related files:
- `src/lib/supabase.ts`
- `src/routes/ProtectedRoute.tsx`
- `src/hooks/useAuth.ts`

## 8.1 Responsibilities of AuthContext
- initialize Supabase client
- track current session
- track current user
- expose loading state during session resolution
- expose signIn, signUp, signOut helpers
- listen to `onAuthStateChange`
- make auth state available to the whole React app

## 8.2 Recommended exposed shape

```ts
interface AuthContextValue {
  user: User | null;
  session: Session | null;
  loading: boolean;
  isAuthenticated: boolean;
  signUp: (email: string, password: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}
```

## 8.3 Behavior rules
- `loading` should remain `true` until initial session resolution finishes
- `isAuthenticated` should be derived from `!!session && !!user`
- app layout should not render protected content until auth loading is resolved
- all API calls should use the latest access token from Supabase session

## 8.4 Why context is needed
The app will have multiple protected pages:
- onboarding
- dashboard
- connectors
- goals
- tasks
- settings

Using a single auth context prevents duplicated auth checks and keeps route protection consistent.

---

## 9. Route Protection in React

Use a wrapper such as:

- `ProtectedRoute.tsx`

Behavior:
- if `loading`, show a lightweight loader
- if not authenticated, redirect to `/login`
- if authenticated, render child route

Protected pages for MVP:
- `/onboarding`
- `/dashboard`
- `/connectors`
- `/goals`
- `/tasks`
- `/settings`

Public pages:
- `/login`
- `/signup`
- landing page

Optional UX rule:
- if user is authenticated but onboarding is incomplete, redirect to `/onboarding`
- if onboarding is complete, redirect to `/dashboard`

---

## 10. FastAPI Backend Authentication Design

The backend should never trust the frontend alone.

Every protected endpoint must verify the Supabase JWT.

Recommended structure:
- `app/core/auth.py`
- `app/dependencies/auth.py`
- `app/api/routes/...`

## 10.1 Backend responsibilities
- read bearer token from header
- verify token signature and validity
- extract `sub` as authenticated user id
- optionally load profile from database
- reject unauthorized requests with 401
- enforce record ownership with filtered queries

## 10.2 Dependency pattern
Use a reusable dependency like:
- `get_current_user()`
- `get_current_user_id()`

Each protected route should depend on one of these.

Example behavior:
- missing token -> `401 Unauthorized`
- invalid token -> `401 Unauthorized`
- valid token but no matching profile yet -> create profile or return controlled error based on endpoint needs

## 10.3 Important rule
Even if the frontend hides another user’s data, backend queries must still always filter by authenticated `user_id`.

Correct pattern:

```python
SELECT * FROM tasks WHERE user_id = current_user_id
```

Not acceptable:
- query by public id only
- trust `user_id` passed from client body
- accept ownership claims from frontend state

---

## 11. Token Strategy

Supabase issues JWT-based sessions.

### Frontend
- session is managed by Supabase client
- access token is retrieved when making API calls
- token is sent as bearer token to FastAPI

### Backend
- token is verified before executing protected logic
- authenticated user id comes from token claims

### Best practices
- do not store custom auth state separately from Supabase session
- do not trust local storage values as identity without verification
- do not pass `user_id` from frontend as source of truth
- always derive the acting user from the verified token

---

## 12. Database Ownership Rules

Because this app stores highly personal data such as routines, fatigue patterns, reminders, and connector accounts, ownership boundaries must be strict. This aligns directly with the trust and privacy direction in the product spec. fileciteturn0file0

## 12.1 Required ownership columns
All user-owned tables should have:
- `user_id UUID NOT NULL`
- foreign key to auth user or profile id
- indexed `user_id`

## 12.2 Recommended tables for MVP auth scope
- `profiles`
- `tasks`
- `goals`
- `reminders`
- `fatigue_checkins`
- `decision_requests`
- `recommendations`
- `connectors`
- `learned_memories`

## 12.3 Connector ownership
A connector row should include fields like:
- `id`
- `user_id`
- `provider`
- `status`
- `external_account_email`
- `scopes_json`
- `connected_at`
- `last_synced_at`

Only the owning user can:
- connect it
- disconnect it
- refresh it
- view its sync status

---

## 13. Supabase Row Level Security Direction

Because Supabase is being used, we should keep the schema compatible with Row Level Security even if some hackathon queries are routed through FastAPI.

Recommended approach:

### Option A - FastAPI-enforced authorization first
Use FastAPI as the main data access layer.

Pros:
- easier to centralize logic
- simpler for orchestration-heavy flows
- clearer integration with workers and business logic

### Option B - FastAPI + RLS together
Use RLS on user-owned tables as a second protection layer.

Recommended long-term direction:
- enable RLS on user-owned tables
- add policies using `auth.uid() = user_id`
- keep FastAPI checks as the application-layer protection

This gives defense in depth.

Example RLS intent:
- authenticated users can only select their own rows
- authenticated users can only insert rows with their own `user_id`
- authenticated users can only update/delete their own rows

---

## 14. Onboarding Authorization Rules

Onboarding must be authenticated.

Why:
- onboarding creates persistent user profile data
- onboarding stores communication preferences
- onboarding may link calendar or email connectors
- onboarding determines which dashboard state should be shown later

Rules:
- unauthenticated users cannot save onboarding data
- onboarding writes only to the authenticated user’s profile
- connector linking during onboarding must be tied to the authenticated user id
- onboarding completion should update `profiles.onboarding_completed = true`

---

## 15. Connector and Channel Security

The app is expected to connect tools such as calendar, email, and messaging channels. The architecture already treats connectors and the communication layer as core system components. fileciteturn0file1

### Rules
- external access tokens must never be exposed to the frontend after storage
- connector secrets should be stored securely on the backend side
- frontend should only see connector status and safe metadata
- user must explicitly initiate connect and disconnect actions
- background jobs must always execute in the context of the owner user

### Telegram linking rule
If Telegram is used as the communication channel:
- the dashboard should store the mapping between app user and Telegram chat/channel identity
- backend must verify that outbound notifications are sent only for the linked authenticated user
- no shared bot state should allow cross-user leakage

---

## 16. Suggested Frontend File Structure

```text
src/
  context/
    AuthContext.tsx
  hooks/
    useAuth.ts
  lib/
    supabase.ts
    api.ts
  routes/
    ProtectedRoute.tsx
  pages/
    LoginPage.tsx
    SignupPage.tsx
    OnboardingPage.tsx
    DashboardPage.tsx
    ConnectorsPage.tsx
    TasksPage.tsx
    GoalsPage.tsx
    SettingsPage.tsx
```

### File purposes
- `supabase.ts` -> creates Supabase browser client
- `AuthContext.tsx` -> holds auth/session state
- `useAuth.ts` -> convenience hook
- `ProtectedRoute.tsx` -> blocks unauthenticated access
- `api.ts` -> attaches bearer token to backend requests

---

## 17. Suggested Backend File Structure

```text
app/
  api/
    routes/
      auth.py
      profiles.py
      tasks.py
      goals.py
      connectors.py
  core/
    config.py
    auth.py
  dependencies/
    auth.py
  models/
  services/
  repositories/
```

### File purposes
- `core/auth.py` -> JWT verification helpers
- `dependencies/auth.py` -> FastAPI auth dependencies
- `routes/*` -> protected endpoints using current authenticated user
- `repositories/*` -> always query by `user_id`

---

## 18. Recommended API Rules

### Public endpoints
- `POST /auth/signup` only if backend wraps signup, otherwise handled by frontend Supabase client
- `POST /auth/login` only if backend wraps login, otherwise handled by frontend Supabase client
- health checks

### Protected endpoints
- `GET /me`
- `PUT /me/profile`
- `GET /tasks`
- `POST /tasks`
- `GET /goals`
- `POST /goals`
- `GET /connectors`
- `POST /connectors/:provider/connect`
- `POST /connectors/:provider/disconnect`

### Rule for protected endpoints
Every protected route must:
- require verified token
- derive current user from token
- ignore any conflicting `user_id` from request body

---

## 19. Error Handling Rules

### Frontend
Show clear states for:
- invalid credentials
- expired session
- unauthorized access
- connector authorization failure

### Backend
Return:
- `401` for unauthenticated requests
- `403` only if authenticated but forbidden by role or policy later
- `404` when resource does not exist for that user

Important:
For owner-scoped resources, returning `404` is often better than revealing that another user’s resource exists.

---

## 20. Security Best Practices for MVP

- use HTTPS everywhere in deployed environments
- keep Supabase anon key only in frontend environment, never service role key
- keep service role key only on the backend if needed
- validate JWTs on backend for all protected routes
- index `user_id` on user-owned tables
- log auth failures and connector failures
- do not expose connector refresh tokens to browser
- do not store secrets in client-side code
- rotate secrets if leaked during development

---

## 21. Recommended Implementation Order

1. Create Supabase project.
2. Add auth tables and `profiles` table.
3. Build `src/lib/supabase.ts`.
4. Build `AuthContext.tsx`.
5. Build `useAuth.ts` hook.
6. Build `ProtectedRoute.tsx`.
7. Add login and signup pages.
8. Add FastAPI JWT verification dependency.
9. Protect `/me`, `/tasks`, `/goals`, `/connectors` endpoints.
10. Add ownership filtering in repositories.
11. Add onboarding completion logic.
12. Add optional RLS policies.

---

## 22. Final Recommendation

For this project, the cleanest and most suitable auth design is:

- **Supabase Auth for authentication**
- **React AuthContext for app-wide session state**
- **FastAPI token verification for protected API access**
- **owner-based authorization using `user_id` on every user-owned record**
- **optional Row Level Security for defense in depth**

This approach fits the current architecture and MVP scope because it is simple enough for hackathon speed, but structured enough to support future connectors, background watchers, and personalized assistant behavior. fileciteturn0file1 fileciteturn0file2
