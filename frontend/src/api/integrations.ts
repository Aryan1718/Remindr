import { simulateRequest } from "@/api/client";
import { getDb, updateDb } from "@/mocks/db";
import type { Integration } from "@/types/domain";

export function listIntegrations() {
  return simulateRequest(() => getDb().integrations);
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
