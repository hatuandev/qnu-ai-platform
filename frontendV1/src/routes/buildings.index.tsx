import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AlertTriangle, Plus, RefreshCw } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import {
  useBuildingsQuery,
  useDeactivateBuilding,
  useDeleteBuilding,
} from "@/features/buildings/api";
import { BuildingFormDialog } from "@/features/buildings/building-form-dialog";
import { BuildingsTable } from "@/features/buildings/buildings-table";
import type { Building } from "@/features/buildings/types";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.string().catch(""),
  status: z.enum(["active", "inactive"]).optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/buildings/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: BuildingsPage,
});

type FormState = { mode: "create" | "edit"; building: Building | null } | null;

function BuildingsPage() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/buildings/" });
  const { can } = useRbac();
  const [formState, setFormState] = useState<FormState>(null);
  const [pendingDeactivate, setPendingDeactivate] = useState<Building | null>(
    null,
  );
  const [pendingDelete, setPendingDelete] = useState<Building | null>(null);
  const deactivate = useDeactivateBuilding();
  const deleteBuilding = useDeleteBuilding();
  const params = useMemo(
    () => ({
      searchCodeOrName: search.q.trim() || undefined,
      status: search.status,
      page: search.page,
      pageSize: search.pageSize,
    }),
    [search.page, search.pageSize, search.q, search.status],
  );
  const query = useBuildingsQuery(params);
  const updateSearch = useCallback(
    (changes: Partial<typeof search>) =>
      void navigate({ search: (previous) => ({ ...previous, ...changes }) }),
    [navigate],
  );
  const hasActiveFilters = Boolean(search.q || search.status);

  if (!can("ktx.buildings.view")) return <AccessDenied />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="KÝ TÚC XÁ / DANH MỤC"
        title="Tòa nhà ký túc xá"
        description="Quản lý danh mục tòa nhà ký túc xá, số tầng, số phòng và trạng thái sử dụng."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw
                className={cn("size-3.5", query.isFetching && "animate-spin")}
              />
              <span>Làm mới</span>
            </Button>
            {can("ktx.buildings.create") ? (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setFormState({ mode: "create", building: null })}
              >
                <Plus className="size-3.5" />
                <span>Thêm tòa nhà</span>
              </Button>
            ) : null}
          </div>
        }
      />
      <BuildingsTable
        data={query.data?.items ?? []}
        page={search.page}
        pageSize={search.pageSize}
        total={query.data?.total ?? 0}
        totalPages={query.data?.totalPages ?? 1}
        isLoading={query.isLoading}
        isError={query.isError}
        errorMessage={
          query.error instanceof Error ? query.error.message : undefined
        }
        hasBuildings={(query.data?.total ?? 0) > 0}
        hasActiveFilters={hasActiveFilters}
        query={search.q}
        status={search.status}
        canUpdate={can("ktx.buildings.update")}
        canDeactivate={can("ktx.buildings.deactivate")}
        canDelete={can("ktx.buildings.deactivate")}
        onRetry={() => void query.refetch()}
        onQueryChange={(q) => updateSearch({ q, page: 1 })}
        onStatusChange={(status) => updateSearch({ status, page: 1 })}
        onResetFilters={() =>
          updateSearch({ q: "", status: undefined, page: 1 })
        }
        onPageChange={(page) => updateSearch({ page })}
        onPageSizeChange={(pageSize) => updateSearch({ pageSize, page: 1 })}
        onView={(building) =>
          void navigate({
            to: "/buildings/$buildingId",
            params: { buildingId: building.id },
          })
        }
        onEdit={(building) => setFormState({ mode: "edit", building })}
        onDeactivate={setPendingDeactivate}
        onDelete={setPendingDelete}
      />
      <BuildingFormDialog
        key={`${formState?.mode ?? "closed"}-${formState?.building?.id ?? "new"}`}
        open={Boolean(formState)}
        onOpenChange={(open) => {
          if (!open) setFormState(null);
        }}
        building={formState?.building}
      />

      {/* Dialog xác nhận Ngừng sử dụng tòa nhà */}
      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        onOpenChange={(open) => {
          if (!open && !deactivate.isPending) setPendingDeactivate(null);
        }}
        title="Ngừng sử dụng tòa nhà?"
        description={
          pendingDeactivate
            ? `Bạn có chắc muốn chuyển tòa nhà “${pendingDeactivate.name}” (${pendingDeactivate.code}) sang trạng thái Ngừng sử dụng? (Hệ thống sẽ từ chối nếu tòa nhà đã có tầng hoặc phòng).`
            : ""
        }
        confirmLabel="Ngừng sử dụng"
        isLoading={deactivate.isPending}
        onConfirm={() => {
          if (!pendingDeactivate) return;
          void deactivate
            .mutateAsync(pendingDeactivate.id)
            .then(() => {
              setPendingDeactivate(null);
              toast.success("Đã chuyển tòa nhà sang trạng thái ngừng sử dụng.");
            })
            .catch((error: unknown) => {
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể ngừng sử dụng tòa nhà.",
              );
            });
        }}
      />

      {/* Dialog xác nhận Xóa tòa nhà */}
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => {
          if (!open && !deleteBuilding.isPending) setPendingDelete(null);
        }}
        title="Xác nhận xóa tòa nhà?"
        description={
          pendingDelete ? (
            <div className="space-y-3 pt-1">
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-destructive">
                <div className="flex items-center gap-2 font-semibold text-sm">
                  <AlertTriangle className="size-4 shrink-0 text-destructive" />
                  <span>Cảnh báo cấp cao nhất</span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-destructive/90">
                  Tòa nhà là cấp danh mục cao nhất trong quản lý cơ sở vật chất.
                  Hành động này sẽ{" "}
                  <strong>xóa vĩnh viễn toàn bộ các dữ liệu trực thuộc</strong>!
                </p>
              </div>

              <div className="rounded-md border bg-muted/40 p-3 text-xs space-y-1.5">
                <p className="font-medium text-foreground">
                  Dữ liệu trực thuộc tòa nhà “
                  <span className="font-semibold">{pendingDelete.name}</span>”
                  sẽ bị xóa:
                </p>
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground ml-1">
                  <li>
                    <strong>{pendingDelete.floorCount} tầng</strong> trực thuộc
                  </li>
                  <li>
                    <strong>{pendingDelete.roomCount} phòng</strong> trực thuộc
                  </li>
                  <li>
                    <strong>Tất cả chỗ</strong> thuộc các phòng trong tòa nhà
                  </li>
                </ul>
              </div>

              <p className="text-xs text-muted-foreground italic">
                * Lưu ý: Hệ thống sẽ từ chối nếu có sinh viên đang lưu trú, có
                lịch sử phân phòng hoặc phòng đang trong đợt đăng ký.
              </p>
            </div>
          ) : (
            ""
          )
        }
        confirmLabel="Xác nhận xóa tất cả"
        confirmVariant="destructive"
        isLoading={deleteBuilding.isPending}
        onConfirm={() => {
          if (!pendingDelete) return;
          void deleteBuilding
            .mutateAsync(pendingDelete.id)
            .then(() => {
              setPendingDelete(null);
              toast.success(
                "Đã xóa tòa nhà và toàn bộ dữ liệu liên quan thành công.",
              );
            })
            .catch((error: unknown) => {
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể xóa tòa nhà.",
              );
            });
        }}
      />
    </div>
  );
}
