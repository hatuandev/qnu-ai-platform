import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/app/api/client";
import { DatePicker } from "@/components/admin/date-pickers";
import { PageHeader } from "@/components/admin/page-header";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAssignmentRoomsQuery } from "@/features/assignments/api";
import {
  useCheckOut,
  useExtendResidence,
  useResidenceHistoryQuery,
  useResidenceQuery,
  useRevokeResidence,
  useTransferResidence,
} from "@/features/residences/api";
import type { ResidenceDetail } from "@/features/residences/types";
import { formatDateOnly, formatDateValue } from "@/lib/date-utils";
import { useRbac } from "@/rbac/context";

const labels: Record<string, string> = {
  active: "Đang cư trú",
  extended: "Đã gia hạn",
  checked_out: "Đã trả phòng",
  cancelled: "Đã thu hồi",
};
const historyActionLabels: Record<string, string> = {
  check_in: "Nhận phòng",
  transfer: "Chuyển phòng",
  extend: "Gia hạn",
  check_out: "Trả phòng",
  cancel: "Thu hồi chỗ ở",
};

export function ResidenceDetail({ residenceId }: { residenceId: string }) {
  const { can } = useRbac();
  const query = useResidenceQuery(residenceId);
  const history = useResidenceHistoryQuery(residenceId);
  const [action, setAction] = useState<ResidenceAction>(null);
  if (query.isLoading)
    return <div className="h-64 animate-pulse rounded-lg border bg-card" />;
  if (query.isError || !query.data)
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        Không thể tải lượt cư trú.
        <br />
        <Button
          className="mt-3"
          variant="outline"
          onClick={() => void query.refetch()}
        >
          Thử lại
        </Button>
      </div>
    );
  const item = query.data;
  const active = item.status === "active" || item.status === "extended";
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Ký túc xá / Cư trú"
        title={`${item.studentName} · ${item.roomCode}`}
        description={`${item.studentCode} · ${labels[item.status]}`}
        actions={
          <Button variant="outline" onClick={() => window.history.back()}>
            Quay lại
          </Button>
        }
      />
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <section className="rounded-lg border bg-card p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <Info
              label="Sinh viên"
              value={`${item.studentName} (${item.studentCode})`}
            />
            <Info
              label="Khoa / lớp"
              value={[item.faculty, item.className].filter(Boolean).join(" · ")}
            />
            <Info
              label="Tòa / phòng"
              value={`${item.buildingName} · ${item.roomCode} · ${item.roomName}`}
            />
            <Info label="Năm học" value={item.academicYearCode} />
            <Info
              label="Ngày bắt đầu"
              value={formatDateValue(item.startDate)}
            />
            <Info
              label="Ngày kết thúc dự kiến"
              value={formatDateValue(item.expectedEndDate) || "—"}
            />
            <div className="sm:col-span-2">
              <Info label="Ghi chú" value={item.note} />
            </div>
          </div>
        </section>
        <aside className="space-y-4">
          <section className="rounded-lg border bg-card p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Trạng thái</p>
              <Badge
                variant={
                  item.status === "checked_out" ? "secondary" : "success"
                }
              >
                {labels[item.status]}
              </Badge>
            </div>
            {active ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {can("ktx.residences.transfer") ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setAction("transfer")}
                  >
                    Chuyển phòng
                  </Button>
                ) : null}
                {can("ktx.residences.extend") ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setAction("extend")}
                  >
                    Gia hạn
                  </Button>
                ) : null}
                {can("ktx.residences.check_out") ? (
                  <>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => setAction("checkout")}
                    >
                      Trả phòng
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setAction("revoke")}
                    >
                      Thu hồi chỗ ở
                    </Button>
                  </>
                ) : null}
              </div>
            ) : null}
          </section>
          <section className="rounded-lg border bg-card p-5">
            <p className="text-sm font-medium">Lịch sử</p>
            <div className="mt-3 space-y-3">
              {history.data?.length ? (
                history.data.map((entry) => (
                  <div key={entry.id} className="border-l-2 pl-3 text-sm">
                    <p className="font-medium">
                      {historyActionLabels[entry.action] ?? entry.action}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(entry.performedAt).toLocaleString("vi-VN")}
                      {entry.note ? ` · ${entry.note}` : ""}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  Chưa có lịch sử.
                </p>
              )}
            </div>
          </section>
        </aside>
      </div>
      <ResidenceActionDialog
        action={action}
        residence={item}
        onClose={() => setAction(null)}
      />
    </div>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm">{value || "—"}</p>
    </div>
  );
}
type ResidenceAction = "checkout" | "revoke" | "extend" | "transfer" | null;

