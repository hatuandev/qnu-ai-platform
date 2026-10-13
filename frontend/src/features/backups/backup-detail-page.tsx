import { Link } from "@tanstack/react-router";
import { ArrowLeft, Download, FlaskConical, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { AccessDenied } from "@/components/admin/access-denied";
import { PageHeader } from "@/components/admin/page-header";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type BackupAction,
  downloadBackup,
  isBackupBusy,
  statusLabels,
  useBackupRecord,
  useBackups,
} from "@/features/backups/api";
import { BackupActionDialog } from "@/features/backups/backup-action-dialog";
import { BackupManageActions } from "@/features/backups/backup-manage-actions";
import { BackupProgressInfo } from "@/features/backups/backup-progress";
import { useRbac } from "@/rbac/context";

export function BackupDetailPage({ backupId }: { backupId: string }) {
  const { can } = useRbac();
  return can("ai.system.backup") ? (
    <BackupDetail backupId={backupId} />
  ) : (
    <AccessDenied />
  );
}

function BackupDetail({ backupId }: { backupId: string }) {
  const query = useBackups();
  const detail = useBackupRecord(backupId);
  const [action, setAction] = useState<BackupAction | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const record = detail.data;
  const busy = query.data?.items.some(isBackupBusy) ?? true;
  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      await downloadBackup(backupId);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Tải bản sao lưu thất bại.",
      );
    } finally {
      setIsDownloading(false);
    }
  };
  return (
    <div className="space-y-6">
      <Link
        to="/settings/backups"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        Sao lưu
      </Link>
      <PageHeader
        title="Chi tiết bản sao lưu"
        description={
          record
            ? new Date(record.created_at).toLocaleString("vi-VN")
            : backupId
        }
        actions={
          <>
            <Button
              variant="outline"
              disabled={!record?.sha256 || isDownloading}
              onClick={() => void handleDownload()}
            >
              <Download className="size-4" />
              Tải xuống
            </Button>
            <Button
              variant="outline"
              disabled={busy || !record?.sha256}
              onClick={() => setAction("verify")}
            >
              <ShieldCheck className="size-4" />
              Kiểm tra
            </Button>
            <Button
              disabled={
                busy || !record?.verified_at || !query.data?.drill_enabled
              }
              onClick={() => setAction("drill")}
            >
              <FlaskConical className="size-4" />
              Khôi phục thử
            </Button>
          </>
        }
      />
      {query.isLoading && <Skeleton className="h-40 w-full" />}
      {query.isError && (
        <Alert variant="destructive">
          <AlertDescription>{query.error.message}</AlertDescription>
        </Alert>
      )}
      {detail.isError && (
        <Alert variant="destructive">
          <AlertDescription>{detail.error.message}</AlertDescription>
        </Alert>
      )}
      {detail.isSuccess && !record && (
        <Alert>
          <AlertDescription>
            Không tìm thấy bản sao lưu trong lịch sử.
          </AlertDescription>
        </Alert>
      )}
      {record && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="space-y-4 p-5">
            <Badge
              variant={record.status === "failed" ? "destructive" : "secondary"}
            >
              {statusLabels[record.status]}
            </Badge>
            <p className="text-sm">{record.stage}</p>
            <BackupProgressInfo record={record} />
            <BackupManageActions record={record} busy={busy} />
            <Progress value={record.progress} />
            <p className="text-sm text-muted-foreground">
              Dung lượng: {(record.size_bytes / 1024 / 1024).toFixed(1)} MB
            </p>
            {record.error && (
              <Alert variant="destructive">
                <AlertDescription>{record.error}</AlertDescription>
              </Alert>
            )}
            <p className="break-all font-mono text-xs text-muted-foreground">
              SHA-256: {record.sha256 ?? "Chưa hoàn tất"}
            </p>
          </Card>
          <Card className="space-y-4 p-5">
            <h2 className="text-sm font-semibold">Kết quả kiểm chứng</h2>
            <p className="text-sm">
              Toàn vẹn:{" "}
              {record.verified_at
                ? new Date(record.verified_at).toLocaleString("vi-VN")
                : "Chưa kiểm tra"}
            </p>
            <p className="text-sm">
              Khôi phục thử:{" "}
              {record.drill_at
                ? new Date(record.drill_at).toLocaleString("vi-VN")
                : "Chưa thực hiện"}
            </p>
            <p className="text-sm text-muted-foreground">
              Kiểm tra toàn vẹn không thay thế khôi phục thử. Sandbox đối soát
              DB, file, khóa ModelOps và vector; chưa thay cho kiểm thử câu trả
              lời chatbot.
            </p>
            <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
              {JSON.stringify(record.components, null, 2)}
            </pre>
            <h3 className="text-sm font-semibold">Lịch sử thao tác</h3>
            <ul className="space-y-2 text-sm">
              {record.history?.map((event) => (
                <li
                  key={`${event.timestamp}-${event.operation}-${event.status}`}
                  className="border-t pt-2"
                >
                  <span>
                    {event.operation === "create"
                      ? "Sao lưu"
                      : event.operation === "import"
                        ? "Nhập file"
                        : event.operation === "copy"
                          ? "Chuyển S3"
                          : event.operation === "verify"
                            ? "Kiểm tra"
                            : "Khôi phục thử"}{" "}
                    · {statusLabels[event.status]}
                  </span>
                  <p className="text-xs text-muted-foreground">
                    {new Date(event.timestamp).toLocaleString("vi-VN")}
                  </p>
                  {event.error && (
                    <p className="text-xs text-destructive">{event.error}</p>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
      {!query.data?.drill_enabled && query.data && (
        <Alert>
          <AlertDescription>
            Khôi phục thử cần bật BACKUP_DRILL_ENABLED trên máy có Docker. Không
            cấp Docker socket cho backend production.
          </AlertDescription>
        </Alert>
      )}
      {action && (
        <BackupActionDialog
          action={action}
          backupId={backupId}
          onClose={() => setAction(null)}
        />
      )}
    </div>
  );
}
