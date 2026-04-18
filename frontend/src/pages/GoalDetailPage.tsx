import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { GoalTaskSection, WatcherStatusPanel } from "@/components/goals/GoalBits";
import { PageContainer } from "@/components/layout/PageContainer";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { useGoalDetailQuery, useGoalsQuery } from "@/features/goals/queries";
import { useTasksQuery } from "@/features/tasks/queries";

export function GoalDetailPage() {
  const { goalId = "" } = useParams();
  const { data } = useGoalDetailQuery(goalId);
  const { data: tasks = [] } = useTasksQuery();
  const linkedTasks = useMemo(
    () => tasks.filter((task) => task.linkedGoalId === goalId),
    [goalId, tasks],
  );

  if (!data) {
    return (
      <PageContainer title="Goal detail" description="Review progress, generated tasks, and recent suggestions.">
        <EmptyState title="Goal not found" description="The selected goal is missing from the mock store." />
      </PageContainer>
    );
  }

  return (
    <PageContainer title={data.title} description={data.summary}>
      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card variant="elevated" className="rounded-panel">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">Goal summary</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded-card border border-border p-4">
              <p className="text-sm font-semibold text-ink">Timeline</p>
              <p className="mt-2 text-sm text-muted">{data.timeline}</p>
            </div>
            <div className="rounded-card border border-border p-4">
              <p className="text-sm font-semibold text-ink">Status</p>
              <p className="mt-2 text-sm text-muted">{data.status}</p>
            </div>
          </div>
          <div className="mt-6 h-2 rounded-full bg-black/5">
            <div className="h-2 rounded-full bg-accent" style={{ width: `${data.progress}%` }} />
          </div>
          <p className="mt-3 text-sm text-muted">{data.progress}% complete</p>
        </Card>
        <WatcherStatusPanel goal={data} />
      </div>
      <GoalTaskSection tasks={linkedTasks} />
    </PageContainer>
  );
}
