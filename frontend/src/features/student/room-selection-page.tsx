import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  Banknote,
  Building2,
  CheckCircle2,
  Clock3,
  DoorOpen,
  LoaderCircle,
  UsersRound,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { AccessDenied } from "@/components/admin/access-denied";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useMyApplicationsQuery,
  useSelectStudentRoom,
  useStudentRoomSelectionQuery,
} from "@/features/student/api";
import type { StudentSelectableRoom } from "@/features/student/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { useRbac } from "@/rbac/context";

const currency = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

export function StudentRoomSelectionPage({
  registrationPeriodId,
}: {
  registrationPeriodId?: string;
}) {
  const { can } = useRbac();
  const applications = useMyApplicationsQuery();
  const selectedApplication = applications.data?.find(
    (item) => item.status === "approved" || item.status === "assigned",
  );
  const periodId =
    registrationPeriodId ?? selectedApplication?.registrationPeriodId;
  const selection = useStudentRoomSelectionQuery(periodId);
  const selectRoom = useSelectStudentRoom();
  const [query, setQuery] = useState("");
  const [confirmRoom, setConfirmRoom] = useState<StudentSelectableRoom | null>(
    null,
  );

  const rooms = useMemo(() => {
    const keyword = query.trim().toLocaleLowerCase("vi");
    return (selection.data?.availableRooms ?? []).filter(
      (room) =>
        !keyword ||
        [
          room.code,
          room.name,
          room.buildingName,
          room.floorName,
          room.roomTypeName,
        ].some((value) => value.toLocaleLowerCase("vi").includes(keyword)),
    );
  }, [query, selection.data]);

  if (!can("ktx.room_selection.view")) return <AccessDenied />;
  if (applications.isLoading && !periodId) return <Skeleton className="h-96" />;
  if (!periodId)
    return (
      <StateCard
        title="Chưa có hồ sơ được duyệt"
        description="Bạn chỉ có thể chọn phòng sau khi hồ sơ được cán bộ duyệt và đợt chọn phòng được thông báo mở."
      />
    );
  if (selection.isLoading) return <Skeleton className="h-96" />;
  if (selection.isError || !selection.data)
    return (
      <StateCard
        title="Chưa thể tải danh sách phòng"
        description={
          selection.error instanceof Error
            ? selection.error.message
            : "Vui lòng thử lại sau."
        }
      />
    );

  const data = selection.data;
  const isSelectable = data.isOpen && can("ktx.room_selection.select");
  const statusMessage: Record<string, string> = {
    awaiting_approval: "Hồ sơ đang chờ duyệt. Bạn chưa thể chọn phòng.",
    awaiting_notification:
      "Hồ sơ đã được duyệt. Vui lòng chờ thông báo mở chọn phòng.",
    not_allocated: "Cán bộ chưa hoàn tất cấu hình phòng cho đợt này.",
    not_scheduled: "Đợt chọn phòng chưa được lên lịch.",
    scheduled: "Đợt chọn phòng đã được lên lịch nhưng chưa bắt đầu.",
    ended: "Thời gian chọn phòng đã kết thúc.",
    assigned: "Lựa chọn phòng của bạn đã được cán bộ chốt.",
  };

  const confirm = () => {
    if (!confirmRoom || !periodId) return;
    void selectRoom
      .mutateAsync({ registrationPeriodId: periodId, roomId: confirmRoom.id })
      .then(() => {
        toast.success(`Đã chọn Phòng ${confirmRoom.code}.`);
        setConfirmRoom(null);
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Không thể lưu lựa chọn phòng.",
        ),
      );
  };

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/student">
          <ArrowLeft /> Tổng quan sinh viên
        </Link>
      </Button>
      <div>
        <p className="type-eyebrow text-muted-foreground">
          Không gian sinh viên
        </p>
        <h1 className="type-page-title">Chọn phòng</h1>
        <p className="type-supporting text-muted-foreground">
          Chọn một phòng còn chỗ trong phạm vi đã được cán bộ mở cho đợt đăng
          ký.
        </p>
      </div>

      <Alert>
        <Clock3 />
        <AlertTitle>{data.periodName}</AlertTitle>
        <AlertDescription>
          {data.selectionStartAt && data.selectionEndAt
            ? `${formatDateTimeValue(data.selectionStartAt)} – ${formatDateTimeValue(data.selectionEndAt)}`
            : "Thời gian chọn phòng chưa được công bố."}
        </AlertDescription>
      </Alert>

      {data.currentSelection ? (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="text-primary" /> Phòng đã chọn
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-semibold">
              Phòng {data.currentSelection.roomCode}
            </p>
            <p className="text-muted-foreground">
              {data.currentSelection.buildingName} ·{" "}
              {data.currentSelection.floorName}
            </p>
            {isSelectable ? (
              <p className="mt-2 type-supporting">
                Bạn có thể đổi sang phòng khác trước khi thời gian chọn kết
                thúc.
              </p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {!isSelectable ? (
        <Alert variant="warning">
          <Clock3 />
          <AlertTitle>Chưa thể chọn phòng</AlertTitle>
          <AlertDescription>
            {statusMessage[data.selectionStatus] ??
              "Đợt chọn phòng hiện chưa mở."}
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="max-w-xl">
        <DebouncedSearchInput
          value={query}
          onChange={setQuery}
          placeholder="Tìm phòng, tòa nhà, tầng hoặc loại phòng..."
        />
      </div>

      {rooms.length === 0 ? (
        <StateCard
          title="Không có phòng phù hợp"
          description="Hãy đổi từ khóa hoặc chờ cán bộ cập nhật phạm vi phòng."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rooms.map((room) => (
            <Card
              key={room.id}
              className={
                room.isSelectedByCurrentStudent ? "border-primary" : undefined
              }
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>Phòng {room.code}</CardTitle>
                    <CardDescription>
                      {room.buildingName} · {room.floorName}
                    </CardDescription>
                  </div>
                  <Badge
                    variant={room.availablePlaces > 0 ? "success" : "secondary"}
                  >
                    {room.availablePlaces} chỗ trống
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3 type-supporting">
                  <span className="flex items-center gap-2">
                    <DoorOpen className="size-4" />
                    {room.roomTypeName}
                  </span>
                  <span className="flex items-center gap-2">
                    <UsersRound className="size-4" />
                    {room.occupiedPlaces}/{room.operationalCapacity}
                  </span>
                  <span className="col-span-2 flex items-center gap-2">
                    <Banknote className="size-4" />
                    {room.priceAmount == null
                      ? "Chưa cấu hình mức phí"
                      : currency.format(room.priceAmount)}
                  </span>
                </div>
                <Button
                  className="w-full"
                  variant={
                    room.isSelectedByCurrentStudent ? "outline" : "default"
                  }
                  disabled={
                    !isSelectable ||
                    !room.isAvailable ||
                    room.isSelectedByCurrentStudent
                  }
                  onClick={() => setConfirmRoom(room)}
                >
                  {room.isSelectedByCurrentStudent
                    ? "Đã chọn"
                    : room.isAvailable
                      ? "Chọn phòng này"
                      : "Đã hết chỗ"}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog
        open={Boolean(confirmRoom)}
        onOpenChange={(open) => {
          if (!open && !selectRoom.isPending) setConfirmRoom(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Xác nhận chọn phòng</DialogTitle>
            <DialogDescription>
              Lựa chọn mới sẽ thay thế phòng bạn đang giữ trước đó.
            </DialogDescription>
          </DialogHeader>
          {confirmRoom ? (
            <div className="rounded-lg border p-4">
              <p className="text-lg font-semibold">Phòng {confirmRoom.code}</p>
              <p className="text-muted-foreground">
                {confirmRoom.buildingName} · {confirmRoom.floorName} ·{" "}
                {confirmRoom.roomTypeName}
              </p>
              <p className="mt-2">
                Còn {confirmRoom.availablePlaces}/
                {confirmRoom.operationalCapacity} chỗ
              </p>
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmRoom(null)}>
              Hủy
            </Button>
            <Button disabled={selectRoom.isPending} onClick={confirm}>
              {selectRoom.isPending ? (
                <LoaderCircle className="animate-spin" />
              ) : null}{" "}
              Xác nhận chọn phòng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StateCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardContent className="py-12 text-center">
        <Building2 className="mx-auto mb-3 size-8 text-muted-foreground" />
        <p className="font-semibold">{title}</p>
        <p className="mx-auto mt-1 max-w-xl type-supporting text-muted-foreground">
          {description}
        </p>
      </CardContent>
    </Card>
  );
}
