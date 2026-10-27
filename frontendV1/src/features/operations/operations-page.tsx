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
  if (!canReadOperations(role))
    return (
      <p role="alert">
        Cần quyền quản trị, biên tập hoặc rà soát để xem trung tâm vận hành.
      </p>
    );
  return (
    <div className="space-y-4">
      <nav aria-label="Chức năng vận hành" className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={view === "jobs" ? "secondary" : "outline"}
          onClick={() => onSearch({ view: "jobs", page: 1 })}
        >
          Tác vụ
        </Button>
        {isLifecycleAdmin(role) ? (
          <>
            <Button
              size="sm"
              variant={view === "backups" ? "secondary" : "outline"}
              onClick={() => onSearch({ view: "backups", page: 1 })}
            >
              Sao lưu
            </Button>
            <Button
              size="sm"
              variant={view === "storage" ? "secondary" : "outline"}
              onClick={() => onSearch({ view: "storage", page: 1 })}
            >
              Dọn tệp
            </Button>
          </>
        ) : null}
      </nav>
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
          <h1 className="type-page-title">Sao lưu bằng chứng</h1>
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
          <h1 className="type-page-title">Dọn tệp dẫn xuất</h1>
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
          <h1 className="type-page-title">Trung tâm vận hành</h1>
          <p className="text-sm text-muted-foreground">
            Theo dõi trạng thái thật, hủy và giao lại tác vụ theo điều kiện của
            server.
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
          <h2 className="font-semibold text-sm">
            Tổng quan tác vụ &amp; usage
          </h2>
          {summary.isPending ? (
            <p role="status">Đang đọc tổng quan…</p>
          ) : summary.isError ? (
            <ErrorState
              error={summary.error}
              onRetry={() => void summary.refetch()}
            />
          ) : (
            <>
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
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {summary.data.usage.map((usage) => (
                  <div
                    key={usage.status}
                    className="rounded-lg border p-3 text-xs"
                  >
                    <p className="font-semibold">
                      Usage · {statusLabel(usage.status)}
                    </p>
                    <p>
                      Token quan sát: {usage.observed_tokens ?? "Chưa có số đo"}
                    </p>
                    <p>
                      Token giữ chỗ: {usage.reserved_tokens ?? "Chưa có số đo"}
                    </p>
                    <p>
                      Chi phí quan sát (USD):{" "}
                      {usage.observed_cost_usd ?? "Chưa có số đo"}
                    </p>
                    <p className="text-muted-foreground">
                      Có chi phí: {usage.cost_records}/{usage.records} bản ghi
                    </p>
                  </div>
                ))}
              </div>
            </>
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
                    <TableCell>
                      {job.progress_done ?? "—"} /{" "}
                      {job.progress_total ?? "Chưa xác định"}
                    </TableCell>
                    <TableCell>{job.usage_tokens ?? "Chưa có số đo"}</TableCell>
                    <TableCell>{formatDateTimeValue(job.created_at)}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          onSearch({ jobId: job.id, jobKind: job.kind })
                        }
                      >
                        Xem
                      </Button>
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
