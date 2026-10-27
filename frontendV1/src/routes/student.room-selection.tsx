import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { StudentRoomSelectionPage } from "@/features/student/room-selection-page";

const searchSchema = z.object({
  registrationPeriodId: z.string().optional().catch(undefined),
});

export const Route = createFileRoute("/student/room-selection")({
  validateSearch: (search) => searchSchema.parse(search),
  component: RoomSelectionRoute,
});

function RoomSelectionRoute() {
  const { registrationPeriodId } = Route.useSearch();
  return (
    <StudentRoomSelectionPage registrationPeriodId={registrationPeriodId} />
  );
}
