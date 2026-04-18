import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveGoal } from "@/api/goals";
import type { Goal } from "@/types/domain";

export function useSaveGoalMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (goal: Goal) => saveGoal(goal),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["goals"] });
    },
  });
}
