import {
  ArrowRight,
  Brain,
  Cpu,
  ExternalLink,
  Eye,
  Layers,
  Plus,
  RefreshCw,
  Sparkles,
  Zap,
} from "lucide-react";
import type React from "react";
import { useId, useMemo } from "react";
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
  ModelComboTaskType,
  ModelOption,
  OCRComboItem,
  SystemModelDefaults,
} from "../../types/modelops";
import { TASK_TYPE_META } from "./modelops-helpers";

export interface SystemDefaultsCardProps {
  systemDefaults?: SystemModelDefaults;
  availableEmbeddings: ModelOption[];
  availableRerankers: ModelOption[];
  availableOcrs: ModelOption[];
  allAvailableModels?: ModelOption[];
  isLoading?: boolean;
  onUpdateDefaults: (payload: Partial<SystemModelDefaults>) => void;
  onNavigateToCombos?: (taskFilter?: string) => void;
  onCreateComboForTask?: (taskType: ModelComboTaskType) => void;
}

export const SystemDefaultsCard: React.FC<SystemDefaultsCardProps> = ({
  systemDefaults,
  availableEmbeddings = [],
  availableRerankers = [],
  availableOcrs = [],
  allAvailableModels = [],
  isLoading,
  onUpdateDefaults,
  onNavigateToCombos,
  onCreateComboForTask,
}) => {
  const embeddingSelectId = useId();
  const rerankerSelectId = useId();
  const ocrSelectId = useId();
  const chatSelectId = useId();

  const allCombos = useMemo(
    () => systemDefaults?.model_combos || [],
    [systemDefaults?.model_combos],
  );

  // Lọc combos theo từng task_type
  const embeddingCombos = useMemo(
    () => allCombos.filter((c) => c.task_type === "embedding"),
    [allCombos],
  );
  const rerankerCombos = useMemo(
    () => allCombos.filter((c) => c.task_type === "reranker"),
    [allCombos],
  );
  const ocrCombos = useMemo(
    () => allCombos.filter((c) => (c.task_type || "ocr") === "ocr"),
    [allCombos],
  );
  const chatCombos = useMemo(
    () => allCombos.filter((c) => c.task_type === "chat"),
    [allCombos],
  );

  // Models cho Chat (lấy các model không phải embedding/reranker)
  const availableChatModels = useMemo(() => {
    return allAvailableModels.filter((m) => {
      const name = m.model_name.toLowerCase();
      return (
        !name.includes("embed") &&
        !name.includes("rerank") &&
        !name.includes("bge-")
      );
    });
  }, [allAvailableModels]);

  // Handler chuyển mode (single vs combo)
  const handleToggleChannelMode = (
    channel: "embedding" | "reranker" | "ocr" | "chat",
    mode: "single" | "combo",
  ) => {
    if (channel === "embedding") {
      onUpdateDefaults({ default_embedding_mode: mode });
    } else if (channel === "reranker") {
      onUpdateDefaults({ default_reranker_mode: mode });
    } else if (channel === "ocr") {
      onUpdateDefaults({ default_ocr_mode: mode });
    } else if (channel === "chat") {
      onUpdateDefaults({ default_chat_mode: mode });
    }
  };

  // Handler chọn combo cho channel
  const handleSelectComboForChannel = (
    channel: "embedding" | "reranker" | "ocr" | "chat",
    comboId: string,
  ) => {
    const target = allCombos.find((c) => c.id === comboId);
    if (!target?.models || target.models.length === 0) return;

    const firstModel = target.models[0];
    const updatedCombos = allCombos.map((c) => {
      if ((c.task_type || "ocr") === channel) {
        return { ...c, is_default: c.id === comboId };
      }
      return c;
    });

    if (channel === "embedding") {
      onUpdateDefaults({
        default_embedding_mode: "combo",
        default_embedding_combo_id: comboId,
        embedding_combo_chain: target.models,
        default_embedding_provider_id:
          firstModel.provider_id ||
          systemDefaults?.default_embedding_provider_id,
        default_embedding_model:
          firstModel.model_name || systemDefaults?.default_embedding_model,
        model_combos: updatedCombos,
      });
    } else if (channel === "reranker") {
      onUpdateDefaults({
        default_reranker_mode: "combo",
        default_reranker_combo_id: comboId,
        reranker_combo_chain: target.models,
        default_reranker_provider_id:
          firstModel.provider_id ||
          systemDefaults?.default_reranker_provider_id,
        default_reranker_model:
          firstModel.model_name || systemDefaults?.default_reranker_model,
        model_combos: updatedCombos,
      });
    } else if (channel === "ocr") {
      onUpdateDefaults({
        default_ocr_mode: "combo",
        default_ocr_combo_id: comboId,
        ocr_combo_chain: target.models,
        default_ocr_provider_id:
          firstModel.provider_id || systemDefaults?.default_ocr_provider_id,
        default_ocr_model:
          firstModel.model_name || systemDefaults?.default_ocr_model,
        model_combos: updatedCombos,
      });
    } else if (channel === "chat") {
      onUpdateDefaults({
        default_chat_mode: "combo",
        default_chat_combo_id: comboId,
        chat_combo_chain: target.models,
        default_chat_provider_id:
          firstModel.provider_id || systemDefaults?.default_chat_provider_id,
        default_chat_model:
          firstModel.model_name || systemDefaults?.default_chat_model,
        model_combos: updatedCombos,
      });
    }
  };

  // Helper render Chain Steps Visualization
  const renderChainPipeline = (
    chain: OCRComboItem[] | undefined,
    taskType: ModelComboTaskType,
  ) => {
    if (!chain || chain.length === 0) {
      return (
        <div className="p-3 rounded-lg border border-dashed border-border/80 bg-muted/20 text-center text-xs text-muted-foreground">
          Chưa cấu hình các bước trong chuỗi dự phòng.
        </div>
      );
    }

    const meta = TASK_TYPE_META[taskType];

    return (
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center justify-between gap-1 text-[11px] text-muted-foreground px-1">
          <span className="font-semibold uppercase tracking-wider text-[10px] truncate">
            Luồng Failover {meta?.shortLabel || ""} ({chain.length} Tầng)
          </span>
          <span className="font-mono text-[10px] text-muted-foreground shrink-0">
            Ưu tiên 1 ➔ {chain.length}
          </span>
        </div>
        <div className="grid grid-cols-1 gap-1.5">
          {chain.map((step, idx) => {
            const isPrimary = idx === 0;
            const isActive = step.is_active ?? true;

            return (
              <div
                key={`${step.provider_id}-${step.model_name}`}
                className={`flex items-center justify-between px-3 py-2 rounded-md border text-xs transition-colors ${
                  isActive
                    ? isPrimary
                      ? "bg-primary/5 border-primary/40 shadow-2xs"
                      : "bg-card border-border/70 hover:border-border"
                    : "bg-muted/40 border-dashed border-border/60 opacity-60"
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className={`size-5 rounded-full flex items-center justify-center text-[10px] font-bold font-mono shrink-0 ${
                      isPrimary
                        ? "bg-primary text-primary-foreground shadow-xs"
                        : "bg-muted text-muted-foreground border border-border"
                    }`}
                  >
                    {idx + 1}
                  </div>
                  <div className="truncate">
                    <div className="flex items-center gap-1.5">
                      <span className="font-semibold text-foreground truncate">
                        {step.model_name}
                      </span>
                      {isPrimary && (
                        <Badge
                          variant="default"
                          className="text-[9px] px-1.5 py-0 h-4 font-mono uppercase bg-primary text-primary-foreground"
                        >
                          Chính
                        </Badge>
                      )}
                      {!isActive && (
                        <Badge
                          variant="secondary"
                          className="text-[9px] px-1 py-0 h-4 font-mono text-muted-foreground"
                        >
                          Tắt
                        </Badge>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {step.provider_name || step.provider_id}
                      {step.description ? ` • ${step.description}` : ""}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0 pl-2">
                  {idx < chain.length - 1 && (
                    <span className="text-[10px] text-muted-foreground/60 hidden sm:inline">
                      Failover ➔
                    </span>
                  )}
                  <span
                    className={`size-2 rounded-full ${
                      isActive ? "bg-emerald-500 animate-pulse" : "bg-muted"
                    }`}
                    title={isActive ? "Mô hình khả dụng" : "Mô hình tạm tắt"}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Xác định active state của từng pipeline
  const embeddingMode = systemDefaults?.default_embedding_mode || "combo";
  const rerankerMode = systemDefaults?.default_reranker_mode || "combo";
  const ocrMode = systemDefaults?.default_ocr_mode || "combo";
  const chatMode = systemDefaults?.default_chat_mode || "single";

  const activeEmbeddingChain =
    systemDefaults?.embedding_combo_chain &&
    systemDefaults.embedding_combo_chain.length > 0
      ? systemDefaults.embedding_combo_chain
      : embeddingCombos.find((c) => c.is_default)?.models ||
        embeddingCombos[0]?.models;

  const activeRerankerChain =
    systemDefaults?.reranker_combo_chain &&
    systemDefaults.reranker_combo_chain.length > 0
      ? systemDefaults.reranker_combo_chain
      : rerankerCombos.find((c) => c.is_default)?.models ||
        rerankerCombos[0]?.models;

  const activeOcrChain =
    systemDefaults?.ocr_combo_chain && systemDefaults.ocr_combo_chain.length > 0
      ? systemDefaults.ocr_combo_chain
      : ocrCombos.find((c) => c.is_default)?.models || ocrCombos[0]?.models;

  const activeChatChain =
    systemDefaults?.chat_combo_chain &&
    systemDefaults.chat_combo_chain.length > 0
      ? systemDefaults.chat_combo_chain
      : chatCombos.find((c) => c.is_default)?.models || chatCombos[0]?.models;

  return (
    <div className="space-y-6">
      {/* Executive Matrix Header */}
      <Card className="p-3.5 sm:p-4 bg-gradient-to-r from-card via-card to-primary/5 border-primary/20 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start sm:items-center gap-2.5 sm:gap-3">
            <div className="p-2 sm:p-2.5 rounded-xl bg-primary/10 text-primary shrink-0 mt-0.5 sm:mt-0">
              <Sparkles className="size-4.5 sm:size-5" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <h3 className="text-sm sm:text-base font-bold text-foreground">
                  Ma Trận Định Tuyến & Dự Phòng
                </h3>
                <Badge
                  variant="outline"
                  className="text-[9px] sm:text-[10px] font-mono border-primary/30 text-primary bg-primary/5 shrink-0"
                >
                  Zero-Downtime AI
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2 sm:line-clamp-none">
                Cấu hình mô hình ưu tiên và chính sách chuyển mạch dự phòng (JIT
                Failover) tự động khi gặp lỗi 429/Timeout cho 4 kênh nhiệm vụ
                cốt lõi.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
            {isLoading && (
              <RefreshCw className="size-4 animate-spin text-primary shrink-0" />
            )}
            {onNavigateToCombos && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onNavigateToCombos()}
                className="h-8 text-xs gap-1.5 w-full sm:w-auto justify-center"
              >
                <Layers className="size-3.5 text-primary" />
                <span>Combos ({allCombos.length})</span>
                <ArrowRight className="size-3 text-muted-foreground" />
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* 4 Mission Pipelines Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ========================================================= */}
        {/* 1. KÊNH EMBEDDING (Nhúng Vector Kho Tri Thức) */}
        {/* ========================================================= */}
        <Card className="p-4 border-border/80 bg-card space-y-4 shadow-2xs hover:border-primary/40 transition-colors">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-2 border-b border-border/60 pb-3">
            <div className="flex items-start sm:items-center gap-2.5 min-w-0">
              <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0 mt-0.5 sm:mt-0">
                <Cpu className="size-4" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                  <h4 className="text-sm font-bold text-foreground">
                    1. Nhúng Vector (Embedding)
                  </h4>
                  <Badge
                    variant="outline"
                    className="text-[10px] font-mono border-primary/20 text-primary bg-primary/5 shrink-0"
                  >
                    1024-dim
                  </Badge>
                </div>
                <p className="text-[11px] text-muted-foreground truncate sm:whitespace-normal">
                  Chuyển văn bản giáo trình & đề thi thành vector ngữ nghĩa.
                </p>
              </div>
            </div>

            {/* Mode Switcher */}
            <div className="flex items-center p-0.5 rounded-lg bg-muted/70 border border-border/70 shrink-0 w-full sm:w-auto">
              <button
                type="button"
                onClick={() => handleToggleChannelMode("embedding", "single")}
                className={`flex-1 sm:flex-initial text-center justify-center px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                  embeddingMode === "single"
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Mô Hình Đơn
              </button>
              <button
                type="button"
                onClick={() => handleToggleChannelMode("embedding", "combo")}
                className={`flex-1 sm:flex-initial text-center justify-center px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                  embeddingMode === "combo"
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Chuỗi Combo
              </button>
            </div>
          </div>

          {embeddingMode === "single" ? (
            <div className="space-y-2.5">
              <label
                htmlFor={embeddingSelectId}
                className="text-[11px] font-semibold text-foreground flex flex-col sm:flex-row sm:items-center justify-between gap-0.5 sm:gap-2"
              >
                <span>Chỉ định mô hình Embedding duy nhất:</span>
                <span className="text-[10px] font-normal text-muted-foreground">
                  (Không có failover tự động khi 429)
                </span>
              </label>
              <Select
                value={`${systemDefaults?.default_embedding_provider_id}:::${systemDefaults?.default_embedding_model}`}
                onValueChange={(val) => {
                  const [pId, mName] = val.split(":::");
                  if (pId && mName) {
                    onUpdateDefaults({
                      default_embedding_provider_id: pId,
                      default_embedding_model: mName,
                      default_embedding_mode: "single",
                    });
                  }
                }}
              >
                <SelectTrigger
                  id={embeddingSelectId}
                  className="w-full h-9 text-xs font-mono bg-card"
                >
                  <SelectValue placeholder="Chọn mô hình Embedding..." />
                </SelectTrigger>
                <SelectContent>
                  {availableEmbeddings.map((opt) => (
                    <SelectItem
                      key={`emb-${opt.provider_id}-${opt.model_name}`}
                      value={`${opt.provider_id}:::${opt.model_name}`}
                    >
                      <span className="font-semibold">{opt.model_name}</span>{" "}
                      <span className="text-muted-foreground text-[11px]">
                        ({opt.provider_name})
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-semibold text-foreground">
                  Combo dự phòng đang áp dụng:
                </span>
                {onCreateComboForTask && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onCreateComboForTask("embedding")}
                    className="h-6 text-[11px] text-primary hover:text-primary/80 hover:underline gap-1 px-1.5"
                  >
                    <Plus className="size-3" />
                    <span>Tạo Combo</span>
                  </Button>
                )}
              </div>

              {embeddingCombos.length > 0 && (
                <Select
                  value={
                    systemDefaults?.default_embedding_combo_id ||
                    embeddingCombos.find((c) => c.is_default)?.id ||
                    embeddingCombos[0]?.id
                  }
                  onValueChange={(comboId) =>
                    handleSelectComboForChannel("embedding", comboId)
                  }
                >
                  <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
                    <SelectValue placeholder="Chọn Combo Embedding..." />
                  </SelectTrigger>
                  <SelectContent>
                    {embeddingCombos.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        <span className="font-bold">{c.name}</span>{" "}
                        <span className="text-muted-foreground text-[11px]">
                          ({c.models?.length || 0} tầng • {c.strategy})
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {renderChainPipeline(activeEmbeddingChain, "embedding")}
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5 min-w-0">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="truncate">
                Chính sách: Failover qua Cloudflare Edge ➔ Local BGE-M3
              </span>
            </span>
            {onNavigateToCombos && (
              <button
                type="button"
                onClick={() => onNavigateToCombos("embedding")}
                className="text-primary hover:text-primary/80 hover:underline flex items-center gap-1 shrink-0 self-end sm:self-auto"
              >
                <span>Xem chi tiết</span>
                <ExternalLink className="size-3" />
              </button>
            )}
          </div>
        </Card>

        {/* ========================================================= */}
        {/* 2. KÊNH RERANKER (Tái Xếp Hạng RAG) */}
        {/* ========================================================= */}
        <Card className="p-4 border-border/80 bg-card space-y-4 shadow-2xs hover:border-primary/40 transition-colors">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-2 border-b border-border/60 pb-3">
            <div className="flex items-start sm:items-center gap-2.5 min-w-0">
              <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0 mt-0.5 sm:mt-0">
                <Zap className="size-4" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                  <h4 className="text-sm font-bold text-foreground">
                    2. Tái Xếp Hạng (Reranker)
                  </h4>
                  <Badge
                    variant="outline"
                    className="text-[10px] font-mono border-primary/20 text-primary bg-primary/5 shrink-0"
                  >
                    Cross-Encoder
                  </Badge>
                </div>
                <p className="text-[11px] text-muted-foreground truncate sm:whitespace-normal">
                  Tái chấm điểm Top-K văn bản trước khi đưa vào Prompt LLM.
                </p>
              </div>
            </div>

            {/* Mode Switcher */}
            <div className="flex items-center p-0.5 rounded-lg bg-muted/70 border border-border/70 shrink-0 w-full sm:w-auto">
              <button
                type="button"
                onClick={() => handleToggleChannelMode("reranker", "single")}
                className={`flex-1 sm:flex-initial text-center justify-center px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                  rerankerMode === "single"
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Mô Hình Đơn
              </button>
              <button
                type="button"
                onClick={() => handleToggleChannelMode("reranker", "combo")}
                className={`flex-1 sm:flex-initial text-center justify-center px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                  rerankerMode === "combo"
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Chuỗi Combo
              </button>
            </div>
          </div>

          {rerankerMode === "single" ? (
            <div className="space-y-2.5">
              <label
                htmlFor={rerankerSelectId}
                className="text-[11px] font-semibold text-foreground flex flex-col sm:flex-row sm:items-center justify-between gap-0.5 sm:gap-2"
              >
                <span>Chỉ định mô hình Reranker duy nhất:</span>
                <span className="text-[10px] font-normal text-muted-foreground">
                  (Không failover tự động)
                </span>
              </label>
              <Select
                value={`${systemDefaults?.default_reranker_provider_id}:::${systemDefaults?.default_reranker_model}`}
                onValueChange={(val) => {
                  const [pId, mName] = val.split(":::");
                  if (pId && mName) {
                    onUpdateDefaults({
                      default_reranker_provider_id: pId,
                      default_reranker_model: mName,
                      default_reranker_mode: "single",
                    });
                  }
                }}
              >
                <SelectTrigger
                  id={rerankerSelectId}
                  className="w-full h-9 text-xs font-mono bg-card"
                >
                  <SelectValue placeholder="Chọn mô hình Reranker..." />
                </SelectTrigger>
                <SelectContent>
                  {availableRerankers.map((opt) => (
                    <SelectItem
                      key={`rerank-${opt.provider_id}-${opt.model_name}`}
                      value={`${opt.provider_id}:::${opt.model_name}`}
                    >
                      <span className="font-semibold">{opt.model_name}</span>{" "}
                      <span className="text-muted-foreground text-[11px]">
                        ({opt.provider_name})
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-semibold text-foreground">
                  Combo dự phòng đang áp dụng:
                </span>
                {onCreateComboForTask && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onCreateComboForTask("reranker")}
                    className="h-6 text-[11px] text-primary hover:text-primary/80 hover:underline gap-1 px-1.5"
                  >
                    <Plus className="size-3" />
                    <span>Tạo Combo</span>
                  </Button>
                )}
              </div>

              {rerankerCombos.length > 0 && (
                <Select
                  value={
                    systemDefaults?.default_reranker_combo_id ||
                    rerankerCombos.find((c) => c.is_default)?.id ||
                    rerankerCombos[0]?.id
                  }
                  onValueChange={(comboId) =>
                    handleSelectComboForChannel("reranker", comboId)
                  }
                >
                  <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
                    <SelectValue placeholder="Chọn Combo Reranker..." />
                  </SelectTrigger>
                  <SelectContent>
                    {rerankerCombos.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        <span className="font-bold">{c.name}</span>{" "}
                        <span className="text-muted-foreground text-[11px]">
                          ({c.models?.length || 0} tầng • {c.strategy})
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {renderChainPipeline(activeRerankerChain, "reranker")}
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5 min-w-0">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="truncate">
                Chính sách: BGE Cross-Encoder ➔ RRF Score Hợp Nhất
              </span>
            </span>
            {onNavigateToCombos && (
              <button
                type="button"
                onClick={() => onNavigateToCombos("reranker")}
                className="text-primary hover:text-primary/80 hover:underline flex items-center gap-1 shrink-0 self-end sm:self-auto"
              >
                <span>Xem chi tiết</span>
                <ExternalLink className="size-3" />
              </button>
            )}
          </div>
        </Card>

        {/* ========================================================= */}
        {/* 3. KÊNH OCR THỊ GIÁC (Bóc Tách Văn Bản & Bảng Biểu) */}
        {/* ========================================================= */}
        <Card className="p-4 border-border/80 bg-card space-y-4 shadow-2xs hover:border-primary/40 transition-colors">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-2 border-b border-border/60 pb-3">
            <div className="flex items-start sm:items-center gap-2.5 min-w-0">
              <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0 mt-0.5 sm:mt-0">
                <Eye className="size-4" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                  <h4 className="text-sm font-bold text-foreground">
                    3. Bóc Tách & OCR (Vision)
                  </h4>
                  <Badge
                    variant="outline"
                    className="text-[10px] font-mono border-primary/20 text-primary bg-primary/5 shrink-0"
                  >
                    Scan & Bảng Biểu
                  </Badge>
                </div>
                <p className="text-[11px] text-muted-foreground truncate sm:whitespace-normal">
                  Nhận diện văn bản scan tiếng Việt, con dấu đỏ và bảng điểm
                  PDF.
                </p>
              </div>
            </div>

            {/* Mode Switcher */}
            <div className="flex items-center p-0.5 rounded-lg bg-muted/70 border border-border/70 shrink-0 w-full sm:w-auto">
              <button
                type="button"
                onClick={() => handleToggleChannelMode("ocr", "single")}
                className={`flex-1 sm:flex-initial text-center justify-center px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                  ocrMode === "single"
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Mô Hình Đơn
              </button>
              <button
                type="button"
                onClick={() => handleToggleChannelMode("ocr", "combo")}
                className={`flex-1 sm:flex-initial text-center justify-center px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                  ocrMode === "combo"
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Chuỗi Combo
              </button>
            </div>
          </div>

          {ocrMode === "single" ? (
            <div className="space-y-2.5">
              <label
                htmlFor={ocrSelectId}
                className="text-[11px] font-semibold text-foreground flex flex-col sm:flex-row sm:items-center justify-between gap-0.5 sm:gap-2"
              >
                <span>Chỉ định mô hình OCR duy nhất:</span>
                <span className="text-[10px] font-normal text-muted-foreground">
                  (Không có failover tự động khi 429)
                </span>
              </label>
              <Select
                value={`${systemDefaults?.default_ocr_provider_id}:::${systemDefaults?.default_ocr_model}`}
                onValueChange={(val) => {
                  const [pId, mName] = val.split(":::");
                  if (pId && mName) {
                    onUpdateDefaults({
                      default_ocr_provider_id: pId,
                      default_ocr_model: mName,
                      default_ocr_mode: "single",
                    });
                  }
                }}
              >
                <SelectTrigger
                  id={ocrSelectId}
                  className="w-full h-9 text-xs font-mono bg-card"
                >
                  <SelectValue placeholder="Chọn mô hình OCR..." />
                </SelectTrigger>
                <SelectContent>
                  {availableOcrs.map((opt) => (
                    <SelectItem
                      key={`ocr-${opt.provider_id}-${opt.model_name}`}
                      value={`${opt.provider_id}:::${opt.model_name}`}
                    >
                      <span className="font-semibold">{opt.model_name}</span>{" "}
                      <span className="text-muted-foreground text-[11px]">
                        ({opt.provider_name})
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-semibold text-foreground">
                  Combo OCR đa tầng đang áp dụng:
                </span>
                {onCreateComboForTask && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onCreateComboForTask("ocr")}
                    className="h-6 text-[11px] text-primary hover:text-primary/80 gap-1 px-1.5"
                  >
                    <Plus className="size-3" />
                    <span>Tạo Combo</span>
                  </Button>
                )}
              </div>

              {ocrCombos.length > 0 && (
                <Select
                  value={
                    systemDefaults?.default_ocr_combo_id ||
                    ocrCombos.find((c) => c.is_default)?.id ||
                    ocrCombos[0]?.id
                  }
                  onValueChange={(comboId) =>
                    handleSelectComboForChannel("ocr", comboId)
                  }
                >
                  <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
                    <SelectValue placeholder="Chọn Combo OCR..." />
                  </SelectTrigger>
                  <SelectContent>
                    {ocrCombos.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        <span className="font-bold">{c.name}</span>{" "}
                        <span className="text-muted-foreground text-[11px]">
                          ({c.models?.length || 0} tầng • {c.strategy})
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {renderChainPipeline(activeOcrChain, "ocr")}
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5 min-w-0">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="truncate">
                Chính sách: Gemini 2.5 Flash ➔ Mistral OCR ➔ Docling
              </span>
            </span>
            {onNavigateToCombos && (
              <button
                type="button"
                onClick={() => onNavigateToCombos("ocr")}
                className="text-primary hover:text-primary/80 hover:underline flex items-center gap-1 shrink-0 self-end sm:self-auto"
              >
                <span>Xem chi tiết</span>
                <ExternalLink className="size-3" />
              </button>
            )}
          </div>
        </Card>

        {/* ========================================================= */}
        {/* 4. KÊNH HỘI THOẠI & LÝ LUẬN (LLM Chat & Reasoning) */}
        {/* ========================================================= */}
        <Card className="p-4 border-border/80 bg-card space-y-4 shadow-2xs hover:border-primary/40 transition-colors">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-2 border-b border-border/60 pb-3">
            <div className="flex items-start sm:items-center gap-2.5 min-w-0">
              <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0 mt-0.5 sm:mt-0">
                <Brain className="size-4" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                  <h4 className="text-sm font-bold text-foreground">
                    4. Chat & Lý Luận (LLM)
                  </h4>
                  <Badge
                    variant="outline"
                    className="text-[10px] font-mono border-primary/20 text-primary bg-primary/5 shrink-0"
                  >
                    Reasoning
                  </Badge>
                </div>
                <p className="text-[11px] text-muted-foreground truncate sm:whitespace-normal">
                  Phục vụ các Trợ lý AI QNU trả lời sinh viên, giải toán & tra
                  cứu.
                </p>
              </div>
            </div>

            {/* Mode Switcher */}
            <div className="flex items-center p-0.5 rounded-lg bg-muted/70 border border-border/70 shrink-0 w-full sm:w-auto">
              <button
                type="button"
                onClick={() => handleToggleChannelMode("chat", "single")}
                className={`flex-1 sm:flex-initial text-center justify-center px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                  chatMode === "single"
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Mô Hình Đơn
              </button>
              <button
                type="button"
                onClick={() => handleToggleChannelMode("chat", "combo")}
                className={`flex-1 sm:flex-initial text-center justify-center px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                  chatMode === "combo"
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Chuỗi Combo
              </button>
            </div>
          </div>

          {chatMode === "single" ? (
            <div className="space-y-2.5">
              <label
                htmlFor={chatSelectId}
                className="text-[11px] font-semibold text-foreground flex flex-col sm:flex-row sm:items-center justify-between gap-0.5 sm:gap-2"
              >
                <span>Chỉ định mô hình Chat mặc định:</span>
                <span className="text-[10px] font-normal text-muted-foreground">
                  (Áp dụng khi Trợ lý AI không chỉ định riêng)
                </span>
              </label>
              <Select
                value={`${systemDefaults?.default_chat_provider_id || "prov_ace0d9fe"}:::${systemDefaults?.default_chat_model || "gemini-2.5-flash"}`}
                onValueChange={(val) => {
                  const [pId, mName] = val.split(":::");
                  if (pId && mName) {
                    onUpdateDefaults({
                      default_chat_provider_id: pId,
                      default_chat_model: mName,
                      default_chat_mode: "single",
                    });
                  }
                }}
              >
                <SelectTrigger
                  id={chatSelectId}
                  className="w-full h-9 text-xs font-mono bg-card"
                >
                  <SelectValue placeholder="Chọn mô hình Chat..." />
                </SelectTrigger>
                <SelectContent>
                  {availableChatModels.map((opt) => (
                    <SelectItem
                      key={`chat-${opt.provider_id}-${opt.model_name}`}
                      value={`${opt.provider_id}:::${opt.model_name}`}
                    >
                      <span className="font-semibold">{opt.model_name}</span>{" "}
                      <span className="text-muted-foreground text-[11px]">
                        ({opt.provider_name})
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-semibold text-foreground">
                  Combo Chat dự phòng đang áp dụng:
                </span>
                {onCreateComboForTask && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onCreateComboForTask("chat")}
                    className="h-6 text-[11px] text-primary hover:text-primary/80 gap-1 px-1.5"
                  >
                    <Plus className="size-3" />
                    <span>Tạo Combo</span>
                  </Button>
                )}
              </div>

              {chatCombos.length > 0 && (
                <Select
                  value={
                    systemDefaults?.default_chat_combo_id ||
                    chatCombos.find((c) => c.is_default)?.id ||
                    chatCombos[0]?.id
                  }
                  onValueChange={(comboId) =>
                    handleSelectComboForChannel("chat", comboId)
                  }
                >
                  <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
                    <SelectValue placeholder="Chọn Combo Chat..." />
                  </SelectTrigger>
                  <SelectContent>
                    {chatCombos.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        <span className="font-bold">{c.name}</span>{" "}
                        <span className="text-muted-foreground text-[11px]">
                          ({c.models?.length || 0} tầng • {c.strategy})
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {renderChainPipeline(activeChatChain, "chat")}
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5 min-w-0">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="truncate">
                Chính sách: Gemini 2.5 ➔ GPT-4o-mini ➔ Local Qwen 2.5
              </span>
            </span>
            {onNavigateToCombos && (
              <button
                type="button"
                onClick={() => onNavigateToCombos("chat")}
                className="text-primary hover:text-primary/80 hover:underline flex items-center gap-1 shrink-0 self-end sm:self-auto"
              >
                <span>Xem chi tiết</span>
                <ExternalLink className="size-3" />
              </button>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
