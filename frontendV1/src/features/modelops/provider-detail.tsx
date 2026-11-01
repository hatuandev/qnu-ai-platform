import { Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowLeft,
  CirclePower,
  Cpu,
  History,
  Pencil,
  RotateCcw,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BUDGET_SOURCE_LABELS,
  BUDGET_STATUS_LABELS,
  CapacityBadge,
  formatTokenLimitValue,
  OperationalBudgetBadge,
  ProviderOperationalBudgetsSummary,
  resolveCapabilityBudgetState,
} from "@/features/modelops/capacity-badge";
import { buildClearTokenLimitsPatch } from "@/features/modelops/capacity-patch";
import { ProviderDiagnosticsPanel } from "@/features/modelops/diagnostics-panel";
import { KeyEventsPanel } from "@/features/modelops/key-events-panel";
import { KeysPanel } from "@/features/modelops/keys-panel";
import { ProviderFormDialog } from "@/features/modelops/provider-form-dialog";
import {
  useProviderQuery,
  useUpdateProvider,
} from "@/features/modelops/queries";
import { ProviderResiliencePanel } from "@/features/modelops/resilience-panel";
import {
  type BudgetSource,
  CAPABILITY_LABELS,
  type Capability,
  PROVIDER_TYPE_LABELS,
  type Provider,
  type TokenLimits,
} from "@/features/modelops/types";
import { formatDateTimeValue } from "@/lib/date-utils";

function resolveFieldSource(
  provider: Provider,
  field: keyof TokenLimits,
): BudgetSource | null {
  if (provider.field_sources?.[field]) {
    return provider.field_sources[field];
  }
  if (provider.operational_budgets) {
    for (const budget of Object.values(provider.operational_budgets)) {
      const src1 = budget?.sources?.[field];
      if (src1) return src1;
    }
  }
  return provider.capacity_basis ?? null;
}

function LimitRow({
  label,
  value,
  source,
}: {
  label: string;
  value: string;
  source?: BudgetSource | null;
}) {
  const isUnknown = value === "Chưa công bố";
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2 border-b py-2 last:border-b-0">
      <dt className="font-mono text-xs text-muted-foreground">{label}</dt>
      <dd className="flex flex-wrap items-center gap-1.5 text-xs font-medium">
        <span
          className={isUnknown ? "text-muted-foreground" : "text-foreground"}
        >
          {value}
        </span>
        {source ? (
          <Badge variant="outline" className="text-[10px] font-normal">
            {BUDGET_SOURCE_LABELS[source]}
          </Badge>
        ) : null}
      </dd>
    </div>
  );
}

