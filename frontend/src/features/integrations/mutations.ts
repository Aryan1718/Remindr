import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  connectGoogleCalendar,
  connectTelegramBot,
  saveIntegration,
  triggerGoogleCalendarSync,
  type GoogleCalendarConnectPayload,
} from "@/api/integrations";
import type { Integration } from "@/types/domain";

export function useSaveIntegrationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (integration: Integration) => saveIntegration(integration),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["integrations"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useConnectTelegramBotMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ botToken, webhookBaseUrl }: { botToken: string; webhookBaseUrl?: string }) =>
      connectTelegramBot({ botToken, webhookBaseUrl }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["integrations"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useConnectGoogleCalendarMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: GoogleCalendarConnectPayload) => connectGoogleCalendar(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["integrations"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useTriggerGoogleCalendarSyncMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (connectorId: string) => triggerGoogleCalendarSync(connectorId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["integrations"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
