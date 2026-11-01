import { Download, FlaskConical, Loader2 } from "lucide-react";
import { useState } from "react";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTimeValue } from "@/lib/date-utils";
import { describeDiagnosticFailure } from "./capacity-badge";
import {
  type DiagnosticCheck,
  useDiagnostics,
  useRunDiagnostic,
} from "./diagnostic-queries";
import { ProviderFormDialog } from "./provider-form-dialog";
import { CAPABILITIES, CAPABILITY_LABELS, type Provider } from "./types";

function Result({ check }: { check: DiagnosticCheck }) {
  const stale = check.configuration_status === "stale";
  const failureInfo =
    check.outcome === "failed"
      ? describeDiagnosticFailure({
          code: check.code,
          httpStatus: check.http_status,
          detail: check.detail,
        })
      : null;

  return (
    <div className="space-y-2 rounded-lg border p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">
          {check.kind === "discovery"
            ? "Danh sách model"
            : CAPABILITY_LABELS[check.kind]}
        </span>
        <Badge
          variant={
            stale
              ? "warning"
              : check.outcome === "ok"
                ? "success"
                : check.outcome === "failed"
                  ? "destructive"
                  : "secondary"
          }
        >
          {stale
            ? "Cần thử lại"
            : check.outcome === "ok"
              ? check.kind === "discovery"
                ? "Đã lấy danh sách"
                : "Thử thành công"
              : check.outcome === "failed"
                ? "Thử thất bại"
                : "Chưa hỗ trợ"}
        </Badge>
      </div>
      {stale && (
        <p className="text-warning">
          Kết quả này cần được thử lại cho cấu hình hiện tại.
        </p>
      )}
      <p>{check.detail}</p>
      {failureInfo && failureInfo.category !== "general" && (
        <p className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">
            {failureInfo.title}:
          </span>{" "}
          {failureInfo.guidance}
        </p>
      )}
      {check.outcome === "ok" && check.kind !== "discovery" && (
        <p className="text-xs text-muted-foreground">
          Mẫu thử chỉ xác nhận kết nối và định dạng phản hồi; không chứng minh
          giới hạn token tối đa và không chuyển ngân sách tạm tính thành đã kiểm
          chứng.
        </p>
      )}
      <p className="break-all font-mono text-xs text-muted-foreground">
        {check.requested_model} · {check.code}
        {check.http_status !== null ? ` · HTTP ${check.http_status}` : ""}
      </p>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span>{formatDateTimeValue(check.tested_at)}</span>
        <span>
          {check.latency_ms === null
            ? "Chưa đo độ trễ"
            : `${check.latency_ms} ms`}
        </span>
        {check.observed_dimension !== null && (
          <span>Số chiều đo được: {check.observed_dimension}</span>
        )}
        {check.total_tokens !== null && (
          <span>Token lượt thử: {check.total_tokens}</span>
        )}
      </div>
      {check.observed_model && (
        <p className="break-all text-xs text-muted-foreground">
          Model server báo: {check.observed_model}
        </p>
      )}
      {check.retry_after && (
        <p className="text-xs">
          Server đề nghị thử lại sau {formatDateTimeValue(check.retry_after)}.
        </p>
      )}
    </div>
  );
}

export function ProviderDiagnosticsPanel({ provider }: { provider: Provider }) {
  const { sessionId, actor, isAuthenticated } = useV1Auth();
  if (!isAuthenticated || !isModelAdmin(actor)) return null;
  return (
    <DiagnosticsContent
      key={`${provider.id}:${sessionId}`}
      provider={provider}
    />
  );
}

function DiagnosticsContent({ provider }: { provider: Provider }) {
  const query = useDiagnostics(provider.id);
  const mutation = useRunDiagnostic(provider.id);
  const [selectedModel, setSelectedModel] = useState("");
  const [editing, setEditing] = useState(false);
  const checks = query.data?.checks ?? [];
  const discovery = checks.find((check) => check.kind === "discovery");
  const available =
    discovery?.configuration_status === "current" && discovery.outcome === "ok"
      ? discovery.models
      : [];
  const model = available.includes(selectedModel) ? selectedModel : "";
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardHeader>
        <CardTitle className="text-sm">Kiểm tra provider</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Trạng thái bật/tắt là cấu hình. Chạy thử mới kiểm tra kết nối và phản
          hồi. Mẫu thử do QNU tạo, không lấy tài liệu của bạn; server có thể
          tính phí lượt gọi.
        </p>
        {!provider.is_active && (
          <p className="text-sm text-muted-foreground">
            Provider đang tắt. Bật lại để lấy danh sách hoặc chạy thử.
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!provider.is_active || mutation.isPending}
            onClick={() => mutation.mutate("discovery")}
          >
            {mutation.isPending && mutation.variables === "discovery" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Download className="size-4" />
            )}
            Lấy danh sách model
          </Button>
          {CAPABILITIES.filter((cap) =>
            provider.capabilities.includes(cap),
          ).map((cap) => (
            <Button
              key={cap}
              variant="outline"
              size="sm"
              disabled={!provider.is_active || mutation.isPending}
              onClick={() => mutation.mutate(cap)}
            >
              {mutation.isPending && mutation.variables === cap ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <FlaskConical className="size-4" />
              )}
              Thử {CAPABILITY_LABELS[cap]}
            </Button>
          ))}
        </div>
        {mutation.isPending && (
          <p role="status" className="text-sm text-muted-foreground">
            Đang chờ server trả kết quả…
          </p>
        )}
        {mutation.isError && <ErrorState error={mutation.error} />}
        {query.isPending ? (
          <Skeleton className="h-20" />
        ) : query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : checks.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Chưa có lần kiểm tra nào.
          </p>
        ) : null}
        {discovery?.configuration_status === "current" &&
          discovery.outcome === "ok" && (
            <div className="space-y-2 rounded-lg border p-3">
              <p className="text-sm">
                Server liệt kê {available.length} model. Có trong danh sách chưa
                có nghĩa đã chạy thử thành công.
              </p>
              {available.length > 0 && (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Select
                    value={model}
                    onValueChange={setSelectedModel}
                    disabled={mutation.isPending}
                  >
                    <SelectTrigger
                      className="w-full sm:max-w-md"
                      aria-label="Model trên server"
                    >
                      <SelectValue placeholder="Chọn model trên server" />
                    </SelectTrigger>
                    <SelectContent>
                      {available.map((id) => (
                        <SelectItem key={id} value={id}>
                          {id}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!model || !provider.is_active}
                    onClick={() => setEditing(true)}
                  >
                    Sửa cấu hình
                  </Button>
                </div>
              )}
            </div>
          )}
        <div className="grid gap-3 lg:grid-cols-2">
          {checks.slice(0, 6).map((check) => (
            <Result key={check.id} check={check} />
          ))}
        </div>
        {editing && (
          <ProviderFormDialog
            open
            onOpenChange={setEditing}
            provider={provider}
            suggestedModel={model}
          />
        )}
      </CardContent>
    </Card>
  );
}
