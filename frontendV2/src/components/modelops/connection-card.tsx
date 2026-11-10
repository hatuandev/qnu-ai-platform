import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  FlaskConical,
  Key,
  Layers,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { useConnectionModelsQuery } from "@/api/modelops/queries";
import type { Connection, ModelProvider } from "@/api/modelops/types";
import { CopyButton } from "@/components/admin/copy-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CAPABILITY_LABELS, CONNECTION_FAMILIES } from "./constants";

export function ConnectionCard({
  connection,
  onEdit,
  onDelete,
  onTest,
  onManageKeys,
  onAddModel,
  onDeleteModel,
  onProbeModel,
}: {
  connection: Connection;
  onEdit: (conn: Connection) => void;
  onDelete: (conn: Connection) => void;
  onTest: (conn: Connection) => void;
  onManageKeys: (conn: Connection) => void;
  onAddModel: (conn: Connection) => void;
  onDeleteModel: (conn: Connection, model: ModelProvider) => void;
  onProbeModel: (model: ModelProvider) => void;
}) {
  const modelsQuery = useConnectionModelsQuery(connection.id);
  const models = modelsQuery.data ?? [];
  const familyMeta =
    CONNECTION_FAMILIES[connection.family] ?? CONNECTION_FAMILIES.custom;

  return (
    <Card className="overflow-hidden border border-border/70 bg-card hover:border-border transition-all duration-200 shadow-2xs">
      {/* Card Header */}
      <CardHeader className="p-4 pb-3 flex flex-row items-start justify-between space-y-0 gap-3 border-b border-border/50 bg-muted/15">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm text-foreground truncate">
              {connection.name}
            </span>
            <Badge
              variant="outline"
              className="text-[10px] h-4.5 px-1.5 font-normal"
            >
              {familyMeta.label}
            </Badge>
            {connection.is_active ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Hoạt động
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <span className="size-1.5 rounded-full bg-muted-foreground/50" />
                Tắt
              </span>
            )}
          </div>

          {/* Endpoint URL with CopyButton */}
          <div className="flex items-center gap-1 text-xs text-muted-foreground font-mono">
            <span
              className="truncate max-w-[280px] sm:max-w-[340px]"
              title={connection.base_url}
            >
              {connection.base_url}
            </span>
            <CopyButton value={connection.base_url} className="size-6 p-0" />
          </div>
        </div>

        {/* SINGLE MENU ⋯ PER CARD (Strict UI Standards) */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="size-7 p-0 shrink-0 text-muted-foreground hover:text-foreground"
              aria-label="Thao tác nhà cung cấp"
            >
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48 text-xs">
            <DropdownMenuItem
              onClick={() => onTest(connection)}
              className="gap-2"
            >
              <RefreshCw className="size-3.5 text-primary" />
              <span>Kiểm tra kết nối</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onAddModel(connection)}
              className="gap-2"
            >
              <Plus className="size-3.5" />
              <span>Thêm mô hình AI</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onManageKeys(connection)}
              className="gap-2"
            >
              <Key className="size-3.5" />
              <span>Quản lý API Key ({connection.active_keys_count || 0})</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onEdit(connection)}
              className="gap-2"
            >
              <Pencil className="size-3.5" />
              <span>Chỉnh sửa kết nối</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => onDelete(connection)}
              className="gap-2 text-destructive focus:text-destructive focus:bg-destructive/10"
            >
              <Trash2 className="size-3.5" />
              <span>Xóa nhà cung cấp</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>

      <CardContent className="p-4 space-y-4">
        {/* Connection Status & Key Metadata Strip */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-0.5">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Key className="size-3.5 text-muted-foreground/70" />
              <span>
                {connection.active_keys_count > 0
                  ? `${connection.active_keys_count} khóa API`
                  : "Chưa có khóa API"}
              </span>
            </span>

            <span className="flex items-center gap-1">
              <Layers className="size-3.5 text-muted-foreground/70" />
              <span>{models.length} mô hình</span>
            </span>
          </div>

          {/* Test Status Indicator */}
          <div className="flex items-center gap-1.5 text-[11px]">
            {connection.last_probe_status === "success" ? (
              <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                <CheckCircle2 className="size-3.5" />
                <span>Sẵn sàng</span>
              </span>
            ) : connection.last_probe_status === "failed" ? (
              <span className="inline-flex items-center gap-1 text-destructive font-medium">
                <AlertCircle className="size-3.5" />
                <span>Lỗi kết nối</span>
              </span>
            ) : (
              <span className="text-muted-foreground">Chưa kiểm tra</span>
            )}
          </div>
        </div>

        {/* Registered Models List */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Mô hình trực thuộc ({models.length})
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-5 px-1.5 text-[11px] gap-1 text-primary hover:text-primary hover:bg-primary/10"
              onClick={() => onAddModel(connection)}
            >
              <Plus className="size-3" />
              <span>Thêm model</span>
            </Button>
          </div>

          {modelsQuery.isLoading ? (
            <div className="py-3 text-center text-xs text-muted-foreground">
              Đang tải danh sách mô hình...
            </div>
          ) : models.length === 0 ? (
            <div className="rounded-md border border-dashed border-border/70 p-3 text-center text-xs text-muted-foreground">
              Chưa có mô hình nào được gán. Hãy thêm mô hình hoặc dùng "Kiểm tra
              kết nối" để phát hiện tự động.
            </div>
          ) : (
            <div className="space-y-1.5">
              {models.map((model) => (
                <div
                  key={model.id}
                  className="group flex items-center justify-between p-2 rounded-md border border-border/50 bg-muted/30 hover:bg-muted/60 transition-colors text-xs gap-2"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <Cpu className="size-3.5 text-primary shrink-0" />
                    <span
                      className="font-mono font-medium truncate text-foreground"
                      title={model.model_name}
                    >
                      {model.model_name}
                    </span>
                    <div className="flex items-center gap-1 shrink-0">
                      {model.capabilities.map((cap) => {
                        const meta = CAPABILITY_LABELS[cap];
                        return (
                          <Badge
                            key={cap}
                            variant="outline"
                            className={`text-[9px] h-3.5 px-1 font-normal ${meta?.badgeColor ?? ""}`}
                          >
                            {cap.toUpperCase()}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    {model.token_limits?.context_window_tokens && (
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {Math.round(
                          model.token_limits.context_window_tokens / 1000,
                        )}
                        k ctx
                      </span>
                    )}

                    {/* Single ⋯ Menu for the Model */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="size-6 p-0 text-muted-foreground hover:text-foreground"
                          aria-label="Thao tác mô hình"
                        >
                          <MoreHorizontal className="size-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-40 text-xs">
                        <DropdownMenuItem
                          onClick={() => onProbeModel(model)}
                          className="gap-2"
                        >
                          <FlaskConical className="size-3.5 text-primary" />
                          <span>Thử nghiệm (Probe)</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => onDeleteModel(connection, model)}
                          className="gap-2 text-destructive focus:text-destructive focus:bg-destructive/10"
                        >
                          <Trash2 className="size-3.5" />
                          <span>Xóa mô hình</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
