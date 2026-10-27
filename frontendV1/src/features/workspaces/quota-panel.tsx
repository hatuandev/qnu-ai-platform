import { Gauge, Loader2, RefreshCw, Save } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { canManageMembers, isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
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
  usePutQuota,
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
  const { actor } = useV1Auth();
  const { role } = useCallerWorkspaceRole(workspaceId);
  const quotaQuery = useQuotaQuery(workspaceId);
  const putQuota = usePutQuota(workspaceId);

  const canEdit = isModelAdmin(actor);
  // `GET /usage` requires the workspace `admin` role; asking as a plain member
  // would only produce a guaranteed 403, so the call is skipped and explained.
  const canViewUsage = canManageMembers(role);

  const usageQuery = useUsageQuery(
    workspaceId,
    { page: usagePage, pageSize: usagePageSize },
    { enabled: canViewUsage },
  );

  const quota = quotaQuery.data;
  const [prevWorkspaceId, setPrevWorkspaceId] = useState(workspaceId);
  const [limitDraft, setLimitDraft] = useState<string | null>(null);
  const [blockedDraft, setBlockedDraft] = useState<boolean | null>(null);

  if (prevWorkspaceId !== workspaceId) {
    setPrevWorkspaceId(workspaceId);
    setLimitDraft(null);
    setBlockedDraft(null);
  }

  const limitValue =
    limitDraft ?? (quota ? (quota.monthly_token_limit?.toString() ?? "") : "");
  const blockedValue = blockedDraft ?? quota?.is_blocked ?? false;

  const MAX_TOKEN_LIMIT = 1_000_000_000_000_000; // 10^15
  const trimmedLimit = limitValue.trim();
  const limitInvalid =
    trimmedLimit !== "" &&
    (!/^\d+$/.test(trimmedLimit) || Number(trimmedLimit) > MAX_TOKEN_LIMIT);

  const dirty =
    quota !== undefined &&
    (trimmedLimit !== (quota.monthly_token_limit?.toString() ?? "") ||
      blockedValue !== quota.is_blocked);

  const usageTotal = usageQuery.data?.meta.total ?? 0;
  const usagePageCount = Math.max(1, Math.ceil(usageTotal / usagePageSize));

  const save = () => {
    if (limitInvalid) return;
    const nextLimit = trimmedLimit === "" ? null : Number(trimmedLimit);
    void putQuota
      .mutateAsync({
        monthly_token_limit: nextLimit,
        is_blocked: blockedValue,
      })
      .then(() => {
        setLimitDraft(null);
        setBlockedDraft(null);
        toast.success("Đã lưu hạn mức token.");
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof ApiProblemError
            ? error.message
            : "Không lưu được hạn mức.",
        ),
      );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Quota &amp; usage</h2>
          <p className="text-xs text-muted-foreground">
            Số liệu theo tháng do backendV1 trả về. &quot;Chưa cấu hình&quot;
            không đồng nghĩa với không giới hạn.
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
          title="Không đọc được quota"
          onRetry={() => void quotaQuery.refetch()}
        />
      ) : quotaQuery.isLoading || !quota ? (
        <Skeleton className="h-28 w-full" />
      ) : (
        <QuotaCard quota={quota} />
      )}

      {quota ? (
        <Card className="rounded-xl shadow-2xs">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Điều chỉnh hạn mức</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!canEdit ? (
              <p className="text-[11px] text-muted-foreground">
                Cần quyền ai.models.manage để sửa quota; thành viên workspace
                chỉ đọc được số liệu.
              </p>
            ) : null}
            <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
              <div className="grid gap-1.5">
                <label htmlFor="quota-limit" className="text-xs font-medium">
                  monthly_token_limit
                </label>
                <Input
                  id="quota-limit"
                  inputMode="numeric"
                  className="h-9 text-xs font-mono"
                  placeholder="Để trống = không giới hạn"
                  value={limitValue}
                  disabled={!canEdit || putQuota.isPending}
                  onChange={(event) => setLimitDraft(event.target.value)}
                  aria-invalid={limitInvalid}
                />
                <p className="text-[11px] text-muted-foreground">
                  Để trống sẽ gửi <code className="font-mono">null</code>: cấu
                  hình không giới hạn token hàng tháng, không phải 0.
                </p>
                {limitInvalid ? (
                  <p role="alert" className="text-[11px] text-destructive">
                    Hạn mức phải là số nguyên không âm và không vượt quá
                    1.000.000.000.000.000 (10^15).
                  </p>
                ) : null}
              </div>
              <div className="flex items-center gap-2 pb-6">
                <Switch
                  id="quota-blocked"
                  checked={blockedValue}
                  disabled={!canEdit || putQuota.isPending}
                  onCheckedChange={setBlockedDraft}
                />
                <label htmlFor="quota-blocked" className="text-xs">
                  Chặn workspace
                </label>
              </div>
              <Button
                size="sm"
                className="mb-6 gap-1.5 text-xs font-semibold"
                disabled={
                  !canEdit || !dirty || limitInvalid || putQuota.isPending
                }
                onClick={save}
              >
                {putQuota.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Save className="size-3.5" />
                )}
                <span>Lưu quota</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Usage gần đây</h3>
        {!canViewUsage ? (
          <p className="rounded-md border bg-muted/40 px-3 py-2 text-[11px] leading-5">
            Danh sách usage yêu cầu vai trò admin của workspace này. Bạn vẫn xem
            được quota tổng hợp ở trên.
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
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm">Kỳ {quota.month_period}</CardTitle>
        <div className="flex items-center gap-1.5">
          {quota.configured ? (
            <Badge variant="info">
              {quota.monthly_token_limit === null
                ? "Đã cấu hình (không giới hạn)"
                : "Đã cấu hình hạn mức"}
            </Badge>
          ) : (
            <Badge variant="secondary">Chưa cấu hình hạn mức</Badge>
          )}
          {quota.is_blocked ? (
            <Badge variant="destructive">Đang chặn</Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Metric
          label="Đã dùng"
          value={formatTokens(quota.tokens_used)}
          hint="tokens_used"
        />
        <Metric
          label="Đang giữ chỗ"
          value={formatTokens(quota.tokens_reserved)}
          hint="tokens_reserved"
        />
        <Metric
          label="Hạn mức tháng"
          value={
            !quota.configured
              ? "chưa cấu hình"
              : quota.monthly_token_limit === null
                ? "không giới hạn"
                : formatTokens(quota.monthly_token_limit)
          }
          hint={
            !quota.configured
              ? "chưa cấu hình qua ModelOps"
              : quota.monthly_token_limit === null
                ? "không bị chặn theo token"
                : "monthly_token_limit"
          }
        />
        <Metric
          label="Còn lại"
          value={
            !quota.configured
              ? "chưa cấu hình"
              : quota.monthly_token_limit === null
                ? "không giới hạn"
                : formatTokens(
                    Math.max(
                      0,
                      quota.monthly_token_limit -
                        quota.tokens_used -
                        quota.tokens_reserved,
                    ),
                  )
          }
          hint={
            !quota.configured
              ? "cần cấu hình để dùng model"
              : quota.monthly_token_limit === null
                ? "không áp trần token"
                : "tính từ hạn mức đã khai báo"
          }
        />
      </CardContent>
    </Card>
  );
}
