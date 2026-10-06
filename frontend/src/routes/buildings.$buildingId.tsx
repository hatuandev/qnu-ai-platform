import { createFileRoute } from "@tanstack/react-router";
import { BuildingDetail } from "@/features/buildings/building-detail";

export const Route = createFileRoute("/buildings/$buildingId")({
  component: BuildingDetailRoute,
});

function BuildingDetailRoute() {
  const { buildingId } = Route.useParams();
  return <BuildingDetail id={buildingId} />;
}
