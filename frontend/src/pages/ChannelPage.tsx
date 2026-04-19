import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Check, Loader2, Send, Shield } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useSaveIntegrationMutation, useConnectTelegramBotMutation } from "@/features/integrations/mutations";
import { useIntegrationsQuery } from "@/features/integrations/queries";
import { useSaveOnboardingMutation } from "@/features/onboarding/mutations";
import { useOnboardingQuery } from "@/features/onboarding/queries";
import type { Integration } from "@/types/domain";

type ConnectionState = "idle" | "focused" | "connecting" | "success" | "error";

interface ParticleSpec {
  id: string;
  left: string;
  top: string;
  delay: string;
  duration: string;
}

const fallbackTelegramIntegration: Integration = {
  id: "telegram",
  provider: "Telegram",
  status: "Not connected",
  lastSync: "Not linked",
  description: "Primary communication channel for suggestions and check-ins.",
  permissions: ["Send messages", "Receive user replies"],
};

function buildTelegramIntegration(
  base: Integration,
  connection: {
    bot_username: string | null;
    bot_first_name: string | null;
    telegram_chat_id: number | null;
    last_event_at: string | null;
  },
): Integration {
  const isLinked = connection.telegram_chat_id !== null;

  return {
    ...base,
    provider: connection.bot_first_name || connection.bot_username || "Telegram",
    status: isLinked ? "Connected" : "Needs reconnect",
    lastSync: connection.last_event_at ? new Date(connection.last_event_at).toLocaleString() : "Waiting for /start",
    description: isLinked
      ? "Your Telegram bot is registered and linked to a Telegram chat. Webhook events are being stored by the backend."
      : "Bot token saved. Open your bot in Telegram and send /start so the backend can capture the chat id.",
  };
}

