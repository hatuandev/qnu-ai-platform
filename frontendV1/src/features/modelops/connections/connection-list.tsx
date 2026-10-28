import { Plus, RefreshCw, Search, Server } from "lucide-react";
import { useState } from "react";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { type Connection, FAMILIES, useConnections } from "./api";
import { ConnectionForm } from "./connection-form";

export function ConnectionList({
  onOpenProvider,
}: {
  onOpenProvider: (connection: Connection) => void;
}) {
  const query = useConnections();
  const connections = Array.isArray(query.data) ? query.data : [];
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const [mode, setMode] = useState<ViewMode>("grid");
  const visible = connections.filter((row) =>
    `${row.name} ${row.base_url} ${FAMILIES[row.family]}`
      .toLowerCase()
      .includes(filter.toLowerCase()),
  );
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI · MODELOPS"
        title="Nhà cung cấp"
        description="Quản lý kết nối đến OpenAI, Gemini hoặc server AI riêng. Thêm API key và các model trong từng nhà cung cấp."
        actions={
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw className="size-3.5" />
              Làm mới
            </Button>
            <Button size="sm" onClick={() => setOpen(true)}>
              <Plus className="size-3.5" />
              Thêm nhà cung cấp
            </Button>
          </div>
        }
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative w-full sm:max-w-sm">
          <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <Input
            className="pl-9 text-xs"
            aria-label="Tìm nhà cung cấp"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Tìm theo tên hoặc địa chỉ API"
          />
        </div>
        <ViewModeToggle value={mode} onChange={setMode} />
      </div>
      {query.isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : visible.length === 0 ? (
        <EmptyState
          title={
            filter ? "Không tìm thấy nhà cung cấp" : "Chưa có nhà cung cấp"
          }
          description="Thêm kết nối trước, sau đó cấu hình API key và model."
        />
      ) : mode === "grid" ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((row) => (
            <Card key={row.id} className="rounded-xl shadow-2xs">
              <CardContent className="space-y-4 p-5">
                <div className="flex justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <Server className="size-5 text-primary" />
                    <div>
                      <h2 className="text-sm font-semibold">{row.name}</h2>
                      <p className="text-xs text-muted-foreground">
                        {FAMILIES[row.family]}
                      </p>
                    </div>
                  </div>
                  <Badge variant={row.is_active ? "success" : "secondary"}>
                    {row.is_active ? "Đang bật" : "Đang tắt"}
                  </Badge>
                </div>
                <p className="break-all font-mono text-xs text-muted-foreground">
                  {row.base_url}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{row.model_count} model</Badge>
                  <Badge variant="outline">
                    {row.active_keys_count}/{row.total_keys_count} khóa
                  </Badge>
                  <ConnectionStatus status={row.last_probe_status} />
                </div>
                <Button
                  className="w-full"
                  variant="outline"
                  size="sm"
                  onClick={() => onOpenProvider(row)}
                >
                  Mở nhà cung cấp
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="overflow-hidden rounded-xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nhà cung cấp</TableHead>
                <TableHead>Địa chỉ API</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Khóa</TableHead>
                <TableHead>Kết nối</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="font-medium">{row.name}</TableCell>
                  <TableCell className="max-w-xs break-all font-mono text-xs">
                    {row.base_url}
                  </TableCell>
                  <TableCell>{row.model_count}</TableCell>
                  <TableCell>
                    {row.active_keys_count}/{row.total_keys_count}
                  </TableCell>
                  <TableCell>
                    <ConnectionStatus status={row.last_probe_status} />
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onOpenProvider(row)}
                    >
                      Chi tiết
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
      <ConnectionForm
        open={open}
        onOpenChange={setOpen}
        onCreated={onOpenProvider}
      />
    </div>
  );
}
export function ConnectionStatus({
  status,
}: {
  status: Connection["last_probe_status"];
}) {
  const labels = {
    success: "Đã kết nối",
    failed: "Kiểm tra thất bại",
    unsupported: "Chưa hỗ trợ kiểm tra",
    untested: "Chưa kiểm tra",
    stale: "Cần kiểm tra lại",
  };
  return (
    <Badge
      variant={
        status === "success"
          ? "success"
          : status === "failed"
            ? "destructive"
            : status === "stale"
              ? "warning"
              : "outline"
      }
    >
      {labels[status]}
    </Badge>
  );
}
