export type AppRoute =
  | "/onboarding"
  | "/dashboard"
  | "/tasks"
  | "/goals"
  | "/integrations"
  | "/settings";

export type StatusTone = "neutral" | "success" | "warning" | "danger" | "info";

export interface Suggestion {
  id: string;
  title: string;
  recommendation: string;
  reason: string;
  urgency: "Low" | "Medium" | "High";
  confidence: "Cautious" | "Strong" | "Very strong";
  type: "focus" | "schedule" | "deadline";
}

export interface Task {
  id: string;
  title: string;
  description: string;
  deadline: string;
  estimatedEffort: string;
  priority: "Low" | "Medium" | "High";
  status: "Planned" | "In progress" | "Completed" | "Deferred";
  energy: "Low" | "Medium" | "High";
  linkedGoalId?: string;
  suggestedWindow: string;
  history: string[];
}

export interface Goal {
  id: string;
  title: string;
  summary: string;
  timeline: string;
  status: "Active" | "At risk" | "Completed";
  progress: number;
  linkedTaskIds: string[];
  watcherState: "Watching" | "Needs input" | "On track";
  suggestions: string[];
}

export interface Integration {
  id: "calendar" | "gmail" | "telegram";
  provider: string;
  status: "Connected" | "Needs reconnect" | "Not connected";
  lastSync: string;
  description: string;
  permissions: string[];
}

export interface DashboardData {
  todayFocus: Task[];
  suggestions: Suggestion[];
  deadlines: Task[];
  scheduleChanges: string[];
  connectors: Integration[];
}

export interface ProfileSettings {
  name: string;
  timezone: string;
  role: string;
  decisionStyle: "Direct recommendation" | "Ranked options";
  fatiguePreference: "Daily" | "Only when needed" | "Manual only";
  explanationDepth: "Brief" | "Balanced" | "Detailed";
  suggestionFrequency: "Low" | "Balanced" | "High";
  reminderStyle: "Gentle" | "Direct" | "Escalating";
  quietHours: {
    start: string;
    end: string;
  };
}

export interface OnboardingDraft {
  stage: "onboarding" | "connectors" | "channel" | "complete";
  name: string;
  timezone: string;
  role: string;
  wakeTime: string;
  sleepTime: string;
  workHours: string;
  commitments: string;
  focusWindow: string;
  decisionStyle: "Direct recommendation" | "Ranked options";
  reminderTolerance: "Light" | "Balanced" | "High";
  fatigueCheckIn: "Daily" | "Only when needed" | "Manual only";
  goalTitle: string;
  goalHorizon: string;
  goalImportance: "Low" | "Medium" | "High";
  goalNotes: string;
  connectors: ("calendar" | "gmail")[];
  telegramConnected: boolean;
  completed: boolean;
}
