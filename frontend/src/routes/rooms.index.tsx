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
  useDeleteRoom,
  useRoomsQuery,
  useUpdateRoomStatus,
} from "@/features/rooms/api";
import { RoomFormDialog } from "@/features/rooms/room-form-dialog";
import { RoomsTable } from "@/features/rooms/rooms-table";
import type { Room, RoomStatus } from "@/features/rooms/types";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.string().catch(""),
  buildingId: z.string().optional().catch(undefined),
  floorId: z.string().optional().catch(undefined),
  roomTypeId: z.string().optional().catch(undefined),
  status: z
    .enum(["available", "full", "maintenance", "inactive"])
    .optional()
    .catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/rooms/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: RoomsPage,
});

function RoomsPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  const [formState, setFormState] = useState<"create" | undefined>();
  const [pendingDeactivate, setPendingDeactivate] = useState<Room | null>(null);
  const [pendingDeleteRooms, setPendingDeleteRooms] = useState<Room[] | null>(
    null,
  );
  const deactivate = useUpdateRoomStatus();
  const deleteRoom = useDeleteRoom();
  const params = useMemo(
    () => ({
      searchCodeOrName: search.q.trim() || undefined,
      buildingId: search.buildingId,
      floorId: search.floorId,
      roomTypeId: search.roomTypeId,
      status: search.status,
      page: search.page,
      pageSize: search.pageSize,
    }),
    [
      search.buildingId,
      search.floorId,
      search.page,
      search.pageSize,
      search.q,
      search.roomTypeId,
      search.status,
    ],
  );
  const query = useRoomsQuery(params);
  const updateSearch = useCallback(
    (changes: Partial<typeof search>) =>
      void navigate({ search: (previous) => ({ ...previous, ...changes }) }),
    [navigate],
  );
  const hasActiveFilters = Boolean(
    search.q ||
      search.buildingId ||
      search.floorId ||
      search.roomTypeId ||
      search.status,
  );

  if (!can("ktx.rooms.view")) return <AccessDenied />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="KÝ TÚC XÁ / CƠ SỞ VẬT CHẤT"
        title="Phòng ở ký túc xá"
        description="Quản lý phòng theo tòa nhà, tầng, loại phòng, sức chứa và tình trạng vận hành."
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
            {can("ktx.rooms.create") ? (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setFormState("create")}
              >
                <Plus className="size-3.5" />
                <span>Thêm phòng</span>
              </Button>
            ) : null}
          </div>
        }
      />
      <RoomsTable
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
        hasRooms={(query.data?.total ?? 0) > 0}
        hasActiveFilters={hasActiveFilters}
        query={search.q}
        buildingId={search.buildingId}
        floorId={search.floorId}
        roomTypeId={search.roomTypeId}
        status={search.status as RoomStatus | undefined}
        onRetry={() => void query.refetch()}
        onQueryChange={(q) => updateSearch({ q, page: 1 })}
        onBuildingChange={(buildingId) =>
          updateSearch({ buildingId, floorId: undefined, page: 1 })
        }
        onFloorChange={(floorId) => updateSearch({ floorId, page: 1 })}
        onRoomTypeChange={(roomTypeId) => updateSearch({ roomTypeId, page: 1 })}
        onStatusChange={(status) => updateSearch({ status, page: 1 })}
        onResetFilters={() =>
          updateSearch({
            q: "",
            buildingId: undefined,
            floorId: undefined,
            roomTypeId: undefined,
            status: undefined,
            page: 1,
          })
        }
        onPageChange={(page) => updateSearch({ page })}
        onPageSizeChange={(pageSize) => updateSearch({ pageSize, page: 1 })}
        canUpdate={can("ktx.rooms.update")}
        canDeactivate={can("ktx.rooms.delete")}
        canDelete={can("ktx.rooms.delete")}
        onView={(room) =>
          void navigate({
            to: "/rooms/$roomId",
            params: { roomId: room.id },
            search: { edit: false },
          })
        }
        onEdit={(room) =>
          void navigate({
            to: "/rooms/$roomId",
            params: { roomId: room.id },
            search: { edit: true },
          })
        }
        onDeactivate={setPendingDeactivate}
        onDelete={(room) => setPendingDeleteRooms([room])}
        onDeleteBatch={(rooms) => setPendingDeleteRooms(rooms)}
      />
      <RoomFormDialog
        key={formState ?? "closed"}
        open={Boolean(formState)}
        onOpenChange={(open) => {
          if (!open) setFormState(undefined);
        }}
        room={formState === "create" ? null : undefined}
      />

      {/* Dialog xác nhận Ngừng sử dụng phòng */}
      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        onOpenChange={(open) => {
          if (!open && !deactivate.isPending) setPendingDeactivate(null);
        }}
        title="Ngừng sử dụng phòng?"
        description={
          pendingDeactivate
            ? `Phòng “${pendingDeactivate.name}” (${pendingDeactivate.code}) sẽ được chuyển sang trạng thái ngừng sử dụng. Dữ liệu phòng và lịch sử cư trú vẫn được giữ lại.`
            : ""
        }
        confirmLabel="Ngừng sử dụng"
        isLoading={deactivate.isPending}
        onConfirm={() => {
          if (!pendingDeactivate) return;
          void deactivate
            .mutateAsync({ id: pendingDeactivate.id, status: "inactive" })
            .then(() => {
              setPendingDeactivate(null);
              toast.success("Đã chuyển phòng sang trạng thái ngừng sử dụng.");
            })
            .catch((error: unknown) => {
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể ngừng sử dụng phòng.",
              );
            });
        }}
      />

      {/* Dialog xác nhận Xóa phòng */}
      <ConfirmDialog
        open={Boolean(pendingDeleteRooms && pendingDeleteRooms.length > 0)}
        onOpenChange={(open) => {
          if (!open && !deleteRoom.isPending) setPendingDeleteRooms(null);
        }}
        title={
          pendingDeleteRooms && pendingDeleteRooms.length > 1
            ? `Xác nhận xóa ${pendingDeleteRooms.length} phòng đã chọn?`
            : "Xác nhận xóa phòng?"
        }
        description={
          pendingDeleteRooms && pendingDeleteRooms.length > 0
            ? `Bạn có chắc muốn xóa ${pendingDeleteRooms.length === 1 ? `phòng “${pendingDeleteRooms[0].name}” (${pendingDeleteRooms[0].code})` : `${pendingDeleteRooms.length} phòng đã chọn`}? Cấu hình mức phí riêng của phòng cũng sẽ bị xóa. Hệ thống sẽ từ chối nếu đã có dữ liệu phân phòng, cư trú hoặc hóa đơn.`
            : ""
        }
        confirmLabel={
          pendingDeleteRooms && pendingDeleteRooms.length > 1
            ? `Xóa ${pendingDeleteRooms.length} phòng`
            : "Xóa phòng"
        }
        confirmVariant="destructive"
        isLoading={deleteRoom.isPending}
        onConfirm={() => {
          if (!pendingDeleteRooms || pendingDeleteRooms.length === 0) return;
          const count = pendingDeleteRooms.length;
          void Promise.all(
            pendingDeleteRooms.map((r) => deleteRoom.mutateAsync(r.id)),
          )
            .then(() => {
              setPendingDeleteRooms(null);
              toast.success(
                count === 1
                  ? "Đã xóa phòng thành công."
                  : `Đã xóa ${count} phòng thành công.`,
              );
            })
            .catch((error: unknown) => {
              toast.error(
                error instanceof Error ? error.message : "Không thể xóa phòng.",
              );
            });
        }}
      />
    </div>
  );
}
