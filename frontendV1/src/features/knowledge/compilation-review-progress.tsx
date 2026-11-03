import { AlertTriangle, Loader2 } from "lucide-react";
import { useState } from "react";
import { v1Client } from "@/app/api/v1";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useCompilationReviewProgressQuery } from "./compilation-queries";
import { cancelCompilationReview } from "./compilation-requests";
import { formatCompilationError } from "./compilation-schemas";
import type { CompilationReviewResponse } from "./compilation-types";

const GROUP_STATUS: Record<string, string> = {
  pending: "Chưa chạy",
  queued: "Chờ xử lý",
  running: "Đang rà soát",
  received: "Đang kiểm tra phản hồi",
  completed: "Hoàn tất",
  failed: "Lỗi",
  uncertain: "Chưa xác định kết quả",
  cancelled: "Đã dừng",
  split: "Đã chia nhỏ",
};

export function ReviewProgressPanel({
  workspaceId,
  collectionId,
  runId,
  review,
  canStop,
  onStopped,
}: {
  workspaceId: string;
  collectionId: string;
  runId: string;
  review: CompilationReviewResponse;
  canStop: boolean;
  onStopped: () => void;
}) {
  const [isStopping, setIsStopping] = useState(false);
  const [stopError, setStopError] = useState(false);
  const query = useCompilationReviewProgressQuery(
    workspaceId,
    collectionId,
    runId,
    review.id,
  );
  const progress = query.data?.review_id === review.id ? query.data : undefined;
  const completionPercent =
    progress && progress.total > 0
      ? (100 * progress.completed) / progress.total
      : null;
  const status =
    review.status === "queued" || review.status === "running"
      ? (progress?.status ?? review.status)
      : review.status;
  const isRunning = status === "queued" || status === "running";
  const errorCode =
    review.error_code ??
    progress?.segments.find((s) => s.error_code)?.error_code;

  async function handleStop() {
    setIsStopping(true);
    setStopError(false);
    try {
      await cancelCompilationReview(
        v1Client,
        workspaceId,
        collectionId,
        runId,
        review.id,
      );
    } catch {
      setStopError(true);
    } finally {
      onStopped();
      void query.refetch();
      setIsStopping(false);
    }
  }

  return (
    <section aria-label="Tiến độ rà soát" className="space-y-4">
      <Alert
        variant={
          isRunning || status === "completed" || status === "cancelled"
            ? "info"
            : "destructive"
        }
      >
        {isRunning ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <AlertTriangle className="size-4" />
        )}
        <AlertTitle>
          {status === "queued"
            ? "Đang chờ rà soát"
            : status === "cancelled"
              ? "Đã dừng rà soát"
              : isRunning
                ? "Đang rà soát độc lập"
                : status === "completed"
                  ? "Đã rà soát xong, đang tải báo cáo"
                  : "Lượt rà soát chưa hoàn tất"}
        </AlertTitle>
        <AlertDescription className="space-y-2">
          <p>
            {status === "cancelled"
              ? "Các nhóm hoàn tất được giữ lại. Nhóm đã gửi tới mô hình có thể chưa xác định kết quả."
              : isRunning
                ? "Tiến độ cập nhật theo từng nhóm. Bạn có thể đổi tab và quay lại xem."
                : status === "completed"
                  ? "Đang đồng bộ báo cáo tổng hợp."
                  : status === "uncertain"
                    ? "Đã gửi yêu cầu tới mô hình nhưng chưa nhận được kết quả xác định. Hệ thống không tự gửi lại."
                    : formatCompilationError(
                        errorCode ?? "",
                        "Lượt rà soát gặp lỗi và đã dừng.",
                      )}
          </p>
          {!isRunning && status !== "completed" && status !== "cancelled" && (
            <p>
              Phần đã hoàn tất và lịch sử được giữ lại. Chưa có báo cáo tổng hợp
              để kết luận toàn bộ tài liệu. Bạn có thể chủ động tạo lượt rà soát
              mới.
            </p>
          )}
          {errorCode && (
            <details>
              <summary>Chi tiết kỹ thuật</summary>
              <code>{errorCode}</code>
            </details>
          )}
        </AlertDescription>
      </Alert>
      {canStop && isRunning && (
        <Button
          variant="outline"
          size="sm"
          disabled={isStopping}
          onClick={() => void handleStop()}
        >
          {isStopping ? "Đang gửi yêu cầu dừng…" : "Dừng rà soát"}
        </Button>
      )}
      {stopError && (
        <p role="alert">
          Chưa xác nhận được yêu cầu dừng. Hãy kiểm tra trạng thái lượt rà soát.
        </p>
      )}
      {query.isError ? (
        <Alert variant="destructive">
          <AlertDescription>
            Không tải được tiến độ nhóm. Trạng thái lượt rà soát ở trên vẫn được
            giữ.
          </AlertDescription>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void query.refetch()}
          >
            Tải lại tiến độ
          </Button>
        </Alert>
      ) : progress ? (
        <div className="space-y-3 text-sm">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 font-medium">
            <p>
              {progress.completed}/{progress.total} nhóm hoàn tất
            </p>
            {completionPercent !== null && (
              <span className="tabular-nums">
                {Math.floor(completionPercent)}%
              </span>
            )}
          </div>
          {completionPercent !== null && (
            <Progress
              aria-label="Nhóm rà soát hoàn tất"
              value={completionPercent}
            />
          )}
          <p className="text-muted-foreground">
            {progress.running} đang chạy · {progress.pending} chưa chạy ·{" "}
            {progress.failed} lỗi · {progress.uncertain} chưa xác định ·{" "}
            {progress.cancelled} đã dừng
          </p>
          {progress.segments.length > 0 && (
            <details>
              <summary className="cursor-pointer">Chi tiết từng nhóm</summary>
              <ul className="mt-2 max-h-72 divide-y overflow-y-auto">
                {progress.segments.map((segment) => (
                  <li
                    key={segment.id ?? segment.index}
                    className="flex flex-wrap items-center gap-2 py-2"
                  >
                    <span>
                      Nhóm {segment.index}
                      {segment.depth > 0 ? " (chia nhỏ)" : ""}
                    </span>
                    <Badge
                      variant={
                        segment.status === "failed" ||
                        segment.status === "uncertain"
                          ? "destructive"
                          : "outline"
                      }
                    >
                      {GROUP_STATUS[segment.status] ??
                        "Trạng thái chưa nhận diện"}
                    </Badge>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground" role="status">
          Đang tải tiến độ nhóm…
        </p>
      )}
    </section>
  );
}
