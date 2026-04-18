import { simulateRequest } from "@/api/client";
import { getDb, updateDb } from "@/mocks/db";
import type { Goal } from "@/types/domain";

export function listGoals() {
  return simulateRequest(() => getDb().goals);
}

export function getGoal(goalId: string) {
  return simulateRequest(() => getDb().goals.find((goal) => goal.id === goalId) ?? null);
}

export function saveGoal(goal: Goal) {
  return simulateRequest(() => {
    const existing = getDb().goals.find((entry) => entry.id === goal.id);

    updateDb((current) => ({
      ...current,
      goals: existing
        ? current.goals.map((entry) => (entry.id === goal.id ? goal : entry))
        : [goal, ...current.goals],
    }));

    return goal;
  });
}
