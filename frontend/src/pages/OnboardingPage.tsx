import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Clock,
  ListTodo,
  Moon,
  Plus,
  Settings,
  Sun,
  Trash2,
  User,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useSaveOnboardingMutation } from "@/features/onboarding/mutations";
import { useOnboardingQuery } from "@/features/onboarding/queries";
import type { OnboardingDraft, OnboardingTask } from "@/types/domain";

type StepId = 0 | 1 | 2 | 3 | 4 | 5;

interface OnboardingFormState {
  fullName: string;
  timezone: string;
  role: string;
  bio: string;
  wakeTime: string;
  sleepTime: string;
  workStart: string;
  workEnd: string;
  recurringCommitments: string;
  focusWindow: string;
  weekendPattern: string;
  tasks: OnboardingTask[];
  recommendationStyle: string;
  reminderStyle: string;
  fatigueCheckIn: string;
  notificationFrequency: string;
  quietHoursStart: string;
  quietHoursEnd: string;
  telegramConnected: boolean;
}

const steps = [
  { id: 0 as const, name: "Welcome", icon: CheckCircle2 },
  { id: 1 as const, name: "Profile", icon: User },
  { id: 2 as const, name: "Routine", icon: Clock },
  { id: 3 as const, name: "Tasks", icon: ListTodo },
  { id: 4 as const, name: "Preferences", icon: Settings },
  { id: 5 as const, name: "Review", icon: CheckCircle2 },
];

const fieldClassName =
  "w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white transition-all duration-200 placeholder:text-white/30 focus:border-cyan-400/50 focus:bg-white/10 focus:outline-none";

const textAreaClassName = `${fieldClassName} resize-none`;

const panelStyle = {
  background:
    "linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%)",
  backdropFilter: "blur(22px)",
  WebkitBackdropFilter: "blur(22px)",
};

function normalizeRole(role: string) {
  const value = role.trim().toLowerCase();
  const allowed = ["professional", "student", "freelancer", "entrepreneur", "creative", "researcher"];
  return allowed.includes(value) ? value : "professional";
}

function normalizeFocusWindow(value: string) {
  const normalized = value.trim().toLowerCase();
  if (["early-morning", "morning", "afternoon", "evening", "night"].includes(normalized)) {
    return normalized;
  }
  if (normalized.includes("night")) return "night";
  if (normalized.includes("evening")) return "evening";
  if (normalized.includes("afternoon")) return "afternoon";
  return "morning";
}

function normalizeWeekendPattern(value: string) {
  const normalized = value.trim().toLowerCase();
  if (["flexible", "similar", "rest", "partial"].includes(normalized)) return normalized;
  return "flexible";
}

function normalizeRecommendationStyle(value?: string) {
  const normalized = value?.trim().toLowerCase();
  if (normalized === "aggressive") return "aggressive";
  if (normalized === "gentle") return "gentle";
  return "balanced";
}

function normalizeReminderStyle(value?: string, fallback?: OnboardingDraft["reminderTolerance"]) {
  const normalized = value?.trim().toLowerCase();
  if (normalized === "persistent") return "persistent";
  if (normalized === "minimal") return "minimal";
  if (normalized === "gentle") return "gentle";

  if (fallback === "High") return "persistent";
  if (fallback === "Light") return "minimal";
  return "gentle";
}

function normalizeFatigueCheckIn(value: OnboardingDraft["fatigueCheckIn"]) {
  if (value === "Daily") return "daily";
  if (value === "Manual only") return "disabled";
  return "weekly";
}

function normalizeNotificationFrequency(value?: string) {
  const normalized = value?.trim().toLowerCase();
  if (normalized === "high") return "high";
  if (normalized === "low") return "low";
  return "moderate";
}

