import {
  Bot,
  Cpu,
  Plus,
  Search,
  Server,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
  type ViewMode,
  ViewModeToggle,
} from "@/components/ui/view-mode-toggle";
import { cn } from "@/lib/utils";
import { type Connection, type ConnectionFamily, FAMILIES, useConnections } from "./api";
import { ConnectionForm } from "./connection-form";

export function ConnectionList({
  onOpenProvider,
}: {
  onOpenProvider: (connection: Connection) => void;
}) {
  const query = useConnections();
  const connections = Array.isArray(query.data) ? query.data : [];

  const [formOpen, setFormOpen] = useState(false);
  const [initialFamily, setInitialFamily] = useState<ConnectionFamily>("openai");
  const [filter, setFilter] = useState("");
  const [mode, setMode] = useState<ViewMode>("grid");

  const visible = connections.filter((row) =>
    `${row.name} ${row.base_url} ${row.prefix ?? ""} ${FAMILIES[row.family]}`
      .toLowerCase()
      .includes(filter.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Server className="size-4" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Nhà cung cấp
            </h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Quản lý kết nối API tới các máy chủ mô hình AI (OpenAI Compatible).
          </p>
        </div>

        {/* Action Buttons styled like screenshot */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-2.5 size-3.5 text-muted-foreground" />
            <Input
              className="pl-8 text-xs h-9"
              aria-label="Tìm nhà cung cấp"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Tìm kiếm nhà cung cấp..."
            />
          </div>

          <Button
            size="sm"
            className="h-9 gap-1.5 text-xs shadow-xs"
            onClick={() => {
              setInitialFamily("openai");
              setFormOpen(true);
            }}
          >
            <Plus className="size-3.5" />
            <span>Thêm mới</span>
          </Button>

          <ViewModeToggle value={mode} onChange={setMode} />
        </div>
      </div>

      {query.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <div className="space-y-6">
          {/* Section: Danh sách nhà cung cấp */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold tracking-tight text-foreground flex items-center gap-2">
                <span>Danh sách nhà cung cấp</span>
                <Badge variant="outline" className="text-[11px] font-normal">
                  {visible.length}
                </Badge>
              </h2>
            </div>

            {visible.length === 0 ? (
              <EmptyState
                title={filter ? "Không tìm thấy nhà cung cấp phù hợp" : "Chưa có nhà cung cấp nào"}
                description="Nhấn vào 'Thêm mới' ở trên để kết nối nhà cung cấp đầu tiên."
              />
            ) : mode === "grid" ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {visible.map((row) => {
                  const hasKeys = row.active_keys_count > 0;

                  return (
                    <Card
                      key={row.id}
                      onClick={() => onOpenProvider(row)}
                      className={cn(
                        "group cursor-pointer rounded-xl border border-border/70 p-4 transition-all hover:border-primary/60 hover:shadow-sm bg-card hover:bg-muted/10 relative",
                      )}
                    >
                      <div className="flex items-start gap-3">
                        {/* Provider Icon Avatar */}
                        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted/60 border border-border/80 group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                          {row.family === "anthropic" ? (
                            <Sparkles className="size-5 text-amber-600 dark:text-amber-400" />
                          ) : row.family === "qnu" ? (
                            <Cpu className="size-5 text-teal-600 dark:text-teal-400" />
                          ) : (
                            <Bot className="size-5 text-primary" />
                          )}
                        </div>

                        {/* Provider Info */}
                        <div className="min-w-0 flex-1 space-y-1">
                          <h3 className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                            {row.name}
                          </h3>

                          {/* Connection Status Badge */}
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {hasKeys ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                                <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                {row.active_keys_count} Đã kết nối
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                                <span className="size-1.5 rounded-full bg-muted-foreground/40" />
                                Chưa có kết nối
                              </span>
                            )}

                            {/* Badge type */}
                            <Badge variant="secondary" className="text-[10px] py-0 px-1.5 font-normal">
                              Trò chuyện
                            </Badge>

                            {row.prefix && (
                              <Badge variant="outline" className="text-[10px] py-0 px-1 font-mono text-muted-foreground">
                                {row.prefix}/
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Card Footer detail */}
                      <div className="mt-3 pt-2.5 border-t border-border/60 flex items-center justify-between text-[11px] text-muted-foreground font-mono">
                        <span className="truncate max-w-[140px]" title={row.base_url}>
                          {row.base_url.replace(/^https?:\/\//, "")}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="shrink-0">{row.model_count} model</span>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-1.5 text-[11px] text-primary hover:text-primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenProvider(row);
                            }}
                          >
                            Mở nhà cung cấp
                          </Button>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            ) : (
              <Card className="overflow-hidden rounded-xl border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tên nhà cung cấp</TableHead>
                      <TableHead>Địa chỉ Base URL</TableHead>
                      <TableHead>Tiền tố (Prefix)</TableHead>
                      <TableHead>Giao thức</TableHead>
                      <TableHead>Số lượng kết nối</TableHead>
                      <TableHead>Số Model</TableHead>
                      <TableHead className="text-right">Thao tác</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visible.map((row) => (
                      <TableRow
                        key={row.id}
                        className="cursor-pointer hover:bg-muted/40"
                        onClick={() => onOpenProvider(row)}
                      >
                        <TableCell className="font-semibold text-foreground">
                          {row.name}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground max-w-xs truncate">
                          {row.base_url}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {row.prefix ? `${row.prefix}/` : "—"}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[10px]">
                            {FAMILIES[row.family] ?? "OpenAI"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {row.active_keys_count > 0 ? (
                            <span className="text-emerald-600 dark:text-emerald-400 font-medium text-xs">
                              ● {row.active_keys_count} Đã kết nối
                            </span>
                          ) : (
                            <span className="text-muted-foreground text-xs">
                              Chưa có kết nối
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {row.model_count} model
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenProvider(row);
                            }}
                          >
                            Chi tiết →
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Connection Form Dialog */}
      <ConnectionForm
        open={formOpen}
        onOpenChange={setFormOpen}
        initialFamily={initialFamily}
        onCreated={(newConn) => {
          void query.refetch();
          onOpenProvider(newConn);
        }}
      />
    </div>
  );
}

export function ConnectionStatus({
  status,
}: {
  status: Connection["last_probe_status"];
}) {
  switch (status) {
    case "success":
      return <Badge variant="success">Hoạt động</Badge>;
    case "failed":
      return <Badge variant="destructive">Lỗi</Badge>;
    case "stale":
      return <Badge variant="warning">Cần kiểm tra</Badge>;
    case "unsupported":
      return <Badge variant="outline">Không hỗ trợ</Badge>;
    default:
      return <Badge variant="secondary">Chưa kiểm tra</Badge>;
  }
}
