import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { ResidencesPage } from "@/features/residences/residences-page";
import type { ResidenceStatus } from "@/features/residences/types";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  status: z
    .enum(["active", "extended", "checked_out", "cancelled"])
    .optional()
    .catch(undefined),
  buildingId: z.string().optional().catch(undefined),
  floorId: z.string().optional().catch(undefined),
  roomId: z.string().optional().catch(undefined),
  registrationPeriodId: z.string().optional().catch(undefined),
  academicYearId: z.string().optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/residences/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: ResidencesIndex,
});

function ResidencesIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();

  if (!can("ktx.residences.view")) return <AccessDenied />;

  return (
    <ResidencesPage
      search={{
        q: String(search.q),
        status: search.status as ResidenceStatus | undefined,
        buildingId: search.buildingId,
        floorId: search.floorId,
        roomId: search.roomId,
        registrationPeriodId: search.registrationPeriodId,
        academicYearId: search.academicYearId,
        page: search.page,
        pageSize: search.pageSize,
      }}
      onSearch={(changes) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