function titleFromValue(value: string) {
  return value
    .replace(/-/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function buildWorkHours(start: string, end: string) {
  return `${start} - ${end}`;
}

function createTask(): OnboardingTask {
  return {
    id: crypto.randomUUID(),
    title: "",
    description: "",
    dueDate: "",
    effort: "1-2 hours",
    priority: "medium",
    energyLevel: "medium",
    recurring: false,
    preferredTime: "morning",
  };
}

function createDefaultFormState(): OnboardingFormState {
  return {
    fullName: "",
    timezone: "America/Los_Angeles",
    role: "professional",
    bio: "",
    wakeTime: "07:00",
    sleepTime: "23:00",
    workStart: "09:00",
    workEnd: "17:00",
    recurringCommitments: "",
    focusWindow: "morning",
    weekendPattern: "flexible",
    tasks: [],
    recommendationStyle: "balanced",
    reminderStyle: "gentle",
    fatigueCheckIn: "daily",
    notificationFrequency: "moderate",
    quietHoursStart: "22:00",
    quietHoursEnd: "08:00",
    telegramConnected: false,
  };
}

function mapDraftToFormState(draft: OnboardingDraft): OnboardingFormState {
  return {
    fullName: draft.name,
    timezone: draft.timezone,
    role: normalizeRole(draft.role),
    bio: draft.bio,
    wakeTime: draft.wakeTime,
    sleepTime: draft.sleepTime,
    workStart: draft.workStart,
    workEnd: draft.workEnd,
    recurringCommitments: draft.commitments,
    focusWindow: normalizeFocusWindow(draft.focusWindow),
    weekendPattern: normalizeWeekendPattern(draft.weekendPattern),
    tasks: draft.tasks.map((task) => ({ ...task })),
    recommendationStyle: normalizeRecommendationStyle(draft.recommendationStyle),
    reminderStyle: normalizeReminderStyle(draft.reminderStyle, draft.reminderTolerance),
    fatigueCheckIn: normalizeFatigueCheckIn(draft.fatigueCheckIn),
    notificationFrequency: normalizeNotificationFrequency(draft.notificationFrequency),
    quietHoursStart: draft.quietHoursStart,
    quietHoursEnd: draft.quietHoursEnd,
    telegramConnected: draft.telegramConnected,
  };
}

function mapFormStateToDraft(
  formState: OnboardingFormState,
  currentDraft: OnboardingDraft | undefined,
  completed: boolean,
): OnboardingDraft {
  const trimmedName = formState.fullName.trim();

  return {
    stage: completed ? "complete" : "onboarding",
    name: trimmedName,
    timezone: formState.timezone,
    role: formState.role,
    bio: formState.bio.trim(),
    wakeTime: formState.wakeTime,
    sleepTime: formState.sleepTime,
    workStart: formState.workStart,
    workEnd: formState.workEnd,
    workHours: buildWorkHours(formState.workStart, formState.workEnd),
    commitments: formState.recurringCommitments.trim(),
    focusWindow: formState.focusWindow,
    weekendPattern: formState.weekendPattern,
    decisionStyle: formState.recommendationStyle === "aggressive" ? "Direct recommendation" : "Ranked options",
    reminderTolerance:
      formState.reminderStyle === "persistent"
        ? "High"
        : formState.reminderStyle === "minimal"
          ? "Light"
          : "Balanced",
    fatigueCheckIn:
      formState.fatigueCheckIn === "daily" || formState.fatigueCheckIn === "twice-daily"
        ? "Daily"
        : formState.fatigueCheckIn === "disabled"
          ? "Manual only"
          : "Only when needed",
    recommendationStyle: titleFromValue(formState.recommendationStyle) as OnboardingDraft["recommendationStyle"],
    reminderStyle: titleFromValue(formState.reminderStyle) as OnboardingDraft["reminderStyle"],
    notificationFrequency:
      titleFromValue(formState.notificationFrequency) as OnboardingDraft["notificationFrequency"],
    quietHoursStart: formState.quietHoursStart,
    quietHoursEnd: formState.quietHoursEnd,
    goalTitle: currentDraft?.goalTitle ?? "",
    goalHorizon: currentDraft?.goalHorizon ?? "",
    goalImportance: currentDraft?.goalImportance ?? "Medium",
    goalNotes: currentDraft?.goalNotes ?? "",
    tasks: formState.tasks.map((task) => ({ ...task })),
    connectors: currentDraft?.connectors ? [...currentDraft.connectors] : [],
    telegramConnected: formState.telegramConnected,
    completed,
  };
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const { data: onboardingDraft } = useOnboardingQuery();
  const saveOnboardingMutation = useSaveOnboardingMutation();

  const [currentStep, setCurrentStep] = useState<StepId>(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formState, setFormState] = useState<OnboardingFormState>(createDefaultFormState);
  const [didHydrateFromDraft, setDidHydrateFromDraft] = useState(false);

  const particles = useMemo(
    () =>
      Array.from({ length: 15 }, (_, index) => ({
        id: `particle-${index}`,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        duration: 3 + Math.random() * 4,
        delay: Math.random() * 5,
      })),
    [],
  );

  useEffect(() => {
    if (!onboardingDraft || didHydrateFromDraft) return;

    setFormState(mapDraftToFormState(onboardingDraft));
    if (onboardingDraft.completed) {
      setCurrentStep(5);
    }
    setDidHydrateFromDraft(true);
  }, [didHydrateFromDraft, onboardingDraft]);

  function updateFormState<K extends keyof OnboardingFormState>(key: K, value: OnboardingFormState[K]) {
    setFormState((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function addTask() {
    const nextTask = createTask();
    setFormState((current) => ({
      ...current,
      tasks: [...current.tasks, nextTask],
    }));
  }

  function updateTask(id: string, updates: Partial<OnboardingTask>) {
    setFormState((current) => ({
      ...current,
      tasks: current.tasks.map((task) => (task.id === id ? { ...task, ...updates } : task)),
    }));
  }

  function removeTask(id: string) {
    setFormState((current) => ({
      ...current,
      tasks: current.tasks.filter((task) => task.id !== id),
    }));
  }

  function validateStep(step: StepId) {
    const nextErrors: Record<string, string> = {};

    if (step === 1 && formState.fullName.trim().length === 0) {
      nextErrors.fullName = "Full name is required";
    }

    if (step === 3) {
      const hasIncompleteTask = formState.tasks.some((task) => task.title.trim().length === 0);
      if (hasIncompleteTask) {
        nextErrors.tasks = "Please complete all task titles or remove incomplete tasks";
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function saveDraft(completed: boolean) {
    const draft = mapFormStateToDraft(formState, onboardingDraft, completed);
    saveOnboardingMutation.mutate(draft);
  }

  function nextStep() {
    if (!validateStep(currentStep)) return;

    saveDraft(false);
    setErrors({});
    setCurrentStep((current) => Math.min(current + 1, 5) as StepId);
  }

  function prevStep() {
    setErrors({});
    setCurrentStep((current) => Math.max(current - 1, 0) as StepId);
  }

  async function finishOnboarding() {
    if (!validateStep(currentStep)) return;

    const draft = {
      ...mapFormStateToDraft(formState, onboardingDraft, false),
      stage: "connectors" as const,
      connectors: [],
      telegramConnected: false,
      completed: false,
    };
    await saveOnboardingMutation.mutateAsync(draft);
    navigate("/integrations");
  }

  function renderWelcomeStep() {
    return (
      <div className="mx-auto max-w-xl py-12 text-center remindr-onboarding-step-entry">
        <h2 className="text-4xl text-white">
          Set up <span className="remindr-wordmark">Remindr</span>
        </h2>
        <p className="mt-6 text-lg leading-relaxed text-cyan-100/70">
          Remindr learns your daily routine and active workload to build more intelligent task
          recommendations. This setup shapes how the assistant schedules work, respects energy, and
          nudges you through Telegram.
        </p>
        <button
          className="group mx-auto mt-12 flex items-center gap-3 rounded-xl border border-cyan-400/30 bg-gradient-to-r from-cyan-500/20 to-teal-500/20 px-8 py-4 text-cyan-100 transition-all duration-300 hover:border-cyan-400/50 hover:from-cyan-500/30 hover:to-teal-500/30"
          onClick={nextStep}
          type="button"
        >
          <span className="text-lg">Start setup</span>
          <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
        </button>
      </div>
    );
  }

  function renderProfileStep() {
    return (
      <div className="mx-auto max-w-2xl space-y-6 remindr-onboarding-step-entry">
        <h2 className="mb-8 text-3xl text-white">Basic Profile</h2>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="fullName">
            Full Name
          </label>
          <input
            className={`${fieldClassName} ${errors.fullName ? "border-red-400/50" : ""}`}
            id="fullName"
            onChange={(event) => updateFormState("fullName", event.target.value)}
            placeholder="Enter your full name"
            type="text"
            value={formState.fullName}
          />
          {errors.fullName ? (
            <div className="flex items-center gap-2 text-sm text-red-400">
              <AlertCircle className="h-4 w-4" />
              <span>{errors.fullName}</span>
            </div>
          ) : null}
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="timezone">
            Timezone
          </label>
          <select
            className={fieldClassName}
            id="timezone"
            onChange={(event) => updateFormState("timezone", event.target.value)}
            value={formState.timezone}
          >
            <option value="America/Los_Angeles">Pacific Time</option>
            <option value="America/New_York">Eastern Time</option>
            <option value="America/Chicago">Central Time</option>
            <option value="Etc/UTC">UTC</option>
            <option value="Europe/Paris">Central European Time</option>
            <option value="Asia/Singapore">Singapore Time</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="role">
            Role / Context
          </label>
          <select
            className={fieldClassName}
            id="role"
            onChange={(event) => updateFormState("role", event.target.value)}
            value={formState.role}
          >
            <option value="professional">Professional</option>
            <option value="student">Student</option>
            <option value="freelancer">Freelancer</option>
            <option value="entrepreneur">Entrepreneur</option>
            <option value="creative">Creative</option>
            <option value="researcher">Researcher</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="bio">
            Bio / Context (Optional)
          </label>
          <textarea
            className={textAreaClassName}
            id="bio"
            onChange={(event) => updateFormState("bio", event.target.value)}
            placeholder="Share any context that helps Remindr understand your workflow..."
            rows={3}
            value={formState.bio}
          />
        </div>
      </div>
    );
  }

  function renderRoutineStep() {
    return (
      <div className="mx-auto max-w-2xl space-y-6 remindr-onboarding-step-entry">
        <h2 className="mb-8 text-3xl text-white">Daily Routine</h2>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="wakeTime">
              <Sun className="h-4 w-4" />
              Wake Time
            </label>
            <input
              className={fieldClassName}
              id="wakeTime"
              onChange={(event) => updateFormState("wakeTime", event.target.value)}
              type="time"
              value={formState.wakeTime}
            />
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="sleepTime">
              <Moon className="h-4 w-4" />
              Sleep Time
            </label>
            <input
              className={fieldClassName}
              id="sleepTime"
              onChange={(event) => updateFormState("sleepTime", event.target.value)}
              type="time"
              value={formState.sleepTime}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="workStart">
              <Briefcase className="h-4 w-4" />
              Work Start
            </label>
            <input
              className={fieldClassName}
              id="workStart"
              onChange={(event) => updateFormState("workStart", event.target.value)}
              type="time"
              value={formState.workStart}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="workEnd">
              Work End
            </label>
            <input
              className={fieldClassName}
              id="workEnd"
              onChange={(event) => updateFormState("workEnd", event.target.value)}
              type="time"
              value={formState.workEnd}
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="commitments">
            Recurring Commitments
          </label>
          <textarea
            className={textAreaClassName}
            id="commitments"
            onChange={(event) => updateFormState("recurringCommitments", event.target.value)}
            placeholder="e.g., Team standup Mon-Fri 9:30 AM, Gym Tue/Thu 6 PM..."
            rows={2}
            value={formState.recurringCommitments}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="focusWindow">
            Best Focus Window
          </label>
          <select
            className={fieldClassName}
            id="focusWindow"
            onChange={(event) => updateFormState("focusWindow", event.target.value)}
            value={formState.focusWindow}
          >
            <option value="early-morning">Early Morning (5 AM - 8 AM)</option>
            <option value="morning">Morning (8 AM - 12 PM)</option>
            <option value="afternoon">Afternoon (12 PM - 5 PM)</option>
            <option value="evening">Evening (5 PM - 9 PM)</option>
            <option value="night">Night (9 PM+)</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="weekendPattern">
            Weekend Pattern
          </label>
          <select
            className={fieldClassName}
            id="weekendPattern"
            onChange={(event) => updateFormState("weekendPattern", event.target.value)}
            value={formState.weekendPattern}
          >
            <option value="flexible">Flexible / No fixed schedule</option>
            <option value="similar">Similar to weekdays</option>
            <option value="rest">Full rest days</option>
            <option value="partial">Partial work (mornings only)</option>
          </select>
        </div>
      </div>
    );
  }

  function renderTasksStep() {
    return (
      <div className="mx-auto max-w-4xl space-y-6 remindr-onboarding-step-entry">
        <div className="mb-8 flex items-center justify-between gap-4">
          <h2 className="text-3xl text-white">Active Tasks</h2>
          <button
            className="flex items-center gap-2 rounded-lg border border-cyan-400/30 bg-cyan-500/20 px-4 py-2 text-cyan-100 transition-all duration-200 hover:border-cyan-400/50 hover:bg-cyan-500/30"
            onClick={addTask}
            type="button"
          >
            <Plus className="h-4 w-4" />
            <span>Add Task</span>
          </button>
        </div>

        {errors.tasks ? (
          <div className="flex items-center gap-2 rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <span>{errors.tasks}</span>
          </div>
        ) : null}

        {formState.tasks.length === 0 ? (
          <div className="rounded-xl border-2 border-dashed border-white/10 py-16 text-center">
            <ListTodo className="mx-auto mb-4 h-12 w-12 text-white/20" />
            <p className="text-white/40">No tasks yet. Add your first task to get started.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {formState.tasks.map((task) => (
              <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm" key={task.id}>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-xs uppercase tracking-[0.18em] text-cyan-100/60">Task Title</label>
                      <input
                        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-all duration-200 placeholder:text-white/30 focus:border-cyan-400/50 focus:outline-none"
                        onChange={(event) => updateTask(task.id, { title: event.target.value })}
                        placeholder="Task name"
                        type="text"
                        value={task.title}
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs uppercase tracking-[0.18em] text-cyan-100/60">Due Date</label>
                      <input
                        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-all duration-200 focus:border-cyan-400/50 focus:outline-none"
                        onChange={(event) => updateTask(task.id, { dueDate: event.target.value })}
                        type="date"
                        value={task.dueDate}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs uppercase tracking-[0.18em] text-cyan-100/60">Description</label>
                    <textarea
                      className="w-full resize-none rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-all duration-200 placeholder:text-white/30 focus:border-cyan-400/50 focus:outline-none"
                      onChange={(event) => updateTask(task.id, { description: event.target.value })}
                      placeholder="Task details..."
                      rows={2}
                      value={task.description}
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                    <div className="space-y-2">
                      <label className="text-xs uppercase tracking-[0.18em] text-cyan-100/60">Effort</label>
                      <select
                        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-all duration-200 focus:border-cyan-400/50 focus:outline-none"
                        onChange={(event) => updateTask(task.id, { effort: event.target.value })}
                        value={task.effort}
                      >
                        <option value="15-30 min">15-30 min</option>
                        <option value="30-60 min">30-60 min</option>
                        <option value="1-2 hours">1-2 hours</option>
                        <option value="2-4 hours">2-4 hours</option>
                        <option value="4+ hours">4+ hours</option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs uppercase tracking-[0.18em] text-cyan-100/60">Priority</label>
                      <select
                        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-all duration-200 focus:border-cyan-400/50 focus:outline-none"
                        onChange={(event) =>
                          updateTask(task.id, {
                            priority: event.target.value as OnboardingTask["priority"],
                          })
                        }
                        value={task.priority}
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs uppercase tracking-[0.18em] text-cyan-100/60">Energy</label>
                      <select
                        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-all duration-200 focus:border-cyan-400/50 focus:outline-none"
                        onChange={(event) =>
                          updateTask(task.id, {
                            energyLevel: event.target.value as OnboardingTask["energyLevel"],
                          })
                        }
                        value={task.energyLevel}
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs uppercase tracking-[0.18em] text-cyan-100/60">Time</label>
                      <select
                        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-all duration-200 focus:border-cyan-400/50 focus:outline-none"
                        onChange={(event) => updateTask(task.id, { preferredTime: event.target.value })}
                        value={task.preferredTime}
                      >
                        <option value="morning">Morning</option>
                        <option value="afternoon">Afternoon</option>
                        <option value="evening">Evening</option>
                        <option value="anytime">Anytime</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex flex-col justify-between gap-3 pt-2 sm:flex-row sm:items-center">
                    <label className="flex cursor-pointer items-center gap-2 text-sm text-cyan-100/70">
                      <input
                        checked={task.recurring}
                        className="h-4 w-4 rounded border-white/10 bg-white/5 text-cyan-500 focus:ring-cyan-500/50 focus:ring-offset-0"
                        onChange={(event) => updateTask(task.id, { recurring: event.target.checked })}
                        type="checkbox"
                      />
                      <span>Recurring task</span>
                    </label>

                    <button
                      className="flex items-center gap-2 self-start rounded-lg px-3 py-1.5 text-red-400/70 transition-all duration-200 hover:bg-red-500/10 hover:text-red-400 sm:self-auto"
                      onClick={() => removeTask(task.id)}
                      type="button"
                    >
                      <Trash2 className="h-4 w-4" />
                      <span>Remove</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  function renderPreferencesStep() {
    return (
      <div className="mx-auto max-w-2xl space-y-6 remindr-onboarding-step-entry">
        <h2 className="mb-8 text-3xl text-white">Preferences</h2>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="recommendationStyle">
            Recommendation Style
          </label>
          <select
            className={fieldClassName}
            id="recommendationStyle"
            onChange={(event) => updateFormState("recommendationStyle", event.target.value)}
            value={formState.recommendationStyle}
          >
            <option value="aggressive">Aggressive - Maximize productivity</option>
            <option value="balanced">Balanced - Sustainable pace</option>
            <option value="gentle">Gentle - Respect energy limits</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="reminderStyle">
            Reminder Style
          </label>
          <select
            className={fieldClassName}
            id="reminderStyle"
            onChange={(event) => updateFormState("reminderStyle", event.target.value)}
            value={formState.reminderStyle}
          >
            <option value="gentle">Gentle nudges</option>
            <option value="persistent">Persistent reminders</option>
            <option value="minimal">Minimal interruption</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="fatigueCheckIn">
            Fatigue Check-in
          </label>
          <select
            className={fieldClassName}
            id="fatigueCheckIn"
            onChange={(event) => updateFormState("fatigueCheckIn", event.target.value)}
            value={formState.fatigueCheckIn}
          >
            <option value="daily">Daily check-in</option>
            <option value="twice-daily">Twice daily</option>
            <option value="weekly">Weekly only</option>
            <option value="disabled">Disabled</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="notificationFrequency">
            Notification Frequency
          </label>
          <select
            className={fieldClassName}
            id="notificationFrequency"
            onChange={(event) => updateFormState("notificationFrequency", event.target.value)}
            value={formState.notificationFrequency}
          >
            <option value="high">High - All updates</option>
            <option value="moderate">Moderate - Important only</option>
            <option value="low">Low - Critical only</option>
          </select>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="quietHoursStart">
              Quiet Hours Start
            </label>
            <input
              className={fieldClassName}
              id="quietHoursStart"
              onChange={(event) => updateFormState("quietHoursStart", event.target.value)}
              type="time"
              value={formState.quietHoursStart}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm uppercase tracking-[0.18em] text-cyan-100/60" htmlFor="quietHoursEnd">
              Quiet Hours End
            </label>
            <input
              className={fieldClassName}
              id="quietHoursEnd"
              onChange={(event) => updateFormState("quietHoursEnd", event.target.value)}
              type="time"
              value={formState.quietHoursEnd}
            />
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/5 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-base text-white">Telegram connection</h3>
              <p className="mt-1 text-sm text-cyan-100/60">
                Chat stays in Telegram. The dashboard remains view-only.
              </p>
            </div>
            <button
              className={`rounded-full border px-4 py-2 text-sm transition-all duration-200 ${
                formState.telegramConnected
                  ? "border-cyan-400/50 bg-cyan-500/25 text-cyan-50"
                  : "border-white/15 bg-white/5 text-white/70 hover:border-white/25 hover:bg-white/10"
              }`}
              onClick={() => updateFormState("telegramConnected", !formState.telegramConnected)}
              type="button"
            >
              {formState.telegramConnected ? "Connected" : "Connect later"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  function renderReviewStep() {
    return (
      <div className="mx-auto max-w-3xl space-y-6 remindr-onboarding-step-entry">
        <h2 className="mb-8 text-3xl text-white">Review &amp; Confirm</h2>

        <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
          <div className="mb-4 flex items-center gap-3">
            <User className="h-5 w-5 text-cyan-400" />
            <h3 className="text-xl text-white">Profile</h3>
          </div>
          <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
            <div>
              <p className="mb-1 text-cyan-100/60">Name</p>
              <p className="text-white">{formState.fullName || "Not set"}</p>
            </div>
            <div>
              <p className="mb-1 text-cyan-100/60">Timezone</p>
              <p className="text-white">{formState.timezone}</p>
            </div>
            <div>
              <p className="mb-1 text-cyan-100/60">Role</p>
              <p className="text-white">{titleFromValue(formState.role)}</p>
            </div>
            {formState.bio ? (
              <div className="sm:col-span-2">
                <p className="mb-1 text-cyan-100/60">Bio</p>
                <p className="text-white/80">{formState.bio}</p>
              </div>
            ) : null}
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
          <div className="mb-4 flex items-center gap-3">
            <Clock className="h-5 w-5 text-cyan-400" />
            <h3 className="text-xl text-white">Daily Routine</h3>
          </div>
          <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
            <div>
              <p className="mb-1 text-cyan-100/60">Wake / Sleep</p>
              <p className="text-white">
                {formState.wakeTime} - {formState.sleepTime}
              </p>
            </div>
            <div>
              <p className="mb-1 text-cyan-100/60">Work Hours</p>
              <p className="text-white">
                {formState.workStart} - {formState.workEnd}
              </p>
            </div>
            <div>
              <p className="mb-1 text-cyan-100/60">Focus Window</p>
              <p className="text-white">{titleFromValue(formState.focusWindow)}</p>
            </div>
            <div>
              <p className="mb-1 text-cyan-100/60">Weekend Pattern</p>
              <p className="text-white">{titleFromValue(formState.weekendPattern)}</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
          <div className="mb-4 flex items-center gap-3">
            <ListTodo className="h-5 w-5 text-cyan-400" />
            <h3 className="text-xl text-white">Active Tasks</h3>
          </div>
          {formState.tasks.length === 0 ? (
            <p className="text-sm text-white/60">No tasks added yet</p>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-cyan-100/60">
                {formState.tasks.length} task{formState.tasks.length !== 1 ? "s" : ""} configured
              </p>
              {formState.tasks.slice(0, 3).map((task) => (
                <div className="rounded-lg bg-white/5 p-3 text-sm" key={task.id}>
                  <p className="mb-1 text-white">{task.title || "Untitled task"}</p>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-cyan-100/60">
                    <span>{titleFromValue(task.priority)} priority</span>
                    <span>{task.effort}</span>
                    {task.dueDate ? <span>Due: {task.dueDate}</span> : null}
                  </div>
                </div>
              ))}
              {formState.tasks.length > 3 ? (
                <p className="text-xs text-white/40">+{formState.tasks.length - 3} more tasks</p>
              ) : null}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
          <div className="mb-4 flex items-center gap-3">
            <Settings className="h-5 w-5 text-cyan-400" />
            <h3 className="text-xl text-white">Preferences</h3>
          </div>
          <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
            <div>
              <p className="mb-1 text-cyan-100/60">Recommendation Style</p>
              <p className="text-white">{titleFromValue(formState.recommendationStyle)}</p>
            </div>
            <div>
              <p className="mb-1 text-cyan-100/60">Reminder Style</p>
              <p className="text-white">{titleFromValue(formState.reminderStyle)}</p>
            </div>
            <div>
              <p className="mb-1 text-cyan-100/60">Notifications</p>
              <p className="text-white">{titleFromValue(formState.notificationFrequency)}</p>
            </div>
            <div>
              <p className="mb-1 text-cyan-100/60">Quiet Hours</p>
              <p className="text-white">
                {formState.quietHoursStart} - {formState.quietHoursEnd}
              </p>
            </div>
            <div className="sm:col-span-2">
              <p className="mb-1 text-cyan-100/60">Telegram</p>
              <p className="text-white">{formState.telegramConnected ? "Connected" : "Connect later"}</p>
            </div>
          </div>
        </div>

        <button
          className="flex w-full items-center justify-center gap-3 rounded-xl border border-cyan-400/40 bg-gradient-to-r from-cyan-500/30 to-teal-500/30 py-4 text-lg text-white transition-all duration-300 hover:border-cyan-400/60 hover:from-cyan-500/40 hover:to-teal-500/40 disabled:cursor-wait disabled:opacity-70"
          disabled={saveOnboardingMutation.isPending}
          onClick={() => void finishOnboarding()}
          type="button"
        >
          <CheckCircle2 className="h-5 w-5" />
          <span>{saveOnboardingMutation.isPending ? "Saving..." : "Continue to Connectors"}</span>
        </button>
      </div>
    );
  }

  function renderStepContent(step: StepId) {
    if (step === 0) return renderWelcomeStep();
    if (step === 1) return renderProfileStep();
    if (step === 2) return renderRoutineStep();
    if (step === 3) return renderTasksStep();
    if (step === 4) return renderPreferencesStep();
    return renderReviewStep();
  }

  return (
    <div className="relative h-screen min-h-screen overflow-hidden bg-gradient-to-b from-[#000810] via-[#001428] to-[#002040] text-white">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div
            className="absolute left-1/4 top-0 h-full w-96 -skew-x-12 bg-gradient-to-b from-cyan-400/20 to-transparent blur-3xl animate-pulse"
            style={{ animationDuration: "8s" }}
          />
          <div
            className="absolute right-1/3 top-0 h-full w-96 skew-x-12 bg-gradient-to-b from-teal-400/20 to-transparent blur-3xl animate-pulse"
            style={{ animationDelay: "2s", animationDuration: "10s" }}
          />
        </div>

        {particles.map((particle) => (
          <div
            className="remindr-onboarding-particle absolute h-1 w-1 rounded-full bg-cyan-300/30"
            key={particle.id}
            style={{
              animationDelay: `${particle.delay}s`,
              animationDuration: `${particle.duration}s`,
              left: particle.left,
              top: particle.top,
            }}
          />
        ))}
      </div>

      <div className="pointer-events-none fixed inset-0 z-0">
        <video
          autoPlay
          className="h-full w-full object-cover"
          loop
          muted
          playsInline
          style={{ filter: "brightness(0.5) contrast(1.1)" }}
        >
          <source
            src="https://res.cloudinary.com/djo4b8zll/video/upload/v1776581493/290328_medium_hrhzlg.mp4"
            type="video/mp4"
          />
        </video>
      </div>

      <div className="pointer-events-none fixed inset-0 z-[1] bg-black/40" />

      <div className="relative z-20 flex h-full w-full items-center justify-center px-4 py-4 sm:px-6 sm:py-6">
        <div className="h-full max-h-[calc(100vh-2rem)] w-full max-w-5xl sm:max-h-[calc(100vh-3rem)]">
          <div
            className="relative flex h-full flex-col overflow-hidden rounded-3xl border border-white/20 shadow-2xl"
            style={panelStyle}
          >
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-teal-500/5" />

            <div className="relative flex h-full flex-col">
              <div className="flex-shrink-0 px-5 pb-4 pt-6 sm:px-8 sm:pt-8">
                <h1 className="remindr-wordmark mb-6 text-2xl text-white">Remindr</h1>

                <div className="flex items-center justify-between gap-1 sm:gap-2">
                  {steps.map((step, index) => {
                    const StepIcon = step.icon;
                    const isComplete = index < currentStep;
                    const isCurrent = index === currentStep;

                    return (
                      <div className="flex items-center gap-1 sm:gap-2" key={step.id}>
                        <div className="flex flex-col items-center gap-1.5">
                          <div
                            className={`flex h-9 w-9 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                              isComplete
                                ? "border-cyan-400/60 bg-cyan-500/30 text-cyan-100"
                                : isCurrent
                                  ? "border-cyan-400/80 bg-cyan-500/20 text-cyan-100"
                                  : "border-white/20 bg-white/5 text-white/40"
                            }`}
                          >
                            {isComplete ? <CheckCircle2 className="h-4 w-4" /> : <StepIcon className="h-4 w-4" />}
                          </div>
                          <span
                            className={`text-[10px] transition-all duration-300 ${
                              index <= currentStep ? "text-cyan-100/80" : "text-white/40"
                            }`}
                          >
                            {step.name}
                          </span>
                        </div>
                        {index < steps.length - 1 ? (
                          <div
                            className={`mx-1 h-0.5 w-6 transition-all duration-300 sm:w-10 ${
                              index < currentStep ? "bg-cyan-400/40" : "bg-white/10"
                            }`}
                          />
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="remindr-scroll-shell flex-1 overflow-y-auto px-5 py-4 sm:px-8">
                <div key={currentStep}>{renderStepContent(currentStep)}</div>
              </div>

              {currentStep > 0 && currentStep < 5 ? (
                <div className="flex-shrink-0 border-t border-white/10 px-5 pb-6 pt-4 sm:px-8 sm:pb-8">
                  <div className="flex justify-between gap-4">
                    <button
                      className="rounded-xl border border-white/10 bg-white/5 px-6 py-2.5 text-white transition-all duration-200 hover:border-white/20 hover:bg-white/10"
                      onClick={prevStep}
                      type="button"
                    >
                      Back
                    </button>
                    <button
                      className="flex items-center gap-2 rounded-xl border border-cyan-400/30 bg-gradient-to-r from-cyan-500/20 to-teal-500/20 px-6 py-2.5 text-white transition-all duration-200 hover:border-cyan-400/50 hover:from-cyan-500/30 hover:to-teal-500/30"
                      onClick={nextStep}
                      type="button"
                    >
                      <span>Continue</span>
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
