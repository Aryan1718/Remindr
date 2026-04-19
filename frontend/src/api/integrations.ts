import { requestJson, simulateRequest } from "@/api/client";
import { getDb, updateDb } from "@/mocks/db";
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

interface TelegramConnectPayload {
  botToken: string;
  webhookBaseUrl?: string;
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

export async function listIntegrations() {
  const telegramConnection = await fetchTelegramConnection();
  return simulateRequest(() => {
    const integrations = getDb().integrations;

    return integrations.map((integration) =>
      integration.id === "telegram"
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
  await getCurrentUserId()
  const response = await requestJson<TelegramConnectionResponse>("/telegram/bots/connect", {
    method: "POST",
    body: JSON.stringify({
      bot_token: botToken,
      webhook_base_url: webhookBaseUrl || undefined,
    }),
  });

  return response.data.connection;
}
