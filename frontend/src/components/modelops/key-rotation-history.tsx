import { useQuery } from "@tanstack/react-query";
import { History, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiClient } from "@/services/api-client";
import type { ProviderApiKey } from "@/types/modelops";

const labels: Record<string, string> = {
  selected: "Chọn khóa",
  rotated: "Chuyển khóa",
  success: "Thành công",
  rate_limited: "Giới hạn tốc độ",
  exhausted: "Hết quota",
  invalid: "Khóa lỗi",
  failed: "Lỗi yêu cầu",
};

export function KeyRotationHistory({
  providerId,
  keys,
}: {
  providerId: string;
  keys: ProviderApiKey[];
}) {
  const history = useQuery({
    queryKey: ["provider-key-history", providerId],
    queryFn: () => apiClient.getProviderKeyHistory(providerId),
    refetchInterval: 10000,
  });
  return (
    <Card className="min-w-0">
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <History className="size-4 text-primary" />
          Lịch sử khóa
        </CardTitle>
        <Button
          variant="outline"
          size="sm"
          disabled={history.isFetching}
          onClick={() => history.refetch()}
        >
          <RefreshCw
            className={`size-3.5 ${history.isFetching ? "animate-spin" : ""}`}
          />
          Làm mới
        </Button>
      </CardHeader>
      <CardContent>
        {history.isPending ? (
          <Skeleton className="h-24 w-full" />
        ) : history.isError ? (
          <p className="text-sm text-destructive" role="alert">
            Không tải được lịch sử. Bấm Làm mới để thử lại.
          </p>
        ) : !history.data.length ? (
          <p className="text-sm text-muted-foreground">
            Chưa có sự kiện. Lịch sử được ghi khi hệ thống sử dụng khóa.
          </p>
        ) : (
          <div className="w-full overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Thời điểm</TableHead>
                  <TableHead>Khóa</TableHead>
                  <TableHead>Sự kiện</TableHead>
                  <TableHead>Lý do</TableHead>
                  <TableHead className="text-right">Token</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.data.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="whitespace-nowrap text-xs">
                      {new Date(event.created_at).toLocaleString("vi-VN")}
                    </TableCell>
                    <TableCell className="text-xs">
                      {keys.find((key) => key.id === event.key_id)?.name ||
                        event.key_id ||
                        "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {labels[event.event_type] || event.event_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {event.reason || "—"}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {event.tokens.toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        <p className="mt-3 text-xs text-muted-foreground">
          30 sự kiện gần nhất · Tự cập nhật mỗi 10 giây
        </p>
      </CardContent>
    </Card>
  );
}
