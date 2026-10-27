import { createFileRoute, Outlet } from "@tanstack/react-router";
export const Route = createFileRoute("/academic-years")({
  component: () => <Outlet />,
});
