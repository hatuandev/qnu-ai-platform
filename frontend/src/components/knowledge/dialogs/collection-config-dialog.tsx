import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  Cpu,
  ExternalLink,
  Eye,
  Loader2,
  Lock,
  RefreshCw,
  Settings,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiClient } from "@/services/modelops-api";
import type { CollectionDataProcessingConfig } from "@/types/knowledge";
import type { ModelOption } from "@/types/modelops";

interface CollectionConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  configName: string;
  setConfigName: (name: string) => void;
  configDescription: string;
  setConfigDescription: (desc: string) => void;
  documentCount?: number;
  dataProcessingConfig: CollectionDataProcessingConfig;
  setDataProcessingConfig: React.Dispatch<
    React.SetStateAction<CollectionDataProcessingConfig>
  >;
  isSaving: boolean;
  onSave: () => void;
}

export function CollectionConfigDialog({
  open,
  onOpenChange,
  configName,
  setConfigName,
  configDescription,
  setConfigDescription,
  documentCount = 0,
  dataProcessingConfig,
  setDataProcessingConfig,
  isSaving,
  onSave,
}: CollectionConfigDialogProps) {
  const [activeTab, setActiveTab] = useState<"general" | "embedding" | "ocr">(
    "general",
  );

  const isVectorLocked = documentCount > 0;

  // Dynamically resolve available models from ModelOps API
  const {
    data: modelDefaults,
    isLoading: isModelsLoading,
    isError: isModelsError,
    refetch: refetchModels,
  } = useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
    staleTime: 60000,
  });

  const availableEmbeddings: ModelOption[] =
    modelDefaults?.available_embeddings || [];
  const availableOcrs: ModelOption[] = modelDefaults?.available_ocrs || [];

  const currentEmbeddingModel = dataProcessingConfig.embedding_model || "";
  const currentEmbeddingProvider =
    dataProcessingConfig.embedding_provider_id || "";
  const currentPrimaryOcr = dataProcessingConfig.primary_ocr_model || "";
  const currentPrimaryOcrProvider =
    dataProcessingConfig.primary_ocr_provider_id || "";
  const currentFallbackOcr = dataProcessingConfig.fallback_ocr_model || "";
  const currentFallbackOcrProvider =
    dataProcessingConfig.fallback_ocr_provider_id || "";
  const isOcrRescueEnabled = dataProcessingConfig.enable_ocr_rescue !== false;

  const handleSelectEmbedding = (item: ModelOption) => {
    if (isVectorLocked) return;
    setDataProcessingConfig((prev) => ({
      ...prev,
      embedding_model: item.model_name,
      embedding_provider_id: item.provider_id,
      embedding_dimension: item.dimension || undefined,
    }));
  };

  const handleSelectPrimaryOcr = (item: ModelOption) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      primary_ocr_model: item.model_name,
      primary_ocr_provider_id: item.provider_id,
    }));
  };

  const handleSelectFallbackOcr = (item: ModelOption) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      fallback_ocr_model: item.model_name,
      fallback_ocr_provider_id: item.provider_id,
    }));
  };

  const handleToggleOcrRescue = (checked: boolean) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      enable_ocr_rescue: checked,
    }));
  };

  const isEmbeddingIncomplete =
    !dataProcessingConfig.embedding_model ||
    !dataProcessingConfig.embedding_provider_id ||
    !dataProcessingConfig.embedding_dimension;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl text-xs p-6">
        <DialogHeader className="pb-3 border-b border-border">
          <DialogTitle className="text-sm font-bold flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                <Settings className="size-4" />
              </div>
              <div>
                <span>Cấu hình Kho Tri Thức</span>
                <p className="text-[11px] font-normal text-muted-foreground">
                  Thiết lập tên kho, quy tắc vector hóa và mô hình thị giác OCR
                </p>
              </div>
            </div>
            {documentCount > 0 && (
              <Badge
                variant="outline"
                className="text-[10px] gap-1 font-mono text-warning border-warning/30 bg-warning/10"
              >
                <Lock className="size-3 text-warning" />
                <span>{documentCount} tài liệu</span>
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) =>
            setActiveTab(v as "general" | "embedding" | "ocr")
          }
          className="pt-2"
        >
          <TabsList className="grid grid-cols-3 h-8 text-xs mb-4">
            <TabsTrigger value="general" className="text-xs h-7 gap-1.5">
              <Settings className="size-3.5" />
              <span>Cơ bản</span>
            </TabsTrigger>
            <TabsTrigger value="embedding" className="text-xs h-7 gap-1.5">
              <Cpu className="size-3.5" />
              <span>Vector Embedding</span>
            </TabsTrigger>
            <TabsTrigger value="ocr" className="text-xs h-7 gap-1.5">
              <Eye className="size-3.5" />
              <span>Vision OCR</span>
            </TabsTrigger>
          </TabsList>

          {/* TAB 1: GENERAL */}
          <TabsContent value="general" className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="config-coll-name"
                className="text-xs font-semibold text-foreground block"
              >
                Tên kho tri thức
              </label>
              <Input
                id="config-coll-name"
                value={configName}
                onChange={(e) => setConfigName(e.target.value)}
                className="h-9 text-xs"
                placeholder="VD: Kho Tuyển sinh & Đào tạo 2026"
              />
            </div>
            <div className="space-y-1.5">
              <label
                htmlFor="config-coll-desc"
                className="text-xs font-semibold text-foreground block"
              >
                Mô tả chi tiết
              </label>
              <Input
                id="config-coll-desc"
                value={configDescription}
                onChange={(e) => setConfigDescription(e.target.value)}
                className="h-9 text-xs"
                placeholder="Mô tả phạm vi văn bản và tri thức chứa trong kho..."
              />
            </div>
          </TabsContent>

          {/* TAB 2: VECTOR EMBEDDING */}
          <TabsContent value="embedding" className="space-y-4">
            {isVectorLocked && (
              <div className="p-3 rounded-lg bg-warning/10 border border-warning/20 text-warning flex items-start gap-2.5">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <div className="space-y-0.5 text-[11px] leading-relaxed">
                  <p className="font-semibold text-foreground">
                    Quy tắc Bất biến Không gian Vector (Vector Invariance)
                  </p>
                  <p className="text-muted-foreground">
                    Kho này hiện có <strong>{documentCount}</strong> tài liệu đã
                    được vector hóa và lập chỉ mục trong Qdrant. Không thể thay
                    đổi mô hình Embedding để tránh lệch không gian toán học. Để
                    thay đổi, cần chạy quy trình di chuyển (migration) hoặc làm
                    trống tài liệu.
                  </p>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground block">
                  Mô hình Embedding được áp dụng
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => refetchModels()}
                  className="h-6 px-1.5 text-[10px] text-muted-foreground gap-1"
                >
                  <RefreshCw className="size-3" />
                  <span>Làm mới</span>
                </Button>
              </div>

              {isModelsLoading ? (
                <div className="p-6 text-center text-muted-foreground flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin text-primary" />
                  <span>Đang tải danh sách mô hình từ ModelOps...</span>
                </div>
              ) : isModelsError || availableEmbeddings.length === 0 ? (
                <div className="p-4 rounded-lg border border-border bg-card text-center space-y-2">
                  <p className="text-xs font-medium text-foreground">
                    Chưa có mô hình Embedding nào được cấu hình trong ModelOps
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    Vui lòng thiết lập nhà cung cấp và mô hình tại trang Quản lý
                    Mô hình trước khi cấu hình kho tri thức.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    asChild
                    className="h-7 text-xs gap-1.5 mt-2"
                  >
                    <Link to="/models">
                      <ExternalLink className="size-3" />
                      <span>Đến trang Quản lý Mô hình</span>
                    </Link>
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {availableEmbeddings.map((item) => {
                    const isSelected =
                      currentEmbeddingModel === item.model_name &&
                      currentEmbeddingProvider === item.provider_id;
                    return (
                      <Button
                        type="button"
                        variant="outline"
                        key={`${item.provider_id}-${item.model_name}`}
                        onClick={() => handleSelectEmbedding(item)}
                        disabled={isVectorLocked}
                        className={`h-auto w-full justify-start whitespace-normal p-3 rounded-lg border text-left transition-all ${
                          isSelected
                            ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                            : "border-border hover:border-muted-foreground/30 bg-card"
                        } ${isVectorLocked ? "opacity-75 cursor-not-allowed" : "cursor-pointer"}`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="font-medium text-xs text-foreground flex items-center gap-2">
                            <Cpu className="size-3.5 text-primary" />
                            <span>
                              {item.model_name} ({item.provider_name})
                            </span>
                          </div>
                          {isSelected && (
                            <Badge
                              variant="default"
                              className="text-[10px] px-1.5 py-0 h-4"
                            >
                              Đang dùng
                            </Badge>
                          )}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-1 flex items-center gap-3">
                          <span>
                            Nhà cung cấp:{" "}
                            <span className="text-foreground">
                              {item.provider_name}
                            </span>
                          </span>
                          <span>•</span>
                          <span>
                            Số chiều:{" "}
                            {item.dimension ? `${item.dimension}D` : "Chưa rõ"}
                          </span>
                        </div>
                      </Button>
                    );
                  })}
                </div>
              )}

              {isEmbeddingIncomplete && (
                <p className="text-[11px] text-destructive pt-1">
                  Mô hình embedding đã chọn thiếu thông tin provider hoặc
                  dimension trong ModelOps. Không thể lưu.
                </p>
              )}
            </div>
          </TabsContent>

          {/* TAB 3: VISION OCR */}
          <TabsContent value="ocr" className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-card">
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5">
                  <Sparkles className="size-3.5 text-primary" />
                  <span className="font-semibold text-xs text-foreground">
                    Cứu hộ Vision OCR khi PDF quét/ảnh
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Tự động chuyển tiếp trang PDF scan hoặc ảnh sang mô hình
                  Vision OCR chuyên sâu
                </p>
              </div>
              <Switch
                checked={isOcrRescueEnabled}
                onCheckedChange={handleToggleOcrRescue}
              />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold text-foreground block">
                Mô hình Vision OCR Chính (Primary)
              </span>
              {isModelsLoading ? (
                <div className="p-4 text-center text-muted-foreground flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin text-primary" />
                  <span>Đang tải mô hình OCR...</span>
                </div>
              ) : isModelsError || availableOcrs.length === 0 ? (
                <div className="p-3 rounded-lg border border-border bg-card text-center space-y-1.5">
                  <p className="text-xs text-muted-foreground">
                    Chưa có mô hình OCR nào được cấu hình trong ModelOps
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    asChild
                    className="h-7 text-xs gap-1.5"
                  >
                    <Link to="/models">
                      <ExternalLink className="size-3" />
                      <span>Cấu hình tại ModelOps</span>
                    </Link>
                  </Button>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {availableOcrs.map((item) => {
                    const isSelected =
                      currentPrimaryOcr === item.model_name &&
                      currentPrimaryOcrProvider === item.provider_id;
                    return (
                      <Button
                        type="button"
                        variant="outline"
                        key={`primary-${item.provider_id}-${item.model_name}`}
                        onClick={() => handleSelectPrimaryOcr(item)}
                        className={`h-auto w-full justify-start whitespace-normal p-2.5 rounded-lg border cursor-pointer text-left transition-all ${
                          isSelected
                            ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                            : "border-border hover:border-muted-foreground/30 bg-card"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-xs text-foreground">
                            {item.model_name} — {item.provider_name}
                          </span>
                          {isSelected && (
                            <Badge
                              variant="default"
                              className="text-[10px] px-1.5 py-0 h-4"
                            >
                              Chính
                            </Badge>
                          )}
                        </div>
                      </Button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold text-foreground block">
                Mô hình Vision OCR Dự phòng (Fallback)
              </span>
              {isModelsLoading ? (
                <div className="p-4 text-center text-muted-foreground flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin text-primary" />
                  <span>Đang tải mô hình OCR...</span>
                </div>
              ) : isModelsError || availableOcrs.length === 0 ? (
                <div className="p-3 rounded-lg border border-border bg-card text-center text-muted-foreground">
                  <p className="text-xs">
                    Chưa có mô hình OCR dự phòng trong ModelOps
                  </p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {availableOcrs.map((item) => {
                    const isSelected =
                      currentFallbackOcr === item.model_name &&
                      currentFallbackOcrProvider === item.provider_id;
                    return (
                      <Button
                        type="button"
                        variant="outline"
                        key={`fallback-${item.provider_id}-${item.model_name}`}
                        onClick={() => handleSelectFallbackOcr(item)}
                        className={`h-auto w-full justify-start whitespace-normal p-2.5 rounded-lg border cursor-pointer text-left transition-all ${
                          isSelected
                            ? "border-warning bg-warning/5 ring-1 ring-warning/30"
                            : "border-border hover:border-muted-foreground/30 bg-card"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-xs text-foreground">
                            {item.model_name} — {item.provider_name}
                          </span>
                          {isSelected && (
                            <Badge
                              variant="outline"
                              className="text-[10px] text-warning border-warning/30 px-1.5 py-0 h-4"
                            >
                              Dự phòng
                            </Badge>
                          )}
                        </div>
                      </Button>
                    );
                  })}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end gap-2 pt-4 border-t border-border mt-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => onOpenChange(false)}
          >
            Hủy bỏ
          </Button>
          <Button
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={onSave}
            disabled={isSaving || isEmbeddingIncomplete}
          >
            {isSaving ? "Đang lưu cấu hình..." : "Lưu Cấu Hình"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
