import {
  AlertTriangle,
  Brain,
  Eye,
  FlaskConical,
  RotateCw,
  Sparkles,
} from "lucide-react";
import { useRef, useState } from "react";
import {
  ResponsiveDialog as Dialog,
  ResponsiveDialogContent as DialogContent,
  ResponsiveDialogDescription as DialogDescription,
  ResponsiveDialogHeader as DialogHeader,
  ResponsiveDialogTitle as DialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  apiClient,
  type ModelProvider,
  type ProviderPreset,
  type SingleModelTestResult,
} from "@/services/api-client";
import type { ModelProbeRole } from "@/types/modelops";
import { formatProbeDetail } from "./probe-result";

export interface AddCustomModelDialogProps {
  initialModelId?: string;
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
    probeRole: ModelProbeRole,
  ) => Promise<void>;
}

export function AddCustomModelDialog({
  initialModelId = "",
  isOpen,
  onClose,
  selectedProvider,
  onConfirmAdd,
}: AddCustomModelDialogProps) {
  const initialConfig = selectedProvider?.model_capabilities?.[initialModelId];
  const declared = selectedProvider?.model_specs?.[initialModelId]?.type;
  const initialRole =
    declared === "embedding" || declared === "reranker" || declared === "ocr"
      ? declared
      : "chat";
  const [modelId, setModelId] = useState(initialModelId);
  const [probeRole, setProbeRole] = useState<ModelProbeRole>(
    initialConfig?.probe_role ?? initialRole,
  );
  const [hasVision, setHasVision] = useState(initialConfig?.vision ?? false);
  const [hasReasoning, setHasReasoning] = useState(
    initialConfig?.reasoning ?? false,
  );
  const [isDefault, setIsDefault] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [result, setResult] = useState<SingleModelTestResult | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const attempt = useRef(0);

  const invalidateTest = () => {
    attempt.current += 1;
    setResult(null);
    setIsTesting(false);
  };
  const handleClose = () => {
    if (isSaving) return;
    invalidateTest();
    setModelId("");
    setProbeRole("chat");
    setHasVision(false);
    setHasReasoning(false);
    setIsDefault(false);
    setSaveError(null);
    onClose();
  };
  const handleTest = async () => {
    if (!selectedProvider || !modelId.trim() || isTesting) return;
    const requestId = ++attempt.current;
    const target = modelId.trim();
    setIsTesting(true);
    setResult(null);
    try {
      const response = await apiClient.testProviderModels(
        selectedProvider.id,
        target,
        probeRole,
      );
      if (requestId === attempt.current) setResult(response.results[0] ?? null);
    } catch (error) {
      if (requestId === attempt.current)
        setResult({
          model_name: target,
          success: false,
          status: "error",
          latency_ms: 0,
          message:
            error instanceof Error
              ? error.message
              : "Không gửi được yêu cầu kiểm tra.",
          tested_at: new Date().toISOString(),
        });
    } finally {
      if (requestId === attempt.current) setIsTesting(false);
    }
  };
  const handleSave = async () => {
    if (!modelId.trim() || isSaving || isTesting) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      await onConfirmAdd(
        modelId.trim(),
        hasVision,
        hasReasoning,
        isDefault && probeRole !== "chat" ? probeRole : "none",
        result,
        probeRole,
      );
      invalidateTest();
      setModelId("");
      setIsDefault(false);
      setHasVision(false);
      setHasReasoning(false);
      onClose();
    } catch (error) {
      setSaveError(
        error instanceof Error ? error.message : "Không lưu được model.",
      );
    } finally {
      setIsSaving(false);
    }
  };
  if (!selectedProvider) return null;
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-lg max-h-[min(820px,calc(100vh-2rem))] flex flex-col p-0 gap-0 overflow-hidden">
        <DialogHeader className="border-b bg-muted/20 p-5 shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            {initialModelId ? "Sửa model" : "Thêm model"}
          </DialogTitle>
          <DialogDescription>
            Giữ nguyên Model ID của {selectedProvider.name}. Chọn đúng vai trò
            để kiểm tra đúng giao thức.
          </DialogDescription>
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto space-y-4 p-5">
          <div className="space-y-2">
            <label htmlFor="gateway-model-id" className="text-sm font-medium">
              Model ID
            </label>
            <div className="flex gap-2">
              <Input
                id="gateway-model-id"
                value={modelId}
                disabled={isSaving || !!initialModelId}
                className="min-w-0 font-mono"
                placeholder="Model ID từ nhà cung cấp"
                onChange={(event) => {
                  setModelId(event.target.value);
                  invalidateTest();
                  setSaveError(null);
                }}
              />
              <Button
                variant="outline"
                disabled={!modelId.trim() || isTesting || isSaving}
                onClick={handleTest}
              >
                {isTesting ? (
                  <RotateCw className="size-4 animate-spin" />
                ) : (
                  <FlaskConical className="size-4" />
                )}
                Kiểm tra
              </Button>
            </div>
            <p className="text-xs text-muted-foreground break-all">
              Gửi nguyên ID: {modelId.trim() || "—"}
            </p>
          </div>
          <div className="space-y-2">
            <label htmlFor="gateway-model-role" className="text-sm font-medium">
              Vai trò kiểm tra
            </label>
            <Select
              value={probeRole}
              disabled={isSaving}
              onValueChange={(value) => {
                setProbeRole(value as ModelProbeRole);
                setIsDefault(false);
                invalidateTest();
              }}
            >
              <SelectTrigger id="gateway-model-role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="chat">Chat</SelectItem>
                <SelectItem value="embedding">Embedding</SelectItem>
                <SelectItem value="reranker">Reranker</SelectItem>
                <SelectItem value="ocr">
                  OCR · kiểm tra danh mục/dịch vụ
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          {result && (
            <div
              role="status"
              className={`rounded-md border p-3 text-sm break-words ${result.success ? "border-success/30 bg-success/10 text-success" : "border-warning/30 bg-warning/10 text-foreground"}`}
            >
              {formatProbeDetail(result)}
              {result.served_model && (
                <p className="mt-1 text-xs">
                  Model phục vụ: {result.served_model} · {result.latency_ms} ms
                </p>
              )}
              {result.embedding_dimension && (
                <p className="mt-1 text-xs">
                  Vector: {result.embedding_dimension} chiều
                </p>
              )}
            </div>
          )}
          {probeRole === "chat" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="flex items-center justify-between gap-3 rounded-md border p-3">
                <span className="flex items-center gap-2 text-sm">
                  <Eye className="size-4" />
                  Vision
                </span>
                <Switch
                  checked={hasVision}
                  disabled={isSaving}
                  onCheckedChange={setHasVision}
                  aria-label="Vision"
                />
              </div>
              <div className="flex items-center justify-between gap-3 rounded-md border p-3">
                <span className="flex items-center gap-2 text-sm">
                  <Brain className="size-4" />
                  Reasoning
                </span>
                <Switch
                  checked={hasReasoning}
                  disabled={isSaving}
                  onCheckedChange={setHasReasoning}
                  aria-label="Reasoning"
                />
              </div>
            </div>
          )}
          {probeRole !== "chat" && (
            <div className="flex items-center justify-between gap-3 text-sm">
              <span>Đặt làm mặc định cho vai trò này</span>
              <Switch
                checked={isDefault}
                disabled={isSaving}
                onCheckedChange={setIsDefault}
                aria-label="Đặt làm mặc định"
              />
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            Bạn có thể lưu cấu hình khi chưa kiểm chứng. Lưu không chứng minh
            model hoạt động; OCR chỉ kiểm tra danh mục/dịch vụ, chưa bóc tách
            tài liệu.
          </p>
          {saveError && (
            <p
              role="alert"
              className="flex items-start gap-2 text-sm text-destructive"
            >
              <AlertTriangle className="size-4 shrink-0" />
              {saveError}
            </p>
          )}
        </div>
        <div className="grid grid-cols-2 sm:flex sm:justify-end gap-2 border-t bg-card p-4 shrink-0">
          <Button variant="outline" disabled={isSaving} onClick={handleClose}>
            Hủy
          </Button>
          <Button
            disabled={!modelId.trim() || isSaving || isTesting}
            onClick={handleSave}
          >
            {isSaving ? "Đang lưu…" : "Lưu"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
