import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveOnboardingDraft } from "@/api/onboarding";
import type { OnboardingDraft } from "@/types/domain";

export function useSaveOnboardingMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (draft: OnboardingDraft) => saveOnboardingDraft(draft),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["onboarding"] });
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
