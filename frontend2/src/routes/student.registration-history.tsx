import { createFileRoute } from "@tanstack/react-router";
import { AccessDenied } from "@/components/admin/access-denied";
import { StudentRegistrationHistoryPage } from "@/features/student/student-registration-history-page";
import { useRbac } from "@/rbac/context";

export const Route = createFileRoute("/student/registration-history")({
  component: RegistrationHistoryRoute,
});

function RegistrationHistoryRoute() {
  const { can } = useRbac();
  return can("ktx.applications.view") ? (
    <StudentRegistrationHistoryPage />
  ) : (
    <AccessDenied />
  );
}
