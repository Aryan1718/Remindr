import { useQuery } from "@tanstack/react-query";
import { getGoal, listGoals } from "@/api/goals";

export function useGoalsQuery() {
  return useQuery({
    queryKey: ["goals"],
    queryFn: listGoals,
  });
}

export function useGoalDetailQuery(goalId: string) {
  return useQuery({
    queryKey: ["goal", goalId],
    queryFn: () => getGoal(goalId),
  });
}
