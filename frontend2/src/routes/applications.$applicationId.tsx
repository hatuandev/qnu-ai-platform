import { createFileRoute } from "@tanstack/react-router";
import { ApplicationDetail } from "@/features/applications/application-detail";
export const Route = createFileRoute("/applications/$applicationId")({
  component: () => (
    <ApplicationDetail applicationId={Route.useParams().applicationId} />
  ),
});
