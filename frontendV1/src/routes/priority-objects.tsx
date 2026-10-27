import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/priority-objects")({
  component: () => <Outlet />,
});
