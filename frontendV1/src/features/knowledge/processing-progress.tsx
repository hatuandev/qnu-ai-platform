import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  WifiOff,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export type ProcessingProgressInput = {
  status: string;
  pages_total?: number | null;
  pages_done?: number | null;
  pages_failed?: number | null;
  results_ready?: boolean | null;
  dispatch_pending?: boolean | null;
  error_code?: string | null;
  error_detail?: string | null;
  unitLabel?: string;
};

export type ComputedProcessingProgress = {
  stageLabel: string;
  detailLabel: string;
  percent: number | null;
  isIndeterminate: boolean;
  isActive: boolean;
  isTerminal: boolean;
  tone: "info" | "success" | "warning" | "destructive" | "neutral";
};

export function computeProcessingProgress(
  input: ProcessingProgressInput,
): ComputedProcessingProgress {
  const {
    status,
    pages_total,
    pages_done,
    pages_failed,
    results_ready,
    dispatch_pending,
    error_detail,
    error_code,
    unitLabel = "trang",
  } = input;

  const total =
    typeof pages_total === "number" && pages_total > 0 ? pages_total : null;
  const done =
    typeof pages_done === "number" && pages_done >= 0 ? pages_done : 0;
  const failed =
    typeof pages_failed === "number" && pages_failed >= 0 ? pages_failed : 0;

  if (status === "uploading") {
    return {
      stageLabel: "Đang tải tệp",
      detailLabel: "Đang truyền dữ liệu tệp lên máy chủ và lưu phiên bản gốc…",
      percent: null,
      isIndeterminate: true,
      isActive: true,
      isTerminal: false,
      tone: "info",
    };
  }

  if (status === "queued" || dispatch_pending === true) {
    return {
      stageLabel: "Đang chờ xử lý",
      detailLabel:
        dispatch_pending === true
          ? "Đã ghi nhận tác vụ bền vững, đang đưa vào hàng đợi xử lý…"
          : "Đang xếp hàng chờ worker nhận xử lý…",
      percent: null,
      isIndeterminate: true,
      isActive: true,
      isTerminal: false,
      tone: "info",
    };
  }

  if (status === "running") {
    if (total === null) {
      return {
        stageLabel: "Đang chuẩn bị tài liệu",
        detailLabel: `Đang phân tích cấu trúc và xác định tổng số ${unitLabel}…`,
        percent: null,
        isIndeterminate: true,
        isActive: true,
        isTerminal: false,
        tone: "info",
      };
    }

    if (done >= total) {
      return {
        stageLabel: "Đang lưu kết quả",
        detailLabel: `Đã xử lý ${done}/${total} ${unitLabel} · Đang kiểm định và lưu kết quả…`,
        percent: 99,
        isIndeterminate: false,
        isActive: true,
        isTerminal: false,
        tone: "info",
      };
    }

    const rawPercent = Math.floor((done / total) * 100);
    const boundedPercent = Math.max(0, Math.min(98, rawPercent));
    const failedSuffix = failed > 0 ? ` · ${failed} ${unitLabel} lỗi` : "";
    return {
      stageLabel: "Đang bóc tách nội dung",
      detailLabel: `Đã xử lý ${done}/${total} ${unitLabel}${failedSuffix}`,
      percent: boundedPercent,
      isIndeterminate: false,
      isActive: true,
      isTerminal: false,
      tone: "info",
    };
  }

  if (status === "completed") {
    if (results_ready === false) {
      return {
        stageLabel: "Đang lưu kết quả",
        detailLabel:
          total !== null
            ? `Đã xử lý ${done}/${total} ${unitLabel} · Đang hoàn tất lưu trữ kết quả…`
            : "Đang hoàn tất lưu trữ kết quả…",
        percent: 99,
        isIndeterminate: false,
        isActive: true,
        isTerminal: false,
        tone: "info",
      };
    }

    return {
      stageLabel: "Hoàn tất",
      detailLabel:
        total !== null
          ? `Đã xử lý ${done}/${total} ${unitLabel}`
          : "Đã hoàn tất xử lý và sẵn sàng sử dụng",
      percent: 100,
      isIndeterminate: false,
      isActive: false,
      isTerminal: true,
      tone: "success",
    };
  }

  if (status === "uncertain") {
    const pageSummary =
      total !== null ? `Đã hoàn tất ${done}/${total} ${unitLabel} · ` : "";
    return {
      stageLabel: "Cần kiểm tra",
      detailLabel: `${pageSummary}${error_detail || error_code || "Có trang chưa xác định được kết quả từ nhà cung cấp AI."}`,
      percent:
        total !== null ? Math.min(98, Math.floor((done / total) * 100)) : null,
      isIndeterminate: false,
      isActive: false,
      isTerminal: true,
      tone: "warning",
    };
  }

  if (status === "cancelled") {
    return {
      stageLabel: "Đã hủy",
      detailLabel:
        total !== null
          ? `Đã dừng ở ${done}/${total} ${unitLabel}`
          : "Tác vụ đã được hủy theo yêu cầu",
      percent:
        total !== null ? Math.min(98, Math.floor((done / total) * 100)) : null,
      isIndeterminate: false,
      isActive: false,
      isTerminal: true,
      tone: "neutral",
    };
  }

  // Default: failed or unknown terminal error
  const failedSummary =
    total !== null
      ? `Đã hoàn tất ${done}/${total} ${unitLabel}${failed > 0 ? ` (${failed} lỗi)` : ""} · `
      : "";
  return {
    stageLabel: "Gặp lỗi",
    detailLabel: `${failedSummary}${error_detail || error_code || "Tác vụ xử lý gặp sự cố."}`,
    percent:
      total !== null ? Math.min(98, Math.floor((done / total) * 100)) : null,
    isIndeterminate: false,
    isActive: false,
    isTerminal: true,
    tone: "destructive",
  };
}

