import { Activity } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AppRequestLog } from "@/features/modelops/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

interface RecentLogsTableProps {
  logs: AppRequestLog[];
  isLoading?: boolean;
}

export function RecentLogsTable({ logs, isLoading }: RecentLogsTableProps) {
  if (logs.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground text-xs">
        <Activity className="size-5 mb-2 opacity-60" />
        <p>Chưa có cuộc gọi API nào được ghi nhận cho workspace này.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent text-[11px]">
            <TableHead className="w-[150px]">Thời gian</TableHead>
            <TableHead className="w-[120px]">Ứng dụng</TableHead>
            <TableHead className="w-[140px]">Trợ lý gọi</TableHead>
            <TableHead className="w-[180px]">Endpoint</TableHead>
            <TableHead className="w-[90px]">Trạng thái</TableHead>
            <TableHead className="w-[90px]">Độ trễ</TableHead>
            <TableHead className="w-[130px] text-right">
              Tokens (P/C/T)
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody className="text-xs">
          {logs.map((log) => {
            const is2xx = log.status_code >= 200 && log.status_code < 300;
            const is4xx = log.status_code >= 400 && log.status_code < 500;
            const is5xx = log.status_code >= 500;

            return (
              <TableRow
                key={log.id}
                className="hover:bg-muted/40 transition-colors"
              >
                <TableCell className="font-mono text-[11px] text-muted-foreground">
                  {formatDateTimeValue(log.created_at)}
                </TableCell>
                <TableCell className="font-mono text-[11px]">
                  {log.app_id}
                </TableCell>
                <TableCell className="font-mono text-[11px]">
                  {log.assistant_id || "—"}
                </TableCell>
                <TableCell
                  className="font-mono text-[11px] truncate max-w-[200px]"
                  title={log.endpoint}
                >
                  {log.endpoint.replace(
                    "/platform/v1alpha1/integrations/openai/v1",
                    "",
                  )}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      is2xx ? "success" : is5xx ? "destructive" : "outline"
                    }
                    className={cn(
                      "text-[10px] py-0 px-1.5 font-mono",
                      is4xx && "border-warning/50 text-warning bg-warning/5",
                    )}
                  >
                    {log.status_code}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-[11px]">
                  {log.latency_ms} ms
                </TableCell>
                <TableCell className="font-mono text-[11px] text-right text-muted-foreground">
                  {log.total_tokens !== null ? (
                    <span>
                      {log.prompt_tokens ?? 0}/{log.completion_tokens ?? 0}/
                      <strong className="text-foreground">
                        {log.total_tokens}
                      </strong>
                    </span>
                  ) : (
                    <span>—</span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
