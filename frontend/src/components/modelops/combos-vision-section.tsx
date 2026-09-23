import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Brain,
  Check,
  CheckCircle2,
  Cpu,
  Eye,
  GitMerge,
  Info,
  Layers,
  Pencil,
  Plus,
  Search,
  ShieldCheck,
  Shuffle,
  Trash2,
  Volume2,
  Zap,
} from "lucide-react";
import type React from "react";
import { useId, useMemo, useState } from "react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Switch } from "../../components/ui/switch";
import type {
  ModelComboItem,
  ModelOption,
  OCRComboItem,
  SystemModelDefaults,
  VisionAdapterConfig,
} from "../../types/modelops";
import { getModelCapabilities } from "./modelops-helpers";

export interface CombosVisionSectionProps {
  systemDefaults?: SystemModelDefaults;
  availableOcrs: ModelOption[];
  allAvailableModels?: ModelOption[];
  onUpdateDefaults: (payload: Partial<SystemModelDefaults>) => void;
}

export const CombosVisionSection: React.FC<CombosVisionSectionProps> = ({
  systemDefaults,
  availableOcrs,
  allAvailableModels = [],
  onUpdateDefaults,
}) => {
  // Lấy danh sách combos từ defaults hoặc khởi tạo mẫu
  const rawCombos = systemDefaults?.model_combos;
  const combos: ModelComboItem[] = useMemo(() => {
    if (rawCombos && rawCombos.length > 0) return rawCombos;
    // Khởi tạo mặc định nếu chưa có
    return [
      {
        id: "combo_qnu_ocr_master",
        name: "qnu-ocr-master",
        strategy: "fallback",
        is_default: true,
        description: "Combo OCR đa tầng mặc định ĐH Quy Nhơn (Tự động failover khi hết Quota 429)",
        models:
          systemDefaults?.ocr_combo_chain && systemDefaults.ocr_combo_chain.length > 0
            ? systemDefaults.ocr_combo_chain
            : [
                {
                  provider_id: "prov_gemini",
                  provider_name: "Google Gemini Cloud",
                  model_name: "gemini-2.5-flash",
                  is_active: true,
                  description: "Bước 1 (Chính): Gemini 2.5 Flash tốc độ cao, đa phương thức",
                },
                {
                  provider_id: "prov_gemini_lite",
                  provider_name: "Google Gemini Cloud",
                  model_name: "gemini-2.5-flash-lite",
                  is_active: true,
                  description: "Bước 2 (Dự phòng 1): Gemini Flash-Lite khi Step 1 chạm Quota",
                },
                {
                  provider_id: "prov_mistral",
                  provider_name: "Mistral Cloud",
                  model_name: "mistral-ocr-2503",
                  is_active: true,
                  description:
                    "Bước 3 (Dự phòng 2): Mistral OCR bóc tách scan tiếng Việt & con dấu",
                },
                {
                  provider_id: "prov_docling",
                  provider_name: "Local Edge Engine",
                  model_name: "docling-tableformer",
                  is_active: true,
                  description:
                    "Bước 4 (Dự phòng 3): IBM Docling TableFormer bóc tách ma trận bảng biểu",
                },
                {
                  provider_id: "prov_easyocr",
                  provider_name: "Local Edge Engine",
                  model_name: "easyocr-vie",
                  is_active: true,
                  description:
                    "Bước 5 (Cứu sinh cuối cùng): EasyOCR CPU/CUDA cục bộ bảo đảm 0 gián đoạn",
                },
              ],
      },
    ];
  }, [rawCombos, systemDefaults?.ocr_combo_chain]);

  // Cấu hình Vision Adapter
  const visionAdapter: VisionAdapterConfig = useMemo(() => {
    return (
      systemDefaults?.vision_adapter || {
        enabled: true,
        strategy: "fallback",
        models: combos.find((c) => c.is_default)?.models || combos[0]?.models || [],
      }
    );
  }, [systemDefaults?.vision_adapter, combos]);

  // State quản lý Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isAddModelModalOpen, setIsAddModelModalOpen] = useState(false);
  const [editingCombo, setEditingCombo] = useState<ModelComboItem | null>(null);

  // Form state cho Combo đang tạo / sửa
  const [comboName, setComboName] = useState("");
  const [comboStrategy, setComboStrategy] = useState<"fallback" | "round_robin" | "fusion">(
    "fallback"
  );
  const [comboDescription, setComboDescription] = useState("");
  const [comboModels, setComboModels] = useState<OCRComboItem[]>([]);
  const [comboIsDefault, setComboIsDefault] = useState(false);

  // Search state cho Add Model modal
  const [modelSearchQuery, setModelSearchQuery] = useState("");
  const [targetPool, setTargetPool] = useState<"combo" | "vision">("combo");

  // Audio adapter state giả lập UI
  const [audioEnabled, setAudioEnabled] = useState(false);

  const comboNameId = useId();
  const comboStrategyId = useId();

  // Danh sách model gộp (kết hợp availableOcrs và allAvailableModels)
  const candidateModelsPool: ModelOption[] = useMemo(() => {
    const map = new Map<string, ModelOption>();
    for (const opt of availableOcrs) {
      map.set(`${opt.provider_id}:::${opt.model_name}`, opt);
    }
    for (const opt of allAvailableModels) {
      const key = `${opt.provider_id}:::${opt.model_name}`;
      if (!map.has(key)) {
        map.set(key, opt);
      }
    }
    return Array.from(map.values());
  }, [availableOcrs, allAvailableModels]);

  // Lọc model theo search query
  const filteredModels = useMemo(() => {
    const q = modelSearchQuery.trim().toLowerCase();
    if (!q) return candidateModelsPool;
    return candidateModelsPool.filter(
      (m) =>
        m.model_name.toLowerCase().includes(q) ||
        m.provider_name.toLowerCase().includes(q) ||
        (m.description || "").toLowerCase().includes(q)
    );
  }, [candidateModelsPool, modelSearchQuery]);

  // Nhóm model theo Provider
  const groupedModelsByProvider = useMemo(() => {
    const groups: Record<string, { provider_name: string; items: ModelOption[] }> = {};
    for (const m of filteredModels) {
      if (!groups[m.provider_id]) {
        groups[m.provider_id] = {
          provider_name: m.provider_name,
          items: [],
        };
      }
      groups[m.provider_id].items.push(m);
    }
    return Object.entries(groups);
  }, [filteredModels]);

  // Mở modal tạo combo mới
  const handleOpenCreateModal = () => {
    setEditingCombo(null);
    setComboName(`combo-${Date.now().toString().slice(-4)}`);
    setComboStrategy("fallback");
    setComboDescription("");
    setComboModels([]);
    setComboIsDefault(combos.length === 0);
    setIsCreateModalOpen(true);
  };

  // Mở modal sửa combo
  const handleOpenEditModal = (combo: ModelComboItem) => {
    setEditingCombo(combo);
    setComboName(combo.name);
    setComboStrategy(combo.strategy);
    setComboDescription(combo.description || "");
    setComboModels([...combo.models]);
    setComboIsDefault(Boolean(combo.is_default));
    setIsCreateModalOpen(true);
  };

  // Lưu combo
  const handleSaveCombo = () => {
    if (!comboName.trim()) return;

    const safeName = comboName.trim().replace(/[^a-zA-Z0-9_.-]/g, "_");
    const newCombo: ModelComboItem = {
      id: editingCombo?.id || `combo_${Date.now()}`,
      name: safeName,
      strategy: comboStrategy,
      description: comboDescription.trim() || undefined,
      models: comboModels,
      is_default: comboIsDefault,
    };

    let updatedCombos: ModelComboItem[];
    if (editingCombo) {
      updatedCombos = combos.map((c) =>
        c.id === editingCombo.id ? newCombo : comboIsDefault ? { ...c, is_default: false } : c
      );
    } else {
      updatedCombos = comboIsDefault
        ? [...combos.map((c) => ({ ...c, is_default: false })), newCombo]
        : [...combos, newCombo];
    }

    onUpdateDefaults({
      model_combos: updatedCombos,
      ...(comboIsDefault && comboModels.length > 0
        ? {
            ocr_combo_chain: comboModels,
            default_ocr_mode: "combo",
            default_ocr_provider_id: comboModels[0].provider_id,
            default_ocr_model: comboModels[0].model_name,
          }
        : {}),
    });

    setIsCreateModalOpen(false);
  };

  // Xóa combo
  const handleDeleteCombo = (comboId: string) => {
    const updated = combos.filter((c) => c.id !== comboId);
    onUpdateDefaults({
      model_combos: updated,
    });
  };

  // Gắn combo làm mặc định
  const handleSetAsDefaultCombo = (combo: ModelComboItem) => {
    const updated = combos.map((c) => ({
      ...c,
      is_default: c.id === combo.id,
    }));
    onUpdateDefaults({
      model_combos: updated,
      ocr_combo_chain: combo.models,
      default_ocr_mode: "combo",
      ...(combo.models.length > 0
        ? {
            default_ocr_provider_id: combo.models[0].provider_id,
            default_ocr_model: combo.models[0].model_name,
          }
        : {}),
    });
  };

  // Toggle model selection trong Modal Add Model
  const handleToggleModelSelection = (opt: ModelOption) => {
    if (targetPool === "combo") {
      const existsIndex = comboModels.findIndex(
        (m) => m.provider_id === opt.provider_id && m.model_name === opt.model_name
      );
      if (existsIndex >= 0) {
        setComboModels((prev) => prev.filter((_, idx) => idx !== existsIndex));
      } else {
        const newItem: OCRComboItem = {
          provider_id: opt.provider_id,
          provider_name: opt.provider_name,
          model_name: opt.model_name,
          is_active: true,
          description: `Mô hình ${opt.model_name} (${opt.provider_name})`,
        };
        setComboModels((prev) => [...prev, newItem]);
      }
    } else {
      // Vision adapter pool
      const currentModels = visionAdapter.models || [];
      const existsIndex = currentModels.findIndex(
        (m) => m.provider_id === opt.provider_id && m.model_name === opt.model_name
      );
      let nextModels: OCRComboItem[];
      if (existsIndex >= 0) {
        nextModels = currentModels.filter((_, idx) => idx !== existsIndex);
      } else {
        nextModels = [
          ...currentModels,
          {
            provider_id: opt.provider_id,
            provider_name: opt.provider_name,
            model_name: opt.model_name,
            is_active: true,
          },
        ];
      }
      onUpdateDefaults({
        vision_adapter: {
          ...visionAdapter,
          models: nextModels,
        },
      });
    }
  };

  // Kiểm tra model đã được chọn hay chưa
  const isModelSelected = (opt: ModelOption): boolean => {
    const pool = targetPool === "combo" ? comboModels : visionAdapter.models;
    return (pool || []).some(
      (m) => m.provider_id === opt.provider_id && m.model_name === opt.model_name
    );
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Strategy Explainer Card */}
      <Card className="p-4 border-primary/25 bg-gradient-to-r from-card via-card to-primary/5 space-y-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Layers className="size-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-foreground">
                  Combos (Tổ Hợp Mô Hình & Chuỗi Dự Phòng)
                </h3>
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono text-primary border-primary/30"
                >
                  Model Combos with Fallback
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Gom nhóm nhiều mô hình dưới một tên gọi duy nhất, lựa chọn chiến lược điều phối và
                tự động nhảy sang mô hình dự phòng khi gặp sự cố Quota hoặc mạng.
              </p>
            </div>
          </div>

          <Button
            onClick={handleOpenCreateModal}
            size="sm"
            className="gap-1.5 self-start sm:self-center"
          >
            <Plus className="size-4" />
            <span>Tạo Combo Mới</span>
          </Button>
        </div>

        {/* Strategy Explainer Grid */}
        <div className="text-xs text-muted-foreground bg-background/60 p-3 rounded-lg border border-border/80 space-y-2">
          <p className="font-semibold text-foreground text-[11px] uppercase tracking-wider">
            Các chiến lược điều phối mô hình (Strategies):
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px]">
            <div className="p-2 rounded-md bg-card border border-border/60 space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-foreground text-sky-600 dark:text-sky-400">
                <ShieldCheck className="size-3.5" />
                <span>Fallback (Tuần Tự Dự Phòng)</span>
              </div>
              <p className="leading-relaxed">
                Gọi tuần tự từng mô hình theo thứ tự ưu tiên. Nếu mô hình chạm hạn ngạch Quota (429)
                hoặc lỗi mạng, tự động chuyển sang mô hình tiếp theo.
              </p>
            </div>

            <div className="p-2 rounded-md bg-card border border-border/60 space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-foreground text-amber-600 dark:text-amber-400">
                <Shuffle className="size-3.5" />
                <span>Round Robin (Xoay Vòng)</span>
              </div>
              <p className="leading-relaxed">
                Xoay vòng lần lượt các mô hình qua từng lượt truy vấn để phân bổ đều tải, tránh làm
                cạn kiệt Quota của một tài khoản duy nhất.
              </p>
            </div>

            <div className="p-2 rounded-md bg-card border border-border/60 space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-foreground text-purple-600 dark:text-purple-400">
                <GitMerge className="size-3.5" />
                <span>Fusion (Truy Vấn Song Song)</span>
              </div>
              <p className="leading-relaxed">
                Gửi truy vấn đồng thời tới các mô hình trong combo, sau đó tổng hợp câu trả lời đạt
                chất lượng cao nhất cho người dùng.
              </p>
            </div>
          </div>
        </div>

        {/* 2. Combos List / Grid */}
        {combos.length === 0 ? (
          <div className="p-8 rounded-lg border border-dashed border-border flex flex-col items-center justify-center gap-2.5 text-center bg-background/40">
            <div className="size-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <Layers className="size-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-foreground">Chưa có combo mô hình nào</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Tạo combo mô hình với cơ chế dự phòng fallback tự động để bảo vệ hệ thống khỏi đứt
                đoạn.
              </p>
            </div>
            <Button
              onClick={handleOpenCreateModal}
              size="sm"
              variant="outline"
              className="gap-1.5 mt-1"
            >
              <Plus className="size-3.5" />
              <span>Tạo Combo</span>
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2.5">
            {combos.map((combo) => (
              <div
                key={combo.id}
                className={`p-3 rounded-lg border transition-all ${
                  combo.is_default
                    ? "bg-card border-primary/40 shadow-xs ring-1 ring-primary/20"
                    : "bg-card/70 border-border/80 hover:border-border"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/40 pb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold font-mono text-foreground">
                      {combo.name}
                    </span>
                    <Badge
                      variant="outline"
                      className={`text-[10px] capitalize font-mono ${
                        combo.strategy === "fallback"
                          ? "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30"
                          : combo.strategy === "round_robin"
                            ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                            : "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30"
                      }`}
                    >
                      {combo.strategy}
                    </Badge>
                    {combo.is_default && (
                      <Badge
                        variant="default"
                        className="text-[10px] bg-emerald-600 text-white dark:bg-emerald-500 font-semibold gap-1"
                      >
                        <CheckCircle2 className="size-3" />
                        <span>Mặc Định Kho Tri Thức</span>
                      </Badge>
                    )}
                    <span className="text-[11px] text-muted-foreground font-mono">
                      ({combo.models.length} mô hình)
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 self-end sm:self-center">
                    {!combo.is_default && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSetAsDefaultCombo(combo)}
                        className="h-7 text-[11px] gap-1 text-primary hover:bg-primary/10"
                        title="Gắn combo này làm mặc định cho Kho Tri Thức & OCR"
                      >
                        <CheckCircle2 className="size-3.5" />
                        <span>Gắn Mặc Định</span>
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenEditModal(combo)}
                      className="size-7 p-0 text-muted-foreground hover:text-foreground"
                      title="Chỉnh sửa combo"
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    {combos.length > 1 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteCombo(combo.id)}
                        className="size-7 p-0 text-destructive/80 hover:text-destructive hover:bg-destructive/10"
                        title="Xóa combo này"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    )}
                  </div>
                </div>

                {/* Models Pills Flow inside Combo */}
                <div className="pt-2">
                  {combo.models.length === 0 ? (
                    <p className="text-[11px] text-muted-foreground italic">
                      Chưa có mô hình nào trong combo này. Bấm &quot;Chỉnh sửa&quot; để bổ sung mô
                      hình.
                    </p>
                  ) : (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {combo.models.map((item, idx) => {
                        const caps = getModelCapabilities(item.model_name);
                        return (
                          <div
                            key={`${combo.id}-${item.provider_id}-${item.model_name}-${idx}`}
                            className="flex items-center gap-1.5"
                          >
                            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-background border border-border text-xs font-mono">
                              <span className="text-[10px] text-muted-foreground font-bold">
                                #{idx + 1}
                              </span>
                              <span className="font-semibold text-[11px] text-foreground">
                                {item.model_name}
                              </span>
                              <span className="text-[10px] text-muted-foreground">
                                ({item.provider_name})
                              </span>
                              {caps.isOcr && (
                                <span title="Hỗ trợ OCR / Vision">
                                  <Eye className="size-3 text-sky-500" />
                                </span>
                              )}
                              {caps.hasReasoning && (
                                <span title="Hỗ trợ Reasoning">
                                  <Brain className="size-3 text-purple-500" />
                                </span>
                              )}
                            </div>
                            {idx < combo.models.length - 1 && (
                              <ArrowRight className="size-3 text-muted-foreground shrink-0" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 3. Vision Adapter Section (Lấy cảm hứng từ 9Router) */}
      <Card className="p-4 border-border space-y-3.5">
        <div>
          <div className="flex items-center gap-2">
            <Eye className="size-4 text-sky-500" />
            <h3 className="text-sm font-bold text-foreground">Vision Adapter</h3>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Mô hình chính không hỗ trợ đọc ảnh hoặc tài liệu scan? Hệ thống tự động chuyển tiếp sang
            pool mô hình thị giác bên dưới.
          </p>
        </div>

        <div className="space-y-2.5">
          {/* Row 1: Vision Pool */}
          <div className="p-3 rounded-lg bg-background/60 border border-border/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start sm:items-center gap-3">
              <Switch
                checked={visionAdapter.enabled}
                onCheckedChange={(val) =>
                  onUpdateDefaults({
                    vision_adapter: {
                      ...visionAdapter,
                      enabled: val,
                    },
                  })
                }
                aria-label="Bật hoặc tắt Vision Adapter"
              />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-foreground">Vision</span>
                  <span className="text-[11px] text-muted-foreground">
                    — hình ảnh (png, jpg, webp, pdf scan...)
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                  {(visionAdapter.models || []).length === 0 ? (
                    <span className="text-[11px] text-muted-foreground italic">
                      Chưa có mô hình nào trong Vision Pool
                    </span>
                  ) : (
                    visionAdapter.models.map((m, idx) => (
                      <Badge
                        key={`vision-pool-${m.provider_id}-${m.model_name}-${idx}`}
                        variant="secondary"
                        className="text-[10px] font-mono gap-1"
                      >
                        <Eye className="size-2.5 text-sky-500" />
                        <span>{m.model_name}</span>
                      </Badge>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
              <div className="flex items-center gap-1.5 border border-border rounded-md px-2 py-1 text-[11px] bg-card">
                <span className="text-muted-foreground">Chế độ:</span>
                <button
                  type="button"
                  onClick={() =>
                    onUpdateDefaults({
                      vision_adapter: {
                        ...visionAdapter,
                        strategy:
                          visionAdapter.strategy === "fallback" ? "round_robin" : "fallback",
                      },
                    })
                  }
                  className="font-bold text-primary hover:underline cursor-pointer"
                >
                  {visionAdapter.strategy === "fallback" ? "Fallback" : "Round Robin"}
                </button>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setTargetPool("vision");
                  setModelSearchQuery("");
                  setIsAddModelModalOpen(true);
                }}
                className="h-8 text-xs gap-1"
              >
                <Plus className="size-3.5" />
                <span>Thêm Model</span>
              </Button>
            </div>
          </div>

          {/* Row 2: Audio Pool */}
          <div className="p-3 rounded-lg bg-background/60 border border-border/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 opacity-80">
            <div className="flex items-start sm:items-center gap-3">
              <Switch
                checked={audioEnabled}
                onCheckedChange={setAudioEnabled}
                aria-label="Bật hoặc tắt Audio Adapter"
              />
              <div>
                <div className="flex items-center gap-2">
                  <Volume2 className="size-3.5 text-purple-500" />
                  <span className="text-xs font-bold text-foreground">Audio</span>
                  <span className="text-[11px] text-muted-foreground">
                    — âm thanh & giọng nói (mp3, wav, m4a...)
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5 italic">
                  Chưa kích hoạt audio input
                </p>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              disabled={!audioEnabled}
              className="h-8 text-xs gap-1 self-end sm:self-center"
            >
              <Plus className="size-3.5" />
              <span>Thêm Model</span>
            </Button>
          </div>
        </div>
      </Card>

      {/* 4. Dialog Tạo / Sửa Combo (Theo phong cách Ảnh 2 9Router) */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="sm:max-w-[540px]">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <Layers className="size-4 text-primary" />
              <span>{editingCombo ? "Chỉnh Sửa Combo" : "Tạo Combo Mới (Create Combo)"}</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Nhóm các mô hình theo chiến lược ưu tiên hoặc cân bằng tải.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Combo Name */}
            <div className="space-y-1.5">
              <label htmlFor={comboNameId} className="text-xs font-semibold text-foreground">
                Tên Combo (Combo Name)
              </label>
              <Input
                id={comboNameId}
                value={comboName}
                onChange={(e) => setComboName(e.target.value)}
                placeholder="my-combo"
                className="h-9 text-xs font-mono"
              />
              <p className="text-[10px] text-muted-foreground">
                Chỉ cho phép chữ cái, chữ số, dấu gạch ngang (-), gạch dưới (_) và dấu chấm (.)
              </p>
            </div>

            {/* Strategy */}
            <div className="space-y-1.5">
              <label htmlFor={comboStrategyId} className="text-xs font-semibold text-foreground">
                Chiến Lược Điều Phối (Strategy)
              </label>
              <Select
                value={comboStrategy}
                onValueChange={(val: "fallback" | "round_robin" | "fusion") =>
                  setComboStrategy(val)
                }
              >
                <SelectTrigger id={comboStrategyId} className="w-full h-9 text-xs">
                  <SelectValue placeholder="Chọn chiến lược" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fallback">
                    Fallback — Thử tuần tự theo thứ tự (Chuyển sang model tiếp khi hết Quota 429)
                  </SelectItem>
                  <SelectItem value="round_robin">
                    Round Robin — Xoay vòng mô hình (Phân bổ đều tải)
                  </SelectItem>
                  <SelectItem value="fusion">Fusion — Truy vấn song song đa mô hình</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Models list inside dialog */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-foreground block">
                Danh Sách Mô Hình (Models)
              </span>

              {comboModels.length === 0 ? (
                <div className="p-6 rounded-lg border border-dashed border-border flex flex-col items-center justify-center gap-2 text-center bg-muted/20">
                  <Layers className="size-6 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">
                    Chưa có mô hình nào được thêm
                  </span>
                </div>
              ) : (
                <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                  {comboModels.map((item, idx) => (
                    <div
                      key={`combo-edit-item-${item.provider_id}-${item.model_name}-${idx}`}
                      className="flex items-center justify-between p-2 rounded-md bg-card border border-border text-xs"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="size-5 rounded-full bg-primary/10 text-primary flex items-center justify-center font-mono font-bold text-[10px] shrink-0">
                          {idx + 1}
                        </span>
                        <div className="min-w-0 truncate">
                          <span className="font-semibold font-mono text-foreground">
                            {item.model_name}
                          </span>
                          <span className="text-[10px] text-muted-foreground ml-1.5">
                            ({item.provider_name})
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={idx === 0}
                          onClick={() => {
                            const next = [...comboModels];
                            const temp = next[idx];
                            next[idx] = next[idx - 1];
                            next[idx - 1] = temp;
                            setComboModels(next);
                          }}
                          className="size-6 p-0 text-muted-foreground hover:text-foreground"
                          title="Lên trên"
                        >
                          <ArrowUp className="size-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={idx === comboModels.length - 1}
                          onClick={() => {
                            const next = [...comboModels];
                            const temp = next[idx];
                            next[idx] = next[idx + 1];
                            next[idx + 1] = temp;
                            setComboModels(next);
                          }}
                          className="size-6 p-0 text-muted-foreground hover:text-foreground"
                          title="Xuống dưới"
                        >
                          <ArrowDown className="size-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setComboModels((prev) => prev.filter((_, i) => i !== idx))}
                          className="size-6 p-0 text-destructive/80 hover:text-destructive"
                          title="Xóa"
                        >
                          <Trash2 className="size-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Add model button (dashed outline style like 9Router) */}
              <button
                type="button"
                onClick={() => {
                  setTargetPool("combo");
                  setModelSearchQuery("");
                  setIsAddModelModalOpen(true);
                }}
                className="w-full py-2 px-3 rounded-md border border-dashed border-primary/40 hover:border-primary text-primary hover:bg-primary/5 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                <Plus className="size-3.5" />
                <span>Thêm Mô Hình (Add Model)</span>
              </button>
            </div>

            {/* Set as Default OCR Checkbox */}
            <div className="flex items-center gap-2 pt-1 border-t border-border/60">
              <input
                type="checkbox"
                id="combo-is-default-checkbox"
                checked={comboIsDefault}
                onChange={(e) => setComboIsDefault(e.target.checked)}
                className="size-4 rounded text-primary focus:ring-primary border-border"
              />
              <label
                htmlFor="combo-is-default-checkbox"
                className="text-xs text-foreground cursor-pointer select-none font-medium"
              >
                Gắn combo này làm OCR Mặc Định của Toàn Hệ Thống (Kho Tri Thức & RAG)
              </label>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" size="sm" onClick={() => setIsCreateModalOpen(false)}>
              Hủy Bỏ
            </Button>
            <Button size="sm" onClick={handleSaveCombo} disabled={!comboName.trim()}>
              {editingCombo ? "Lưu Thay Đổi" : "Tạo Combo"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 5. Dialog Thêm Mô Hình Vào Combo (Add Model to Combo Modal - Chuẩn Ảnh 3 9Router) */}
      <Dialog open={isAddModelModalOpen} onOpenChange={setIsAddModelModalOpen}>
        <DialogContent className="sm:max-w-[580px] max-h-[85vh] flex flex-col p-5">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <Layers className="size-4 text-primary" />
              <span>
                {targetPool === "combo" ? "Thêm Mô Hình Vào Combo" : "Thêm Mô Hình Vào Vision Pool"}
              </span>
            </DialogTitle>
          </DialogHeader>

          {/* Hint Banner (như ảnh 3 9Router) */}
          <div className="p-2.5 rounded-lg bg-primary/5 border border-primary/20 text-xs text-muted-foreground flex items-center gap-2">
            <Info className="size-4 text-primary shrink-0" />
            <span>
              Bấm vào mô hình để thêm, bấm lại lần nữa để gỡ bỏ. Thay đổi sẽ được cập nhật tự động.
            </span>
          </div>

          {/* Search Bar (như ảnh 3 9Router) */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 size-3.5 text-muted-foreground" />
            <Input
              value={modelSearchQuery}
              onChange={(e) => setModelSearchQuery(e.target.value)}
              placeholder="Tìm kiếm mô hình hoặc nhà cung cấp..."
              className="pl-9 h-9 text-xs"
            />
          </div>

          {/* Groups of Models (như ảnh 3 9Router) */}
          <div className="overflow-y-auto flex-1 space-y-4 pr-1 py-1">
            {groupedModelsByProvider.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-6">
                Không tìm thấy mô hình nào phù hợp với từ khóa &quot;{modelSearchQuery}&quot;.
              </p>
            ) : (
              groupedModelsByProvider.map(([providerId, group]) => (
                <div key={providerId} className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                    <span className="text-primary">•</span>
                    <span>{group.provider_name}</span>
                    <span className="text-muted-foreground font-mono font-normal">
                      ({group.items.length})
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {group.items.map((opt) => {
                      const selected = isModelSelected(opt);
                      const caps = getModelCapabilities(opt.model_name);
                      return (
                        <button
                          key={`${opt.provider_id}:::${opt.model_name}`}
                          type="button"
                          onClick={() => handleToggleModelSelection(opt)}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-mono border transition-all cursor-pointer ${
                            selected
                              ? "bg-primary/10 border-primary text-primary font-bold shadow-xs ring-1 ring-primary/20"
                              : "bg-card border-border text-foreground hover:border-primary/50"
                          }`}
                        >
                          <span>{opt.model_name}</span>
                          {caps.isOcr && (
                            <span title="Vision / OCR">
                              <Eye className="size-3 text-sky-500" />
                            </span>
                          )}
                          {caps.hasReasoning && (
                            <span title="Reasoning">
                              <Brain className="size-3 text-purple-500" />
                            </span>
                          )}
                          {caps.capabilityLabel.includes("Fast") && (
                            <span title="Tốc độ cao">
                              <Zap className="size-3 text-amber-500" />
                            </span>
                          )}
                          {opt.category === "local" && (
                            <span title="Local Engine">
                              <Cpu className="size-3 text-emerald-500" />
                            </span>
                          )}
                          {selected && <Check className="size-3 text-primary ml-0.5" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>

          <DialogFooter className="pt-2 border-t border-border">
            <Button size="sm" onClick={() => setIsAddModelModalOpen(false)}>
              Hoàn Tất
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
