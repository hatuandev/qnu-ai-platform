import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { useOperationAction } from "./queries";
import { acceptRecovery } from "./requests";
import { jobKindSchema } from "./search";
import { type JobKind, statusLabel } from "./types";
export function OperationReceipt({
  workspaceId,
  actionId,
  onJob,
}: {
  workspaceId: string;
  actionId: string;
  onJob: (kind: JobKind, id: string) => void;
}) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const current = useActionScope();
  const query = useOperationAction(workspaceId, actionId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef(false);
  const retry = async () => {
    const action = query.data;
    if (action?.status !== "pending" || active.current) return;
    active.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await acceptRecovery(v1Client, workspaceId, action);
      if (!current()) return;
      await client.cancelQueries({
        queryKey: [
          "v1",
          sessionId,
          "operations-action",
          workspaceId,
          action.id,
        ],
      });
      if (!current()) return;
      client.setQueryData(
        ["v1", sessionId, "operations-action", workspaceId, action.id],
        result,
      );
    } catch (cause) {
      if (current())
        setError(
          cause instanceof Error
            ? cause.message
            : "Chưa tiếp tục được thao tác đã xác nhận.",
        );
    } finally {
      active.current = false;
      if (current()) setBusy(false);
    }
  };
  return (
    <Card>
      <CardContent className="p-4 text-sm space-y-2">
        {query.isPending ? (
          <p role="status">Đang đọc biên nhận giao lại…</p>
        ) : query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : (
          <>
            <p className="break-all">
              {query.data.action === "delete_backup"
                ? "Biên nhận xóa bản sao lưu"
                : "Biên nhận giao lại"}
              : {query.data.id}
            </p>
            <Badge variant="outline">
              {query.data.action === "delete_backup" &&
              query.data.status === "dispatched"
                ? "Đã gửi yêu cầu xóa"
                : query.data.action === "delete_backup" &&
                    query.data.status === "pending"
                  ? "Chờ gửi yêu cầu xóa"
                  : statusLabel(query.data.status)}
            </Badge>
            <p>
              {query.data.status === "dispatched"
                ? query.data.action === "delete_backup"
                  ? "Đã gửi yêu cầu xóa; xem trạng thái bản sao lưu để biết kết quả."
                  : "Đã giao lại; xem trạng thái tác vụ để biết kết quả xử lý."
                : query.data.reason}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={!jobKindSchema.safeParse(query.data.kind).success}
                onClick={() =>
                  onJob(query.data.kind as JobKind, query.data.job_id)
                }
              >
                Xem tác vụ liên quan
              </Button>
              {query.data.status === "pending" ? (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busy}
                  onClick={() => void retry()}
                >
                  {query.data.action === "delete_backup"
                    ? "Tiếp tục xóa đã xác nhận"
                    : "Tiếp tục giao lại đã xác nhận"}
                </Button>
              ) : null}
            </div>
            {error ? (
              <p role="alert" className="text-destructive">
                {error}
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
