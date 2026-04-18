import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveTask } from "@/api/tasks";
import type { Task } from "@/types/domain";

export function useSaveTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (task: Task) => saveTask(task),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
