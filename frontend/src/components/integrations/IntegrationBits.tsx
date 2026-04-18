import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { Integration } from "@/types/domain";

export function IntegrationCard({
  integration,
  onToggle,
}: {
  integration: Integration;
  onToggle: (integration: Integration) => void;
}) {
  return (
    <Card variant="clickable" className="rounded-panel">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xl font-semibold text-ink">{integration.provider}</p>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted">{integration.description}</p>
        </div>
        <Badge
          tone={
            integration.status === "Connected"
              ? "success"
              : integration.status === "Needs reconnect"
                ? "warning"
                : "neutral"
          }
        >
          {integration.status}
        </Badge>
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        {integration.permissions.map((permission) => (
          <Badge key={permission} tone="info">
            {permission}
          </Badge>
        ))}
      </div>
      <div className="mt-5 flex items-center justify-between">
        <p className="text-sm text-muted">Last sync: {integration.lastSync}</p>
        <Button onClick={() => onToggle(integration)} type="button">
          {integration.status === "Connected" ? "Reconnect" : "Connect"}
        </Button>
      </div>
    </Card>
  );
}
