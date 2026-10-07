import {
  AlertTriangle,
  Bot,
  Brain,
  Check,
  CheckCircle2,
  Copy,
  Cpu,
  Eye,
  FlaskConical,
  Loader2,
  Plus,
  RotateCw,
  ScanText,
  Star,
  Trash2,
  Type,
  X,
  Zap,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import type {
  ModelProvider,
  ProviderModelsTestResponse,
  ProviderPreset,
  SingleModelTestResult,
  SystemModelDefaults,
} from "../../services/api-client";
import {
  getModelCapabilities,
  getModelDisplayName,
  PRESET_SUGGESTED_MODELS,
} from "./modelops-helpers";

export interface ModelsGridProps {
  selectedProvider: ModelProvider;
  presets: ProviderPreset[];
  systemDefaults?: SystemModelDefaults;
  modelTestResults: Record<string, SingleModelTestResult>;
  modelTestSummary: ProviderModelsTestResponse | null;
  unavailableModelsCount: number;
  isTestingAllModels: boolean;
  testingModelName: string | null;
  onOpenAddModelModal: () => void;
  onTestAllModels: (providerId: string) => void;
  onTestSingleModel: (providerId: string, modelName: string) => void;
  onRemoveModel: (provider: ModelProvider, modelName: string) => void;
  onCleanUnavailableModels: (provider: ModelProvider) => void;
  onQuickAddPresetModel: (provider: ModelProvider, modelName: string) => void;
}

export const ModelsGrid: React.FC<ModelsGridProps> = ({
  selectedProvider,
  presets,
  systemDefaults,
  modelTestResults,
  modelTestSummary,
  unavailableModelsCount,
  isTestingAllModels,
  testingModelName,
  onOpenAddModelModal,
  onTestAllModels,
  onTestSingleModel,
  onRemoveModel,
  onCleanUnavailableModels,
  onQuickAddPresetModel,
}) => {
  const [modelFilter, setModelFilter] = useState<
    "all" | "embedding" | "ocr" | "vision" | "reasoning" | "reranker" | "default"
  >("all");
  const [copiedModelId, setCopiedModelId] = useState<string | null>(null);

  const filteredModels = useMemo(() => {
    const allM = selectedProvider.models || [];
    if (modelFilter === "all") return allM;
    if (modelFilter === "embedding") {
      return allM.filter((m) => getModelCapabilities(m).isEmbedding);
    }
    if (modelFilter === "ocr") {
      return allM.filter((m) => getModelCapabilities(m).isOcr);
    }
    if (modelFilter === "vision") {
      return allM.filter((m) => getModelCapabilities(m).hasVision);
    }
    if (modelFilter === "reasoning") {
      return allM.filter((m) => getModelCapabilities(m).hasReasoning);
    }
    if (modelFilter === "reranker") {
      return allM.filter((m) => getModelCapabilities(m).isReranker);
    }
    if (modelFilter === "default") {
      return allM.filter(
        (m) =>
          (selectedProvider.id ===
            systemDefaults?.default_embedding_provider_id &&
            m === systemDefaults?.default_embedding_model) ||
          (selectedProvider.id ===
            systemDefaults?.default_reranker_provider_id &&
            m === systemDefaults?.default_reranker_model) ||
          (selectedProvider.id === systemDefaults?.default_ocr_provider_id &&
            m === systemDefaults?.default_ocr_model),
      );
    }
    return allM;
  }, [selectedProvider, modelFilter, systemDefaults]);

  const handleCopyModelId = (id: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(id);
      setCopiedModelId(id);
      setTimeout(() => setCopiedModelId(null), 1500);
    }
  };

  const currentPreset = presets.find((pr) => pr.code === selectedProvider.type);
  const suggestedList =
    currentPreset?.suggested_models ||
    PRESET_SUGGESTED_MODELS[selectedProvider.type] ||
    [];

  return (
    <Card className="p-6 space-y-5 border-border shadow-xs bg-card">
      {/* Header with Title, Count badge, Capabilities Filter, and Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/70">
        <div className="flex items-center gap-2.5">
          <h2 className="text-base font-bold text-foreground flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            Mô Hình Khả Dụng
          </h2>
          <Badge
            variant="outline"
            className="font-mono text-xs text-primary border-primary/30"
          >
            {(selectedProvider.models || []).length} models
          </Badge>
        </div>

        {/* Filter & Action Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Capability Filter Select */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground font-medium hidden md:inline">
              Lọc:
            </span>
            <Select
              value={modelFilter}
              onValueChange={(val) =>
                setModelFilter(
                  val as
                    | "all"
                    | "embedding"
                    | "ocr"
                    | "vision"
                    | "reasoning"
                    | "reranker"
                    | "default",
                )
              }
            >
              <SelectTrigger className="h-8 w-44 text-xs font-medium">
                <SelectValue placeholder="Tất cả mô hình" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tất cả mô hình</SelectItem>
                <SelectItem value="embedding">Embedding (Vector nhúng)</SelectItem>
                <SelectItem value="ocr">OCR & Bóc tách (Vision OCR)</SelectItem>
                <SelectItem value="vision">Vision (Thị giác)</SelectItem>
                <SelectItem value="reasoning">Reasoning (Suy luận)</SelectItem>
                <SelectItem value="reranker">Reranker (Tái xếp hạng)</SelectItem>
                <SelectItem value="default">Mặc định hệ thống</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Add Custom Model Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenAddModelModal}
            className="h-8 px-3 text-xs gap-1.5 text-primary border-primary/30 hover:bg-primary/10 cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Thêm Model</span>
          </Button>

          {/* Bulk Test Button */}
          <Button
            variant="outline"
            size="sm"
            disabled={
              isTestingAllModels || (selectedProvider.models || []).length === 0
            }
            onClick={() => onTestAllModels(selectedProvider.id)}
            className="h-8 px-3 text-xs text-primary border-primary/30 hover:bg-primary/10 gap-1.5 cursor-pointer"
            title="Gửi ping kiểm tra tính khả dụng thực tế của toàn bộ các model này"
          >
            {isTestingAllModels ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Zap className="h-3.5 w-3.5" />
            )}
            <span>{isTestingAllModels ? "Đang test..." : "Test tất cả"}</span>
          </Button>
        </div>
      </div>

      {/* Model Cards Grid (3 Columns on Desktop) */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {filteredModels.length === 0 &&
        (selectedProvider.models || []).length > 0 ? (
          <div className="col-span-full py-8 text-center text-xs text-muted-foreground italic border border-dashed rounded-lg">
            Không tìm thấy model nào phù hợp với bộ lọc đã chọn.
          </div>
        ) : null}

        {filteredModels.map((m) => {
          const isDefEmbedding =
            selectedProvider.id ===
              systemDefaults?.default_embedding_provider_id &&
            m === systemDefaults?.default_embedding_model;
          const isDefReranker =
            selectedProvider.id ===
              systemDefaults?.default_reranker_provider_id &&
            m === systemDefaults?.default_reranker_model;
          const isDefOcr =
            selectedProvider.id === systemDefaults?.default_ocr_provider_id &&
            m === systemDefaults?.default_ocr_model;
          const isDefault = isDefEmbedding || isDefReranker || isDefOcr;

          const testRes = modelTestResults[m];
          const isTestingThis = testingModelName === m || isTestingAllModels;
          const capabilities = getModelCapabilities(m);
          const displayName = getModelDisplayName(m);

          return (
            <div
              key={m}
              className={`rounded-lg border p-3 bg-card transition-all flex items-center justify-between gap-2.5 group relative hover:border-primary/50 hover:shadow-xs ${
                testRes?.status === "unavailable"
                  ? "border-destructive/50 bg-destructive/5"
                  : isDefault
                    ? "border-primary/40 bg-primary/5"
                    : "border-border/80"
              }`}
            >
              {/* Left Model Type Icon */}
              <div
                className={`p-2 rounded-md border shrink-0 flex items-center justify-center transition-colors ${
                  capabilities.isEmbedding
                    ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-600 dark:text-indigo-400"
                    : capabilities.isReranker
                      ? "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400"
                      : capabilities.isOcr
                        ? "bg-primary/10 border-primary/30 text-primary"
                        : capabilities.hasVision
                          ? "bg-sky-500/10 border-sky-500/30 text-sky-600 dark:text-sky-400"
                          : capabilities.hasReasoning
                            ? "bg-purple-500/10 border-purple-500/30 text-purple-600 dark:text-purple-400"
                            : "bg-muted/60 border-border/50 text-foreground/80"
                }`}
                title={capabilities.capabilityLabel}
              >
                {capabilities.isEmbedding ? (
                  <Cpu className="h-4 w-4" />
                ) : capabilities.isReranker ? (
                  <Zap className="h-4 w-4" />
                ) : capabilities.isOcr ? (
                  <ScanText className="h-4 w-4" />
                ) : capabilities.hasVision ? (
                  <Eye className="h-4 w-4" />
                ) : capabilities.hasReasoning ? (
                  <Brain className="h-4 w-4" />
                ) : (
                  <Bot className="h-4 w-4" />
                )}
              </div>

              {/* Center Info */}
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span
                    className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-muted/70 text-foreground border border-border/60 truncate max-w-[160px]"
                    title={m}
                  >
                    {m}
                  </span>

                  {/* Embedding Badge */}
                  {capabilities.isEmbedding && (
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1.5 py-0 h-3.5 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/25 gap-0.5 font-semibold"
                      title="Mô hình Vector Embedding (Kho Tri Thức & Semantic Search)"
                    >
                      <Cpu className="h-2.5 w-2.5" />
                      Embedding
                    </Badge>
                  )}

                  {/* Reranker Badge */}
                  {capabilities.isReranker && (
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1.5 py-0 h-3.5 bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/25 gap-0.5 font-semibold"
                      title="Mô hình Cross-Encoder Reranker (Tái xếp hạng ngữ nghĩa cho RAG)"
                    >
                      <Zap className="h-2.5 w-2.5" />
                      Reranker
                    </Badge>
                  )}

                  {/* OCR Badge */}
                  {capabilities.isOcr && (
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1.5 py-0 h-3.5 bg-primary/10 text-primary border-primary/25 gap-0.5 font-semibold"
                      title="Mô hình hỗ trợ bóc tách tài liệu và nhận diện OCR"
                    >
                      <ScanText className="h-2.5 w-2.5" />
                      OCR
                    </Badge>
                  )}

                  {/* Vision Badge (Non-OCR) */}
                  {capabilities.hasVision && !capabilities.isOcr && (
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1.5 py-0 h-3.5 bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/25 gap-0.5 font-medium"
                      title="Mô hình đa phương thức (Vision / Thị giác)"
                    >
                      <Eye className="h-2.5 w-2.5" />
                      Vision
                    </Badge>
                  )}

                  {/* Reasoning Badge */}
                  {capabilities.hasReasoning &&
                    !capabilities.isEmbedding &&
                    !capabilities.isReranker && (
                      <Badge
                        variant="outline"
                        className="text-[9px] px-1.5 py-0 h-3.5 bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/25 gap-0.5 font-medium"
                        title="Mô hình suy luận có tư duy CoT (Reasoning / Deep Thinking)"
                      >
                        <Brain className="h-2.5 w-2.5" />
                        Reasoning
                      </Badge>
                    )}

                  {/* Text Badge (Pure LLM only) */}
                  {!capabilities.hasVision &&
                    !capabilities.isOcr &&
                    !capabilities.isEmbedding &&
                    !capabilities.isReranker &&
                    !capabilities.hasReasoning && (
                      <Badge
                        variant="outline"
                        className="text-[9px] px-1 py-0 h-3.5 bg-muted/60 text-muted-foreground border-border/60 gap-0.5 font-normal"
                        title="Mô hình thuần văn bản (Text-only, không hỗ trợ OCR/Thị giác/Embedding)"
                      >
                        <Type className="h-2.5 w-2.5" />
                        Text
                      </Badge>
                    )}

                  {/* Default Roles Badges */}
                  {isDefEmbedding && (
                    <Badge
                      variant="secondary"
                      className="text-[9px] px-1.5 py-0 h-3.5 bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border border-indigo-500/30 gap-0.5 font-medium"
                      title="Mô hình Embedding mặc định toàn hệ thống"
                    >
                      <Star className="h-2.5 w-2.5 fill-current" />
                      Default Embed
                    </Badge>
                  )}
                  {isDefReranker && (
                    <Badge
                      variant="secondary"
                      className="text-[9px] px-1.5 py-0 h-3.5 bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30 gap-0.5 font-medium"
                      title="Mô hình Reranker mặc định toàn hệ thống"
                    >
                      <Star className="h-2.5 w-2.5 fill-current" />
                      Default Rerank
                    </Badge>
                  )}
                  {isDefOcr && (
                    <Badge
                      variant="secondary"
                      className="text-[9px] px-1.5 py-0 h-3.5 bg-primary/15 text-primary border border-primary/30 gap-0.5 font-medium"
                      title="Mô hình OCR mặc định toàn hệ thống"
                    >
                      <Star className="h-2.5 w-2.5 fill-current" />
                      Default OCR
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span
                    className="truncate max-w-[130px] italic"
                    title={capabilities.capabilityLabel}
                  >
                    {displayName}
                  </span>
                  <div className="flex items-center gap-1 text-muted-foreground/70 shrink-0">
                    {capabilities.isEmbedding && (
                      <span title="Chuyên gia Nhúng Vector Ngữ Nghĩa (Vector Embedding)">
                        <Cpu className="h-3 w-3 text-indigo-500" />
                      </span>
                    )}
                    {capabilities.isReranker && (
                      <span title="Chuyên gia Tái xếp hạng RAG (Cross-Encoder)">
                        <Zap className="h-3 w-3 text-amber-500" />
                      </span>
                    )}
                    {capabilities.isOcr && (
                      <span title="Chuyên gia OCR / Bóc tách tài liệu">
                        <ScanText className="h-3 w-3 text-primary" />
                      </span>
                    )}
                    {capabilities.hasVision && !capabilities.isOcr && (
                      <span title="Hỗ trợ Vision / Đa phương thức">
                        <Eye className="h-3 w-3 text-primary" />
                      </span>
                    )}
                    {capabilities.hasReasoning && (
                      <span title="Hỗ trợ Suy luận chuyên sâu (Reasoning)">
                        <Brain className="h-3 w-3 text-muted-foreground" />
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Toolbar / Test Badge */}
              <div className="flex items-center gap-1 shrink-0">
                {/* Test Status Indicator */}
                {isTestingThis ? (
                  <span
                    className="text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded flex items-center gap-1"
                    title="Đang kiểm tra..."
                  >
                    <RotateCw className="h-2.5 w-2.5 animate-spin" />
                  </span>
                ) : testRes ? (
                  testRes.status === "available" ? (
                    <span
                      className="inline-flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded font-sans border border-emerald-500/20"
                      title={`Khả dụng (${testRes.latency_ms}ms) - ${testRes.message}`}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
                      <span>{testRes.latency_ms}ms</span>
                    </span>
                  ) : testRes.status === "temporarily_overloaded" ||
                    testRes.message?.includes("503") ||
                    testRes.message?.includes("quá tải") ? (
                    <span
                      className="inline-flex items-center gap-1 text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded font-sans border border-amber-500/30"
                      title={`Máy chủ quá tải tạm thời: ${testRes.message}`}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" />
                      <span>503 Tạm bận</span>
                    </span>
                  ) : testRes.status === "deprecated" ? (
                    <span
                      className="inline-flex items-center gap-1 text-[10px] text-destructive bg-destructive/10 px-1.5 py-0.5 rounded font-sans border border-destructive/30"
                      title={`Đã hết hạn (410 Gone): ${testRes.message}`}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-destructive shrink-0" />
                      <span>410 Hết hạn</span>
                    </span>
                  ) : testRes.status === "payment_required" ? (
                    <span
                      className="inline-flex items-center gap-1 text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded font-sans border border-amber-500/30"
                      title={`Yêu cầu nạp credits (HTTP 402): ${testRes.message}`}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" />
                      <span>402 Credits</span>
                    </span>
                  ) : testRes.status === "unavailable" ? (
                    <span
                      className="inline-flex items-center gap-1 text-[10px] text-destructive bg-destructive/10 px-1.5 py-0.5 rounded font-sans border border-destructive/30"
                      title={`Không tìm thấy (404): ${testRes.message}`}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-destructive shrink-0" />
                      <span>404</span>
                    </span>
                  ) : testRes.status === "rate_limited" ? (
                    <span
                      className="inline-flex items-center gap-1 text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded font-sans border border-amber-500/30"
                      title={testRes.message}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" />
                      <span>429</span>
                    </span>
                  ) : (
                    <span
                      className="inline-flex items-center gap-1 text-[10px] text-destructive bg-destructive/10 px-1.5 py-0.5 rounded font-sans border border-destructive/30"
                      title={testRes.message}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-destructive shrink-0" />
                      <span>Lỗi</span>
                    </span>
                  )
                ) : null}

                {/* Quick Action Buttons */}
                <button
                  type="button"
                  disabled={isTestingThis}
                  onClick={() => onTestSingleModel(selectedProvider.id, m)}
                  className="p-1 rounded text-muted-foreground hover:text-primary hover:bg-muted/70 transition-colors cursor-pointer"
                  title={`Test hiệu lực model '${m}'`}
                >
                  <FlaskConical className="h-3.5 w-3.5" />
                </button>

                <button
                  type="button"
                  onClick={() => handleCopyModelId(m)}
                  className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/70 transition-colors cursor-pointer"
                  title="Sao chép Model ID"
                >
                  {copiedModelId === m ? (
                    <Check className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => onRemoveModel(selectedProvider, m)}
                  className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
                  title={`Xóa model '${m}'`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          );
        })}

        {/* Dashed "+ Add Model" Card Button */}
        <button
          type="button"
          onClick={onOpenAddModelModal}
          className="border-2 border-dashed border-primary/30 hover:border-primary hover:bg-primary/5 rounded-lg p-3.5 flex items-center justify-center gap-2 text-primary font-medium text-xs transition-all cursor-pointer min-h-[58px]"
          title="Thêm mô hình tùy chỉnh mới vào Provider"
        >
          <Plus className="h-4 w-4" />
          <span>Thêm model</span>
        </button>
      </div>

      {/* Dead Models Cleanup Alert */}
      {unavailableModelsCount > 0 && (
        <div className="flex items-center justify-between p-3 rounded-md bg-destructive/10 border border-destructive/30 text-xs">
          <div className="flex items-center gap-2 text-destructive font-medium">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>
              Phát hiện <strong>{unavailableModelsCount}</strong> model không
              còn hiệu lực do nhà cung cấp ngừng cung cấp (HTTP 404).
            </span>
          </div>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => onCleanUnavailableModels(selectedProvider)}
            className="h-7 px-2.5 text-xs gap-1 cursor-pointer"
            title="Tự động loại bỏ các model không còn hỗ trợ khỏi cấu hình Provider"
          >
            <Trash2 className="h-3 w-3" />
            <span>Dọn Model Lỗi</span>
          </Button>
        </div>
      )}

      {/* Test Success Summary Banner */}
      {modelTestSummary && unavailableModelsCount === 0 && (
        <div className="flex items-center gap-2 p-2.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>
            Đã kiểm tra <strong>{modelTestSummary.total_models}</strong> model:
            Toàn bộ <strong>{modelTestSummary.available_models}</strong> model
            đều đang hoạt động tốt!
          </span>
        </div>
      )}

      {/* Quick Suggest from Presets */}
      {suggestedList.length > 0 && (
        <div className="pt-3 border-t border-border/60 space-y-2">
          <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
            Gợi Ý 1-Click Thêm Nhanh ({selectedProvider.name}):
          </span>
          <div className="flex flex-wrap gap-1.5">
            {suggestedList.map((sm) => {
              const isAlreadyAdded = (selectedProvider.models || []).includes(
                sm,
              );
              return (
                <button
                  type="button"
                  key={sm}
                  disabled={isAlreadyAdded}
                  onClick={() => onQuickAddPresetModel(selectedProvider, sm)}
                  className={`text-[11px] font-mono px-2 py-1 rounded border transition-colors ${
                    isAlreadyAdded
                      ? "bg-muted/40 text-muted-foreground/50 border-transparent cursor-not-allowed"
                      : "bg-muted/20 hover:bg-primary/10 hover:text-primary hover:border-primary/40 text-muted-foreground border-border cursor-pointer"
                  }`}
                >
                  + {sm}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
};
