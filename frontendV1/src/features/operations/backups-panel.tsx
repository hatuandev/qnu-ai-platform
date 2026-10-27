import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useV1Auth } from "@/app/auth/v1";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { ErrorState } from "@/components/admin/error-state";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatBytes } from "@/features/knowledge/schemas";
import { formatDateTimeValue } from "@/lib/date-utils";
import { BackupCreate } from "./backup-create";
import { BackupDetails } from "./backup-details";
import { MaintenanceDialog } from "./maintenance-dialog";
import { useBackups, useRetention } from "./maintenance-queries";
import type { OperationsSearch } from "./search";
import { statusLabel } from "./types";

export function BackupsPanel({
  workspaceId,
  search,
  onSearch,
}: {
  workspaceId: string;
  search: OperationsSearch;
  onSearch: (patch: Partial<OperationsSearch>) => void;
}) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const backups = useBackups(workspaceId, search.page, search.pageSize);
  const retention = useRetention(workspaceId);
  const [deleting, setDeleting] = useState<string | null>(null);
  return (
    <div className="space-y-4">
      <BackupCreate
        workspaceId={workspaceId}
        onCreated={(id) => {
          onSearch({ backupId: id, page: 1 });
          void client.invalidateQueries({
            queryKey: ["v1", sessionId, "backups", workspaceId],
          });
        }}
      />
      {search.backupId ? (
        <BackupDetails
          key={search.backupId}
          workspaceId={workspaceId}
          id={search.backupId}
        />
      ) : null}
      <div className="flex flex-wrap justify-between gap-2">
        <h2 className="text-sm font-semibold">Các bản sao lưu</h2>
        <Button
          variant="outline"
          size="sm"
          disabled={backups.isFetching}
          onClick={() => {
            void backups.refetch();
            void retention.refetch();
          }}
        >
          Làm mới
        </Button>
      </div>
      {retention.isError ? (
        <ErrorState
          error={retention.error}
          onRetry={() => void retention.refetch()}
        />
      ) : retention.data ? (
        <p className="text-sm text-muted-foreground">
          Tệp gốc và raw OCR giữ lâu dài.{" "}
          {retention.data.automatic_delete
            ? "Server có cấu hình tự dọn."
            : "Không tự động xóa."}{" "}
          Danh sách đủ hạn xóa được server kiểm tra lại khi xem trước.
        </p>
      ) : (
        <p role="status">Đang đọc chính sách lưu giữ…</p>
      )}
      {backups.isPending ? (
        <p role="status">Đang đọc bản sao lưu…</p>
      ) : backups.isError ? (
        <ErrorState
          error={backups.error}
          onRetry={() => void backups.refetch()}
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Bản sao lưu</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Dung lượng</TableHead>
                  <TableHead>Giữ đến</TableHead>
                  <TableHead>Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {backups.data.items.map((backup) => (
                  <TableRow key={backup.id}>
                    <TableCell className="max-w-64 break-all">
                      <p className="font-mono text-xs">{backup.id}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTimeValue(backup.created_at)}
                      </p>
                    </TableCell>
                    <TableCell>
                      {statusLabel(backup.status)}
                      {backup.error_code ? (
                        <p className="text-destructive text-xs">
                          {backup.error_code}
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      {backup.size_bytes === null
                        ? "Chưa có số đo"
                        : formatBytes(backup.size_bytes)}
                    </TableCell>
                    <TableCell>
                      {backup.retain_until
                        ? formatDateTimeValue(backup.retain_until)
                        : "Lâu dài"}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onSearch({ backupId: backup.id })}
                        >
                          Xem
                        </Button>
                        {!retention.isError &&
                        retention.data?.eligible_backup_ids.includes(
                          backup.id,
                        ) ? (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => setDeleting(backup.id)}
                          >
                            Xóa hết hạn
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {backups.data.items.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground text-center">
                Chưa có bản sao lưu.
              </p>
            ) : null}
          </div>
          <DataTablePagination
            page={search.page}
            pageSize={search.pageSize}
            pageCount={Math.max(
              1,
              Math.ceil(backups.data.total / search.pageSize),
            )}
            total={backups.data.total}
            onPageChange={(page) => onSearch({ page })}
            onPageSizeChange={(pageSize) => onSearch({ pageSize, page: 1 })}
          />
        </>
      )}
      {deleting ? (
        <MaintenanceDialog
          key={deleting}
          workspaceId={workspaceId}
          backupId={deleting}
          onClose={() => setDeleting(null)}
          onReceipt={(id) =>
            onSearch({ operationActionId: id, backupId: deleting })
          }
        />
      ) : null}
    </div>
  );
}
