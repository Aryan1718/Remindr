import type {
  DashboardData,
  Goal,
  Integration,
  OnboardingDraft,
  ProfileSettings,
  Task,
} from "@/types/domain";

const storageKey = "fuk-frontend-mock-db";

interface MockDb {
  dashboard: DashboardData;
  tasks: Task[];
  goals: Goal[];
  integrations: Integration[];
  settings: ProfileSettings;
  onboarding: OnboardingDraft;
}

const onboardingDefaults: OnboardingDraft = {
  stage: "onboarding",
  name: "Chris",
  timezone: "UTC-8 (Pacific Time)",
  role: "professional",
  bio: "",
  wakeTime: "07:00",
  sleepTime: "23:00",
  workStart: "09:00",
  workEnd: "17:00",
  workHours: "9:00 AM - 5:00 PM",
  commitments: "Tue/Thu meetings, evening gym",
  focusWindow: "morning",
  weekendPattern: "flexible",
  decisionStyle: "Direct recommendation",
  reminderTolerance: "Balanced",
  fatigueCheckIn: "Only when needed",
  recommendationStyle: "Balanced",
  reminderStyle: "Gentle",
  notificationFrequency: "Moderate",
  quietHoursStart: "22:00",
  quietHoursEnd: "08:00",
  goalTitle: "Land the MVP planning sprint",
  goalHorizon: "4 weeks",
  goalImportance: "High",
  goalNotes: "Need steady progress without overload.",
  tasks: [],
  connectors: [],
  telegramConnected: false,
  completed: false,
};

function normalizeOnboardingDraft(draft?: Partial<OnboardingDraft>): OnboardingDraft {
  return {
    ...onboardingDefaults,
    ...draft,
    tasks: draft?.tasks ? draft.tasks.map((task) => ({ ...task })) : [],
    connectors: draft?.connectors ? [...draft.connectors] : [],
  };
}

const seedTasks: Task[] = [
  {
    id: "task-1",
    title: "Draft product strategy memo",
    description: "Write the first draft before the Monday review.",
    deadline: new Date(Date.now() + 86_400_000).toISOString(),
    estimatedEffort: "90 min",
    priority: "High",
    status: "In progress",
    energy: "High",
    linkedGoalId: "goal-1",
    suggestedWindow: "1:00 PM - 2:30 PM",
    history: ["Moved earlier because your afternoon is overloaded.", "Reminder delayed after low-energy check-in."],
  },
  {
    id: "task-2",
    title: "Review three open job listings",
    description: "Capture fit notes and save two follow-ups.",
    deadline: new Date(Date.now() + 2 * 86_400_000).toISOString(),
    estimatedEffort: "45 min",
    priority: "Medium",
    status: "Planned",
    energy: "Medium",
    linkedGoalId: "goal-2",
    suggestedWindow: "4:00 PM - 4:45 PM",
    history: ["Grouped with outreach work to reduce context switching."],
  },
  {
    id: "task-3",
    title: "Triage Gmail inbox for urgent replies",
    description: "Reply to flagged senders and archive low-value threads.",
    deadline: new Date().toISOString(),
    estimatedEffort: "25 min",
    priority: "High",
    status: "Planned",
    energy: "Low",
    suggestedWindow: "11:30 AM - 11:55 AM",
    history: ["Pulled forward because it unblocks later work."],
  },
];

const seedGoals: Goal[] = [
  {
    id: "goal-1",
    title: "Ship assistant MVP planning pack",
    summary: "Finish the product, architecture, and implementation package for the MVP.",
    timeline: "This month",
    status: "Active",
    progress: 72,
    linkedTaskIds: ["task-1"],
    watcherState: "On track",
    suggestions: ["Keep writing tasks before noon when focus is strongest."],
  },
  {
    id: "goal-2",
    title: "Restart focused job search",
    summary: "Build a light weekly routine for job review and outreach.",
    timeline: "Next 6 weeks",
    status: "At risk",
    progress: 28,
    linkedTaskIds: ["task-2"],
    watcherState: "Needs input",
    suggestions: ["Narrow target roles to avoid low-yield browsing."],
  },
];

const seedIntegrations: Integration[] = [
  {
    id: "calendar",
    provider: "Google Calendar",
    status: "Connected",
    lastSync: "5 minutes ago",
    description: "Used to understand routines, meetings, and open focus windows.",
    permissions: ["Read calendars", "Read event metadata"],
  },
  {
    id: "gmail",
    provider: "Gmail",
    status: "Needs reconnect",
    lastSync: "Yesterday",
    description: "Used to detect urgent threads and timing-sensitive commitments.",
    permissions: ["Read message metadata", "Read sender and labels"],
  },
  {
    id: "outlook",
    provider: "Outlook",
    status: "Not connected",
    lastSync: "Not linked",
    description: "Used to pull work communication signals and confirmed scheduling context.",
    permissions: ["Read mailbox metadata", "Read calendar metadata"],
  },
  {
    id: "telegram",
    provider: "Telegram",
    status: "Connected",
    lastSync: "Live",
    description: "Primary communication channel for suggestions and check-ins.",
    permissions: ["Send messages", "Receive user replies"],
  },
];

const seedSettings: ProfileSettings = {
  name: "Chris",
  timezone: "America/Los_Angeles",
  role: "Professional",
  decisionStyle: "Direct recommendation",
  fatiguePreference: "Only when needed",
  explanationDepth: "Balanced",
  suggestionFrequency: "Balanced",
  reminderStyle: "Gentle",
  quietHours: {
    start: "21:30",
    end: "07:00",
  },
};

const seedOnboarding: OnboardingDraft = normalizeOnboardingDraft();

const seedDb: MockDb = {
  dashboard: {
    todayFocus: [seedTasks[0], seedTasks[2]],
    suggestions: [
      {
        id: "suggestion-1",
        title: "Protect your best focus block",
        recommendation: "Start the strategy memo before lunch.",
        reason: "Your calendar is light and your last three high-output sessions happened before 2 PM.",
        urgency: "High",
        confidence: "Very strong",
        type: "focus",
      },
      {
        id: "suggestion-2",
        title: "Reduce tomorrow's overload",
        recommendation: "Move inbox triage into today and keep tomorrow for review work.",
        reason: "Tomorrow already has two fixed meetings and a goal checkpoint.",
        urgency: "Medium",
        confidence: "Strong",
        type: "schedule",
      },
    ],
    deadlines: [seedTasks[2], seedTasks[0], seedTasks[1]],
    scheduleChanges: [
      "Inbox triage moved from tomorrow morning to today at 11:30 AM.",
      "Memo block shortened to 90 minutes after lower afternoon energy was detected.",
      "Reminder cadence reduced tonight because quiet hours begin at 9:30 PM.",
    ],
    connectors: seedIntegrations,
  },
  tasks: seedTasks,
  goals: seedGoals,
  integrations: seedIntegrations,
  settings: seedSettings,
  onboarding: seedOnboarding,
};

function loadDb(): MockDb {
  const raw = window.localStorage.getItem(storageKey);
  if (!raw) return seedDb;

  try {
    const parsed = JSON.parse(raw) as Partial<MockDb>;
    return {
      ...seedDb,
      ...parsed,
      onboarding: normalizeOnboardingDraft(parsed.onboarding),
    };
  } catch {
    return seedDb;
  }
}

let db: MockDb = loadDb();

function persist() {
  window.localStorage.setItem(storageKey, JSON.stringify(db));
}

export function getDb() {
  return db;
}

export function updateDb(updater: (current: MockDb) => MockDb) {
  db = updater(db);
  persist();
  return db;
}
