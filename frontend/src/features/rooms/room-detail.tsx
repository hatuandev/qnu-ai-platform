import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  Building2,
  DoorClosed,
  Pencil,
  Trash2,
  UserCheck,
  Users,
  Users2,
  Wrench,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRoomAssignmentsQuery } from "@/features/assignments/api";
import type { AssignmentStatus } from "@/features/assignments/types";
import {
  roomStatusLabels,
  useDeleteRoom,
  useRoomQuery,
} from "@/features/rooms/api";
import { RoomFormDialog } from "@/features/rooms/room-form-dialog";
import { formatDateTimeValue, formatDateValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const assignmentLabels: Record<AssignmentStatus, string> = {
  selected: "Đang giữ chỗ",
  assigned: "Đã xếp phòng",
  checked_in: "Đã nhận phòng",
  cancelled: "Đã hủy",
};

const assignmentVariants: Record<
  AssignmentStatus,
  "success" | "warning" | "destructive" | "secondary" | "outline"
> = {
  checked_in: "success",
  assigned: "outline",
  selected: "warning",
  cancelled: "secondary",
};

const assignmentDots: Record<AssignmentStatus, string> = {
  checked_in: "bg-emerald-500",
  assigned: "bg-blue-500",
  selected: "bg-amber-500",
  cancelled: "bg-muted-foreground/60",
};

export function RoomDetail({
  id,
  autoEdit = false,
}: {
  id: string;
  autoEdit?: boolean;
}) {
  const { can } = useRbac();
  const navigate = useNavigate();
  const query = useRoomQuery(id);
  const occupantsQuery = useRoomAssignmentsQuery(id);
  const deleteRoom = useDeleteRoom();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const autoEditApplied = useRef(false);
  const canEdit = can("ktx.rooms.update");

  useEffect(() => {
    if (autoEdit && canEdit && query.data && !autoEditApplied.current) {
      autoEditApplied.current = true;
      setEditOpen(true);
    }
  }, [autoEdit, canEdit, query.data]);

  if (!can("ktx.rooms.view")) return <AccessDenied />;
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
          icon={DoorClosed}
          title="Không thể tải thông tin phòng"
          description="Có thể phòng đã bị xóa hoặc xảy ra sự cố kết nối."
          action={{
            label: "Quay lại danh sách phòng",
            onClick: () =>
              void navigate({
                to: "/rooms",
                search: {
                  q: "",
                  buildingId: undefined,
                  floorId: undefined,
                  roomTypeId: undefined,
                  status: undefined,
                  page: 1,
                  pageSize: 10,
                },
              }),
          }}
        />
      </div>
    );
  }

  const room = query.data;
  const occupants = (occupantsQuery.data ?? []).filter(
    (item) => item.status !== "cancelled",
  );
  const occupancyRate =
    room.operationalCapacity > 0
      ? Math.round((room.occupiedPlaces / room.operationalCapacity) * 100)
      : 0;

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / CƠ SỞ VẬT CHẤT / CHI TIẾT PHÒNG"
        title={room.name}
        description={`${room.code} · ${room.buildingName ? `${room.buildingName} · ` : ""}Tầng ${room.floorNumber} · Loại: ${room.roomTypeName}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              asChild
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
            >
              <Link
                to="/rooms"
                search={{
                  q: "",
                  buildingId: undefined,
                  floorId: undefined,
                  roomTypeId: undefined,
                  status: undefined,
                  page: 1,
                  pageSize: 10,
                }}
              >
                <ArrowLeft className="size-3.5" />
                <span>Danh sách phòng</span>
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
            {can("ktx.rooms.delete") ? (
              <Button
                variant="destructive"
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 className="size-3.5" />
                <span>Xóa phòng</span>
              </Button>
            ) : null}
          </div>
        }
      />

      {/* 2. Top 4 KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Users}
            label="Sức chứa thiết kế"
            value={`${room.capacity} chỗ`}
            helper="Quy chuẩn thiết kế ban đầu"
          />
          <KpiMetric
            icon={Wrench}
            label="Sức chứa vận hành"
            value={`${room.operationalCapacity} chỗ`}
            helper="Chỗ ở thực tế được phép dùng"
          />
          <KpiMetric
            icon={UserCheck}
            label="Đang sử dụng"
            value={`${room.occupiedPlaces} chỗ`}
            trend="positive"
            helper={`Tỷ lệ lấp đầy đạt ${occupancyRate}%`}
          />
          <KpiMetric
            icon={DoorClosed}
            label="Chỗ còn trống"
            value={`${room.availablePlaces} chỗ`}
            trend={room.availablePlaces > 0 ? "positive" : "neutral"}
            helper="Sẵn sàng tiếp nhận sinh viên"
          />
        </CardContent>
      </Card>

      {/* 3. Detailed Room Info Card */}
      <Card className="border bg-card shadow-xs">
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Building2 className="size-4 text-primary" />
            <span>Thông tin chi tiết phòng</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5 pt-4 sm:grid-cols-2 lg:grid-cols-3">
          <InfoItem label="Mã phòng" value={room.code} isMono />
          <InfoItem label="Tên phòng" value={room.name} />
          <InfoItem label="Loại phòng" value={room.roomTypeName} />
          <InfoItem
            label="Tòa nhà"
            value={`${room.buildingCode}${room.buildingName ? ` · ${room.buildingName}` : ""}`}
          />
          <InfoItem label="Tầng" value={`Tầng ${room.floorNumber}`} />
          <InfoItem
            label="Trạng thái"
            value={
              <Badge
                variant={
                  room.status === "available"
                    ? "success"
                    : room.status === "full"
                      ? "warning"
                      : room.status === "maintenance"
                        ? "destructive"
                        : "secondary"
                }
                className="gap-1.5 font-medium px-2.5 py-0.5 text-xs mt-1"
              >
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    room.status === "available"
                      ? "bg-emerald-500"
                      : room.status === "full"
                        ? "bg-amber-500"
                        : room.status === "maintenance"
                          ? "bg-destructive"
                          : "bg-muted-foreground/60",
                  )}
                />
                {roomStatusLabels[room.status] || room.status}
              </Badge>
            }
          />
          <InfoItem label="Ghi chú" value={room.note || "Không có ghi chú"} />
          <InfoItem
            label="Cập nhật gần nhất"
            value={formatDateTimeValue(room.lastModified)}
          />
        </CardContent>
      </Card>

      {/* 4. Occupants in Room Card */}
      <Card className="border bg-card shadow-xs">
        <CardHeader className="pb-3 border-b">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Users2 className="size-4 text-primary" />
              <span>Sinh viên đang ở trong phòng ({occupants.length})</span>
            </CardTitle>
            <Badge variant="outline" className="text-xs font-mono">
              {room.occupiedPlaces}/{room.operationalCapacity} chỗ
            </Badge>
          </div>
          <p className="type-supporting text-xs text-muted-foreground mt-1">
            Danh sách sinh viên đang giữ chỗ, đã xếp phòng và đã nhận phòng thực
            tế.
          </p>
        </CardHeader>
        <CardContent className="p-0">
          {occupantsQuery.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-32 w-full rounded-lg" />
            </div>
          ) : occupants.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={Users}
                title="Chưa có sinh viên trong phòng"
                description="Phòng này hiện chưa có sinh viên đăng ký giữ chỗ hoặc cư trú."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40 hover:bg-muted/40">
                    <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                      Sinh viên
                    </TableHead>
                    <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                      Trạng thái
                    </TableHead>
                    <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                      Ngày xếp phòng
                    </TableHead>
                    <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                      Ghi chú
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {occupants.map((item) => (
                    <TableRow key={item.id} className="whitespace-nowrap">
                      <TableCell className="py-3">
                        <p className="font-semibold text-foreground text-sm">
                          {item.studentName}
                        </p>
                        <p className="font-mono text-xs text-muted-foreground">
                          {item.studentCode}
                        </p>
                      </TableCell>
                      <TableCell className="py-3">
                        <Badge
                          variant={assignmentVariants[item.status]}
                          className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
                        >
                          <span
                            className={cn(
                              "size-1.5 rounded-full",
                              assignmentDots[item.status],
                            )}
                          />
                          {assignmentLabels[item.status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="py-3 font-mono text-xs text-muted-foreground">
                        {formatDateValue(item.assignedAt)}
                      </TableCell>
                      <TableCell className="py-3 text-xs text-muted-foreground">
                        {item.note || "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 5. Dialogs */}
      <RoomFormDialog open={editOpen} onOpenChange={setEditOpen} room={room} />
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Xác nhận xóa phòng?"
        description={`Xóa phòng “${room.name}” (${room.code}) và cấu hình mức phí riêng của phòng. Hệ thống sẽ từ chối nếu phòng đã có dữ liệu phân phòng, cư trú hoặc hóa đơn.`}
        confirmLabel="Xóa phòng"
        confirmVariant="destructive"
        isLoading={deleteRoom.isPending}
        onConfirm={() =>
          void deleteRoom
            .mutateAsync(room.id)
            .then(() => {
              toast.success("Đã xóa phòng thành công.");
              void navigate({
                to: "/rooms",
                search: {
                  q: "",
                  buildingId: undefined,
                  floorId: undefined,
                  roomTypeId: undefined,
                  status: undefined,
                  page: 1,
                  pageSize: 10,
                },
              });
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error ? error.message : "Không thể xóa phòng.",
              ),
            )
        }
      />
    </div>
  );
}

function InfoItem({
  label,
  value,
  isMono = false,
}: {
  label: string;
  value: React.ReactNode;
  isMono?: boolean;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {label}
      </p>
      {typeof value === "string" ? (
        <p
          className={cn(
            "text-sm font-medium text-foreground",
            isMono && "font-mono font-semibold",
          )}
        >
          {value}
        </p>
      ) : (
        value
      )}
    </div>
  );
}
