import { AssistantHeader } from "@/components/assistants/assistant-header";
import {
  type AssistantSubView,
  AssistantWorkspaceNav,
} from "@/components/assistants/assistant-workspace-nav";
import { AssistantCloneDialog } from "@/components/assistants/dialogs/assistant-clone-dialog";
import { AssistantEmbedDialog } from "@/components/assistants/dialogs/assistant-embed-dialog";
import { AssistantVersionHistoryDialog } from "@/components/assistants/dialogs/assistant-version-history-dialog";
import { AssistantDangerZone } from "@/components/assistants/sections/assistant-danger-zone";
import { AssistantGuardrailsSection } from "@/components/assistants/sections/assistant-guardrails-section";
import { AssistantKnowledgeSection } from "@/components/assistants/sections/assistant-knowledge-section";
import { AssistantModelSection } from "@/components/assistants/sections/assistant-model-section";
import { AssistantPersonaSection } from "@/components/assistants/sections/assistant-persona-section";
import { AssistantToolsSection } from "@/components/assistants/sections/assistant-tools-section";
import type { AssistantEditForm } from "@/components/assistants/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ChannelsPage } from "@/pages/channels-page";
import { ChatStudioPage } from "@/pages/chat-studio-page";
import { DAGCanvasPage } from "@/pages/dag-canvas-page";
import { EvaluationPage } from "@/pages/evaluation-page";
import { RunsPage } from "@/pages/runs-page";
import { type AssistantItem, apiClient } from "@/services/api-client";
import {
  activateAssistant,
  cloneAssistant,
  deactivateAssistant,
  exportAssistantBundle,
  forkAssistantWorkflow,
  generateAssistantSpec,
  getAssistant,
  getAssistantReadiness,
  getAssistantVersions,
  publishAssistant,
  rollbackAssistantVersion,
  updateAssistant,
} from "@/services/assistants-api";
import { modelopsApi } from "@/services/modelops-api";
import { workflowsApi } from "@/services/workflows-api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

interface AssistantDetailPageProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  subView?: AssistantSubView;
  assistantId?: string;
}

function getReferenceFromPath(currentPath: string): string {
  const parts = currentPath.split("/").filter(Boolean);
  const assistantsIndex = parts.indexOf("assistants");
  if (assistantsIndex !== -1 && parts[assistantsIndex + 1]) {
    return decodeURIComponent(parts[assistantsIndex + 1]);
  }
  return decodeURIComponent(parts.at(-1) ?? "");
}

function toEditForm(item: AssistantItem): AssistantEditForm {
  const cfg = item.config;
  const questions =
    Array.isArray(item.sample_questions) && item.sample_questions.length > 0
      ? item.sample_questions
      : Array.isArray(cfg.sample_questions) && cfg.sample_questions.length > 0
        ? cfg.sample_questions
        : [];
  return {
    name: item.name,
    description: item.description,
    category: item.category,
    system_prompt: item.system_prompt,
    workflow_id: item.workflow_id,
    collection_id: item.collection_id,
    sample_questions: questions.map((q, idx) => ({
      id: `sq-${idx}-${Date.now().toString(36)}`,
      text: q,
    })),
    primary_model: cfg.model_policy.primary_model || "gpt-4o-mini",
    fallback_model: cfg.model_policy.fallback_model || "gemini-1.5-flash",
    temperature: cfg.model_policy.temperature ?? 0.2,
    max_tokens: cfg.model_policy.max_tokens ?? 1200,
    thinking_budget: cfg.model_policy.thinking_budget ?? 0,
    block_prompt_injection: cfg.guardrails.block_prompt_injection ?? true,
    mask_pii: cfg.guardrails.mask_pii ?? true,
    require_grounded_answer: cfg.guardrails.require_grounded_answer ?? true,
    protect_system_prompt: cfg.guardrails.protect_system_prompt ?? true,
    human_approval_required: cfg.tools.human_approval_required ?? true,
    require_citations: cfg.output_policy.require_citations ?? true,
    no_answer_message:
      cfg.guardrails.no_answer_message ||
      "Thông tin này chưa có trong nguồn chính thức. Vui lòng liên hệ đơn vị phụ trách để được hỗ trợ.",
  };
}

