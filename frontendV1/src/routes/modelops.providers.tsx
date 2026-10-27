import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/modelops/providers")({
  component: () => <Outlet />,
});
