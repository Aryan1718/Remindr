import { ArrowRight, CheckCircle2, Clock3, Link2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { Integration, Suggestion, Task } from "@/types/domain";
import { formatRelativeDate } from "@/lib/utils";

export function FocusCard({ tasks }: { tasks: Task[] }) {
  return (
    <Card variant="elevated" className="rounded-panel">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-[0.3em] text-faint">Today focus</p>
          <h3 className="mt-2 font-display text-3xl uppercase leading-[1] tracking-[0.04em] text-ink">
            START WITH THE HIGH-LEVERAGE ITEMS.
          </h3>
        </div>
        <Badge tone="info">Limited list</Badge>
      </div>
      <div className="mt-6 space-y-4">
        {tasks.map((task) => (
          <div className="rounded-card border border-white/10 bg-black p-4" key={task.id}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-base font-medium uppercase tracking-[0.08em] text-ink">{task.title}</p>
                <p className="mt-2 text-sm text-faint">{task.suggestedWindow}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={task.priority === "High" ? "warning" : "neutral"}>{task.priority}</Badge>
                <Badge tone="neutral">{task.energy} energy</Badge>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function SuggestionCard({ suggestion }: { suggestion: Suggestion }) {
  return (
    <Card variant="clickable" className="rounded-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.3em] text-faint">{suggestion.type}</p>
          <h3 className="mt-2 text-xl font-medium uppercase tracking-[0.06em] text-ink">{suggestion.title}</h3>
        </div>
        <Badge tone={suggestion.urgency === "High" ? "warning" : "info"}>
          {suggestion.urgency} urgency
        </Badge>
      </div>
      <p className="mt-4 text-lg leading-7 text-ink">{suggestion.recommendation}</p>
      <p className="mt-3 text-sm leading-7 text-faint">{suggestion.reason}</p>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <Badge tone="neutral">{suggestion.confidence}</Badge>
        <div className="flex gap-2">
          <Button type="button">Accept</Button>
          <Button type="button" variant="secondary">
            Dismiss
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function DeadlineList({ tasks }: { tasks: Task[] }) {
  return (
    <Card variant="standard" className="rounded-panel">
      <h3 className="font-display text-2xl uppercase tracking-[0.04em] text-ink">Upcoming deadlines</h3>
      <div className="mt-5 space-y-4">
        {tasks.map((task) => (
          <div className="flex items-center justify-between gap-3 border-b border-border pb-4 last:border-none last:pb-0" key={task.id}>
            <div className="flex items-center gap-3">
              <Clock3 className="h-4 w-4 text-muted" />
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.06em] text-ink">{task.title}</p>
                <p className="text-sm text-faint">{task.estimatedEffort}</p>
              </div>
            </div>
            <Badge tone={task.priority === "High" ? "danger" : "neutral"}>
              {formatRelativeDate(task.deadline)}
            </Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ScheduleChangeList({ changes }: { changes: string[] }) {
  return (
    <Card variant="warm" className="rounded-panel">
      <h3 className="font-display text-2xl uppercase tracking-[0.04em] text-ink">Recent schedule changes</h3>
      <div className="mt-5 space-y-4">
        {changes.map((change) => (
          <div className="flex gap-3" key={change}>
            <ArrowRight className="mt-1 h-4 w-4 text-accent" />
            <p className="text-sm leading-7 text-faint">{change}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ConnectorStatusCard({ connectors }: { connectors: Integration[] }) {
  return (
    <Card variant="standard" className="rounded-panel">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-2xl uppercase tracking-[0.04em] text-ink">Connector status</h3>
        <Link2 className="h-4 w-4 text-muted" />
      </div>
      <div className="mt-5 space-y-4">
        {connectors.map((connector) => (
          <div className="flex items-start justify-between gap-3 rounded-card border border-white/10 bg-black p-4" key={connector.id}>
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.06em] text-ink">{connector.provider}</p>
              <p className="mt-1 text-sm text-faint">{connector.lastSync}</p>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-success" />
              <Badge
                tone={
                  connector.status === "Connected"
                    ? "success"
                    : connector.status === "Needs reconnect"
                      ? "warning"
                      : "neutral"
                }
              >
                {connector.status}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
