import { useEffect } from "react";
import type { PropsWithChildren } from "react";
import { useAuthStore } from "@/stores/authStore";

export function AuthBootstrap({ children }: PropsWithChildren) {
  const initialized = useAuthStore((state) => state.initialized);

  useEffect(() => {
    if (!initialized) {
      void useAuthStore.getState().initialize();
    }
  }, [initialized]);

  return <>{children}</>;
}
