import { useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { PageContainer } from "@/components/layout/PageContainer";

export function ConnectorCallbackPage() {
  const { provider = "connector" } = useParams();
  const [search] = useSearchParams();
  const status = search.get("status") ?? "success";
  const tone = useMemo(() => (status === "success" ? "success" : "warning"), [status]);

  return (
    <PageContainer
      title="Connector callback"
      description="Mock callback surface for provider auth results and post-connect confirmation."
    >
      <Card variant="elevated" className="mx-auto max-w-2xl rounded-panel text-center">
        <Badge tone={tone}>{status === "success" ? "Connected" : "Needs review"}</Badge>
        <h2 className="mt-4 font-display text-4xl tracking-[-0.04em] text-ink">
          {provider} authorization processed
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-muted">
          In production this route would receive provider state, validate the callback, and then refresh the integration list.
        </p>
        <Button className="mt-6" type="button" variant="secondary">
          Return to integrations
        </Button>
      </Card>
    </PageContainer>
  );
}
