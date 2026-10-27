import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  DoorClosed,
  Layers,
  MapPin,
  Pencil,
  Power,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/app/api/client";
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
  useBuildingQuery,
  useDeactivateBuilding,
  useDeleteBuilding,
} from "@/features/buildings/api";
import { BuildingFormDialog } from "@/features/buildings/building-form-dialog";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

export function BuildingDetail({ id }: { id: string }) {
  const { can } = useRbac();
  const navigate = useNavigate();
  const query = useBuildingQuery(id);
  const deactivate = useDeactivateBuilding();
  const deleteBuilding = useDeleteBuilding();
  const [editOpen, setEditOpen] = useState(false);
  const [deactivateOpen, setDeactivateOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (!can("ktx.buildings.view")) return <AccessDenied />;

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
    const notFound =
      query.error instanceof ApiError && query.error.status === 404;
    return (
      <div className="p-8">
        <EmptyState
          icon={Building2}
          title={
            notFound
              ? "Không tìm thấy tòa nhà"
              : "Không thể tải thông tin tòa nhà"
          }
          description={
            notFound
              ? "Tòa nhà có thể đã bị xóa hoặc bạn không còn quyền truy cập."
              : (query.error?.message ?? "Hãy kiểm tra lại kết nối mạng.")
          }
          action={{
            label: "Quay lại danh sách tòa nhà",
            onClick: () =>
              void navigate({
                to: "/buildings",
                search: { q: "", status: undefined, page: 1, pageSize: 10 },
              }),
          }}
        />
      </div>
    );
  }

  const building = query.data;
  const canEdit = can("ktx.buildings.update");
  const canDeactivate =
    can("ktx.buildings.deactivate") && building.status === "active";

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / DANH MỤC / CHI TIẾT TÒA NHÀ"
        title={building.name}
        description={`Mã tòa nhà: ${building.code} · ${building.address ? `${building.address} · ` : ""}${building.status === "active" ? "Đang hoạt động" : "Ngừng sử dụng"}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              asChild
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
            >
              <Link
                to="/buildings"
                search={{ q: "", status: undefined, page: 1, pageSize: 10 }}
              >
                <ArrowLeft className="size-3.5" />
                <span>Danh sách tòa nhà</span>
              </Link>
            </Button>
            {canEdit ? (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setEditOpen(true)}
              >
                <Pencil className="size-3.5" />
                <span>Chỉnh sửa</span>
              </Button>
            ) : null}
            {canDeactivate ? (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs font-semibold text-amber-600 hover:text-amber-700"
                onClick={() => setDeactivateOpen(true)}
              >
                <Power className="size-3.5" />
                <span>Ngừng sử dụng</span>
              </Button>
            ) : null}
            {can("ktx.buildings.deactivate") ? (
              <Button
                variant="destructive"
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 className="size-3.5" />
                <span>Xóa tòa nhà</span>
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
            label="Tổng số tầng"
            value={building.floorCount.toLocaleString("vi-VN")}
            helper="Số tầng được phân bổ cho tòa nhà"
          />
          <KpiMetric
            icon={DoorClosed}
            label="Tổng số phòng"
            value={building.roomCount.toLocaleString("vi-VN")}
            helper="Tổng số phòng thuộc các tầng"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Trạng thái"
            value={
              building.status === "active" ? "Đang hoạt động" : "Ngừng sử dụng"
            }
            trend={building.status === "active" ? "positive" : "neutral"}
            helper={
              building.status === "active"
                ? "Tòa nhà sẵn sàng phục vụ"
                : "Tòa nhà tạm ngưng hoạt động"
            }
          />
        </CardContent>
      </Card>

      {/* 3. Detailed Info Card */}
      <Card className="border bg-card shadow-xs">
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Building2 className="size-4 text-primary" />
            <span>Thông tin chi tiết tòa nhà</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5 pt-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Mã tòa nhà
            </p>
            <p className="text-sm font-semibold font-mono text-foreground">
              {building.code}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Tên tòa nhà
            </p>
            <p className="text-sm font-medium text-foreground">
              {building.name}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Trạng thái
            </p>
            <Badge
              variant={building.status === "active" ? "success" : "secondary"}
              className="gap-1.5 font-medium px-2.5 py-0.5 text-xs mt-1"
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  building.status === "active"
                    ? "bg-emerald-500"
                    : "bg-muted-foreground/60",
                )}
              />
              {building.status === "active"
                ? "Đang hoạt động"
                : "Ngừng sử dụng"}
            </Badge>
          </div>
          <div className="space-y-1 sm:col-span-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <MapPin className="size-3 text-muted-foreground" />
              Địa chỉ
            </p>
            <p className="text-sm font-medium text-foreground">
              {building.address || "Chưa cập nhật địa chỉ"}
            </p>
          </div>
          <div className="space-y-1 sm:col-span-2 lg:col-span-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Mô tả
            </p>
            <p className="text-sm font-medium text-foreground whitespace-pre-wrap">
              {building.description || "Chưa có thông tin mô tả."}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 4. Dialogs */}
      <BuildingFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        building={building}
      />

      <ConfirmDialog
        open={deactivateOpen}
        onOpenChange={(open) => {
          if (!open && !deactivate.isPending) setDeactivateOpen(false);
        }}
        title="Ngừng sử dụng tòa nhà?"
        description={`Bạn có chắc chắn muốn chuyển tòa nhà “${building.name}” sang trạng thái ngừng sử dụng?`}
        confirmLabel="Ngừng sử dụng"
        confirmVariant="default"
        isLoading={deactivate.isPending}
        onConfirm={() =>
          void deactivate
            .mutateAsync(building.id)
            .then(() => {
              setDeactivateOpen(false);
              toast.success("Đã ngừng sử dụng tòa nhà.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể ngừng sử dụng tòa nhà.",
              ),
            )
        }
      />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={(open) => {
          if (!open && !deleteBuilding.isPending) setDeleteOpen(false);
        }}
        title="Xác nhận xóa tòa nhà?"
        description={`Bạn có chắc chắn muốn xóa tòa nhà “${building.name}” (${building.code}) không? Hệ thống sẽ từ chối nếu tòa nhà còn phòng hoặc tầng đang hoạt động.`}
        confirmLabel="Xóa tòa nhà"
        confirmVariant="destructive"
        isLoading={deleteBuilding.isPending}
        onConfirm={() =>
          void deleteBuilding
            .mutateAsync(building.id)
            .then(() => {
              setDeleteOpen(false);
              toast.success("Đã xóa tòa nhà thành công.");
              void navigate({
                to: "/buildings",
                search: { q: "", status: undefined, page: 1, pageSize: 10 },
              });
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể xóa tòa nhà.",
              ),
            )
        }
      />
    </div>
  );
}
