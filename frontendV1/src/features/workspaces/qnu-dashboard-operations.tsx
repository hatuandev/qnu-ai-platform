import { Link } from "@tanstack/react-router";
import { CircleCheck, Clock, TriangleAlert } from "lucide-react";
import { ErrorState } from "@/components/admin/error-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
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
import { useOperationsSummary } from "@/features/operations/queries";
import { JOB_LABEL, statusLabel } from "@/features/operations/types";

export function DashboardOperations({ workspaceId }: { workspaceId: string }) {
  const query = useOperationsSummary(workspaceId, true);
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardHeader>
        <CardTitle className="text-sm">Tác vụ và sử dụng model</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {query.isPending ? (
          <Skeleton className="h-40" />
        ) : query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : (
          <>
            <p className="text-xs text-muted-foreground">
              Tổng hợp các bản ghi hiện có trong workspace, không giới hạn theo
              ngày. Tự đọc lại mỗi 5 giây khi trang đang mở.
            </p>
            <div className="grid divide-y rounded-lg border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
              <KpiMetric
                label="Đang chờ / chạy"
                value={String(
                  query.data.jobs
                    .filter((j) => ["queued", "running"].includes(j.status))
                    .reduce((n, j) => n + j.count, 0),
                )}
                icon={Clock}
              />
              <KpiMetric
                label="Cần kiểm tra"
                value={String(
                  query.data.jobs
                    .filter((j) => ["failed", "uncertain"].includes(j.status))
                    .reduce((n, j) => n + j.count, 0),
                )}
                icon={TriangleAlert}
              />
              <KpiMetric
                label="Hoàn tất"
                value={String(
                  query.data.jobs
                    .filter((j) => j.status === "completed")
                    .reduce((n, j) => n + j.count, 0),
                )}
                icon={CircleCheck}
              />
            </div>
            <nav
              className="flex flex-wrap gap-2"
              aria-label="Tác vụ theo loại và trạng thái"
            >
              {query.data.jobs.map((j) => (
                <Button
                  key={`${j.kind}:${j.status}`}
                  variant="outline"
                  size="sm"
                  asChild
                >
                  <Link
                    to="/workspaces/$workspaceId/operations"
                    params={{ workspaceId }}
                    search={{
                      page: 1,
                      pageSize: 20,
                      kind: j.kind,
                      status: j.status,
                    }}
                  >
                    {JOB_LABEL[j.kind]} · {statusLabel(j.status)}: {j.count}
                  </Link>
                </Button>
              ))}
            </nav>
            {query.data.jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Chưa có tác vụ được ghi nhận.
              </p>
            ) : null}
            {query.data.usage.length ? (
              <div className="overflow-x-auto">
                <Table aria-label="Usage model theo trạng thái">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Trạng thái</TableHead>
                      <TableHead>Bản ghi</TableHead>
                      <TableHead>Token quan sát</TableHead>
                      <TableHead>Token giữ chỗ</TableHead>
                      <TableHead>Chi phí quan sát (USD)</TableHead>
                      <TableHead>Có số đo chi phí</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {query.data.usage.map((u) => (
                      <TableRow key={u.status}>
                        <TableCell>{statusLabel(u.status)}</TableCell>
                        <TableCell>{u.records}</TableCell>
                        <TableCell>
                          {u.observed_tokens ?? "Chưa có số đo"}
                        </TableCell>
                        <TableCell>
                          {u.reserved_tokens ?? "Chưa có số đo"}
                        </TableCell>
                        <TableCell>
                          {u.observed_cost_usd ?? "Chưa có số đo"}
                        </TableCell>
                        <TableCell>
                          {u.cost_records}/{u.records}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>{" "}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Chưa có bản ghi sử dụng model.
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Chi phí chỉ cộng các bản ghi có số đo; ô chưa có số đo không được
              xem là 0.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
