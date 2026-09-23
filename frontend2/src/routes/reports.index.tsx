import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { ReportsPage } from "@/features/reports/reports-page";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  academicYearId: z.string().optional().catch(undefined),
});

export const Route = createFileRoute("/reports/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: ReportsIndex,
});

function ReportsIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();

  if (!can("ktx.reports.view")) return <AccessDenied />;

  return (
    <ReportsPage
      academicYearId={search.academicYearId}
      onAcademicYearChange={(academicYearId) =>
        void navigate({ search: { academicYearId } })
      }
    />
  );
}
