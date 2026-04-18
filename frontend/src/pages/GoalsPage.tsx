import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input, Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { PageContainer } from "@/components/layout/PageContainer";
import { GoalCard } from "@/components/goals/GoalBits";
import { useSaveGoalMutation } from "@/features/goals/mutations";
import { useGoalsQuery } from "@/features/goals/queries";
import type { Goal } from "@/types/domain";

const blankGoal: Goal = {
  id: `goal-draft-${Date.now()}`,
  title: "",
  summary: "",
  timeline: "",
  status: "Active",
  progress: 0,
  linkedTaskIds: [],
  watcherState: "Watching",
  suggestions: [],
};

export function GoalsPage() {
  const { data } = useGoalsQuery();
  const mutation = useSaveGoalMutation();
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);

  const goals = useMemo(() => data ?? [], [data]);

  return (
    <PageContainer
      title="Goals"
      description="Longer-horizon targets that the assistant can break into tasks and keep in view."
      actions={
        <Button onClick={() => setEditingGoal({ ...blankGoal, id: `goal-draft-${Date.now()}` })} type="button">
          New goal
        </Button>
      }
    >
      {goals.length ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {goals.map((goal) => (
            <GoalCard goal={goal} key={goal.id} onEdit={setEditingGoal} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No goals yet"
          description="Add a goal and let the backend later structure it into concrete tasks."
          actionLabel="Create goal"
          onAction={() => setEditingGoal({ ...blankGoal, id: `goal-draft-${Date.now()}` })}
        />
      )}
      <Modal open={Boolean(editingGoal)} onClose={() => setEditingGoal(null)} title="Goal editor">
        {editingGoal ? (
          <div className="space-y-4">
            <label className="space-y-2">
              <span className="text-sm font-semibold">Goal title</span>
              <Input defaultValue={editingGoal.title} id="goal-title" />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold">Timeline</span>
              <Input defaultValue={editingGoal.timeline} id="goal-timeline" />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold">Summary</span>
              <Textarea defaultValue={editingGoal.summary} id="goal-summary" />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold">Watcher state</span>
              <Select defaultValue={editingGoal.watcherState} id="goal-watcher">
                <option>Watching</option>
                <option>Needs input</option>
                <option>On track</option>
              </Select>
            </label>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setEditingGoal(null)} type="button" variant="secondary">
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  const nextGoal: Goal = {
                    ...editingGoal,
                    title: (document.getElementById("goal-title") as HTMLInputElement).value,
                    timeline: (document.getElementById("goal-timeline") as HTMLInputElement).value,
                    summary: (document.getElementById("goal-summary") as HTMLTextAreaElement).value,
                    watcherState: (document.getElementById("goal-watcher") as HTMLSelectElement)
                      .value as Goal["watcherState"],
                  };
                  await mutation.mutateAsync(nextGoal);
                  setEditingGoal(null);
                }}
                type="button"
              >
                Save goal
              </Button>
            </div>
          </div>
        ) : (
          <Card variant="warm">Loading goal…</Card>
        )}
      </Modal>
    </PageContainer>
  );
}
