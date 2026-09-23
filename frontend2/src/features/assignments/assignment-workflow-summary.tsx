import {
  AlertCircle,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  DoorOpen,
  SlidersHorizontal,
  UserCheck,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { AssignmentWorkspace } from "@/features/assignments/types";
import { formatDateTimeValue } from "@/lib/date-utils";

const allocationStatusLabels: Record<string, string> = {
  not_allocated: "Chưa phân bổ phòng",
  allocated: "Đã phân bổ phòng",
  selection_open: "Đang mở chọn phòng",
  selection_ended: "Đã hết thời gian chọn phòng",
  finalized: "Đã chốt chỗ ở",
};

export function formatAssignmentTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return formatDateTimeValue(value);
}

export function AssignmentWorkflowSummary({
  workspace,
  isLoading,
  error,
  onRetry,
  onOpenRoomScope,
}: {
  workspace?: AssignmentWorkspace;
  isLoading: boolean;
  error?: Error | null;
  onRetry: () => void;
  onOpenRoomScope?: () => void;
}) {
  if (isLoading) {
    return (
      <section className="rounded-xl border bg-card p-4 sm:p-5 shadow-2xs">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <Skeleton key={item} className="h-24 rounded-lg" />
          ))}
        </div>
      </section>
    );
  }

  if (error || !workspace) {
    return (
      <section className="rounded-xl border border-dashed bg-card p-6 text-center shadow-2xs">
        <p className="font-semibold text-foreground">
          Không thể tải trạng thái quy trình xếp phòng
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Thông tin hồ sơ và trạng thái chốt phòng chưa sẵn sàng.
        </p>
        <Button className="mt-3" variant="outline" size="sm" onClick={onRetry}>
          Thử lại
        </Button>
      </section>
    );
  }

  const status = workspace.allocationStatus;
  const statusVariant =
    status === "finalized"
      ? "success"
      : status === "selection_open"
        ? "default"
        : status === "selection_ended"
          ? "warning"
          : "secondary";

  const totalCapacity =
    workspace.availablePlaceCount +
    workspace.assignedCount +
    workspace.selectedCount;
  const usedPlaces = workspace.assignedCount + workspace.selectedCount;
  const fillPercentage =
    totalCapacity > 0 ? Math.round((usedPlaces / totalCapacity) * 100) : 0;
  const assignedPercent =
    totalCapacity > 0 ? (workspace.assignedCount / totalCapacity) * 100 : 0;
  const selectedPercent =
    totalCapacity > 0 ? (workspace.selectedCount / totalCapacity) * 100 : 0;

  const statusTitle =
    status === "selection_open"
      ? "Đợt chọn phòng đang mở"
      : status === "selection_ended"
        ? "Đợt chọn phòng đã kết thúc"
        : status === "finalized"
          ? "Lựa chọn phòng đã được chốt"
          : "Chưa đủ điều kiện chuyển bước";

  const statusDesc =
    status === "selection_open"
      ? "Tiếp tục theo dõi hồ sơ. Chỉ chốt sau khi hết thời gian chọn phòng."
      : status === "selection_ended"
        ? "Có thể kiểm tra xung đột phòng, giới tính và chốt các hồ sơ hợp lệ."
        : status === "finalized"
          ? "Các hồ sơ hợp lệ đã chuyển sang trạng thái đã xếp."
          : "Cần phân bổ phòng, gửi thông báo và mở phạm vi phòng trước.";

  return (
    <section className="rounded-xl border bg-card shadow-2xs overflow-hidden">
      <div className="grid lg:grid-cols-12 gap-0 divide-y lg:divide-y-0 lg:divide-x">
        {/* Left Panel (7 cols): Workflow, Scope, Progress & Current Status */}
        <div className="lg:col-span-7 p-4 sm:p-5 flex flex-col justify-between space-y-3.5">
          {/* Header Info */}
          <div className="flex flex-wrap items-center justify-between gap-2.5">
            <div className="flex items-center gap-2.5">
              <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground shrink-0">
                <ClipboardCheck className="size-4" />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-sm sm:text-base font-bold text-foreground">
                    Quy trình chốt chỗ ở
                  </h2>
                  <Badge
                    variant={statusVariant}
                    className="gap-1.5 font-medium text-xs px-2.5 py-0.5"
                  >
                    <span
                      className={`size-1.5 rounded-full ${
                        status === "finalized"
                          ? "bg-success"
                          : status === "selection_open"
                            ? "bg-info"
                            : status === "selection_ended"
                              ? "bg-warning"
                              : "bg-muted-foreground/60"
                      }`}
                    />
                    {allocationStatusLabels[status] ?? status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  <span className="font-mono font-semibold">
                    {workspace.periodCode}
                  </span>{" "}
                  · {workspace.periodName}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/30 px-2.5 py-1 rounded-md border shrink-0">
              <Clock3 className="size-3.5" />
              <span>
                {workspace.roomSelectionEndAt
                  ? `Hạn: ${formatAssignmentTime(workspace.roomSelectionEndAt)}`
                  : "Chưa cấu hình hạn"}
              </span>
            </div>
          </div>

          {/* Progress / Capacity Bar */}
          <div className="space-y-1.5 rounded-lg border bg-muted/15 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground font-medium flex items-center gap-1.5">
                <span>Tỷ lệ phân bổ & chỗ ở:</span>
                <strong className="text-foreground">
                  {usedPlaces} / {totalCapacity} chỗ ({fillPercentage}%)
                </strong>
              </span>
              <span className="text-xs text-muted-foreground font-medium">
                Còn trống:{" "}
                <strong className="text-foreground">
                  {workspace.availablePlaceCount}
                </strong>{" "}
                chỗ
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted/50 flex">
              <div
                style={{ width: `${assignedPercent}%` }}
                className="bg-success transition-all"
                title={`Đã chốt: ${workspace.assignedCount}`}
              />
              <div
                style={{ width: `${selectedPercent}%` }}
                className="bg-info transition-all"
                title={`Đang giữ chỗ: ${workspace.selectedCount}`}
              />
            </div>
          </div>

          {/* Status Alert Note & Room Scope Action */}
          <div className="rounded-lg border bg-muted/20 px-3.5 py-2.5 text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5">
            <div className="flex items-start gap-2">
              <AlertCircle className="size-4 text-muted-foreground shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-foreground">
                  {statusTitle}:{" "}
                </span>
                <span className="text-muted-foreground">{statusDesc}</span>
              </div>
            </div>
            {onOpenRoomScope ? (
              <Button
                variant="outline"
                size="sm"
                className="h-7 gap-1 text-xs shrink-0 self-start sm:self-auto font-medium"
                onClick={onOpenRoomScope}
              >
                <SlidersHorizontal className="size-3" />
                <span>
                  {workspace.openedRoomCount > 0
                    ? "Cấu hình phòng"
                    : "Mở cấu hình"}
                </span>
              </Button>
            ) : null}
          </div>
        </div>

        {/* Right Panel (5 cols): 4 Compact KPI Mini-Cards in 2x2 Grid */}
        <div className="lg:col-span-5 p-4 bg-muted/10 flex flex-col justify-center">
          <div className="grid grid-cols-2 gap-2.5">
            <WorkflowStat
              label="Đã chọn phòng"
              value={workspace.selectedCount}
              hint="Chờ cán bộ chốt"
              icon={<UserCheck className="size-3.5" />}
              emphasis={workspace.selectedCount > 0 ? "primary" : undefined}
            />
            <WorkflowStat
              label="Chưa chọn phòng"
              value={workspace.awaitingAssignmentCount}
              hint="Có thể xếp thủ công"
              icon={<Users className="size-3.5" />}
            />
            <WorkflowStat
              label="Đã chốt chỗ ở"
              value={workspace.assignedCount}
              hint="Chờ phát hành HĐ & thanh toán"
              icon={<CheckCircle2 className="size-3.5" />}
              emphasis={workspace.assignedCount > 0 ? "success" : undefined}
            />
            <WorkflowStat
              label="Đang cư trú"
              value={workspace.checkedInCount}
              hint={`${workspace.openedRoomCount} phòng đang mở`}
              icon={<DoorOpen className="size-3.5" />}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function WorkflowStat({
  label,
  value,
  hint,
  icon,
  emphasis,
}: {
  label: string;
  value: number;
  hint: string;
  icon?: React.ReactNode;
  emphasis?: "primary" | "success";
}) {
  return (
    <div className="flex flex-col justify-between rounded-lg border bg-card p-3 shadow-2xs">
      <div className="flex items-center justify-between gap-1.5">
        <p className="text-[11px] font-medium text-muted-foreground truncate">
          {label}
        </p>
        {icon ? (
          <div className="flex size-5 items-center justify-center rounded bg-muted text-muted-foreground shrink-0">
            {icon}
          </div>
        ) : null}
      </div>
      <p
        className={`mt-1.5 font-mono text-xl font-bold tracking-tight ${
          emphasis === "success"
            ? "text-success"
            : emphasis === "primary"
              ? "text-primary"
              : "text-foreground"
        }`}
      >
        {value}
      </p>
      <p className="mt-0.5 text-[10px] text-muted-foreground truncate">
        {hint}
      </p>
    </div>
  );
}
