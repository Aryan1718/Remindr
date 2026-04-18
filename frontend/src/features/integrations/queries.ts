import { useQuery } from "@tanstack/react-query";
import { listIntegrations } from "@/api/integrations";

export function useIntegrationsQuery() {
  return useQuery({
    queryKey: ["integrations"],
    queryFn: listIntegrations,
  });
}
