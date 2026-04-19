import { readStoredSession } from "@/api/auth";
import { requestJson, simulateRequest } from "@/api/client";
import { getDb, updateDb } from "@/mocks/db";
import { useAuthStore } from "@/stores/authStore";
import type { Integration } from "@/types/domain";

interface TelegramConnectionResponse {
  success: boolean;
  data: {
    connection: {
      user_id: string;
      bot_username: string | null;
      bot_first_name: string | null;
      bot_token_hint: string;
      telegram_user_id: number | null;
      telegram_chat_id: number | null;
      webhook_url: string | null;
      webhook_status: string;
      last_event_at: string | null;
      updated_at: string;
    } | null;
  };
}

interface CurrentUserResponse {
  success: boolean;
  data: {
    user: {
      id: string;
    };
  };
}

interface ConnectorListResponse {
  success: boolean;
  data: {
    items: Array<{
      id: string;
      provider: "google_calendar" | "gmail" | "telegram" | "google_notes";
      status: "connected" | "expired" | "revoked" | "error";
      account_email: string | null;
      metadata_json: Record<string, unknown>;
      last_sync_at: string | null;
      updated_at: string | null;
    }>;
  };
}

interface ConnectorEnvelopeResponse {
  success: boolean;
  data: {
    connector?: {
      id: string;
      provider: "google_calendar";
      status: "connected" | "expired" | "revoked" | "error";
      account_email: string | null;
      metadata_json: Record<string, unknown>;
      last_sync_at: string | null;
      updated_at: string | null;
    };
    connector_id?: string;
    job_id?: string;
    job_type?: string;
    job_status?: string;
  };
}

interface TelegramConnectPayload {
  botToken: string;
  webhookBaseUrl?: string;
}

export interface GoogleCalendarConnectPayload {
  accountEmail: string;
  accessToken: string;
  refreshToken?: string;
  tokenExpiresAt?: string;
  calendarId?: string;
}

interface GoogleCalendarOAuthStartResponse {
  success: boolean;
  data: {
    authorization_url: string;
  };
}

async function getCurrentUserId() {
  const response = await requestJson<CurrentUserResponse>("/me");
  return response.data.user.id;
}

function formatTelegramIntegration(
  base: Integration,
  connection: TelegramConnectionResponse["data"]["connection"],
): Integration {
  if (!connection) {
    return {
      ...base,
      status: "Not connected",
      lastSync: "Not linked",
      description:
        "Bring your own Telegram bot token, then start that bot in Telegram so this app can receive webhook events for your account.",
    };
  }

  const isLinked = connection.telegram_chat_id !== null;
  const lastSync = connection.last_event_at
    ? new Date(connection.last_event_at).toLocaleString()
    : "Waiting for /start";

  return {
    ...base,
    status: isLinked ? "Connected" : "Needs reconnect",
    lastSync,
    description: isLinked
      ? "Your Telegram bot is registered and linked to a Telegram chat. Webhook events are being stored by the backend."
      : "Bot token saved. Open your bot in Telegram and send /start so the backend can capture the chat id.",
  };
}

async function fetchTelegramConnection() {
  try {
    const response = await requestJson<TelegramConnectionResponse>("/telegram/bots/me");
    return response.data.connection;
  } catch {
    return null;
  }
}

function formatGoogleCalendarIntegration(
  base: Integration,
  connection:
    | ConnectorListResponse["data"]["items"][number]
    | null,
): Integration {
  if (!connection) {
    return {
      ...base,
      status: "Not connected",
      lastSync: "Not linked",
      description:
        "Connect Google Calendar so the assistant can read external commitments as scheduling constraints without writing into the internal planner.",
    };
  }

  const connected = connection.status === "connected";
  return {
    ...base,
    status: connected ? "Connected" : "Needs reconnect",
    lastSync: connection.last_sync_at ? new Date(connection.last_sync_at).toLocaleString() : "Waiting for first sync",
    description: connected
      ? `Reading ${String(connection.metadata_json.calendar_id || "primary")} for external availability and constraint sync.`
      : "The Google Calendar connector exists, but it needs attention before sync can continue cleanly.",
  };
}

async function fetchConnectorList() {
  try {
    const response = await requestJson<ConnectorListResponse>("/connectors");
    return response.data.items;
  } catch {
    return [];
  }
}

export async function listIntegrations() {
  const connectors = await fetchConnectorList();
  const telegramConnection = await fetchTelegramConnection();
  return simulateRequest(() => {
    const integrations = getDb().integrations;

    return integrations.map((integration) =>
      integration.id === "calendar"
        ? formatGoogleCalendarIntegration(
            integration,
            connectors.find((connector) => connector.provider === "google_calendar") ?? null,
          )
        : integration.id === "telegram"
        ? formatTelegramIntegration(integration, telegramConnection)
        : integration,
    );
  });
}

export function saveIntegration(integration: Integration) {
  return simulateRequest(() => {
    updateDb((current) => ({
      ...current,
      integrations: current.integrations.map((entry) =>
        entry.id === integration.id ? integration : entry,
      ),
      dashboard: {
        ...current.dashboard,
        connectors: current.dashboard.connectors.map((entry) =>
          entry.id === integration.id ? integration : entry,
        ),
      },
    }));

    return integration;
  });
}

export async function connectTelegramBot({ botToken, webhookBaseUrl }: TelegramConnectPayload) {
  const accessToken = useAuthStore.getState().accessToken ?? readStoredSession()?.accessToken ?? null;
  if (!accessToken) {
    throw new Error("You need to log in again before connecting Telegram.");
  }

  await getCurrentUserId();
  const response = await requestJson<TelegramConnectionResponse>("/telegram/bots/connect", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      bot_token: botToken,
      webhook_base_url: webhookBaseUrl || undefined,
    }),
  });

  return response.data.connection;
}

export async function connectGoogleCalendar({
  accountEmail,
  accessToken,
  refreshToken,
  tokenExpiresAt,
  calendarId,
}: GoogleCalendarConnectPayload) {
  const response = await requestJson<ConnectorEnvelopeResponse>("/connectors/google-calendar/connect", {
    method: "POST",
    body: JSON.stringify({
      account_email: accountEmail,
      access_token: accessToken,
      refresh_token: refreshToken || undefined,
      token_expires_at: tokenExpiresAt || undefined,
      metadata_json: {
        calendar_id: calendarId || "primary",
      },
    }),
  });

  return response.data.connector;
}

export async function triggerGoogleCalendarSync(connectorId: string) {
  const response = await requestJson<ConnectorEnvelopeResponse>(`/connectors/${connectorId}/sync`, {
    method: "POST",
    body: JSON.stringify({
      sync_mode: "incremental",
      lookahead_days: 14,
      lookback_days: 7,
      force: false,
    }),
  });

  return response.data;
}

export async function startGoogleCalendarOAuth() {
  const response = await requestJson<GoogleCalendarOAuthStartResponse>("/connectors/google-calendar/oauth/start", {
    method: "POST",
    body: JSON.stringify({}),
  });
  return response.data.authorization_url;
}
