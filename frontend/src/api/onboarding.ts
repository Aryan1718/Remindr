import { simulateRequest } from "@/api/client";
import { getDb, updateDb } from "@/mocks/db";
import type { OnboardingDraft } from "@/types/domain";

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
      },
    }));
    return draft;
  });
}
