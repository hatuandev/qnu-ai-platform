import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Button } from "@/components/ui/button";
import { formatBytes } from "@/features/knowledge/schemas";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { formatDateTimeValue } from "@/lib/date-utils";
import { downloadBlob } from "@/lib/download-blob";
import { useBackup } from "./maintenance-queries";
import { downloadBackup, verifyBackup } from "./maintenance-requests";
import { statusLabel } from "./types";

export function BackupDetails({
  workspaceId,
  id,
}: {
  workspaceId: string;
  id: string;
}) {
  const { sessionId } = useV1Auth();
  const current = useActionScope();
  const query = useBackup(workspaceId, id);
  const verification = useQuery({
    queryKey: ["v1", sessionId, "backup-verification", workspaceId, id],
    queryFn: ({ signal }) => verifyBackup(v1Client, workspaceId, id, signal),
    enabled: false,
    retry: false,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef(false);
  const download = async () => {
    if (active.current) return;
    active.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await downloadBackup(v1Client, workspaceId, id);
      if (current()) downloadBlob(result.blob, result.fileName ?? `${id}.zip`);
    } catch (cause) {
      if (current())
        setError(
          cause instanceof Error
            ? cause.message
            : "Không tải được bản sao lưu.",
        );
    } finally {
      active.current = false;
      if (current()) setBusy(false);
    }
  };
  if (query.isPending) return <p role="status">Đang đọc bản sao lưu…</p>;
  if (query.isError)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  const backup = query.data;
  return (
    <section
      aria-label="Chi tiết bản sao lưu"
      className="rounded-lg border p-4 space-y-3 text-sm"
    >
      <h2 className="font-semibold break-all">Bản sao lưu {backup.id}</h2>
      <p>
        {statusLabel(backup.status)} ·{" "}
        {backup.size_bytes === null
          ? "Chưa có số đo dung lượng"
          : formatBytes(backup.size_bytes)}
      </p>
      <p>
        Giữ đến:{" "}
        {backup.retain_until
          ? formatDateTimeValue(backup.retain_until)
          : "Lâu dài"}
      </p>
      <p className="break-all text-xs text-muted-foreground">
        SHA-256: {backup.sha256 ?? "Chưa có"}
      </p>
      {backup.error_code ? (
        <p role="alert" className="text-destructive">
          {backup.error_code}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={backup.status !== "completed" || verification.isFetching}
          onClick={() => void verification.refetch()}
        >
          Kiểm tra toàn vẹn
        </Button>
        <Button
          size="sm"
          disabled={backup.status !== "completed" || busy}
          onClick={() => void download()}
        >
          {busy ? "Đang tải…" : "Tải ZIP"}
        </Button>
      </div>
      {verification.isFetching ? (
        <p role="status">Đang kiểm tra nội dung…</p>
      ) : verification.isError ? (
        <ErrorState
          error={verification.error}
          onRetry={() => void verification.refetch()}
        />
      ) : verification.data ? (
        <p role="status">
          {verification.data.verified
            ? `Đã xác minh toàn vẹn ${verification.data.objects} tệp.`
            : "Chưa xác minh được toàn vẹn."}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-destructive">
          {error}
        </p>
      ) : null}
    </section>
  );
}
