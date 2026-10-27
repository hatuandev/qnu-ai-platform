import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { QnuDashboardPage } from "@/features/workspaces/qnu-dashboard-page";

const searchSchema = z.object({
  workspaceId: z.string().min(1).max(64).optional(),
  page: z.coerce.number().int().positive().catch(1).optional(),
});

export const Route = createFileRoute("/dashboard")({
  validateSearch: (search) => searchSchema.parse(search),
  component: DashboardRoute,
});

function DashboardRoute() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <QnuDashboardPage
      workspaceId={search.workspaceId}
      page={search.page ?? 1}
      onSearch={(patch) =>
        void navigate({ search: (prev) => ({ ...prev, ...patch }) })
      }
    />
  );
}
