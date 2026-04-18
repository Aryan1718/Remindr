import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveSettings } from "@/api/settings";
import type { ProfileSettings } from "@/types/domain";

export function useSaveSettingsMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (settings: ProfileSettings) => saveSettings(settings),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
