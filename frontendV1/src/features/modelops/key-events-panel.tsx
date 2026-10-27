import { ScrollText } from "lucide-react";
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
import { useKeyEventsQuery } from "@/features/modelops/queries";
import { formatDateTimeValue } from "@/lib/date-utils";

export function KeyEventsPanel({ providerId }: { providerId: string }) {
  const query = useKeyEventsQuery(providerId);
  const events = query.data ?? [];

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold">Nhật ký key</h2>
        <p className="text-xs text-muted-foreground">
          Bản ghi audit do backendV1 trả về cho provider này. Không có secret
          trong nhật ký.
        </p>
      </div>

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          {query.isLoading ? (
            <div className="grid gap-2 p-4">
              {[0, 1, 2].map((row) => (
                <Skeleton key={row} className="h-10 w-full" />
              ))}
            </div>
          ) : events.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              title="Chưa có thao tác nào trên key"
              description="Thêm, xoay hoặc thu hồi key sẽ xuất hiện ở đây."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[170px]">Thời điểm</TableHead>
                  <TableHead className="w-[180px]">Hành động</TableHead>
                  <TableHead>Người thực hiện</TableHead>
                  <TableHead>Lý do</TableHead>
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
                    <TableCell className="text-xs">
                      {event.reason ?? (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      )}
    </div>
  );
}
