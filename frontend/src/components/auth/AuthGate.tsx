import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getPostLoginRoute, useAuthStore } from "@/stores/authStore";

function AuthLoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-black text-white">
      <div className="rounded-full border border-cyan-400/20 bg-white/5 px-5 py-3 text-sm tracking-[0.2em] text-cyan-200">
        Restoring session...
      </div>
    </div>
  );
}

export function ProtectedRoute() {
  const location = useLocation();
  const initialized = useAuthStore((state) => state.initialized);
  const status = useAuthStore((state) => state.status);

  if (!initialized || status === "loading") {
    return <AuthLoadingScreen />;
  }

  if (status !== "authenticated") {
    const redirectPath = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate replace to={`/login?redirect=${encodeURIComponent(redirectPath)}`} />;
  }

  return <Outlet />;
}

export function PublicOnlyRoute() {
  const initialized = useAuthStore((state) => state.initialized);
  const snapshot = useAuthStore((state) => state.snapshot);
  const status = useAuthStore((state) => state.status);

  if (!initialized || status === "loading") {
    return <AuthLoadingScreen />;
  }

  if (status === "authenticated") {
    return <Navigate replace to={getPostLoginRoute(snapshot)} />;
  }

  return <Outlet />;
}
