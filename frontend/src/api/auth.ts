import { frontendEnv } from "@/lib/env";
import type {
  ApiErrorEnvelope,
  ApiSuccessEnvelope,
  SupabasePasswordSession,
  UserSnapshot,
} from "@/types/auth";

const SESSION_STORAGE_KEY = "remindr.auth.session";

export interface StoredSession {
  accessToken: string;
  refreshToken: string | null;
}

export class AuthApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, options?: { code?: string; status?: number }) {
    super(message);
    this.name = "AuthApiError";
    this.code = options?.code ?? "auth_error";
    this.status = options?.status ?? 500;
  }
}

function resolveErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const apiPayload = payload as ApiErrorEnvelope & {
    msg?: string;
    error_description?: string;
  };

  return (
    apiPayload.error?.message ||
    apiPayload.msg ||
    apiPayload.error_description ||
    fallback
  );
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function requestJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  const payload = await parseJson(response);

  if (!response.ok) {
    throw new AuthApiError(resolveErrorMessage(payload, "Request failed"), {
      code:
        typeof payload === "object" && payload && "error" in payload
          ? ((payload as ApiErrorEnvelope).error?.code ?? "request_failed")
          : "request_failed",
      status: response.status,
    });
  }

  return payload as T;
}

export async function signInWithPassword(email: string, password: string): Promise<SupabasePasswordSession> {
  return requestJson<SupabasePasswordSession>(
    `${frontendEnv.supabaseUrl}/auth/v1/token?grant_type=password`,
    {
      method: "POST",
      headers: {
        apikey: frontendEnv.supabaseAnonKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    },
  );
}

export async function fetchUserSnapshot(accessToken: string): Promise<UserSnapshot> {
  const response = await requestJson<ApiSuccessEnvelope<UserSnapshot>>(
    `${frontendEnv.apiBaseUrl}/me`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  return response.data;
}

export async function syncSession(
  accessToken: string,
  payload: { full_name?: string; timezone?: string } = {},
): Promise<UserSnapshot> {
  const response = await requestJson<ApiSuccessEnvelope<UserSnapshot>>(
    `${frontendEnv.apiBaseUrl}/auth/session/sync`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return response.data;
}

function storageForPersistence(persist: boolean): Storage {
  return persist ? window.localStorage : window.sessionStorage;
}

export function persistSession(session: StoredSession, persist: boolean) {
  window.localStorage.removeItem(SESSION_STORAGE_KEY);
  window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
  storageForPersistence(persist).setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function readStoredSession(): StoredSession | null {
  const raw =
    window.localStorage.getItem(SESSION_STORAGE_KEY) ??
    window.sessionStorage.getItem(SESSION_STORAGE_KEY);

  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<StoredSession>;
    if (typeof parsed.accessToken !== "string" || parsed.accessToken.length === 0) {
      return null;
    }

    return {
      accessToken: parsed.accessToken,
      refreshToken: typeof parsed.refreshToken === "string" ? parsed.refreshToken : null,
    };
  } catch {
    return null;
  }
}

export function clearStoredSession() {
  window.localStorage.removeItem(SESSION_STORAGE_KEY);
  window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
}
