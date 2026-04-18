import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import type { Task } from "@/types/domain";
import { formatRelativeDate } from "@/lib/utils";

export function TaskFilters({
  query,
  onQueryChange,
}: {
  query: string;
  onQueryChange: (value: string) => void;
}) {
  return (
    <Card variant="warm" className="rounded-panel">
      <div className="grid gap-4 md:grid-cols-[2fr_1fr_1fr]">
        <Input placeholder="Search tasks" value={query} onChange={(event) => onQueryChange(event.target.value)} />
        <Select defaultValue="all">
          <option value="all">All status</option>
          <option value="planned">Planned</option>
          <option value="active">In progress</option>
        </Select>
        <Select defaultValue="all">
          <option value="all">All energy</option>
          <option value="low">Low energy</option>
          <option value="high">High energy</option>
        </Select>
      </div>
    </Card>
  );
}

export function TaskCard({ task, onEdit }: { task: Task; onEdit: (task: Task) => void }) {
  return (
    <Card variant="clickable" className="rounded-panel">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <Link className="text-xl font-semibold text-ink" to={`/tasks/${task.id}`}>
            {task.title}
          </Link>
          <p className="mt-2 text-sm leading-6 text-muted">{task.description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={task.priority === "High" ? "warning" : "neutral"}>{task.priority}</Badge>
          <Badge tone="neutral">{task.status}</Badge>
          <Badge tone="info">{task.energy} energy</Badge>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <div className="flex flex-wrap gap-4">
          <span>{formatRelativeDate(task.deadline)}</span>
          <span>{task.estimatedEffort}</span>
          <span>{task.suggestedWindow}</span>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="secondary">
            Complete
          </Button>
          <Button onClick={() => onEdit(task)} type="button">
            Edit
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function TaskEditorModal({
  open,
  task,
  onClose,
  onSave,
}: {
  open: boolean;
  task: Task;
  onClose: () => void;
  onSave: (task: Task) => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title={task.id.startsWith("task-") ? "Edit task" : "Create task"}>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">Title</span>
          <Input defaultValue={task.title} id="task-title" />
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">Deadline</span>
          <Input defaultValue={task.deadline.slice(0, 10)} id="task-deadline" type="date" />
        </label>
        <label className="space-y-2 md:col-span-2">
          <span className="text-sm font-semibold text-ink">Description</span>
          <Textarea defaultValue={task.description} id="task-description" />
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">Priority</span>
          <Select defaultValue={task.priority} id="task-priority">
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </Select>
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">Energy</span>
          <Select defaultValue={task.energy} id="task-energy">
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </Select>
        </label>
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <Button onClick={onClose} type="button" variant="secondary">
          Cancel
        </Button>
        <Button
          onClick={() => {
            const title = (document.getElementById("task-title") as HTMLInputElement).value;
            const deadline = (document.getElementById("task-deadline") as HTMLInputElement).value;
            const description = (document.getElementById("task-description") as HTMLTextAreaElement).value;
            const priority = (document.getElementById("task-priority") as HTMLSelectElement).value as Task["priority"];
            const energy = (document.getElementById("task-energy") as HTMLSelectElement).value as Task["energy"];

            onSave({
              ...task,
              title,
              deadline: new Date(deadline).toISOString(),
              description,
              priority,
              energy,
            });
          }}
          type="button"
        >
          Save task
        </Button>
      </div>
    </Modal>
  );
}
