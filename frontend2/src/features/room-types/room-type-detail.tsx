import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  BedDouble,
  CheckCircle2,
  DoorClosed,
  Pencil,
  Power,
  Users,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useDeactivateRoomType,
  useRoomTypeQuery,
} from "@/features/room-types/api";
import { RoomTypeFormDialog } from "@/features/room-types/room-type-form-dialog";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

export function RoomTypeDetail({ id }: { id: string }) {
  const { can } = useRbac();
  const navigate = useNavigate();
  const query = useRoomTypeQuery(id);
  const deactivate = useDeactivateRoomType();
  const [formOpen, setFormOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!can("ktx.room_types.view")) return <AccessDenied />;

  if (query.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20 w-full rounded-xl" />
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="p-8">
        <EmptyState
          icon={BedDouble}
          title="Không thể tải thông tin loại phòng"
          description={
            query.error instanceof Error
              ? query.error.message
              : "Loại phòng không tồn tại hoặc bạn không có quyền truy cập."
          }
          action={{
            label: "Quay lại danh sách loại phòng",
            onClick: () =>
              void navigate({
                to: "/room-types",
                search: { q: "", isActive: undefined, page: 1, pageSize: 10 },
              }),
          }}
        />
      </div>
    );
  }

  const roomType = query.data;

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / DANH MỤC / CHI TIẾT LOẠI PHÒNG"
        title={roomType.name}
        description={`Mã loại phòng: ${roomType.code} · Sức chứa: ${roomType.capacity} người/phòng · ${roomType.isActive ? "Đang sử dụng" : "Ngừng sử dụng"}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              asChild
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
            >
              <Link
                to="/room-types"
                search={{ q: "", isActive: undefined, page: 1, pageSize: 10 }}
              >
                <ArrowLeft className="size-3.5" />
                <span>Danh sách loại phòng</span>
              </Link>
            </Button>
            {can("ktx.room_types.update") ? (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setFormOpen(true)}
              >
                <Pencil className="size-3.5" />
                <span>Chỉnh sửa</span>
              </Button>
            ) : null}
            {can("ktx.room_types.deactivate") && roomType.isActive ? (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs font-semibold text-amber-600 hover:text-amber-700"
                onClick={() => setConfirmOpen(true)}
              >
                <Power className="size-3.5" />
                <span>Ngừng sử dụng</span>
              </Button>
            ) : null}
          </div>
        }
      />

      {/* 2. Top KPI Metrics Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Users}
            label="Sức chứa tiêu chuẩn"
            value={`${roomType.capacity} người`}
            helper="Số lượng sinh viên tối đa mỗi phòng"
          />
          <KpiMetric
            icon={DoorClosed}
            label="Số phòng áp dụng"
            value={`${roomType.roomCount} phòng`}
            helper="Tổng phòng đang sử dụng loại phòng này"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Trạng thái"
            value={roomType.isActive ? "Đang sử dụng" : "Ngừng sử dụng"}
            trend={roomType.isActive ? "positive" : "neutral"}
            helper={
              roomType.isActive
                ? "Loại phòng đang mở áp dụng"
                : "Loại phòng tạm ngưng áp dụng"
            }
          />
        </CardContent>
      </Card>

      {/* 3. Detailed Info Card */}
      <Card className="border bg-card shadow-xs">
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <BedDouble className="size-4 text-primary" />
            <span>Thông tin chi tiết loại phòng</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5 pt-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Mã loại phòng
            </p>
            <p className="text-sm font-semibold font-mono text-foreground">
              {roomType.code}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Tên loại phòng
            </p>
            <p className="text-sm font-medium text-foreground">
              {roomType.name}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Trạng thái
            </p>
            <Badge
              variant={roomType.isActive ? "success" : "secondary"}
              className="gap-1.5 font-medium px-2.5 py-0.5 text-xs mt-1"
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  roomType.isActive
                    ? "bg-emerald-500"
                    : "bg-muted-foreground/60",
                )}
              />
              {roomType.isActive ? "Đang sử dụng" : "Ngừng sử dụng"}
            </Badge>
          </div>
          <div className="space-y-1 sm:col-span-2 lg:col-span-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Mô tả
            </p>
            <p className="text-sm font-medium text-foreground whitespace-pre-wrap">
              {roomType.description || "Chưa có thông tin mô tả."}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 4. Dialogs */}
      <RoomTypeFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        roomType={roomType}
      />

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={(open) => {
          if (!open && !deactivate.isPending) setConfirmOpen(false);
        }}
        title="Ngừng sử dụng loại phòng?"
        description={`Bạn có chắc chắn muốn chuyển loại phòng “${roomType.name}” sang trạng thái ngừng sử dụng?`}
        confirmLabel="Ngừng sử dụng"
        confirmVariant="default"
        isLoading={deactivate.isPending}
        onConfirm={() =>
          void deactivate
            .mutateAsync(roomType.id)
            .then(() => {
              setConfirmOpen(false);
              toast.success("Đã ngừng sử dụng loại phòng.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể ngừng sử dụng loại phòng.",
              ),
            )
        }
      />
    </div>
  );
}
