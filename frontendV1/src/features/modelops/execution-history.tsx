import { RefreshCw } from "lucide-react";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTimeValue } from "@/lib/date-utils";
import { useExecutions } from "./resilience-queries";

export function ExecutionHistory({ providerId }: { providerId: string }) {
  const query = useExecutions(providerId);
  return (
    <div className="space-y-3 border-t pt-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Lượt gọi gần đây</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw className="size-3.5" /> Làm mới
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Tối đa 50 lượt. Token chưa đo giữ là chưa biết; hạn mức vẫn được quản lý
        ở sổ sử dụng của workspace.
      </p>
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.isPending ? (
        <Skeleton className="h-16" />
      ) : !query.data?.length ? (
        <p className="text-sm text-muted-foreground">
          Chưa có lượt gọi runtime nào.
        </p>
      ) : (
        <div className="grid gap-2 lg:grid-cols-2">
          {query.data.map((item) => (
            <div
              key={item.id}
              className="min-w-0 space-y-2 rounded-md border p-3 text-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="break-all font-medium">
                  {item.model_name} · {item.capability}
                </span>
                <Badge variant={item.code === "ok" ? "success" : "warning"}>
                  {item.code === "ok"
                    ? "Thành công"
                    : item.code === "cancelled"
                      ? "Đã dừng"
                      : "Gặp lỗi"}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                {formatDateTimeValue(item.created_at)} · lần {item.attempt} ·{" "}
                {item.latency_ms === null
                  ? "Chưa đo thời gian"
                  : `${item.latency_ms} ms`}{" "}
                ·{" "}
                {item.total_tokens === null
                  ? "Chưa biết token"
                  : `${item.total_tokens} token`}
              </p>
              <p className="break-all text-xs text-muted-foreground">
                {item.code}
                {item.upstream_status === null
                  ? ""
                  : ` · HTTP ${item.upstream_status}`}
              </p>
              <details>
                <summary className="cursor-pointer text-xs text-muted-foreground">
                  Mã truy vết
                </summary>
                <p className="mt-1 break-all font-mono text-xs">
                  Lượt: {item.call_id}
                  <br />
                  Khóa: {item.key_id ?? "Không dùng"}
                  <br />
                  Sổ sử dụng: {item.usage_id ?? "Chưa gắn"}
                </p>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
