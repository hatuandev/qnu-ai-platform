import { createFileRoute } from "@tanstack/react-router";
import { AssignmentDetail } from "@/features/assignments/assignment-detail";
export const Route = createFileRoute("/assignments/$assignmentId")({
  component: () => (
    <AssignmentDetail assignmentId={Route.useParams().assignmentId} />
  ),
});
