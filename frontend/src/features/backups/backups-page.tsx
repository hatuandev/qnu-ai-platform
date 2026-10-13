import { Link } from "@tanstack/react-router";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { HardDrive, RefreshCw, Settings2, Upload } from "lucide-react";
import { useState } from "react";
import { AccessDenied } from "@/components/admin/access-denied";
import { PageHeader } from "@/components/admin/page-header";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  type BackupRecord,
  isBackupBusy,
  statusLabels,
  useBackups,
} from "@/features/backups/api";
import { BackupActionDialog } from "@/features/backups/backup-action-dialog";
import { BackupImportDialog } from "@/features/backups/backup-import-dialog";
import { BackupManageActions } from "@/features/backups/backup-manage-actions";
import { BackupProgressInfo } from "@/features/backups/backup-progress";
import { useRbac } from "@/rbac/context";

const columns: ColumnDef<BackupRecord>[] = [
  {
    accessorKey: "created_at",
    header: "Bản sao lưu",
    cell: ({ row }) => (
      <Link
        to="/settings/backups/$backupId"
        params={{ backupId: row.original.id }}
        className="font-medium text-primary hover:underline"
      >
        {new Date(row.original.created_at).toLocaleString("vi-VN")}
      </Link>
    ),
  },
  {
    accessorKey: "status",
    header: "Trạng thái",
    cell: ({ row }) => (
      <div className="space-y-2">
        <Badge
          variant={
            row.original.status === "failed" ? "destructive" : "secondary"
          }
        >
          {statusLabels[row.original.status]}
        </Badge>
        <p className="text-xs text-muted-foreground">{row.original.stage}</p>
        {row.original.error && (
          <p className="text-xs text-destructive">{row.original.error}</p>
        )}
        <BackupProgressInfo record={row.original} />
        {isBackupBusy(row.original) && (
          <Progress value={row.original.progress} className="h-1.5" />
        )}
      </div>
    ),
  },
  {
    accessorKey: "size_bytes",
    header: "Dung lượng",
    cell: ({ row }) =>
      row.original.size_bytes
        ? `${(row.original.size_bytes / 1024 / 1024).toFixed(1)} MB`
        : "—",
  },
  {
    id: "verification",
    header: "Kiểm chứng",
    cell: ({ row }) =>
      row.original.drill_at
        ? "Khôi phục thử đạt"
        : row.original.verified_at
          ? "Toàn vẹn đạt; chưa khôi phục thử"
          : "Chưa kiểm chứng",
  },
];

export function BackupsPage() {
  const { can } = useRbac();
  return can("ai.system.backup") ? <BackupList /> : <AccessDenied />;
}

function BackupList() {
  const query = useBackups();
  const [isOpen, setIsOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const busy = query.data?.items.some(isBackupBusy) ?? false;
  const table = useReactTable({
    data: query.data?.items ?? [],
    columns: [
      ...columns,
      {
        id: "actions",
        header: "Thao tác",
        cell: ({ row }) => (
          <BackupManageActions record={row.original} busy={busy} />
        ),
      },
    ],
    getRowId: (record) => record.id,
    getCoreRowModel: getCoreRowModel(),
  });
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Cài đặt / Sao lưu"
        title="Sao lưu & Khôi phục"
        description="Bảo vệ toàn bộ bản cài đặt. Khôi phục thử không thay đổi dữ liệu đang dùng."
        actions={
          <>
            <Button variant="outline" asChild>
              <Link to="/settings/backups/policy">
                <Settings2 className="size-4" />
                Chính sách
              </Link>
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsImportOpen(true)}
              disabled={busy || !query.data}
            >
              <Upload className="size-4" />
              Nhập file
            </Button>
            <Button
              variant="outline"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw className="size-4" />
              Làm mới
            </Button>
            <Button
              onClick={() => setIsOpen(true)}
              disabled={busy || !query.data}
            >
              <HardDrive className="size-4" />
              Sao lưu
            </Button>
          </>
        }
      />
      <Alert>
        <AlertDescription>
          Bản sao lưu được mã hóa bằng mật khẩu riêng. Hãy tải hoặc chép sang ổ
          ngoài/máy khác; bản chỉ nằm trên máy đang chạy app chưa bảo vệ được
          khi hỏng ổ đĩa.
        </AlertDescription>
      </Alert>
      {query.data && (
        <p className="break-all text-sm text-muted-foreground">
          Nơi lưu: {query.data.directory}
        </p>
      )}
      {query.isError && (
        <Alert variant="destructive">
          <AlertDescription>{query.error.message}</AlertDescription>
        </Alert>
      )}
      {query.isLoading ? (
        <Skeleton className="h-36 w-full" />
      ) : (
        <div className="w-full overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((group) => (
                <TableRow key={group.id}>
                  {group.headers.map((header) => (
                    <TableHead key={header.id}>
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
              {!query.data?.items.length && (
                <TableRow>
                  <TableCell
                    colSpan={columns.length + 1}
                    className="h-28 text-center text-muted-foreground"
                  >
                    {query.isError
                      ? "Không tải được lịch sử sao lưu."
                      : "Chưa có bản sao lưu."}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}
      {isOpen && (
        <BackupActionDialog action="create" onClose={() => setIsOpen(false)} />
      )}
      {isImportOpen && (
        <BackupImportDialog onClose={() => setIsImportOpen(false)} />
      )}
    </div>
  );
}
