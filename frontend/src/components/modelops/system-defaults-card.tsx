import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CheckCircle2,
  Cpu,
  Layers,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  Zap,
} from "lucide-react";
import type React from "react";
import { useId, useState } from "react";
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
import { Switch } from "../../components/ui/switch";
import type { OCRComboItem, SystemModelDefaults } from "../../types/modelops";

export const DEFAULT_QNU_OCR_COMBO_CHAIN: OCRComboItem[] = [
  {
    provider_id: "prov_gemini",
    provider_name: "Google Gemini Cloud",
    model_name: "gemini-2.5-flash",
    is_active: true,
    description: "Bước 1 (Chính): Gemini 2.5 Flash tốc độ cao, nhận diện bảng và chữ viết tay",
  },
  {
    provider_id: "prov_gemini_lite",
    provider_name: "Google Gemini Cloud",
    model_name: "gemini-2.5-flash-lite",
    is_active: true,
    description: "Bước 2 (Dự phòng 1): Gemini Flash-Lite chi phí thấp khi Step 1 chạm hạn mức",
  },
  {
    provider_id: "prov_mistral",
    provider_name: "Mistral Cloud",
    model_name: "mistral-ocr-2503",
    is_active: true,
    description: "Bước 3 (Dự phòng 2): Mistral OCR Cloud Vision xử lý scan phức tạp & con dấu đỏ",
  },
  {
    provider_id: "prov_docling",
    provider_name: "Local Edge Engine",
    model_name: "docling-tableformer",
    is_active: true,
    description: "Bước 4 (Dự phòng 3): IBM Docling TableFormer bóc tách ma trận bảng biểu cục bộ",
  },
  {
    provider_id: "prov_easyocr",
    provider_name: "Local Edge Engine",
    model_name: "easyocr-vie",
    is_active: true,
    description: "Bước 5 (Cứu sinh cuối cùng): EasyOCR CPU/CUDA cục bộ bảo đảm 0 gián đoạn",
  },
];

export interface SystemDefaultsCardProps {
  systemDefaults?: SystemModelDefaults;
  availableEmbeddings: Array<{ provider_id: string; provider_name: string; model_name: string }>;
  availableRerankers: Array<{ provider_id: string; provider_name: string; model_name: string }>;
  availableOcrs: Array<{ provider_id: string; provider_name: string; model_name: string }>;
  isLoading?: boolean;
  onUpdateDefaults: (payload: Partial<SystemModelDefaults>) => void;
}

