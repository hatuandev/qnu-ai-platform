import { Link } from "@tanstack/react-router";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useLifecycleAction } from "./queries";
import { RetryLifecycleAction } from "./retry-action";
import type { LifecycleAction } from "./types";
import { ACTION_LABEL } from "./types";

export function LifecycleReceipt({
  workspaceId,
  actionId,
}: {
  workspaceId: string;
  actionId: string;
}) {
  const query = useLifecycleAction(workspaceId, actionId);
  if (query.isPending) return <p role="status">Đang đọc biên nhận thao tác…</p>;
  if (query.isError)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  return <LifecycleReceiptView workspaceId={workspaceId} action={query.data} />;
}
export function LifecycleReceiptView({
  workspaceId,
  action,
}: {
  workspaceId: string;
  action: LifecycleAction;
}) {
  const labels: Record<string, string> = {
    preview: "Chưa xác nhận",
    pending: "Đang xử lý",
    completed: "Hoàn tất",
    failed: "Thất bại",
  };
  return (
    <div className="space-y-2 rounded-lg border p-3 text-sm" aria-live="polite">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{ACTION_LABEL[action.action]}</span>
        <Badge variant={action.status === "failed" ? "destructive" : "outline"}>
          {labels[action.status] ?? action.status}
        </Badge>
      </div>
      <p className="break-all text-xs text-muted-foreground">
        Biên nhận: {action.id}
      </p>
      {action.status === "pending" && action.accepted_at ? (
        <RetryLifecycleAction
          key={action.id}
          workspaceId={workspaceId}
          action={action}
        />
      ) : null}
      {action.error_code ? (
        <p role="alert" className="text-destructive">
          {action.error_code}
        </p>
      ) : null}
      {action.status === "pending" && action.action === "replace" ? (
        <p>
          Bản cũ tiếp tục phục vụ trong khi chỉ mục mới được chuẩn bị. Chưa
          chuyển sang bản mới.
        </p>
      ) : null}
      {typeof action.result?.index_run_id === "string" ? (
        <p className="break-all text-xs">
          Lượt chỉ mục: {action.result.index_run_id}
        </p>
      ) : null}
      {action.result?.upstream_abort_guaranteed === false ? (
        <p className="text-xs text-muted-foreground">
          Đã hủy tại QNU; server AI có thể vẫn hoàn tất yêu cầu đã nhận. Usage
          được giữ theo số đo thực tế.
        </p>
      ) : null}
      {action.action === "restore" &&
      action.kind === "assistant" &&
      action.status === "completed" ? (
        <p>Đã khôi phục trợ lý ở trạng thái tắt. Hãy bật lại khi sẵn sàng.</p>
      ) : null}
      {action.kind === "conversation" || action.kind === "job" ? (
        <Button asChild size="sm" variant="outline">
          <Link
            to="/workspaces/$workspaceId/resources"
            params={{ workspaceId }}
            search={{ page: 1, actionId: action.id }}
          >
            Theo dõi biên nhận
          </Link>
        </Button>
      ) : (
        <Button asChild size="sm" variant="outline">
          <Link
            to="/workspaces/$workspaceId/operations"
            params={{ workspaceId }}
            search={{ page: 1, pageSize: 20, lifecycleActionId: action.id }}
          >
            Theo dõi biên nhận
          </Link>
        </Button>
      )}
    </div>
  );
}
