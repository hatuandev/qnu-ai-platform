import { createFileRoute } from "@tanstack/react-router";
import { ModelOpsEventsPage } from "@/features/modelops/events-page";

export const Route = createFileRoute("/modelops/events")({
  component: ModelOpsEventsPage,
});