export const SystemDefaultsCard: React.FC<SystemDefaultsCardProps> = ({
  systemDefaults,
  availableEmbeddings,
  availableRerankers,
  availableOcrs,
  isLoading,
  onUpdateDefaults,
}) => {
  const currentMode = systemDefaults?.default_ocr_mode || "combo";
  const rawChain = systemDefaults?.ocr_combo_chain;
  const comboChain: OCRComboItem[] =
    rawChain && rawChain.length > 0 ? rawChain : DEFAULT_QNU_OCR_COMBO_CHAIN;

  const [selectedNewOcr, setSelectedNewOcr] = useState<string>("");
  const embeddingSelectId = useId();
  const rerankerSelectId = useId();
  const singleOcrSelectId = useId();

  const handleToggleMode = (mode: "combo" | "single") => {
    onUpdateDefaults({
      default_ocr_mode: mode,
    });
  };

  const handleMoveUp = (index: number) => {
    if (index <= 0) return;
    const next = [...comboChain];
    const temp = next[index];
    next[index] = next[index - 1];
    next[index - 1] = temp;
    onUpdateDefaults({
      ocr_combo_chain: next,
      default_ocr_mode: currentMode,
    });
  };

  const handleMoveDown = (index: number) => {
    if (index >= comboChain.length - 1) return;
    const next = [...comboChain];
    const temp = next[index];
    next[index] = next[index + 1];
    next[index + 1] = temp;
    onUpdateDefaults({
      ocr_combo_chain: next,
      default_ocr_mode: currentMode,
    });
  };

  const handleToggleActive = (index: number) => {
    const next = comboChain.map((item, idx) =>
      idx === index ? { ...item, is_active: !(item.is_active ?? true) } : item
    );
    onUpdateDefaults({
      ocr_combo_chain: next,
      default_ocr_mode: currentMode,
    });
  };

  const handleRemoveStep = (index: number) => {
    const next = comboChain.filter((_, idx) => idx !== index);
    onUpdateDefaults({
      ocr_combo_chain: next,
      default_ocr_mode: currentMode,
    });
  };

  const handleAddStep = () => {
    if (!selectedNewOcr) return;
    const [pId, mName] = selectedNewOcr.split(":::");
    if (!pId || !mName) return;

    const opt = availableOcrs.find((o) => o.provider_id === pId && o.model_name === mName);
    const newItem: OCRComboItem = {
      provider_id: pId,
      provider_name: opt?.provider_name || pId,
      model_name: mName,
      is_active: true,
      description: `Mô hình dự phòng ${mName} (${opt?.provider_name || pId})`,
    };

    const next = [...comboChain, newItem];
    onUpdateDefaults({
      ocr_combo_chain: next,
      default_ocr_mode: currentMode,
    });
    setSelectedNewOcr("");
  };

  const handleResetStandardChain = () => {
    onUpdateDefaults({
      ocr_combo_chain: DEFAULT_QNU_OCR_COMBO_CHAIN,
      default_ocr_mode: "combo",
    });
  };

  const activeStepsCount = comboChain.filter((c) => c.is_active ?? true).length;

  return (
    <Card className="p-4 border-primary/20 bg-gradient-to-r from-card via-card to-primary/5 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-primary/10 text-primary">
            <Sparkles className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-foreground">
                Mô Hình Mặc Định Hệ Thống (Active System Defaults)
              </h3>
              <Badge
                variant="outline"
                className="text-[10px] font-mono text-primary border-primary/30"
              >
                Kho Tri Thức & RAG
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Áp dụng xuyên suốt khi nạp tài liệu vào Kho Tri Thức (Embedding), bóc tách văn bản
              (OCR Dự Phòng) và truy xuất Trợ lý AI (Reranker).
            </p>
          </div>
        </div>
        {isLoading && <RefreshCw className="size-3.5 animate-spin text-primary shrink-0" />}
      </div>

      {/* 3 Core Defaults Columns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* 1. Default Embedding */}
        <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Cpu className="size-3.5 text-primary" />
              <span>Embedding (Kho Tri Thức)</span>
            </span>
            <Badge variant="secondary" className="text-[10px] font-mono">
              1024-dim
            </Badge>
          </div>
          <Select
            value={`${systemDefaults?.default_embedding_provider_id}:::${systemDefaults?.default_embedding_model}`}
            onValueChange={(val) => {
              const [pId, mName] = val.split(":::");
              if (pId && mName) {
                onUpdateDefaults({
                  default_embedding_provider_id: pId,
                  default_embedding_model: mName,
                });
              }
            }}
          >
            <SelectTrigger id={embeddingSelectId} className="w-full h-8 text-xs font-mono bg-card">
              <SelectValue placeholder="Chọn mô hình Embedding mặc định" />
            </SelectTrigger>
            <SelectContent>
              {availableEmbeddings.map((opt) => (
                <SelectItem
                  key={`${opt.provider_id}:::${opt.model_name}`}
                  value={`${opt.provider_id}:::${opt.model_name}`}
                >
                  <span className="font-semibold">{opt.model_name}</span>{" "}
                  <span className="text-muted-foreground text-[11px]">({opt.provider_name})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[10px] text-muted-foreground">
            {systemDefaults?.default_embedding_provider_id === "prov_cloudflare"
              ? "Đang dùng Cloudflare Edge GPU (~1.0s / 16 chunks)"
              : "Đang dùng SentenceTransformers CPU Cục Bộ"}
          </p>
        </div>

        {/* 2. Default Reranker */}
        <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Zap className="size-3.5 text-amber-500" />
              <span>Reranker (Truy Xuất RAG)</span>
            </span>
            <Badge variant="secondary" className="text-[10px] font-mono">
              Cross-Encoder
            </Badge>
          </div>
          <Select
            value={`${systemDefaults?.default_reranker_provider_id}:::${systemDefaults?.default_reranker_model}`}
            onValueChange={(val) => {
              const [pId, mName] = val.split(":::");
              if (pId && mName) {
                onUpdateDefaults({
                  default_reranker_provider_id: pId,
                  default_reranker_model: mName,
                });
              }
            }}
          >
            <SelectTrigger id={rerankerSelectId} className="w-full h-8 text-xs font-mono bg-card">
              <SelectValue placeholder="Chọn mô hình Reranker mặc định" />
            </SelectTrigger>
            <SelectContent>
              {availableRerankers.map((opt) => (
                <SelectItem
                  key={`${opt.provider_id}:::${opt.model_name}`}
                  value={`${opt.provider_id}:::${opt.model_name}`}
                >
                  <span className="font-semibold">{opt.model_name}</span>{" "}
                  <span className="text-muted-foreground text-[11px]">({opt.provider_name})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[10px] text-muted-foreground">
            {systemDefaults?.default_reranker_provider_id === "prov_cloudflare"
              ? "Đang dùng Cloudflare BGE-Reranker-Base (~1.2s)"
              : "Đang dùng thuật toán RRF Fused Scoring nội bộ"}
          </p>
        </div>

        {/* 3. OCR Policy & Mode */}
        <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <ShieldCheck className="size-3.5 text-sky-500" />
              <span>OCR Mặc Định Hệ Thống</span>
            </span>
            <Badge
              variant={currentMode === "combo" ? "default" : "secondary"}
              className="text-[10px] font-mono"
            >
              {currentMode === "combo" ? "Combo Đa Tầng" : "Mô Hình Đơn"}
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-1.5 p-0.5 rounded-md bg-muted/60 border border-border/60">
            <button
              type="button"
              onClick={() => handleToggleMode("combo")}
              className={`py-1 text-[11px] font-medium rounded transition-colors text-center ${
                currentMode === "combo"
                  ? "bg-card text-primary font-bold shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Combo Dự Phòng
            </button>
            <button
              type="button"
              onClick={() => handleToggleMode("single")}
              className={`py-1 text-[11px] font-medium rounded transition-colors text-center ${
                currentMode === "single"
                  ? "bg-card text-primary font-bold shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Mô Hình Đơn
            </button>
          </div>

          {currentMode === "single" ? (
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
                id={singleOcrSelectId}
                className="w-full h-8 text-xs font-mono bg-card"
              >
                <SelectValue placeholder="Chọn mô hình OCR đơn lẻ" />
              </SelectTrigger>
              <SelectContent>
                {availableOcrs.map((opt) => (
                  <SelectItem
                    key={`${opt.provider_id}:::${opt.model_name}`}
                    value={`${opt.provider_id}:::${opt.model_name}`}
                  >
                    <span className="font-semibold">{opt.model_name}</span>{" "}
                    <span className="text-muted-foreground text-[11px]">({opt.provider_name})</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <div className="flex items-center justify-between text-[11px] bg-primary/10 px-2.5 py-1.5 rounded border border-primary/20">
              <span className="text-primary font-medium flex items-center gap-1">
                <CheckCircle2 className="size-3" />
                <span>{activeStepsCount} mô hình đang kích hoạt</span>
              </span>
              <span className="text-[10px] text-muted-foreground">Failover tự động</span>
            </div>
          )}

          <p className="text-[10px] text-muted-foreground">
            {currentMode === "combo"
              ? "Tự động nhảy sang model tiếp theo khi model trước hết Quota (429) hoặc lỗi"
              : "Cố định 1 model duy nhất (có nguy cơ đứt quãng khi hết hạn ngạch API)"}
          </p>
        </div>
      </div>

      {/* OCR Combo Chain Detail Panel */}
      <div className="p-3.5 rounded-lg bg-background/80 border border-primary/20 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-2">
          <div className="flex items-center gap-2">
            <div className="p-1 rounded bg-primary/15 text-primary">
              <Layers className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-bold text-foreground">
                  Cấu Hình Chuỗi Combo OCR Dự Phòng Đa Tầng (Sequential Failover Chain)
                </h4>
                {currentMode === "combo" && (
                  <Badge
                    variant="outline"
                    className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 gap-1"
                  >
                    <ShieldCheck className="size-3" />
                    <span>Đang làm OCR Mặc Định</span>
                  </Badge>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground">
                Thứ tự thực thi ưu tiên từ trên xuống dưới. Nếu model phía trước hết Quota hoặc gặp
                sự cố mạng, hệ thống tự động gọi model tiếp theo.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center">
            {currentMode !== "combo" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleToggleMode("combo")}
                className="h-7 text-xs gap-1 border-primary/40 text-primary hover:bg-primary/10"
              >
                <CheckCircle2 className="size-3" />
                <span>Gắn Combo Làm Mặc Định</span>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetStandardChain}
              className="h-7 text-xs text-muted-foreground hover:text-foreground gap-1"
              title="Khôi phục 5 bước tiêu chuẩn của Trường Đại học Quy Nhơn"
            >
              <RotateCcw className="size-3" />
              <span>Khôi phục Chuỗi Chuẩn</span>
            </Button>
          </div>
        </div>

        {/* Visual Pipeline Flow */}
        <div className="overflow-x-auto pb-1">
          <div className="flex items-center gap-1.5 min-w-max py-1 px-1">
            {comboChain.map((item, idx) => {
              const isActive = item.is_active ?? true;
              return (
                <div
                  key={`visual-step-${item.provider_id}-${item.model_name}-${idx}`}
                  className="flex items-center gap-1.5"
                >
                  <div
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs transition-colors ${
                      isActive
                        ? "bg-card border-border shadow-xs text-foreground"
                        : "bg-muted/40 border-border/50 text-muted-foreground opacity-60"
                    }`}
                  >
                    <span
                      className={`size-4 rounded-full text-[10px] flex items-center justify-center font-bold font-mono ${
                        idx === 0 && isActive
                          ? "bg-primary text-primary-foreground"
                          : isActive
                            ? "bg-muted text-foreground"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {idx + 1}
                    </span>
                    <span className="font-semibold text-[11px]">{item.model_name}</span>
                    <span className="text-[10px] text-muted-foreground">
                      ({item.provider_name})
                    </span>
                  </div>
                  {idx < comboChain.length - 1 && (
                    <ArrowRight className="size-3 text-muted-foreground shrink-0" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Steps List Table / Cards */}
        <div className="space-y-1.5">
          {comboChain.map((item, idx) => {
            const isActive = item.is_active ?? true;
            return (
              <div
                key={`row-${item.provider_id}-${item.model_name}-${idx}`}
                className={`flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 rounded-md border transition-all ${
                  isActive
                    ? "bg-card border-border/80 shadow-xs"
                    : "bg-muted/30 border-border/40 opacity-70"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`size-6 rounded-md flex items-center justify-center text-xs font-bold font-mono shrink-0 ${
                      idx === 0 && isActive
                        ? "bg-primary/20 text-primary border border-primary/30"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    #{idx + 1}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-foreground font-mono">
                        {item.model_name}
                      </span>
                      <Badge variant="secondary" className="text-[10px] py-0">
                        {item.provider_name}
                      </Badge>
                      {idx === 0 && (
                        <Badge
                          variant="outline"
                          className="text-[9px] bg-primary/10 text-primary border-primary/20"
                        >
                          Chính (Primary)
                        </Badge>
                      )}
                      {idx > 0 && (
                        <Badge
                          variant="outline"
                          className="text-[9px] text-muted-foreground border-border"
                        >
                          Dự phòng #{idx}
                        </Badge>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-[11px] text-muted-foreground truncate">
                        {item.description}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                  <div className="flex items-center gap-1.5 mr-2">
                    <span className="text-[11px] text-muted-foreground">
                      {isActive ? "Bật" : "Tắt"}
                    </span>
                    <Switch
                      checked={isActive}
                      onCheckedChange={() => handleToggleActive(idx)}
                      aria-label={`Bật hoặc tắt bước ${idx + 1}`}
                    />
                  </div>

                  <div className="flex items-center border border-border rounded-md bg-background/60 p-0.5">
                    <button
                      type="button"
                      disabled={idx === 0}
                      onClick={() => handleMoveUp(idx)}
                      className="p-1 rounded text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:pointer-events-none transition-colors"
                      title="Di chuyển lên trên (Tăng mức độ ưu tiên)"
                    >
                      <ArrowUp className="size-3.5" />
                    </button>
                    <button
                      type="button"
                      disabled={idx === comboChain.length - 1}
                      onClick={() => handleMoveDown(idx)}
                      className="p-1 rounded text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:pointer-events-none transition-colors"
                      title="Di chuyển xuống dưới (Giảm mức độ ưu tiên)"
                    >
                      <ArrowDown className="size-3.5" />
                    </button>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveStep(idx)}
                    className="size-7 p-0 text-destructive/80 hover:text-destructive hover:bg-destructive/10"
                    title="Xóa mô hình này khỏi Combo"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Add New Model To Combo Form */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pt-1 border-t border-border/60">
          <div className="grow">
            <Select value={selectedNewOcr} onValueChange={setSelectedNewOcr}>
              <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
                <SelectValue placeholder="Chọn mô hình OCR có sẵn để bổ sung vào chuỗi..." />
              </SelectTrigger>
              <SelectContent>
                {availableOcrs.map((opt) => (
                  <SelectItem
                    key={`available-opt-${opt.provider_id}:::${opt.model_name}`}
                    value={`${opt.provider_id}:::${opt.model_name}`}
                  >
                    <span className="font-semibold">{opt.model_name}</span>{" "}
                    <span className="text-muted-foreground text-[11px]">({opt.provider_name})</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            size="sm"
            disabled={!selectedNewOcr}
            onClick={handleAddStep}
            className="h-8 text-xs gap-1.5 shrink-0"
          >
            <Plus className="size-3.5" />
            <span>Thêm Vào Chuỗi Dự Phòng</span>
          </Button>
        </div>

        {/* Safety & Quota Alert Footer */}
        <div className="flex items-start gap-2 p-2 rounded-md bg-muted/40 border border-border/60 text-[11px] text-muted-foreground">
          <ShieldAlert className="size-3.5 text-amber-500 shrink-0 mt-0.5" />
          <p>
            Chính sách <span className="font-semibold text-foreground">Zero Quota Failure</span>:
            Khi OCR gặp mã lỗi{" "}
            <code className="font-mono text-primary">429 (Rate Limit / Quota Exceeded)</code> hoặc
            timeout, hệ thống sẽ tự động bypass và kích hoạt tức thì bước tiếp theo trong chuỗi mà
            không báo lỗi ra màn hình người dùng.
          </p>
        </div>
      </div>
    </Card>
  );
};
