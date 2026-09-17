import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronRight,
  Copy,
  Globe,
  KeyRound,
  Layers,
  Lock,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  RotateCw,
  Server,
  ShieldCheck,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { EmptyState } from "../components/admin/empty-state";
import { ProviderIcon } from "../components/icons/provider-icon";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Switch } from "../components/ui/switch";
import {
  type ModelProvider,
  type ProviderApiKey,
  type ProviderPreset,
  apiClient,
} from "../services/api-client";

export interface ModelOpsPageProps {
  currentPath?: string;
  onNavigate?: (path: string) => void;
}

export const ModelOpsPage: React.FC<ModelOpsPageProps> = ({ currentPath, onNavigate }) => {
  const queryClient = useQueryClient();

  // Selected Provider for Detail View
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(() => {
    if (currentPath?.startsWith("/models/")) {
      const id = currentPath.replace("/models/", "").trim();
      return id || null;
    }
    if (typeof window !== "undefined" && window.location.pathname.startsWith("/models/")) {
      const id = window.location.pathname.replace("/models/", "").trim();
      return id || null;
    }
    return null;
  });

  // Sync selectedProviderId with currentPath prop
  useEffect(() => {
    if (currentPath) {
      if (currentPath.startsWith("/models/")) {
        const id = currentPath.replace("/models/", "").trim();
        setSelectedProviderId(id || null);
      } else if (currentPath === "/models") {
        setSelectedProviderId(null);
      }
    }
  }, [currentPath]);

  // Dialog State for Provider Create/Edit
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ModelProvider | null>(null);

  // Form State for Provider
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState<ModelProvider["type"]>("openai");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [accountId, setAccountId] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [newModelInput, setNewModelInput] = useState("");
  const [isActive, setIsActive] = useState(true);

  // Testing status for entire Provider
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    id: string;
    success: boolean;
    message: string;
  } | null>(null);

  // Key Pool Form State (Adding a new key in detail view)
  const [showAddKeyForm, setShowAddKeyForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeySecret, setNewKeySecret] = useState("");
  const [newKeyPriority, setNewKeyPriority] = useState(1);
  const [newKeyQuota, setNewKeyQuota] = useState("");

  // Testing single key status
  const [testingKeyId, setTestingKeyId] = useState<string | null>(null);
  const [keyTestFeedback, setKeyTestFeedback] = useState<Record<string, string>>({});

  // Simulating Key Rotation status
  const [simulatingRotation, setSimulatingRotation] = useState(false);
  const [rotationResult, setRotationResult] = useState<{
    success: boolean;
    rotated: boolean;
    message: string;
  } | null>(null);

  // Copy feedback state
  const [copiedUrl, setCopiedUrl] = useState(false);

  // Detail View inline model input
  const [detailModelInput, setDetailModelInput] = useState("");

  // Fetch Providers
  const { data: providers = [], isLoading } = useQuery({
    queryKey: ["model-providers"],
    queryFn: () => apiClient.getModelProviders(),
  });

  // Fetch Provider Presets
  const { data: presets = [] } = useQuery({
    queryKey: ["provider-presets"],
    queryFn: () => apiClient.getProviderPresets(),
  });

  // Fetch Keys for Selected Provider in Detail View
  const {
    data: providerKeys = [],
    isLoading: loadingKeys,
    refetch: refetchKeys,
  } = useQuery({
    queryKey: ["provider-keys", selectedProviderId],
    queryFn: () =>
      selectedProviderId ? apiClient.getProviderKeys(selectedProviderId) : Promise.resolve([]),
    enabled: !!selectedProviderId,
  });

  // Identify current selected provider object
  const selectedProvider = providers.find((p) => p.id === selectedProviderId) || null;

  // Navigation handlers
  const handleSelectProvider = (providerId: string) => {
    setSelectedProviderId(providerId);
    setTestResult(null);
    setShowAddKeyForm(false);
    setRotationResult(null);
    setKeyTestFeedback({});
    const nextPath = `/models/${providerId}`;
    if (onNavigate) {
      onNavigate(nextPath);
    } else if (typeof window !== "undefined") {
      window.history.pushState(null, "", nextPath);
    }
  };

  const handleBackToList = () => {
    setSelectedProviderId(null);
    setTestResult(null);
    setShowAddKeyForm(false);
    setRotationResult(null);
    setKeyTestFeedback({});
    const nextPath = "/models";
    if (onNavigate) {
      onNavigate(nextPath);
    } else if (typeof window !== "undefined") {
      window.history.pushState(null, "", nextPath);
    }
  };

  // Provider Mutations
  const createMutation = useMutation({
    mutationFn: (payload: {
      name: string;
      provider_type: string;
      models: string[];
      api_base_url?: string;
      api_key?: string;
      account_id?: string;
      is_active?: boolean;
    }) => apiClient.createModelProvider(payload),
    onSuccess: (newProv) => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
      closeModal();
      if (newProv?.id) {
        handleSelectProvider(newProv.id);
      }
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Partial<{
        name: string;
        provider_type: string;
        models: string[];
        api_base_url?: string;
        api_key?: string;
        account_id?: string;
        is_active?: boolean;
      }>;
    }) => apiClient.updateModelProvider(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
      closeModal();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteModelProvider(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
      if (selectedProviderId) {
        handleBackToList();
      }
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => apiClient.toggleModelProvider(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  // Key Pool Mutations
  const addKeyMutation = useMutation({
    mutationFn: ({
      providerId,
      payload,
    }: {
      providerId: string;
      payload: {
        name: string;
        api_key: string;
        priority: number;
        quota_limit?: number;
      };
    }) => apiClient.addProviderKey(providerId, payload),
    onSuccess: () => {
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
      setNewKeyName("");
      setNewKeySecret("");
      setNewKeyPriority(1);
      setNewKeyQuota("");
      setShowAddKeyForm(false);
    },
  });

  const deleteKeyMutation = useMutation({
    mutationFn: ({
      providerId,
      keyId,
    }: {
      providerId: string;
      keyId: string;
    }) => apiClient.deleteProviderKey(providerId, keyId),
    onSuccess: () => {
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  const toggleKeyMutation = useMutation({
    mutationFn: ({
      providerId,
      keyId,
      isActive,
    }: {
      providerId: string;
      keyId: string;
      isActive: boolean;
    }) => apiClient.toggleProviderKey(providerId, keyId, isActive),
    onSuccess: () => {
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  // Modal Openers
  const openCreateModal = () => {
    setEditingProvider(null);
    setName("");
    setProviderType("openai");
    setApiBaseUrl("");
    setApiKey("");
    setAccountId("");
    setModels([]);
    setNewModelInput("");
    setIsActive(true);
    setIsModalOpen(true);
  };

  const openEditModal = (prov: ModelProvider) => {
    setEditingProvider(prov);
    setName(prov.name);
    setProviderType(prov.type);
    setApiBaseUrl(prov.api_base_url || "");
    setApiKey("");
    setAccountId(prov.account_id || "");
    setModels(prov.models || []);
    setNewModelInput("");
    setIsActive(prov.is_active);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingProvider(null);
  };

  const PRESET_SUGGESTED_MODELS: Record<string, string[]> = {
    openai: ["gpt-4o", "gpt-4o-mini", "o1-mini"],
    gemini: ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
    claude: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
    deepseek: ["deepseek-chat", "deepseek-reasoner"],
    groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    mistral: ["mistral-ocr-latest"],
    cloudflare: ["@cf/baai/bge-m3", "@cf/baai/bge-reranker-base", "@cf/baai/bge-reranker-large"],
    nvidia: ["meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-r1"],
    ollama: ["qwen2.5:7b", "llama3.1:8b", "bge-m3:latest"],
    local_vllm: ["qwen2.5-7b-instruct"],
    openrouter: ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct"],
    sentence_transformers: ["BAAI/bge-m3"],
    docling: ["docling-tableformer-local"],
  };

  // Preset Selection
  const applyPreset = (preset: ProviderPreset) => {
    setProviderType(preset.code as ModelProvider["type"]);
    setName(preset.name);
    if (preset.default_base_url) {
      setApiBaseUrl(preset.default_base_url);
    }
    // Dữ liệu sạch: Không tự động nhồi bất kỳ model nào vào danh sách
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

  const handleSaveProvider = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    if (editingProvider) {
      updateMutation.mutate({
        id: editingProvider.id,
        payload: {
          name,
          provider_type: providerType,
          models,
          api_base_url: apiBaseUrl.trim() || undefined,
          api_key: apiKey.trim() || undefined,
          account_id: accountId.trim() || undefined,
          is_active: isActive,
        },
      });
    } else {
      createMutation.mutate({
        name,
        provider_type: providerType,
        models,
        api_base_url: apiBaseUrl.trim() || undefined,
        api_key: apiKey.trim() || undefined,
        account_id: accountId.trim() || undefined,
        is_active: isActive,
      });
    }
  };

  // Detail View: Add model tag directly
  const handleDetailAddModel = (provider: ModelProvider) => {
    const val = detailModelInput.trim();
    if (!val) return;
    const currentModels = provider.models || [];
    if (!currentModels.includes(val)) {
      const updated = [...currentModels, val];
      updateMutation.mutate({
        id: provider.id,
        payload: { models: updated },
      });
    }
    setDetailModelInput("");
  };

  // Detail View: Remove model tag directly
  const handleDetailRemoveModel = (provider: ModelProvider, modelName: string) => {
    const updated = (provider.models || []).filter((m) => m !== modelName);
    updateMutation.mutate({
      id: provider.id,
      payload: { models: updated },
    });
  };

  // Detail View: Quick add suggested model from Preset
  const handleQuickAddPresetModel = (provider: ModelProvider, modelName: string) => {
    const currentModels = provider.models || [];
    if (!currentModels.includes(modelName)) {
      const updated = [...currentModels, modelName];
      updateMutation.mutate({
        id: provider.id,
        payload: { models: updated },
      });
    }
  };

  // Testing connection for provider
  const handleTestConnection = async (providerId: string) => {
    setTestingId(providerId);
    setTestResult(null);
    try {
      const res = await apiClient.testModelProvider(providerId);
      setTestResult({
        id: providerId,
        success: res.success,
        message: `${res.message} (${res.latency_ms} ms)`,
      });
    } catch (_err) {
      setTestResult({
        id: providerId,
        success: false,
        message: "Không thể kết nối tới nhà cung cấp. Vui lòng kiểm tra API Key hoặc Base URL.",
      });
    } finally {
      setTestingId(null);
    }
  };

  // Testing connection for single key
  const handleTestSingleKey = async (providerId: string, keyId: string) => {
    setTestingKeyId(keyId);
    try {
      const res = await apiClient.testProviderKey(providerId, keyId);
      setKeyTestFeedback((prev) => ({
        ...prev,
        [keyId]: `${res.message} (${res.latency_ms}ms)`,
      }));
    } catch {
      setKeyTestFeedback((prev) => ({
        ...prev,
        [keyId]: "Kiểm tra khóa thất bại.",
      }));
    } finally {
      setTestingKeyId(null);
    }
  };

  // Simulating 429 key rotation failover
  const handleSimulateRotation = async (providerId: string) => {
    setSimulatingRotation(true);
    setRotationResult(null);
    try {
      const res = await apiClient.simulateKeyRotation(providerId, {
        tokens_consumed: 3500,
        trigger_rate_limit: true,
        cooldown_seconds: 60,
      });
      setRotationResult({
        success: res.success,
        rotated: res.rotated,
        message: res.message,
      });
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    } catch (err: unknown) {
      const errorObj = err as Error;
      setRotationResult({
        success: false,
        rotated: false,
        message: errorObj.message || "Mô phỏng xoay vòng thất bại.",
      });
    } finally {
      setSimulatingRotation(false);
    }
  };

  // Add new key handler
  const handleSaveNewKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProvider || !newKeyName.trim() || !newKeySecret.trim()) return;

    addKeyMutation.mutate({
      providerId: selectedProvider.id,
      payload: {
        name: newKeyName.trim(),
        api_key: newKeySecret.trim(),
        priority: newKeyPriority,
        quota_limit: newKeyQuota ? Number.parseInt(newKeyQuota, 10) : undefined,
      },
    });
  };

  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  const copyToClipboard = (text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  const handleCopyKey = (keyId: string, text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedKeyId(keyId);
      setTimeout(() => setCopiedKeyId(null), 2000);
    }
  };

  // Find preset for current provider to get suggested models
  const currentPreset = selectedProvider
    ? presets.find((p) => p.code === selectedProvider.type)
    : null;

  // -------------------------------------------------------------
  // RENDER OVERVIEW VIEW MODAL HELPER
  // -------------------------------------------------------------
  const renderProviderModal = () => (
    <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
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

        <form onSubmit={handleSaveProvider} className="space-y-3.5 text-xs pt-2">
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
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="gemini">Google Gemini</SelectItem>
                  <SelectItem value="claude">Anthropic Claude</SelectItem>
                  <SelectItem value="deepseek">DeepSeek AI</SelectItem>
                  <SelectItem value="groq">Groq Cloud (LPU)</SelectItem>
                  <SelectItem value="openrouter">OpenRouter Gateway</SelectItem>
                  <SelectItem value="mistral">Mistral AI</SelectItem>
                  <SelectItem value="cloudflare">Cloudflare Workers AI</SelectItem>
                  <SelectItem value="nvidia">NVIDIA NIM</SelectItem>
                  <SelectItem value="ollama">Ollama (On-Premise)</SelectItem>
                  <SelectItem value="local_vllm">Local vLLM Server</SelectItem>
                  <SelectItem value="custom">Tùy Chỉnh (OpenAI Compatible)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Special Field: Cloudflare Account ID */}
          {providerType === "cloudflare" && (
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Cloudflare Account ID *</span>
              <Input
                placeholder="b7e5c89a0123456789abcdef01234567"
                value={accountId}
                onChange={(e) => {
                  const idVal = e.target.value.trim();
                  setAccountId(idVal);
                  if (idVal) {
                    setApiBaseUrl(`https://api.cloudflare.com/client/v4/accounts/${idVal}/ai/run`);
                  }
                }}
                className="text-xs h-9 font-mono"
              />
            </div>
          )}

          <div className="space-y-1.5">
            <span className="font-semibold text-foreground block">API Base URL Endpoint</span>
            <Input
              placeholder={
                providerType === "local_vllm" || providerType === "local"
                  ? "http://localhost:8000/v1"
                  : providerType === "ollama"
                    ? "http://localhost:11434/v1"
                    : providerType === "deepseek"
                      ? "https://api.deepseek.com/v1"
                      : providerType === "groq"
                        ? "https://api.groq.com/openai/v1"
                        : providerType === "openrouter"
                          ? "https://openrouter.ai/api/v1"
                          : providerType === "mistral"
                            ? "https://api.mistral.ai/v1"
                            : providerType === "nvidia"
                              ? "https://integrate.api.nvidia.com/v1"
                              : "https://api.openai.com/v1"
              }
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              className="text-xs h-9 font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <span className="font-semibold text-foreground block">
              Khóa API Secret Key {editingProvider ? "(Để trống nếu không đổi)" : "*"}
            </span>
            <div className="relative">
              <Input
                type="password"
                required={!editingProvider}
                placeholder={editingProvider ? "••••••••••••••••" : "sk-..."}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="text-xs h-9 font-mono pr-8"
              />
              <Lock className="h-3.5 w-3.5 absolute right-2.5 top-2.5 text-muted-foreground" />
            </div>
            <span className="text-[10px] text-muted-foreground block">
              Sau khi tạo Provider, bạn có thể bổ sung thêm nhiều khóa API vào nhóm (Key Pool).
            </span>
          </div>

          {/* Model Management */}
          <div className="space-y-1.5 pt-1">
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

            {/* Tags display */}
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
              onClick={closeModal}
              className="text-xs h-8"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!name.trim() || createMutation.isPending || updateMutation.isPending}
              className="text-xs h-8"
            >
              {createMutation.isPending || updateMutation.isPending
                ? "Đang lưu..."
                : "Lưu Cấu Hình"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );

  // -------------------------------------------------------------
  // RENDER DETAIL VIEW (When a Provider is selected)
  // -------------------------------------------------------------
  if (selectedProviderId) {
    if (isLoading) {
      return (
        <div className="p-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-3">
          <RefreshCw className="h-6 w-6 animate-spin text-primary" />
          <span>Đang tải thông tin chi tiết Provider...</span>
        </div>
      );
    }

    if (!selectedProvider) {
      return (
        <div className="space-y-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBackToList}
            className="text-xs gap-1.5 -ml-2 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Quay lại danh sách Provider</span>
          </Button>
          <Card className="p-8 border-dashed border-border bg-card/50">
            <EmptyState
              icon={AlertTriangle}
              title="Không Tìm Thấy Provider"
              description="Nhà cung cấp này có thể đã bị xóa hoặc đường dẫn không hợp lệ."
              action={
                <Button size="sm" onClick={handleBackToList} className="text-xs h-8">
                  Về Danh Sách Provider
                </Button>
              }
            />
          </Card>
        </div>
      );
    }

    const isTesting = testingId === selectedProvider.id;
    const hasTestMsg = testResult && testResult.id === selectedProvider.id;

    return (
      <div className="space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-xs">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBackToList}
              className="h-8 px-2.5 text-xs gap-1.5 text-muted-foreground hover:text-foreground -ml-2"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Quay lại danh sách Nhà cung cấp</span>
            </Button>
            <span className="text-muted-foreground/60">/</span>
            <span className="font-semibold text-foreground flex items-center gap-2">
              <ProviderIcon code={selectedProvider.type} size={18} />
              {selectedProvider.name}
            </span>
          </div>

          <Badge variant="outline" className="font-mono text-xs text-primary border-primary/30">
            Chi Tiết Provider
          </Badge>
        </div>

        {/* Hero Provider Header Card */}
        <Card className="p-6 space-y-4 border-border/80 shadow-xs bg-card">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            {/* Left: Icon, Name, Type, Base URL */}
            <div className="flex items-start gap-3.5 min-w-0">
              <div className="p-2.5 rounded-lg bg-muted/40 border border-border/60 shrink-0 mt-0.5 flex items-center justify-center">
                <ProviderIcon code={selectedProvider.type} size={36} />
              </div>
              <div className="space-y-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-xl font-bold tracking-tight text-foreground">
                    {selectedProvider.name}
                  </h1>
                  <Badge
                    variant="secondary"
                    className="font-mono text-[11px] uppercase tracking-wider"
                  >
                    {selectedProvider.type}
                  </Badge>
                  <Badge
                    variant={selectedProvider.is_active ? "success" : "outline"}
                    className="text-[11px]"
                  >
                    {selectedProvider.is_active ? "Đang Hoạt Động" : "Đang Tạm Dừng"}
                  </Badge>
                </div>

                {selectedProvider.api_base_url ? (
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                    <Globe className="h-3 w-3 text-primary shrink-0" />
                    <span className="truncate max-w-md">{selectedProvider.api_base_url}</span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(selectedProvider.api_base_url || "")}
                      className="p-1 hover:text-foreground rounded transition-colors"
                      title="Sao chép URL"
                    >
                      {copiedUrl ? (
                        <Check className="h-3 w-3 text-success" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Sử dụng endpoint mặc định của nhà cung cấp
                  </p>
                )}
              </div>
            </div>

            {/* Right: Controls & Actions */}
            <div className="flex flex-wrap items-center gap-2.5 shrink-0 pt-2 lg:pt-0 border-t lg:border-t-0 border-border/60">
              {/* Toggle Switch */}
              <div className="flex items-center gap-2 bg-muted/40 px-3 py-1.5 rounded-md border border-border">
                <span className="text-xs font-medium text-foreground">
                  {selectedProvider.is_active ? "Bật Hoạt Động" : "Tạm Dừng"}
                </span>
                <Switch
                  checked={selectedProvider.is_active}
                  onCheckedChange={() => toggleMutation.mutate(selectedProvider.id)}
                  aria-label="Bật hoặc tắt Provider"
                />
              </div>

              {/* Ping Connection Button */}
              <Button
                variant="outline"
                size="sm"
                disabled={isTesting}
                onClick={() => handleTestConnection(selectedProvider.id)}
                className="h-9 text-xs gap-1.5"
              >
                {isTesting ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin text-primary" />
                ) : (
                  <Play className="h-3.5 w-3.5 text-primary" />
                )}
                <span>{isTesting ? "Đang kiểm tra..." : "Test Kết Nối"}</span>
              </Button>

              {/* Edit Provider Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => openEditModal(selectedProvider)}
                className="h-9 text-xs gap-1.5"
              >
                <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                <span>Chỉnh Sửa</span>
              </Button>

              {/* Delete Provider Button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (
                    window.confirm(
                      `Bạn có chắc chắn muốn xóa Provider '${selectedProvider.name}'? Thao tác này không thể hoàn tác.`
                    )
                  ) {
                    deleteMutation.mutate(selectedProvider.id);
                  }
                }}
                className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                title="Xóa Provider"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Test Connection Result Alert Banner */}
          {hasTestMsg && (
            <div
              className={`p-3 rounded-md text-xs flex items-center gap-2 ${
                testResult.success
                  ? "bg-success/10 text-success border border-success/30"
                  : "bg-destructive/10 text-destructive border border-destructive/30"
              }`}
            >
              {testResult.success ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <AlertTriangle className="h-4 w-4 shrink-0" />
              )}
              <span className="leading-relaxed font-medium">{testResult.message}</span>
            </div>
          )}
        </Card>

        {/* Main Content Grid: Left 2/3 Key Pool, Right 1/3 Models & Specs */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* LEFT 2 COLS: KEY POOL & ROTATION FAILOVER */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="p-5 space-y-4 border-border">
              {/* Header Key Pool */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/70">
                <div>
                  <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                    <Layers className="h-4 w-4 text-primary" />
                    Nhóm Khóa API (Key Pool)
                    <Badge variant="outline" className="font-mono text-xs">
                      {providerKeys.length} Keys
                    </Badge>
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Hỗ trợ nạp nhiều API key, tự động xoay vòng khi chạm Rate Limit 429 hoặc cạn
                    Token Quota.
                  </p>
                </div>

                {/* Toolbar Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={simulatingRotation || providerKeys.length <= 1}
                    onClick={() => handleSimulateRotation(selectedProvider.id)}
                    className="h-8 text-xs gap-1.5"
                    title="Mô phỏng sự cố 429 trên khóa hiện tại để kiểm tra cơ chế nhảy khóa tự động"
                  >
                    <Zap
                      className={`h-3.5 w-3.5 text-warning ${simulatingRotation ? "animate-spin" : ""}`}
                    />
                    <span>{simulatingRotation ? "Đang test..." : "Test 429 Failover"}</span>
                  </Button>

                  <Button
                    size="sm"
                    onClick={() => setShowAddKeyForm(!showAddKeyForm)}
                    className="h-8 text-xs gap-1.5"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>{showAddKeyForm ? "Đóng Form" : "Thêm Khóa Mới"}</span>
                  </Button>
                </div>
              </div>

              {/* Simulation Result Alert */}
              {rotationResult && (
                <div
                  className={`p-3 rounded-md text-xs flex items-start gap-2.5 ${
                    rotationResult.rotated
                      ? "bg-warning/10 text-warning border border-warning/30"
                      : rotationResult.success
                        ? "bg-success/10 text-success border border-success/30"
                        : "bg-destructive/10 text-destructive border border-destructive/30"
                  }`}
                >
                  <Zap className="h-4 w-4 shrink-0 mt-0.5" />
                  <div>
                    <strong className="block font-semibold">
                      {rotationResult.rotated
                        ? "⚡ Tự Động Xoay Khóa Thành Công!"
                        : "Thông Báo Xử Lý Token"}
                    </strong>
                    <span className="leading-relaxed">{rotationResult.message}</span>
                  </div>
                </div>
              )}

              {/* Add New Key Form Card */}
              {showAddKeyForm && (
                <form
                  onSubmit={handleSaveNewKey}
                  className="p-4 bg-muted/30 rounded-md border border-border space-y-3.5"
                >
                  <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                    <KeyRound className="h-3.5 w-3.5 text-primary" />
                    Thêm Khóa API Mới Vào Nhóm
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-foreground block">
                        Tên nhãn gợi nhớ *
                      </span>
                      <Input
                        required
                        placeholder="VD: Key Khoa CNTT 2, Free Tier B..."
                        value={newKeyName}
                        onChange={(e) => setNewKeyName(e.target.value)}
                        className="h-8 text-xs"
                      />
                    </div>

                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-foreground block">
                        Mã khóa Secret Key *
                      </span>
                      <Input
                        required
                        type="password"
                        placeholder="sk-proj-..."
                        value={newKeySecret}
                        onChange={(e) => setNewKeySecret(e.target.value)}
                        className="h-8 text-xs font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-foreground block">
                        Độ ưu tiên (Priority)
                      </span>
                      <Input
                        type="number"
                        min={1}
                        max={99}
                        value={newKeyPriority}
                        onChange={(e) =>
                          setNewKeyPriority(Number.parseInt(e.target.value, 10) || 1)
                        }
                        className="h-8 text-xs"
                      />
                      <span className="text-[10px] text-muted-foreground block">
                        1 = Ưu tiên cao nhất (được sử dụng trước)
                      </span>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-foreground block">
                        Hạn mức Token (Quota Limit)
                      </span>
                      <Input
                        type="number"
                        placeholder="Để trống = Không giới hạn quota"
                        value={newKeyQuota}
                        onChange={(e) => setNewKeyQuota(e.target.value)}
                        className="h-8 text-xs"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-1 border-t border-border/60">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAddKeyForm(false)}
                      className="h-8 text-xs"
                    >
                      Hủy
                    </Button>
                    <Button
                      type="submit"
                      size="sm"
                      disabled={
                        !newKeyName.trim() || !newKeySecret.trim() || addKeyMutation.isPending
                      }
                      className="h-8 text-xs"
                    >
                      {addKeyMutation.isPending ? "Đang lưu..." : "Lưu Khóa Vào Nhóm"}
                    </Button>
                  </div>
                </form>
              )}

              {/* Keys List */}
              <div className="space-y-3">
                {loadingKeys ? (
                  <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                    <RefreshCw className="h-4 w-4 animate-spin text-primary" />
                    <span>Đang tải danh sách khóa API...</span>
                  </div>
                ) : providerKeys.length === 0 ? (
                  <div className="p-8 text-center text-xs text-muted-foreground border border-dashed rounded-md space-y-2">
                    <p className="font-medium text-foreground">Chưa có khóa API nào trong nhóm.</p>
                    <p className="text-muted-foreground">
                      Bấm nút &quot;Thêm Khóa Mới&quot; ở trên để thiết lập khóa đầu tiên cho
                      Provider này.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {providerKeys.map((keyItem: ProviderApiKey) => {
                      const isKeyTesting = testingKeyId === keyItem.id;
                      const testFeedback = keyTestFeedback[keyItem.id];
                      const hasQuota = keyItem.quota_limit && keyItem.quota_limit > 0;
                      const quotaLimit = keyItem.quota_limit || 1;
                      const pct = hasQuota
                        ? Math.min(100, Math.round((keyItem.usage_tokens / quotaLimit) * 100))
                        : 0;

                      return (
                        <div
                          key={keyItem.id}
                          className={`p-3.5 rounded-md border transition-all space-y-2.5 ${
                            keyItem.status === "rate_limited"
                              ? "bg-warning/5 border-warning/40"
                              : keyItem.is_active
                                ? "bg-card border-border hover:border-border/80"
                                : "bg-muted/20 border-dashed opacity-60"
                          }`}
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            {/* Key Identity */}
                            <div className="flex items-center gap-2.5 min-w-0 flex-wrap">
                              <span
                                className="font-mono text-[11px] font-bold px-1.5 py-0.5 rounded bg-muted border border-border text-foreground"
                                title="Độ ưu tiên sử dụng"
                              >
                                #{keyItem.priority}
                              </span>
                              <span className="font-semibold text-xs text-foreground">
                                {keyItem.name}
                              </span>
                              <div className="flex items-center gap-1.5 bg-muted/60 px-2 py-0.5 rounded border border-border/70">
                                <code className="text-xs font-mono font-medium text-foreground tracking-wide select-all">
                                  {keyItem.api_key_masked}
                                </code>
                                <button
                                  type="button"
                                  onClick={() => handleCopyKey(keyItem.id, keyItem.api_key_masked)}
                                  className="p-0.5 text-muted-foreground hover:text-foreground rounded transition-colors"
                                  title="Sao chép mã khóa"
                                >
                                  {copiedKeyId === keyItem.id ? (
                                    <Check className="h-3 w-3 text-success" />
                                  ) : (
                                    <Copy className="h-3 w-3" />
                                  )}
                                </button>
                              </div>
                            </div>

                            {/* Status Badge & Actions */}
                            <div className="flex items-center gap-2 shrink-0">
                              {keyItem.status === "rate_limited" ? (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] bg-warning/10 text-warning border-warning/30 flex items-center gap-1"
                                >
                                  <RotateCw className="h-2.5 w-2.5 animate-spin" />
                                  <span>Cooldown 429</span>
                                </Badge>
                              ) : keyItem.status === "exhausted" ? (
                                <Badge variant="destructive" className="text-[10px]">
                                  Hết Quota
                                </Badge>
                              ) : keyItem.is_active ? (
                                <Badge variant="success" className="text-[10px]">
                                  Sẵn Sàng
                                </Badge>
                              ) : (
                                <Badge variant="secondary" className="text-[10px]">
                                  Đã Tắt
                                </Badge>
                              )}

                              {/* Toggle switch for individual key */}
                              <Switch
                                checked={keyItem.is_active}
                                onCheckedChange={(checked) =>
                                  toggleKeyMutation.mutate({
                                    providerId: selectedProvider.id,
                                    keyId: keyItem.id,
                                    isActive: checked,
                                  })
                                }
                                aria-label={`Bật hoặc tắt khóa ${keyItem.name}`}
                              />
                            </div>
                          </div>

                          {/* Usage & Quota Bar */}
                          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                            <span>
                              Đã dùng:{" "}
                              <strong className="text-foreground font-mono">
                                {keyItem.usage_tokens.toLocaleString()}
                              </strong>{" "}
                              {hasQuota
                                ? `/ ${keyItem.quota_limit?.toLocaleString()} tokens (${pct}%)`
                                : "tokens (không giới hạn)"}
                            </span>
                            {keyItem.last_used_at && (
                              <span className="text-[10px]">
                                Lần dùng cuối:{" "}
                                {new Date(keyItem.last_used_at).toLocaleTimeString("vi-VN")}
                              </span>
                            )}
                          </div>

                          {hasQuota && (
                            <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                              <div
                                className={`h-full transition-all ${
                                  pct > 90
                                    ? "bg-destructive"
                                    : pct > 70
                                      ? "bg-warning"
                                      : "bg-primary"
                                }`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          )}

                          {/* Test Feedback Banner */}
                          {testFeedback && (
                            <div className="text-[11px] text-primary p-2 bg-primary/5 rounded border border-primary/20">
                              {testFeedback}
                            </div>
                          )}

                          {/* Action Toolbar */}
                          <div className="flex items-center justify-between border-t border-border/50 pt-2 text-xs">
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={isKeyTesting}
                              onClick={() => handleTestSingleKey(selectedProvider.id, keyItem.id)}
                              className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                            >
                              <Play className="h-3 w-3 text-primary" />
                              <span>{isKeyTesting ? "Đang kiểm tra..." : "Test Khóa Này"}</span>
                            </Button>

                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                if (window.confirm(`Xóa khóa '${keyItem.name}' khỏi nhóm?`)) {
                                  deleteKeyMutation.mutate({
                                    providerId: selectedProvider.id,
                                    keyId: keyItem.id,
                                  });
                                }
                              }}
                              className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive gap-1"
                              title="Xóa khóa khỏi nhóm"
                            >
                              <Trash2 className="h-3 w-3" />
                              <span>Xóa</span>
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </Card>

            {/* Resilience Policy Info Card */}
            <Card className="p-5 space-y-3 bg-muted/10 border-border/70">
              <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-primary" />
                Cơ Chế Điều Phối JIT Key Failover & Fallback
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Khi thực hiện suy luận LLM, Gateway sẽ tự động chọn khóa khả dụng có độ ưu tiên cao
                nhất (#1). Nếu khóa đó gặp lỗi{" "}
                <code className="text-warning">HTTP 429 Too Many Requests</code> hoặc chạm hạn ngạch
                token, hệ thống lập tức chuyển sang khóa dự phòng kế tiếp và đưa khóa cũ vào trạng
                thái Cooldown trong 60 giây mà không làm gián đoạn trải nghiệm người dùng.
              </p>
            </Card>
          </div>

          {/* RIGHT 1 COL: MODELS & SPECIFICATIONS */}
          <div className="space-y-6">
            {/* Models Card */}
            <Card className="p-5 space-y-4 border-border">
              <div className="flex items-center justify-between pb-2 border-b border-border/70">
                <div>
                  <h3 className="text-sm font-bold text-foreground">Mô Hình Khả Dụng</h3>
                  <p className="text-xs text-muted-foreground">
                    {(selectedProvider.models || []).length} mô hình đã cấu hình
                  </p>
                </div>
              </div>

              {/* Models Tags */}
              <div className="space-y-2">
                <div className="flex flex-wrap gap-1.5 min-h-[32px]">
                  {(selectedProvider.models || []).length === 0 ? (
                    <div className="w-full text-center py-4 text-xs text-muted-foreground italic border border-dashed rounded-md">
                      Chưa cấu hình mô hình nào. Hãy nhập tên model ở ô bên dưới hoặc bấm vào gợi ý.
                    </div>
                  ) : (
                    (selectedProvider.models || []).map((m) => (
                      <Badge
                        key={m}
                        variant="outline"
                        className="text-xs font-mono bg-background gap-1.5 py-1 px-2.5 border-border"
                      >
                        <span>{m}</span>
                        <button
                          type="button"
                          onClick={() => handleDetailRemoveModel(selectedProvider, m)}
                          className="text-muted-foreground hover:text-destructive transition-colors"
                          title={`Xóa model ${m}`}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))
                  )}
                </div>

                {/* Add model input */}
                <div className="flex items-center gap-1.5 pt-2">
                  <Input
                    placeholder="Ví dụ: gpt-4o, gemini-1.5-flash..."
                    value={detailModelInput}
                    onChange={(e) => setDetailModelInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleDetailAddModel(selectedProvider);
                      }
                    }}
                    className="h-8 text-xs font-mono"
                  />
                  <Button
                    size="sm"
                    onClick={() => handleDetailAddModel(selectedProvider)}
                    className="h-8 px-3 text-xs"
                    disabled={!detailModelInput.trim()}
                  >
                    Thêm
                  </Button>
                </div>
              </div>

              {/* Quick Suggest from Presets */}
              {(() => {
                const suggestedList =
                  currentPreset?.suggested_models ||
                  PRESET_SUGGESTED_MODELS[selectedProvider.type] ||
                  [];
                if (suggestedList.length === 0) return null;
                return (
                  <div className="pt-2 border-t border-border/60 space-y-2">
                    <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                      Gợi Ý 1-Click Thêm Nhanh ({selectedProvider.name}):
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {suggestedList.map((sm) => {
                        const isAlreadyAdded = (selectedProvider.models || []).includes(sm);
                        return (
                          <button
                            type="button"
                            key={sm}
                            disabled={isAlreadyAdded}
                            onClick={() => handleQuickAddPresetModel(selectedProvider, sm)}
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
                );
              })()}
            </Card>

            {/* Provider Technical Specs Card */}
            <Card className="p-5 space-y-3 border-border">
              <h3 className="text-sm font-bold text-foreground">Thông Số Kỹ Thuật</h3>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">ID:</span>
                  <span className="text-foreground truncate max-w-[150px]">
                    {selectedProvider.id}
                  </span>
                </div>
                {selectedProvider.type === "cloudflare" && (
                  <div className="flex justify-between py-1 border-b border-border/50">
                    <span className="text-muted-foreground">Account ID:</span>
                    <span className="text-foreground truncate max-w-[150px] font-mono">
                      {selectedProvider.account_id || "(Chưa cấu hình)"}
                    </span>
                  </div>
                )}
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Giao thức:</span>
                  <span className="text-foreground uppercase">{selectedProvider.type}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Trạng thái:</span>
                  <span
                    className={
                      selectedProvider.is_active ? "text-success" : "text-muted-foreground"
                    }
                  >
                    {selectedProvider.is_active ? "Kích Hoạt (Active)" : "Tạm Ngừng"}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Tổng Keys:</span>
                  <span className="text-foreground font-bold">{providerKeys.length}</span>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Modal edit provider reuse */}
        {renderProviderModal()}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Quản Lý Provider
            <Badge variant="outline" className="font-mono text-xs text-primary border-primary/30">
              ModelOps
            </Badge>
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Quản lý các nhà cung cấp mô hình LLM, nhóm khóa API xoay vòng (Key Pool), và chính sách
            phục hồi dự phòng.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button size="sm" onClick={openCreateModal} className="text-xs h-8 gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            <span>Thêm Provider Mới</span>
          </Button>
        </div>
      </div>

      {/* Overview Cards Grid - Minimalist & Clean Design */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
            <RefreshCw className="h-4 w-4 animate-spin text-primary" />
            <span>Đang tải danh sách nhà cung cấp...</span>
          </div>
        ) : providers.length === 0 ? (
          <Card className="p-8 border-dashed border-border bg-card/50">
            <EmptyState
              icon={Server}
              title="Chưa Có Provider Nào Được Cấu Hình"
              description="Hệ thống đang ở trạng thái dữ liệu sạch. Bắt đầu bằng việc thêm nhà cung cấp LLM mới theo nhu cầu thực tế của đơn vị."
              action={
                <Button size="sm" onClick={openCreateModal} className="text-xs h-8 gap-1.5">
                  <Plus className="h-3.5 w-3.5" />
                  <span>Thêm Provider Mới</span>
                </Button>
              }
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {providers.map((prov) => {
              return (
                <Card
                  key={prov.id}
                  onClick={() => handleSelectProvider(prov.id)}
                  className="group p-4 transition-all flex items-center justify-between cursor-pointer hover:border-primary/70 hover:shadow-md hover:-translate-y-0.5 bg-card border border-border"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="w-11 h-11 rounded-lg bg-muted/40 p-2 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform border border-border/50">
                      <ProviderIcon code={prov.type || prov.code} size={30} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="font-bold text-sm text-foreground truncate group-hover:text-primary transition-colors">
                        {prov.name}
                      </h3>
                      <span className="text-[11px] font-mono text-muted-foreground uppercase mt-0.5 block">
                        {prov.type}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Resilience & Dynamic Fallback Policy */}
      <div className="space-y-3.5">
        <h2 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Chính Sách Chuyển Vùng Dự Phòng (Dynamic Fallback & Key Rotation)
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-4 space-y-2">
            <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-primary" />
              Cơ Chế JIT Key Failover Trong Nhóm (Key Pool)
            </h4>
            <div className="p-3 rounded-md bg-muted/40 border border-border/80 text-xs space-y-1 font-mono">
              <p className="text-foreground">
                Tự động chuyển khóa:{" "}
                <span className="text-primary font-bold">Priority #1 → #2 → #3</span>
              </p>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Khi một khóa chạm Rate Limit HTTP 429 hoặc cạn Token Quota, hệ thống lập tức chuyển
              sang khóa dự phòng kế tiếp và đưa khóa cũ vào thời gian nghỉ (Cooldown 60s).
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-info" />
              Chuyển Vùng Nhà Cung Cấp Fallback (Circuit Breaker)
            </h4>
            <div className="p-3 rounded-md bg-muted/40 border border-border/80 text-xs space-y-1 font-mono">
              <p className="text-foreground">
                Thứ tự Provider:{" "}
                <span className="text-primary font-bold">
                  {providers
                    .filter((p) => p.is_active)
                    .map((p) => p.name)
                    .join(" → ") || "Chưa có provider kích hoạt"}
                </span>
              </p>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Nếu toàn bộ khóa trong nhóm của nhà cung cấp chính đều kiệt sức hoặc lỗi mạng quá 15
              giây, Circuit Breaker sẽ nhảy sang Provider dự phòng kế tiếp.
            </p>
          </Card>
        </div>
      </div>

      {/* Provider Modal (Create / Edit with Presets) */}
      {renderProviderModal()}
    </div>
  );
};
