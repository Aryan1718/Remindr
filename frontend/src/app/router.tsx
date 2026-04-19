import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { RoutePlaceholderPage } from "@/pages/RoutePlaceholderPage";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate replace to="/login" />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/onboarding",
    element: (
      <RoutePlaceholderPage
        description="The onboarding flow is being rebuilt from scratch around your new frontend direction."
        title="Onboarding"
      />
    ),
  },
  {
    path: "/dashboard",
    element: (
      <RoutePlaceholderPage
        description="The dashboard has been cleared so the next redesign can replace it cleanly."
        title="Dashboard"
      />
    ),
  },
  {
    path: "/tasks",
    element: (
      <RoutePlaceholderPage
        description="The task management UI is waiting for the new screen set."
        title="Tasks"
      />
    ),
  },
  {
    path: "/tasks/:taskId",
    element: (
      <RoutePlaceholderPage
        description="The task detail view has been removed until the new frontend is dropped in."
        title="Task detail"
      />
    ),
  },
  {
    path: "/goals",
    element: (
      <RoutePlaceholderPage
        description="The goals surface has been cleared for the redesign pass."
        title="Goals"
      />
    ),
  },
  {
    path: "/goals/:goalId",
    element: (
      <RoutePlaceholderPage
        description="The goal detail view will be rebuilt once you send the new design."
        title="Goal detail"
      />
    ),
  },
  {
    path: "/integrations",
    element: (
      <RoutePlaceholderPage
        description="The integrations screen is temporarily replaced with a clean placeholder."
        title="Integrations"
      />
    ),
  },
  {
    path: "/settings",
    element: (
      <RoutePlaceholderPage
        description="Settings is now out of the live surface until the new version is ready."
        title="Settings"
      />
    ),
  },
  {
    path: "/connectors/:provider/callback",
    element: (
      <RoutePlaceholderPage
        description="Connector callback handling will be rebuilt after the core screens are replaced."
        title="Connector callback"
      />
    ),
  },
  {
    path: "/welcome",
    element: <Navigate replace to="/login" />,
  },
  {
    path: "/start",
    element: <Navigate replace to="/onboarding" />,
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
