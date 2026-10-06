import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/document-types")({
  component: () => <Outlet />,
});