function ResidenceActionDialog({
  action,
  residence,
  onClose,
}: {
  action: ResidenceAction;
  residence: ResidenceDetail;
  onClose: () => void;
}) {
  const checkout = useCheckOut();
  const revoke = useRevokeResidence();
  const extend = useExtendResidence();
  const transfer = useTransferResidence();
  const rooms = useAssignmentRoomsQuery();
  const [date, setDate] = useState<Date | undefined>();
  const [roomId, setRoomId] = useState("");
  const [note, setNote] = useState("");
  useEffect(() => {
    if (action) {
      setDate(new Date());
      setRoomId("");
      setNote("");
    }
  }, [action]);
  if (!action) return null;
  const mutation =
    action === "checkout"
      ? checkout
      : action === "revoke"
        ? revoke
        : action === "extend"
          ? extend
          : transfer;
  const title =
    action === "checkout"
      ? "Xác nhận trả phòng"
      : action === "revoke"
        ? "Thu hồi chỗ ở"
        : action === "extend"
          ? "Gia hạn cư trú"
          : "Chuyển phòng";
  const description =
    action === "checkout"
      ? "Kết thúc lượt cư trú và giải phóng một chỗ trong phòng."
      : action === "revoke"
        ? "Kết thúc lượt cư trú theo quyết định của cán bộ."
        : action === "extend"
          ? "Cập nhật thời hạn dự kiến của lượt cư trú hiện tại."
          : "Chọn phòng mới còn chỗ để chuyển sinh viên.";
  const submit = () => {
    if ((action === "checkout" || action === "revoke") && date)
      void (action === "checkout" ? checkout : revoke)
        .mutateAsync({
          id: residence.id,
          actualEndDate: formatDateOnly(date),
          note: note.trim() || undefined,
        })
        .then(() => {
          onClose();
          toast.success("Đã cập nhật cư trú.");
        })
        .catch(showError);
    else if (action === "extend" && date)
      void extend
        .mutateAsync({
          id: residence.id,
          newExpectedEndDate: formatDateOnly(date),
          note: note.trim() || undefined,
        })
        .then(() => {
          onClose();
          toast.success("Đã gia hạn cư trú.");
        })
        .catch(showError);
    else if (action === "transfer" && roomId)
      void transfer
        .mutateAsync({
          id: residence.id,
          newRoomId: roomId,
          note: note.trim() || undefined,
        })
        .then(() => {
          onClose();
          toast.success("Đã chuyển phòng.");
        })
        .catch(showError);
  };
  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open && !mutation.isPending) onClose();
      }}
    >
      <ResponsiveDialogContent className="max-w-lg">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>{title}</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {description}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="grid gap-4 py-4">
          {action === "checkout" || action === "revoke" ? (
            <Alert variant={action === "revoke" ? "warning" : "destructive"}>
              <AlertTriangle />
              <AlertTitle>
                {action === "revoke"
                  ? "Đây là thao tác thu hồi"
                  : "Chỗ trong phòng sẽ được giải phóng"}
              </AlertTitle>
              <AlertDescription>
                {action === "revoke"
                  ? "Chỉ dùng khi cần kết thúc chỗ ở theo quyết định của cán bộ."
                  : "Sau khi xác nhận, sinh viên không còn cư trú tại phòng này."}
              </AlertDescription>
            </Alert>
          ) : null}
          {action === "transfer" ? (
            <div className="grid gap-2">
              <Label htmlFor="residence-transfer-room">Phòng mới</Label>
              <Select value={roomId} onValueChange={setRoomId}>
                <SelectTrigger id="residence-transfer-room">
                  <SelectValue placeholder="Chọn phòng mới" />
                </SelectTrigger>
                <SelectContent>
                  {rooms.data
                    ?.filter(
                      (room) =>
                        room.id !== residence.roomId &&
                        room.availablePlaces > 0,
                    )
                    .map((room) => (
                      <SelectItem key={room.id} value={room.id}>
                        {room.code} · {room.name} · còn {room.availablePlaces}{" "}
                        chỗ
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <>
              <div className="grid gap-2">
                <Label htmlFor="residence-action-date">
                  {action === "extend"
                    ? "Ngày kết thúc mới"
                    : "Ngày kết thúc cư trú"}
                </Label>
                <DatePicker
                  id="residence-action-date"
                  value={date}
                  onChange={setDate}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="residence-action-note">
                  Ghi chú xử lý (không bắt buộc)
                </Label>
                <Textarea
                  id="residence-action-note"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </div>
            </>
          )}
        </div>
        <ResponsiveDialogFooter>
          <Button
            variant="outline"
            disabled={mutation.isPending}
            onClick={onClose}
          >
            Hủy
          </Button>
          <Button
            disabled={
              mutation.isPending || (action === "transfer" ? !roomId : !date)
            }
            onClick={submit}
          >
            {mutation.isPending
              ? "Đang xử lý..."
              : action === "extend"
                ? "Lưu gia hạn"
                : action === "transfer"
                  ? "Xác nhận chuyển phòng"
                  : "Xác nhận"}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

function showError(error: unknown) {
  toast.error(
    error instanceof ApiError || error instanceof Error
      ? error.message
      : "Không thể cập nhật cư trú.",
  );
}
