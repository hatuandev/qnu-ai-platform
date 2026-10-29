import { Link } from "@tanstack/react-router";
import { ExternalLink } from "lucide-react";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProcessingProgress } from "@/features/knowledge/processing-progress";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import {
  isLifecycleAdmin,
  isLifecycleEditor,
} from "@/features/lifecycle/permissions";
import { formatDateTimeValue } from "@/lib/date-utils";
import { useJob } from "./queries";
import { JOB_LABEL, type JobKind, type JobView, statusLabel } from "./types";
export function JobDetails({
  workspaceId,
  kind,
  jobId,
  role,
  onRecover,
  onClose,
}: {
  workspaceId: string;
  kind: JobKind;
  jobId: string;
  role: CallerWorkspaceRole;
  onRecover: (job: JobView) => void;
  onClose: () => void;
}) {
  const query = useJob(workspaceId, kind, jobId);
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardContent className="space-y-3 p-4">
        <div className="flex justify-between gap-2">
          <h2 className="font-semibold text-sm">Chi tiết tác vụ</h2>
          <Button size="sm" variant="ghost" onClick={onClose}>
            Đóng chi tiết
          </Button>
        </div>
        {query.isPending ? (
          <p role="status">Đang đọc tác vụ…</p>
        ) : query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">
                  {JOB_LABEL[query.data.kind]}
                </span>
                <Badge variant="outline">
                  {statusLabel(query.data.status)}
                </Badge>
              </div>
              {query.data.collection_id && query.data.source_id ? (
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs gap-1.5"
                >
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                    params={{
                      workspaceId,
                      collectionId: query.data.collection_id,
                      sourceId: query.data.source_id,
                    }}
                    search={{
                      revisionId: query.data.revision_id ?? undefined,
                      runId:
                        query.data.kind === "ocr" ? query.data.id : undefined,
                    }}
                  >
                    <span>Mở tài liệu nguồn</span>
                    <ExternalLink className="size-3.5" />
                  </Link>
                </Button>
              ) : query.data.collection_id &&
                (query.data.compilation_run_id ||
                  query.data.kind === "compiler") ? (
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs gap-1.5"
                >
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                    params={{
                      workspaceId,
                      collectionId: query.data.collection_id,
                      runId: query.data.compilation_run_id ?? query.data.id,
                    }}
                  >
                    <span>Mở bản biên soạn</span>
                    <ExternalLink className="size-3.5" />
                  </Link>
                </Button>
              ) : null}
            </div>
            <ProcessingProgress
              progress={{
                status: query.data.status,
                pages_total: query.data.progress_total,
                pages_done: query.data.progress_done,
                error_code: query.data.error_code,
                unitLabel:
                  query.data.kind === "index"
                    ? "chunk"
                    : query.data.kind === "ocr"
                      ? "trang"
                      : "mục",
              }}
              isPollError={query.isError}
            />
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">Mã tác vụ</dt>
                <dd className="break-all">{query.data.id}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Tiến độ quan sát</dt>
                <dd>
                  {query.data.progress_done ?? "Chưa có số đo"} /{" "}
                  {query.data.progress_total ?? "Chưa xác định tổng"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Số lần thử</dt>
                <dd>{query.data.attempts ?? "Chưa có số đo"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Token đã ghi nhận</dt>
                <dd>{query.data.usage_tokens ?? "Chưa có số đo"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Hạn xử lý hiện tại</dt>
                <dd>
                  {query.data.lease_expires_at
                    ? formatDateTimeValue(query.data.lease_expires_at)
                    : "Chưa xác định"}
                </dd>
              </div>
            </dl>
            {query.data.error_code ? (
              <p role="alert" className="break-all text-sm text-destructive">
                {query.data.error_code}
              </p>
            ) : null}
            <p className="text-xs text-muted-foreground">
              Điều kiện giao lại từ server: {query.data.recovery_reason}. Lỗi
              hoặc kết quả chưa rõ không được tự gửi lại model.
            </p>
            {isLifecycleEditor(role) ? (
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={
                    !query.data.recovery_allowed ||
                    (query.data.kind === "backup" && !isLifecycleAdmin(role))
                  }
                  onClick={() => onRecover(query.data)}
                >
                  Xem trước giao lại
                </Button>
                {query.data.kind !== "backup" &&
                query.data.kind !== "turn" &&
                ["queued", "running"].includes(query.data.status) ? (
                  <LifecycleActions
                    workspaceId={workspaceId}
                    kind="job"
                    resourceId={query.data.id}
                    label={`${JOB_LABEL[query.data.kind]} #${query.data.id.slice(-8)}`}
                    jobKind={query.data.kind}
                    role={role}
                  />
                ) : null}
              </div>
            ) : null}
            {query.data.kind === "turn" ? (
              <p className="text-xs text-muted-foreground">
                Chủ hội thoại hủy lượt hỏi tại màn hội thoại của mình.
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
