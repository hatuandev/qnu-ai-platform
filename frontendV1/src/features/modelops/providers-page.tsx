import {
  CheckCircle2,
  Cpu,
  Filter,
  Key,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  type ViewMode,
  ViewModeToggle,
} from "@/components/ui/view-mode-toggle";
import { ProviderCardGrid } from "@/features/modelops/provider-card-grid";
import { ProviderFormDialog } from "@/features/modelops/provider-form-dialog";
import { ProvidersTable } from "@/features/modelops/providers-table";
import { useProvidersSummaryQuery } from "@/features/modelops/queries";
import type { Provider } from "@/features/modelops/types";
import { cn } from "@/lib/utils";

export function ProvidersPage({
  onOpenProvider,
}: {
  onOpenProvider: (provider: Provider) => void;
}) {
  const { actor } = useV1Auth();
  const query = useProvidersSummaryQuery();
  const [createOpen, setCreateOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [capabilityFilter, setCapabilityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const canManage = isModelAdmin(actor);
  const providers = query.data ?? [];

  // Filter logic: text search + capability + status
  const visible = useMemo(() => {
    return providers.filter((p) => {
      // 1. Text filter
      const needle = filter.trim().toLowerCase();
      if (needle) {
        const matches = [p.name, p.model_name, p.base_url, p.provider_type]
          .join(" ")
          .toLowerCase()
          .includes(needle);
        if (!matches) return false;
      }

      // 2. Capability filter
      if (capabilityFilter !== "all") {
        if (!p.capabilities.includes(capabilityFilter)) {
          return false;
        }
      }

      // 3. Status filter
      if (statusFilter === "active" && !p.is_active) return false;
      if (statusFilter === "inactive" && p.is_active) return false;

      return true;
    });
  }, [filter, capabilityFilter, statusFilter, providers]);

  // Quick stats
  const activeCount = useMemo(
    () => providers.filter((p) => p.is_active).length,
    [providers],
  );
  const healthyCount = useMemo(
    () => providers.filter((p) => p.last_probe_status === "success").length,
    [providers],
  );
  const noKeysCount = useMemo(
    () => providers.filter((p) => p.total_keys_count === 0).length,
    [providers],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI · MODELOPS"
        title="Providers"
        description="Mỗi provider là một endpoint gắn với đúng một model. Phân nhóm trực quan theo họ nhà cung cấp, giám sát tình trạng khóa và kiểm tra kết nối."
        actions={
          <div className="flex items-center gap-2">
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
            {canManage ? (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setCreateOpen(true)}
              >
                <Plus className="size-3.5" />
                <span>Thêm provider</span>
              </Button>
            ) : null}
          </div>
        }
      />

      {/* Summary Stat Pills */}
      {!query.isLoading && providers.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-xl border border-border bg-card p-3 shadow-2xs">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-xs font-medium">Tổng số provider</span>
              <Cpu className="size-4" />
            </div>
            <div className="mt-2 text-2xl font-bold text-foreground">
              {providers.length}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {activeCount} đang hoạt động
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-3 shadow-2xs">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-xs font-medium">Đã kết nối</span>
              <CheckCircle2 className="size-4 text-emerald-500" />
            </div>
            <div className="mt-2 text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {healthyCount}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Đạt kiểm tra gần nhất
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-3 shadow-2xs">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-xs font-medium">Khóa server AI</span>
              <Key className="size-4 text-primary" />
            </div>
            <div className="mt-2 text-2xl font-bold text-foreground">
              {providers.reduce((acc, p) => acc + p.active_keys_count, 0)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Tổng số khóa active
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-3 shadow-2xs">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-xs font-medium">Cần lưu ý</span>
              <Filter className="size-4 text-warning" />
            </div>
            <div className="mt-2 text-2xl font-bold text-warning">
              {noKeysCount}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Provider chưa có khóa
            </p>
          </div>
        </div>
      )}

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          {/* Controls toolbar: Search, Capability Filter, Status Filter, ViewModeToggle */}
          <div className="flex flex-col gap-3 border-b px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2 flex-1">
              <div className="relative w-full sm:max-w-xs">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="h-8 pl-8 text-xs"
                  placeholder="Lọc theo tên, model, URL..."
                  value={filter}
                  onChange={(event) => setFilter(event.target.value)}
                  aria-label="Lọc provider"
                />
              </div>

              {/* Capability Filter */}
              <Select
                value={capabilityFilter}
                onValueChange={setCapabilityFilter}
              >
                <SelectTrigger className="h-8 w-[140px] text-xs">
                  <SelectValue placeholder="Chức năng" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tất cả chức năng</SelectItem>
                  <SelectItem value="chat">Chat</SelectItem>
                  <SelectItem value="embedding">Embedding</SelectItem>
                  <SelectItem value="rerank">Rerank</SelectItem>
                  <SelectItem value="ocr">OCR</SelectItem>
                </SelectContent>
              </Select>

              {/* Status Filter */}
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-8 w-[130px] text-xs">
                  <SelectValue placeholder="Trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tất cả trạng thái</SelectItem>
                  <SelectItem value="active">Đang bật</SelectItem>
                  <SelectItem value="inactive">Đang tắt</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <ViewModeToggle value={viewMode} onChange={setViewMode} />
            </div>
          </div>

          {!query.isLoading && providers.length === 0 ? (
            <EmptyState
              icon={Cpu}
              title="Chưa có provider nào"
              description={
                canManage
                  ? "Thêm provider đầu tiên để cấu hình model cho nền tảng."
                  : "Cần quyền ai.models.manage để thêm provider."
              }
              action={
                canManage
                  ? {
                      label: "Thêm provider",
                      onClick: () => setCreateOpen(true),
                    }
                  : undefined
              }
            />
          ) : !query.isLoading && visible.length === 0 ? (
            <EmptyState
              icon={Search}
              title="Không có provider khớp bộ lọc"
              description="Xóa từ khóa hoặc bộ lọc để xem toàn bộ danh sách."
              action={{
                label: "Xóa bộ lọc",
                onClick: () => {
                  setFilter("");
                  setCapabilityFilter("all");
                  setStatusFilter("all");
                },
              }}
            />
          ) : viewMode === "grid" ? (
            <ProviderCardGrid providers={visible} onOpen={onOpenProvider} />
          ) : (
            <ProvidersTable
              providers={visible}
              isLoading={query.isLoading}
              onOpen={onOpenProvider}
            />
          )}
        </Card>
      )}

      <ProviderFormDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
