import { createFileRoute } from "@tanstack/react-router";
import { AccessDenied } from "@/components/admin/access-denied";
import { StudentRegistrationPage } from "@/features/student/student-registration-page";
import { useRbac } from "@/rbac/context";

export const Route = createFileRoute("/student/register")({
  component: StudentRegistrationRoute,
});

function StudentRegistrationRoute() {
  const { can } = useRbac();
  return can("ktx.applications.submit") ? (
    <StudentRegistrationPage />
  ) : (
    <AccessDenied />
  );
}
