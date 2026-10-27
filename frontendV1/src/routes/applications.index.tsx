import { createFileRoute, Navigate } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { z } from "zod";
import { useAuth } from "@/app/auth";
import { AccessDenied } from "@/components/admin/access-denied";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { ApplicationsPage } from "@/features/applications/applications-page";
import { CreateApplicationDialog } from "@/features/applications/create-application-dialog";
import type { ApplicationStatus } from "@/features/applications/types";
import { isStudentAccount } from "@/rbac/backend-role-map";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  status: z
    .enum([
      "draft",
      "submitted",
      "need_supplement",
      "approved",
      "rejected",
      "cancelled",
      "assigned",
    ])
    .optional()
    .catch(undefined),
  registrationPeriodId: z.string().optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
  create: z.coerce.boolean().optional().catch(undefined),
});

export const Route = createFileRoute("/applications/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: ApplicationsIndex,
});

function ApplicationsIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  const { user } = useAuth();

  if (isStudentAccount(user?.userType)) {
    return <Navigate to="/student/registration-history" replace />;
  }
  if (!can("ktx.applications.view")) return <AccessDenied />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Ký túc xá / Vận hành"
        title="Hồ sơ đăng ký"
        description="Theo dõi hồ sơ đăng ký nội trú và các trạng thái xử lý."
        actions={
          can("ktx.applications.create") ? (
            <Button
              onClick={() =>
                void navigate({
                  search: (previous) => ({ ...previous, create: true }),
                })
              }
            >
              <Plus className="size-4 mr-1.5" />
              Thêm hồ sơ
            </Button>
          ) : null
        }
      />
      <ApplicationsPage
        search={{
          q: String(search.q),
          status: search.status as ApplicationStatus | undefined,
          registrationPeriodId: search.registrationPeriodId,
          page: search.page,
          pageSize: search.pageSize,
        }}
        onSearch={(changes) =>
          void navigate({
            search: (previous) => ({ ...previous, ...changes }),
          })
        }
        canReview={can("ktx.applications.review")}
      />
      <CreateApplicationDialog
        open={Boolean(search.create)}
        onOpenChange={(open) =>
          void navigate({
            search: (previous) => ({
              ...previous,
              create: open ? true : undefined,
            }),
          })
        }
      />
    </div>
  );
}
