import { type SyntheticEvent, useMemo, useState } from "react";
import {
  AlertCircle,
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  LogOut,
  Mail,
  MessageSquare,
  XCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useSaveIntegrationMutation } from "@/features/integrations/mutations";
import { useIntegrationsQuery } from "@/features/integrations/queries";
import { useAuthStore } from "@/stores/authStore";
import type { Integration } from "@/types/domain";

type ConnectorId = "gmail" | "outlook" | "calendar";
type TaskType = "event" | "deadline" | "task";
type TaskSource = "telegram" | "gmail" | "outlook" | "calendar";
type TaskStatus = "upcoming" | "completed";

interface ConfirmedTaskItem {
  id: number;
  title: string;
  date?: string;
  time: string;
  type: TaskType;
  source: TaskSource;
  status: TaskStatus;
}

interface SuggestionItem {
  id: number;
  text: string;
  timing: string;
  type: "energy" | "recovery" | "deadline";
}

interface ParticleSpec {
  id: string;
  left: string;
  top: string;
  delay: string;
  duration: string;
}

const confirmedTasks: {
  today: ConfirmedTaskItem[];
  upcoming: ConfirmedTaskItem[];
  later: ConfirmedTaskItem[];
} = {
  today: [
    {
      id: 1,
      title: "Product Strategy Review",
      time: "09:00 AM",
      type: "event",
      source: "calendar",
      status: "upcoming",
    },
    {
      id: 2,
      title: "Complete Q2 Report",
      time: "02:00 PM",
      type: "task",
      source: "telegram",
      status: "upcoming",
    },
    {
      id: 3,
      title: "Review design mockups",
      time: "04:30 PM",
      type: "task",
      source: "gmail",
      status: "completed",
    },
  ],
  upcoming: [
    {
      id: 4,
      title: "Design System Sprint",
      date: "Tue, Apr 16",
      time: "10:30 AM",
      type: "event",
      source: "calendar",
      status: "upcoming",
    },
    {
      id: 5,
      title: "API Documentation Deadline",
      date: "Tue, Apr 16",
      time: "04:00 PM",
      type: "deadline",
      source: "outlook",
      status: "upcoming",
    },
    {
      id: 6,
      title: "Investor Presentation",
      date: "Wed, Apr 17",
      time: "11:00 AM",
      type: "event",
      source: "calendar",
      status: "upcoming",
    },
  ],
  later: [
    {
      id: 7,
      title: "Client Demo - Beta Release",
      date: "Thu, Apr 18",
      time: "10:00 AM",
      type: "event",
      source: "calendar",
      status: "upcoming",
    },
    {
      id: 8,
      title: "Security Audit Review",
      date: "Fri, Apr 19",
      time: "02:30 PM",
      type: "deadline",
      source: "gmail",
      status: "upcoming",
    },
  ],
};

const baseSuggestions: SuggestionItem[] = [
  {
    id: 1,
    text: "Move code review to tomorrow morning during your peak focus window",
    timing: "Tomorrow, 9:00 AM",
    type: "energy",
  },
  {
    id: 2,
    text: "Schedule 30min recovery after client demo on Thursday",
    timing: "Thursday, 11:30 AM",
    type: "recovery",
  },
  {
    id: 3,
    text: "Block prep time for security audit on Thursday afternoon",
    timing: "Thursday, 3:00 PM",
    type: "deadline",
  },
];

function buildFallbackIntegration(id: ConnectorId): Integration {
  return {
    id,
    provider: id === "calendar" ? "Calendar" : id === "gmail" ? "Gmail" : "Outlook",
    status: "Not connected",
    lastSync: "Not linked",
    description: "Connector is available but not linked yet.",
    permissions: [],
  };
}

function getSourceIcon(source: TaskSource) {
  switch (source) {
    case "telegram":
      return <MessageSquare className="h-3 w-3" />;
    case "gmail":
    case "outlook":
      return <Mail className="h-3 w-3" />;
    case "calendar":
      return <Calendar className="h-3 w-3" />;
    default:
      return <Clock className="h-3 w-3" />;
  }
}

