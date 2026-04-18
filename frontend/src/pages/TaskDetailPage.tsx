import { useParams } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/ui/EmptyState";
import { useTaskDetailQuery } from "@/features/tasks/queries";

export function TaskDetailPage() {
  const { taskId = "" } = useParams();
  const { data } = useTaskDetailQuery(taskId);

  if (!data) {
    return (
      <PageContainer title="Task detail" description="Review recommendation history and the current execution window.">
        <EmptyState
          title="Task not found"
          description="The selected task is missing from the mock store."
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer title={data.title} description="The task detail view explains why this item is placed where it is.">
      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card variant="elevated" className="rounded-panel">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">Description</p>
          <p className="mt-4 text-sm leading-7 text-muted">{data.description}</p>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-card border border-border p-4">
              <p className="text-sm font-semibold text-ink">Suggested execution window</p>
              <p className="mt-2 text-sm text-muted">{data.suggestedWindow}</p>
            </div>
            <div className="rounded-card border border-border p-4">
              <p className="text-sm font-semibold text-ink">Status</p>
              <p className="mt-2 text-sm text-muted">{data.status}</p>
            </div>
          </div>
        </Card>
        <Card variant="warm" className="rounded-panel">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">Recommendation history</p>
          <div className="mt-4 space-y-3">
            {data.history.map((entry) => (
              <p className="rounded-card border border-border bg-[#1a1d21] p-4 text-sm leading-6 text-muted" key={entry}>
                {entry}
              </p>
            ))}
          </div>
        </Card>
      </div>
    </PageContainer>
  );
}
