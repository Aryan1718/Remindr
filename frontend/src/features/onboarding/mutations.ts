import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveOnboardingDraft } from "@/api/onboarding";
import { useAuthStore } from "@/stores/authStore";
import type { OnboardingDraft } from "@/types/domain";

export function useSaveOnboardingMutation() {
  const queryClient = useQueryClient();
  const setSnapshot = useAuthStore((state) => state.setSnapshot);

  return useMutation({
    mutationFn: (draft: OnboardingDraft) => saveOnboardingDraft(draft),
    onSuccess: (snapshot) => {
      setSnapshot(snapshot);
      void queryClient.invalidateQueries({ queryKey: ["onboarding"] });
    },
  });
}
