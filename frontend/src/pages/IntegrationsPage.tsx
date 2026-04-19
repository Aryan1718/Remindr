import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { startGoogleCalendarOAuth } from "@/api/integrations";
import { useSaveIntegrationMutation } from "@/features/integrations/mutations";
import { useSaveOnboardingMutation } from "@/features/onboarding/mutations";
import { useOnboardingQuery } from "@/features/onboarding/queries";
import { useIntegrationsQuery } from "@/features/integrations/queries";
import type { Integration, OnboardingDraft } from "@/types/domain";

type ConnectorId = "gmail" | "outlook" | "calendar";
type ConnectorStatus = "disconnected" | "connected" | "syncing";

interface JellyfishConnectorDefinition {
  id: ConnectorId;
  name: string;
  description: string;
  accentColor: string;
  glowColor: string;
  positionClassName: string;
  driftClassName: string;
  buttonShadow: string;
  lastSyncLabel: string;
}

interface ParticleSpec {
  id: string;
  left: string;
  top: string;
  delay: string;
  duration: string;
  size: number;
}

const connectorDefinitions: JellyfishConnectorDefinition[] = [
  {
    id: "gmail",
    name: "Gmail",
    description: "Sync important email-based commitments and follow-up signals.",
    accentColor: "rgb(234, 67, 53)",
    glowColor: "rgba(234, 67, 53, 0.34)",
    positionClassName: "lg:left-[4%] lg:top-[9%]",
    driftClassName: "remindr-jellyfish-drift-a",
    buttonShadow: "0 10px 34px rgba(234, 67, 53, 0.28)",
    lastSyncLabel: "Email commitments",
  },
  {
    id: "outlook",
    name: "Outlook",
    description: "Connect work communication and scheduling context from Microsoft accounts.",
    accentColor: "rgb(0, 120, 212)",
    glowColor: "rgba(0, 120, 212, 0.34)",
    positionClassName: "lg:left-[37%] lg:top-[3%]",
    driftClassName: "remindr-jellyfish-drift-b",
    buttonShadow: "0 10px 34px rgba(0, 120, 212, 0.28)",
    lastSyncLabel: "Work context",
  },
  {
    id: "calendar",
    name: "Calendar",
    description: "Import confirmed events, meetings, and dates into the planning surface.",
    accentColor: "rgb(20, 184, 166)",
    glowColor: "rgba(20, 184, 166, 0.38)",
    positionClassName: "lg:left-[69%] lg:top-[11%]",
    driftClassName: "remindr-jellyfish-drift-c",
    buttonShadow: "0 10px 34px rgba(20, 184, 166, 0.28)",
    lastSyncLabel: "Confirmed events",
  },
];

function createFallbackIntegration(definition: JellyfishConnectorDefinition): Integration {
  return {
    id: definition.id,
    provider: definition.name,
    status: "Not connected",
    lastSync: "Not linked",
    description: definition.description,
    permissions: [],
  };
}

function normalizeConnectorStatus(isConnected: boolean, isSyncing: boolean): ConnectorStatus {
  if (isSyncing) return "syncing";
  return isConnected ? "connected" : "disconnected";
}

