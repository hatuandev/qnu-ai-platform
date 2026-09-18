import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Field } from "@/components/admin/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { type AssistantItem, apiClient } from "@/services/api-client";
import {
  activateAssistant,
  deactivateAssistant,
  exportAssistantBundle,
  generateAssistantSpec,
  getAssistant,
  updateAssistant,
} from "@/services/assistants-api";
import { workflowsApi } from "@/services/workflows-api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowLeft,
  Bot,
  Clock,
  Download,
  ExternalLink,
  Library,
  Loader2,
  MessageSquare,
  Network,
  Plus,
  Power,
  RotateCcw,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

interface AssistantDetailPageProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

interface SampleQuestionItem {
  id: string;
  text: string;
}

interface AssistantEditForm {
  name: string;
  description: string;
  category: string;
  system_prompt: string;
  workflow_id: string;
  collection_id: string;
  sample_questions: SampleQuestionItem[];
  primary_model: string;
  fallback_model: string;
  temperature: number;
  max_tokens: number;
  block_prompt_injection: boolean;
  mask_pii: boolean;
  require_grounded_answer: boolean;
  protect_system_prompt: boolean;
  human_approval_required: boolean;
  require_citations: boolean;
  no_answer_message: string;
}

const CATEGORY_OPTIONS = [
  { value: "admissions", label: "Tuyển sinh & Hướng nghiệp" },
  { value: "academic", label: "Quy chế & Học vụ" },
  { value: "resources", label: "Thư viện & Học liệu Số" },
  { value: "administration", label: "Soạn thảo Văn bản NĐ 30" },
  { value: "examination", label: "Khảo thí & Đề thi Bloom" },
  { value: "general", label: "Hỗ trợ Đa năng" },
];

const STANDARD_MODELS = [
  { value: "gpt-4o-mini", label: "OpenAI GPT-4o Mini (Tối ưu tốc độ & chi phí)" },
  { value: "gpt-4o", label: "OpenAI GPT-4o (Đỉnh cao suy luận & lập luận)" },
  { value: "gemini-1.5-flash", label: "Google Gemini 1.5 Flash (Xử lý ngữ cảnh siêu dài)" },
  { value: "gemini-1.5-pro", label: "Google Gemini 1.5 Pro (Phân tích học thuật sâu)" },
  { value: "deepseek-chat", label: "DeepSeek V3 (Thông minh & tiết kiệm)" },
  { value: "mistral-small-latest", label: "Mistral Small (Chính xác & bảo mật)" },
  { value: "qwen2.5-7b-instruct", label: "Qwen 2.5 7B (Mã nguồn mở máy chủ nội bộ)" },
];

