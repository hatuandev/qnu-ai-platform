import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  CirclePower,
  Pencil,
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
import { CapacityBadge } from "@/features/modelops/capacity-badge";
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
  CAPABILITY_LABELS,
  type Capability,
  PROVIDER_TYPE_LABELS,
  type Provider,
} from "@/features/modelops/types";
import { formatDateTimeValue } from "@/lib/date-utils";

function DeclaredValue({
  label,
  value,
}: {
  label: string;
  value: number | string | null;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b py-1.5 last:border-b-0">
      <dt className="font-mono text-[11px] text-muted-foreground">{label}</dt>
      <dd className="break-all text-xs font-medium">
        {value === null ? (
          <span className="text-muted-foreground">chưa khai báo</span>
        ) : (
          value
        )}
      </dd>
    </div>
  );
}

function CapacityPanel({ provider }: { provider: Provider }) {
  const limits = provider.token_limits;
  const ocr = limits?.ocr_page_input ?? null;

  return (
    <Card className="rounded-xl shadow-2xs">
      <CardHeader className="flex flex-row items-center justify-between gap-2 pb-2">
        <CardTitle className="text-sm">Năng lực đã khai báo</CardTitle>
        <div className="flex flex-wrap items-center gap-1.5">
          <CapacityBadge status={provider.capacity_status} />
          {provider.capacity_basis ? (
            <Badge variant="outline" className="text-[10px]">
              {provider.capacity_basis}
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-[11px] leading-5 text-muted-foreground">
          Đây là khai báo của quản trị viên, không phải giá trị đo hay kiểm
          chứng từ provider. &quot;Chưa khai báo&quot; không có nghĩa là không
          giới hạn.
        </p>

        {provider.capacity_status === "stale" ? (
          <p className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-[11px] leading-5">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
            <span>
              Endpoint hoặc model đã thay đổi sau lần khai báo trước, nên số
              liệu cũ không còn áp dụng. Cần khai báo lại để dùng cho tính toán.
            </span>
          </p>
        ) : null}

        <dl className="grid gap-x-6 sm:grid-cols-2">
          <DeclaredValue
            label="context_window_tokens"
            value={limits?.context_window_tokens ?? null}
          />
          <DeclaredValue
            label="max_input_tokens"
            value={limits?.max_input_tokens ?? null}
          />
          <DeclaredValue
            label="max_output_tokens"
            value={limits?.max_output_tokens ?? null}
          />
          <DeclaredValue
            label="embedding_dimension"
            value={provider.embedding_dimension}
          />
        </dl>

        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            ocr_page_input
          </p>
          {ocr ? (
            <dl className="grid gap-x-6 sm:grid-cols-2">
              <DeclaredValue
                label="max_image_width"
                value={ocr.max_image_width}
              />
              <DeclaredValue
                label="max_image_height"
                value={ocr.max_image_height}
              />
              <DeclaredValue
                label="input_tokens_upper_bound"
                value={ocr.input_tokens_upper_bound}
              />
              <DeclaredValue label="prompt_sha256" value={ocr.prompt_sha256} />
            </dl>
          ) : (
            <p className="text-[11px] text-muted-foreground">
              Chưa khai báo ngân sách token cho một trang ảnh.
            </p>
          )}
        </div>

        {provider.embedding_dimension_status === "stale" ? (
          <p className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-[11px] leading-5">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
            <span>
              embedding_dimension cần khai báo lại: model hoặc endpoint đã đổi
              sau lần khai báo trước.
            </span>
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function ProviderDetail({ providerId }: { providerId: string }) {
  const { actor } = useV1Auth();
  const query = useProviderQuery(providerId);
  const updateMutation = useUpdateProvider(providerId);
  const [editOpen, setEditOpen] = useState(false);
  const [toggleOpen, setToggleOpen] = useState(false);

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
          <Link to="/modelops/providers">
            <ArrowLeft className="size-3.5" />
            Danh sách provider
          </Link>
        </Button>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0">
            <p className="type-metadata mb-2 font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              QNU AI · ModelOps · Provider
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="type-page-title m-0 truncate">{provider.name}</h1>
              {provider.is_active ? (
                <Badge variant="success">Đang bật</Badge>
              ) : (
                <Badge variant="secondary">Đang tắt</Badge>
              )}
            </div>
            <p className="mt-1.5 font-mono text-xs text-muted-foreground">
              {PROVIDER_TYPE_LABELS[provider.provider_type]} ·{" "}
              {provider.model_name} · {provider.id}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
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
              <span>
                {provider.is_active ? "Tắt provider" : "Bật provider"}
              </span>
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

      <ProviderDiagnosticsPanel provider={provider} />
      <ProviderResiliencePanel provider={provider} />
      <CapacityPanel provider={provider} />
      <KeysPanel providerId={providerId} />
      <KeyEventsPanel providerId={providerId} />

      <ProviderFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        provider={provider}
      />

      <ConfirmDialog
        open={toggleOpen}
        onOpenChange={(open) => {
          if (!updateMutation.isPending) setToggleOpen(open);
        }}
        title={provider.is_active ? "Tắt provider?" : "Bật lại provider?"}
        description={
          provider.is_active
            ? "Provider bị tắt sẽ không còn trong catalog cấp cho workspace và không dùng cho request mới. Cấu hình, key và năng lực đã khai báo vẫn được giữ nguyên."
            : "Provider trở lại trạng thái hoạt động và có thể được cấp cho workspace."
        }
        confirmLabel={provider.is_active ? "Tắt provider" : "Bật provider"}
        confirmVariant={provider.is_active ? "destructive" : "default"}
        isLoading={updateMutation.isPending}
        onConfirm={() => {
          void updateMutation
            .mutateAsync({ is_active: !provider.is_active })
            .then(() => {
              setToggleOpen(false);
              toast.success(
                provider.is_active
                  ? "Đã tắt provider."
                  : "Đã bật lại provider.",
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof ApiProblemError
                  ? error.message
                  : "Không đổi được trạng thái provider.",
              ),
            );
        }}
      />
    </div>
  );
}
