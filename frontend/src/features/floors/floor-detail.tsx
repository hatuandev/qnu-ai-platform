import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  CheckCircle2,
  DoorClosed,
  Layers,
  Pencil,
  Trash2,
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
import { useDeleteFloor, useFloorQuery } from "@/features/floors/api";
import { FloorFormDialog } from "@/features/floors/floor-form-dialog";
import type { FloorStatus } from "@/features/floors/types";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const statusLabels: Record<FloorStatus, string> = {
  active: "Đang hoạt động",
  inactive: "Ngừng sử dụng",
};

export function FloorDetail({
  buildingId,
  floorId,
}: {
  buildingId: string;
  floorId: string;
}) {
  const { can } = useRbac();
  const navigate = useNavigate();
  const query = useFloorQuery(buildingId, floorId);
  const deleteFloor = useDeleteFloor();
  const [formOpen, setFormOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!can("ktx.floors.view")) return <AccessDenied />;

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
          icon={Layers}
          title="Không thể tải thông tin tầng"
          description={
            query.error instanceof Error
              ? query.error.message
              : "Tầng không tồn tại hoặc bạn không có quyền truy cập."
          }
          action={{
            label: "Quay lại danh sách tầng",
            onClick: () =>
              void navigate({
                to: "/floors",
                search: { buildingId, q: "", status: undefined },
              }),
          }}
        />
      </div>
    );
  }

  const floor = query.data;

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / DANH MỤC / CHI TIẾT TẦNG"
        title={floor.name}
        description={`Tầng ${floor.floorNumber} thuộc tòa nhà đang quản lý.`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              asChild
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
            >
              <Link
                to="/floors"
                search={{ buildingId, q: "", status: undefined }}
              >
                <ArrowLeft className="size-3.5" />
                <span>Danh sách tầng</span>
              </Link>
            </Button>
            {can("ktx.floors.update") ? (
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
            {can("ktx.floors.deactivate") ? (
              <Button
                variant="destructive"
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setConfirmOpen(true)}
              >
                <Trash2 className="size-3.5" />
                <span>Xóa tầng</span>
              </Button>
            ) : null}
          </div>
        }
      />

      {/* 2. Top KPI Metrics Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Layers}
            label="Số tầng"
            value={`Tầng ${floor.floorNumber}`}
            helper="Vị trí tầng trong tòa nhà"
          />
          <KpiMetric
            icon={DoorClosed}
            label="Số phòng"
            value={`${floor.roomCount} phòng`}
            helper="Tổng số phòng thuộc tầng"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Trạng thái"
            value={statusLabels[floor.status]}
            trend={floor.status === "active" ? "positive" : "neutral"}
            helper={
              floor.status === "active"
                ? "Tầng đang hoạt động đón sinh viên"
                : "Tầng tạm ngưng sử dụng"
            }
          />
        </CardContent>
      </Card>

      {/* 3. Detailed Info Card */}
      <Card className="border bg-card shadow-xs">
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Layers className="size-4 text-primary" />
            <span>Thông tin chi tiết tầng</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5 pt-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Tên tầng
            </p>
            <p className="text-sm font-semibold text-foreground">
              {floor.name}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Số tầng định danh
            </p>
            <p className="text-sm font-medium font-mono text-foreground">
              Tầng {floor.floorNumber}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Trạng thái
            </p>
            <Badge
              variant={floor.status === "active" ? "success" : "secondary"}
              className="gap-1.5 font-medium px-2.5 py-0.5 text-xs mt-1"
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  floor.status === "active"
                    ? "bg-emerald-500"
                    : "bg-muted-foreground/60",
                )}
              />
              {statusLabels[floor.status]}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* 4. Dialogs */}
      <FloorFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        buildingId={buildingId}
        floor={floor}
      />

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={(open) => {
          if (!open && !deleteFloor.isPending) setConfirmOpen(false);
        }}
        title="Xác nhận xóa tầng?"
        description={`Bạn có chắc chắn muốn xóa tầng “${floor.name}” (Tầng ${floor.floorNumber}) không? Hệ thống sẽ từ chối nếu tầng còn phòng đang hoạt động.`}
        confirmLabel="Xóa tầng"
        confirmVariant="destructive"
        isLoading={deleteFloor.isPending}
        onConfirm={() =>
          void deleteFloor
            .mutateAsync({ buildingId, id: floor.id })
            .then(() => {
              setConfirmOpen(false);
              toast.success("Đã xóa tầng thành công.");
              void navigate({
                to: "/floors",
                search: { buildingId, q: "", status: undefined },
              });
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error ? error.message : "Không thể xóa tầng.",
              ),
            )
        }
      />
    </div>
  );
}