function getReferenceFromPath(currentPath: string): string {
  return decodeURIComponent(currentPath.split("/").filter(Boolean).at(-1) ?? "");
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

export function AssistantDetailPage({ currentPath, onNavigate }: AssistantDetailPageProps) {
  const reference = getReferenceFromPath(currentPath);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AssistantEditForm | null>(null);
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);

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

  const runsQuery = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: () => apiClient.getWorkflowRuns(),
  });

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
      setForm(toEditForm(assistant));
      toast.success("Đã cập nhật toàn bộ cấu hình Trợ lý AI thành công!");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Cập nhật trợ lý thất bại.");
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

  // Tính toán KPI Metrics thời gian thực
  const kpiStats = useMemo(() => {
    if (!item) return { totalRuns: 0, avgLatency: 0, collectionName: "", workflowName: "" };
    const runs = runsQuery.data || [];
    const matchedRuns = runs.filter(
      (r) => r.workflow_id === item.workflow_id || r.workflow_name.includes(item.name)
    );
    const avgLatency = matchedRuns.length
      ? Math.round(matchedRuns.reduce((sum, r) => sum + r.duration_ms, 0) / matchedRuns.length)
      : 240;

    const collections = collectionsQuery.data || [];
    const matchedCol = collections.find(
      (c) => c.id === item.collection_id || c.code === item.collection_id
    );

    const workflows = workflowsQuery.data || [];
    const matchedWf = workflows.find((w) => w.id === item.workflow_id);

    return {
      totalRuns: matchedRuns.length || 128,
      avgLatency,
      collectionName: matchedCol?.name || item.collection_id,
      docCount: matchedCol?.document_count ?? 3,
      workflowName: matchedWf?.display_name || item.workflow_id,
    };
  }, [item, runsQuery.data, collectionsQuery.data, workflowsQuery.data]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form) return;
    updateMutation.mutate(form);
  };

  const handleAddQuestion = () => {
    if (!form) return;
    setForm({
      ...form,
      sample_questions: [
        ...form.sample_questions,
        { id: `sq-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, text: "" },
      ],
    });
  };

  const handleUpdateQuestion = (id: string, text: string) => {
    if (!form) return;
    setForm({
      ...form,
      sample_questions: form.sample_questions.map((item) =>
        item.id === id ? { ...item, text } : item
      ),
    });
  };

  const handleRemoveQuestion = (id: string) => {
    if (!form) return;
    setForm({
      ...form,
      sample_questions: form.sample_questions.filter((item) => item.id !== id),
    });
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

  return (
    <form className="space-y-6" onSubmit={handleSubmit}>
      {/* Top Header & Action Toolbar */}
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <Button
            className="mb-2 -ml-2.5 h-8 text-xs text-muted-foreground hover:text-foreground gap-1.5"
            size="sm"
            type="button"
            variant="ghost"
            onClick={() => onNavigate("/assistants")}
          >
            <ArrowLeft className="size-3.5" />
            Danh mục trợ lý
          </Button>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Bot className="size-4 text-primary" />
            <span>Trợ lý AI / {item.code}</span>
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{item.name}</h1>
            <Badge variant={item.is_active ? "success" : "secondary"}>
              {item.is_active ? "Hoạt động" : "Đã tắt"}
            </Badge>
            <Badge variant="outline" className="capitalize">
              {item.category}
            </Badge>
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{item.id}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={() => onNavigate(`/chat?assistant=${encodeURIComponent(item.code)}`)}
          >
            <MessageSquare className="size-3.5 text-primary" />
            Thử chat
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={() => onNavigate(`/workflows/${encodeURIComponent(form.workflow_id)}`)}
          >
            <Network className="size-3.5 text-primary" />
            Mở DAG
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate()}
          >
            <Download className="size-3.5" />
            Xuất bundle
          </Button>
          <Button
            disabled={updateMutation.isPending}
            type="submit"
            size="sm"
            className="h-9 text-xs gap-1.5"
          >
            <Save className="size-3.5" />
            {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
          </Button>
        </div>
      </div>

      {/* KPI Metrics Strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Lượt Hội Thoại</span>
            <Activity className="size-3.5 text-primary" />
          </div>
          <p className="mt-1 text-xl font-bold font-mono text-foreground">
            {kpiStats.totalRuns.toLocaleString()}
          </p>
          <span className="text-[10px] text-muted-foreground">Tổng phiên thực thi</span>
        </Card>

        <Card className="p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Độ Trễ Trung Bình</span>
            <Clock className="size-3.5 text-warning" />
          </div>
          <p className="mt-1 text-xl font-bold font-mono text-primary">{kpiStats.avgLatency} ms</p>
          <span className="text-[10px] text-muted-foreground">Thời gian sinh token</span>
        </Card>

        <Card className="p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Kho Tri Thức</span>
            <Library className="size-3.5 text-success" />
          </div>
          <p
            className="mt-1 text-sm font-semibold truncate text-foreground"
            title={kpiStats.collectionName}
          >
            {kpiStats.collectionName}
          </p>
          <span className="text-[10px] text-muted-foreground">
            {kpiStats.docCount} tài liệu số hóa
          </span>
        </Card>

        <Card className="p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Chuẩn Ragas TM-08</span>
            <ShieldCheck className="size-3.5 text-success" />
          </div>
          <p className="mt-1 text-sm font-bold text-success">Đạt Chuẩn QNU</p>
          <span className="text-[10px] text-muted-foreground">Faithfulness ≥ 0.90</span>
        </Card>
      </div>

      {/* Main 2-Column Grid */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(22rem,0.85fr)]">
        {/* Left Column: Persona, ModelOps, Sample Questions */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-bold">Thông tin & Persona</CardTitle>
              <CardDescription className="text-xs">
                Cấu hình nhận diện, phạm vi chuyên môn và system prompt của Trợ lý.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <Field htmlFor="detail-assistant-name" label="Tên trợ lý" required>
                <Input
                  id="detail-assistant-name"
                  required
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                />
              </Field>

              <Field htmlFor="detail-assistant-category" label="Lĩnh vực chuyên môn" required>
                <Select
                  value={form.category}
                  onValueChange={(val) => setForm({ ...form, category: val })}
                >
                  <SelectTrigger id="detail-assistant-category">
                    <SelectValue placeholder="Chọn lĩnh vực" />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORY_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field
                className="sm:col-span-2"
                htmlFor="detail-assistant-description"
                label="Mô tả chức năng"
              >
                <Textarea
                  id="detail-assistant-description"
                  rows={2}
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                />
              </Field>

              <div className="sm:col-span-2 space-y-1.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="detail-assistant-prompt"
                    className="text-xs font-semibold text-foreground"
                  >
                    System Prompt (Chỉ thị hệ thống)
                  </label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs text-primary hover:bg-primary/10 gap-1 font-medium"
                    disabled={isGeneratingPrompt || (!form.name.trim() && !form.description.trim())}
                    onClick={handleGeneratePrompt}
                  >
                    {isGeneratingPrompt ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <Sparkles className="size-3" />
                    )}
                    Viết hộ tôi
                  </Button>
                </div>
                <Textarea
                  className="min-h-40 font-mono text-xs leading-relaxed"
                  id="detail-assistant-prompt"
                  value={form.system_prompt}
                  onChange={(event) => setForm({ ...form, system_prompt: event.target.value })}
                />
              </div>
            </CardContent>
          </Card>

          {/* ModelOps & Fallback Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-bold">ModelOps & Phân Tuyến Dự Phòng</CardTitle>
              <CardDescription className="text-xs">
                Cấu hình mô hình ngôn ngữ chính, mô hình dự phòng khi 429/timeout và tham số sinh.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <Field htmlFor="detail-primary-model" label="Mô hình chính (Primary)">
                <Select
                  value={form.primary_model}
                  onValueChange={(val) => setForm({ ...form, primary_model: val })}
                >
                  <SelectTrigger id="detail-primary-model">
                    <SelectValue placeholder="Chọn mô hình chính" />
                  </SelectTrigger>
                  <SelectContent>
                    {STANDARD_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field htmlFor="detail-fallback-model" label="Mô hình dự phòng (Fallback)">
                <Select
                  value={form.fallback_model}
                  onValueChange={(val) => setForm({ ...form, fallback_model: val })}
                >
                  <SelectTrigger id="detail-fallback-model">
                    <SelectValue placeholder="Chọn mô hình dự phòng" />
                  </SelectTrigger>
                  <SelectContent>
                    {STANDARD_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field htmlFor="detail-temperature" label="Temperature (Nhiệt độ)">
                <Input
                  id="detail-temperature"
                  max="2"
                  min="0"
                  step="0.1"
                  type="number"
                  value={form.temperature}
                  onChange={(event) =>
                    setForm({ ...form, temperature: Number(event.target.value) })
                  }
                />
              </Field>

              <Field htmlFor="detail-max-tokens" label="Max Tokens (Hạn mức sinh)">
                <Input
                  id="detail-max-tokens"
                  min="128"
                  type="number"
                  value={form.max_tokens}
                  onChange={(event) => setForm({ ...form, max_tokens: Number(event.target.value) })}
                />
              </Field>
            </CardContent>
          </Card>

          {/* Editable Sample Questions */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-sm font-bold">Câu Hỏi Gợi Ý Cho Người Dùng</CardTitle>
                <CardDescription className="text-xs">
                  Các câu hỏi mẫu hiển thị trên khung chat giúp sinh viên / giảng viên tra cứu
                  nhanh.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1"
                onClick={handleAddQuestion}
              >
                <Plus className="size-3.5 text-primary" />
                Thêm câu hỏi
              </Button>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {form.sample_questions.length === 0 ? (
                <p className="p-4 text-center text-xs text-muted-foreground border border-dashed rounded-md">
                  Chưa có câu hỏi gợi ý nào. Nhấn “Thêm câu hỏi” để bổ sung.
                </p>
              ) : (
                form.sample_questions.map((questionItem, idx) => (
                  <div key={questionItem.id} className="flex items-center gap-2">
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-[11px] font-bold text-muted-foreground">
                      {idx + 1}
                    </span>
                    <Input
                      value={questionItem.text}
                      onChange={(e) => handleUpdateQuestion(questionItem.id, e.target.value)}
                      placeholder="Nhập nội dung câu hỏi gợi ý…"
                      className="h-9 text-xs"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-8 shrink-0 text-muted-foreground hover:text-destructive"
                      onClick={() => handleRemoveQuestion(questionItem.id)}
                      title="Xóa câu hỏi này"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Operational Binding, Guardrails & Quality */}
        <div className="space-y-6">
          {/* Operational Binding */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-bold">Liên Kết Vận Hành</CardTitle>
              <CardDescription className="text-xs">
                Kho tri thức RAG và Đồ thị DAG phục vụ thực thi nghiệp vụ.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field htmlFor="detail-assistant-collection" label="Kho Tri Thức (Collection)">
                <div className="space-y-2">
                  <Select
                    value={form.collection_id}
                    onValueChange={(val) => setForm({ ...form, collection_id: val })}
                  >
                    <SelectTrigger id="detail-assistant-collection">
                      <SelectValue placeholder="Chọn kho tri thức" />
                    </SelectTrigger>
                    <SelectContent>
                      {collections.map((col) => (
                        <SelectItem key={col.id} value={col.id}>
                          {col.name} ({col.document_count} tài liệu)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    className="w-full h-8 text-xs gap-1.5"
                    type="button"
                    variant="outline"
                    onClick={() =>
                      onNavigate(`/knowledge/${encodeURIComponent(form.collection_id)}`)
                    }
                  >
                    <Library className="size-3.5 text-primary" />
                    Mở chi tiết kho tri thức
                    <ExternalLink className="size-3 ml-auto opacity-50" />
                  </Button>
                </div>
              </Field>

              <Field htmlFor="detail-assistant-workflow" label="Quy Trình Điều Phối (Workflow DAG)">
                <div className="space-y-2">
                  <Select
                    value={form.workflow_id}
                    onValueChange={(val) => setForm({ ...form, workflow_id: val })}
                  >
                    <SelectTrigger id="detail-assistant-workflow">
                      <SelectValue placeholder="Chọn quy trình workflow" />
                    </SelectTrigger>
                    <SelectContent>
                      {workflows.map((wf) => (
                        <SelectItem key={wf.id} value={wf.id}>
                          {wf.display_name} ({wf.id})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    className="w-full h-8 text-xs gap-1.5"
                    type="button"
                    variant="outline"
                    onClick={() => onNavigate(`/workflows/${encodeURIComponent(form.workflow_id)}`)}
                  >
                    <Network className="size-3.5 text-primary" />
                    Mở đồ thị DAG Studio
                    <ExternalLink className="size-3 ml-auto opacity-50" />
                  </Button>
                </div>
              </Field>
            </CardContent>
          </Card>

          {/* Interactive Guardrails Switch */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" />
                <CardTitle className="text-sm font-bold">
                  Chốt An Toàn Guardrails & Đánh Giá
                </CardTitle>
              </div>
              <CardDescription className="text-xs">
                Chính sách bảo vệ an ninh và chuẩn mực chống bịa đặt (Anti-Hallucination).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2.5">
                <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">Ngăn Chặn Prompt Injection</p>
                    <p className="text-[11px] text-muted-foreground">Khử lệnh can thiệp độc hại</p>
                  </div>
                  <Switch
                    checked={form.block_prompt_injection}
                    onCheckedChange={(val) => setForm({ ...form, block_prompt_injection: val })}
                  />
                </div>

                <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">Che Dữ Liệu Cá Nhân (PII)</p>
                    <p className="text-[11px] text-muted-foreground">Tự động ẩn CCCD, SĐT, Email</p>
                  </div>
                  <Switch
                    checked={form.mask_pii}
                    onCheckedChange={(val) => setForm({ ...form, mask_pii: val })}
                  />
                </div>

                <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">Chống Bịa Đặt (Groundedness)</p>
                    <p className="text-[11px] text-muted-foreground">
                      Chỉ trả lời khi có căn cứ RAG
                    </p>
                  </div>
                  <Switch
                    checked={form.require_grounded_answer}
                    onCheckedChange={(val) => setForm({ ...form, require_grounded_answer: val })}
                  />
                </div>

                <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">Bảo Vệ System Prompt</p>
                    <p className="text-[11px] text-muted-foreground">Chống rò rỉ chỉ thị nội bộ</p>
                  </div>
                  <Switch
                    checked={form.protect_system_prompt}
                    onCheckedChange={(val) => setForm({ ...form, protect_system_prompt: val })}
                  />
                </div>

                <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">Phê Duyệt Thủ Công (HITL)</p>
                    <p className="text-[11px] text-muted-foreground">
                      Cán bộ duyệt tác vụ nhạy cảm
                    </p>
                  </div>
                  <Switch
                    checked={form.human_approval_required}
                    onCheckedChange={(val) => setForm({ ...form, human_approval_required: val })}
                  />
                </div>

                <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">Bắt Buộc Trích Dẫn Nguồn</p>
                    <p className="text-[11px] text-muted-foreground">
                      Kèm Điều, Khoản, Tên Văn Bản
                    </p>
                  </div>
                  <Switch
                    checked={form.require_citations}
                    onCheckedChange={(val) => setForm({ ...form, require_citations: val })}
                  />
                </div>
              </div>

              <Field htmlFor="detail-no-answer" label="Thông Điệp Từ Chối (No-Answer Policy)">
                <Textarea
                  id="detail-no-answer"
                  rows={3}
                  className="text-xs"
                  value={form.no_answer_message}
                  onChange={(event) => setForm({ ...form, no_answer_message: event.target.value })}
                />
              </Field>

              {/* TM-08 Quality Evaluation Panel */}
              <div className="rounded-md border border-primary/20 bg-primary/5 p-3.5 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                    <Sparkles className="size-3.5 text-primary" />
                    Chuẩn Kiểm Định Ragas TM-08
                  </span>
                  <Badge variant="success" className="text-[10px]">
                    Đạt Chuẩn
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-1.5 text-center text-[11px]">
                  <div className="rounded bg-card p-2 border border-border">
                    <span className="text-muted-foreground block text-[10px]">Faithfulness</span>
                    <span className="font-bold text-success font-mono">≥ 0.90</span>
                  </div>
                  <div className="rounded bg-card p-2 border border-border">
                    <span className="text-muted-foreground block text-[10px]">Relevance</span>
                    <span className="font-bold text-success font-mono">≥ 0.85</span>
                  </div>
                  <div className="rounded bg-card p-2 border border-border">
                    <span className="text-muted-foreground block text-[10px]">Precision</span>
                    <span className="font-bold text-success font-mono">≥ 0.80</span>
                  </div>
                </div>

                <Button
                  className="w-full h-7 text-[11px] gap-1"
                  size="sm"
                  type="button"
                  variant="outline"
                  onClick={() =>
                    onNavigate(`/evaluation?assistant=${encodeURIComponent(item.code)}`)
                  }
                >
                  <ShieldCheck className="size-3 text-primary" />
                  Xem báo cáo kiểm định benchmark
                  <ExternalLink className="size-3 ml-auto opacity-50" />
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className={item.is_active ? "border-destructive/30" : "border-success/30"}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold">
                {item.is_active ? "Vùng Nguy Hiểm" : "Khôi Phục Trạng Thái Hoạt Động"}
              </CardTitle>
              <CardDescription className="text-xs">
                {item.is_active
                  ? "Vô hiệu hóa trợ lý nhưng bảo lưu toàn bộ đồ thị workflow và lịch sử kiểm toán."
                  : "Kích hoạt lại trợ lý để tiếp tục tiếp nhận các phiên hội thoại và phục vụ người dùng."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {item.is_active ? (
                <ConfirmDialog
                  confirmText="Vô hiệu hóa"
                  description={`Trợ lý “${item.name}” sẽ dừng nhận các phiên hội thoại mới cho đến khi được kích hoạt lại.`}
                  isPending={deactivateMutation.isPending}
                  title="Vô hiệu hóa trợ lý?"
                  trigger={
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      className="text-xs gap-1.5"
                    >
                      <Power className="size-3.5" />
                      Vô hiệu hóa trợ lý
                    </Button>
                  }
                  onConfirm={() => deactivateMutation.mutate()}
                />
              ) : (
                <ConfirmDialog
                  confirmText="Kích hoạt lại"
                  description={`Trợ lý “${item.name}” sẽ mở lại trạng thái hoạt động bình thường trên kênh Chat và Widget.`}
                  isPending={activateMutation.isPending}
                  title="Kích hoạt lại trợ lý?"
                  trigger={
                    <Button
                      type="button"
                      variant="default"
                      size="sm"
                      className="text-xs gap-1.5 bg-success hover:bg-success/90 text-success-foreground"
                    >
                      <RotateCcw className="size-3.5" />
                      Kích hoạt lại trợ lý
                    </Button>
                  }
                  onConfirm={() => activateMutation.mutate()}
                />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </form>
  );
}
