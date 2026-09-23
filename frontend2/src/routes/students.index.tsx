import { createFileRoute, Navigate } from "@tanstack/react-router";
import { z } from "zod";
import { useAuth } from "@/app/auth";
import { AccessDenied } from "@/components/admin/access-denied";
import {
  StudentsPage,
  type StudentsSearch,
} from "@/features/students/students-page";
import { isStudentAccount } from "@/rbac/backend-role-map";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.string().catch(""),
  faculty: z.string().catch(""),
  status: z
    .enum(["studying", "paused", "graduated", "unknown", "inactive"])
    .optional()
    .catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
  create: z.coerce.boolean().catch(false),
});

export const Route = createFileRoute("/students/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: StudentsIndex,
});

function StudentsIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  const { user } = useAuth();

  if (isStudentAccount(user?.userType)) {
    return <Navigate to="/dashboard" replace />;
  }
  if (!can("ktx.students.view")) return <AccessDenied />;

  return (
    <StudentsPage
      search={search as StudentsSearch}
      onSearchChange={(changes: Partial<StudentsSearch>) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
