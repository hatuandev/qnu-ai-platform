import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { useAuth } from "@/app/auth";
import { DashboardPage as DashboardFeaturePage } from "@/features/dashboard/dashboard-page";
import { StudentDashboardPage } from "@/features/student/student-dashboard-page";
import { isStudentAccount } from "@/rbac/backend-role-map";

const searchSchema = z.object({});

export const Route = createFileRoute("/dashboard")({
  validateSearch: (search) => searchSchema.parse(search),
  component: DashboardRoute,
});

function DashboardRoute() {
  const { user } = useAuth();
  return isStudentAccount(user?.userType) ? (
    <StudentDashboardPage />
  ) : (
    <DashboardFeaturePage />
  );
}
