import { Navigate, Outlet, RouterProvider, createBrowserRouter } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { ConnectorCallbackPage } from "@/pages/ConnectorCallbackPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { GoalDetailPage } from "@/pages/GoalDetailPage";
import { GoalsPage } from "@/pages/GoalsPage";
import { IntegrationsPage } from "@/pages/IntegrationsPage";
import { LandingPage } from "@/pages/LandingPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SetupFlowPage } from "@/pages/SetupFlowPage";
import { TaskDetailPage } from "@/pages/TaskDetailPage";
import { TasksPage } from "@/pages/TasksPage";
import { useOnboardingQuery } from "@/features/onboarding/queries";

function Shell() {
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}

function ProtectedShell() {
  const { data } = useOnboardingQuery();

  if (!data) return null;
  if (!data.completed) {
    return <Navigate replace to="/start" />;
  }

  return <Shell />;
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <LandingPage />,
  },
  {
    path: "/start",
    element: <SetupFlowPage />,
  },
  {
    path: "/",
    element: <ProtectedShell />,
    children: [
      { path: "dashboard", element: <DashboardPage /> },
      { path: "tasks", element: <TasksPage /> },
      { path: "tasks/:taskId", element: <TaskDetailPage /> },
      { path: "goals", element: <GoalsPage /> },
      { path: "goals/:goalId", element: <GoalDetailPage /> },
      { path: "integrations", element: <IntegrationsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "connectors/:provider/callback", element: <ConnectorCallbackPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
