import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/residence-contracts")({
  component: () => <Outlet />,
});
