import { createFileRoute } from "@tanstack/react-router";
import { ResidenceDetail } from "@/features/residences/residence-detail";
export const Route = createFileRoute("/residences/$residenceId")({
  component: () => (
    <ResidenceDetail residenceId={Route.useParams().residenceId} />
  ),
});
