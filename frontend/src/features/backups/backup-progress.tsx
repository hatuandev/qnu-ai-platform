import { type BackupRecord, isBackupBusy } from "@/features/backups/api";

export function BackupProgressInfo({ record }: { record: BackupRecord }) {
  const elapsed = record.stage_started_at
    ? Math.max(
        0,
        Math.floor(
          (Date.now() - new Date(record.stage_started_at).getTime()) / 1000,
        ),
      )
    : 0;
  return (
    <div className="space-y-1 text-xs text-muted-foreground">
      {isBackupBusy(record) && (
        <p>
          Bước hiện tại: {Math.floor(elapsed / 60)} phút {elapsed % 60} giây.
          Thanh tiến độ theo giai đoạn, không phải thời gian còn lại.
        </p>
      )}
      {isBackupBusy(record) && record.total_bytes > 0 && (
        <p>
          {(record.processed_bytes / 1024 ** 2).toFixed(1)} /{" "}
          {(record.total_bytes / 1024 ** 2).toFixed(1)} MB
        </p>
      )}
      <p>
        S3/MinIO:{" "}
        {record.remote_status === "verified"
          ? "Đã đọc lại và kiểm chứng"
          : record.remote_status === "failed"
            ? "Chuyển thất bại; bản local được giữ"
            : record.remote_status === "copying"
              ? "Đang chuyển/kiểm chứng"
              : "Chưa có bản đã kiểm chứng"}
      </p>
      {record.remote_error && (
        <p className="text-destructive">{record.remote_error}</p>
      )}
    </div>
  );
}
