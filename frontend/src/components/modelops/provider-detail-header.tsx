import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Cloud,
  Copy,
  Cpu,
  Globe,
  Pencil,
  Play,
  RefreshCw,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import type React from "react";
import { ProviderIcon } from "../../components/icons/provider-icon";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Switch } from "../../components/ui/switch";
import type { ModelProvider } from "../../services/api-client";
import { getProviderCategory } from "./modelops-helpers";

export interface ProviderDetailHeaderProps {
  selectedProvider: ModelProvider;
  isTesting: boolean;
  testResult: { id: string; success: boolean; message: string } | null;
  copiedUrl: boolean;
  onBackToList: () => void;
  onCopyUrl: (url: string) => void;
  onToggleActive: () => void;
  onTestConnection: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export const ProviderDetailHeader: React.FC<ProviderDetailHeaderProps> = ({
  selectedProvider,
  isTesting,
  testResult,
  copiedUrl,
  onBackToList,
  onCopyUrl,
  onToggleActive,
  onTestConnection,
  onEdit,
  onDelete,
}) => {
  const hasTestMsg = testResult && testResult.id === selectedProvider.id;
  const cat = getProviderCategory(selectedProvider);

  return (
    <>
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBackToList}
            className="h-8 px-2.5 text-xs gap-1.5 text-muted-foreground hover:text-foreground -ml-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Quay lại danh sách Nhà cung cấp</span>
          </Button>
          <span className="text-muted-foreground/60">/</span>
          <span className="font-semibold text-foreground flex items-center gap-2">
            <ProviderIcon code={selectedProvider.type} size={18} />
            {selectedProvider.name}
          </span>
        </div>

        <Badge variant="outline" className="font-mono text-xs text-primary border-primary/30">
          Chi Tiết Provider
        </Badge>
      </div>

      {/* Hero Provider Header Card */}
      <Card className="p-6 space-y-4 border-border/80 shadow-xs bg-card">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5 min-w-0">
            <div className="p-2.5 rounded-lg bg-muted/40 border border-border/60 shrink-0 mt-0.5 flex items-center justify-center">
              <ProviderIcon code={selectedProvider.type} size={36} />
            </div>
            <div className="space-y-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  {selectedProvider.name}
                </h1>
                <Badge
                  variant="secondary"
                  className="font-mono text-[11px] uppercase tracking-wider"
                >
                  {selectedProvider.type}
                </Badge>
                {cat === "cloud" ? (
                  <Badge
                    variant="outline"
                    className="text-[11px] font-mono text-sky-600 dark:text-sky-400 border-sky-500/30 gap-1"
                  >
                    <Cloud className="h-3 w-3" />
                    Cloud
                  </Badge>
                ) : cat === "local" ? (
                  <Badge
                    variant="outline"
                    className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 border-emerald-500/30 gap-1"
                  >
                    <Cpu className="h-3 w-3" />
                    Local
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="text-[11px] font-mono text-amber-600 dark:text-amber-400 border-amber-500/30 gap-1"
                  >
                    <SlidersHorizontal className="h-3 w-3" />
                    Custom
                  </Badge>
                )}
                <Badge
                  variant={selectedProvider.is_active ? "success" : "outline"}
                  className="text-[11px]"
                >
                  {selectedProvider.is_active ? "Đang Hoạt Động" : "Đang Tạm Dừng"}
                </Badge>
              </div>

              {selectedProvider.api_base_url ? (
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                  <Globe className="h-3 w-3 text-primary shrink-0" />
                  <span className="truncate max-w-md">{selectedProvider.api_base_url}</span>
                  <button
                    type="button"
                    onClick={() => onCopyUrl(selectedProvider.api_base_url || "")}
                    className="p-1 hover:text-foreground rounded transition-colors"
                    title="Sao chép URL"
                  >
                    {copiedUrl ? (
                      <Check className="h-3 w-3 text-success" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </button>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Sử dụng endpoint mặc định của nhà cung cấp
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0 pt-2 lg:pt-0 border-t lg:border-t-0 border-border/60">
            <div className="flex items-center gap-2 bg-muted/40 px-3 py-1.5 rounded-md border border-border">
              <span className="text-xs font-medium text-foreground">
                {selectedProvider.is_active ? "Bật Hoạt Động" : "Tạm Dừng"}
              </span>
              <Switch
                checked={selectedProvider.is_active}
                onCheckedChange={onToggleActive}
                aria-label="Bật hoặc tắt Provider"
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              disabled={isTesting}
              onClick={onTestConnection}
              className="h-9 text-xs gap-1.5"
            >
              {isTesting ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin text-primary" />
              ) : (
                <Play className="h-3.5 w-3.5 text-primary" />
              )}
              <span>{isTesting ? "Đang kiểm tra..." : "Test Kết Nối"}</span>
            </Button>

            <Button variant="outline" size="sm" onClick={onEdit} className="h-9 text-xs gap-1.5">
              <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
              <span>Chỉnh Sửa</span>
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              title="Xóa Provider"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {hasTestMsg && (
          <div
            className={`p-3 rounded-md text-xs flex items-center gap-2 ${
              testResult.success
                ? "bg-success/10 text-success border border-success/30"
                : "bg-destructive/10 text-destructive border border-destructive/30"
            }`}
          >
            {testResult.success ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <AlertTriangle className="h-4 w-4 shrink-0" />
            )}
            <span className="leading-relaxed font-medium">{testResult.message}</span>
          </div>
        )}
      </Card>
    </>
  );
};
