import { createFileRoute, Navigate } from "@tanstack/react-router";
import { useAuth } from "@/app/auth";
import { AccessDenied } from "@/components/admin/access-denied";
import { StudentDetail } from "@/features/students/student-detail";
import { isStudentAccount } from "@/rbac/backend-role-map";
import { useRbac } from "@/rbac/context";

export const Route = createFileRoute("/students/$studentId")({
  component: StudentDetailRoute,
});

function StudentDetailRoute() {
  const { studentId } = Route.useParams();
  const { can } = useRbac();
  const { user } = useAuth();

  if (isStudentAccount(user?.userType)) {
    return <Navigate to="/dashboard" replace />;
  }
  if (!can("ktx.students.view")) return <AccessDenied />;
  return <StudentDetail studentId={studentId} />;
}
