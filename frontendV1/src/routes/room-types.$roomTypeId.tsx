import { createFileRoute } from "@tanstack/react-router";
import { RoomTypeDetail } from "@/features/room-types/room-type-detail";

export const Route = createFileRoute("/room-types/$roomTypeId")({
  component: () => <RoomTypeDetail id={Route.useParams().roomTypeId} />,
});
