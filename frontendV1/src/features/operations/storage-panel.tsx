import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Button } from "@/components/ui/button";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { CleanupInventory } from "./cleanup-inventory";
import { MaintenanceDialog } from "./maintenance-dialog";
import { useCleanup } from "./maintenance-queries";
import { acceptCleanup } from "./maintenance-requests";

export function StoragePanel({
  workspaceId,
  actionId,
  onReceipt,
}: {
  workspaceId: string;
  actionId?: string;
  onReceipt: (id: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <h2 className="text-sm font-semibold">
          Dọn tệp dẫn xuất không còn sử dụng
        </h2>
        <p className="text-sm text-muted-foreground">
          Chỉ xét tệp từ tác vụ đã kết thúc, đủ tuổi và không còn tham chiếu.
          Nếu còn tác vụ đang chạy, server sẽ yêu cầu chờ.
        </p>
        <Button onClick={() => setIsOpen(true)}>Xem trước việc dọn tệp</Button>
      </div>
      {actionId ? (
        <CleanupReceipt
          key={actionId}
          workspaceId={workspaceId}
          id={actionId}
        />
      ) : null}
      {isOpen ? (
        <MaintenanceDialog
          workspaceId={workspaceId}
          onClose={() => setIsOpen(false)}
          onReceipt={onReceipt}
        />
      ) : null}
    </section>
  );
}
export function CleanupReceipt({
  workspaceId,
  id,
}: {
  workspaceId: string;
  id: string;
}) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const current = useActionScope();
  const query = useCleanup(workspaceId, id);
  const active = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resume = async () => {
    if (query.data?.status !== "pending" || active.current) return;
    active.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await acceptCleanup(v1Client, workspaceId, query.data);
      if (!current()) return;
      await client.cancelQueries({
        queryKey: ["v1", sessionId, "storage-cleanup", workspaceId, id],
      });
      if (current())
        client.setQueryData(
          ["v1", sessionId, "storage-cleanup", workspaceId, id],
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
  if (query.isPending) return <p role="status">Đang đọc biên nhận dọn tệp…</p>;
  if (query.isError)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  return (
    <div className="rounded-lg border p-4 space-y-3">
      <h3 className="text-sm font-semibold break-all">
        Biên nhận dọn tệp {query.data.id}
      </h3>
      <CleanupInventory action={query.data} />
      {query.data.status === "pending" ? (
        <Button variant="outline" disabled={busy} onClick={() => void resume()}>
          Tiếp tục dọn đã xác nhận
        </Button>
      ) : null}
      {query.data.status === "preview" ? (
        <p className="text-sm text-warning">
          Bản xem trước này chưa ghi nhận xác nhận. Hãy mở một bản xem trước mới
          để kiểm tra lại.
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