export function CapacityPanel({
  provider,
  canManage = false,
  onEdit,
  onClearDeclaredLimits,
  isClearing = false,
}: {
  provider: Provider;
  canManage?: boolean;
  onEdit?: () => void;
  onClearDeclaredLimits?: () => void;
  isClearing?: boolean;
}) {
  const updateMutation = useUpdateProvider(provider.id);
  const [confirmClearOpen, setConfirmClearOpen] = useState(false);

  const limits = provider.token_limits;
  const ocr = limits?.ocr_page_input ?? null;
  const capabilities = (provider.capabilities ?? []) as Capability[];
  const hasOperationalBudgets = Boolean(
    provider.operational_budgets &&
      Object.keys(provider.operational_budgets).length > 0,
  );
  const clearing = isClearing || updateMutation.isPending;

  const handleConfirmClear = async () => {
    try {
      await updateMutation.mutateAsync(buildClearTokenLimitsPatch());
      toast.success(
        "Đã xóa khai báo giới hạn; model chuyển sang dùng ngân sách vận hành tự động.",
      );
      setConfirmClearOpen(false);
    } catch (error) {
      toast.error(
        error instanceof ApiProblemError
          ? error.message
          : "Không thể xóa khai báo giới hạn.",
      );
    }
  };

  return (
    <Card className="rounded-xl shadow-2xs">
      <CardHeader className="flex flex-col gap-3 pb-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-sm">
            Giới hạn model & Ngân sách vận hành
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Phân biệt thông số kỹ thuật đã biết của model với ngân sách vận hành
            đang áp dụng theo từng chức năng (đơn vị: token).
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <CapacityBadge
            status={provider.capacity_status}
            basis={provider.capacity_basis}
          />
          {canManage && onEdit ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={onEdit}
            >
              <Pencil className="size-3.5" />
              <span>Khai báo / cập nhật</span>
            </Button>
          ) : null}
          {canManage && provider.token_limits !== null ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              disabled={clearing}
              onClick={() => {
                if (onClearDeclaredLimits) {
                  onClearDeclaredLimits();
                } else {
                  setConfirmClearOpen(true);
                }
              }}
            >
              <RotateCcw className="size-3.5" />
              <span>Xóa khai báo giới hạn</span>
            </Button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-6 text-sm">
        {provider.capacity_status === "stale" ? (
          <p className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-xs leading-5">
            <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" />
            <span>
              Endpoint hoặc model đã thay đổi sau lần khai báo trước, nên số
              liệu cũ không còn áp dụng. Cần lấy lại hoặc cập nhật thông số
              trước khi chạy.
            </span>
          </p>
        ) : null}

        {provider.embedding_dimension_status === "stale" ? (
          <p className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-xs leading-5">
            <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" />
            <span>
              embedding_dimension cần cập nhật lại: model hoặc endpoint đã đổi
              sau lần khai báo trước.
            </span>
          </p>
        ) : null}

        {/* Phần 1: Giới hạn đã biết của model */}
        <section className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-1.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Giới hạn đã biết của model
            </h3>
            <span className="text-xs text-muted-foreground">
              Nguồn:{" "}
              {provider.capacity_basis
                ? BUDGET_SOURCE_LABELS[provider.capacity_basis]
                : "Chưa công bố"}
            </span>
          </div>

          <dl className="grid gap-x-6 sm:grid-cols-2">
            <LimitRow
              label="context_window_tokens"
              value={formatTokenLimitValue(limits?.context_window_tokens)}
              source={
                limits?.context_window_tokens != null
                  ? resolveFieldSource(provider, "context_window_tokens")
                  : null
              }
            />
            <LimitRow
              label="max_input_tokens"
              value={formatTokenLimitValue(limits?.max_input_tokens)}
              source={
                limits?.max_input_tokens != null
                  ? resolveFieldSource(provider, "max_input_tokens")
                  : null
              }
            />
            <LimitRow
              label="max_output_tokens"
              value={formatTokenLimitValue(limits?.max_output_tokens)}
              source={
                limits?.max_output_tokens != null
                  ? resolveFieldSource(provider, "max_output_tokens")
                  : null
              }
            />
            <LimitRow
              label="embedding_dimension"
              value={
                provider.embedding_dimension != null
                  ? `${provider.embedding_dimension.toLocaleString("vi-VN")} chiều`
                  : "Chưa công bố"
              }
            />
          </dl>

          <div className="pt-2">
            <p className="mb-1 font-mono text-xs font-medium text-muted-foreground">
              ocr_page_input
            </p>
            {ocr ? (
              <dl className="grid gap-x-6 sm:grid-cols-2">
                <LimitRow
                  label="max_image_width"
                  value={`${ocr.max_image_width.toLocaleString("vi-VN")} px`}
                />
                <LimitRow
                  label="max_image_height"
                  value={`${ocr.max_image_height.toLocaleString("vi-VN")} px`}
                />
                <LimitRow
                  label="input_tokens_upper_bound"
                  value={formatTokenLimitValue(ocr.input_tokens_upper_bound)}
                  source={resolveFieldSource(provider, "ocr_page_input")}
                />
                <LimitRow label="prompt_sha256" value={ocr.prompt_sha256} />
              </dl>
            ) : (
              <p className="text-xs text-muted-foreground">
                Chưa công bố ngân sách token cho một trang ảnh.
              </p>
            )}
          </div>
        </section>

        {/* Phần 2: Ngân sách đang áp dụng */}
        <section className="space-y-3 border-t pt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Ngân sách đang áp dụng
            </h3>
            <span className="text-xs text-muted-foreground">
              Chính sách vận hành từ backend theo từng chức năng
            </span>
          </div>

          {!hasOperationalBudgets ? (
            <p className="text-xs text-muted-foreground">
              {BUDGET_STATUS_LABELS.missing_info}
            </p>
          ) : (
            <div className="divide-y">
              {capabilities.map((cap) => {
                const resolved = resolveCapabilityBudgetState(provider, cap);
                const budget = resolved.budget;
                const budgetLimits = budget?.token_limits ?? null;
                const sources = budget?.sources ?? {};
                return (
                  <div
                    key={cap}
                    className="space-y-2 py-3 first:pt-1 last:pb-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-foreground">
                        {CAPABILITY_LABELS[cap] ?? cap}
                      </span>
                      <OperationalBudgetBadge
                        model={provider}
                        capability={cap}
                      />
                    </div>

                    {resolved.isBlocked ? (
                      <div className="rounded-md bg-warning/10 px-3 py-2 text-xs text-foreground">
                        <p>{resolved.reason}</p>
                        {resolved.reasonCode ? (
                          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                            Mã lý do: {resolved.reasonCode}
                          </p>
                        ) : null}
                      </div>
                    ) : budgetLimits ? (
                      <dl className="grid gap-x-6 sm:grid-cols-2">
                        <LimitRow
                          label="context_window_tokens"
                          value={formatTokenLimitValue(
                            budgetLimits.context_window_tokens,
                          )}
                          source={sources.context_window_tokens ?? null}
                        />
                        <LimitRow
                          label="max_input_tokens"
                          value={formatTokenLimitValue(
                            budgetLimits.max_input_tokens,
                          )}
                          source={sources.max_input_tokens ?? null}
                        />
                        <LimitRow
                          label="max_output_tokens"
                          value={formatTokenLimitValue(
                            budgetLimits.max_output_tokens,
                          )}
                          source={sources.max_output_tokens ?? null}
                        />
                        {cap === "ocr" ? (
                          <LimitRow
                            label="ocr_page_input"
                            value={
                              budgetLimits.ocr_page_input
                                ? formatTokenLimitValue(
                                    budgetLimits.ocr_page_input
                                      .input_tokens_upper_bound,
                                  )
                                : "Chưa công bố"
                            }
                            source={sources.ocr_page_input ?? null}
                          />
                        ) : null}
                      </dl>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        {BUDGET_STATUS_LABELS.missing_info}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </CardContent>

      <ConfirmDialog
        open={confirmClearOpen}
        onOpenChange={(next) => {
          if (!clearing) setConfirmClearOpen(next);
        }}
        title="Xóa giới hạn token đã khai báo?"
        description={
          <div className="space-y-2 text-xs">
            <p>
              Thao tác này gửi{" "}
              <code className="font-mono">token_limits: null</code> để xóa giới
              hạn đã khai báo của model{" "}
              <strong className="font-mono">{provider.model_name}</strong>.
            </p>
            <p>
              Sau khi xóa, model sẽ chuyển sang dùng ngân sách vận hành tự động
              (tạm tính) của hệ thống cho đến khi được đồng bộ từ server hoặc
              khai báo lại.
            </p>
          </div>
        }
        confirmLabel="Xác nhận xóa khai báo"
        isLoading={clearing}
        onConfirm={() => void handleConfirmClear()}
      />
    </Card>
  );
}

export function ProviderDetail({ providerId }: { providerId: string }) {
  const { actor } = useV1Auth();
  const query = useProviderQuery(providerId);
  const updateMutation = useUpdateProvider(providerId);
  const [editOpen, setEditOpen] = useState(false);
  const [toggleOpen, setToggleOpen] = useState(false);
  const [clearLimitsOpen, setClearLimitsOpen] = useState(false);

  const canManage = isModelAdmin(actor);
  const provider = query.data;

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (query.isError || !provider) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link to="/modelops/providers">
            <ArrowLeft className="size-3.5" />
            Danh sách provider
          </Link>
        </Button>
        <ErrorState
          error={query.error}
          title="Không mở được provider"
          onRetry={() => void query.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          {provider.parent_id ? (
            <Link
              to="/modelops/providers/$providerId"
              params={{ providerId: provider.parent_id }}
            >
              <ArrowLeft className="size-3.5" />
              Nhà cung cấp
            </Link>
          ) : (
            <Link to="/modelops/providers">
              <ArrowLeft className="size-3.5" />
              Nhà cung cấp
            </Link>
          )}
        </Button>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0 space-y-1.5">
            <p className="type-metadata font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              QNU AI · ModelOps · Model
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="type-page-title m-0 truncate">
                {provider.parent_id ? provider.model_name : provider.name}
              </h1>
              {provider.is_active ? (
                <Badge variant="success">Đang bật</Badge>
              ) : (
                <Badge variant="secondary">Đang tắt</Badge>
              )}
              <ProviderOperationalBudgetsSummary
                provider={provider}
                showBasis
              />
            </div>
            <p className="font-mono text-xs text-muted-foreground">
              {PROVIDER_TYPE_LABELS[provider.provider_type]} ·{" "}
              {provider.model_name}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              className="gap-1.5 text-xs"
              disabled={!canManage || updateMutation.isPending}
              title={
                canManage ? undefined : "Cần quyền ai.models.manage để sửa"
              }
              onClick={() => setEditOpen(true)}
            >
              <Pencil className="size-3.5" />
              <span>Sửa</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              disabled={!canManage || updateMutation.isPending}
              title={
                canManage
                  ? undefined
                  : "Cần quyền ai.models.manage để đổi trạng thái"
              }
              onClick={() => setToggleOpen(true)}
            >
              <CirclePower className="size-3.5" />
              <span>{provider.is_active ? "Tắt model" : "Bật model"}</span>
            </Button>
          </div>
        </div>

        <Card className="rounded-xl shadow-2xs">
          <CardContent className="grid gap-3 py-4 text-xs sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-muted-foreground">Base URL</p>
              <p className="mt-0.5 break-all font-mono">{provider.base_url}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Capabilities</p>
              <p className="mt-0.5">
                {provider.capabilities.length === 0
                  ? "—"
                  : provider.capabilities
                      .map(
                        (capability) =>
                          CAPABILITY_LABELS[capability as Capability] ??
                          capability,
                      )
                      .join(", ")}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Priority / Timeout</p>
              <p className="mt-0.5">
                {provider.priority} · {provider.timeout_seconds}s
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Cập nhật</p>
              <p className="mt-0.5">
                {formatDateTimeValue(provider.updated_at)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {!canManage ? (
        <p className="flex items-start gap-2 rounded-md border bg-muted/40 px-3 py-2 text-[11px] leading-5">
          <ShieldAlert className="mt-0.5 size-3.5 shrink-0" />
          <span>
            Tài khoản của bạn không có quyền ai.models.manage. Trang chỉ đọc;
            mọi thao tác ghi đều bị máy chủ từ chối.
          </span>
        </p>
      ) : null}

      {/* 1. AI Server Keys block placed near top for fast access */}
      {!provider.parent_id ? (
        <KeysPanel providerId={providerId} />
      ) : (
        <Button asChild variant="outline">
          <Link
            to="/modelops/providers/$providerId"
            params={{ providerId: provider.parent_id }}
          >
            Quản lý API key tại nhà cung cấp
          </Link>
        </Button>
      )}

      {/* 2. Connection Diagnostics & Functional Probing block */}
      <ProviderDiagnosticsPanel provider={provider} />

      {/* 3. Advanced Configuration Tabs: Resilience, Declared Capacity, and Event History */}
      <div className="space-y-4 pt-2">
        <div className="border-b pb-2">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">
            Cấu hình nâng cao & Lịch sử
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Các chính sách phục hồi, giới hạn token đã biết, ngân sách đang áp
            dụng và nhật ký kiểm toán khóa.
          </p>
        </div>

        <Tabs defaultValue="capacity" className="w-full">
          <TabsList className="w-full justify-start">
            <TabsTrigger value="capacity" className="gap-1.5 text-xs">
              <Cpu className="size-3.5" />
              <span>Giới hạn & Ngân sách</span>
            </TabsTrigger>
            <TabsTrigger value="resilience" className="gap-1.5 text-xs">
              <Activity className="size-3.5" />
              <span>Dự phòng & Phục hồi</span>
            </TabsTrigger>
            <TabsTrigger value="events" className="gap-1.5 text-xs">
              <History className="size-3.5" />
              <span>Lịch sử sự kiện khóa</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="capacity">
            <CapacityPanel
              provider={provider}
              canManage={canManage}
              isClearing={updateMutation.isPending}
              onClearDeclaredLimits={() => setClearLimitsOpen(true)}
            />
          </TabsContent>

          <TabsContent value="resilience">
            <ProviderResiliencePanel provider={provider} />
          </TabsContent>

          <TabsContent value="events">
            <KeyEventsPanel providerId={providerId} />
          </TabsContent>
        </Tabs>
      </div>

      <ProviderFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        provider={provider}
      />

      <ConfirmDialog
        open={clearLimitsOpen}
        onOpenChange={(open) => {
          if (!updateMutation.isPending) setClearLimitsOpen(open);
        }}
        title="Xóa giới hạn token đã khai báo?"
        description={
          <div className="space-y-2 text-xs">
            <p>
              Thao tác này gửi{" "}
              <code className="font-mono">token_limits: null</code> để xóa thông
              số giới hạn đã lưu của model{" "}
              <strong className="font-mono">{provider.model_name}</strong>.
            </p>
            <p>
              Model sẽ chuyển sang dùng ngân sách vận hành tự động (tạm tính) do
              backend quyết định cho đến khi được đồng bộ từ server hoặc khai
              báo lại.
            </p>
          </div>
        }
        confirmLabel="Xác nhận xóa khai báo"
        isLoading={updateMutation.isPending}
        onConfirm={() => {
          void updateMutation
            .mutateAsync(buildClearTokenLimitsPatch())
            .then(() => {
              setClearLimitsOpen(false);
              toast.success(
                "Đã xóa khai báo giới hạn; model dùng ngân sách vận hành tự động.",
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof ApiProblemError
                  ? error.message
                  : "Không xóa được khai báo giới hạn.",
              ),
            );
        }}
      />

      <ConfirmDialog
        open={toggleOpen}
        onOpenChange={(open) => {
          if (!updateMutation.isPending) setToggleOpen(open);
        }}
        title={provider.is_active ? "Tắt model?" : "Bật lại model?"}
        description={
          provider.is_active
            ? "Model bị tắt sẽ không còn trong catalog cấp cho workspace và không dùng cho request mới. Cấu hình, key và năng lực đã khai báo vẫn được giữ nguyên."
            : "Model trở lại trạng thái hoạt động và có thể được cấp cho workspace."
        }
        confirmLabel={provider.is_active ? "Tắt model" : "Bật model"}
        confirmVariant={provider.is_active ? "destructive" : "default"}
        isLoading={updateMutation.isPending}
        onConfirm={() => {
          void updateMutation
            .mutateAsync({ is_active: !provider.is_active })
            .then(() => {
              setToggleOpen(false);
              toast.success(
                provider.is_active ? "Đã tắt model." : "Đã bật lại model.",
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof ApiProblemError
                  ? error.message
                  : "Không đổi được trạng thái model.",
              ),
            );
        }}
      />
    </div>
  );
}
