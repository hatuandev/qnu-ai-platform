import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  Brain,
  Check,
  CheckCircle2,
  ChevronRight,
  Cloud,
  Copy,
  Cpu,
  Eye,
  FlaskConical,
  Globe,
  KeyRound,
  Layers,
  Loader2,
  Lock,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  RotateCw,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Star,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
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
  type ProviderModelsTestResponse,
  type ProviderPreset,
  type SingleModelTestResult,
  type SystemModelDefaults,
  apiClient,
} from "../services/api-client";

export type ProviderCategory = "all" | "cloud" | "local" | "custom";

export const getProviderCategory = (prov: ModelProvider): "cloud" | "local" | "custom" => {
  const t = (prov.type || prov.code || "").toLowerCase();
  if (t === "custom") return "custom";
  if (
    t === "sentence_transformers" ||
    t === "docling" ||
    t === "ollama" ||
    t === "local_vllm" ||
    t === "local" ||
    prov.id.includes("local") ||
    prov.id.includes("sentence_transformers") ||
    prov.id.includes("docling") ||
    prov.name.toLowerCase().includes("local") ||
    prov.name.toLowerCase().includes("cục bộ")
  ) {
    return "local";
  }
  return "cloud";
};

export const getModelCapabilities = (modelName: string) => {
  const mLower = modelName.toLowerCase();
  const hasVision =
    mLower.includes("vision") ||
    mLower.includes("flash") ||
    mLower.includes("4o") ||
    mLower.includes("sonnet") ||
    mLower.includes("opus") ||
    mLower.includes("ocr") ||
    mLower.includes("docling");
  const hasReasoning =
    mLower.includes("reason") ||
    mLower.includes("o1") ||
    mLower.includes("o3") ||
    mLower.includes("r1") ||
    mLower.includes("thinking") ||
    mLower.includes("pro") ||
    mLower.includes("high");
  return { hasVision, hasReasoning };
};

