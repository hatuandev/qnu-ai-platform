import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Brain,
  Check,
  Copy,
  Cpu,
  Eye,
  Layers,
  Pencil,
  Plus,
  Search,
  Star,
  Trash2,
  Zap,
} from "lucide-react";
import type React from "react";
import { useId, useMemo, useState } from "react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Checkbox } from "../../components/ui/checkbox";
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
import type {
  ModelComboItem,
  ModelComboTaskType,
  ModelOption,
  OCRComboItem,
  SystemModelDefaults,
} from "../../types/modelops";
import {
  STRATEGY_META,
  TASK_TYPE_META,
  getModelCapabilities,
} from "./modelops-helpers";

export interface CombosVisionSectionProps {
  systemDefaults?: SystemModelDefaults;
  availableOcrs?: ModelOption[];
  availableEmbeddings?: ModelOption[];
  availableRerankers?: ModelOption[];
  allAvailableModels?: ModelOption[];
  initialTaskFilter?: string;
  onUpdateDefaults: (payload: Partial<SystemModelDefaults>) => void;
}

export const CombosVisionSection: React.FC<CombosVisionSectionProps> = ({
  systemDefaults,
  availableOcrs = [],
  availableEmbeddings = [],
  availableRerankers = [],
  allAvailableModels = [],
  initialTaskFilter = "all",
  onUpdateDefaults,
}) => {
  // Lấy danh sách combos
  const combos: ModelComboItem[] = useMemo(() => {
    return systemDefaults?.model_combos || [];
  }, [systemDefaults?.model_combos]);

  // Bộ lọc task type
  const [selectedTaskFilter, setSelectedTaskFilter] =
    useState<string>(initialTaskFilter);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // State Modal Tạo / Sửa Combo
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCombo, setEditingCombo] = useState<ModelComboItem | null>(null);

  // Form State
  const [formTaskType, setFormTaskType] = useState<ModelComboTaskType>("ocr");
  const [formName, setFormName] = useState("");
  const [formStrategy, setFormStrategy] = useState<
    "fallback" | "round_robin" | "fusion"
  >("fallback");
  const [formDescription, setFormDescription] = useState("");
  const [formModels, setFormModels] = useState<OCRComboItem[]>([]);
  const [formIsDefault, setFormIsDefault] = useState(false);

  // State Drawer / Picker Thêm Model
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [pickerSearchQuery, setPickerSearchQuery] = useState("");

  const comboNameId = useId();
  const comboStrategyId = useId();

  // Đếm số lượng combos theo từng loại tác vụ
  const counts = useMemo(() => {
    const map: Record<string, number> = {
      all: combos.length,
      ocr: 0,
      embedding: 0,
      reranker: 0,
      chat: 0,
    };
    for (const c of combos) {
      const t = c.task_type || "ocr";
      map[t] = (map[t] || 0) + 1;
    }
    return map;
  }, [combos]);

  // Lọc combos hiển thị theo tab và search
  const filteredCombos = useMemo(() => {
    let result = combos;
    if (selectedTaskFilter !== "all") {
      result = result.filter(
        (c) => (c.task_type || "ocr") === selectedTaskFilter,
      );
    }
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          (c.description || "").toLowerCase().includes(q) ||
          c.models.some(
            (m) =>
              m.model_name.toLowerCase().includes(q) ||
              m.provider_name.toLowerCase().includes(q),
          ),
      );
    }
    return result;
  }, [combos, selectedTaskFilter, searchQuery]);

  // Bộ lọc candidate models thông minh theo formTaskType
  const candidateModelsForTask = useMemo(() => {
    if (formTaskType === "embedding") {
      if (availableEmbeddings.length > 0) return availableEmbeddings;
      return allAvailableModels.filter(
        (m) => getModelCapabilities(m.model_name).isEmbedding,
      );
    }
    if (formTaskType === "reranker") {
      if (availableRerankers.length > 0) return availableRerankers;
      return allAvailableModels.filter(
        (m) => getModelCapabilities(m.model_name).isReranker,
      );
    }
    if (formTaskType === "ocr") {
      if (availableOcrs.length > 0) return availableOcrs;
      return allAvailableModels.filter(
        (m) => getModelCapabilities(m.model_name).isOcr,
      );
    }
    // chat
    return allAvailableModels.filter((m) => {
      const caps = getModelCapabilities(m.model_name);
      return !caps.isEmbedding && !caps.isReranker;
    });
  }, [
    formTaskType,
    availableEmbeddings,
    availableRerankers,
    availableOcrs,
    allAvailableModels,
  ]);

  // Lọc models trong picker theo query
  const filteredCandidatesInPicker = useMemo(() => {
    const q = pickerSearchQuery.trim().toLowerCase();
    if (!q) return candidateModelsForTask;
    return candidateModelsForTask.filter(
      (m) =>
        m.model_name.toLowerCase().includes(q) ||
        m.provider_name.toLowerCase().includes(q) ||
        (m.description || "").toLowerCase().includes(q),
    );
  }, [candidateModelsForTask, pickerSearchQuery]);

  // Mở modal tạo mới
  const handleOpenCreateModal = (taskType: ModelComboTaskType = "ocr") => {
    setEditingCombo(null);
    setFormTaskType(taskType);
    setFormName(`combo-${taskType}-${Date.now().toString().slice(-4)}`);
    setFormStrategy("fallback");
    setFormDescription("");
    setFormModels([]);
    setFormIsDefault(false);
    setPickerSearchQuery("");
    setIsPickerOpen(false);
    setIsModalOpen(true);
  };

  // Mở modal sửa
  const handleOpenEditModal = (combo: ModelComboItem) => {
    setEditingCombo(combo);
    setFormTaskType(combo.task_type || "ocr");
    setFormName(combo.name);
    setFormStrategy(combo.strategy);
    setFormDescription(combo.description || "");
    setFormModels([...combo.models]);
    setFormIsDefault(Boolean(combo.is_default));
    setPickerSearchQuery("");
    setIsPickerOpen(false);
    setIsModalOpen(true);
  };

  // Nhân bản combo
  const handleCloneCombo = (combo: ModelComboItem) => {
    const cloned: ModelComboItem = {
      ...combo,
      id: `combo_${Date.now()}`,
      name: `${combo.name}-copy`,
      is_default: false,
    };
    onUpdateDefaults({
      model_combos: [...combos, cloned],
    });
  };

  // Xóa combo
  const handleDeleteCombo = (comboId: string) => {
    const target = combos.find((c) => c.id === comboId);
    if (!target) return;
    if (
      target.is_default &&
      combos.filter(
        (c) => (c.task_type || "ocr") === (target.task_type || "ocr"),
      ).length === 1
    ) {
      alert("Không thể xóa Combo mặc định duy nhất của nhóm tác vụ này!");
      return;
    }
    const updated = combos.filter((c) => c.id !== comboId);
    onUpdateDefaults({
      model_combos: updated,
    });
  };

  // Đặt làm mặc định kênh
  const handleSetDefault = (combo: ModelComboItem) => {
    const taskT = combo.task_type || "ocr";
    const updatedCombos = combos.map((c) => {
      if ((c.task_type || "ocr") === taskT) {
        return { ...c, is_default: c.id === combo.id };
      }
      return c;
    });

    const firstModel = combo.models[0];
    const payload: Partial<SystemModelDefaults> = {
      model_combos: updatedCombos,
    };

    if (taskT === "embedding") {
      payload.default_embedding_mode = "combo";
      payload.default_embedding_combo_id = combo.id;
      payload.embedding_combo_chain = combo.models;
      if (firstModel) {
        payload.default_embedding_provider_id = firstModel.provider_id;
        payload.default_embedding_model = firstModel.model_name;
      }
    } else if (taskT === "reranker") {
      payload.default_reranker_mode = "combo";
      payload.default_reranker_combo_id = combo.id;
      payload.reranker_combo_chain = combo.models;
      if (firstModel) {
        payload.default_reranker_provider_id = firstModel.provider_id;
        payload.default_reranker_model = firstModel.model_name;
      }
    } else if (taskT === "ocr") {
      payload.default_ocr_mode = "combo";
      payload.default_ocr_combo_id = combo.id;
      payload.ocr_combo_chain = combo.models;
      if (firstModel) {
        payload.default_ocr_provider_id = firstModel.provider_id;
        payload.default_ocr_model = firstModel.model_name;
      }
    } else if (taskT === "chat") {
      payload.default_chat_mode = "combo";
      payload.default_chat_combo_id = combo.id;
      payload.chat_combo_chain = combo.models;
      if (firstModel) {
        payload.default_chat_provider_id = firstModel.provider_id;
        payload.default_chat_model = firstModel.model_name;
      }
    }

    onUpdateDefaults(payload);
  };

  // Thao tác sắp xếp mô hình trong form
  const handleMoveStep = (index: number, direction: "up" | "down") => {
    const targetIdx = direction === "up" ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= formModels.length) return;
    const next = [...formModels];
    const temp = next[index];
    next[index] = next[targetIdx];
    next[targetIdx] = temp;
    setFormModels(next);
  };

  const handleToggleStepActive = (index: number) => {
    setFormModels(
      formModels.map((item, idx) =>
        idx === index
          ? { ...item, is_active: !(item.is_active ?? true) }
          : item,
      ),
    );
  };

  const handleRemoveStep = (index: number) => {
    setFormModels(formModels.filter((_, idx) => idx !== index));
  };

  const handleAddCandidateToForm = (modelOpt: ModelOption) => {
    const exists = formModels.some(
      (m) =>
        m.provider_id === modelOpt.provider_id &&
        m.model_name === modelOpt.model_name,
    );
    if (exists) return;

    const newItem: OCRComboItem = {
      provider_id: modelOpt.provider_id,
      provider_name: modelOpt.provider_name,
      model_name: modelOpt.model_name,
      provider_type: modelOpt.provider_type,
      is_active: true,
      description: modelOpt.description,
    };
    setFormModels([...formModels, newItem]);
  };

  // Lưu combo từ modal
  const handleSaveCombo = () => {
    if (!formName.trim()) return;

    const safeName = formName.trim().replace(/[^a-zA-Z0-9_.-]/g, "_");
    const itemData: ModelComboItem = {
      id: editingCombo?.id || `combo_${Date.now()}`,
      name: safeName,
      task_type: formTaskType,
      strategy: formStrategy,
      description: formDescription.trim() || undefined,
      models: formModels,
      is_default: formIsDefault,
    };

    let updatedCombos: ModelComboItem[];
    if (editingCombo) {
      updatedCombos = combos.map((c) => {
        if (c.id === editingCombo.id) return itemData;
        if (formIsDefault && (c.task_type || "ocr") === formTaskType) {
          return { ...c, is_default: false };
        }
        return c;
      });
    } else {
      updatedCombos = formIsDefault
        ? [
            ...combos.map((c) =>
              (c.task_type || "ocr") === formTaskType
                ? { ...c, is_default: false }
                : c,
            ),
            itemData,
          ]
        : [...combos, itemData];
    }

    const payload: Partial<SystemModelDefaults> = {
      model_combos: updatedCombos,
    };

    if (formIsDefault && formModels.length > 0) {
      const first = formModels[0];
      if (formTaskType === "embedding") {
        payload.default_embedding_mode = "combo";
        payload.default_embedding_combo_id = itemData.id;
        payload.embedding_combo_chain = formModels;
        payload.default_embedding_provider_id = first.provider_id;
        payload.default_embedding_model = first.model_name;
      } else if (formTaskType === "reranker") {
        payload.default_reranker_mode = "combo";
        payload.default_reranker_combo_id = itemData.id;
        payload.reranker_combo_chain = formModels;
        payload.default_reranker_provider_id = first.provider_id;
        payload.default_reranker_model = first.model_name;
      } else if (formTaskType === "ocr") {
        payload.default_ocr_mode = "combo";
        payload.default_ocr_combo_id = itemData.id;
        payload.ocr_combo_chain = formModels;
        payload.default_ocr_provider_id = first.provider_id;
        payload.default_ocr_model = first.model_name;
      } else if (formTaskType === "chat") {
        payload.default_chat_mode = "combo";
        payload.default_chat_combo_id = itemData.id;
        payload.chat_combo_chain = formModels;
        payload.default_chat_provider_id = first.provider_id;
        payload.default_chat_model = first.model_name;
      }
    }

    onUpdateDefaults(payload);
    setIsModalOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <Card className="p-4 bg-gradient-to-r from-card via-card to-primary/5 border-primary/20 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary shrink-0">
              <Layers className="size-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-foreground">
                  Trung Tâm Quản Lý Combos Đa Nhiệm (Multi-task Combos Hub)
                </h3>
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono border-primary/30 text-primary bg-primary/5"
                >
                  {combos.length} Combos Sẵn Sàng
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Thiết lập chuỗi dự phòng (Fallback Chains), cân bằng tải (Round
                Robin) hoặc chạy song song (Fusion) cho từng tác vụ AI.
              </p>
            </div>
          </div>

          <Button
            size="sm"
            onClick={() => handleOpenCreateModal("ocr")}
            className="gap-1.5 self-start sm:self-center shrink-0 shadow-xs"
          >
            <Plus className="size-3.5" />
            <span>Tạo Combo Mới</span>
          </Button>
        </div>
      </Card>

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 border-b border-border/70 pb-3">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <Button
            variant={selectedTaskFilter === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedTaskFilter("all")}
            className="h-8 text-xs gap-1.5 rounded-full"
          >
            <span>Tất Cả</span>
            <Badge
              variant="secondary"
              className="text-[9px] px-1 py-0 h-4 bg-background/50 font-mono"
            >
              {counts.all}
            </Badge>
          </Button>

          <Button
            variant={selectedTaskFilter === "ocr" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedTaskFilter("ocr")}
            className="h-8 text-xs gap-1.5 rounded-full"
          >
            <Eye className="size-3" />
            <span>OCR Thị Giác</span>
            <Badge
              variant="secondary"
              className="text-[9px] px-1 py-0 h-4 bg-background/50 font-mono"
            >
              {counts.ocr}
            </Badge>
          </Button>

          <Button
            variant={selectedTaskFilter === "embedding" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedTaskFilter("embedding")}
            className="h-8 text-xs gap-1.5 rounded-full"
          >
            <Cpu className="size-3" />
            <span>Nhúng Vector</span>
            <Badge
              variant="secondary"
              className="text-[9px] px-1 py-0 h-4 bg-background/50 font-mono"
            >
              {counts.embedding}
            </Badge>
          </Button>

          <Button
            variant={selectedTaskFilter === "reranker" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedTaskFilter("reranker")}
            className="h-8 text-xs gap-1.5 rounded-full"
          >
            <Zap className="size-3" />
            <span>Tái Xếp Hạng</span>
            <Badge
              variant="secondary"
              className="text-[9px] px-1 py-0 h-4 bg-background/50 font-mono"
            >
              {counts.reranker}
            </Badge>
          </Button>

          <Button
            variant={selectedTaskFilter === "chat" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedTaskFilter("chat")}
            className="h-8 text-xs gap-1.5 rounded-full"
          >
            <Brain className="size-3" />
            <span>LLM Chat</span>
            <Badge
              variant="secondary"
              className="text-[9px] px-1 py-0 h-4 bg-background/50 font-mono"
            >
              {counts.chat}
            </Badge>
          </Button>
        </div>

        {/* Realtime Search Input */}
        <div className="relative w-full sm:w-64 shrink-0">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tên combo, model..."
            className="h-8 pl-8 text-xs bg-card"
          />
        </div>
      </div>

      {/* Combos Cards Grid */}
      {filteredCombos.length === 0 ? (
        <Card className="p-8 text-center border-dashed border-border bg-card/40 space-y-3">
          <div className="size-10 rounded-full bg-muted flex items-center justify-center mx-auto text-muted-foreground">
            <Layers className="size-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-foreground">
              Không tìm thấy Combo nào
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              Chưa có combo nào cho nhóm tác vụ này hoặc từ khóa tìm kiếm không
              khớp.
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              handleOpenCreateModal(
                selectedTaskFilter === "all"
                  ? "ocr"
                  : (selectedTaskFilter as ModelComboTaskType),
              )
            }
            className="h-8 text-xs gap-1.5 mx-auto"
          >
            <Plus className="size-3.5" />
            <span>Tạo Combo Cho Tác Vụ Này</span>
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredCombos.map((combo) => {
            const taskT = combo.task_type || "ocr";
            const taskMeta = TASK_TYPE_META[taskT] || TASK_TYPE_META.ocr;
            const stratMeta =
              STRATEGY_META[combo.strategy] || STRATEGY_META.fallback;

            return (
              <Card
                key={combo.id}
                className={`p-4 bg-card border flex flex-col justify-between gap-3.5 transition-all shadow-2xs hover:shadow-xs ${
                  combo.is_default
                    ? "border-primary/50 ring-1 ring-primary/20"
                    : "border-border/80 hover:border-border"
                }`}
              >
                {/* Card Top: Badges & Actions */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-mono ${taskMeta.badgeClass}`}
                      >
                        {taskMeta.shortLabel}
                      </Badge>

                      <Badge
                        variant="outline"
                        className={`text-[10px] font-mono ${stratMeta.badgeClass}`}
                      >
                        {combo.strategy}
                      </Badge>

                      {combo.is_default && (
                        <Badge
                          variant="default"
                          className="text-[10px] font-mono flex items-center gap-1 bg-primary text-primary-foreground"
                        >
                          <Star className="size-2.5 fill-current" />
                          <span>Mặc Định Kênh</span>
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCloneCombo(combo)}
                        className="size-7 text-muted-foreground hover:text-foreground"
                        title="Nhân bản Combo"
                      >
                        <Copy className="size-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleOpenEditModal(combo)}
                        className="size-7 text-muted-foreground hover:text-foreground"
                        title="Chỉnh sửa Combo"
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteCombo(combo.id)}
                        className="size-7 text-muted-foreground hover:text-destructive"
                        title="Xóa Combo"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-bold font-mono text-foreground">
                      {combo.name}
                    </h4>
                    {combo.description && (
                      <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">
                        {combo.description}
                      </p>
                    )}
                  </div>
                </div>

                {/* Card Middle: Visual Failover Pipeline */}
                <div className="space-y-1.5 bg-muted/20 p-2.5 rounded-lg border border-border/50">
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">
                    <span>
                      Chuỗi Điều Phối ({combo.models?.length || 0} Tầng)
                    </span>
                    <span className="font-mono">{stratMeta.label}</span>
                  </div>

                  <div className="space-y-1">
                    {combo.models?.map((step, idx) => {
                      const isActive = step.is_active ?? true;
                      const isFirst = idx === 0;

                      return (
                        <div
                          key={`${combo.id}-${step.provider_id}-${step.model_name}-${idx}`}
                          className={`flex items-center justify-between px-2.5 py-1.5 rounded-md border text-xs ${
                            isActive
                              ? isFirst
                                ? "bg-card border-primary/30"
                                : "bg-card/70 border-border/60"
                              : "bg-muted/40 border-dashed border-border/40 opacity-50"
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className={`size-4 rounded-full flex items-center justify-center text-[9px] font-mono font-bold shrink-0 ${
                                isFirst
                                  ? "bg-primary text-primary-foreground"
                                  : "bg-muted text-muted-foreground border border-border"
                              }`}
                            >
                              {idx + 1}
                            </span>
                            <span className="font-semibold text-foreground truncate">
                              {step.model_name}
                            </span>
                            <span className="text-[10px] text-muted-foreground truncate hidden sm:inline">
                              ({step.provider_name})
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 pl-1">
                            {idx < combo.models.length - 1 && (
                              <ArrowRight className="size-3 text-muted-foreground/60" />
                            )}
                            <span
                              className={`size-1.5 rounded-full ${
                                isActive ? "bg-emerald-500" : "bg-muted"
                              }`}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Card Bottom: Make Default Button */}
                <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[11px]">
                  <span className="text-muted-foreground text-[10px]">
                    ID: <code className="font-mono">{combo.id}</code>
                  </span>
                  {!combo.is_default && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSetDefault(combo)}
                      className="h-7 text-xs gap-1 border-primary/30 text-primary hover:bg-primary/10"
                    >
                      <Star className="size-3" />
                      <span>Gắn làm Mặc Định Kênh</span>
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL TẠO / CHỈNH SỬA COMBO */}
      {/* ========================================================= */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <Layers className="size-4 text-primary" />
              <span>
                {editingCombo
                  ? `Chỉnh Sửa Combo: ${editingCombo.name}`
                  : "Tạo Chuỗi Combo Dự Phòng Mới"}
              </span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Định nghĩa danh sách các mô hình ưu tiên tuần tự khi gặp sự cố
              chạm hạn ngạch (Quota 429) hoặc lỗi mạng.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* 1. Chọn Task Type */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Loại Tác Vụ Cốt Lõi (Task Type):
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {(
                  [
                    {
                      id: "ocr",
                      label: "Vision OCR",
                      icon: Eye,
                    },
                    {
                      id: "embedding",
                      label: "Embedding",
                      icon: Cpu,
                    },
                    {
                      id: "reranker",
                      label: "Reranker",
                      icon: Zap,
                    },
                    {
                      id: "chat",
                      label: "LLM Chat",
                      icon: Brain,
                    },
                  ] as const
                ).map((t) => {
                  const Icon = t.icon;
                  const isSel = formTaskType === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setFormTaskType(t.id)}
                      className={`flex items-center justify-center gap-1.5 p-2 rounded-lg border text-xs font-semibold transition-all ${
                        isSel
                          ? "bg-primary text-primary-foreground border-primary shadow-xs"
                          : "bg-card text-muted-foreground border-border hover:text-foreground"
                      }`}
                    >
                      <Icon className="size-3.5" />
                      <span>{t.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 2. Tên Combo & Chiến Lược */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label
                  htmlFor={comboNameId}
                  className="text-xs font-semibold text-foreground"
                >
                  Tên Định Danh Combo:
                </label>
                <Input
                  id={comboNameId}
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="ví dụ: qnu-embedding-shield"
                  className="h-8 text-xs font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor={comboStrategyId}
                  className="text-xs font-semibold text-foreground"
                >
                  Chiến Lược Điều Phối (Strategy):
                </label>
                <Select
                  value={formStrategy}
                  onValueChange={(val: "fallback" | "round_robin" | "fusion") =>
                    setFormStrategy(val)
                  }
                >
                  <SelectTrigger
                    id={comboStrategyId}
                    className="h-8 text-xs font-mono"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fallback">
                      Fallback (Dự Phòng Lỗi 429)
                    </SelectItem>
                    <SelectItem value="round_robin">
                      Round Robin (Cân Bằng Tải)
                    </SelectItem>
                    <SelectItem value="fusion">
                      Fusion (Đồng Thời / Ghép Điểm)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 3. Mô tả */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Mô Tả Nghiệp Vụ:
              </label>
              <Input
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="Chuỗi failover bảo vệ hạn ngạch..."
                className="h-8 text-xs"
              />
            </div>

            {/* 4. Danh sách mô hình trong chuỗi */}
            <div className="space-y-2 pt-2 border-t border-border">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <span>Chuỗi Mô Hình ({formModels.length} Bước)</span>
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsPickerOpen(!isPickerOpen)}
                  className="h-7 text-xs gap-1 border-primary/30 text-primary hover:bg-primary/10"
                >
                  <Plus className="size-3" />
                  <span>
                    {isPickerOpen ? "Đóng Khung Thêm" : "Thêm Mô Hình"}
                  </span>
                </Button>
              </div>

              {/* Picker Drawer */}
              {isPickerOpen && (
                <div className="p-3 rounded-lg border border-primary/30 bg-primary/5 space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-semibold text-primary">
                      Gợi ý mô hình phù hợp với tác vụ{" "}
                      {formTaskType.toUpperCase()}:
                    </span>
                    <Input
                      value={pickerSearchQuery}
                      onChange={(e) => setPickerSearchQuery(e.target.value)}
                      placeholder="Lọc mô hình..."
                      className="h-7 text-xs w-44 bg-card"
                    />
                  </div>

                  <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
                    {filteredCandidatesInPicker.length === 0 ? (
                      <p className="text-xs text-muted-foreground text-center py-2">
                        Không tìm thấy mô hình tương thích.
                      </p>
                    ) : (
                      filteredCandidatesInPicker.map((m) => {
                        const isAdded = formModels.some(
                          (fm) =>
                            fm.provider_id === m.provider_id &&
                            fm.model_name === m.model_name,
                        );

                        return (
                          <div
                            key={`cand-${m.provider_id}-${m.model_name}`}
                            className="flex items-center justify-between p-2 rounded-md bg-card border border-border text-xs"
                          >
                            <div className="min-w-0 pr-2">
                              <span className="font-semibold text-foreground truncate block">
                                {m.model_name}
                              </span>
                              <span className="text-[11px] text-muted-foreground">
                                {m.provider_name} • {m.provider_type}
                              </span>
                            </div>
                            <Button
                              size="sm"
                              variant={isAdded ? "secondary" : "default"}
                              disabled={isAdded}
                              onClick={() => handleAddCandidateToForm(m)}
                              className="h-6 text-[11px] px-2 shrink-0"
                            >
                              {isAdded ? "Đã Thêm" : "+ Thêm"}
                            </Button>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}

              {/* Steps list */}
              {formModels.length === 0 ? (
                <div className="p-6 rounded-lg border border-dashed border-border text-center text-xs text-muted-foreground">
                  Chuỗi chưa có mô hình nào. Nhấn &quot;Thêm Mô Hình&quot; ở
                  trên để bắt đầu xây dựng luồng failover.
                </div>
              ) : (
                <div className="space-y-1.5">
                  {formModels.map((item, idx) => {
                    const isFirst = idx === 0;
                    const isLast = idx === formModels.length - 1;
                    const isActive = item.is_active ?? true;

                    return (
                      <div
                        key={`form-step-${item.provider_id}-${item.model_name}-${idx}`}
                        className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-card text-xs"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="size-5 rounded-full bg-primary/10 text-primary font-bold font-mono text-[10px] flex items-center justify-center shrink-0">
                            {idx + 1}
                          </span>
                          <div className="truncate">
                            <span className="font-semibold text-foreground truncate block">
                              {item.model_name}
                            </span>
                            <span className="text-[11px] text-muted-foreground">
                              {item.provider_name}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          <Button
                            variant="ghost"
                            size="icon"
                            disabled={isFirst}
                            onClick={() => handleMoveStep(idx, "up")}
                            className="size-6 text-muted-foreground hover:text-foreground"
                            title="Di chuyển lên"
                          >
                            <ArrowUp className="size-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            disabled={isLast}
                            onClick={() => handleMoveStep(idx, "down")}
                            className="size-6 text-muted-foreground hover:text-foreground"
                            title="Di chuyển xuống"
                          >
                            <ArrowDown className="size-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleToggleStepActive(idx)}
                            className={`size-6 ${
                              isActive
                                ? "text-emerald-500"
                                : "text-muted-foreground"
                            }`}
                            title={isActive ? "Đang bật" : "Đang tắt"}
                          >
                            <Check className="size-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRemoveStep(idx)}
                            className="size-6 text-destructive hover:bg-destructive/10"
                            title="Xóa bước này"
                          >
                            <Trash2 className="size-3" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* 5. Gắn làm mặc định */}
            <div className="pt-2 border-t border-border flex items-center space-x-2">
              <Checkbox
                id="combo-default-checkbox"
                checked={formIsDefault}
                onCheckedChange={(checked) =>
                  setFormIsDefault(Boolean(checked))
                }
              />
              <label
                htmlFor="combo-default-checkbox"
                className="text-xs font-semibold text-foreground cursor-pointer"
              >
                Đặt làm Chuỗi Dự Phòng MẶC ĐỊNH cho kênh tác vụ{" "}
                <span className="text-primary uppercase">{formTaskType}</span>
              </label>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsModalOpen(false)}
            >
              Hủy
            </Button>
            <Button
              size="sm"
              disabled={!formName.trim() || formModels.length === 0}
              onClick={handleSaveCombo}
            >
              Lưu Cấu Hình Combo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