export function IntegrationsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const { data = [] } = useIntegrationsQuery();
  const { data: onboardingDraft } = useOnboardingQuery();
  const saveMutation = useSaveIntegrationMutation();
  const saveOnboardingMutation = useSaveOnboardingMutation();
  const [syncingIds, setSyncingIds] = useState<ConnectorId[]>([]);
  const [connectedIds, setConnectedIds] = useState<ConnectorId[]>([]);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const timeoutIds = useRef<number[]>([]);
  const callbackStatus = search.get("status");
  const callbackConnectorId = search.get("connector_id");
  const callbackJobStatus = search.get("job_status");
  const callbackReason = search.get("reason");

  const particles = useMemo<ParticleSpec[]>(
    () =>
      Array.from({ length: 20 }, (_, index) => ({
        id: `connector-particle-${index}`,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        delay: `${Math.random() * 10}s`,
        duration: `${18 + Math.random() * 12}s`,
        size: Math.round(2 + Math.random() * 3),
      })),
    [],
  );

  const connectorMap = useMemo(() => new Map(data.map((integration) => [integration.id, integration])), [data]);

  const connectors = useMemo(
    () =>
      connectorDefinitions.map((definition) => {
        const integration = (connectorMap.get(definition.id) as Integration | undefined) ?? createFallbackIntegration(definition);
        const isConnected = connectedIds.includes(definition.id);
        return {
          ...definition,
          integration,
          status: normalizeConnectorStatus(isConnected, syncingIds.includes(definition.id)),
        };
      }),
    [connectedIds, connectorMap, syncingIds],
  );

  useEffect(() => {
    return () => {
      timeoutIds.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
    };
  }, []);

  useEffect(() => {
    if (!onboardingDraft || onboardingDraft.stage !== "connectors") return;
    setConnectedIds([]);
  }, [onboardingDraft?.stage]);

  useEffect(() => {
    if (callbackStatus !== "success") {
      return;
    }
    setConnectedIds((current) => (current.includes("calendar") ? current : [...current, "calendar"]));
  }, [callbackStatus]);

  function dismissCallbackBanner() {
    const next = new URLSearchParams(search);
    next.delete("status");
    next.delete("connector_id");
    next.delete("job_status");
    next.delete("reason");
    setSearch(next, { replace: true });
  }

  function queueConnectorDraftUpdate(nextConnectorIds: ConnectorId[]) {
    if (!onboardingDraft) return;

    void saveOnboardingMutation.mutateAsync({
      ...onboardingDraft,
      stage: "connectors",
      completed: false,
      connectors: nextConnectorIds,
    });
  }

  async function handleConnect(connectorId: ConnectorId) {
    const connector = connectors.find((entry) => entry.id === connectorId);
    if (!connector || connector.status !== "disconnected") return;
    if (connectorId === "calendar") {
      setSyncingIds((current) => [...current, connectorId]);
      try {
        const authorizationUrl = await startGoogleCalendarOAuth();
        window.location.assign(authorizationUrl);
        return;
      } catch {
        setSyncingIds((current) => current.filter((entry) => entry !== connectorId));
        navigate("/integrations/google-calendar");
        return;
      }
    }

    if (syncingIds.includes(connectorId)) {
      return;
    }

    setSyncingIds((current) => [...current, connectorId]);
    const nextConnectedIds = Array.from(new Set([...connectedIds, connectorId])) as ConnectorId[];

    const timeoutId = window.setTimeout(() => {
      setConnectedIds(nextConnectedIds);
      void saveMutation
        .mutateAsync({
          ...connector.integration,
          provider: connector.name,
          description: connector.description,
          status: "Connected",
          lastSync: "Just now",
        })
        .then(() => {
          queueConnectorDraftUpdate(nextConnectedIds);
        })
        .finally(() => {
          setSyncingIds((current) => current.filter((entry) => entry !== connectorId));
        });
    }, 1700);

    timeoutIds.current.push(timeoutId);
  }

  async function completeConnectorStep() {
    setIsFinalizing(true);

    try {
      if (onboardingDraft) {
        await saveOnboardingMutation.mutateAsync({
          ...onboardingDraft,
          stage: "channel",
          completed: false,
          connectors: connectedIds,
        });
      }

      navigate("/channel");
    } finally {
      setIsFinalizing(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-white">
      <video
        autoPlay
        className="absolute inset-0 h-full w-full object-cover opacity-60"
        loop
        muted
        playsInline
      >
        <source
          src="https://res.cloudinary.com/djo4b8zll/video/upload/v1776586889/137572-766938284_medium_s4c0oh.mp4"
          type="video/mp4"
        />
      </video>

      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/40 via-slate-950/30 to-black/65" />

      <div className="pointer-events-none absolute inset-0">
        {particles.map((particle) => (
          <div
            className="remindr-connector-particle absolute rounded-full bg-cyan-300/30"
            key={particle.id}
            style={{
              animationDelay: particle.delay,
              animationDuration: particle.duration,
              height: `${particle.size}px`,
              left: particle.left,
              top: particle.top,
              width: `${particle.size}px`,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 flex min-h-screen flex-col px-6 pb-12 pt-10 sm:px-8 lg:px-10">
        <header className="mx-auto w-full max-w-7xl remindr-connector-page-entry">
          <p className="remindr-wordmark text-3xl text-cyan-100/90 sm:text-4xl">Remindr</p>
        </header>

        <main className="flex flex-1 flex-col items-center pt-10 sm:pt-14">
          {callbackStatus ? (
            <div className="remindr-connector-page-entry mx-auto mb-8 w-full max-w-3xl" style={{ animationDelay: "0.08s" }}>
              <div
                className={`rounded-3xl border px-5 py-4 text-left backdrop-blur ${
                  callbackStatus === "success"
                    ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-50"
                    : "border-amber-400/30 bg-amber-500/10 text-amber-50"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] opacity-80">
                      {callbackStatus === "success" ? "Calendar connected" : "Connection needs review"}
                    </p>
                    <p className="mt-2 text-sm leading-7">
                      {callbackStatus === "success"
                        ? `Google Calendar connected successfully${callbackJobStatus ? ` and sync ${callbackJobStatus}` : ""}.`
                        : callbackReason || "Google Calendar authorization could not be completed."}
                    </p>
                    {callbackConnectorId ? (
                      <p className="mt-2 text-xs uppercase tracking-[0.18em] opacity-70">Connector {callbackConnectorId}</p>
                    ) : null}
                  </div>
                  <button
                    className="rounded-full border border-white/15 px-3 py-1 text-xs uppercase tracking-[0.18em] text-white/80 transition hover:border-white/30 hover:text-white"
                    onClick={dismissCallbackBanner}
                    type="button"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          <div className="remindr-connector-page-entry mx-auto max-w-3xl text-center" style={{ animationDelay: "0.12s" }}>
            <h1 className="text-4xl font-semibold text-white sm:text-5xl lg:text-6xl">
              Connect your services
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-sm leading-7 text-cyan-100/72 sm:text-base sm:leading-8">
              Link the tools Remindr should watch before you enter the dashboard. These connectors
              are limited to confirmed schedule and communication context only.
            </p>
          </div>

          <div className="relative mx-auto mt-12 w-full max-w-7xl lg:h-[38rem]">
            <div className="grid gap-10 lg:block">
              {connectors.map((connector, index) => (
                <JellyfishCard
                  connector={connector}
                  key={connector.id}
                  onConnect={handleConnect}
                  style={{ animationDelay: `${0.28 + index * 0.14}s` }}
                />
              ))}
            </div>
          </div>
        </main>

        <footer className="mx-auto mt-8 flex w-full max-w-7xl flex-col items-center justify-center gap-4 sm:flex-row sm:gap-6">
          <button
            className="rounded-full bg-cyan-500/90 px-10 py-4 text-sm font-medium text-white transition-all duration-300 hover:bg-cyan-400 hover:shadow-[0_20px_48px_rgba(34,211,238,0.28)] disabled:cursor-wait disabled:opacity-70"
            disabled={isFinalizing}
            onClick={() => void completeConnectorStep()}
            type="button"
          >
            {isFinalizing ? "Opening channel..." : "Continue to channel"}
          </button>
          <button
            className="px-8 py-4 text-sm text-cyan-100/60 transition-colors duration-300 hover:text-cyan-100/90"
            disabled={isFinalizing}
            onClick={() => void completeConnectorStep()}
            type="button"
          >
            Skip for now
          </button>
        </footer>
      </div>
    </div>
  );
}

function JellyfishCard({
  connector,
  onConnect,
  style,
}: {
  connector: JellyfishConnectorDefinition & { integration: Integration; status: ConnectorStatus };
  onConnect: (id: ConnectorId) => void;
  style?: React.CSSProperties;
}) {
  const isBusy = connector.status === "syncing";
  const isConnected = connector.status === "connected";
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className={`remindr-connector-card-entry relative mx-auto w-full max-w-[18rem] lg:absolute ${connector.positionClassName}`}
      style={style}
    >
      <div
        className={`relative ${connector.driftClassName}`}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div
          className={`absolute inset-x-5 top-4 h-44 rounded-full blur-3xl transition-all duration-500 ${
            isConnected ? "remindr-jellyfish-connected-glow" : ""
          }`}
          style={{
            backgroundColor: connector.glowColor,
            opacity: isConnected ? 1 : isHovered ? 0.82 : 0.52,
            transform: `scale(${isConnected ? 1.32 : isHovered ? 1.1 : 1})`,
          }}
        />

        <div
          className="pointer-events-none absolute inset-x-8 top-7 h-36 rounded-full blur-[72px] transition-all duration-500"
          style={{
            background: `radial-gradient(circle, ${connector.glowColor} 0%, transparent 72%)`,
            opacity: isConnected ? 1 : isHovered ? 0.62 : 0.24,
            transform: `scale(${isConnected ? 1.24 : isHovered ? 1.08 : 0.96})`,
          }}
        />

        <div className="relative mx-auto w-[18rem] pt-4">
          <div
            className="remindr-jellyfish-bell group relative mx-auto flex h-[19rem] w-[18rem] flex-col items-center justify-center overflow-hidden rounded-[42%_42%_48%_48%/35%_35%_60%_60%] border border-white/15 px-7 pb-14 pt-7 text-center shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur-2xl transition-transform duration-300 hover:scale-[1.02]"
            style={{
              background: isConnected
                ? `linear-gradient(180deg, ${connector.glowColor} 0%, rgba(255,255,255,0.08) 46%, rgba(255,255,255,0.04) 100%)`
                : "linear-gradient(180deg, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.06) 46%, rgba(255,255,255,0.03) 100%)",
              boxShadow: isConnected
                ? `0 0 0 1px rgba(255,255,255,0.08), 0 0 110px ${connector.glowColor}, inset 0 0 58px ${connector.glowColor}`
                : isHovered
                  ? `0 0 0 1px rgba(255,255,255,0.08), 0 0 46px ${connector.glowColor}, inset 0 0 24px rgba(255,255,255,0.06)`
                  : "0 0 0 1px rgba(255,255,255,0.04)",
              transform: `scale(${isConnected ? 1.05 : isHovered ? 1.03 : 1})`,
            }}
          >
            <div
              className="pointer-events-none absolute inset-x-10 top-6 h-16 rounded-full blur-2xl transition-all duration-500"
              style={{
                background: `radial-gradient(circle, ${connector.glowColor} 0%, transparent 68%)`,
                opacity: isConnected ? 1 : isHovered ? 0.8 : 0.45,
                transform: `scale(${isConnected ? 1.16 : isHovered ? 1.08 : 1})`,
              }}
            />

            <h3
              className="text-3xl font-semibold text-white transition-transform duration-500"
              style={{ transform: `scale(${isConnected ? 1.04 : isHovered ? 1.02 : 1})` }}
            >
              {connector.name}
            </h3>

            <button
              className="mt-7 flex min-w-[10rem] items-center justify-center gap-2 rounded-full border border-white/10 px-6 py-3 text-sm font-medium text-white transition-transform duration-300 hover:scale-[1.03] disabled:cursor-wait disabled:scale-100 disabled:opacity-75"
              disabled={isBusy || isConnected}
              onClick={() => onConnect(connector.id)}
              style={{
                backgroundColor: isConnected ? "rgba(255,255,255,0.14)" : connector.accentColor,
                boxShadow: isConnected ? `0 0 36px ${connector.glowColor}` : connector.buttonShadow,
              }}
              type="button"
            >
              {isBusy ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Connecting...</span>
                </>
              ) : isConnected ? (
                <span>Connected</span>
              ) : (
                <span>Connect</span>
              )}
            </button>
          </div>

          <svg
            className="pointer-events-none absolute left-1/2 top-[12.25rem] h-52 w-[16rem] -translate-x-1/2 opacity-60"
            fill="none"
            viewBox="0 0 256 220"
          >
            <path
              className="remindr-jellyfish-tentacle-a"
              d="M48 0C52 38 34 82 42 128C48 165 62 192 56 220"
              stroke={connector.accentColor}
              strokeLinecap="round"
              strokeWidth="2.4"
            />
            <path
              className="remindr-jellyfish-tentacle-b"
              d="M84 0C88 42 72 88 84 144C92 180 102 198 98 220"
              stroke={connector.accentColor}
              strokeLinecap="round"
              strokeWidth="1.8"
            />
            <path
              className="remindr-jellyfish-tentacle-c"
              d="M128 0C132 44 124 98 136 154C144 188 144 202 142 220"
              stroke={connector.accentColor}
              strokeLinecap="round"
              strokeWidth="2.8"
            />
            <path
              className="remindr-jellyfish-tentacle-b"
              d="M172 0C180 34 164 94 178 150C186 180 196 198 194 220"
              stroke={connector.accentColor}
              strokeLinecap="round"
              strokeWidth="1.7"
              style={{ animationDelay: "-0.8s" }}
            />
            <path
              className="remindr-jellyfish-tentacle-a"
              d="M208 0C214 30 198 76 210 122C220 164 230 194 224 220"
              stroke={connector.accentColor}
              strokeLinecap="round"
              strokeWidth="2.3"
              style={{ animationDelay: "-1.1s" }}
            />
          </svg>
        </div>
      </div>
    </div>
  );
}