export const getModelDisplayName = (modelName: string): string => {
  if (modelName.startsWith("@cf/")) {
    return modelName.replace("@cf/", "").toUpperCase();
  }
  const clean = modelName.replace(/^ag\//, "").replace(/-\d{8}$/, "");
  return clean
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
};

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

  // Category Filter Tab ("all" | "cloud" | "local" | "custom")
  const [activeCategoryTab, setActiveCategoryTab] = useState<ProviderCategory>("all");

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

  // Testing models state
  const [isTestingAllModels, setIsTestingAllModels] = useState(false);
  const [testingModelName, setTestingModelName] = useState<string | null>(null);
  const [modelTestResults, setModelTestResults] = useState<Record<string, SingleModelTestResult>>(
    {}
  );
  const [modelTestSummary, setModelTestSummary] = useState<ProviderModelsTestResponse | null>(null);

  // Add Custom Model Dialog state (Image 2 style)
  const [isAddModelModalOpen, setIsAddModelModalOpen] = useState(false);
  const [newCustomModelId, setNewCustomModelId] = useState("");
  const [isVisionCapable, setIsVisionCapable] = useState(false);
  const [isReasoningCapable, setIsReasoningCapable] = useState(false);
  const [testingNewModel, setTestingNewModel] = useState(false);
  const [newModelTestResult, setNewModelTestResult] = useState<SingleModelTestResult | null>(null);
  const [modelRoleDefault, setModelRoleDefault] = useState<
    "none" | "embedding" | "reranker" | "ocr"
  >("none");

  // Filter & Copy feedback
  const [modelFilter, setModelFilter] = useState<"all" | "vision" | "reasoning" | "default">("all");
  const [copiedModelId, setCopiedModelId] = useState<string | null>(null);

  // Fetch Providers
  const providersQuery = useQuery({
    queryKey: ["model-providers"],
    queryFn: () => apiClient.getModelProviders(),
  });

  const providers = providersQuery.data || [];
  const isLoading = providersQuery.isLoading;

  const cloudProviders = useMemo(
    () => providers.filter((p) => getProviderCategory(p) === "cloud"),
    [providers]
  );
  const localProviders = useMemo(
    () => providers.filter((p) => getProviderCategory(p) === "local"),
    [providers]
  );
  const customProviders = useMemo(
    () => providers.filter((p) => getProviderCategory(p) === "custom"),
    [providers]
  );

  // Fetch System Model Routing Defaults
  const defaultsQuery = useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
  });
  const systemDefaults = defaultsQuery.data?.defaults;
  const availableEmbeddings = defaultsQuery.data?.available_embeddings || [];
  const availableRerankers = defaultsQuery.data?.available_rerankers || [];
  const availableOcrs = defaultsQuery.data?.available_ocrs || [];

  const updateDefaultsMutation = useMutation({
    mutationFn: (payload: Partial<SystemModelDefaults>) =>
      apiClient.updateSystemModelDefaults(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system-model-defaults"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-collections"] });
    },
  });

  const setDefaultMutation = useMutation({
    mutationFn: ({
      providerId,
      role,
      modelName,
    }: {
      providerId: string;
      role: "embedding" | "reranker" | "ocr";
      modelName: string;
    }) => apiClient.setProviderModelAsDefault(providerId, role, modelName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system-model-defaults"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-collections"] });
    },
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

  // Count unavailable models
  const unavailableModelsCount = useMemo(() => {
    if (!selectedProvider) return 0;
    return (selectedProvider.models || []).filter(
      (m) => modelTestResults[m]?.status === "unavailable"
    ).length;
  }, [selectedProvider, modelTestResults]);

  // Filtered models for Available Models Grid
  const filteredModels = useMemo(() => {
    const allM = selectedProvider?.models || [];
    if (modelFilter === "all") return allM;
    if (modelFilter === "vision") {
      return allM.filter((m) => getModelCapabilities(m).hasVision);
    }
    if (modelFilter === "reasoning") {
      return allM.filter((m) => getModelCapabilities(m).hasReasoning);
    }
    if (modelFilter === "default") {
      return allM.filter(
        (m) =>
          (selectedProvider?.id === systemDefaults?.default_embedding_provider_id &&
            m === systemDefaults?.default_embedding_model) ||
          (selectedProvider?.id === systemDefaults?.default_reranker_provider_id &&
            m === systemDefaults?.default_reranker_model) ||
          (selectedProvider?.id === systemDefaults?.default_ocr_provider_id &&
            m === systemDefaults?.default_ocr_model)
      );
    }
    return allM;
  }, [selectedProvider, modelFilter, systemDefaults]);

  // Navigation handlers
  const handleSelectProvider = (providerId: string) => {
    setSelectedProviderId(providerId);
    setTestResult(null);
    setShowAddKeyForm(false);
    setRotationResult(null);
    setKeyTestFeedback({});
    setModelTestResults({});
    setModelTestSummary(null);
    setIsTestingAllModels(false);
    setTestingModelName(null);
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
    setModelTestResults({});
    setModelTestSummary(null);
    setIsTestingAllModels(false);
    setTestingModelName(null);
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
  const openCreateModal = (defaultType: ModelProvider["type"] = "openai") => {
    setEditingProvider(null);
    setName("");
    setProviderType(defaultType);
    setApiBaseUrl(defaultType === "custom" ? "http://localhost:8000/v1" : "");
    setApiKey("");
    setAccountId("");
    setModels(PRESET_SUGGESTED_MODELS[defaultType] || []);
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

  // Testing all models for provider
  const handleTestAllModels = async (providerId: string) => {
    setIsTestingAllModels(true);
    try {
      const res = await apiClient.testProviderModels(providerId);
      setModelTestSummary(res);
      const resultMap: Record<string, SingleModelTestResult> = {};
      for (const r of res.results) {
        resultMap[r.model_name] = r;
      }
      setModelTestResults(resultMap);
    } catch (_err) {
      setModelTestSummary(null);
    } finally {
      setIsTestingAllModels(false);
    }
  };

  // Testing single model
  const handleTestSingleModel = async (providerId: string, modelName: string) => {
    setTestingModelName(modelName);
    try {
      const res = await apiClient.testProviderModels(providerId, modelName);
      if (res.results && res.results.length > 0) {
        const r = res.results[0];
        setModelTestResults((prev) => ({
          ...prev,
          [modelName]: r,
        }));
      }
    } catch (_err) {
      setModelTestResults((prev) => ({
        ...prev,
        [modelName]: {
          model_name: modelName,
          success: false,
          status: "error",
          latency_ms: 0,
          message: "Lỗi mạng hoặc không thể gửi request kiểm tra",
          tested_at: new Date().toISOString(),
        },
      }));
    } finally {
      setTestingModelName(null);
    }
  };

  // 1-Click clean dead / unavailable models from provider
  const handleCleanUnavailableModels = (provider: ModelProvider) => {
    const deadModels = (provider.models || []).filter(
      (m) => modelTestResults[m]?.status === "unavailable"
    );
    if (deadModels.length === 0) return;
    const remaining = (provider.models || []).filter(
      (m) => modelTestResults[m]?.status !== "unavailable"
    );
    updateMutation.mutate({
      id: provider.id,
      payload: { models: remaining },
    });
    setModelTestResults((prev) => {
      const copy = { ...prev };
      for (const d of deadModels) {
        delete copy[d];
      }
      return copy;
    });
    if (modelTestSummary) {
      setModelTestSummary((prev) =>
        prev
          ? {
              ...prev,
              total_models: remaining.length,
              unavailable_models: 0,
              results: prev.results.filter((r) => r.status !== "unavailable"),
            }
          : null
      );
    }
  };

  // Add Model Modal handlers (Image 2 style)
  const handleOpenAddModelModal = (prefillId = "") => {
    setNewCustomModelId(prefillId);
    const lower = prefillId.toLowerCase();
    setIsVisionCapable(
      lower.includes("flash") ||
        lower.includes("vision") ||
        lower.includes("4o") ||
        lower.includes("sonnet") ||
        lower.includes("ocr")
    );
    setIsReasoningCapable(
      lower.includes("o1") ||
        lower.includes("o3") ||
        lower.includes("reason") ||
        lower.includes("r1") ||
        lower.includes("thinking")
    );
    setNewModelTestResult(null);
    setModelRoleDefault("none");
    setIsAddModelModalOpen(true);
  };

  const handleCloseAddModelModal = () => {
    setIsAddModelModalOpen(false);
    setNewCustomModelId("");
    setNewModelTestResult(null);
    setTestingNewModel(false);
  };

  const handleTestNewModel = async () => {
    if (!selectedProvider || !newCustomModelId.trim()) return;
    setTestingNewModel(true);
    setNewModelTestResult(null);
    try {
      const res = await apiClient.testProviderModels(selectedProvider.id, newCustomModelId.trim());
      if (res.results && res.results.length > 0) {
        setNewModelTestResult(res.results[0]);
      }
    } catch (_err) {
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

  const handleConfirmAddCustomModel = () => {
    if (!selectedProvider) return;
    const trimmed = newCustomModelId.trim();
    if (!trimmed) return;
    const currentModels = selectedProvider.models || [];
    if (!currentModels.includes(trimmed)) {
      const updated = [...currentModels, trimmed];
      updateMutation.mutate({
        id: selectedProvider.id,
        payload: { models: updated },
      });
      if (newModelTestResult) {
        setModelTestResults((prev) => ({
          ...prev,
          [trimmed]: newModelTestResult,
        }));
      }
      if (modelRoleDefault !== "none") {
        setDefaultMutation.mutate({
          providerId: selectedProvider.id,
          role: modelRoleDefault,
          modelName: trimmed,
        });
      }
    }
    handleCloseAddModelModal();
  };

  const handleCopyModelId = (id: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(id);
      setCopiedModelId(id);
      setTimeout(() => setCopiedModelId(null), 1500);
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
                  <SelectItem value="sentence_transformers">
                    Local SentenceTransformers (PyTorch)
                  </SelectItem>
                  <SelectItem value="docling">Docling Local (IBM Research)</SelectItem>
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
                  {(() => {
                    const cat = getProviderCategory(selectedProvider);
                    if (cat === "cloud") {
                      return (
                        <Badge
                          variant="outline"
                          className="text-[11px] font-mono text-sky-600 dark:text-sky-400 border-sky-500/30 gap-1"
                        >
                          <Cloud className="h-3 w-3" />
                          Cloud
                        </Badge>
                      );
                    }
                    if (cat === "local") {
                      return (
                        <Badge
                          variant="outline"
                          className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 border-emerald-500/30 gap-1"
                        >
                          <Cpu className="h-3 w-3" />
                          Local
                        </Badge>
                      );
                    }
                    return (
                      <Badge
                        variant="outline"
                        className="text-[11px] font-mono text-amber-600 dark:text-amber-400 border-amber-500/30 gap-1"
                      >
                        <SlidersHorizontal className="h-3 w-3" />
                        Custom
                      </Badge>
                    );
                  })()}
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

        {/* Available Models Full-Width Card (Style of User Reference Image 1) */}
        <Card className="p-6 space-y-5 border-border shadow-xs bg-card">
          {/* Header with Title, Count badge, Capabilities Filter, and Action Buttons */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/70">
            <div className="flex items-center gap-2.5">
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <Bot className="h-4 w-4 text-primary" />
                Mô Hình Khả Dụng (Available Models)
              </h2>
              <Badge variant="outline" className="font-mono text-xs text-primary border-primary/30">
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
                    setModelFilter(val as "all" | "vision" | "reasoning" | "default")
                  }
                >
                  <SelectTrigger className="h-8 w-44 text-xs font-medium">
                    <SelectValue placeholder="Tất cả mô hình" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tất cả mô hình</SelectItem>
                    <SelectItem value="vision">Vision (Thị giác)</SelectItem>
                    <SelectItem value="reasoning">Reasoning (Suy luận)</SelectItem>
                    <SelectItem value="default">Mặc định hệ thống</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Add Custom Model Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleOpenAddModelModal()}
                className="h-8 px-3 text-xs gap-1.5 text-primary border-primary/30 hover:bg-primary/10 cursor-pointer"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Thêm Model</span>
              </Button>

              {/* Bulk Test Button */}
              <Button
                variant="outline"
                size="sm"
                disabled={isTestingAllModels || (selectedProvider.models || []).length === 0}
                onClick={() => handleTestAllModels(selectedProvider.id)}
                className="h-8 px-3 text-xs text-primary border-primary/30 hover:bg-primary/10 gap-1.5 cursor-pointer"
                title="Gửi ping kiểm tra tính khả dụng thực tế của toàn bộ các model này"
              >
                {isTestingAllModels ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Zap className="h-3.5 w-3.5" />
                )}
                <span>{isTestingAllModels ? "Đang Kiểm Tra..." : "Test Tất Cả"}</span>
              </Button>
            </div>
          </div>

          {/* Model Cards Grid (3 Columns on Desktop) */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filteredModels.length === 0 && (selectedProvider.models || []).length > 0 ? (
              <div className="col-span-full py-8 text-center text-xs text-muted-foreground italic border border-dashed rounded-lg">
                Không tìm thấy model nào phù hợp với bộ lọc đã chọn.
              </div>
            ) : null}

            {filteredModels.map((m) => {
              const isDefEmbedding =
                selectedProvider.id === systemDefaults?.default_embedding_provider_id &&
                m === systemDefaults?.default_embedding_model;
              const isDefReranker =
                selectedProvider.id === systemDefaults?.default_reranker_provider_id &&
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
                  {/* Left Robot Icon */}
                  <div className="p-2 rounded-md bg-muted/60 border border-border/50 text-primary shrink-0 flex items-center justify-center">
                    <Bot className="h-4 w-4" />
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

                      {isDefEmbedding && (
                        <Badge
                          variant="secondary"
                          className="text-[9px] px-1 py-0 h-3.5 bg-primary/20 text-primary border-none gap-0.5"
                        >
                          <Star className="h-2.5 w-2.5 fill-primary" />
                          Embed
                        </Badge>
                      )}
                      {isDefReranker && (
                        <Badge
                          variant="secondary"
                          className="text-[9px] px-1 py-0 h-3.5 bg-amber-500/20 text-amber-500 border-none gap-0.5"
                        >
                          <Star className="h-2.5 w-2.5 fill-amber-500" />
                          Rerank
                        </Badge>
                      )}
                      {isDefOcr && (
                        <Badge
                          variant="secondary"
                          className="text-[9px] px-1 py-0 h-3.5 bg-sky-500/20 text-sky-500 border-none gap-0.5"
                        >
                          <Star className="h-2.5 w-2.5 fill-sky-500" />
                          OCR
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span className="truncate max-w-[130px] italic">{displayName}</span>
                      <div className="flex items-center gap-1 text-muted-foreground/70 shrink-0">
                        {capabilities.hasVision && (
                          <span title="Hỗ trợ Vision / Đa phương thức">
                            <Eye className="h-3 w-3" />
                          </span>
                        )}
                        {capabilities.hasReasoning && (
                          <span title="Hỗ trợ Suy luận chuyên sâu (Reasoning)">
                            <Brain className="h-3 w-3" />
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
                      ) : testRes.status === "unavailable" ? (
                        <span
                          className="inline-flex items-center gap-1 text-[10px] text-destructive bg-destructive/10 px-1.5 py-0.5 rounded font-sans border border-destructive/30"
                          title={`Hết hiệu lực: ${testRes.message}`}
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
                      onClick={() => handleTestSingleModel(selectedProvider.id, m)}
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
                      onClick={() => handleDetailRemoveModel(selectedProvider, m)}
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
              onClick={() => handleOpenAddModelModal()}
              className="border-2 border-dashed border-primary/30 hover:border-primary hover:bg-primary/5 rounded-lg p-3.5 flex items-center justify-center gap-2 text-primary font-medium text-xs transition-all cursor-pointer min-h-[58px]"
              title="Thêm mô hình tùy chỉnh mới vào Provider"
            >
              <Plus className="h-4 w-4" />
              <span>Thêm Mô Hình (Add Model)</span>
            </button>
          </div>

          {/* Dead Models Cleanup Alert */}
          {unavailableModelsCount > 0 && (
            <div className="flex items-center justify-between p-3 rounded-md bg-destructive/10 border border-destructive/30 text-xs">
              <div className="flex items-center gap-2 text-destructive font-medium">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>
                  Phát hiện <strong>{unavailableModelsCount}</strong> model không còn hiệu lực do
                  nhà cung cấp ngừng cung cấp (HTTP 404).
                </span>
              </div>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => handleCleanUnavailableModels(selectedProvider)}
                className="h-7 px-2.5 text-xs gap-1 cursor-pointer"
                title="Tự động loại bỏ các model không còn hỗ trợ khỏi cấu hình Provider"
              >
                <Trash2 className="h-3 w-3" />
                <span>Dọn Dẹp Model Lỗi</span>
              </Button>
            </div>
          )}

          {/* Test Success Summary Banner */}
          {modelTestSummary && unavailableModelsCount === 0 && (
            <div className="flex items-center gap-2 p-2.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>
                Đã kiểm tra <strong>{modelTestSummary.total_models}</strong> model: Toàn bộ{" "}
                <strong>{modelTestSummary.available_models}</strong> model đều đang hoạt động tốt!
              </span>
            </div>
          )}

          {/* Quick Suggest from Presets */}
          {(() => {
            const currentPreset = presets.find((pr) => pr.code === selectedProvider.type);
            const suggestedList =
              currentPreset?.suggested_models ||
              PRESET_SUGGESTED_MODELS[selectedProvider.type] ||
              [];
            if (suggestedList.length === 0) return null;
            return (
              <div className="pt-3 border-t border-border/60 space-y-2">
                <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                  Gợi Ý 1-Click Thêm Nhanh ({selectedProvider.name}):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {suggestedList.map((sm) => {
                    const isAlreadyAdded = (selectedProvider.models || []).includes(sm);
                    return (
                      <button
                        type="button"
                        key={sm}
                        disabled={isAlreadyAdded}
                        onClick={() => handleQuickAddPresetModel(selectedProvider, sm)}
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
            );
          })()}
        </Card>

        {/* Main Content Grid: Left 2/3 Key Pool, Right 1/3 Specs */}
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

          {/* RIGHT 1 COL: SPECIFICATIONS */}
          <div className="space-y-6">
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

        {/* Add Custom Model Dialog (User Reference Image 2 Style) */}
        <Dialog open={isAddModelModalOpen} onOpenChange={setIsAddModelModalOpen}>
          <DialogContent className="sm:max-w-md p-6 space-y-5 rounded-lg bg-card border-border shadow-lg">
            <div className="space-y-2">
              {/* Mac-style window controls dots */}
              <div className="flex items-center gap-1.5 mb-1">
                <span className="h-2.5 w-2.5 rounded-full bg-destructive/80 inline-block" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80 inline-block" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80 inline-block" />
              </div>
              <DialogTitle className="text-base font-bold text-foreground">
                Thêm Mô Hình Tùy Chỉnh (Add Custom Model)
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Nhập mã định danh model do {selectedProvider?.name} cung cấp và kiểm thử tính khả
                dụng trực tiếp.
              </DialogDescription>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-foreground block">
                Mã Định Danh Model (Model ID)
              </span>
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Ví dụ: gemini-2.0-flash, gpt-4o, claude-3-5-sonnet..."
                  value={newCustomModelId}
                  onChange={(e) => {
                    setNewCustomModelId(e.target.value);
                    setNewModelTestResult(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleConfirmAddCustomModel();
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
                >
                  {testingNewModel ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <FlaskConical className="h-3.5 w-3.5" />
                  )}
                  <span>{testingNewModel ? "Đang Test..." : "Test"}</span>
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground font-mono">
                Gửi tới nhà cung cấp dưới dạng:{" "}
                <code className="text-foreground bg-muted/60 px-1 py-0.5 rounded font-mono">
                  {newCustomModelId.trim() || "model-id"}
                </code>
              </p>

              {newModelTestResult && (
                <div
                  className={`p-2.5 rounded-md text-xs border flex items-center justify-between ${
                    newModelTestResult.status === "available"
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400"
                      : newModelTestResult.status === "rate_limited"
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400"
                        : "bg-destructive/10 border-destructive/30 text-destructive"
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    {newModelTestResult.status === "available" ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                    )}
                    <span>{newModelTestResult.message}</span>
                  </div>
                  {newModelTestResult.latency_ms > 0 && (
                    <span className="font-mono font-semibold text-[11px]">
                      {newModelTestResult.latency_ms}ms
                    </span>
                  )}
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
                    <p className="text-[10px] text-muted-foreground">Hỗ trợ ảnh & OCR</p>
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
                    <p className="text-[10px] text-muted-foreground">Suy luận tư duy</p>
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
            {(() => {
              if (!selectedProvider) return null;
              const currentPreset = presets.find((pr) => pr.code === selectedProvider.type);
              const suggestedList =
                currentPreset?.suggested_models ||
                PRESET_SUGGESTED_MODELS[selectedProvider.type] ||
                [];
              if (suggestedList.length === 0) return null;
              return (
                <div className="space-y-1.5 pt-2 border-t border-border/60">
                  <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                    Gợi ý nhanh từ {selectedProvider.name}:
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {suggestedList.map((sm) => {
                      const isAlreadyAdded = (selectedProvider.models || []).includes(sm);
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
                                lower.includes("ocr")
                            );
                            setIsReasoningCapable(
                              lower.includes("o1") ||
                                lower.includes("o3") ||
                                lower.includes("reason") ||
                                lower.includes("r1") ||
                                lower.includes("thinking")
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
              );
            })()}

            {/* Dialog Footer Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/60">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleCloseAddModelModal}
                className="h-9 px-4 text-xs cursor-pointer"
              >
                Hủy
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={
                  !newCustomModelId.trim() ||
                  (selectedProvider?.models || []).includes(newCustomModelId.trim())
                }
                onClick={handleConfirmAddCustomModel}
                className="h-9 px-4 text-xs cursor-pointer"
              >
                Thêm Mô Hình
              </Button>
            </div>
          </DialogContent>
        </Dialog>

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
          <Button
            size="sm"
            onClick={() => openCreateModal("openai")}
            className="text-xs h-8 gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Thêm Provider Mới</span>
          </Button>
        </div>
      </div>

      {/* System Default Routing Card */}
      <Card className="p-4 border-primary/20 bg-gradient-to-r from-card via-card to-primary/5 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-2.5">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" />
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
                Tự động áp dụng khi nạp tài liệu vào Kho Tri Thức (Embedding) và khi Trợ lý AI thực
                hiện truy xuất thông tin (Reranker).
              </p>
            </div>
          </div>
          {defaultsQuery.isLoading && (
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-primary shrink-0" />
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          {/* 1. Default Embedding */}
          <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 text-primary" />
                Embedding (Kho Tri Thức)
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
                  updateDefaultsMutation.mutate({
                    default_embedding_provider_id: pId,
                    default_embedding_model: mName,
                  });
                }
              }}
            >
              <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
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
                ? "⚡ Đang dùng Cloudflare Edge GPU (~1.0s / 16 chunks)"
                : "💻 Đang dùng SentenceTransformers CPU Cục Bộ"}
            </p>
          </div>

          {/* 2. Default Reranker */}
          <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5 text-amber-500" />
                Reranker (Truy Xuất RAG)
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
                  updateDefaultsMutation.mutate({
                    default_reranker_provider_id: pId,
                    default_reranker_model: mName,
                  });
                }
              }}
            >
              <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
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
                ? "⚡ Đang dùng Cloudflare BGE-Reranker-Base (~1.2s)"
                : "💻 Đang dùng thuật toán RRF Fused Scoring nội bộ"}
            </p>
          </div>

          {/* 3. Default OCR */}
          <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-sky-500" />
                OCR (Bóc Tách Văn Bản)
              </span>
              <Badge variant="secondary" className="text-[10px] font-mono">
                Vision / OCR
              </Badge>
            </div>
            <Select
              value={`${systemDefaults?.default_ocr_provider_id}:::${systemDefaults?.default_ocr_model}`}
              onValueChange={(val) => {
                const [pId, mName] = val.split(":::");
                if (pId && mName) {
                  updateDefaultsMutation.mutate({
                    default_ocr_provider_id: pId,
                    default_ocr_model: mName,
                  });
                }
              }}
            >
              <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
                <SelectValue placeholder="Chọn mô hình OCR mặc định" />
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
            <p className="text-[10px] text-muted-foreground">
              {systemDefaults?.default_ocr_provider_id === "prov_mistral"
                ? "🌐 Đang dùng Mistral OCR Cloud Vision"
                : "💻 Đang dùng Docling TableFormer Cục Bộ"}
            </p>
          </div>
        </div>
      </Card>

      {/* Category Tabs / Filters */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3">
        <Button
          variant={activeCategoryTab === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveCategoryTab("all")}
          className="h-8 text-xs gap-1.5 rounded-full"
        >
          <span>Tất Cả</span>
          <Badge
            variant="secondary"
            className="ml-0.5 text-[10px] px-1.5 py-0 h-4 bg-background/30 text-inherit border-none"
          >
            {providers.length}
          </Badge>
        </Button>

        <Button
          variant={activeCategoryTab === "cloud" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveCategoryTab("cloud")}
          className="h-8 text-xs gap-1.5 rounded-full"
        >
          <Cloud className="h-3.5 w-3.5" />
          <span>Cloud (Đám Mây)</span>
          <Badge
            variant="secondary"
            className="ml-0.5 text-[10px] px-1.5 py-0 h-4 bg-background/30 text-inherit border-none"
          >
            {cloudProviders.length}
          </Badge>
        </Button>

        <Button
          variant={activeCategoryTab === "local" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveCategoryTab("local")}
          className="h-8 text-xs gap-1.5 rounded-full"
        >
          <Cpu className="h-3.5 w-3.5" />
          <span>Local (Cục Bộ)</span>
          <Badge
            variant="secondary"
            className="ml-0.5 text-[10px] px-1.5 py-0 h-4 bg-background/30 text-inherit border-none"
          >
            {localProviders.length}
          </Badge>
        </Button>

        <Button
          variant={activeCategoryTab === "custom" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveCategoryTab("custom")}
          className="h-8 text-xs gap-1.5 rounded-full"
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          <span>Custom (Tùy Chỉnh)</span>
          <Badge
            variant="secondary"
            className="ml-0.5 text-[10px] px-1.5 py-0 h-4 bg-background/30 text-inherit border-none"
          >
            {customProviders.length}
          </Badge>
        </Button>
      </div>

      {/* Grouped Provider Sections */}
      <div className="space-y-8">
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
                <Button
                  size="sm"
                  onClick={() => openCreateModal("openai")}
                  className="text-xs h-8 gap-1.5"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Thêm Provider Mới</span>
                </Button>
              }
            />
          </Card>
        ) : (
          <>
            {/* Nhóm Cloud */}
            {(activeCategoryTab === "all" || activeCategoryTab === "cloud") && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-sky-500/10 text-sky-500">
                      <Cloud className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-sm font-bold text-foreground">Nhóm Cloud (Đám Mây)</h2>
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono text-sky-600 dark:text-sky-400 border-sky-500/30"
                        >
                          {cloudProviders.length} Provider{cloudProviders.length !== 1 ? "s" : ""}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        Nhà cung cấp dịch vụ mô hình AI và Edge GPU vận hành trên nền tảng đám mây
                        (Cloudflare, Mistral, OpenAI, Gemini...)
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openCreateModal("cloudflare")}
                    className="h-7 text-xs text-muted-foreground hover:text-primary gap-1"
                  >
                    <Plus className="h-3 w-3" />
                    <span>Thêm Cloud</span>
                  </Button>
                </div>

                {cloudProviders.length === 0 ? (
                  <Card className="p-6 border-dashed border-border bg-card/40 text-center">
                    <p className="text-xs text-muted-foreground">Chưa có Provider đám mây nào.</p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {cloudProviders.map((prov) => (
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
                            <div className="flex items-center gap-1.5">
                              <h3 className="font-bold text-sm text-foreground truncate group-hover:text-primary transition-colors">
                                {prov.name}
                              </h3>
                              {!prov.is_active && (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] px-1.5 py-0 h-4 text-muted-foreground border-muted-foreground/30 font-mono shrink-0"
                                >
                                  Tắt
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[11px] font-mono text-muted-foreground uppercase">
                                {prov.type}
                              </span>
                              {prov.models && prov.models.length > 0 && (
                                <span className="text-[10px] text-muted-foreground/70 font-mono truncate">
                                  • {prov.models.length} model{prov.models.length > 1 ? "s" : ""}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Nhóm Local */}
            {(activeCategoryTab === "all" || activeCategoryTab === "local") && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-emerald-500/10 text-emerald-500">
                      <Cpu className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-sm font-bold text-foreground">
                          Nhóm Local (Cục Bộ / On-Premise)
                        </h2>
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                        >
                          {localProviders.length} Provider{localProviders.length !== 1 ? "s" : ""}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        Mô hình AI bóc tách và tính toán chạy trực tiếp trên máy chủ nội bộ ĐH Quy
                        Nhơn (SentenceTransformers BGE-M3, Docling OCR, Ollama...)
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openCreateModal("ollama")}
                    className="h-7 text-xs text-muted-foreground hover:text-primary gap-1"
                  >
                    <Plus className="h-3 w-3" />
                    <span>Thêm Local</span>
                  </Button>
                </div>

                {localProviders.length === 0 ? (
                  <Card className="p-6 border-dashed border-border bg-card/40 text-center">
                    <p className="text-xs text-muted-foreground">Chưa có Provider cục bộ nào.</p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {localProviders.map((prov) => (
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
                            <div className="flex items-center gap-1.5">
                              <h3 className="font-bold text-sm text-foreground truncate group-hover:text-primary transition-colors">
                                {prov.name}
                              </h3>
                              {!prov.is_active && (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] px-1.5 py-0 h-4 text-muted-foreground border-muted-foreground/30 font-mono shrink-0"
                                >
                                  Tắt
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[11px] font-mono text-muted-foreground uppercase">
                                {prov.type}
                              </span>
                              {prov.models && prov.models.length > 0 && (
                                <span className="text-[10px] text-muted-foreground/70 font-mono truncate">
                                  • {prov.models.length} model{prov.models.length > 1 ? "s" : ""}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Nhóm Custom */}
            {(activeCategoryTab === "all" || activeCategoryTab === "custom") && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-amber-500/10 text-amber-500">
                      <SlidersHorizontal className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-sm font-bold text-foreground">
                          Nhóm Custom (Tùy Chỉnh / Tự Cấu Hình)
                        </h2>
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono text-amber-600 dark:text-amber-400 border-amber-500/30"
                        >
                          {customProviders.length} Provider{customProviders.length !== 1 ? "s" : ""}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        Cổng API tùy chỉnh tương thích giao thức OpenAI API (vLLM, TGI, LocalAI,
                        FastAPI tự phát triển...)
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openCreateModal("custom")}
                    className="h-7 text-xs text-muted-foreground hover:text-primary gap-1"
                  >
                    <Plus className="h-3 w-3" />
                    <span>Thêm Custom</span>
                  </Button>
                </div>

                {customProviders.length === 0 ? (
                  <Card className="p-5 border-dashed border-border/80 bg-card/30 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-md bg-muted flex items-center justify-center text-muted-foreground shrink-0">
                        <SlidersHorizontal className="h-4 w-4" />
                      </div>
                      <div className="text-xs">
                        <p className="font-medium text-foreground">
                          Chưa có Provider tùy chỉnh nào
                        </p>
                        <p className="text-muted-foreground text-[11px]">
                          Thêm endpoint riêng để kết nối mô hình chuyên biệt hoặc máy chủ tự host
                          của phòng ban.
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openCreateModal("custom")}
                      className="h-8 text-xs gap-1.5 shrink-0"
                    >
                      <Plus className="h-3 w-3" />
                      <span>Thêm Custom Provider</span>
                    </Button>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {customProviders.map((prov) => (
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
                            <div className="flex items-center gap-1.5">
                              <h3 className="font-bold text-sm text-foreground truncate group-hover:text-primary transition-colors">
                                {prov.name}
                              </h3>
                              {!prov.is_active && (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] px-1.5 py-0 h-4 text-muted-foreground border-muted-foreground/30 font-mono shrink-0"
                                >
                                  Tắt
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[11px] font-mono text-muted-foreground uppercase">
                                {prov.type}
                              </span>
                              {prov.models && prov.models.length > 0 && (
                                <span className="text-[10px] text-muted-foreground/70 font-mono truncate">
                                  • {prov.models.length} model{prov.models.length > 1 ? "s" : ""}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
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
