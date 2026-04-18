import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageContainer } from "@/components/layout/PageContainer";
import { TaskCard, TaskEditorModal, TaskFilters } from "@/components/tasks/TaskBits";
import { useSaveTaskMutation } from "@/features/tasks/mutations";
import { useTasksQuery } from "@/features/tasks/queries";
import type { Task } from "@/types/domain";

const newTask: Task = {
  id: `draft-${Date.now()}`,
  title: "",
  description: "",
  deadline: new Date().toISOString(),
  estimatedEffort: "45 min",
  priority: "Medium",
  status: "Planned",
  energy: "Medium",
  suggestedWindow: "TBD",
  history: [],
};

export function TasksPage() {
  const { data } = useTasksQuery();
  const mutation = useSaveTaskMutation();
  const [query, setQuery] = useState("");
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  const tasks = useMemo(
    () =>
      (data ?? []).filter((task) =>
        `${task.title} ${task.description}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [data, query],
  );

  return (
    <PageContainer
      title="Tasks"
      description="Structured task management for the assistant. Keep editing light and let scheduling logic surface in the dashboard."
      actions={
        <Button
          onClick={() => setEditingTask({ ...newTask, id: `draft-${Date.now()}` })}
          type="button"
        >
          New task
        </Button>
      }
    >
      <TaskFilters onQueryChange={setQuery} query={query} />
      {tasks.length ? (
        <div className="space-y-4">
          {tasks.map((task) => (
            <TaskCard key={task.id} onEdit={setEditingTask} task={task} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No tasks yet"
          description="Create a task and let the assistant decide when it should surface."
          actionLabel="Create task"
          onAction={() => setEditingTask({ ...newTask, id: `draft-${Date.now()}` })}
        />
      )}
      {editingTask ? (
        <TaskEditorModal
          onClose={() => setEditingTask(null)}
          onSave={async (task) => {
            await mutation.mutateAsync(task);
            setEditingTask(null);
          }}
          open
          task={editingTask}
        />
      ) : null}
    </PageContainer>
  );
}