function getTypeBadgeColor(type: TaskType) {
  switch (type) {
    case "event":
      return "bg-cyan-400/20 text-cyan-300 border-cyan-400/30";
    case "deadline":
      return "bg-red-400/20 text-red-300 border-red-400/30";
    case "task":
      return "bg-teal-400/20 text-teal-300 border-teal-400/30";
    default:
      return "bg-white/10 text-cyan-100 border-white/20";
  }
}

export function DashboardPage() {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const { data: integrations = [] } = useIntegrationsQuery();
  const saveIntegrationMutation = useSaveIntegrationMutation();
  const [acceptedSuggestionIds, setAcceptedSuggestionIds] = useState<number[]>([]);
  const [dismissedSuggestionIds, setDismissedSuggestionIds] = useState<number[]>([]);
  const [pendingConnectorId, setPendingConnectorId] = useState<ConnectorId | null>(null);

  const particles = useMemo<ParticleSpec[]>(
    () =>
      Array.from({ length: 25 }, (_, index) => ({
        id: `dashboard-particle-${index}`,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        delay: `${Math.random() * 2}s`,
        duration: `${3 + Math.random() * 4}s`,
      })),
    [],
  );

  const integrationMap = useMemo(
    () => new Map(integrations.map((integration) => [integration.id, integration])),
    [integrations],
  );

  const telegramIntegration =
    (integrationMap.get("telegram") as Integration | undefined) ?? {
      id: "telegram",
      provider: "Telegram",
      status: "Not connected",
      lastSync: "Not linked",
      description: "Conversation channel is waiting for setup.",
      permissions: [],
    };

  const connectorIntegrations = (["gmail", "outlook", "calendar"] as const).map(
    (connectorId) =>
      (integrationMap.get(connectorId) as Integration | undefined) ?? buildFallbackIntegration(connectorId),
  );

  const connectors = {
    gmail: connectorIntegrations.find((integration) => integration.id === "gmail")?.status === "Connected",
    outlook: connectorIntegrations.find((integration) => integration.id === "outlook")?.status === "Connected",
    calendar: connectorIntegrations.find((integration) => integration.id === "calendar")?.status === "Connected",
  };

  const telegramActive = telegramIntegration.status === "Connected";

  const suggestions = baseSuggestions.filter((item) => !dismissedSuggestionIds.includes(item.id));

  function handleVideoLoad(event: SyntheticEvent<HTMLVideoElement>) {
    const video = event.currentTarget;
    video.playbackRate = 0.5;
  }

  async function handleConnectorAction(connectorId: ConnectorId) {
    const integration =
      connectorIntegrations.find((entry) => entry.id === connectorId) ?? buildFallbackIntegration(connectorId);

    if (pendingConnectorId) return;
    if (connectorId === "calendar" && integration.status !== "Connected") {
      navigate("/integrations/google-calendar");
      return;
    }

    setPendingConnectorId(connectorId);

    try {
      await saveIntegrationMutation.mutateAsync({
        ...integration,
        status: integration.status === "Connected" ? "Not connected" : "Connected",
        lastSync: integration.status === "Connected" ? "Not linked" : "Just now",
      });
    } finally {
      setPendingConnectorId(null);
    }
  }

  function handleAcceptSuggestion(id: number) {
    setAcceptedSuggestionIds((current) => (current.includes(id) ? current : [...current, id]));
  }

  function handleDismissSuggestion(id: number) {
    setDismissedSuggestionIds((current) => (current.includes(id) ? current : [...current, id]));
  }

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#0a0e1a]">
      <div className="fixed inset-0">
        <video
          autoPlay
          className="absolute inset-0 h-full w-full object-cover opacity-25"
          loop
          muted
          onLoadedData={handleVideoLoad}
          playsInline
        >
          <source
            src="https://res.cloudinary.com/djo4b8zll/video/upload/v1776633961/67433-522170592_medium_ta41qr.mp4"
            type="video/mp4"
          />
        </video>

        <div className="absolute inset-0 opacity-15">
          <div className="absolute left-1/4 top-0 h-96 w-96 rounded-full bg-cyan-500/20 blur-[120px]" />
          <div className="absolute right-1/4 top-1/3 h-[500px] w-[500px] rounded-full bg-teal-400/10 blur-[150px]" />
          <div className="absolute bottom-0 left-1/2 h-96 w-96 rounded-full bg-blue-500/15 blur-[140px]" />
        </div>

        <div className="absolute inset-0 bg-[#0a0e1a]/50" />
      </div>

      <div className="pointer-events-none fixed inset-0 z-[1]">
        {particles.map((particle) => (
          <span
            className="remindr-dashboard-particle absolute h-1 w-1 rounded-full bg-cyan-300/30"
            key={particle.id}
            style={{
              animationDelay: particle.delay,
              animationDuration: particle.duration,
              left: particle.left,
              top: particle.top,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 grid h-full grid-rows-[auto_minmax(0,1fr)]">
        <header className="relative flex shrink-0 justify-center pb-6 pt-10">
          <div className="relative">
            <h1 className="remindr-wordmark bg-gradient-to-r from-cyan-200 via-teal-100 to-cyan-200 bg-clip-text text-7xl tracking-[0.35em] text-transparent">
              Remindr
            </h1>
            <div className="absolute -inset-6 -z-10 rounded-full bg-cyan-400/5 blur-2xl" />
          </div>

          <button
            className="absolute right-16 top-10 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-sm text-cyan-100 transition-all hover:border-cyan-400/30 hover:bg-white/[0.08]"
            onClick={handleLogout}
            type="button"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </header>

        <div className="min-h-0 px-16 pb-6">
          <div className="mx-auto grid h-full max-w-[1800px] grid-cols-3 gap-8">
            <div className="col-span-2 grid min-h-0 h-full grid-rows-[minmax(0,1fr)_auto] gap-6">
              <div className="relative min-h-0 overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.03] shadow-2xl backdrop-blur-xl">
                <div className="absolute inset-0 rounded-3xl shadow-[inset_0_1px_2px_rgba(255,255,255,0.1)]" />

                <div className="relative flex h-full min-h-0 flex-col p-8">
                  <div className="mb-6 shrink-0">
                    <h2 className="mb-2 text-3xl tracking-wide text-cyan-50">Confirmed Work</h2>
                    <p className="text-sm tracking-wide text-cyan-300/60">
                      All confirmed tasks, deadlines, and commitments
                    </p>
                  </div>

                  <div className="grid min-h-0 flex-1 grid-cols-3 gap-4">
                    <TaskGroup heading="Today" subheading="Mon, Apr 15" tasks={confirmedTasks.today} />
                    <TaskGroup heading="Upcoming" subheading="Next confirmed" tasks={confirmedTasks.upcoming} />
                    <TaskGroup heading="Later This Week" subheading="Queued next" tasks={confirmedTasks.later} />
                  </div>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.03] shadow-xl backdrop-blur-xl">
                <div className="absolute inset-0 rounded-2xl shadow-[inset_0_1px_2px_rgba(255,255,255,0.1)]" />

                <div className="relative p-4">
                  <h3 className="mb-3 text-xs uppercase tracking-[0.22em] text-cyan-200/75">
                    Fatigue · Stress Bar
                  </h3>

                  <div className="mb-2 flex justify-between px-2 text-[11px] text-cyan-300/50">
                    <span>6 AM</span>
                    <span>9 AM</span>
                    <span>12 PM</span>
                    <span>3 PM</span>
                    <span>6 PM</span>
                    <span>9 PM</span>
                  </div>

                  <div className="relative h-14 overflow-hidden rounded-2xl border border-white/10 shadow-inner">
                    <div className="absolute inset-0 flex">
                      <div className="w-[12.5%] bg-gradient-to-r from-cyan-400/20 to-teal-400/25" />
                      <div className="w-[12.5%] bg-gradient-to-r from-teal-400/25 to-green-400/40" />
                      <div className="w-[12.5%] bg-gradient-to-r from-green-400/40 to-emerald-400/45" />
                      <div className="w-[12.5%] bg-gradient-to-r from-emerald-400/45 to-green-400/40" />
                      <div className="w-[12.5%] bg-gradient-to-r from-green-400/40 to-yellow-400/30" />
                      <div className="w-[12.5%] bg-gradient-to-r from-yellow-400/30 to-orange-400/35" />
                      <div className="w-[12.5%] bg-gradient-to-r from-orange-400/35 to-red-400/45" />
                      <div className="w-[12.5%] bg-gradient-to-r from-red-400/45 to-red-400/50" />
                    </div>

                    <div className="absolute inset-y-1.5 left-[12.5%] w-[25%] rounded-xl border border-green-400/50" />
                    <div className="absolute inset-y-1.5 left-[62.5%] w-[25%] rounded-xl border border-red-400/50" />
                    <div className="absolute inset-y-1.5 right-[4%] w-[10%] rounded-xl border border-purple-400/45" />
                  </div>
                </div>
              </div>
            </div>

            <div className="col-span-1 min-h-0">
              <div className="flex h-full min-h-0 flex-col gap-6 pr-2">
                <div className="relative shrink-0 overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.03] shadow-xl backdrop-blur-xl">
                  <div className="absolute inset-0 rounded-2xl shadow-[inset_0_1px_2px_rgba(255,255,255,0.1)]" />

                  <div className="relative p-6">
                    <div className="mb-4 flex items-start justify-between">
                      <div>
                        <h3 className="mb-1 text-lg tracking-wide text-cyan-50">Telegram</h3>
                        <p className="text-xs text-cyan-300/60">Conversation channel</p>
                      </div>
                      <div className="relative">
                        <MessageSquare className="h-6 w-6 text-cyan-300" />
                        {telegramActive ? (
                          <div className="absolute -right-1 -top-1 h-3 w-3 rounded-full border-2 border-[#0a0e1a] bg-green-400 shadow-lg shadow-green-400/50" />
                        ) : null}
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div
                        className={`rounded-lg border px-4 py-2.5 text-sm ${
                          telegramActive
                            ? "border-green-400/30 bg-green-400/10 text-green-300"
                            : "border-red-400/30 bg-red-400/10 text-red-300"
                        }`}
                      >
                        {telegramActive ? "Active" : "Disconnected"}
                      </div>

                      {telegramActive ? <p className="text-xs text-cyan-300/50">{telegramIntegration.lastSync}</p> : null}

                      <button
                        className="w-full rounded-lg border border-white/10 bg-white/[0.05] px-4 py-2.5 text-sm text-cyan-100 transition-all hover:border-cyan-400/30 hover:bg-white/[0.08]"
                        onClick={() => navigate("/channel")}
                        type="button"
                      >
                        Manage
                      </button>
                    </div>
                  </div>
                </div>

                <div className="relative shrink-0 overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.03] shadow-xl backdrop-blur-xl">
                  <div className="absolute inset-0 rounded-2xl shadow-[inset_0_1px_2px_rgba(255,255,255,0.1)]" />

                  <div className="relative p-6">
                    <h3 className="mb-5 text-lg tracking-wide text-cyan-50">Connectors</h3>

                    <div className="space-y-3">
                      {connectorIntegrations.map((integration) => {
                        const isConnected = integration.status === "Connected";
                        const isPending = pendingConnectorId === integration.id;

                        return (
                          <div
                            className={`rounded-lg border p-4 transition-all ${
                              isConnected
                                ? "border-cyan-400/30 bg-cyan-400/5"
                                : integration.id === "calendar"
                                  ? "border-red-400/30 bg-red-400/5"
                                  : "border-white/10 bg-white/[0.03]"
                            }`}
                            key={integration.id}
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="flex items-center gap-3">
                                {integration.id === "calendar" ? (
                                  <Calendar className="h-5 w-5 text-cyan-300" />
                                ) : (
                                  <Mail className="h-5 w-5 text-cyan-300" />
                                )}
                                <span className="text-sm text-cyan-100">{integration.provider}</span>
                              </div>

                              {integration.id === "calendar" && !connectors.calendar ? (
                                <XCircle className="h-5 w-5 text-red-400" />
                              ) : isConnected ? (
                                <CheckCircle2 className="h-5 w-5 text-green-400" />
                              ) : (
                                <AlertCircle className="h-5 w-5 text-red-400" />
                              )}
                            </div>

                            <button
                              className="mt-3 w-full rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-xs text-cyan-100 transition-all hover:border-cyan-400/30 hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={Boolean(pendingConnectorId)}
                              onClick={() => void handleConnectorAction(integration.id as ConnectorId)}
                              type="button"
                            >
                              {isPending ? "Working..." : isConnected ? "Disconnect" : "Connect"}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div className="relative min-h-0 flex-1 overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.03] shadow-xl backdrop-blur-xl">
                  <div className="absolute inset-0 rounded-2xl shadow-[inset_0_1px_2px_rgba(255,255,255,0.1)]" />

                  <div className="relative flex h-full min-h-0 flex-col p-6">
                    <h3 className="mb-5 shrink-0 text-lg tracking-wide text-cyan-50">Suggestions</h3>

                    <div className="remindr-scroll-shell min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
                      {suggestions.map((suggestion) => {
                        const accepted = acceptedSuggestionIds.includes(suggestion.id);

                        return (
                          <div
                            className="group rounded-lg border border-white/10 bg-white/[0.03] p-4 transition-all hover:border-cyan-400/30"
                            key={suggestion.id}
                          >
                            <div className="mb-3">
                              <p className="mb-2 text-sm leading-relaxed text-cyan-100">{suggestion.text}</p>
                              <p className="flex items-center gap-1.5 text-xs text-cyan-300/50">
                                <Clock className="h-3 w-3" />
                                {suggestion.timing}
                              </p>
                            </div>

                            <div className="flex gap-2">
                              <button
                                className="flex-1 rounded-lg px-3 py-2 text-xs text-cyan-300/70 transition-colors hover:bg-white/[0.05]"
                                onClick={() => handleDismissSuggestion(suggestion.id)}
                                type="button"
                              >
                                Dismiss
                              </button>
                              <button
                                className="flex-1 rounded-lg border border-cyan-400/30 bg-cyan-400/20 px-3 py-2 text-xs text-cyan-50 transition-colors hover:bg-cyan-400/30"
                                onClick={() => handleAcceptSuggestion(suggestion.id)}
                                type="button"
                              >
                                {accepted ? "Accepted" : "Accept"}
                              </button>
                            </div>
                          </div>
                        );
                      })}

                      {!suggestions.length ? (
                        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-4 py-5 text-sm text-cyan-100/60">
                          No suggestions right now.
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

function TaskGroup({
  heading,
  subheading,
  tasks,
}: {
  heading: string;
  subheading: string;
  tasks: ConfirmedTaskItem[];
}) {
  return (
    <div className="flex h-full min-h-0 flex-col rounded-2xl border border-white/10 bg-black/10 p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs uppercase tracking-[0.2em] text-cyan-300/70">{heading}</h3>
          <p className="mt-1 text-[11px] tracking-wide text-cyan-100/45">{subheading}</p>
        </div>
        <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] text-cyan-100/65">
          {tasks.length}
        </span>
      </div>

      <div className="remindr-scroll-shell min-h-0 flex-1 space-y-2.5 overflow-y-auto pr-1">
        {tasks.map((task) => (
          <div
            className={`group relative rounded-xl border p-3 transition-all ${
              task.status === "completed"
                ? "border-teal-400/20 bg-teal-400/5"
                : "border-white/10 bg-white/[0.03] hover:border-cyan-400/30 hover:bg-white/[0.06]"
            }`}
            key={task.id}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="mb-2 flex items-start gap-2">
                  <h4
                    className={`text-sm leading-5 ${
                      task.status === "completed" ? "text-cyan-100/60 line-through" : "text-cyan-50"
                    }`}
                  >
                    {task.title}
                  </h4>
                  {task.status === "completed" ? <Check className="h-4 w-4 text-teal-400" /> : null}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="flex items-center gap-1.5 text-[11px] text-cyan-300/70">
                    <Clock className="h-3 w-3" />
                    {task.date ? `${task.date} · ${task.time}` : task.time}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] ${getTypeBadgeColor(task.type)}`}>
                    {task.type}
                  </span>
                  <span className="flex items-center gap-1 text-[10px] uppercase tracking-[0.18em] text-cyan-300/50">
                    {getSourceIcon(task.source)}
                    {task.source}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
