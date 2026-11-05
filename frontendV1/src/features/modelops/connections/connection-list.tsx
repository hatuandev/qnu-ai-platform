import {
  Bot,
  CheckCircle2,
  ChevronRight,
  Cpu,
  Plus,
  RotateCcw,
  Server,
  Sparkles,
} from "lucide-react";
import { useMemo, useState } from "react";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  type Connection,
  type ConnectionFamily,
  FAMILIES,
  useConnections,
} from "./api";
import { ConnectionForm } from "./connection-form";
import { connectionProtocol } from "./presentation";

export function ConnectionList({
  onOpenProvider,
}: {
  onOpenProvider: (connection: Connection) => void;
}) {
  const query = useConnections();
  const connections = Array.isArray(query.data) ? query.data : [];

  const [formOpen, setFormOpen] = useState(false);
  const [initialFamily, setInitialFamily] =
    useState<ConnectionFamily>("openai");
  const [filter, setFilter] = useState("");
  const [mode, setMode] = useState<ViewMode>("grid");

  const totalModels = useMemo(
    () => connections.reduce((acc, c) => acc + (c.model_count ?? 0), 0),
    [connections],
  );

  const activeConnections = useMemo(
    () => connections.filter((c) => c.active_keys_count > 0).length,
    [connections],
  );

  const visible = connections.filter((row) =>
    `${row.name} ${row.base_url} ${row.prefix ?? ""} ${FAMILIES[row.family]}`
      .toLowerCase()
      .includes(filter.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* 1. Page Header Chuẩn */}
      <PageHeader
        eyebrow="QNU AI · HẠ TẦNG"
        title="Nhà cung cấp"
        description="Quản lý kết nối tới máy chủ mô hình AI và dịch vụ OCR tài liệu."
        actions={
          <Button
            size="default"
            className="gap-2 shadow-xs"
            onClick={() => {
              setInitialFamily("openai");
              setFormOpen(true);
            }}
          >
            <Plus className="size-4" />
            <span>Thêm mới</span>
          </Button>
        }
      />

      {/* 2. Dải KPI Metrics Thống Kê Tổng Quan */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Server}
            label="Tổng số nhà cung cấp"
            value={connections.length.toLocaleString("vi-VN")}
          />
          <KpiMetric
            icon={Cpu}
            label="Tổng số mô hình (Models)"
            value={totalModels.toLocaleString("vi-VN")}
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Nhà cung cấp sẵn sàng"
            value={activeConnections.toLocaleString("vi-VN")}
          />
        </CardContent>
      </Card>

      {/* 3. Toolbar: Tìm kiếm & Đổi chế độ xem */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="w-full sm:w-80">
          <DebouncedSearchInput
            placeholder="Tìm kiếm nhà cung cấp..."
            value={filter}
            onChange={setFilter}
            className="text-xs h-9"
          />
        </div>

        <div className="flex items-center justify-end gap-2">
          {filter ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-9 px-2.5 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setFilter("")}
            >
              <RotateCcw className="size-3.5 mr-1" />
              <span>Đặt lại</span>
            </Button>
          ) : null}
          <ViewModeToggle value={mode} onChange={setMode} />
        </div>
      </div>

      {/* 4. Trạng thái Loading / Error / Empty / Nội dung */}
      {query.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-36 w-full rounded-xl" />
          <Skeleton className="h-36 w-full rounded-xl" />
          <Skeleton className="h-36 w-full rounded-xl" />
        </div>
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : visible.length === 0 ? (
        <Card className="rounded-xl shadow-2xs border-border/70">
          <CardContent className="py-12">
            <EmptyState
              icon={Server}
              title={
                filter
                  ? "Không tìm thấy nhà cung cấp phù hợp"
                  : "Chưa có nhà cung cấp nào"
              }
              description={
                filter
                  ? `Không có kết nối nào khớp với từ khóa "${filter}".`
                  : "Nhấn vào 'Thêm mới' ở trên để kết nối nhà cung cấp đầu tiên."
              }
              action={
                !filter
                  ? {
                      label: "Thêm nhà cung cấp",
                      onClick: () => {
                        setInitialFamily("openai");
                        setFormOpen(true);
                      },
                    }
                  : undefined
              }
            />
          </CardContent>
        </Card>
      ) : mode === "grid" ? (
        /* Grid View */
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((row) => {
            const hasKeys = row.active_keys_count > 0;

            return (
              <Card
                key={row.id}
                onClick={() => onOpenProvider(row)}
                className={cn(
                  "group cursor-pointer rounded-xl border border-border/70 p-4 transition-all hover:border-primary/60 hover:shadow-xs bg-card hover:bg-muted/10 relative flex flex-col justify-between",
                )}
              >
                <div>
                  <div className="flex items-start gap-3">
                    {/* Provider Icon Avatar */}
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
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
                          <span className="text-[11px] text-muted-foreground">
                            {row.active_keys_count} khóa đang bật
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                            <span className="size-1.5 rounded-full bg-muted-foreground/40" />
                            Chưa có khóa
                          </span>
                        )}

                        {/* Badge type */}
                        <Badge
                          variant="secondary"
                          className="text-[10px] py-0 px-1.5 font-normal"
                        >
                          {connectionProtocol(row)}
                        </Badge>
                        <ConnectionStatus status={row.last_probe_status} />

                        {row.prefix && (
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 px-1 font-mono text-muted-foreground"
                          >
                            {row.prefix}/
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card Footer detail */}
                <div className="mt-3.5 pt-2.5 border-t border-border/60 flex items-center justify-between text-[11px] text-muted-foreground font-mono">
                  <span
                    className="truncate max-w-[140px] text-muted-foreground/80"
                    title={row.base_url}
                  >
                    {row.base_url.replace(/^https?:\/\//, "")}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="shrink-0 text-foreground font-medium">
                      {row.model_count} model
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 px-1.5 text-[11px] text-primary hover:text-primary hover:underline gap-0.5 group-hover:translate-x-0.5 transition-transform"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenProvider(row);
                      }}
                    >
                      <span>Mở nhà cung cấp</span>
                      <ChevronRight className="size-3" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        /* Table View */
        <Card className="overflow-hidden rounded-xl border border-border/70 shadow-2xs">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40">
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                  Tên nhà cung cấp
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                  Địa chỉ Base URL
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                  Tiền tố (Prefix)
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                  Giao thức
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                  Số lượng kết nối
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                  Số Model
                </TableHead>
                <TableHead className="text-right font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                  Thao tác
                </TableHead>
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
                      {connectionProtocol(row)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {row.active_keys_count > 0 ? (
                      <span className="text-muted-foreground text-xs">
                        {row.active_keys_count} khóa đang bật
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-xs">
                        Chưa có khóa
                      </span>
                    )}
                    <ConnectionStatus status={row.last_probe_status} />
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {row.model_count} model
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-xs text-primary hover:text-primary gap-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenProvider(row);
                      }}
                    >
                      <span>Chi tiết</span>
                      <ChevronRight className="size-3" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
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
