import { Gauge, RefreshCw } from "lucide-react";
import { canManageMembers } from "@/app/auth/v1";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
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
import {
  useCallerWorkspaceRole,
  useQuotaQuery,
  useUsageQuery,
} from "@/features/workspaces/queries";
import type { Quota } from "@/features/workspaces/types";
import { formatDateTimeValue } from "@/lib/date-utils";

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
      {hint ? (
        <p className="mt-0.5 text-[11px] text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

function formatTokens(value: number | null): string {
  if (value === null) return "—";
  return new Intl.NumberFormat("vi-VN").format(value);
}

export function WorkspaceQuotaPanel({
  workspaceId,
  usagePage,
  usagePageSize,
  onUsagePageChange,
  onUsagePageSizeChange,
}: {
  workspaceId: string;
  usagePage: number;
  usagePageSize: number;
  onUsagePageChange: (page: number) => void;
  onUsagePageSizeChange: (pageSize: number) => void;
}) {
  const { role } = useCallerWorkspaceRole(workspaceId);
  const quotaQuery = useQuotaQuery(workspaceId);
  const canViewUsage = canManageMembers(role);

  const usageQuery = useUsageQuery(
    workspaceId,
    { page: usagePage, pageSize: usagePageSize },
    { enabled: canViewUsage },
  );

  const quota = quotaQuery.data;
  const usageTotal = usageQuery.data?.meta.total ?? 0;
  const usagePageCount = Math.max(1, Math.ceil(usageTotal / usagePageSize));

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Mức sử dụng</h2>
          <p className="text-xs text-muted-foreground">
            Theo dõi số token và các lượt gọi mô hình.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 text-xs"
          onClick={() => {
            void quotaQuery.refetch();
            if (canViewUsage) void usageQuery.refetch();
          }}
          disabled={quotaQuery.isFetching || usageQuery.isFetching}
        >
          <RefreshCw
            className={
              quotaQuery.isFetching || usageQuery.isFetching
                ? "size-3.5 animate-spin"
                : "size-3.5"
            }
          />
          <span>Làm mới</span>
        </Button>
      </div>

      {quotaQuery.isError ? (
        <ErrorState
          error={quotaQuery.error}
          title="Không đọc được số liệu tháng"
          onRetry={() => void quotaQuery.refetch()}
        />
      ) : quotaQuery.isLoading || !quota ? (
        <Skeleton className="h-28 w-full" />
      ) : (
        <QuotaCard quota={quota} />
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Usage gần đây</h3>
        {!canViewUsage ? (
          <p className="rounded-md border bg-muted/40 px-3 py-2 text-[11px] leading-5">
            Danh sách usage yêu cầu vai trò admin của workspace này. Bạn vẫn xem
            được số liệu tổng hợp ở trên.
          </p>
        ) : usageQuery.isError ? (
          <ErrorState
            error={usageQuery.error}
            title="Không đọc được usage"
            onRetry={() => void usageQuery.refetch()}
          />
        ) : (
          <Card className="overflow-hidden rounded-xl shadow-2xs">
            {usageQuery.isLoading ? (
              <div className="grid gap-2 p-4">
                {[0, 1, 2].map((row) => (
                  <Skeleton key={row} className="h-10 w-full" />
                ))}
              </div>
            ) : (usageQuery.data?.items.length ?? 0) === 0 ? (
              <EmptyState
                icon={Gauge}
                title="Chưa có bản ghi usage"
                description="Workspace chưa phát sinh request nào."
              />
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[170px]">Thời điểm</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead className="hidden md:table-cell">
                        Capability
                      </TableHead>
                      <TableHead className="w-[120px]">Trạng thái</TableHead>
                      <TableHead className="w-[130px] text-right">
                        Tokens
                      </TableHead>
                      <TableHead className="hidden w-[120px] text-right lg:table-cell">
                        Cost (USD)
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(usageQuery.data?.items ?? []).map((record) => (
                      <TableRow key={record.id}>
                        <TableCell className="text-xs text-muted-foreground">
                          {formatDateTimeValue(record.created_at)}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {record.model_name}
                        </TableCell>
                        <TableCell className="hidden text-xs md:table-cell">
                          {record.capability}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[10px]">
                            {record.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right text-xs tabular-nums">
                          {record.total_tokens === null ? (
                            <span className="text-muted-foreground">
                              chưa biết
                            </span>
                          ) : (
                            formatTokens(record.total_tokens)
                          )}
                        </TableCell>
                        <TableCell className="hidden text-right text-xs tabular-nums lg:table-cell">
                          {record.cost_usd === null ? (
                            <span className="text-muted-foreground">
                              chưa biết
                            </span>
                          ) : (
                            record.cost_usd
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <div className="border-t px-3">
                  <DataTablePagination
                    page={usagePage}
                    pageSize={usagePageSize}
                    pageCount={usagePageCount}
                    total={usageTotal}
                    onPageChange={onUsagePageChange}
                    onPageSizeChange={onUsagePageSizeChange}
                  />
                </div>
              </>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}

function QuotaCard({ quota }: { quota: Quota }) {
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Kỳ {quota.month_period}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-2 sm:grid-cols-2">
        <Metric label="Token đã dùng" value={formatTokens(quota.tokens_used)} />
        <Metric
          label="Token đang giữ chỗ"
          value={formatTokens(quota.tokens_reserved)}
        />
      </CardContent>
    </Card>
  );
}
