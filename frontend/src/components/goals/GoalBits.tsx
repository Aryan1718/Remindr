import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { Goal, Task } from "@/types/domain";

export function GoalCard({ goal, onEdit }: { goal: Goal; onEdit: (goal: Goal) => void }) {
  return (
    <Card variant="clickable" className="rounded-panel">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <Link className="text-xl font-semibold text-ink" to={`/goals/${goal.id}`}>
            {goal.title}
          </Link>
          <p className="mt-2 text-sm leading-6 text-muted">{goal.summary}</p>
        </div>
        <Badge tone={goal.status === "At risk" ? "warning" : goal.status === "Completed" ? "success" : "info"}>
          {goal.status}
        </Badge>
      </div>
      <div className="mt-5">
        <div className="h-2 rounded-full bg-black/5">
          <div className="h-2 rounded-full bg-accent" style={{ width: `${goal.progress}%` }} />
        </div>
        <div className="mt-3 flex items-center justify-between text-sm text-muted">
          <span>{goal.timeline}</span>
          <span>{goal.progress}% complete</span>
        </div>
      </div>
      <div className="mt-5 flex items-center justify-between">
        <Badge tone="neutral">{goal.watcherState}</Badge>
        <Button onClick={() => onEdit(goal)} type="button">
          Edit goal
        </Button>
      </div>
    </Card>
  );
}

export function GoalTaskSection({ tasks }: { tasks: Task[] }) {
  return (
    <Card variant="standard" className="rounded-panel">
      <h3 className="font-display text-2xl text-ink">Generated tasks</h3>
      <div className="mt-4 space-y-3">
        {tasks.map((task) => (
          <div className="rounded-card border border-border p-4" key={task.id}>
            <p className="text-sm font-semibold text-ink">{task.title}</p>
            <p className="mt-1 text-sm text-muted">{task.suggestedWindow}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function WatcherStatusPanel({ goal }: { goal: Goal }) {
  return (
    <Card variant="warm" className="rounded-panel">
      <p className="text-xs uppercase tracking-[0.18em] text-muted">Watcher state</p>
      <h3 className="mt-2 font-display text-3xl tracking-[-0.03em] text-ink">{goal.watcherState}</h3>
      <div className="mt-4 space-y-3">
        {goal.suggestions.map((item) => (
          <p className="rounded-card border border-border bg-[#1a1d21] p-4 text-sm leading-6 text-muted" key={item}>
            {item}
          </p>
        ))}
      </div>
    </Card>
  );
}
