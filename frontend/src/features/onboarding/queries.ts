import { useQuery } from "@tanstack/react-query";
import { getOnboardingDraft } from "@/api/onboarding";

export function useOnboardingQuery() {
  return useQuery({
    queryKey: ["onboarding"],
    queryFn: getOnboardingDraft,
  });
}
