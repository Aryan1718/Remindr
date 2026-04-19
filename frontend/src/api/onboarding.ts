import { requestJson } from "@/api/client";
import type { ApiSuccessEnvelope, UserSnapshot } from "@/types/auth";
import type { OnboardingDraft } from "@/types/domain";

const DISPLAY_TO_IANA_TIMEZONE: Record<string, string> = {
  "UTC-8 (Pacific Time)": "America/Los_Angeles",
  "UTC-5 (Eastern Time)": "America/New_York",
  "UTC-6 (Central Time)": "America/Chicago",
  "UTC+0 (GMT)": "Etc/UTC",
  "UTC+1 (CET)": "Europe/Paris",
  "UTC+8 (Singapore)": "Asia/Singapore",
};

function normalizeTimezone(value: string | null | undefined) {
  if (!value) return "America/Los_Angeles";
  return DISPLAY_TO_IANA_TIMEZONE[value] ?? value;
}

function titleCase(value: string) {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function asString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function asBoolean(value: unknown, fallback = false) {
  return typeof value === "boolean" ? value : fallback;
}

function mapSnapshotToDraft(snapshot: UserSnapshot): OnboardingDraft {
  const profile = snapshot.preferences.profile_json ?? {};
  const preferredResponse = asString(snapshot.preferences.preferred_response_style, "balanced").toLowerCase();
  const reminderTolerance = asString(snapshot.preferences.reminder_tolerance, "gentle").toLowerCase();

  return {
    stage: snapshot.preferences.onboarding_completed ? "complete" : "onboarding",
    name: snapshot.user.full_name ?? "",
    timezone: normalizeTimezone(snapshot.user.timezone),
    role: asString(profile.role, "professional"),
    bio: asString(profile.bio),
    wakeTime: snapshot.preferences.wake_time ?? "07:00",
    sleepTime: snapshot.preferences.sleep_time ?? "23:00",
    workStart: snapshot.preferences.work_start_time ?? "09:00",
    workEnd: snapshot.preferences.work_end_time ?? "17:00",
    workHours: `${snapshot.preferences.work_start_time ?? "09:00"} - ${snapshot.preferences.work_end_time ?? "17:00"}`,
    commitments: asString(profile.recurringCommitments),
    focusWindow: asString(profile.focusWindow, "morning"),
    weekendPattern: asString(profile.weekendPattern, "flexible"),
    decisionStyle:
      asString(snapshot.preferences.decision_style_default).toLowerCase() === "direct_recommendation"
        ? "Direct recommendation"
        : "Ranked options",
    reminderTolerance:
      reminderTolerance === "persistent"
        ? "High"
        : reminderTolerance === "minimal"
          ? "Light"
          : "Balanced",
    fatigueCheckIn: snapshot.preferences.fatigue_prompt_enabled ? "Daily" : "Manual only",
    recommendationStyle: titleCase(preferredResponse) as OnboardingDraft["recommendationStyle"],
    reminderStyle:
      reminderTolerance === "persistent"
        ? "Persistent"
        : reminderTolerance === "minimal"
          ? "Minimal"
          : "Gentle",
    notificationFrequency: titleCase(asString(profile.notificationFrequency, "moderate")) as OnboardingDraft["notificationFrequency"],
    quietHoursStart: asString(profile.quietHoursStart, "22:00"),
    quietHoursEnd: asString(profile.quietHoursEnd, "08:00"),
    goalTitle: "",
    goalHorizon: "",
    goalImportance: "Medium",
    goalNotes: "",
    tasks: [],
    connectors: [],
    telegramConnected: asBoolean(profile.telegramConnected),
    completed: snapshot.preferences.onboarding_completed,
  };
}

function mapDraftToSnapshotPayload(draft: OnboardingDraft) {
  const reminderTolerance =
    draft.reminderStyle === "Persistent"
      ? "persistent"
      : draft.reminderStyle === "Minimal"
        ? "minimal"
        : "gentle";

  return {
    full_name: draft.name.trim(),
    timezone: normalizeTimezone(draft.timezone),
    wake_time: draft.wakeTime,
    sleep_time: draft.sleepTime,
    work_start_time: draft.workStart,
    work_end_time: draft.workEnd,
    preferred_response_style: draft.recommendationStyle.toLowerCase(),
    decision_style_default:
      draft.decisionStyle === "Direct recommendation" ? "direct_recommendation" : "ranked_options",
    reminder_tolerance: reminderTolerance,
    fatigue_prompt_enabled: draft.fatigueCheckIn !== "Manual only",
    onboarding_completed: draft.completed,
    profile_json: {
      role: draft.role,
      bio: draft.bio,
      recurringCommitments: draft.commitments,
      focusWindow: draft.focusWindow,
      weekendPattern: draft.weekendPattern,
      notificationFrequency: draft.notificationFrequency.toLowerCase(),
      quietHoursStart: draft.quietHoursStart,
      quietHoursEnd: draft.quietHoursEnd,
      telegramConnected: draft.telegramConnected,
    },
  };
}

export function getOnboardingDraft() {
  return requestJson<ApiSuccessEnvelope<UserSnapshot>>("/me").then((response) => mapSnapshotToDraft(response.data));
}

export function saveOnboardingDraft(draft: OnboardingDraft) {
  return requestJson<ApiSuccessEnvelope<UserSnapshot>>("/me", {
    method: "PATCH",
    body: JSON.stringify(mapDraftToSnapshotPayload(draft)),
  }).then((response) => response.data);
}
