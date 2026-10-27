import { ScrollText } from "lucide-react";
import { canManageMembers } from "@/app/auth/v1";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Card } from "@/components/ui/card";
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
  useCallerWorkspaceRole,
  useWorkspaceEventsQuery,
} from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";

export function WorkspaceAuditPanel({
  workspaceId,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: {
  workspaceId: string;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}) {
  const { role, isPending } = useCallerWorkspaceRole(workspaceId);
  const canView = canManageMembers(role);
  const query = useWorkspaceEventsQuery(
    workspaceId,
    { page, pageSize },
    { enabled: canView },
  );

  const total = query.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const events = query.data?.items ?? [];

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold">Nhật ký workspace</h2>
        <p className="text-xs text-muted-foreground">
          Bản ghi do backendV1 trả về cho workspace này. Nhật ký cần vai trò
          admin của workspace hoặc quyền quản trị nền tảng.
        </p>
      </div>

      {!canView && !isPending ? (
        <p className="rounded-md border bg-muted/40 px-3 py-2 text-[11px] leading-5">
          Tài khoản của bạn không có quyền xem nhật ký của workspace này. Đây là
          giới hạn quyền, không phải danh sách rỗng.
        </p>
      ) : query.isError ? (
        <ErrorState
          error={query.error}
          title="Không đọc được nhật ký"
          onRetry={() => void query.refetch()}
        />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          {query.isLoading || isPending ? (
            <div className="grid gap-2 p-4">
              {[0, 1, 2].map((row) => (
                <Skeleton key={row} className="h-10 w-full" />
              ))}
            </div>
          ) : events.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              title="Chưa có bản ghi nào"
              description="Thay đổi thành viên, trạng thái hay cấu hình model sẽ xuất hiện ở đây."
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[170px]">Thời điểm</TableHead>
                    <TableHead className="w-[220px]">Hành động</TableHead>
                    <TableHead className="w-[180px]">Người thực hiện</TableHead>
                    <TableHead className="hidden md:table-cell">
                      Đối tượng
                    </TableHead>
                    <TableHead>Chi tiết</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map((event) => (
                    <TableRow key={event.id}>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDateTimeValue(event.created_at)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {event.action}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {event.actor_ref ?? "—"}
                      </TableCell>
                      <TableCell className="hidden text-xs md:table-cell">
                        {event.target_type ? (
                          <span className="font-mono">
                            {event.target_type}
                            {event.target_id ? `:${event.target_id}` : ""}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {Object.keys(event.detail).length === 0 ? (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        ) : (
                          <details>
                            <summary className="cursor-pointer text-[11px] text-muted-foreground hover:text-foreground">
                              Xem chi tiết
                            </summary>
                            <pre className="mt-1 max-h-40 overflow-auto rounded-md bg-muted/60 p-2 text-[11px] leading-5">
                              {JSON.stringify(event.detail, null, 2)}
                            </pre>
                          </details>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="border-t px-3">
                <DataTablePagination
                  page={page}
                  pageSize={pageSize}
                  pageCount={pageCount}
                  total={total}
                  onPageChange={onPageChange}
                  onPageSizeChange={onPageSizeChange}
                />
              </div>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
