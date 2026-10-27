import { RefreshCw, ScrollText } from "lucide-react";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
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
import { useModelOpsEventsQuery } from "@/features/modelops/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

export function ModelOpsEventsPage() {
  const query = useModelOpsEventsQuery();
  const events = query.data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI · MODELOPS"
        title="Nhật ký cấu hình"
        description="Bản ghi audit của provider, key và model mặc định do backendV1 trả về. Đây là dữ liệu thật, không phải mẫu."
        actions={
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs font-semibold"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
          >
            <RefreshCw
              className={cn("size-3.5", query.isFetching && "animate-spin")}
            />
            <span>Làm mới</span>
          </Button>
        }
      />

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          {query.isLoading ? (
            <div className="grid gap-2 p-4">
              {[0, 1, 2, 3].map((row) => (
                <Skeleton key={row} className="h-10 w-full" />
              ))}
            </div>
          ) : events.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              title="Chưa có bản ghi cấu hình"
              description="Thay đổi provider, key hoặc model mặc định sẽ xuất hiện ở đây."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[170px]">Thời điểm</TableHead>
                  <TableHead className="w-[200px]">Hành động</TableHead>
                  <TableHead className="w-[180px]">Người thực hiện</TableHead>
                  <TableHead className="hidden lg:table-cell">
                    Provider
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
                      {event.actor_ref}
                    </TableCell>
                    <TableCell className="hidden font-mono text-xs lg:table-cell">
                      {event.provider_id ?? "—"}
                    </TableCell>
                    <TableCell>
                      {Object.keys(event.detail).length === 0 ? (
                        <span className="text-xs text-muted-foreground">—</span>
                      ) : (
                        <details className="group">
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
          )}
        </Card>
      )}

      <p className="text-[11px] text-muted-foreground">
        API trả tối đa 50 bản ghi gần nhất và không phân trang.
      </p>
    </div>
  );
}