function downloadBundle(filename: string, bundle: object) {
  const content = JSON.stringify(bundle, null, 2);
  const blob = new Blob([content], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function AssistantDetailPage({
  currentPath,
  onNavigate,
  subView = "overview",
  assistantId,
}: AssistantDetailPageProps) {
  const reference = assistantId || getReferenceFromPath(currentPath);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AssistantEditForm | null>(null);
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [isEmbedOpen, setIsEmbedOpen] = useState(false);
  const [isCloneOpen, setIsCloneOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const assistantQuery = useQuery({
    queryKey: ["assistants", reference],
    queryFn: () => getAssistant(reference),
    enabled: Boolean(reference),
  });

  const collectionsQuery = useQuery({
    queryKey: ["knowledge-collections"],
    queryFn: () => apiClient.getCollections(),
  });

  const workflowsQuery = useQuery({
    queryKey: ["workflow-definitions"],
    queryFn: () => workflowsApi.listDefinitions(),
  });

  const providersQuery = useQuery({
    queryKey: ["modelops", "providers"],
    queryFn: () => modelopsApi.getModelProviders(),
  });

  const availableModels = useMemo(() => {
    const providers = providersQuery.data ?? [];
    const list: { value: string; label: string; providerName: string }[] = [];
    const seen = new Set<string>();
    for (const prov of providers) {
      if (!prov.is_active) continue;
      for (const m of prov.models ?? []) {
        if (!seen.has(m)) {
          seen.add(m);
          list.push({
            value: m,
            label: `${m} (${prov.name})`,
            providerName: prov.name,
          });
        }
      }
    }
    return list;
  }, [providersQuery.data]);

  useEffect(() => {
    if (assistantQuery.data) {
      setForm(toEditForm(assistantQuery.data));
    }
  }, [assistantQuery.data]);

  const updateMutation = useMutation({
    mutationFn: async (value: AssistantEditForm) => {
      const current = assistantQuery.data;
      if (!current) throw new Error("Không có dữ liệu trợ lý để cập nhật.");
      return updateAssistant(reference, {
        name: value.name,
        description: value.description,
        category: value.category,
        system_prompt: value.system_prompt,
        workflow_id: value.workflow_id,
        collection_id: value.collection_id,
        config: {
          ...current.config,
          sample_questions: value.sample_questions
            .map((q) => q.text.trim())
            .filter((t) => t.length > 0),
          model_policy: {
            ...current.config.model_policy,
            primary_model: value.primary_model,
            fallback_model: value.fallback_model,
            temperature: value.temperature,
            max_tokens: value.max_tokens,
            thinking_budget: value.thinking_budget ?? 0,
          },
          guardrails: {
            ...current.config.guardrails,
            block_prompt_injection: value.block_prompt_injection,
            mask_pii: value.mask_pii,
            require_grounded_answer: value.require_grounded_answer,
            protect_system_prompt: value.protect_system_prompt,
            no_answer_message: value.no_answer_message,
          },
          tools: {
            ...current.config.tools,
            human_approval_required: value.human_approval_required,
          },
          output_policy: {
            ...current.config.output_policy,
            require_citations: value.require_citations,
          },
        },
      });
    },
    onSuccess: (assistant) => {
      queryClient.setQueryData(["assistants", reference], assistant);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      queryClient.invalidateQueries({ queryKey: ["assistant-readiness", reference] });
      queryClient.invalidateQueries({ queryKey: ["assistant-readiness", assistant.code] });
      setForm(toEditForm(assistant));
      toast.success("Đã lưu thay đổi cấu hình thành công!", {
        description: `Các thiết lập của "${assistant.name}" đã được cập nhật vào hệ thống.`,
      });
    },
    onError: (error: Error) => {
      toast.error("Lưu thay đổi thất bại", {
        description: error.message || "Cập nhật trợ lý thất bại.",
      });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateAssistant(reference),
    onSuccess: (assistant) => {
      queryClient.setQueryData(["assistants", reference], assistant);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success("Đã vô hiệu hóa trợ lý. Lịch sử và workflow vẫn được bảo lưu.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const activateMutation = useMutation({
    mutationFn: () => activateAssistant(reference),
    onSuccess: (assistant) => {
      queryClient.setQueryData(["assistants", reference], assistant);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success(`Đã kích hoạt lại Trợ lý “${assistant.name}” thành công!`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const exportMutation = useMutation({
    mutationFn: () => exportAssistantBundle(reference),
    onSuccess: (bundle) => {
      downloadBundle(`${bundle.assistant.code}.qnu.bundle.json`, bundle);
      toast.success("Đã xuất gói cấu hình bundle JSON thành công.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const item = assistantQuery.data;

  const readinessQuery = useQuery({
    queryKey: ["assistant-readiness", item?.code],
    queryFn: () => getAssistantReadiness(item?.code as string),
    enabled: Boolean(item?.code),
    staleTime: 30_000,
  });

  const publishMutation = useMutation({
    mutationFn: () => publishAssistant(reference),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["assistants", reference] });
      queryClient.invalidateQueries({ queryKey: ["assistant-readiness", item?.code] });
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success(res.message);
    },
    onError: (err: Error) => toast.error(`Xuất bản thất bại: ${err.message}`),
  });

  const forkWorkflowMutation = useMutation({
    mutationFn: () => forkAssistantWorkflow(reference),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["assistants", reference] });
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      queryClient.invalidateQueries({ queryKey: ["workflow-definitions"] });
      toast.success("Tách quy trình thành công!", {
        description: `Đã tạo workflow riêng: ${res.new_workflow_name} (${res.new_workflow_id})`,
      });
      if (form) {
        setForm({ ...form, workflow_id: res.new_workflow_id });
      }
    },
    onError: (err: Error) => toast.error(`Tách quy trình thất bại: ${err.message}`),
  });

  const cloneMutation = useMutation({
    mutationFn: (data: {
      new_code: string;
      new_name: string;
      new_description?: string;
      target_collection_id?: string;
      fork_workflow?: boolean;
    }) => cloneAssistant(reference, data),
    onSuccess: (cloned) => {
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success(`Đã nhân bản thành công Trợ lý "${cloned.name}"!`);
      setIsCloneOpen(false);
      onNavigate(`/assistants/${encodeURIComponent(cloned.code)}`);
    },
    onError: (err: Error) => toast.error(`Nhân bản thất bại: ${err.message}`),
  });

  const versionsQuery = useQuery({
    queryKey: ["assistant-versions", item?.code],
    queryFn: () => getAssistantVersions(item?.code as string),
    enabled: Boolean(item?.code) && isHistoryOpen,
  });

  const rollbackMutation = useMutation({
    mutationFn: (versionId: string) => rollbackAssistantVersion(reference, versionId),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["assistants", reference] });
      queryClient.invalidateQueries({ queryKey: ["assistant-versions", item?.code] });
      queryClient.invalidateQueries({ queryKey: ["assistant-readiness", item?.code] });
      toast.success(`Đã khôi phục thành công về phiên bản ${res.restored_version}`);
      setIsHistoryOpen(false);
    },
    onError: (err: Error) => toast.error(`Khôi phục thất bại: ${err.message}`),
  });

  const handleGeneratePrompt = async () => {
    if (!form) return;
    const idea = form.description.trim() || form.name.trim();
    if (!idea) {
      toast.warning("Vui lòng nhập Tên hoặc Mô tả để AI viết System Prompt phù hợp.");
      return;
    }
    setIsGeneratingPrompt(true);
    try {
      const spec = await generateAssistantSpec(idea, form.category);
      setForm((prev) => (prev ? { ...prev, system_prompt: spec.system_prompt } : null));
      toast.success("AI đã tối ưu và viết lại System Prompt chuẩn 5 phần ĐH Quy Nhơn!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không thể tự sinh prompt.");
    } finally {
      setIsGeneratingPrompt(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form) return;
    updateMutation.mutate(form);
  };

  if (assistantQuery.isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-muted-foreground">
        Đang tải thông tin Trợ lý AI từ CSDL…
      </div>
    );
  }

  if (!item || !form) {
    return (
      <Card>
        <CardContent className="space-y-4 p-8">
          <p className="font-semibold text-foreground">Không tìm thấy Trợ lý AI</p>
          <p className="text-xs text-muted-foreground">
            Mã định danh hoặc bí danh “{reference}” không tồn tại trong hệ thống.
          </p>
          <Button variant="outline" onClick={() => onNavigate("/assistants")}>
            <ArrowLeft className="size-4" />
            Quay lại danh mục trợ lý
          </Button>
        </CardContent>
      </Card>
    );
  }

  const collections = collectionsQuery.data || [];
  const workflows = workflowsQuery.data || [];
  // Khi ở subView workflow, hiển thị trực tiếp màn hình DAG Studio độc lập toàn màn hình
  if (subView === "workflow") {
    return (
      <DAGCanvasPage
        currentPath={`/workflows/${form?.workflow_id || item.workflow_id}`}
        initialWorkflowId={form?.workflow_id || item.workflow_id}
        onNavigate={onNavigate}
        onNavigateToChat={(code) =>
          onNavigate(`/assistants/${encodeURIComponent(code)}/playground`)
        }
        backPath={`/assistants/${encodeURIComponent(item.code || item.id)}`}
        backLabel={`Trợ lý ${item.name}`}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header & Action Toolbar & KPI Strip */}
      <AssistantHeader
        assistant={item}
        onNavigate={onNavigate}
        subView={subView}
        onOpenClone={() => setIsCloneOpen(true)}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenEmbed={() => setIsEmbedOpen(true)}
        onExport={() => exportMutation.mutate()}
        isExporting={exportMutation.isPending}
        onSave={() => form && updateMutation.mutate(form)}
        isSaving={updateMutation.isPending}
        onPublish={() => publishMutation.mutate()}
        isPublishing={publishMutation.isPending}
        readiness={readinessQuery.data}
        isReadinessLoading={readinessQuery.isLoading}
        isReadinessFetching={readinessQuery.isFetching}
        onRefetchReadiness={() => readinessQuery.refetch()}
        workflowId={form?.workflow_id || item.workflow_id}
      />

      {/* Local Workspace Sub-Navigation Pills */}
      <AssistantWorkspaceNav
        assistantId={item.code || item.id}
        activeSubView={subView}
        onNavigate={onNavigate}
      />

      {/* Sub-view Content Switcher */}
      {subView === "playground" ? (
        <ChatStudioPage initialAssistant={item.code} />
      ) : subView === "channels" ? (
        <ChannelsPage />
      ) : subView === "quality" ? (
        <EvaluationPage onNavigateToKnowledge={() => onNavigate("/knowledge")} />
      ) : subView === "runs" ? (
        <RunsPage
          currentPath={currentPath}
          onNavigate={onNavigate}
          onNavigateToCanvas={() =>
            onNavigate(`/assistants/${encodeURIComponent(item.code)}/workflow`)
          }
        />
      ) : subView === "models" ? (
        /* TAB 2: MÔ HÌNH & AN TOÀN */
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-6">
              <AssistantModelSection
                form={form}
                onChange={setForm}
                availableModels={availableModels}
              />
            </div>
            <div className="space-y-6">
              <AssistantGuardrailsSection
                form={form}
                onChange={setForm}
                assistantCode={item.code}
                onNavigate={onNavigate}
              />
            </div>
          </div>
        </form>
      ) : subView === "tools" ? (
        /* TAB 3: QUY TRÌNH & CÔNG CỤ */
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)]">
            <div className="space-y-6">
              <AssistantToolsSection
                form={form}
                onChange={setForm}
                workflows={workflows}
                onNavigate={onNavigate}
                assistant={item}
                onForkWorkflow={() => forkWorkflowMutation.mutate()}
                isForkingWorkflow={forkWorkflowMutation.isPending}
              />
            </div>
            <div className="space-y-6">
              <AssistantDangerZone
                assistant={item}
                isActivating={activateMutation.isPending}
                isDeactivating={deactivateMutation.isPending}
                onActivate={() => activateMutation.mutate()}
                onDeactivate={() => deactivateMutation.mutate()}
              />
            </div>
          </div>
        </form>
      ) : (
        /* TAB 1: THÔNG TIN & TRI THỨC (Mặc định overview) */
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(20rem,0.75fr)]">
            <div className="space-y-6">
              <AssistantPersonaSection
                form={form}
                onChange={setForm}
                onGeneratePrompt={handleGeneratePrompt}
                isGeneratingPrompt={isGeneratingPrompt}
              />
            </div>
            <div className="space-y-6">
              <AssistantKnowledgeSection
                form={form}
                onChange={setForm}
                collections={collections}
                onNavigate={onNavigate}
              />
            </div>
          </div>
        </form>
      )}

      {/* 1-Click Clone Assistant Dialog */}
      <AssistantCloneDialog
        open={isCloneOpen}
        onOpenChange={setIsCloneOpen}
        originalName={item.name}
        initialCode={`${item.code}_copy`}
        initialName={`${item.name} (Bản sao)`}
        initialDescription={`Bản sao nhân bản từ ${item.name} chuyên trách phục vụ đơn vị.`}
        initialCollectionId={item.collection_id}
        isPending={cloneMutation.isPending}
        onConfirm={(data) => {
          cloneMutation.mutate({
            new_code: data.code,
            new_name: data.name,
            new_description: data.description || undefined,
            target_collection_id: data.collectionId || undefined,
            fork_workflow: data.forkWorkflow,
          });
        }}
      />

      {/* Dialog Mã Nhúng Web Widget */}
      <AssistantEmbedDialog
        open={isEmbedOpen}
        onOpenChange={setIsEmbedOpen}
        assistantCode={item.code}
        assistantName={item.name}
      />

      {/* Assistant Version History & Rollback Dialog */}
      <AssistantVersionHistoryDialog
        open={isHistoryOpen}
        onOpenChange={setIsHistoryOpen}
        assistantName={item.name}
        versions={versionsQuery.data}
        isLoading={versionsQuery.isLoading}
        onRollback={(versionId) => rollbackMutation.mutate(versionId)}
        isRollbacking={rollbackMutation.isPending}
      />
    </div>
  );
}
