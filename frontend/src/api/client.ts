import { sleep } from "@/lib/utils";

export async function simulateRequest<T>(resolver: () => T): Promise<T> {
  await sleep(200);
  return resolver();
}

export function getApiBaseUrl() {
  const viteEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
  return viteEnv?.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const payload = (await response.json()) as T | { detail?: string };
  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? payload.detail
        : "Request failed";
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }

  return payload as T;
}
