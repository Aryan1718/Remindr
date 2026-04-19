import { sleep } from "@/lib/utils";

export async function simulateRequest<T>(resolver: () => T): Promise<T> {
  await sleep(200);
  return resolver();
}

export function getApiBaseUrl() {
  const viteEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
  return viteEnv?.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";
}

function findAuthTokenInStorage(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const directKeys = ["access_token", "supabase.access_token"];
  for (const key of directKeys) {
    const value = window.localStorage.getItem(key);
    if (value?.trim()) {
      return value.trim();
    }
  }

  for (let index = 0; index < window.localStorage.length; index += 1) {
    const key = window.localStorage.key(index);
    if (!key || !/^sb-.*-auth-token$/.test(key)) {
      continue;
    }

    const raw = window.localStorage.getItem(key);
    if (!raw) {
      continue;
    }

    try {
      const parsed = JSON.parse(raw) as unknown;
      const candidate = extractAccessToken(parsed);
      if (candidate) {
        return candidate;
      }
    } catch {
      continue;
    }
  }

  return null;
}

function extractAccessToken(value: unknown): string | null {
  if (!value) {
    return null;
  }
  if (typeof value === "string") {
    return null;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const candidate = extractAccessToken(item);
      if (candidate) {
        return candidate;
      }
    }
    return null;
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.access_token === "string" && record.access_token.trim()) {
      return record.access_token.trim();
    }
    for (const nested of Object.values(record)) {
      const candidate = extractAccessToken(nested);
      if (candidate) {
        return candidate;
      }
    }
  }
  return null;
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const authToken = findAuthTokenInStorage();
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  const payload = (await response.json()) as
    | T
    | { detail?: string; error?: { message?: string } };
  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null
        ? "error" in payload && payload.error?.message
          ? payload.error.message
          : "detail" in payload
            ? payload.detail
            : "Request failed"
        : "Request failed";
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }

  return payload as T;
}
