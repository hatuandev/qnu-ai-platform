import { Link } from "@tanstack/react-router";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { useState } from "react";
import { useV1Auth } from "@/app/auth/v1";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ProcessingProgress } from "@/features/knowledge/processing-progress";
import { LifecycleReceipt } from "@/features/lifecycle/action-receipt";
import {
  canReadOperations,
  isLifecycleAdmin,
} from "@/features/lifecycle/permissions";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { BackupsPanel } from "./backups-panel";
import { JobDetails } from "./job-details";
import { OperationReceipt } from "./operation-receipt";
import { useJobs, useOperationsSummary } from "./queries";
import { ReadinessPanel } from "./readiness-panel";
import { RecoveryDialog } from "./recovery-dialog";
import type { OperationsSearch } from "./search";
import { StoragePanel } from "./storage-panel";
import {
  JOB_LABEL,
  JOB_STATUSES,
  type JobKind,
  type JobView,
  statusLabel,
} from "./types";

function renderJobResourceLink(workspaceId: string, job: JobView) {
  if (!job.collection_id) return null;
  if (job.source_id) {
    return (
      <Button
        asChild
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-xs gap-1"
      >
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
          params={{
            workspaceId,
            collectionId: job.collection_id,
            sourceId: job.source_id,
          }}
          search={{
            revisionId: job.revision_id ?? undefined,
            runId: job.kind === "ocr" ? job.id : undefined,
          }}
        >
          <span>Mở tài liệu</span>
          <ExternalLink className="size-3" />
        </Link>
      </Button>
    );
  }
  const compilationRunId =
    job.compilation_run_id || (job.kind === "compiler" ? job.id : null);
  if (compilationRunId) {
    return (
      <Button
        asChild
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-xs gap-1"
      >
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
          params={{
            workspaceId,
            collectionId: job.collection_id,
            runId: compilationRunId,
          }}
        >
          <span>Mở nội dung đã chuẩn bị</span>
          <ExternalLink className="size-3" />
        </Link>
      </Button>
    );
  }
  if (job.kind === "index") {
    return (
      <Button
        asChild
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-xs gap-1"
      >
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId/search"
          params={{
            workspaceId,
            collectionId: job.collection_id,
          }}
          search={{ page: 1, pageSize: 20 }}
        >
          <span>Mở chỉ mục kho</span>
          <ExternalLink className="size-3" />
        </Link>
      </Button>
    );
  }
  return null;
}

