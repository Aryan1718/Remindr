import { simulateRequest } from "@/api/client";
import { getDb, updateDb } from "@/mocks/db";
import type { OnboardingDraft } from "@/types/domain";

function mapNotificationFrequency(value: OnboardingDraft["notificationFrequency"]) {
  if (value === "High") return "High" as const;
  if (value === "Low") return "Low" as const;
  return "Balanced" as const;
}

function mapReminderStyle(value: OnboardingDraft["reminderStyle"]) {
  if (value === "Persistent") return "Escalating" as const;
  if (value === "Minimal") return "Direct" as const;
  return "Gentle" as const;
}

export function getOnboardingDraft() {
  return simulateRequest(() => getDb().onboarding);
}

export function saveOnboardingDraft(draft: OnboardingDraft) {
  return simulateRequest(() => {
    updateDb((current) => ({
      ...current,
      onboarding: draft,
      settings: {
        ...current.settings,
        name: draft.name,
        timezone: draft.timezone,
        role: draft.role,
        decisionStyle: draft.decisionStyle,
        fatiguePreference: draft.fatigueCheckIn,
        suggestionFrequency: mapNotificationFrequency(draft.notificationFrequency),
        reminderStyle: mapReminderStyle(draft.reminderStyle),
        quietHours: {
          start: draft.quietHoursStart,
          end: draft.quietHoursEnd,
        },
      },
    }));
    return draft;
  });
}
