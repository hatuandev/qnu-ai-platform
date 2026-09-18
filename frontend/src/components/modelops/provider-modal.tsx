import { KeyRound, X } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { ProviderIcon } from "../../components/icons/provider-icon";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import type { ModelProvider, ProviderPreset } from "../../services/api-client";

export interface ProviderModalProps {
  isOpen: boolean;
  onClose: () => void;
  editingProvider: ModelProvider | null;
  presets: ProviderPreset[];
  initialType?: ModelProvider["type"];
  onSave: (data: {
    name: string;
    type: ModelProvider["type"];
    api_base_url: string;
    api_key: string;
    account_id: string;
    models: string[];
    is_active: boolean;
  }) => void;
  isSaving: boolean;
}

export const ProviderModal: React.FC<ProviderModalProps> = ({
  isOpen,
  onClose,
  editingProvider,
  presets,
  initialType = "openai",
  onSave,
  isSaving,
}) => {
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState<ModelProvider["type"]>(initialType);
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [accountId, setAccountId] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [newModelInput, setNewModelInput] = useState("");
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (editingProvider) {
      setName(editingProvider.name);
      setProviderType(editingProvider.type || "openai");
      setApiBaseUrl(editingProvider.api_base_url || "");
      setApiKey("");
      setAccountId(editingProvider.account_id || "");
      setModels(editingProvider.models || []);
      setIsActive(editingProvider.is_active);
    } else {
      setName("");
      setProviderType(initialType);
      setApiBaseUrl("");
      setApiKey("");
      setAccountId("");
      setModels([]);
      setIsActive(true);
    }
  }, [editingProvider, initialType]);

  const applyPreset = (preset: ProviderPreset) => {
    setProviderType(preset.code as ModelProvider["type"]);
    setName(preset.name);
    if (preset.default_base_url) {
      setApiBaseUrl(preset.default_base_url);
    }
    setModels([]);
  };

  const handleAddModelTag = () => {
    const trimmed = newModelInput.trim();
    if (trimmed && !models.includes(trimmed)) {
      setModels([...models, trimmed]);
      setNewModelInput("");
    }
  };

  const handleRemoveModelTag = (mToRemove: string) => {
    setModels(models.filter((m) => m !== mToRemove));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSave({
      name: name.trim(),
      type: providerType,
      api_base_url: apiBaseUrl.trim(),
      api_key: apiKey.trim(),
      account_id: accountId.trim(),
      models,
      is_active: isActive,
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-sm font-bold flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-primary" />
            {editingProvider
              ? `Chỉnh Sửa Provider: ${editingProvider.name}`
              : "Thêm Nhà Cung Cấp LLM Mới"}
          </DialogTitle>
          <DialogDescription className="text-xs">
            Chọn mẫu cấu hình sẵn từ các nhà cung cấp phổ biến hoặc tự do tùy chỉnh thông số kết
            nối.
          </DialogDescription>
        </DialogHeader>

        {/* Quick Presets Carousel */}
        {!editingProvider && presets.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
              Mẫu Cấu Hình Sẵn (Presets):
            </span>
            <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto p-1 bg-muted/20 rounded-md border border-border/60">
              {presets.map((preset) => {
                const isSelected = providerType === preset.code;
                return (
                  <button
                    type="button"
                    key={preset.code}
                    onClick={() => applyPreset(preset)}
                    className={`text-[11px] px-2.5 py-1 rounded-md border transition-all flex items-center gap-1.5 ${
                      isSelected
                        ? "bg-primary text-primary-foreground border-primary font-medium shadow-xs"
                        : "bg-background hover:bg-muted text-foreground border-border"
                    }`}
                  >
                    <ProviderIcon code={preset.code} size={15} />
                    <span>{preset.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs pt-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Tên hiển thị *</span>
              <Input
                required
                placeholder="Ví dụ: OpenAI Production..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="text-xs h-9"
              />
            </div>

            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Loại Provider *</span>
              <Select
                value={providerType}
                onValueChange={(val) => setProviderType(val as ModelProvider["type"])}
              >
                <SelectTrigger className="w-full h-9 text-xs">
                  <SelectValue placeholder="Chọn loại Provider" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai">OpenAI (GPT-4o, o1, Embedding)</SelectItem>
                  <SelectItem value="gemini">Google Gemini (Gemini 1.5, 2.0)</SelectItem>
                  <SelectItem value="claude">Anthropic Claude (Claude 3.5)</SelectItem>
                  <SelectItem value="deepseek">DeepSeek (Chat & Reasoner)</SelectItem>
                  <SelectItem value="groq">Groq (Ultra-low latency Llama 3)</SelectItem>
                  <SelectItem value="mistral">Mistral AI (OCR & Mistral Large)</SelectItem>
                  <SelectItem value="cloudflare">Cloudflare Workers AI (Edge GPU)</SelectItem>
                  <SelectItem value="nvidia">NVIDIA NIM (LLM & Vision)</SelectItem>
                  <SelectItem value="ollama">Ollama (Local Models)</SelectItem>
                  <SelectItem value="local_vllm">Local vLLM / HuggingFace</SelectItem>
                  <SelectItem value="sentence_transformers">
                    SentenceTransformers (CPU Cục Bộ)
                  </SelectItem>
                  <SelectItem value="docling">Docling TableFormer (Bóc Tách Cục Bộ)</SelectItem>
                  <SelectItem value="custom">Custom Provider (Tương thích OpenAI)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <span className="font-semibold text-foreground block">Base URL Cổng API</span>
            <Input
              placeholder="VD: https://api.openai.com/v1 (Để trống nếu dùng mặc định)"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              className="text-xs h-9 font-mono"
            />
          </div>

          {providerType === "cloudflare" && (
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Cloudflare Account ID *</span>
              <Input
                required
                placeholder="Nhập Cloudflare Account ID (32 ký tự hex)"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                className="text-xs h-9 font-mono"
              />
            </div>
          )}

          <div className="space-y-1.5">
            <span className="font-semibold text-foreground block">
              {editingProvider
                ? "Khóa API Key Mới (Để trống nếu không đổi)"
                : "API Key Ban Đầu (Có thể bổ sung thêm sau trong Key Pool)"}
            </span>
            <Input
              type="password"
              placeholder={editingProvider ? "••••••••••••••••" : "sk-..."}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="text-xs h-9 font-mono"
            />
          </div>

          {/* Model Tags input */}
          <div className="space-y-1.5">
            <span className="font-semibold text-foreground block">Danh sách mô hình hỗ trợ</span>
            <div className="flex gap-2">
              <Input
                placeholder="Nhập mã model (VD: gpt-4o, gemini-1.5-flash...)"
                value={newModelInput}
                onChange={(e) => setNewModelInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddModelTag();
                  }
                }}
                className="text-xs h-8 font-mono"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddModelTag}
                className="text-xs h-8 shrink-0"
              >
                Thêm
              </Button>
            </div>

            <div className="flex flex-wrap gap-1 pt-1 min-h-[28px]">
              {models.length === 0 ? (
                <span className="text-[11px] text-muted-foreground italic">
                  Chưa có mô hình nào được gán.
                </span>
              ) : (
                models.map((m) => (
                  <Badge key={m} variant="secondary" className="text-[11px] font-mono gap-1 pr-1">
                    <span>{m}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveModelTag(m)}
                      className="hover:text-destructive"
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </Badge>
                ))
              )}
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="isActiveToggle"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary h-4 w-4"
              />
              <label
                htmlFor="isActiveToggle"
                className="font-semibold text-foreground text-xs cursor-pointer"
              >
                Kích hoạt Provider này trong chuỗi xử lý
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              className="text-xs h-8"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!name.trim() || isSaving}
              className="text-xs h-8"
            >
              {isSaving ? "Đang lưu..." : "Lưu Cấu Hình"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
