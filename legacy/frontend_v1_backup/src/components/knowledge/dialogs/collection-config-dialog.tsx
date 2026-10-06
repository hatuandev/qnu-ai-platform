import { AlertCircle, Cpu, Eye, Lock, Settings, Sparkles } from "lucide-react";
import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { CollectionDataProcessingConfig } from "@/types/knowledge";

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

const AVAILABLE_EMBEDDINGS = [
  {
    model: "bge-m3:latest",
    provider: "prov_rtx5090_ollama",
    label: "BGE-M3 Multilingual (1024D) - RTX 5090 On-Premise",
    dim: 1024,
  },
  {
    model: "@cf/baai/bge-m3",
    provider: "prov_cloudflare",
    label: "Cloudflare BGE-M3 (1024D) - Cloud Edge",
    dim: 1024,
  },
  {
    model: "text-embedding-3-small",
    provider: "prov_openai",
    label: "OpenAI Text-Embedding-3 Small (1536D)",
    dim: 1536,
  },
  {
    model: "text-embedding-3-large",
    provider: "prov_openai",
    label: "OpenAI Text-Embedding-3 Large (3072D)",
    dim: 3072,
  },
];

const AVAILABLE_OCR_MODELS = [
  {
    model: "qwen3-vl:8b",
    provider: "prov_rtx5090_ollama",
    label: "Qwen3-VL 8B Instruct (RTX 5090 On-Premise) - Khuyến nghị",
  },
  {
    model: "gemini-3.1-flash-lite",
    provider: "prov_gemini",
    label: "Google Gemini 3.1 Flash Lite (Google AI)",
  },
  {
    model: "gemini-2.5-flash",
    provider: "prov_gemini",
    label: "Google Gemini 2.5 Flash (Google AI)",
  },
  {
    model: "gpt-4o-mini",
    provider: "prov_openai",
    label: "OpenAI GPT-4o-mini Vision (OpenAI Cloud)",
  },
  {
    model: "mistral-ocr-2503",
    provider: "prov_mistral",
    label: "Mistral OCR 2503 Document Understanding",
  },
];

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
  const [activeTab, setActiveTab] = useState<"general" | "embedding" | "ocr">("general");

  const isVectorLocked = documentCount > 0;

  const currentEmbeddingModel = dataProcessingConfig.embedding_model || "bge-m3:latest";
  const currentPrimaryOcr = dataProcessingConfig.primary_ocr_model || "qwen3-vl:8b";
  const currentFallbackOcr = dataProcessingConfig.fallback_ocr_model || "gemini-3.1-flash-lite";
  const isOcrRescueEnabled = dataProcessingConfig.enable_ocr_rescue !== false;

  const handleSelectEmbedding = (item: (typeof AVAILABLE_EMBEDDINGS)[0]) => {
    if (isVectorLocked) return;
    setDataProcessingConfig((prev) => ({
      ...prev,
      embedding_model: item.model,
      embedding_provider_id: item.provider,
      embedding_dimension: item.dim,
    }));
  };

  const handleSelectPrimaryOcr = (item: (typeof AVAILABLE_OCR_MODELS)[0]) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      primary_ocr_model: item.model,
      primary_ocr_provider_id: item.provider,
    }));
  };

  const handleSelectFallbackOcr = (item: (typeof AVAILABLE_OCR_MODELS)[0]) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      fallback_ocr_model: item.model,
      fallback_ocr_provider_id: item.provider,
    }));
  };

  const handleToggleOcrRescue = (checked: boolean) => {
    setDataProcessingConfig((prev) => ({
      ...prev,
      enable_ocr_rescue: checked,
    }));
  };

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
              <Badge variant="outline" className="text-[10px] gap-1 font-mono">
                <Lock className="size-3 text-amber-500" />
                <span>{documentCount} tài liệu</span>
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as "general" | "embedding" | "ocr")}
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
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-400 flex items-start gap-2.5">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <div className="space-y-0.5 text-[11px] leading-relaxed">
                  <p className="font-semibold">
                    Quy tắc Bất biến Không gian Vector (Vector Invariance)
                  </p>
                  <p>
                    Kho này hiện có <strong>{documentCount}</strong> tài liệu đã được vector hóa và
                    lập chỉ mục trong Qdrant. Không thể thay đổi mô hình Embedding để tránh lệch
                    không gian toán học. Để thay đổi, vui lòng xóa toàn bộ tài liệu trước.
                  </p>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground block">
                Mô hình Embedding được áp dụng
              </label>
              <div className="space-y-2">
                {AVAILABLE_EMBEDDINGS.map((item) => {
                  const isSelected = currentEmbeddingModel === item.model;
                  return (
                    <div
                      key={item.model}
                      onClick={() => handleSelectEmbedding(item)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        isSelected
                          ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                          : "border-border hover:border-muted-foreground/30 bg-card"
                      } ${isVectorLocked ? "opacity-75 cursor-not-allowed" : "cursor-pointer"}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-xs text-foreground flex items-center gap-2">
                          <Cpu className="size-3.5 text-primary" />
                          <span>{item.label}</span>
                        </div>
                        {isSelected && (
                          <Badge variant="default" className="text-[10px] px-1.5 py-0 h-4">
                            Đang dùng
                          </Badge>
                        )}
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-1 flex items-center gap-3">
                        <span>Model: <code className="text-foreground">{item.model}</code></span>
                        <span>•</span>
                        <span>Kích thước vector: {item.dim} chiều</span>
                      </div>
                    </div>
                  );
                })}
              </div>
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
                  Tự động chuyển tiếp trang PDF scan hoặc ảnh sang mô hình Vision OCR chuyên sâu
                </p>
              </div>
              <Switch
                checked={isOcrRescueEnabled}
                onCheckedChange={handleToggleOcrRescue}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground block">
                Mô hình Vision OCR Chính (Primary)
              </label>
              <div className="space-y-1.5">
                {AVAILABLE_OCR_MODELS.map((item) => {
                  const isSelected = currentPrimaryOcr === item.model;
                  return (
                    <div
                      key={item.model}
                      onClick={() => handleSelectPrimaryOcr(item)}
                      className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                          : "border-border hover:border-muted-foreground/30 bg-card"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-xs text-foreground">
                          {item.label}
                        </span>
                        {isSelected && (
                          <Badge variant="default" className="text-[10px] px-1.5 py-0 h-4">
                            Chính
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground block">
                Mô hình Vision OCR Dự phòng (Fallback)
              </label>
              <div className="space-y-1.5">
                {AVAILABLE_OCR_MODELS.map((item) => {
                  const isSelected = currentFallbackOcr === item.model;
                  return (
                    <div
                      key={item.model}
                      onClick={() => handleSelectFallbackOcr(item)}
                      className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? "border-amber-500 bg-amber-500/5 ring-1 ring-amber-500/30"
                          : "border-border hover:border-muted-foreground/30 bg-card"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-xs text-foreground">
                          {item.label}
                        </span>
                        {isSelected && (
                          <Badge variant="outline" className="text-[10px] text-amber-600 dark:text-amber-400 border-amber-500/30 px-1.5 py-0 h-4">
                            Dự phòng
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
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
            disabled={isSaving}
          >
            {isSaving ? "Đang lưu cấu hình..." : "Lưu Cấu Hình"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
