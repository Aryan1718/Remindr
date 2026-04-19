import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IntegrationCard } from "@/components/integrations/IntegrationBits";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { useConnectTelegramBotMutation, useSaveIntegrationMutation } from "@/features/integrations/mutations";
import { useIntegrationsQuery } from "@/features/integrations/queries";
import type { Integration } from "@/types/domain";

export function IntegrationsPage() {
  const navigate = useNavigate();
  const { data = [] } = useIntegrationsQuery();
  const saveMutation = useSaveIntegrationMutation();
  const telegramMutation = useConnectTelegramBotMutation();
  const [selectedIntegration, setSelectedIntegration] = useState<Integration | null>(null);
  const [botToken, setBotToken] = useState("");
  const [webhookBaseUrl, setWebhookBaseUrl] = useState(window.location.origin);
  const [error, setError] = useState<string | null>(null);

  const telegramIntegration = useMemo(
    () => data.find((integration) => integration.id === "telegram") ?? null,
    [data],
  );

  async function handleConnect(integration: Integration) {
    if (integration.id !== "telegram") {
      await saveMutation.mutateAsync({
        ...integration,
        status: "Connected",
        lastSync: "Just now",
      });
      navigate(`/connectors/${integration.id}/callback?status=success`);
      return;
    }

    setSelectedIntegration(integration);
    setError(null);
  }

  async function submitTelegramBot() {
    setError(null);

    try {
      await telegramMutation.mutateAsync({
        botToken,
        webhookBaseUrl,
      });
      setSelectedIntegration(null);
      setBotToken("");
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : "Unable to connect the Telegram bot.");
    }
  }

  return (
    <>
      <PageContainer
        title="Integrations"
        description="Google integrations are still mock-driven. Telegram is wired to the backend so each user can register their own bot token and receive webhook events through that bot."
      >
        <div className="space-y-4">
          {data.map((integration) => (
            <IntegrationCard integration={integration} key={integration.id} onToggle={handleConnect} />
          ))}
          {telegramIntegration ? (
            <div className="rounded-panel border border-border bg-surface-alt px-5 py-4 text-sm leading-6 text-muted">
              <p className="font-medium text-ink">Telegram bring-your-own-bot flow</p>
              <p className="mt-2">
                Create a bot with BotFather, paste that token here, then open your bot in Telegram and send{" "}
                <span className="font-medium text-ink">/start</span> so the backend can capture the chat id on the
                webhook route.
              </p>
            </div>
          ) : null}
        </div>
      </PageContainer>

      <Modal
        open={selectedIntegration?.id === "telegram"}
        onClose={() => setSelectedIntegration(null)}
        title="Connect your Telegram bot"
      >
        <div className="space-y-5">
          <div className="space-y-2">
            <p className="text-sm uppercase tracking-[0.16em] text-faint">Bot token</p>
            <Input
              onChange={(event) => setBotToken(event.target.value)}
              placeholder="123456789:AA..."
              type="password"
              value={botToken}
            />
          </div>
          <div className="space-y-2">
            <p className="text-sm uppercase tracking-[0.16em] text-faint">Webhook base URL</p>
            <Input
              onChange={(event) => setWebhookBaseUrl(event.target.value)}
              placeholder="https://your-public-app-url.com"
              value={webhookBaseUrl}
            />
            <p className="text-sm leading-6 text-muted">
              The backend will register <span className="font-medium text-ink">/api/v1/telegram/webhook/demo-user</span>{" "}
              under this base URL.
            </p>
          </div>
          <div className="rounded-panel border border-border bg-black/20 px-4 py-3 text-sm leading-6 text-muted">
            <p>After saving the token:</p>
            <p>1. Open your Telegram bot.</p>
            <p>2. Press Start or send /start.</p>
            <p>3. Telegram will hit the webhook and your chat id will be stored on the Telegram connector.</p>
          </div>
          {error ? <p className="text-sm text-danger">{error}</p> : null}
          <div className="flex justify-end gap-3">
            <Button onClick={() => setSelectedIntegration(null)} type="button" variant="ghost">
              Cancel
            </Button>
            <Button
              disabled={!botToken.trim() || telegramMutation.isPending}
              onClick={submitTelegramBot}
              type="button"
            >
              {telegramMutation.isPending ? "Saving..." : "Save bot token"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