export function ProcessingProgress({
  progress,
  compact = false,
  isPollError = false,
  className,
}: {
  progress: ProcessingProgressInput;
  compact?: boolean;
  isPollError?: boolean;
  className?: string;
}) {
  const computed = computeProcessingProgress(progress);

  const badgeVariant =
    computed.tone === "success"
      ? "success"
      : computed.tone === "warning"
        ? "warning"
        : computed.tone === "destructive"
          ? "destructive"
          : computed.tone === "info"
            ? "info"
            : "outline";

  if (compact) {
    return (
      <div
        className={cn("min-w-[160px] space-y-1.5", className)}
        aria-live={computed.isActive ? "polite" : "off"}
      >
        <div className="flex items-center justify-between gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 font-medium text-foreground truncate">
            {computed.isActive ? (
              <Loader2 className="size-3 shrink-0 animate-spin text-primary motion-reduce:animate-none" />
            ) : computed.tone === "success" ? (
              <CheckCircle2 className="size-3 shrink-0 text-success" />
            ) : computed.tone === "warning" ? (
              <AlertTriangle className="size-3 shrink-0 text-warning" />
            ) : computed.tone === "destructive" ? (
              <XCircle className="size-3 shrink-0 text-destructive" />
            ) : (
              <Clock className="size-3 shrink-0 text-muted-foreground" />
            )}
            <span className="truncate">{computed.stageLabel}</span>
          </span>
          {computed.percent !== null ? (
            <span className="font-mono text-[11px] font-semibold tabular-nums text-muted-foreground shrink-0">
              {computed.percent}%
            </span>
          ) : null}
        </div>
        {(computed.isActive || computed.percent !== null) && (
          <div className="relative">
            {computed.isIndeterminate ? (
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-primary/15">
                <div className="h-full w-2/5 rounded-full bg-primary/70 animate-pulse motion-reduce:animate-none" />
              </div>
            ) : (
              <Progress
                value={computed.percent ?? 0}
                className="h-1.5"
                aria-label={`${computed.stageLabel}: ${computed.percent ?? 0}%`}
              />
            )}
          </div>
        )}
        <p className="truncate text-[11px] text-muted-foreground">
          {computed.detailLabel}
        </p>
        {isPollError ? (
          <p className="inline-flex items-center gap-1 text-[10px] text-warning">
            <WifiOff className="size-2.5 shrink-0" />
            Chưa cập nhật được tiến độ mới
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-xl border border-border/70 bg-muted/15 p-3.5 space-y-2.5",
        className,
      )}
      aria-live={computed.isActive ? "polite" : "off"}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {computed.isActive ? (
            <Loader2 className="size-4 shrink-0 animate-spin text-primary motion-reduce:animate-none" />
          ) : computed.tone === "success" ? (
            <CheckCircle2 className="size-4 shrink-0 text-success" />
          ) : computed.tone === "warning" ? (
            <AlertTriangle className="size-4 shrink-0 text-warning" />
          ) : computed.tone === "destructive" ? (
            <XCircle className="size-4 shrink-0 text-destructive" />
          ) : (
            <Clock className="size-4 shrink-0 text-muted-foreground" />
          )}
          <span className="text-sm font-semibold text-foreground">
            {computed.stageLabel}
          </span>
          <Badge variant={badgeVariant} className="text-[11px]">
            {computed.percent !== null ? `${computed.percent}%` : "Đang xử lý"}
          </Badge>
        </div>
        {isPollError ? (
          <span className="inline-flex items-center gap-1.5 rounded-md border border-warning/40 bg-warning/10 px-2 py-0.5 text-[11px] font-medium text-warning">
            <WifiOff className="size-3 shrink-0" />
            Mất kết nối tạm thời — đang giữ số liệu gần nhất
          </span>
        ) : null}
      </div>

      {computed.isIndeterminate ? (
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-primary/15"
          role="progressbar"
          aria-label={computed.stageLabel}
        >
          <div className="h-full w-1/3 rounded-full bg-primary/75 animate-pulse motion-reduce:animate-none" />
        </div>
      ) : (
        <Progress
          value={computed.percent ?? 0}
          className="h-2"
          aria-label={`${computed.stageLabel}: ${computed.percent ?? 0}%`}
        />
      )}

      <p className="text-xs text-muted-foreground">{computed.detailLabel}</p>
    </div>
  );
}
