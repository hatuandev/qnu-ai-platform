import { createFileRoute } from "@tanstack/react-router";
import { AssistantsPage } from "@/features/assistants/assistants-page";

export const Route = createFileRoute("/assistants/")({
  component: AssistantsIndexRoute,
});

function AssistantsIndexRoute() {
  return <AssistantsPage />;
}
