import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { PageHeader } from "@/components/admin/page-header";
import { AssignmentsPage } from "@/features/assignments/assignments-page";
import type { AssignmentStatus } from "@/features/assignments/types";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  periodId: z.string().optional().catch(undefined),
  buildingId: z.string().optional().catch(undefined),
  floorId: z.string().optional().catch(undefined),
  roomId: z.string().optional().catch(undefined),
  status: z
    .enum(["selected", "assigned", "checked_in", "cancelled"])
    .optional()
    .catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/assignments/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: AssignmentsIndex,
});

function AssignmentsIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();

  if (!can("ktx.assignments.view")) return <AccessDenied />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Ký túc xá / Vận hành"
        title="Xếp phòng"
        description="Gán hồ sơ đã duyệt vào phòng và theo dõi trạng thái chốt chỗ ở."
      />
      <AssignmentsPage
        search={{
          q: String(search.q),
          registrationPeriodId: search.periodId,
          buildingId: search.buildingId,
          floorId: search.floorId,
          roomId: search.roomId,
          status: search.status as AssignmentStatus | undefined,
          page: search.page,
          pageSize: search.pageSize,
        }}
        onSearch={(changes) =>
          void navigate({
            search: (previous) => ({
              ...previous,
              ...changes,
              periodId:
                changes.registrationPeriodId === undefined
                  ? previous.periodId
                  : changes.registrationPeriodId,
              buildingId:
                changes.buildingId === undefined
                  ? previous.buildingId
                  : changes.buildingId,
              floorId:
                changes.floorId === undefined
                  ? previous.floorId
                  : changes.floorId,
              roomId:
                changes.roomId === undefined ? previous.roomId : changes.roomId,
            }),
          })
        }
        canCreate={can("ktx.assignments.create")}
        canFinalize={can("ktx.assignments.create")}
        canCancel={can("ktx.assignments.cancel")}
      />
    </div>
  );
}
