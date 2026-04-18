import { useQuery } from "@tanstack/react-query";
import { getSettings } from "@/api/settings";

export function useSettingsQuery() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });
}
