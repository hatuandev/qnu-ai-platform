import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { RoomDetail } from "@/features/rooms/room-detail";

export const Route = createFileRoute("/rooms/$roomId")({
  validateSearch: z.object({ edit: z.coerce.boolean().catch(false) }),
  component: () => (
    <RoomDetail
      id={Route.useParams().roomId}
      autoEdit={Route.useSearch().edit}
    />
  ),
});
