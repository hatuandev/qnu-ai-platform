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
  const retained = action.result?.current_publication_retained === true;
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
      {action.action === "replace" && action.status === "pending" ? (
        <p>
          Chưa chuyển sang bản mới.{" "}
          {retained
            ? "Máy chủ xác nhận bản xuất bản hiện tại được giữ nguyên trong lúc chuẩn bị chỉ mục mới."
            : "Đang chờ máy chủ xác nhận việc giữ bản xuất bản hiện tại."}
        </p>
      ) : null}
      {action.action === "replace" && action.status === "failed" ? (
        <p>
          Chưa chuyển sang bản mới.{" "}
          {retained
            ? "Máy chủ xác nhận bản xuất bản hiện tại không bị thay đổi; kiểm tra trạng thái phục vụ thực tế ở trang tài liệu."
            : "Không xác nhận được bản xuất bản hiện tại còn được giữ; kiểm tra trạng thái phục vụ thực tế ở trang tài liệu."}
        </p>
      ) : null}
      {action.action === "replace" &&
      action.status === "completed" &&
      action.result?.current_publication_retained === false ? (
        <p>Đã chuyển bản xuất bản và chỉ mục sang phiên bản thay thế.</p>
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
      <Button asChild size="sm" variant="outline">
        <Link
          to="/workspaces/$workspaceId/operations"
          params={{ workspaceId }}
          search={{ page: 1, pageSize: 20, lifecycleActionId: action.id }}
        >
          Theo dõi biên nhận
        </Link>
      </Button>
    </div>
  );
}
