import { useQuery } from "@tanstack/react-query";
import { getTask, listTasks } from "@/api/tasks";

export function useTasksQuery() {
  return useQuery({
    queryKey: ["tasks"],
    queryFn: listTasks,
  });
}

export function useTaskDetailQuery(taskId: string) {
  return useQuery({
    queryKey: ["task", taskId],
    queryFn: () => getTask(taskId),
  });
}
