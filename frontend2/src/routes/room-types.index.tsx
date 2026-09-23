import { createFileRoute } from "@tanstack/react-router";
import { Plus, RefreshCw } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import {
  useDeactivateRoomType,
  useDeleteRoomType,
  useRoomTypesQuery,
} from "@/features/room-types/api";
import { RoomTypeFormDialog } from "@/features/room-types/room-type-form-dialog";
import { RoomTypesTable } from "@/features/room-types/room-types-table";
import type { RoomType } from "@/features/room-types/types";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  isActive: z.enum(["active", "inactive"]).optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});
export const Route = createFileRoute("/room-types/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: RoomTypesPage,
});

function RoomTypesPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  const [formState, setFormState] = useState<RoomType | null | "create">();
  const [pendingDeactivate, setPendingDeactivate] = useState<RoomType | null>(
    null,
  );
  const [pendingDelete, setPendingDelete] = useState<RoomType | null>(null);
  const deactivate = useDeactivateRoomType();
  const deleteRoomType = useDeleteRoomType();
  const params = useMemo(
    () => ({
      searchCodeOrName: String(search.q).trim() || undefined,
      isActive:
        search.isActive === undefined
          ? undefined
          : search.isActive === "active",
      page: search.page,
      pageSize: search.pageSize,
    }),
    [search.isActive, search.page, search.pageSize, search.q],
  );
  const query = useRoomTypesQuery(params);
  const updateSearch = useCallback(
    (changes: Partial<typeof search>) =>
      void navigate({ search: (previous) => ({ ...previous, ...changes }) }),
    [navigate],
  );
  if (!can("ktx.room_types.view")) return <AccessDenied />;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="KÝ TÚC XÁ / DANH MỤC"
        title="Loại phòng"
        description="Quản lý sức chứa và trạng thái sử dụng của các loại phòng. Mức phí được cấu hình riêng theo năm học hoặc theo phòng."
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
            {can("ktx.room_types.create") ? (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setFormState("create")}
              >
                <Plus className="size-3.5" />
                <span>Thêm loại phòng</span>
              </Button>
            ) : null}
          </div>
        }
      />
      <RoomTypesTable
        data={query.data?.items ?? []}
        total={query.data?.total ?? 0}
        totalPages={query.data?.totalPages ?? 1}
        page={search.page}
        pageSize={search.pageSize}
        isLoading={query.isLoading}
        isError={query.isError}
        errorMessage={
          query.error instanceof Error ? query.error.message : undefined
        }
        hasRoomTypes={(query.data?.total ?? 0) > 0}
        hasActiveFilters={Boolean(search.q || search.isActive)}
        query={String(search.q)}
        isActive={params.isActive}
        canUpdate={can("ktx.room_types.update")}
        canDeactivate={can("ktx.room_types.deactivate")}
        canDelete={can("ktx.room_types.deactivate")}
        onRetry={() => void query.refetch()}
        onQueryChange={(q) => updateSearch({ q, page: 1 })}
        onActiveChange={(isActive) =>
          updateSearch({
            isActive:
              isActive === undefined
                ? undefined
                : isActive
                  ? "active"
                  : "inactive",
            page: 1,
          })
        }
        onResetFilters={() =>
          updateSearch({ q: "", isActive: undefined, page: 1 })
        }
        onPageChange={(page) => updateSearch({ page })}
        onPageSizeChange={(pageSize) => updateSearch({ pageSize, page: 1 })}
        onView={(roomType) =>
          void navigate({
            to: "/room-types/$roomTypeId",
            params: { roomTypeId: roomType.id },
          })
        }
        onEdit={setFormState}
        onDeactivate={setPendingDeactivate}
        onDelete={setPendingDelete}
      />
      <RoomTypeFormDialog
        key={`${formState === "create" ? "create" : (formState?.id ?? "closed")}`}
        open={Boolean(formState)}
        onOpenChange={(open) => {
          if (!open) setFormState(undefined);
        }}
        roomType={formState === "create" ? null : formState}
      />

      {/* Dialog xác nhận Ngừng sử dụng loại phòng */}
      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        onOpenChange={(open) => {
          if (!open && !deactivate.isPending) setPendingDeactivate(null);
        }}
        title="Ngừng sử dụng loại phòng?"
        description={
          pendingDeactivate
            ? `Bạn có chắc muốn chuyển loại phòng “${pendingDeactivate.name}” (${pendingDeactivate.code}) sang trạng thái Ngừng sử dụng? Loại phòng này sẽ không còn được chọn cho phòng mới.`
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
              toast.success(
                "Đã chuyển loại phòng sang trạng thái ngừng sử dụng.",
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể ngừng sử dụng loại phòng.",
              ),
            );
        }}
      />

      {/* Dialog xác nhận Xóa loại phòng */}
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => {
          if (!open && !deleteRoomType.isPending) setPendingDelete(null);
        }}
        title="Xác nhận xóa loại phòng?"
        description={
          pendingDelete
            ? `Bạn có chắc chắn muốn xóa loại phòng “${pendingDelete.name}” (${pendingDelete.code}) không? Hệ thống sẽ từ chối nếu loại phòng đã có phòng đang sử dụng.`
            : ""
        }
        confirmLabel="Xóa loại phòng"
        confirmVariant="destructive"
        isLoading={deleteRoomType.isPending}
        onConfirm={() => {
          if (!pendingDelete) return;
          void deleteRoomType
            .mutateAsync(pendingDelete.id)
            .then(() => {
              setPendingDelete(null);
              toast.success("Đã xóa loại phòng thành công.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể xóa loại phòng.",
              ),
            );
        }}
      />
    </div>
  );
}