type Props = {
  workspaceId: string;
  search: OperationsSearch;
  onSearch: (patch: Partial<OperationsSearch>) => void;
};
export function OperationsPage(props: Props) {
  const { sessionId } = useV1Auth();
  return (
    <OperationsSession key={`${sessionId}:${props.workspaceId}`} {...props} />
  );
}
function OperationsSession({ workspaceId, search, onSearch }: Props) {
  const { role, isPending } = useCallerWorkspaceRole(workspaceId);
  const view = search.view ?? "jobs";
  if (isPending) return <p role="status">Đang kiểm tra quyền vận hành…</p>;
  if (!canReadOperations(role) && search.lifecycleActionId)
    return (
      <LifecycleReceipt
        workspaceId={workspaceId}
        actionId={search.lifecycleActionId}
      />
    );
  if (!canReadOperations(role))
    return (
      <p role="alert">
        Cần quyền quản trị, biên tập hoặc rà soát để xem trung tâm vận hành.
      </p>
    );
  return (
    <div className="space-y-4">
      {view === "jobs" ? (
        <OperationsJobs
          workspaceId={workspaceId}
          search={search}
          onSearch={onSearch}
        />
      ) : !isLifecycleAdmin(role) ? (
        <p role="alert">Chỉ quản trị viên được quản lý sao lưu và dọn tệp.</p>
      ) : view === "backups" ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h1 className="type-page-title">Sao lưu bằng chứng</h1>
              <p className="text-sm text-muted-foreground">
                Tạo và quản lý bản sao lưu bằng chứng của đơn vị.
              </p>
            </div>
            <Button asChild variant="outline" size="sm" className="gap-1.5">
              <Link to="/settings">
                <ArrowLeft className="size-3.5" />
                <span>Về Cấu hình</span>
              </Link>
            </Button>
          </div>
          {search.operationActionId ? (
            <OperationReceipt
              key={search.operationActionId}
              workspaceId={workspaceId}
              actionId={search.operationActionId}
              onJob={(_kind, id) => onSearch({ backupId: id })}
            />
          ) : null}
          <BackupsPanel
            workspaceId={workspaceId}
            search={search}
            onSearch={onSearch}
          />
        </>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h1 className="type-page-title">Dọn dữ liệu dẫn xuất</h1>
              <p className="text-sm text-muted-foreground">
                Kiểm tra và dọn dẹp các tệp dẫn xuất không còn tham chiếu.
              </p>
            </div>
            <Button asChild variant="outline" size="sm" className="gap-1.5">
              <Link to="/settings">
                <ArrowLeft className="size-3.5" />
                <span>Về Cấu hình</span>
              </Link>
            </Button>
          </div>
          <StoragePanel
            workspaceId={workspaceId}
            actionId={search.cleanupActionId}
            onReceipt={(id) => onSearch({ cleanupActionId: id })}
          />
        </>
      )}
    </div>
  );
}
function OperationsJobs({ workspaceId, search, onSearch }: Props) {
  const { role, isPending } = useCallerWorkspaceRole(workspaceId);
  const allowed = canReadOperations(role) && !isPending;
  const jobs = useJobs(
    workspaceId,
    {
      page: search.page,
      pageSize: search.pageSize,
      kind: search.kind,
      status: search.status,
      collectionId: search.collectionId,
    },
    allowed,
  );
  const summary = useOperationsSummary(workspaceId, allowed);
  const [recover, setRecover] = useState<JobView | null>(null);
  if (isPending) return <p role="status">Đang kiểm tra quyền vận hành…</p>;
  if (!allowed)
    return (
      <p role="alert">
        Cần quyền quản trị, biên tập hoặc rà soát để xem trung tâm vận hành.
      </p>
    );
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="type-page-title">Tác vụ</h1>
          <p className="text-sm text-muted-foreground">
            Danh sách công việc đang chạy hoặc cần xử lý, tiến độ thực tế và
            liên kết quay về đúng tài liệu hoặc nội dung đã chuẩn bị.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            void jobs.refetch();
            void summary.refetch();
          }}
          disabled={jobs.isFetching}
        >
          Làm mới
        </Button>
      </div>
      {search.lifecycleActionId ? (
        <LifecycleReceipt
          workspaceId={workspaceId}
          actionId={search.lifecycleActionId}
        />
      ) : null}
      {search.operationActionId ? (
        <OperationReceipt
          key={search.operationActionId}
          workspaceId={workspaceId}
          actionId={search.operationActionId}
          onJob={(kind, id) => onSearch({ jobId: id, jobKind: kind })}
        />
      ) : null}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-4 space-y-3">
          <h2 className="font-semibold text-sm">Tổng quan tác vụ</h2>
          {summary.isPending ? (
            <p role="status">Đang đọc tổng quan…</p>
          ) : summary.isError ? (
            <ErrorState
              error={summary.error}
              onRetry={() => void summary.refetch()}
            />
          ) : (
            <div className="flex flex-wrap gap-2">
              {summary.data.jobs.map((item) => (
                <Badge key={`${item.kind}:${item.status}`} variant="outline">
                  {JOB_LABEL[item.kind]} · {statusLabel(item.status)}:{" "}
                  {item.count}
                </Badge>
              ))}
              {summary.data.jobs.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Chưa có tác vụ được ghi nhận.
                </p>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>
      {isLifecycleAdmin(role) ? (
        <ReadinessPanel workspaceId={workspaceId} />
      ) : null}
      {search.jobId && search.jobKind ? (
        <JobDetails
          workspaceId={workspaceId}
          kind={search.jobKind}
          jobId={search.jobId}
          role={role}
          onRecover={setRecover}
          onClose={() => onSearch({ jobId: undefined, jobKind: undefined })}
        />
      ) : null}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-semibold text-sm">Danh sách tác vụ</h2>
        <div className="flex flex-wrap gap-2">
          <Select
            value={search.kind ?? "all"}
            onValueChange={(value) =>
              onSearch({
                kind: value === "all" ? undefined : (value as JobKind),
                page: 1,
              })
            }
          >
            <SelectTrigger className="w-44 text-xs" aria-label="Loại tác vụ">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Mọi loại tác vụ</SelectItem>
              {Object.entries(JOB_LABEL).map(([key, value]) => (
                <SelectItem key={key} value={key}>
                  {value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={search.status ?? "all"}
            onValueChange={(value) =>
              onSearch({ status: value === "all" ? undefined : value, page: 1 })
            }
          >
            <SelectTrigger
              className="w-44 text-xs"
              aria-label="Trạng thái tác vụ"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Mọi trạng thái</SelectItem>
              {JOB_STATUSES.map((value) => (
                <SelectItem key={value} value={value}>
                  {statusLabel(value)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {search.collectionId ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSearch({ collectionId: undefined, page: 1 })}
            >
              Bỏ lọc bộ sưu tập
            </Button>
          ) : null}
        </div>
      </div>
      {jobs.isPending ? (
        <p role="status">Đang đọc tác vụ…</p>
      ) : jobs.isError ? (
        <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
      ) : (
        <>
          <div className="w-full overflow-x-auto rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tác vụ</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Tiến độ</TableHead>
                  <TableHead>Token</TableHead>
                  <TableHead>Tạo lúc</TableHead>
                  <TableHead>Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.data.items.map((job) => (
                  <TableRow key={`${job.kind}:${job.id}`}>
                    <TableCell>
                      <span className="font-medium">{JOB_LABEL[job.kind]}</span>
                      <p
                        className="max-w-48 truncate text-xs text-muted-foreground"
                        title={job.id}
                      >
                        {job.id}
                      </p>
                    </TableCell>
                    <TableCell>
                      {statusLabel(job.status)}
                      {job.error_code ? (
                        <p className="text-xs text-destructive">
                          {job.error_code}
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell className="min-w-[200px]">
                      <ProcessingProgress
                        compact
                        progress={{
                          status: job.status,
                          pages_total: job.progress_total,
                          pages_done: job.progress_done,
                          error_code: job.error_code,
                          unitLabel:
                            job.kind === "index"
                              ? "chunk"
                              : job.kind === "ocr"
                                ? "trang"
                                : "mục",
                        }}
                        isPollError={jobs.isError}
                      />
                    </TableCell>
                    <TableCell>{job.usage_tokens ?? "Chưa có số đo"}</TableCell>
                    <TableCell>{formatDateTimeValue(job.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {renderJobResourceLink(workspaceId, job)}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            onSearch({ jobId: job.id, jobKind: job.kind })
                          }
                        >
                          Xem
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {jobs.data.items.length === 0 ? (
              <p className="p-6 text-sm text-center text-muted-foreground">
                Không có tác vụ khớp bộ lọc.
              </p>
            ) : null}
          </div>
          <DataTablePagination
            page={search.page}
            pageSize={search.pageSize}
            pageCount={Math.max(
              1,
              Math.ceil(jobs.data.total / search.pageSize),
            )}
            total={jobs.data.total}
            onPageChange={(page) => onSearch({ page })}
            onPageSizeChange={(pageSize) => onSearch({ pageSize, page: 1 })}
          />
        </>
      )}
      {recover ? (
        <RecoveryDialog
          key={`${recover.kind}:${recover.id}`}
          workspaceId={workspaceId}
          job={recover}
          onClose={() => setRecover(null)}
        />
      ) : null}
    </div>
  );
}
