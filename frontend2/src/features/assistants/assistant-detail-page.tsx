import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
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
import { knowledgeApi } from "@/services/knowledge-api";
import { modelopsApi } from "@/services/modelops-api";
import { workflowsApi } from "@/services/workflows-api";
import type { AssistantItem } from "@/types/assistants";
import { AssistantPlaygroundTab } from "./assistant-playground-tab";
import { AssistantWorkflowTab } from "./assistant-workflow-tab";

interface AssistantDetailPageProps {
  assistantId: string;
  initialTab?: AssistantSubView;
}

function toEditForm(item: AssistantItem): AssistantEditForm {
  const cfg = item.config;
  const questions =
    Array.isArray(item.sample_questions) && item.sample_questions.length > 0
      ? item.sample_questions
      : Array.isArray(cfg?.sample_questions) && cfg.sample_questions.length > 0
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
      id: `sq-${idx}`,
      text: q,
    })),
    primary_model: cfg?.model_policy?.primary_model || "gpt-4o-mini",
    fallback_model:
      cfg?.model_policy?.fallback_model || "gemini-2.5-flash-lite",
    temperature: cfg?.model_policy?.temperature ?? 0.2,
    max_tokens: cfg?.model_policy?.max_tokens ?? 1200,
    thinking_budget: cfg?.model_policy?.thinking_budget ?? 0,
    block_prompt_injection: cfg?.guardrails?.block_prompt_injection ?? true,
    mask_pii: cfg?.guardrails?.mask_pii ?? true,
    require_grounded_answer: cfg?.guardrails?.require_grounded_answer ?? true,
    protect_system_prompt: cfg?.guardrails?.protect_system_prompt ?? true,
    human_approval_required: cfg?.tools?.human_approval_required ?? true,
    require_citations: cfg?.output_policy?.require_citations ?? true,
    no_answer_message:
      cfg?.guardrails?.no_answer_message ||
      "Thông tin này chưa có trong nguồn văn bản chính thức của Trường Đại học Quy Nhơn. Vui lòng liên hệ đơn vị phụ trách.",
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
  assistantId,
  initialTab,
}: AssistantDetailPageProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [form, setForm] = useState<AssistantEditForm | null>(null);
  const [subView, setSubView] = useState<AssistantSubView>(
    initialTab || "overview",
  );
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [isEmbedOpen, setIsEmbedOpen] = useState(false);
  const [isCloneOpen, setIsCloneOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  useEffect(() => {
    if (initialTab) {
      setSubView(initialTab);
    }
  }, [initialTab]);

  // 1. Fetch Assistant
  const assistantQuery = useQuery({
    queryKey: ["assistants", assistantId],
    queryFn: () => getAssistant(assistantId),
    enabled: Boolean(assistantId),
  });

  // 2. Fetch Supporting Metadata
  const collectionsQuery = useQuery({
    queryKey: ["knowledge-collections"],
    queryFn: () => knowledgeApi.getCollections(),
  });

  const workflowsQuery = useQuery({
    queryKey: ["workflow-definitions"],
    queryFn: () => workflowsApi.listDefinitions(),
  });

  const providersQuery = useQuery({
    queryKey: ["modelops", "providers"],
    queryFn: () => modelopsApi.getModelProviders(),
  });

  const readinessQuery = useQuery({
    queryKey: ["assistant-readiness", assistantId],
    queryFn: () => getAssistantReadiness(assistantId),
    enabled: Boolean(assistantId),
  });

  const versionsQuery = useQuery({
    queryKey: ["assistant-versions", assistantId],
    queryFn: () => getAssistantVersions(assistantId),
    enabled: Boolean(assistantId),
  });

  // Sync Form State
  useEffect(() => {
    if (assistantQuery.data) {
      setForm(toEditForm(assistantQuery.data));
    }
  }, [assistantQuery.data]);

  // Available Models calculation
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

  // Mutations
  const updateMutation = useMutation({
    mutationFn: async (value: AssistantEditForm) => {
      const current = assistantQuery.data;
      if (!current) throw new Error("Không có dữ liệu trợ lý để cập nhật.");
      return updateAssistant(assistantId, {
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
            ...current.config?.model_policy,
            primary_model: value.primary_model,
            fallback_model: value.fallback_model,
            temperature: value.temperature,
            max_tokens: value.max_tokens,
            thinking_budget: value.thinking_budget ?? 0,
          },
          guardrails: {
            ...current.config?.guardrails,
            block_prompt_injection: value.block_prompt_injection,
            mask_pii: value.mask_pii,
            require_grounded_answer: value.require_grounded_answer,
            protect_system_prompt: value.protect_system_prompt,
            no_answer_message: value.no_answer_message,
          },
          tools: {
            ...current.config?.tools,
            human_approval_required: value.human_approval_required,
          },
          output_policy: {
            ...current.config?.output_policy,
            require_citations: value.require_citations,
          },
        },
      });
    },
    onSuccess: (assistant) => {
      queryClient.setQueryData(["assistants", assistantId], assistant);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      queryClient.invalidateQueries({
        queryKey: ["assistant-readiness", assistantId],
      });
      setForm(toEditForm(assistant));
      toast.success("Đã lưu thay đổi cấu hình thành công!", {
        description: `Các thiết lập của "${assistant.name}" đã được cập nhật.`,
      });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishAssistant(assistantId),
    onSuccess: (res) => {
      toast.success(res.message || "Đã phát hành Trợ lý thành công!", {
        description: `Điểm sẵn sàng đạt: ${res.readiness_score}/100.`,
      });
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      queryClient.invalidateQueries({
        queryKey: ["assistant-readiness", assistantId],
      });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const forkWorkflowMutation = useMutation({
    mutationFn: () => forkAssistantWorkflow(assistantId),
    onSuccess: (res) => {
      toast.success(
        res.message ||
          `Đã nhân bản workflow riêng: “${res.new_workflow_name}”!`,
      );
      if (form) {
        setForm({ ...form, workflow_id: res.new_workflow_id });
      }
      queryClient.invalidateQueries({ queryKey: ["assistants", assistantId] });
      queryClient.invalidateQueries({ queryKey: ["workflow-definitions"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const exportMutation = useMutation({
    mutationFn: () => exportAssistantBundle(assistantId),
    onSuccess: (bundle) => {
      downloadBundle(`${bundle.assistant.code}.qnu.bundle.json`, bundle);
      toast.success("Đã xuất gói cấu hình bundle JSON thành công.");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const rollbackMutation = useMutation({
    mutationFn: (versionId: string) =>
      rollbackAssistantVersion(assistantId, versionId),
    onSuccess: (res) => {
      toast.success(
        res.message || `Đã khôi phục về phiên bản ${res.restored_version}!`,
      );
      queryClient.invalidateQueries({ queryKey: ["assistants", assistantId] });
      queryClient.invalidateQueries({
        queryKey: ["assistant-versions", assistantId],
      });
      setIsHistoryOpen(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const cloneMutation = useMutation({
    mutationFn: (data: {
      new_code: string;
      new_name: string;
      new_description?: string;
      target_collection_id?: string;
      fork_workflow?: boolean;
    }) => cloneAssistant(assistantId, data),
    onSuccess: (newAst) => {
      toast.success(`Đã nhân bản thành công Trợ lý “${newAst.name}”!`);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      setIsCloneOpen(false);
      navigate({
        to: "/assistants/$assistantId",
        params: { assistantId: newAst.code || newAst.id },
      });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateAssistant(assistantId),
    onSuccess: (assistant) => {
      queryClient.setQueryData(["assistants", assistantId], assistant);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success(
        "Đã vô hiệu hóa trợ lý. Lịch sử và workflow vẫn được bảo lưu.",
      );
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const activateMutation = useMutation({
    mutationFn: () => activateAssistant(assistantId),
    onSuccess: (assistant) => {
      queryClient.setQueryData(["assistants", assistantId], assistant);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success(`Đã kích hoạt lại Trợ lý “${assistant.name}” thành công!`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const handleGeneratePrompt = async () => {
    if (!form) return;
    setIsGeneratingPrompt(true);
    try {
      const brief = `${form.name}. Lĩnh vực: ${form.category}. Mô tả: ${form.description}`;
      const spec = await generateAssistantSpec(brief);
      setForm({
        ...form,
        system_prompt: spec.system_prompt || form.system_prompt,
      });
      toast.success("Đã tự động soạn thảo System Prompt thành công!");
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Tự động soạn thảo prompt thất bại.",
      );
    } finally {
      setIsGeneratingPrompt(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (form) {
      updateMutation.mutate(form);
    }
  };

  if (assistantQuery.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-muted-foreground gap-3">
        <Loader2 className="size-6 animate-spin text-primary" />
        <span className="text-xs">Đang tải thông tin Trợ lý AI từ CSDL...</span>
      </div>
    );
  }

  const item = assistantQuery.data;

  if (!item || !form) {
    return (
      <Card className="border-border">
        <CardContent className="space-y-4 p-8 text-center">
          <p className="font-semibold text-foreground text-sm">
            Không tìm thấy Trợ lý AI
          </p>
          <p className="text-xs text-muted-foreground">
            Mã định danh hoặc bí danh “{assistantId}” không tồn tại trong hệ
            thống.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate({ to: "/assistants" })}
            className="h-8 text-xs gap-1.5"
          >
            <ArrowLeft className="size-3.5" />
            <span>Quay lại danh mục</span>
          </Button>
        </CardContent>
      </Card>
    );
  }

  const collections = collectionsQuery.data || [];
  const workflows = workflowsQuery.data || [];

  return (
    <div className="space-y-6">
      {/* 1. Hero Header & Readiness Telemetry */}
      <AssistantHeader
        assistant={item}
        onNavigate={(path) => {
          if (path.includes("/workflow")) {
            setSubView("workflow");
          } else if (path.includes("/playground")) {
            setSubView("playground");
          } else {
            navigate({ to: path as never });
          }
        }}
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

      {/* 2. Workspace Navigation Tabs */}
      <AssistantWorkspaceNav
        assistantId={item.code || item.id}
        activeSubView={subView}
        onSelectSubView={(view) => setSubView(view)}
      />

      {/* 3. Sub-View Content */}
      {subView === "playground" ? (
        <AssistantPlaygroundTab assistant={item} />
      ) : subView === "workflow" ? (
        <AssistantWorkflowTab
          assistant={item}
          onForkWorkflow={() => forkWorkflowMutation.mutate()}
          isForking={forkWorkflowMutation.isPending}
        />
      ) : subView === "models" ? (
        /* Tab 2: Models & Guardrails */
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <AssistantModelSection
              form={form}
              onChange={setForm}
              availableModels={availableModels}
            />
            <AssistantGuardrailsSection
              form={form}
              onChange={setForm}
              assistantCode={item.code}
              onNavigate={(path) => navigate({ to: path as never })}
            />
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              size="sm"
              disabled={updateMutation.isPending}
              className="h-9 px-4 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Save className="size-3.5" />
              <span>
                {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
              </span>
            </Button>
          </div>
        </form>
      ) : subView === "tools" ? (
        /* Tab 3: Tools & Danger Zone */
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)]">
            <AssistantToolsSection
              form={form}
              onChange={setForm}
              workflows={workflows}
              onNavigate={(path) => navigate({ to: path as never })}
              assistant={item}
              onForkWorkflow={() => forkWorkflowMutation.mutate()}
              isForkingWorkflow={forkWorkflowMutation.isPending}
            />

            <AssistantDangerZone
              assistant={item}
              isDeactivating={deactivateMutation.isPending}
              isActivating={activateMutation.isPending}
              onDeactivate={() => deactivateMutation.mutate()}
              onActivate={() => activateMutation.mutate()}
            />
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              size="sm"
              disabled={updateMutation.isPending}
              className="h-9 px-4 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Save className="size-3.5" />
              <span>
                {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
              </span>
            </Button>
          </div>
        </form>
      ) : (
        /* Default Tab: Overview (Persona + Knowledge) */
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <AssistantPersonaSection
              form={form}
              onChange={setForm}
              onGeneratePrompt={handleGeneratePrompt}
              isGeneratingPrompt={isGeneratingPrompt}
            />

            <AssistantKnowledgeSection
              form={form}
              onChange={setForm}
              collections={collections}
              onNavigate={(path) => navigate({ to: path as never })}
            />
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              size="sm"
              disabled={updateMutation.isPending}
              className="h-9 px-4 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Save className="size-3.5" />
              <span>
                {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
              </span>
            </Button>
          </div>
        </form>
      )}

      {/* 4. Modals & Dialogs */}
      {isCloneOpen && (
        <AssistantCloneDialog
          open={isCloneOpen}
          onOpenChange={setIsCloneOpen}
          originalName={item.name}
          initialCode={`${item.code}_copy`}
          initialName={`${item.name} (Bản sao)`}
          initialDescription={item.description}
          initialCollectionId={item.collection_id}
          onConfirm={(data) => {
            cloneMutation.mutate({
              new_code: data.code,
              new_name: data.name,
              new_description: data.description,
              target_collection_id: data.collectionId,
              fork_workflow: data.forkWorkflow,
            });
          }}
          isPending={cloneMutation.isPending}
        />
      )}

      {isHistoryOpen && (
        <AssistantVersionHistoryDialog
          open={isHistoryOpen}
          onOpenChange={setIsHistoryOpen}
          assistantName={item.name}
          versions={versionsQuery.data || []}
          isLoading={versionsQuery.isLoading}
          onRollback={(versionId) => rollbackMutation.mutate(versionId)}
          isRollbacking={rollbackMutation.isPending}
        />
      )}

      {isEmbedOpen && (
        <AssistantEmbedDialog
          open={isEmbedOpen}
          onOpenChange={setIsEmbedOpen}
          assistantCode={item.code}
          assistantName={item.name}
        />
      )}
    </div>
  );
}
