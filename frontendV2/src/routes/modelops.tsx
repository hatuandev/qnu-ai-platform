import { createFileRoute } from "@tanstack/react-router";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Cpu,
  Key,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Server,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import {
  useConnectionsQuery,
  useDeleteConnectionMutation,
} from "@/api/modelops/queries";
import type { Connection, ModelProvider } from "@/api/modelops/types";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { CopyButton } from "@/components/admin/copy-button";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { AddModelDialog } from "@/components/modelops/add-model-dialog";
import { ConnectionFormDialog } from "@/components/modelops/connection-form-dialog";
import { CONNECTION_FAMILIES } from "@/components/modelops/constants";
import { ModelProbeDialog } from "@/components/modelops/model-probe-dialog";
import { ProviderDetailSheet } from "@/components/modelops/provider-detail-sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/modelops")({
  component: ModelOpsPage,
});

function ModelOpsPage() {
  const { data, isLoading, refetch, isFetching } = useConnectionsQuery();
  const deleteConnectionMutation = useDeleteConnectionMutation();

  const connections = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  // Search & Filter
  const [search, setSearch] = useState("");
  const [selectedFamily, setSelectedFamily] = useState<string>("all");

  // Selected connection for Drawer Sheet
  const [selectedConnection, setSelectedConnection] =
    useState<Connection | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  // Dialogs
  const [formOpen, setFormOpen] = useState(false);
  const [editingConnection, setEditingConnection] = useState<Connection | null>(
    null,
  );

  const [addModelOpen, setAddModelOpen] = useState(false);
  const [addModelConnection, setAddModelConnection] =
    useState<Connection | null>(null);
  const [prefillModelName, setPrefillModelName] = useState("");

  const [probeDialogOpen, setProbeDialogOpen] = useState(false);
  const [probingModel, setProbingModel] = useState<ModelProvider | null>(null);

  const [connToDelete, setConnToDelete] = useState<Connection | null>(null);

  // Derived metrics
  const totalModels = useMemo(
    () => connections.reduce((acc, c) => acc + (c.model_count ?? 0), 0),
    [connections],
  );

  const activeWithKeys = useMemo(
    () =>
      connections.filter((c) => c.is_active && c.active_keys_count > 0).length,
    [connections],
  );

  const verifiedSuccess = useMemo(
    () => connections.filter((c) => c.last_probe_status === "success").length,
    [connections],
  );

  // Filtered list
  const filteredConnections = useMemo(() => {
    return connections.filter((conn) => {
      const matchSearch =
        search.trim() === "" ||
        conn.name.toLowerCase().includes(search.toLowerCase()) ||
        conn.base_url.toLowerCase().includes(search.toLowerCase()) ||
        conn.family.toLowerCase().includes(search.toLowerCase());

      const matchFamily =
        selectedFamily === "all" || conn.family === selectedFamily;

      return matchSearch && matchFamily;
    });
  }, [connections, search, selectedFamily]);

  // Keep selectedConnection synced with latest query data
  const currentSelected = useMemo(() => {
    if (!selectedConnection) return null;
    return (
      connections.find((c) => c.id === selectedConnection.id) ??
      selectedConnection
    );
  }, [connections, selectedConnection]);

  // Actions
  const handleOpenRowDetail = (conn: Connection) => {
    setSelectedConnection(conn);
    setSheetOpen(true);
  };

  const handleOpenAddConnection = () => {
    setEditingConnection(null);
    setFormOpen(true);
  };

  const handleOpenEdit = (conn: Connection) => {
    setEditingConnection(conn);
    setFormOpen(true);
  };

  const handleOpenAddModel = (conn: Connection, prefill = "") => {
    setAddModelConnection(conn);
    setPrefillModelName(prefill);
    setAddModelOpen(true);
  };

  const handleOpenProbe = (model: ModelProvider) => {
    setProbingModel(model);
    setProbeDialogOpen(true);
  };

  const handleDeleteConnectionConfirm = async () => {
    if (!connToDelete) return;
    try {
      await deleteConnectionMutation.mutateAsync(connToDelete.id);
      toast.success(`Đã xóa nhà cung cấp "${connToDelete.name}"`);
      if (selectedConnection?.id === connToDelete.id) {
        setSheetOpen(false);
      }
      setConnToDelete(null);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Có lỗi xảy ra khi xóa nhà cung cấp";
      toast.error(msg);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* 1. Page Header Chuẩn QNU */}
      <PageHeader
        eyebrow="Hạ tầng Trí tuệ Nhân tạo · ModelOps"
        title="Nhà cung cấp"
        description="Quản lý kết nối API, cấu hình endpoint, API keys và các mô hình AI phục vụ hội thoại, trích xuất và embedding."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => void refetch()}
              disabled={isFetching}
            >
              <RefreshCw
                className={`size-3.5 ${isFetching ? "animate-spin" : ""}`}
              />
              <span>Làm mới</span>
            </Button>
            <Button
              size="sm"
              className="h-8 gap-1.5 text-xs shadow-2xs"
              onClick={handleOpenAddConnection}
            >
              <Plus className="size-3.5" />
              <span>Thêm nhà cung cấp</span>
            </Button>
          </div>
        }
      />

      {/* 2. Dải KPI Metrics Tinh Gọn (High Data-to-Ink Ratio) */}
      <Card className="overflow-hidden border border-border/70 bg-card shadow-2xs">
        <CardContent className="grid p-0 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-border/60">
          <KpiMetric
            icon={Server}
            label="Tổng nhà cung cấp"
            value={connections.length.toString()}
            helper={`${activeWithKeys} cấu hình có khóa hoạt động`}
          />
          <KpiMetric
            icon={Cpu}
            label="Mô hình AI đã gán"
            value={totalModels.toString()}
            helper="Hội thoại, Embedding, Rerank & OCR"
          />
          <KpiMetric
            icon={Activity}
            label="Kết nối đã xác thực"
            value={`${verifiedSuccess} / ${connections.length}`}
            helper={
              verifiedSuccess === connections.length && connections.length > 0
                ? "Tất cả kết nối hoạt động tốt"
                : "Một số kết nối cần kiểm tra lại"
            }
          />
        </CardContent>
      </Card>

      {/* 3. Thanh công cụ & Bộ lọc phẳng (Flat Filter Bar) */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pb-2 border-b border-border/60">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          <DebouncedSearchInput
            value={search}
            onChange={setSearch}
            placeholder="Tìm theo tên nhà cung cấp, endpoint, chuẩn giao thức..."
            className="w-full sm:w-80 h-8 text-xs"
          />

          <Select value={selectedFamily} onValueChange={setSelectedFamily}>
            <SelectTrigger className="w-full sm:w-48 h-8 text-xs">
              <SelectValue placeholder="Tất cả chuẩn giao thức" />
            </SelectTrigger>
            <SelectContent className="text-xs">
              <SelectItem value="all">Tất cả giao thức</SelectItem>
              {Object.values(CONNECTION_FAMILIES).map((fam) => (
                <SelectItem key={fam.id} value={fam.id}>
                  {fam.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-2 text-xs text-muted-foreground">
          <span>{filteredConnections.length} nhà cung cấp</span>
        </div>
      </div>

      {/* 4. Bảng Dữ liệu Phẳng Cao cấp (Pristine Data Table) */}
      {isLoading ? (
        <div className="rounded-lg border border-border/70 bg-card p-6 space-y-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : filteredConnections.length === 0 ? (
        <EmptyState
          icon={Server}
          title={
            connections.length === 0
              ? "Chưa có nhà cung cấp AI nào"
              : "Không tìm thấy kết quả phù hợp"
          }
          description={
            connections.length === 0
              ? "Khai báo nhà cung cấp AI đầu tiên (như OpenAI, vLLM hoặc Google Gemini) để bắt đầu sử dụng các tính năng trợ lý và bóc tách tài liệu."
              : "Thử điều chỉnh từ khóa tìm kiếm hoặc chọn chuẩn giao thức khác."
          }
          action={
            connections.length === 0
              ? {
                  label: "Thêm nhà cung cấp mới",
                  onClick: handleOpenAddConnection,
                }
              : undefined
          }
        />
      ) : (
        <div className="rounded-lg border border-border/70 bg-card overflow-x-auto shadow-2xs">
          <Table>
            <TableHeader>
              <TableRow className="h-10 text-xs bg-muted/20 hover:bg-muted/20">
                <TableHead className="min-w-[180px] whitespace-nowrap">
                  Nhà cung cấp
                </TableHead>
                <TableHead className="whitespace-nowrap">
                  Chuẩn giao thức
                </TableHead>
                <TableHead className="min-w-[200px] whitespace-nowrap">
                  Endpoint URL
                </TableHead>
                <TableHead className="text-center whitespace-nowrap">
                  Khóa API
                </TableHead>
                <TableHead className="text-center whitespace-nowrap">
                  Số mô hình
                </TableHead>
                <TableHead className="whitespace-nowrap">
                  Kiểm tra kết nối
                </TableHead>
                <TableHead className="text-center whitespace-nowrap">
                  Trạng thái
                </TableHead>
                <TableHead className="w-[70px] text-right whitespace-nowrap">
                  Thao tác
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredConnections.map((conn) => {
                const fam =
                  CONNECTION_FAMILIES[conn.family] ??
                  CONNECTION_FAMILIES.custom;

                return (
                  <TableRow
                    key={conn.id}
                    onClick={() => handleOpenRowDetail(conn)}
                    className="h-13 text-xs cursor-pointer hover:bg-muted/40 transition-colors group"
                  >
                    {/* Column 1: Tên nhà cung cấp */}
                    <TableCell className="font-semibold text-foreground">
                      <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full shrink-0 bg-primary/60 group-hover:bg-primary transition-colors" />
                        <span className="group-hover:text-primary transition-colors truncate max-w-[200px]">
                          {conn.name}
                        </span>
                      </div>
                    </TableCell>

                    {/* Column 2: Họ giao thức */}
                    <TableCell className="whitespace-nowrap">
                      <Badge
                        variant="outline"
                        className="text-[10px] h-5 px-1.5 font-normal whitespace-nowrap shrink-0"
                      >
                        {fam.label}
                      </Badge>
                    </TableCell>

                    {/* Column 3: Endpoint URL */}
                    <TableCell
                      className="font-mono text-muted-foreground text-[11px]"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center gap-1 max-w-[280px]">
                        <span className="truncate" title={conn.base_url}>
                          {conn.base_url}
                        </span>
                        <CopyButton
                          value={conn.base_url}
                          className="size-5 p-0 shrink-0"
                          tooltip="Sao chép Endpoint"
                        />
                      </div>
                    </TableCell>

                    {/* Column 4: Khóa API */}
                    <TableCell className="text-center whitespace-nowrap">
                      {conn.active_keys_count > 0 ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-5 px-1.5 font-normal gap-1 whitespace-nowrap shrink-0 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                        >
                          <Key className="size-2.5 shrink-0" />
                          <span>{conn.active_keys_count} hoạt động</span>
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground text-[11px] whitespace-nowrap">
                          Chưa có khóa
                        </span>
                      )}
                    </TableCell>

                    {/* Column 5: Số mô hình */}
                    <TableCell className="text-center whitespace-nowrap">
                      <Badge
                        variant="secondary"
                        className="text-[10px] h-5 px-1.5 font-normal whitespace-nowrap shrink-0"
                      >
                        {conn.model_count} mô hình
                      </Badge>
                    </TableCell>

                    {/* Column 6: Trạng thái kiểm tra */}
                    <TableCell className="whitespace-nowrap">
                      {conn.last_probe_status === "success" ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium text-[11px] whitespace-nowrap">
                          <CheckCircle2 className="size-3.5 shrink-0" />
                          <span>Sẵn sàng</span>
                        </span>
                      ) : conn.last_probe_status === "failed" ? (
                        <span className="inline-flex items-center gap-1 text-destructive font-medium text-[11px] whitespace-nowrap">
                          <AlertCircle className="size-3.5 shrink-0" />
                          <span>Lỗi kết nối</span>
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-[11px] whitespace-nowrap">
                          Chưa kiểm tra
                        </span>
                      )}
                    </TableCell>

                    {/* Column 7: Trạng thái hoạt động */}
                    <TableCell className="text-center whitespace-nowrap">
                      {conn.is_active ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                          <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                          Bật
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground whitespace-nowrap">
                          <span className="size-1.5 rounded-full bg-muted-foreground/50 shrink-0" />
                          Tắt
                        </span>
                      )}
                    </TableCell>

                    {/* Column 8: Thao tác menu ⋯ duy nhất */}
                    <TableCell
                      className="text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="size-7 p-0 text-muted-foreground hover:text-foreground"
                            aria-label="Thao tác"
                          >
                            <MoreHorizontal className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          align="end"
                          className="w-52 text-xs"
                        >
                          <DropdownMenuItem
                            onClick={() => handleOpenRowDetail(conn)}
                            className="gap-2 font-medium"
                          >
                            <ChevronRight className="size-3.5 text-primary" />
                            <span>Quản lý chi tiết & Models</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => handleOpenAddModel(conn)}
                            className="gap-2"
                          >
                            <Plus className="size-3.5" />
                            <span>Thêm mô hình AI</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => handleOpenEdit(conn)}
                            className="gap-2"
                          >
                            <Pencil className="size-3.5" />
                            <span>Chỉnh sửa kết nối</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => setConnToDelete(conn)}
                            className="gap-2 text-destructive focus:text-destructive focus:bg-destructive/10"
                          >
                            <Trash2 className="size-3.5" />
                            <span>Xóa nhà cung cấp</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* 5. SLIDE-OVER SHEET: Bảng điều khiển ngăn kéo chi tiết (Chuẩn Phương án 3) */}
      <ProviderDetailSheet
        connection={currentSelected}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onOpenAddModel={(conn, prefill) => handleOpenAddModel(conn, prefill)}
        onOpenProbeModel={handleOpenProbe}
        onRequestDeleteConnection={(conn) => setConnToDelete(conn)}
      />

      {/* 6. Hộp thoại Thêm / Chỉnh sửa Nhà cung cấp */}
      <ConnectionFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        connection={editingConnection}
      />

      {/* 7. Hộp thoại Đăng ký Mô hình AI */}
      {addModelConnection && (
        <AddModelDialog
          open={addModelOpen}
          onOpenChange={setAddModelOpen}
          connection={addModelConnection}
          prefillModelName={prefillModelName}
        />
      )}

      {/* 8. Hộp thoại Thử nghiệm Mô hình (Probe Active) */}
      {probingModel && (
        <ModelProbeDialog
          open={probeDialogOpen}
          onOpenChange={setProbeDialogOpen}
          model={probingModel}
        />
      )}

      {/* 9. Xác nhận Xóa Nhà cung cấp */}
      <ConfirmDialog
        open={Boolean(connToDelete)}
        onOpenChange={(open) => !open && setConnToDelete(null)}
        title="Xóa nhà cung cấp AI"
        description={
          <>
            Bạn có chắc chắn muốn xóa nhà cung cấp{" "}
            <strong>{connToDelete?.name}</strong>? Toàn bộ mô hình và khóa API
            trực thuộc cũng sẽ bị xóa khỏi hệ thống.
          </>
        }
        confirmLabel="Xác nhận xóa"
        confirmVariant="destructive"
        isLoading={deleteConnectionMutation.isPending}
        onConfirm={handleDeleteConnectionConfirm}
      />
    </div>
  );
}
