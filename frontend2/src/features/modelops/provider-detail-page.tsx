import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Cpu, KeyRound } from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { AddCustomModelDialog } from "@/components/modelops/add-custom-model-dialog";
import { KeyPoolSection } from "@/components/modelops/key-pool-section";
import { ModelsGrid } from "@/components/modelops/models-grid";
import { ProviderDetailHeader } from "@/components/modelops/provider-detail-header";
import { ProviderModal } from "@/components/modelops/provider-modal";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  apiClient,
  type ModelProvider,
  type ProviderModelsTestResponse,
  type SingleModelTestResult,
} from "@/services/api-client";

export interface ProviderDetailPageProps {
  providerId: string;
}

export const ProviderDetailPage: React.FC<ProviderDetailPageProps> = ({
  providerId,
}) => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Dialog & Modal States
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isAddModelModalOpen, setIsAddModelModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  // Active Tab in Detail View
  const [activeTab, setActiveTab] = useState<"models" | "keys">("models");

  // Testing status for entire Provider
  const [isTestingProvider, setIsTestingProvider] = useState(false);
  const [testResult, setTestResult] = useState<{
    id: string;
    success: boolean;
    message: string;
  } | null>(null);

  // Copy feedback state
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Testing single key status
  const [testingKeyId, setTestingKeyId] = useState<string | null>(null);
  const [keyTestFeedback, setKeyTestFeedback] = useState<
    Record<string, string>
  >({});

  // Simulating Key Rotation status
  const [simulatingRotation, setSimulatingRotation] = useState(false);
  const [rotationResult, setRotationResult] = useState<{
    success: boolean;
    rotated: boolean;
    message: string;
  } | null>(null);

  // Testing models state
  const [isTestingAllModels, setIsTestingAllModels] = useState(false);
  const [testingModelName, setTestingModelName] = useState<string | null>(null);
  const [modelTestResults, setModelTestResults] = useState<
    Record<string, SingleModelTestResult>
  >({});
  const [modelTestSummary, setModelTestSummary] =
    useState<ProviderModelsTestResponse | null>(null);

  // -------------------------------------------------------------
  // DATA FETCHING & QUERIES
  // -------------------------------------------------------------
  const providersQuery = useQuery({
    queryKey: ["model-providers"],
    queryFn: () => apiClient.getModelProviders(),
  });

  const providers = providersQuery.data || [];
  const selectedProvider = providers.find((p) => p.id === providerId) || null;

  const { data: presets = [] } = useQuery({
    queryKey: ["provider-presets"],
    queryFn: () => apiClient.getProviderPresets(),
  });

  const defaultsQuery = useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
  });
  const systemDefaults = defaultsQuery.data?.defaults;

  const {
    data: providerKeys = [],
    isLoading: loadingKeys,
    refetch: refetchKeys,
  } = useQuery({
    queryKey: ["provider-keys", providerId],
    queryFn: () => apiClient.getProviderKeys(providerId),
    enabled: !!providerId,
  });

  const unavailableModelsCount = useMemo(() => {
    if (!selectedProvider) return 0;
    return (selectedProvider.models || []).filter(
      (m) => modelTestResults[m]?.status === "unavailable",
    ).length;
  }, [selectedProvider, modelTestResults]);

  // -------------------------------------------------------------
  // MUTATIONS
  // -------------------------------------------------------------
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
      setIsEditModalOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteModelProvider(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
      navigate({ to: "/models" });
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
      pId,
      payload,
    }: {
      pId: string;
      payload: Parameters<typeof apiClient.addProviderKey>[1];
    }) => apiClient.addProviderKey(pId, payload),
    onSuccess: () => {
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  const deleteKeyMutation = useMutation({
    mutationFn: ({ pId, keyId }: { pId: string; keyId: string }) =>
      apiClient.deleteProviderKey(pId, keyId),
    onSuccess: () => {
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  const toggleKeyMutation = useMutation({
    mutationFn: ({
      pId,
      keyId,
      isActive,
    }: {
      pId: string;
      keyId: string;
      isActive: boolean;
    }) => apiClient.updateProviderKey(pId, keyId, { is_active: isActive }),
    onSuccess: () => {
      refetchKeys();
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    },
  });

  const setDefaultMutation = useMutation({
    mutationFn: ({
      pId,
      role,
      modelName,
    }: {
      pId: string;
      role: "embedding" | "reranker" | "ocr";
      modelName: string;
    }) => apiClient.setProviderModelAsDefault(pId, role, modelName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system-model-defaults"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-collections"] });
    },
  });

  // -------------------------------------------------------------
  // HANDLERS
  // -------------------------------------------------------------
  const handleBackToList = () => {
    navigate({ to: "/models" });
  };

  const copyToClipboard = (text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  const handleTestConnection = async (id: string) => {
    setIsTestingProvider(true);
    setTestResult(null);
    try {
      const res = await apiClient.testModelProvider(id);
      setTestResult({
        id,
        success: res.success,
        message: `${res.message} (${res.latency_ms} ms)`,
      });
      queryClient.invalidateQueries({ queryKey: ["model-providers"] });
    } catch (err: unknown) {
      const errorObj = err as Error;
      setTestResult({
        id,
        success: false,
        message: errorObj.message || "Lỗi khi kiểm tra kết nối Provider.",
      });
    } finally {
      setIsTestingProvider(false);
    }
  };

  const handleExportSingle = async (
    id: string,
    name: string,
    providerType?: string,
  ) => {
    setIsExporting(true);
    try {
      const data = await apiClient.exportProvider(id, true);
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const safeName = (name || id)
        .toLowerCase()
        .replace(/[^a-z0-9_-]/g, "_")
        .slice(0, 30);
      a.href = url;
      a.download = `qnu_provider_${safeName}_${providerType || "llm"}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      alert("Không thể xuất cấu hình Provider. Vui lòng thử lại!");
    } finally {
      setIsExporting(false);
    }
  };

  const handleTestAllModels = async (pId: string) => {
    setIsTestingAllModels(true);
    setModelTestSummary(null);
    try {
      const res = await apiClient.testProviderModels(pId);
      setModelTestSummary(res);
      const mapped: Record<string, SingleModelTestResult> = {};
      for (const item of res.results || []) {
        mapped[item.model_name] = item;
      }
      setModelTestResults(mapped);
    } catch {
      alert("Lỗi khi kiểm tra tất cả mô hình.");
    } finally {
      setIsTestingAllModels(false);
    }
  };

  const handleTestSingleModel = async (pId: string, modelName: string) => {
    setTestingModelName(modelName);
    try {
      const res = await apiClient.testProviderModels(pId, modelName);
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
      (m) => modelTestResults[m]?.status === "unavailable",
    );
    if (deadModels.length === 0) return;
    const remaining = (provider.models || []).filter(
      (m) => modelTestResults[m]?.status !== "unavailable",
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
          : null,
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

  const handleQuickAddPresetModel = (
    provider: ModelProvider,
    modelName: string,
  ) => {
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
    tResult: SingleModelTestResult | null,
  ) => {
    if (!selectedProvider) return;
    const currentModels = selectedProvider.models || [];
    if (!currentModels.includes(modelId)) {
      const updated = [...currentModels, modelId];
      updateMutation.mutate({
        id: selectedProvider.id,
        payload: { models: updated },
      });
      if (tResult) {
        setModelTestResults((prev) => ({
          ...prev,
          [modelId]: tResult,
        }));
      }
      if (defaultRole !== "none") {
        setDefaultMutation.mutate({
          pId: selectedProvider.id,
          role: defaultRole,
          modelName: modelId,
        });
      }
    }
  };

  const handleSimulateRotation = async (pId: string) => {
    setSimulatingRotation(true);
    setRotationResult(null);
    try {
      const res = await apiClient.simulateKeyRotation(pId, {
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

  const handleTestSingleKey = async (pId: string, keyId: string) => {
    setTestingKeyId(keyId);
    try {
      const res = await apiClient.testProviderKey(pId, keyId);
      setKeyTestFeedback((prev) => ({
        ...prev,
        [keyId]: `${res.message} (${res.latency_ms}ms)`,
      }));
    } catch {
      setKeyTestFeedback((prev) => ({
        ...prev,
        [keyId]: "Lỗi kiểm tra khóa",
      }));
    } finally {
      setTestingKeyId(null);
    }
  };

  // -------------------------------------------------------------
  // RENDER LOADING OR NOT FOUND
  // -------------------------------------------------------------
  if (providersQuery.isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-muted rounded-md" />
        <Card className="h-40 bg-muted/40 border-border" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="h-28 bg-muted/30 border-border" />
          <Card className="h-28 bg-muted/30 border-border" />
          <Card className="h-28 bg-muted/30 border-border" />
        </div>
      </div>
    );
  }

  if (!selectedProvider) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-xs">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBackToList}
            className="h-8 px-2.5 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Danh sách Provider</span>
          </Button>
        </div>
        <EmptyState
          title="Không tìm thấy Provider"
          description={`Không tìm thấy cấu hình Nhà cung cấp với mã định danh "${providerId}". Có thể Provider này đã bị xóa hoặc đường dẫn chưa chính xác.`}
          action={{
            label: "Quay Về Danh Sách Provider",
            onClick: handleBackToList,
          }}
        />
      </div>
    );
  }

  // -------------------------------------------------------------
  // RENDER DETAIL VIEW
  // -------------------------------------------------------------
  return (
    <div className="space-y-6 pb-12">
      {/* 1. Provider Hero Detail Header (Breadcrumbs, Name, Badges, Actions) */}
      <ProviderDetailHeader
        selectedProvider={selectedProvider}
        isTesting={isTestingProvider}
        testResult={testResult}
        copiedUrl={copiedUrl}
        isExporting={isExporting}
        onBackToList={handleBackToList}
        onCopyUrl={copyToClipboard}
        onToggleActive={() => toggleMutation.mutate(selectedProvider.id)}
        onTestConnection={() => handleTestConnection(selectedProvider.id)}
        onExport={() =>
          handleExportSingle(
            selectedProvider.id,
            selectedProvider.name,
            selectedProvider.type,
          )
        }
        onEdit={() => setIsEditModalOpen(true)}
        onDelete={() => setIsDeleteDialogOpen(true)}
      />

      {/* 2. Section Navigation Tabs */}
      <div className="flex items-center gap-1.5 sm:gap-2 border-b border-border pb-2 overflow-x-auto">
        <Button
          variant={activeTab === "models" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("models")}
          className="h-8 px-2.5 sm:px-3 text-xs gap-1.5 rounded-md shrink-0"
        >
          <Cpu className="size-3.5 shrink-0" />
          <span>Mô hình</span>
        </Button>

        <Button
          variant={activeTab === "keys" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("keys")}
          className="h-8 px-2.5 sm:px-3 text-xs gap-1.5 rounded-md shrink-0"
        >
          <KeyRound className="size-3.5 shrink-0" />
          <span>Khóa API</span>
        </Button>
      </div>

      {/* 4. Active Tab Content */}
      {activeTab === "models" && (
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
      )}

      {activeTab === "keys" && (
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
              pId: selectedProvider.id,
              payload,
            })
          }
          onTestSingleKey={handleTestSingleKey}
          onDeleteKey={(pId, keyId) => deleteKeyMutation.mutate({ pId, keyId })}
          onToggleKeyActive={(pId, keyId, isActive) =>
            toggleKeyMutation.mutate({ pId, keyId, isActive })
          }
        />
      )}

      {/* 5. Add Custom Model Dialog */}
      <AddCustomModelDialog
        isOpen={isAddModelModalOpen}
        onClose={() => setIsAddModelModalOpen(false)}
        selectedProvider={selectedProvider}
        presets={presets}
        onConfirmAdd={handleConfirmAddCustomModel}
      />

      {/* 6. Edit Provider Modal */}
      <ProviderModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        editingProvider={selectedProvider}
        presets={presets}
        initialType={selectedProvider.type}
        onSave={(data) => {
          updateMutation.mutate({
            id: selectedProvider.id,
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
        }}
        isSaving={updateMutation.isPending}
      />

      {/* 7. Confirm Delete Dialog */}
      <ConfirmDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        title="Xóa Nhà Cung Cấp Mô Hình"
        description={`Bạn có chắc chắn muốn xóa Provider "${selectedProvider.name}" khỏi hệ thống? Tất cả các khóa API và cấu hình liên kết sẽ bị xóa vĩnh viễn.`}
        confirmLabel="Xác Nhận Xóa"
        confirmVariant="destructive"
        isPending={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate(selectedProvider.id)}
      />
    </div>
  );
};
