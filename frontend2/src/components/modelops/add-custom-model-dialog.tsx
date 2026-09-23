import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Eye,
  FlaskConical,
  RotateCw,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Switch } from "../../components/ui/switch";
import {
  apiClient,
  type ModelProvider,
  type ProviderPreset,
  type SingleModelTestResult,
} from "../../services/api-client";
import { PRESET_SUGGESTED_MODELS } from "./modelops-helpers";

export interface AddCustomModelDialogProps {
  isOpen: boolean;
  onClose: () => void;
  selectedProvider: ModelProvider | null;
  presets: ProviderPreset[];
  onConfirmAdd: (
    modelId: string,
    isVision: boolean,
    isReasoning: boolean,
    defaultRole: "none" | "embedding" | "reranker" | "ocr",
    testResult: SingleModelTestResult | null,
  ) => void;
}

export const AddCustomModelDialog: React.FC<AddCustomModelDialogProps> = ({
  isOpen,
  onClose,
  selectedProvider,
  presets,
  onConfirmAdd,
}) => {
  const [newCustomModelId, setNewCustomModelId] = useState("");
  const [isVisionCapable, setIsVisionCapable] = useState(false);
  const [isReasoningCapable, setIsReasoningCapable] = useState(false);
  const [testingNewModel, setTestingNewModel] = useState(false);
  const [newModelTestResult, setNewModelTestResult] =
    useState<SingleModelTestResult | null>(null);
  const [modelRoleDefault, setModelRoleDefault] = useState<
    "none" | "embedding" | "reranker" | "ocr"
  >("none");

  const handleClose = () => {
    setNewCustomModelId("");
    setIsVisionCapable(false);
    setIsReasoningCapable(false);
    setNewModelTestResult(null);
    setTestingNewModel(false);
    setModelRoleDefault("none");
    onClose();
  };

  const handleTestNewModel = async () => {
    if (!selectedProvider || !newCustomModelId.trim()) return;
    setTestingNewModel(true);
    setNewModelTestResult(null);
    try {
      const res = await apiClient.testProviderModels(
        selectedProvider.id,
        newCustomModelId.trim(),
      );
      if (res.results && res.results.length > 0) {
        setNewModelTestResult(res.results[0]);
      }
    } catch {
      setNewModelTestResult({
        model_name: newCustomModelId.trim(),
        success: false,
        status: "error",
        latency_ms: 0,
        message: "Không thể kết nối hoặc gửi request kiểm tra tới Provider.",
        tested_at: new Date().toISOString(),
      });
    } finally {
      setTestingNewModel(false);
    }
  };

  const handleConfirm = () => {
    const trimmed = newCustomModelId.trim();
    if (!trimmed) return;
    onConfirmAdd(
      trimmed,
      isVisionCapable,
      isReasoningCapable,
      modelRoleDefault,
      newModelTestResult,
    );
    handleClose();
  };

  if (!selectedProvider) return null;

  const currentPreset = presets.find((pr) => pr.code === selectedProvider.type);
  const suggestedList =
    currentPreset?.suggested_models ||
    PRESET_SUGGESTED_MODELS[selectedProvider.type] ||
    [];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-lg p-6 space-y-4 border-border shadow-xl">
        {/* Mac-style Window Controls Header */}
        <div className="flex items-center gap-1.5 pb-1">
          <span className="h-3 w-3 rounded-full bg-red-500/80 inline-block" />
          <span className="h-3 w-3 rounded-full bg-yellow-500/80 inline-block" />
          <span className="h-3 w-3 rounded-full bg-green-500/80 inline-block" />
        </div>

        <DialogHeader className="space-y-1">
          <DialogTitle className="text-base font-bold text-foreground flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            Thêm Mô Hình Tùy Chỉnh (Add Custom Model)
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Cấu hình ID mô hình tương thích với Provider {selectedProvider.name}{" "}
            và kiểm tra tính khả dụng trực tiếp trước khi kích hoạt.
          </DialogDescription>
        </DialogHeader>

        {/* Model ID Input with inline test button */}
        <div className="space-y-2 pt-1">
          <span className="text-xs font-semibold text-foreground block">
            Mã định danh mô hình (Model ID) *
          </span>
          <div className="flex gap-2">
            <Input
              required
              placeholder="VD: gpt-4o, gemini-2.0-flash, mistral-ocr-latest..."
              value={newCustomModelId}
              onChange={(e) => {
                setNewCustomModelId(e.target.value);
                setNewModelTestResult(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  if (newCustomModelId.trim()) handleConfirm();
                }
              }}
              className="font-mono text-xs h-9 flex-1"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!newCustomModelId.trim() || testingNewModel}
              onClick={handleTestNewModel}
              className="h-9 px-3 text-xs gap-1.5 text-primary border-primary/30 hover:bg-primary/10 shrink-0 cursor-pointer"
              title="Gửi ping kiểm tra xem Model ID này có phản hồi từ Provider không"
            >
              {testingNewModel ? (
                <RotateCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <FlaskConical className="h-3.5 w-3.5" />
              )}
              <span>{testingNewModel ? "Đang test..." : "Test"}</span>
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground font-mono">
            Gửi tới nhà cung cấp dưới dạng:{" "}
            {newCustomModelId.trim() || "model-id"}
          </p>

          {/* Test result status badge */}
          {newModelTestResult && (
            <div
              className={`p-2.5 rounded-md text-xs flex items-center gap-2 ${
                newModelTestResult.status === "available"
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                  : newModelTestResult.status === "rate_limited"
                    ? "bg-amber-500/10 text-amber-500 border border-amber-500/30"
                    : "bg-destructive/10 text-destructive border border-destructive/30"
              }`}
            >
              {newModelTestResult.status === "available" ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <AlertTriangle className="h-4 w-4 shrink-0" />
              )}
              <div className="flex-1 font-medium">
                {newModelTestResult.status === "available" ? (
                  <span>
                    Khả dụng! Độ trễ phản hồi:{" "}
                    <strong>{newModelTestResult.latency_ms}ms</strong> (
                    {newModelTestResult.message})
                  </span>
                ) : newModelTestResult.status === "rate_limited" ? (
                  <span>
                    Chạm Rate Limit (429): {newModelTestResult.message}
                  </span>
                ) : (
                  <span>
                    Không khả dụng (404/Error): {newModelTestResult.message}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Capabilities switches */}
        <div className="space-y-2 pt-2 border-t border-border/70">
          <span className="text-xs font-semibold text-foreground block">
            Khả Năng Hỗ Trợ (Capabilities)
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div className="flex items-center justify-between p-2.5 rounded-md border border-border/70 bg-muted/20">
              <div className="space-y-0.5">
                <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
                  <Eye className="h-3.5 w-3.5 text-primary" />
                  Vision
                </span>
                <p className="text-[10px] text-muted-foreground">
                  Hỗ trợ ảnh & OCR
                </p>
              </div>
              <Switch
                checked={isVisionCapable}
                onCheckedChange={setIsVisionCapable}
                aria-label="Bật tính năng Vision"
              />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-md border border-border/70 bg-muted/20">
              <div className="space-y-0.5">
                <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
                  <Brain className="h-3.5 w-3.5 text-primary" />
                  Reasoning
                </span>
                <p className="text-[10px] text-muted-foreground">
                  Suy luận tư duy
                </p>
              </div>
              <Switch
                checked={isReasoningCapable}
                onCheckedChange={setIsReasoningCapable}
                aria-label="Bật tính năng Reasoning"
              />
            </div>
          </div>
        </div>

        {/* Quick suggestions from provider preset */}
        {suggestedList.length > 0 && (
          <div className="space-y-1.5 pt-2 border-t border-border/60">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
              Gợi ý nhanh từ {selectedProvider.name}:
            </span>
            <div className="flex flex-wrap gap-1">
              {suggestedList.map((sm) => {
                const isAlreadyAdded = (selectedProvider.models || []).includes(
                  sm,
                );
                return (
                  <button
                    type="button"
                    key={sm}
                    disabled={isAlreadyAdded}
                    onClick={() => {
                      setNewCustomModelId(sm);
                      const lower = sm.toLowerCase();
                      setIsVisionCapable(
                        lower.includes("flash") ||
                          lower.includes("vision") ||
                          lower.includes("4o") ||
                          lower.includes("sonnet") ||
                          lower.includes("ocr"),
                      );
                      setIsReasoningCapable(
                        lower.includes("o1") ||
                          lower.includes("o3") ||
                          lower.includes("reason") ||
                          lower.includes("r1") ||
                          lower.includes("thinking"),
                      );
                      setNewModelTestResult(null);
                    }}
                    className={`text-[11px] font-mono px-2 py-0.5 rounded border transition-colors ${
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

        {/* Dialog Footer Actions */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/60">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleClose}
            className="h-9 px-4 text-xs cursor-pointer"
          >
            Hủy
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={
              !newCustomModelId.trim() ||
              (selectedProvider.models || []).includes(newCustomModelId.trim())
            }
            onClick={handleConfirm}
            className="h-9 px-4 text-xs cursor-pointer"
          >
            Thêm Mô Hình
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
