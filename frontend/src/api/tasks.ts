import { simulateRequest } from "@/api/client";
import { getDb, updateDb } from "@/mocks/db";
import type { Task } from "@/types/domain";

export function listTasks() {
  return simulateRequest(() => getDb().tasks);
}

export function getTask(taskId: string) {
  return simulateRequest(() => getDb().tasks.find((task) => task.id === taskId) ?? null);
}

export function saveTask(task: Task) {
  return simulateRequest(() => {
    const existing = getDb().tasks.find((entry) => entry.id === task.id);

    updateDb((current) => {
      const tasks = existing
        ? current.tasks.map((entry) => (entry.id === task.id ? task : entry))
        : [task, ...current.tasks];

      return {
        ...current,
        tasks,
        dashboard: {
          ...current.dashboard,
          deadlines: tasks.slice(0, 3),
          todayFocus: tasks.filter((entry) => entry.status !== "Completed").slice(0, 2),
        },
      };
    });

    return task;
  });
}
