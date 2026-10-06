import { Link } from "@tanstack/react-router";
import { Clock, DoorOpen, MapPin } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useLiveCountdown } from "@/features/student/dashboard/helpers";
import type {
  StudentRoomSelection,
  StudentSelectedRoom,
} from "@/features/student/types";
import { formatDateTimeValue } from "@/lib/date-utils";

const roomStatusLabels: Record<StudentSelectedRoom["status"], string> = {
  selected: "Bạn đã chọn",
  assigned: "Đã được xếp",
  checked_in: "Đã nhận phòng",
};

export function RoomCard({
  selection,
}: {
  selection?: StudentRoomSelection | null;
}) {
  const selectionDeadline = useLiveCountdown(selection?.selectionEndAt);
  if (!selection) return null;
  const room = selection.currentSelection;

  if (!room) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-base">Phòng của bạn</CardTitle>
            {selection.selectionStatus === "open" && selectionDeadline ? (
              <Badge
                variant={selectionDeadline.badgeVariant}
                className="px-1.5 py-0 text-[11px]"
              >
                <Clock className="mr-1 size-3" />
                Đóng chọn phòng: {selectionDeadline.detailedLabel}
              </Badge>
            ) : null}
          </div>
          <CardDescription>{selection.periodName}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Chưa có phòng.{" "}
            {selection.selectionStatus === "open"
              ? "Chọn phòng ngay trong thời gian đang mở."
              : "Bạn sẽ nhận thông báo khi đến lượt."}
          </p>
          {selection.selectionStatus === "open" ? (
            <Button asChild size="sm" variant="outline">
              <Link
                to="/student/room-selection"
                search={{
                  registrationPeriodId: selection.registrationPeriodId,
                }}
              >
                Chọn phòng ngay
              </Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-base">Phòng của bạn</CardTitle>
          <div className="flex items-center gap-1.5">
            {selection.selectionStatus === "open" && selectionDeadline ? (
              <Badge
                variant={selectionDeadline.badgeVariant}
                className="px-1.5 py-0 text-[11px]"
              >
                <Clock className="mr-1 size-3" />
                {selectionDeadline.detailedLabel}
              </Badge>
            ) : null}
            <Badge variant={room.status === "checked_in" ? "success" : "info"}>
              {roomStatusLabels[room.status]}
            </Badge>
          </div>
        </div>
        <CardDescription>{selection.periodName}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <DoorOpen className="size-5" />
          </div>
          <div className="min-w-0">
            <p className="font-semibold">Phòng {room.roomName}</p>
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              <MapPin className="size-3.5" />
              {room.buildingName} · Tầng {room.floorName}
            </p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Chọn lúc {formatDateTimeValue(room.selectedAt)}
        </p>
        <Button asChild size="sm" variant="outline">
          <Link
            to="/student/room-selection"
            search={{ registrationPeriodId: selection.registrationPeriodId }}
          >
            {selection.selectionStatus === "open"
              ? "Đổi phòng / Xem chi tiết"
              : "Xem chi tiết"}
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
