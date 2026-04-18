import { simulateRequest } from "@/api/client";
import { getDb, updateDb } from "@/mocks/db";
import type { ProfileSettings } from "@/types/domain";

export function getSettings() {
  return simulateRequest(() => getDb().settings);
}

export function saveSettings(settings: ProfileSettings) {
  return simulateRequest(() => {
    updateDb((current) => ({ ...current, settings }));
    return settings;
  });
}
