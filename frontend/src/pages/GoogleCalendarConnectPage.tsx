import { ArrowLeft, CalendarRange, CheckCircle2, ChevronDown, Link2, Orbit } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { startGoogleCalendarOAuth } from "@/api/integrations";
import { PageContainer } from "@/components/layout/PageContainer";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import {
  useConnectGoogleCalendarMutation,
  useTriggerGoogleCalendarSyncMutation,
} from "@/features/integrations/mutations";

const panelClassName =
  "relative overflow-hidden rounded-[28px] border border-white/12 bg-[linear-gradient(160deg,rgba(255,255,255,0.05),rgba(255,255,255,0.015))] shadow-[0_24px_80px_rgba(0,0,0,0.35)]";

export function GoogleCalendarConnectPage() {
  const navigate = useNavigate();
  const connectMutation = useConnectGoogleCalendarMutation();
  const syncMutation = useTriggerGoogleCalendarSyncMutation();

  const [accountEmail, setAccountEmail] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [tokenExpiresAt, setTokenExpiresAt] = useState("");
  const [calendarId, setCalendarId] = useState("primary");
  const [pageError, setPageError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [oauthPending, setOauthPending] = useState(false);

  const isSubmitting = connectMutation.isPending || syncMutation.isPending || oauthPending;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;

    setPageError(null);

    try {
      const connector = await connectMutation.mutateAsync({
        accountEmail,
        accessToken,
        refreshToken,
        tokenExpiresAt: tokenExpiresAt || undefined,
        calendarId,
      });

      if (!connector?.id) {
        throw new Error("Connector registration completed without a connector id.");
      }

      const sync = await syncMutation.mutateAsync(connector.id);
      navigate(
        `/connectors/google-calendar/callback?status=success&connector_id=${encodeURIComponent(connector.id)}&job_status=${encodeURIComponent(sync.job_status || "queued")}`,
      );
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to connect Google Calendar.");
    }
  }

  async function handleOAuthStart() {
    if (isSubmitting) return;
    setPageError(null);
    setOauthPending(true);

    try {
      const authorizationUrl = await startGoogleCalendarOAuth();
      window.location.assign(authorizationUrl);
    } catch (error) {
      setOauthPending(false);
      setPageError(error instanceof Error ? error.message : "Unable to start Google Calendar OAuth.");
    }
  }

  return (
    <PageContainer
      title="Google Calendar"
      description="Connect the external calendar truth layer without writing those events into the assistant-owned planner. This screen uses the backend connector contract directly: register connector, then queue sync."
      actions={
        <Link
          className="inline-flex items-center gap-2 border border-white/14 px-4 py-3 text-[12px] uppercase tracking-[0.18em] text-white/78 transition hover:border-white/30 hover:bg-white/5 hover:text-white"
          to="/integrations"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to integrations
        </Link>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <section className={panelClassName}>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,192,0,0.16),transparent_28%),radial-gradient(circle_at_left_center,rgba(41,171,226,0.14),transparent_32%)]" />
          <div className="relative p-6 md:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-2xl">
                <Badge tone="info">Backend contract active</Badge>
                <h2 className="mt-4 font-display text-4xl uppercase leading-[0.95] tracking-[0.03em] text-ink">
                  Register then sync in one pass
                </h2>
                <p className="mt-4 max-w-xl text-sm leading-7 text-faint">
                  This page is the frontend handoff surface for the current MVP. It expects the Google OAuth exchange
                  to have already produced tokens, then sends those tokens to the backend connector endpoints and
                  immediately queues a normalization sync.
                </p>
              </div>
              <div className="grid min-w-[220px] gap-3">
                <div className="border border-white/12 bg-black/25 px-4 py-3">
                  <p className="text-[10px] uppercase tracking-[0.28em] text-faint">Window</p>
                  <p className="mt-2 text-lg uppercase tracking-[0.08em] text-ink">Past 7 / next 14 days</p>
                </div>
                <div className="border border-white/12 bg-black/25 px-4 py-3">
                  <p className="text-[10px] uppercase tracking-[0.28em] text-faint">Writes</p>
                  <p className="mt-2 text-lg uppercase tracking-[0.08em] text-ink">External events only</p>
                </div>
              </div>
            </div>

            <div className="mt-8 space-y-6">
              <div className="rounded-[24px] border border-white/12 bg-black/20 p-6">
                <p className="text-[10px] uppercase tracking-[0.28em] text-faint">Recommended flow</p>
                <h3 className="mt-3 font-display text-2xl uppercase tracking-[0.04em] text-ink">
                  Connect with one click
                </h3>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-muted">
                  This is now the normal user path. The button requests an authenticated backend OAuth start URL, then
                  redirects into Google consent and returns through the backend callback flow.
                </p>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <Button onClick={handleOAuthStart} type="button">
                    {oauthPending ? "Redirecting..." : "Connect Google Calendar"}
                  </Button>
                  <p className="text-sm leading-6 text-faint">
                    If Google OAuth is configured in the backend, this will send you straight into the real consent flow.
                  </p>
                </div>
              </div>

              {pageError ? (
                <div className="border border-danger/30 bg-danger/10 px-4 py-3 text-sm leading-6 text-danger">
                  {pageError}
                </div>
              ) : null}

              <div className="overflow-hidden rounded-[24px] border border-white/12 bg-black/18">
                <button
                  className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left transition hover:bg-white/5"
                  onClick={() => setShowAdvanced((current) => !current)}
                  type="button"
                >
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.28em] text-faint">Advanced</p>
                    <p className="mt-2 text-lg uppercase tracking-[0.06em] text-ink">Manual token entry for testing</p>
                  </div>
                  <ChevronDown
                    className={`h-5 w-5 text-faint transition-transform ${showAdvanced ? "rotate-180" : ""}`}
                  />
                </button>

                {showAdvanced ? (
                  <form className="grid gap-5 border-t border-white/10 px-6 py-6" onSubmit={handleSubmit}>
                    <div className="grid gap-5 md:grid-cols-2">
                      <label className="space-y-2">
                        <span className="text-[10px] uppercase tracking-[0.28em] text-faint">Google account email</span>
                        <Input
                          onChange={(event) => setAccountEmail(event.target.value)}
                          placeholder="you@example.com"
                          type="email"
                          value={accountEmail}
                        />
                      </label>
                      <label className="space-y-2">
                        <span className="text-[10px] uppercase tracking-[0.28em] text-faint">Calendar id</span>
                        <Input
                          onChange={(event) => setCalendarId(event.target.value)}
                          placeholder="primary"
                          value={calendarId}
                        />
                      </label>
                    </div>

                    <label className="space-y-2">
                      <span className="text-[10px] uppercase tracking-[0.28em] text-faint">Access token</span>
                      <Input
                        onChange={(event) => setAccessToken(event.target.value)}
                        placeholder="ya29..."
                        type="password"
                        value={accessToken}
                      />
                    </label>

                    <div className="grid gap-5 md:grid-cols-[1fr_0.8fr]">
                      <label className="space-y-2">
                        <span className="text-[10px] uppercase tracking-[0.28em] text-faint">Refresh token</span>
                        <Input
                          onChange={(event) => setRefreshToken(event.target.value)}
                          placeholder="1//0..."
                          type="password"
                          value={refreshToken}
                        />
                      </label>
                      <label className="space-y-2">
                        <span className="text-[10px] uppercase tracking-[0.28em] text-faint">Token expires at</span>
                        <Input
                          onChange={(event) => setTokenExpiresAt(event.target.value)}
                          placeholder="2026-04-20T00:00:00Z"
                          value={tokenExpiresAt}
                        />
                      </label>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 pt-2">
                      <Button disabled={!accountEmail.trim() || !accessToken.trim() || isSubmitting} type="submit">
                        {isSubmitting ? "Connecting..." : "Connect and sync calendar"}
                      </Button>
                      <p className="text-sm leading-6 text-faint">
                        This submits directly to the backend connector endpoints for local validation.
                      </p>
                    </div>
                  </form>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-6">
          <Card className="rounded-[28px] border-white/12 bg-surface-alt/80">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/12 bg-black/25">
                <Link2 className="h-5 w-5 text-accent" />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.28em] text-faint">Exact frontend flow</p>
                <p className="mt-1 text-lg uppercase tracking-[0.06em] text-ink">What this page does</p>
              </div>
            </div>
            <div className="mt-5 space-y-4 text-sm leading-7 text-muted">
              <p>1. Takes Google OAuth token output from the frontend handoff.</p>
              <p>2. Stores the connector row in backend `connectors`.</p>
              <p>3. Queues async sync work instead of blocking the UI.</p>
              <p>4. Leaves `internal_calendar` untouched and writes normalized rows separately.</p>
            </div>
          </Card>

          <Card className="rounded-[28px] border-white/12 bg-surface-alt/80">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/12 bg-black/25">
                <CalendarRange className="h-5 w-5 text-focus" />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.28em] text-faint">Required today</p>
                <p className="mt-1 text-lg uppercase tracking-[0.06em] text-ink">Token handoff fields</p>
              </div>
            </div>
            <div className="mt-5 space-y-3 text-sm leading-7 text-muted">
              <p>`account_email` and `access_token` are required for the current backend contract.</p>
              <p>`refresh_token` and `token_expires_at` should be passed whenever your OAuth provider returns them.</p>
              <p>`calendar_id` defaults to `primary` and matches the MVP sync target.</p>
            </div>
          </Card>

          <Card className="rounded-[28px] border-white/12 bg-[linear-gradient(180deg,rgba(255,192,0,0.12),rgba(255,192,0,0.03))]">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-accent/30 bg-black/25">
                <Orbit className="h-5 w-5 text-accent" />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.28em] text-faint">Next improvement</p>
                <p className="mt-1 text-lg uppercase tracking-[0.06em] text-ink">Swap in auth code exchange</p>
              </div>
            </div>
            <div className="mt-5 space-y-3 text-sm leading-7 text-muted">
              <p>
                Once a backend Google OAuth callback endpoint exists, this page can replace manual token fields with a
                single “Continue with Google Calendar” redirect.
              </p>
              <p className="flex items-center gap-2 text-success">
                <CheckCircle2 className="h-4 w-4" />
                The connect and sync contract below can stay the same.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}
