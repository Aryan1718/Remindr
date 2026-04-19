import { create } from "zustand";
import {
  clearStoredSession,
  fetchUserSnapshot,
  persistSession,
  readStoredSession,
  signInWithPassword,
  syncSession,
  type StoredSession,
} from "@/api/auth";
import type { UserSnapshot } from "@/types/auth";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface LoginPayload {
  email: string;
  password: string;
  rememberMe: boolean;
}

interface OAuthCallbackPayload {
  accessToken: string;
  refreshToken?: string | null;
}

interface AuthStore {
  status: AuthStatus;
  snapshot: UserSnapshot | null;
  accessToken: string | null;
  initialized: boolean;
  error: string | null;
  initialize: () => Promise<void>;
  login: (payload: LoginPayload) => Promise<UserSnapshot>;
  completeOAuthLogin: (payload: OAuthCallbackPayload) => Promise<UserSnapshot>;
  logout: () => void;
  clearError: () => void;
}

function preferredName(snapshot: UserSnapshot): string | undefined {
  return snapshot.user.full_name ?? snapshot.user.email ?? undefined;
}

async function hydrateSession(stored: StoredSession): Promise<UserSnapshot> {
  try {
    return await syncSession(stored.accessToken);
  } catch {
    return fetchUserSnapshot(stored.accessToken);
  }
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  status: "loading",
  snapshot: null,
  accessToken: null,
  initialized: false,
  error: null,
  async initialize() {
    if (get().initialized) {
      return;
    }

    const stored = readStoredSession();
    if (!stored) {
      set({ status: "unauthenticated", snapshot: null, accessToken: null, initialized: true });
      return;
    }

    set({ status: "loading", error: null });

    try {
      const snapshot = await hydrateSession(stored);
      set({
        status: "authenticated",
        snapshot,
        accessToken: stored.accessToken,
        initialized: true,
        error: null,
      });
    } catch (error) {
      clearStoredSession();
      set({
        status: "unauthenticated",
        snapshot: null,
        accessToken: null,
        initialized: true,
        error: error instanceof Error ? error.message : "Unable to restore your session",
      });
    }
  },
  async login({ email, password, rememberMe }) {
    set({ status: "loading", error: null });

    try {
      const session = await signInWithPassword(email, password);
      const snapshot = await syncSession(session.access_token, {
        full_name:
          session.user.user_metadata?.full_name ||
          session.user.user_metadata?.name ||
          undefined,
      });

      persistSession(
        {
          accessToken: session.access_token,
          refreshToken: session.refresh_token ?? null,
        },
        rememberMe,
      );

      set({
        status: "authenticated",
        snapshot,
        accessToken: session.access_token,
        initialized: true,
        error: null,
      });

      return snapshot;
    } catch (error) {
      clearStoredSession();
      const message = error instanceof Error ? error.message : "Unable to sign in";
      set({
        status: "unauthenticated",
        snapshot: null,
        accessToken: null,
        initialized: true,
        error: message,
      });
      throw error;
    }
  },
  async completeOAuthLogin({ accessToken, refreshToken }) {
    set({ status: "loading", error: null });

    try {
      const snapshot = await syncSession(accessToken);
      persistSession(
        {
          accessToken,
          refreshToken: refreshToken ?? null,
        },
        true,
      );
      set({
        status: "authenticated",
        snapshot,
        accessToken,
        initialized: true,
        error: null,
      });
      return snapshot;
    } catch (error) {
      clearStoredSession();
      const message = error instanceof Error ? error.message : "Unable to finish sign in";
      set({
        status: "unauthenticated",
        snapshot: null,
        accessToken: null,
        initialized: true,
        error: message,
      });
      throw error;
    }
  },
  logout() {
    clearStoredSession();
    set({
      status: "unauthenticated",
      snapshot: null,
      accessToken: null,
      initialized: true,
      error: null,
    });
  },
  clearError() {
    if (get().error) {
      set({ error: null });
    }
  },
}));

export function getPostLoginRoute(snapshot: UserSnapshot | null): string {
  if (!snapshot) {
    return "/login";
  }

  return snapshot.preferences.onboarding_completed ? "/dashboard" : "/onboarding";
}

export function getDisplayName(snapshot: UserSnapshot | null): string | null {
  if (!snapshot) {
    return null;
  }

  return preferredName(snapshot) ?? null;
}
