import { createFileRoute } from "@tanstack/react-router";
import { FloorDetail } from "@/features/floors/floor-detail";

export const Route = createFileRoute("/floors/$buildingId/$floorId")({
  component: () => {
    const { buildingId, floorId } = Route.useParams();
    return <FloorDetail buildingId={buildingId} floorId={floorId} />;
  },
});
