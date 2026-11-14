import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/assistants")({
  component: AssistantsLayout,
});

function AssistantsLayout() {
  return <Outlet />;
}
