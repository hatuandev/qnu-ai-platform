import { Cpu, Plus, RefreshCw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ProviderFormDialog } from "@/features/modelops/provider-form-dialog";
import { ProvidersTable } from "@/features/modelops/providers-table";
import { useProvidersQuery } from "@/features/modelops/queries";
import type { Provider } from "@/features/modelops/types";
import { cn } from "@/lib/utils";

export function ProvidersPage({
  onOpenProvider,
}: {
  onOpenProvider: (provider: Provider) => void;
}) {
  const { actor } = useV1Auth();
  const query = useProvidersQuery();
  const [createOpen, setCreateOpen] = useState(false);
  const [filter, setFilter] = useState("");

  const canManage = isModelAdmin(actor);
  const providers = query.data ?? [];
  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return providers;
    return providers.filter((provider) =>
      [
        provider.name,
        provider.model_name,
        provider.base_url,
        provider.provider_type,
      ]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [filter, providers]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI · MODELOPS"
        title="Providers"
        description="Mỗi provider là một endpoint gắn với đúng một model. Danh sách lấy trực tiếp từ backendV1; quyền quản trị do máy chủ kiểm tra bằng ai.models.manage."
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

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          <div className="flex flex-col gap-2 border-b px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:max-w-xs">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="h-8 pl-8 text-xs"
                placeholder="Lọc theo tên, model, URL"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                aria-label="Lọc provider"
              />
            </div>
            <p className="text-[11px] text-muted-foreground">
              Lọc cục bộ trên {providers.length} bản ghi đã tải. API v1alpha1
              không hỗ trợ tìm kiếm phía máy chủ.
            </p>
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
              description="Xóa từ khóa để xem toàn bộ danh sách."
              action={{
                label: "Xóa bộ lọc",
                onClick: () => setFilter(""),
              }}
            />
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
