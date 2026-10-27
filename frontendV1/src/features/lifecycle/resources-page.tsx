import { Link } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, RefreshCw, Trash2 } from "lucide-react";
import { useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { LifecycleReceipt } from "./action-receipt";
import { LifecycleActions } from "./lifecycle-actions";
import { useArchivedResources } from "./queries";
import { RESOURCE_LABEL } from "./types";

type Props = {
  workspaceId: string;
  page: number;
  actionId?: string;
  onPageChange: (page: number) => void;
};
export function ResourcesPage(props: Props) {
  const { sessionId } = useV1Auth();
  return (
    <ResourceSession key={`${sessionId}:${props.workspaceId}`} {...props} />
  );
}
function ResourceSession({ workspaceId, page, actionId, onPageChange }: Props) {
  const { role, isPending } = useCallerWorkspaceRole(workspaceId);
  const allowed = role.kind === "member" || role.kind === "platform-admin";
  const query = useArchivedResources(workspaceId, page, allowed && !isPending);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="type-page-title flex items-center gap-2">
            <Trash2 className="size-5" />
            Lưu trữ &amp; Thùng rác
          </h1>
          <p className="text-sm text-muted-foreground">
            Xóa có thể khôi phục. Bản gốc, raw OCR và lịch sử vẫn được giữ.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => void query.refetch()}
          disabled={!allowed || query.isFetching}
        >
          <RefreshCw className="size-3.5" />
          Làm mới
        </Button>
      </div>
      {actionId && allowed ? (
        <LifecycleReceipt workspaceId={workspaceId} actionId={actionId} />
      ) : null}
      {isPending ? (
        <p role="status">Đang kiểm tra quyền…</p>
      ) : !allowed ? (
        <p role="alert">Bạn không có quyền truy cập đơn vị này.</p>
      ) : query.isPending ? (
        <p role="status">Đang đọc tài nguyên lưu trữ…</p>
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <>
          <div className="grid gap-3 lg:grid-cols-2">
            {query.data.items.slice(0, 20).map((resource) => (
              <Card
                key={`${resource.kind}:${resource.resource_id}`}
                className="rounded-xl shadow-2xs"
              >
                <CardContent className="space-y-3 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h2 className="font-medium text-sm">
                      {RESOURCE_LABEL[resource.kind]}{" "}
                      <span className="text-muted-foreground">
                        #{resource.resource_id.slice(-8)}
                      </span>
                    </h2>
                    <Badge
                      variant={
                        resource.status === "deleted" ? "warning" : "outline"
                      }
                    >
                      {resource.status === "deleted"
                        ? "Trong thùng rác"
                        : "Đã lưu trữ"}
                    </Badge>
                  </div>
                  <p className="break-all text-xs text-muted-foreground">
                    {resource.resource_id} ·{" "}
                    {formatDateTimeValue(resource.updated_at)}
                  </p>
                  <LifecycleActions
                    workspaceId={workspaceId}
                    kind={resource.kind}
                    resourceId={resource.resource_id}
                    label={`${RESOURCE_LABEL[resource.kind]} #${resource.resource_id.slice(-8)}`}
                    role={role}
                    status={resource.status}
                    ownedConversation={resource.kind === "conversation"}
                  />
                </CardContent>
              </Card>
            ))}
          </div>
          {query.data.items.length === 0 ? (
            <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              Trang này không có tài nguyên lưu trữ hoặc đã xóa trong phạm vi
              quyền của bạn.
            </p>
          ) : null}
          <div className="flex items-center justify-end gap-2 text-sm">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              <ChevronLeft className="size-4" />
              Trước
            </Button>
            <span>Trang {page}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={query.data.items.length <= 20}
              onClick={() => onPageChange(page + 1)}
            >
              Sau
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </>
      )}
      <p className="text-xs text-muted-foreground">
        Khôi phục không tự chạy lại tác vụ đã hủy; trợ lý được khôi phục vẫn ở
        trạng thái tắt. Nếu cần chỉ mục mới, mở{" "}
        <Link
          to="/workspaces/$workspaceId/collections"
          params={{ workspaceId }}
          search={{ page: 1, pageSize: 20 }}
          className="text-primary underline"
        >
          kho tri thức
        </Link>{" "}
        để chuẩn bị lại.
      </p>
    </div>
  );
}
