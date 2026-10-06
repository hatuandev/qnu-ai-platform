import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/difficult-areas")({
  component: () => <Outlet />,
});