export function ChannelPage() {
  const navigate = useNavigate();
  const { data: onboardingDraft } = useOnboardingQuery();
  const { data: integrations = [] } = useIntegrationsQuery();
  const saveOnboardingMutation = useSaveOnboardingMutation();
  const saveIntegrationMutation = useSaveIntegrationMutation();
  const connectTelegramMutation = useConnectTelegramBotMutation();
  const [botToken, setBotToken] = useState("");
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [isFocused, setIsFocused] = useState(false);
  const [errorMessage, setErrorMessage] = useState("Please enter a valid bot token");
  const [isFinishing, setIsFinishing] = useState(false);

  const particles = useMemo<ParticleSpec[]>(
    () =>
      Array.from({ length: 20 }, (_, index) => ({
        id: `channel-particle-${index}`,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        delay: `${Math.random() * 5}s`,
        duration: `${8 + Math.random() * 4}s`,
      })),
    [],
  );

  const telegramIntegration =
    integrations.find((integration) => integration.id === "telegram") ?? fallbackTelegramIntegration;

  useEffect(() => {
    if (onboardingDraft?.telegramConnected) {
      setConnectionState("success");
    }
  }, [onboardingDraft?.telegramConnected]);

  useEffect(() => {
    if (connectionState !== "error" || errorMessage !== "Please enter a valid bot token") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setConnectionState("idle");
    }, 3000);

    return () => window.clearTimeout(timeoutId);
  }, [connectionState, errorMessage]);

  async function finalizeChannelStep(telegramConnected: boolean) {
    if (!onboardingDraft) {
      navigate("/dashboard");
      return;
    }

    setIsFinishing(true);

    try {
      await saveOnboardingMutation.mutateAsync({
        ...onboardingDraft,
        stage: "complete",
        telegramConnected,
        completed: true,
      });

      navigate("/dashboard");
    } finally {
      setIsFinishing(false);
    }
  }

  async function handleConnect() {
    if (!botToken.trim()) {
      setErrorMessage("Please enter a valid bot token");
      setConnectionState("error");
      return;
    }

    setConnectionState("connecting");

    try {
      const connection = await connectTelegramMutation.mutateAsync({ botToken: botToken.trim() });
      if (!connection) {
        throw new Error("Unable to connect Telegram");
      }

      await saveIntegrationMutation.mutateAsync(
        buildTelegramIntegration(telegramIntegration, {
          bot_username: connection.bot_username,
          bot_first_name: connection.bot_first_name,
          telegram_chat_id: connection.telegram_chat_id,
          last_event_at: connection.last_event_at,
        }),
      );

      if (onboardingDraft) {
        await saveOnboardingMutation.mutateAsync({
          ...onboardingDraft,
          stage: "channel",
          telegramConnected: true,
          completed: false,
        });
      }

      setConnectionState("success");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to connect Telegram");
      setConnectionState("error");
    }
  }

  function handleTokenChange(value: string) {
    setBotToken(value);
    if (connectionState === "error") {
      setConnectionState(isFocused ? "focused" : "idle");
      setErrorMessage("Please enter a valid bot token");
    }
  }

  function handleFocus() {
    setIsFocused(true);
    if (connectionState !== "connecting" && connectionState !== "success") {
      setConnectionState("focused");
    }
  }

  function handleBlur() {
    setIsFocused(false);
    if (connectionState === "focused") {
      setConnectionState("idle");
    }
  }

  return (
    <div className="relative h-screen w-full overflow-hidden bg-black">
      <div className="absolute inset-0 z-0">
        <video autoPlay className="h-full w-full object-cover opacity-60" loop muted playsInline>
          <source
            src="https://res.cloudinary.com/djo4b8zll/video/upload/v1776581119/48596-454825141_medium_ttqyeq.mp4"
            type="video/mp4"
          />
        </video>
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/70" />
        <div className="absolute inset-0 bg-gradient-to-t from-cyan-950/20 via-transparent to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-br from-blue-950/10 via-transparent to-teal-950/10" />
      </div>

      <div className="pointer-events-none absolute inset-0 z-10">
        {particles.map((particle) => (
          <div
            className="remindr-channel-particle absolute h-1 w-1 rounded-full bg-cyan-300/30"
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

      <div className="pointer-events-none absolute inset-0 z-10 overflow-hidden">
        <div className="remindr-channel-light-ray absolute left-1/4 top-0 h-full w-px bg-gradient-to-b from-cyan-400/10 via-transparent to-transparent" />
        <div
          className="remindr-channel-light-ray absolute right-1/3 top-0 h-full w-px bg-gradient-to-b from-cyan-400/10 via-transparent to-transparent"
          style={{ animationDelay: "1s", animationDuration: "8s" }}
        />
      </div>

      <div className="relative z-30 flex h-full w-full flex-col items-center justify-between px-6 py-10 sm:px-8 sm:py-12">
        <div className="remindr-channel-page-entry text-center">
          <h1 className="remindr-wordmark text-2xl text-cyan-100/90 sm:text-3xl">Remindr</h1>
          <div className="mx-auto mt-2 h-px w-20 bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
        </div>

        <div className="remindr-channel-card-entry w-full max-w-xl">
          <div
            className="relative overflow-hidden rounded-3xl border border-cyan-500/20 bg-gradient-to-br from-slate-900/60 via-slate-800/40 to-slate-900/60 backdrop-blur-2xl"
            style={{
              boxShadow:
                "0 0 60px rgba(6, 182, 212, 0.15), inset 0 0 60px rgba(6, 182, 212, 0.03)",
            }}
          >
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent" />
            <div className="absolute left-0 right-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent" />

            <div className="remindr-channel-glow absolute -right-20 -top-20 h-40 w-40 rounded-full bg-cyan-500/20 blur-3xl" />

            <div className="relative p-7 sm:p-12">
              {connectionState === "success" ? (
                <div className="text-center">
                  <div className="mb-6 inline-flex h-20 w-20 items-center justify-center rounded-full border-2 border-emerald-400/50 bg-emerald-500/20">
                    <Check className="h-10 w-10 text-emerald-400" />
                  </div>
                  <h2 className="text-2xl text-white sm:text-3xl">Channel Connected</h2>
                  <p className="mb-8 mt-4 text-sm leading-7 text-cyan-200/70 sm:text-base">
                    Your Telegram channel is now linked to Remindr. You&apos;ll receive your reminders
                    and updates there.
                  </p>
                  <button
                    className="rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 px-8 py-4 text-white transition-all duration-300 hover:from-cyan-500 hover:to-cyan-400 hover:shadow-[0_18px_44px_rgba(34,211,238,0.22)] disabled:cursor-wait disabled:opacity-60"
                    disabled={isFinishing}
                    onClick={() => void finalizeChannelStep(true)}
                    type="button"
                  >
                    {isFinishing ? "Opening dashboard..." : "Continue to Dashboard"}
                  </button>
                </div>
              ) : (
                <div>
                  <div className="mb-10 text-center">
                    <h2 className="text-2xl text-white sm:text-3xl">Connect your channel</h2>
                    <p className="mt-4 text-sm leading-7 text-cyan-200/70 sm:text-base">
                      Telegram is the primary conversation surface for Remindr.
                    </p>
                  </div>

                  <div className="mb-8 rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-blue-950/40 to-cyan-950/30 p-5 sm:p-6">
                    <div className="mb-6 flex items-start gap-4">
                      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg shadow-blue-500/30">
                        <Send className="h-7 w-7 text-white" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <h3 className="text-xl text-white">Telegram</h3>
                        <p className="mt-2 text-sm text-cyan-200/60">
                          Your conversation channel for reminders, updates, and interactions.
                        </p>
                      </div>
                    </div>

                    <div className="mb-4 flex items-center gap-2 rounded-lg border border-cyan-500/10 bg-cyan-950/30 px-3 py-2 text-xs text-cyan-300/60">
                      <Shield className="h-3.5 w-3.5" />
                      <span>End-to-end encrypted connection</span>
                    </div>

                    <div className="mb-4">
                      <label className="mb-3 block text-sm text-cyan-200/80" htmlFor="channel-token">
                        Bot Token
                      </label>
                      <div
                        className="relative overflow-hidden rounded-xl border bg-slate-900/60 backdrop-blur-sm transition-all duration-300"
                        style={{
                          borderColor:
                            connectionState === "error"
                              ? "rgba(239, 68, 68, 0.5)"
                              : isFocused
                                ? "rgba(6, 182, 212, 0.5)"
                                : "rgba(6, 182, 212, 0.2)",
                          boxShadow: isFocused
                            ? "0 0 20px rgba(6, 182, 212, 0.2)"
                            : "0 0 0 rgba(6, 182, 212, 0)",
                        }}
                      >
                        <input
                          className="w-full bg-transparent px-4 py-3.5 text-white outline-none placeholder:text-cyan-300/30"
                          id="channel-token"
                          onBlur={handleBlur}
                          onChange={(event) => handleTokenChange(event.target.value)}
                          onFocus={handleFocus}
                          placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                          type="text"
                          value={botToken}
                        />
                      </div>
                      <p className="mt-2 text-xs text-cyan-300/50">
                        Paste your Telegram bot token to link the conversation channel.
                      </p>
                    </div>

                    {connectionState === "error" ? (
                      <div className="remindr-channel-message flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-950/30 px-3 py-2 text-sm text-red-400">
                        <AlertCircle className="h-4 w-4" />
                        <span>{errorMessage}</span>
                      </div>
                    ) : null}
                  </div>

                  <div className="flex flex-col gap-3">
                    <button
                      className="group relative w-full overflow-hidden rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 px-6 py-4 text-white shadow-lg shadow-cyan-500/25 transition-all duration-300 hover:from-cyan-500 hover:to-cyan-400 hover:shadow-[0_18px_44px_rgba(34,211,238,0.22)] disabled:cursor-wait disabled:opacity-50"
                      disabled={connectionState === "connecting" || connectTelegramMutation.isPending}
                      onClick={() => void handleConnect()}
                      type="button"
                    >
                      <span className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-500 group-hover:translate-x-full" />
                      <span className="relative flex items-center justify-center gap-2">
                        {connectionState === "connecting" || connectTelegramMutation.isPending ? (
                          <>
                            <Loader2 className="h-5 w-5 animate-spin" />
                            Connecting...
                          </>
                        ) : (
                          "Connect Telegram"
                        )}
                      </span>
                    </button>

                    <button
                      className="px-6 py-3 text-cyan-300/70 transition-colors hover:text-cyan-200 disabled:cursor-wait disabled:opacity-50"
                      disabled={connectionState === "connecting" || connectTelegramMutation.isPending || isFinishing}
                      onClick={() => void finalizeChannelStep(false)}
                      type="button"
                    >
                      {isFinishing ? "Opening dashboard..." : "Skip for now"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="h-12" />
      </div>
    </div>
  );
}
