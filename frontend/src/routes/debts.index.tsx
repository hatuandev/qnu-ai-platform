import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { DebtsPage } from "@/features/invoices/debts-page";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.string().catch(""),
  academicYearId: z.string().optional().catch(undefined),
  roomId: z.string().optional().catch(undefined),
});

export const Route = createFileRoute("/debts/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: DebtsIndex,
});

function DebtsIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  if (!can("ktx.debts.view")) return <AccessDenied />;
  return (
    <DebtsPage
      search={search}
      onSearch={(changes) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
