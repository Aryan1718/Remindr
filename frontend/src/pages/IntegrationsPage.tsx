import { useNavigate } from "react-router-dom";
import { PageContainer } from "@/components/layout/PageContainer";
import { IntegrationCard } from "@/components/integrations/IntegrationBits";
import { useSaveIntegrationMutation } from "@/features/integrations/mutations";
import { useIntegrationsQuery } from "@/features/integrations/queries";

export function IntegrationsPage() {
  const navigate = useNavigate();
  const { data = [] } = useIntegrationsQuery();
  const mutation = useSaveIntegrationMutation();

  return (
    <PageContainer
      title="Integrations"
      description="Connect, reconnect, and inspect data sources. The cards are mock-driven but modeled around the callback flow documented for the backend."
    >
      <div className="space-y-4">
        {data.map((integration) => (
          <IntegrationCard
            integration={integration}
            key={integration.id}
            onToggle={async (current) => {
              await mutation.mutateAsync({
                ...current,
                status: "Connected",
                lastSync: "Just now",
              });
              navigate(`/connectors/${current.id}/callback?status=success`);
            }}
          />
        ))}
      </div>
    </PageContainer>
  );
}
