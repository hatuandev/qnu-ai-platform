import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Cloud, Cpu, Plus, RefreshCw, Server, SlidersHorizontal } from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { EmptyState } from "../components/admin/empty-state";
import { AddCustomModelDialog } from "../components/modelops/add-custom-model-dialog";
import { KeyPoolSection } from "../components/modelops/key-pool-section";
import {
  type ProviderCategory,
  getProviderCategory,
} from "../components/modelops/modelops-helpers";
import { ModelsGrid } from "../components/modelops/models-grid";
import { ProviderCard } from "../components/modelops/provider-card";
import { ProviderDetailHeader } from "../components/modelops/provider-detail-header";
import { ProviderModal } from "../components/modelops/provider-modal";
import { ResiliencePolicyCard } from "../components/modelops/resilience-policy-card";
import { SystemDefaultsCard } from "../components/modelops/system-defaults-card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import {
  type ModelProvider,
  type ProviderModelsTestResponse,
  type SingleModelTestResult,
  type SystemModelDefaults,
  apiClient,
} from "../services/api-client";

export type { ProviderCategory };
export { getProviderCategory };
export {
  getModelCapabilities,
  getModelDisplayName,
} from "../components/modelops/modelops-helpers";

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

  // Master View Category Filter Tab
  const [activeCategoryTab, setActiveCategoryTab] = useState<ProviderCategory>("all");

  // Dialog State for Provider Create/Edit
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ModelProvider | null>(null);
  const [initialType, setInitialType] = useState<ModelProvider["type"]>("openai");

  // Testing status for entire Provider
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    id: string;
    success: boolean;
    message: string;
  } | null>(null);

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

  // Add Custom Model Dialog state
  const [isAddModelModalOpen, setIsAddModelModalOpen] = useState(false);

  // -------------------------------------------------------------
  // DATA FETCHING & QUERIES
  // -------------------------------------------------------------
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

  const { data: presets = [] } = useQuery({
    queryKey: ["provider-presets"],
    queryFn: () => apiClient.getProviderPresets(),
  });

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

  const selectedProvider = providers.find((p) => p.id === selectedProviderId) || null;

  const unavailableModelsCount = useMemo(() => {
    if (!selectedProvider) return 0;
    return (selectedProvider.models || []).filter(
      (m) => modelTestResults[m]?.status === "unavailable"
    ).length;
  }, [selectedProvider, modelTestResults]);

  // -------------------------------------------------------------
  // MUTATIONS
  // -------------------------------------------------------------
  const createMutation = useMutation({
    mutationFn: (payload: Parameters<typeof apiClient.createModelProvider>[0]) =>
      apiClient.createModelProvider(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
      setIsModalOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Parameters<typeof apiClient.updateModelProvider>[1];
    }) => apiClient.updateModelProvider(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
      setIsModalOpen(false);
      setEditingProvider(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteModelProvider(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
      handleBackToList();
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => apiClient.toggleModelProvider(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  const addKeyMutation = useMutation({
    mutationFn: ({
      providerId,
      payload,
    }: {
      providerId: string;
      payload: Parameters<typeof apiClient.addProviderKey>[1];
    }) => apiClient.addProviderKey(providerId, payload),
    onSuccess: () => {
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  const deleteKeyMutation = useMutation({
    mutationFn: ({ providerId, keyId }: { providerId: string; keyId: string }) =>
      apiClient.deleteProviderKey(providerId, keyId),
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
    }) => apiClient.updateProviderKey(providerId, keyId, { is_active: isActive }),
    onSuccess: () => {
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  // -------------------------------------------------------------
  // HANDLERS
  // -------------------------------------------------------------
  const handleSelectProvider = (providerId: string) => {
    setSelectedProviderId(providerId);
    setTestResult(null);
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

  const openCreateModal = (defaultType: ModelProvider["type"] = "openai") => {
    setEditingProvider(null);
    setInitialType(defaultType);
    setIsModalOpen(true);
  };

  const openEditModal = (provider: ModelProvider) => {
    setEditingProvider(provider);
    setInitialType(provider.type || "openai");
    setIsModalOpen(true);
  };

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
    } catch {
      setTestResult({
        id: providerId,
        success: false,
        message: "Không thể kết nối tới nhà cung cấp. Vui lòng kiểm tra API Key hoặc Base URL.",
      });
    } finally {
      setTestingId(null);
    }
  };

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
    } catch {
      setModelTestSummary(null);
    } finally {
      setIsTestingAllModels(false);
    }
  };

  const handleTestSingleModel = async (providerId: string, modelName: string) => {
    setTestingModelName(modelName);
    try {
      const res = await apiClient.testProviderModels(providerId, modelName);
      if (res.results && res.results.length > 0) {
        setModelTestResults((prev) => ({
          ...prev,
          [modelName]: res.results[0],
        }));
      }
    } catch {
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
            }
          : null
      );
    }
  };

  const handleRemoveModel = (provider: ModelProvider, modelName: string) => {
    const currentModels = provider.models || [];
    const updated = currentModels.filter((m) => m !== modelName);
    updateMutation.mutate({
      id: provider.id,
      payload: { models: updated },
    });
  };

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

  const handleConfirmAddCustomModel = (
    modelId: string,
    _isVision: boolean,
    _isReasoning: boolean,
    defaultRole: "none" | "embedding" | "reranker" | "ocr",
    testResult: SingleModelTestResult | null
  ) => {
    if (!selectedProvider) return;
    const currentModels = selectedProvider.models || [];
    if (!currentModels.includes(modelId)) {
      const updated = [...currentModels, modelId];
      updateMutation.mutate({
        id: selectedProvider.id,
        payload: { models: updated },
      });
      if (testResult) {
        setModelTestResults((prev) => ({
          ...prev,
          [modelId]: testResult,
        }));
      }
      if (defaultRole !== "none") {
        setDefaultMutation.mutate({
          providerId: selectedProvider.id,
          role: defaultRole,
          modelName: modelId,
        });
      }
    }
  };

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

  const copyToClipboard = (text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  // -------------------------------------------------------------
  // DETAIL VIEW (When Provider is selected)
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
            className="h-8 px-2.5 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Quay lại danh sách Provider</span>
          </Button>
          <Card className="p-8 text-center text-xs text-muted-foreground">
            Không tìm thấy Provider với ID &quot;{selectedProviderId}&quot;. Có thể Provider này đã
            bị xóa.
          </Card>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* Provider Detail Header */}
        <ProviderDetailHeader
          selectedProvider={selectedProvider}
          isTesting={testingId === selectedProvider.id}
          testResult={testResult}
          copiedUrl={copiedUrl}
          onBackToList={handleBackToList}
          onCopyUrl={copyToClipboard}
          onToggleActive={() => toggleMutation.mutate(selectedProvider.id)}
          onTestConnection={() => handleTestConnection(selectedProvider.id)}
          onEdit={() => openEditModal(selectedProvider)}
          onDelete={() => {
            if (
              window.confirm(
                `Bạn có chắc chắn muốn xóa Provider '${selectedProvider.name}'? Thao tác này không thể hoàn tác.`
              )
            ) {
              deleteMutation.mutate(selectedProvider.id);
            }
          }}
        />

        {/* Available Models Full-Width Card Grid */}
        <ModelsGrid
          selectedProvider={selectedProvider}
          presets={presets}
          systemDefaults={systemDefaults}
          modelTestResults={modelTestResults}
          modelTestSummary={modelTestSummary}
          unavailableModelsCount={unavailableModelsCount}
          isTestingAllModels={isTestingAllModels}
          testingModelName={testingModelName}
          onOpenAddModelModal={() => setIsAddModelModalOpen(true)}
          onTestAllModels={handleTestAllModels}
          onTestSingleModel={handleTestSingleModel}
          onRemoveModel={handleRemoveModel}
          onCleanUnavailableModels={handleCleanUnavailableModels}
          onQuickAddPresetModel={handleQuickAddPresetModel}
        />

        {/* Key Pool & Specs Section */}
        <KeyPoolSection
          selectedProvider={selectedProvider}
          providerKeys={providerKeys}
          loadingKeys={loadingKeys}
          simulatingRotation={simulatingRotation}
          rotationResult={rotationResult}
          testingKeyId={testingKeyId}
          keyTestFeedback={keyTestFeedback}
          isAddingKey={addKeyMutation.isPending}
          onSimulateRotation={handleSimulateRotation}
          onSaveNewKey={(payload) =>
            addKeyMutation.mutate({
              providerId: selectedProvider.id,
              payload,
            })
          }
          onTestSingleKey={handleTestSingleKey}
          onDeleteKey={(providerId, keyId) => deleteKeyMutation.mutate({ providerId, keyId })}
          onToggleKeyActive={(providerId, keyId, isActive) =>
            toggleKeyMutation.mutate({ providerId, keyId, isActive })
          }
        />

        {/* Add Custom Model Dialog */}
        <AddCustomModelDialog
          isOpen={isAddModelModalOpen}
          onClose={() => setIsAddModelModalOpen(false)}
          selectedProvider={selectedProvider}
          presets={presets}
          onConfirmAdd={handleConfirmAddCustomModel}
        />

        {/* Modal edit provider reuse */}
        <ProviderModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setEditingProvider(null);
          }}
          editingProvider={editingProvider}
          presets={presets}
          initialType={initialType}
          onSave={(data) => {
            if (editingProvider) {
              updateMutation.mutate({
                id: editingProvider.id,
                payload: {
                  name: data.name,
                  provider_type: data.type,
                  api_base_url: data.api_base_url || undefined,
                  api_key: data.api_key || undefined,
                  account_id: data.account_id || undefined,
                  models: data.models,
                  is_active: data.is_active,
                },
              });
            } else {
              createMutation.mutate({
                name: data.name,
                provider_type: data.type,
                api_base_url: data.api_base_url || undefined,
                api_key: data.api_key || undefined,
                account_id: data.account_id || undefined,
                models: data.models,
                is_active: data.is_active,
              });
            }
          }}
          isSaving={createMutation.isPending || updateMutation.isPending}
        />
      </div>
    );
  }

  // -------------------------------------------------------------
  // MASTER LIST VIEW
  // -------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Top Header */}
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
      <SystemDefaultsCard
        systemDefaults={systemDefaults}
        availableEmbeddings={availableEmbeddings}
        availableRerankers={availableRerankers}
        availableOcrs={availableOcrs}
        isLoading={defaultsQuery.isLoading}
        onUpdateDefaults={(payload) => updateDefaultsMutation.mutate(payload)}
      />

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
                      <ProviderCard key={prov.id} provider={prov} onSelect={handleSelectProvider} />
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
                      <ProviderCard key={prov.id} provider={prov} onSelect={handleSelectProvider} />
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
                      <ProviderCard key={prov.id} provider={prov} onSelect={handleSelectProvider} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Resilience & Dynamic Fallback Policy */}
      <ResiliencePolicyCard
        activeProviderNames={providers.filter((p) => p.is_active).map((p) => p.name)}
      />

      {/* Provider Modal (Create / Edit with Presets) */}
      <ProviderModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingProvider(null);
        }}
        editingProvider={editingProvider}
        presets={presets}
        initialType={initialType}
        onSave={(data) => {
          if (editingProvider) {
            updateMutation.mutate({
              id: editingProvider.id,
              payload: {
                name: data.name,
                provider_type: data.type,
                api_base_url: data.api_base_url || undefined,
                api_key: data.api_key || undefined,
                account_id: data.account_id || undefined,
                models: data.models,
                is_active: data.is_active,
              },
            });
          } else {
            createMutation.mutate({
              name: data.name,
              provider_type: data.type,
              api_base_url: data.api_base_url || undefined,
              api_key: data.api_key || undefined,
              account_id: data.account_id || undefined,
              models: data.models,
              is_active: data.is_active,
            });
          }
        }}
        isSaving={createMutation.isPending || updateMutation.isPending}
      />
    </div>
  );
};
