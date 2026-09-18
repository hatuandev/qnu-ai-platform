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
import { type AssistantLifecycleConfig, apiClient } from "@/services/api-client";
import {
  type AssistantInput,
  type AssistantTemplate,
  createAssistant,
  listAssistantTemplates,
} from "@/services/assistants-api";
import { workflowsApi } from "@/services/workflows-api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Bot, Save, ShieldCheck } from "lucide-react";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

interface AssistantCreatePageProps {
  onNavigate: (path: string) => void;
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

const DEFAULT_CONFIG: AssistantLifecycleConfig = {
  sample_questions: [],
  persona_scope: {
    persona: "Trợ lý AI chính thức của Trường Đại học Quy Nhơn.",
    allowed_topics: [],
    out_of_scope_policy: "Từ chối lịch sự và hướng dẫn người dùng đến đơn vị phụ trách.",
  },
  knowledge_policy: {
    chunking_strategy: "SemanticChunker",
    require_structured_facts: false,
    retrieval_limit: 10,
  },
  model_policy: {
    primary_model: "gpt-4o-mini",
    fallback_model: "gemini-1.5-flash",
    temperature: 0.2,
    max_tokens: 1200,
  },
  guardrails: {
    block_prompt_injection: true,
    mask_pii: true,
    require_grounded_answer: true,
    protect_system_prompt: true,
    no_answer_message:
      "Thông tin này chưa có trong nguồn chính thức. Vui lòng liên hệ đơn vị phụ trách để được hỗ trợ.",
  },
  tools: { enabled_tools: [], human_approval_required: true },
  output_policy: {
    formats: ["markdown"],
    require_citations: true,
    citation_format: "Tên văn bản, Điều/Khoản, Trang",
  },
  evaluation_policy: {
    faithfulness_threshold: 0.9,
    answer_relevance_threshold: 0.85,
    context_precision_threshold: 0.8,
  },
};

const EMPTY_INPUT: AssistantInput = {
  code: "",
  name: "",
  description: "",
  category: "academic",
  system_prompt: "",
  workflow_id: "",
  collection_id: "",
  is_active: true,
  tenant_id: "tenant_qnu",
  config: DEFAULT_CONFIG,
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Không thể tạo trợ lý.";
}

function toInput(template: AssistantTemplate): AssistantInput {
  return {
    code: template.code,
    name: template.name,
    description: template.description,
    category: template.category,
    system_prompt: template.system_prompt,
    workflow_id: template.workflow_id,
    collection_id: template.collection_id,
    is_active: true,
    tenant_id: "tenant_qnu",
    config: structuredClone(template.config),
  };
}

function PolicySwitch({
  checked,
  label,
  description,
  onCheckedChange,
}: {
  checked: boolean;
  label: string;
  description: string;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-md border border-border p-3">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
      </div>
      <Switch checked={checked} aria-label={label} onCheckedChange={onCheckedChange} />
    </div>
  );
}

export function AssistantCreatePage({ onNavigate }: AssistantCreatePageProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AssistantInput>(EMPTY_INPUT);
  const [selectedTemplate, setSelectedTemplate] = useState("blank");
  const templatesQuery = useQuery({
    queryKey: ["assistant-templates"],
    queryFn: listAssistantTemplates,
  });
  const collectionsQuery = useQuery({
    queryKey: ["knowledge-collections"],
    queryFn: () => apiClient.getCollections(),
  });
  const workflowsQuery = useQuery({
    queryKey: ["workflow-definitions"],
    queryFn: () => workflowsApi.listDefinitions(),
  });
  const createMutation = useMutation({
    mutationFn: createAssistant,
    onSuccess: (assistant) => {
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success(`Đã khởi tạo thành công Trợ lý “${assistant.name}”!`);
      onNavigate(`/assistants/${encodeURIComponent(assistant.code)}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Tạo trợ lý thất bại.");
    },
  });

  const updateConfig = (config: AssistantLifecycleConfig) =>
    setForm((value) => ({ ...value, config }));
  const handleTemplateChange = (code: string) => {
    setSelectedTemplate(code);
    const template = templatesQuery.data?.find((item) => item.code === code);
    setForm(template ? toInput(template) : EMPTY_INPUT);
  };
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate(form);
  };

  return (
    <form className="space-y-6" onSubmit={handleSubmit}>
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <Button
            className="mb-3 -ml-3"
            size="sm"
            type="button"
            variant="ghost"
            onClick={() => onNavigate("/assistants")}
          >
            <ArrowLeft className="size-4" />
            Danh mục trợ lý
          </Button>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Bot className="size-4 text-primary" />
            <span>Trợ lý AI / Tạo mới</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight">Tạo trợ lý AI</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Cấu hình theo vòng đời 7 bước để trợ lý có phạm vi rõ, nguồn tri thức thật và cơ chế
            chống bịa đặt ngay từ đầu.
          </p>
        </div>
        <Button disabled={createMutation.isPending} type="submit">
          <Save className="size-4" />
          {createMutation.isPending ? "Đang tạo..." : "Tạo trợ lý"}
        </Button>
      </div>

      {createMutation.error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-xs text-destructive">
          {getErrorMessage(createMutation.error)}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle>1. Persona & phạm vi</CardTitle>
              <CardDescription>Chọn mẫu Core hoặc bắt đầu với cấu hình trống.</CardDescription>
            </div>
            <Badge variant="info">Bước 1/7</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <Field className="lg:col-span-2" htmlFor="assistant-template" label="Mẫu chuẩn">
            <Select value={selectedTemplate} onValueChange={handleTemplateChange}>
              <SelectTrigger id="assistant-template">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="blank">Cấu hình trống</SelectItem>
                {(templatesQuery.data ?? []).map((template) => (
                  <SelectItem key={template.code} value={template.code}>
                    {template.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field htmlFor="assistant-code" label="Mã trợ lý" required>
            <Input
              id="assistant-code"
              pattern="[a-z0-9]+(?:[-_][a-z0-9]+)*"
              placeholder="student-support"
              required
              value={form.code}
              onChange={(event) => setForm((value) => ({ ...value, code: event.target.value }))}
            />
          </Field>
          <Field htmlFor="assistant-name" label="Tên hiển thị" required>
            <Input
              id="assistant-name"
              required
              value={form.name}
              onChange={(event) => setForm((value) => ({ ...value, name: event.target.value }))}
            />
          </Field>
          <Field className="lg:col-span-2" htmlFor="assistant-description" label="Mô tả" required>
            <Textarea
              id="assistant-description"
              required
              value={form.description}
              onChange={(event) =>
                setForm((value) => ({ ...value, description: event.target.value }))
              }
            />
          </Field>
          <Field htmlFor="assistant-category" label="Lĩnh vực chuyên môn" required>
            <Select
              value={form.category}
              onValueChange={(cat) => setForm((value) => ({ ...value, category: cat }))}
            >
              <SelectTrigger id="assistant-category">
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
          <Field htmlFor="assistant-persona" label="Tư cách trợ lý" required>
            <Input
              id="assistant-persona"
              required
              value={form.config.persona_scope.persona}
              onChange={(event) =>
                updateConfig({
                  ...form.config,
                  persona_scope: { ...form.config.persona_scope, persona: event.target.value },
                })
              }
            />
          </Field>
          <Field
            className="lg:col-span-2"
            htmlFor="assistant-prompt"
            label="System prompt"
            required
          >
            <Textarea
              className="min-h-36"
              id="assistant-prompt"
              required
              value={form.system_prompt}
              onChange={(event) =>
                setForm((value) => ({ ...value, system_prompt: event.target.value }))
              }
            />
          </Field>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>2. Knowledge & RAG</CardTitle>
            <CardDescription>Gắn kho tri thức thật và chiến lược chunking.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field htmlFor="assistant-collection" label="Kho tri thức" required>
              <Select
                value={form.collection_id}
                onValueChange={(collectionId) =>
                  setForm((value) => ({ ...value, collection_id: collectionId }))
                }
              >
                <SelectTrigger id="assistant-collection">
                  <SelectValue placeholder="Chọn kho tri thức" />
                </SelectTrigger>
                <SelectContent>
                  {(collectionsQuery.data ?? []).map((collection) => (
                    <SelectItem key={collection.id} value={collection.id}>
                      {collection.name} ({collection.document_count} tài liệu)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field htmlFor="assistant-chunking" label="Chiến lược chunking">
              <Select
                value={form.config.knowledge_policy.chunking_strategy}
                onValueChange={(strategy) =>
                  updateConfig({
                    ...form.config,
                    knowledge_policy: {
                      ...form.config.knowledge_policy,
                      chunking_strategy: strategy as "ClauseBasedChunker" | "SemanticChunker",
                    },
                  })
                }
              >
                <SelectTrigger id="assistant-chunking">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="SemanticChunker">
                    SemanticChunker (Cẩm nang / Đoạn văn)
                  </SelectItem>
                  <SelectItem value="ClauseBasedChunker">
                    ClauseBasedChunker (Quy chế / Điều khoản)
                  </SelectItem>
                </SelectContent>
              </Select>
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>3. ModelOps & fallback</CardTitle>
            <CardDescription>Mô hình chính, dự phòng và tham số sinh.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field htmlFor="assistant-primary-model" label="Mô hình chính (Primary)" required>
              <Select
                value={form.config.model_policy.primary_model}
                onValueChange={(val) =>
                  updateConfig({
                    ...form.config,
                    model_policy: {
                      ...form.config.model_policy,
                      primary_model: val,
                    },
                  })
                }
              >
                <SelectTrigger id="assistant-primary-model">
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

            <Field htmlFor="assistant-fallback-model" label="Mô hình dự phòng (Fallback)" required>
              <Select
                value={form.config.model_policy.fallback_model}
                onValueChange={(val) =>
                  updateConfig({
                    ...form.config,
                    model_policy: {
                      ...form.config.model_policy,
                      fallback_model: val,
                    },
                  })
                }
              >
                <SelectTrigger id="assistant-fallback-model">
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
            <Field htmlFor="assistant-temperature" label="Temperature">
              <Input
                id="assistant-temperature"
                max="2"
                min="0"
                step="0.1"
                type="number"
                value={form.config.model_policy.temperature}
                onChange={(event) =>
                  updateConfig({
                    ...form.config,
                    model_policy: {
                      ...form.config.model_policy,
                      temperature: Number(event.target.value),
                    },
                  })
                }
              />
            </Field>
            <Field htmlFor="assistant-max-tokens" label="Max tokens">
              <Input
                id="assistant-max-tokens"
                min="128"
                type="number"
                value={form.config.model_policy.max_tokens}
                onChange={(event) =>
                  updateConfig({
                    ...form.config,
                    model_policy: {
                      ...form.config.model_policy,
                      max_tokens: Number(event.target.value),
                    },
                  })
                }
              />
            </Field>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-primary" />
            <CardTitle>4–7. Guardrails, công cụ, đầu ra & đánh giá</CardTitle>
          </div>
          <CardDescription>
            Các kiểm soát production bắt buộc trước khi đưa trợ lý vào dùng.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-2">
          <PolicySwitch
            checked={form.config.guardrails.require_grounded_answer}
            description="Không trả lời khi không có căn cứ từ kho tri thức."
            label="Bắt buộc grounded answer"
            onCheckedChange={(checked) =>
              updateConfig({
                ...form.config,
                guardrails: { ...form.config.guardrails, require_grounded_answer: checked },
              })
            }
          />
          <PolicySwitch
            checked={form.config.guardrails.mask_pii}
            description="Che CCCD, số điện thoại và email trong dữ liệu nhạy cảm."
            label="Che dữ liệu cá nhân"
            onCheckedChange={(checked) =>
              updateConfig({
                ...form.config,
                guardrails: { ...form.config.guardrails, mask_pii: checked },
              })
            }
          />
          <PolicySwitch
            checked={form.config.tools.human_approval_required}
            description="Các công cụ thay đổi dữ liệu cần cán bộ phê duyệt."
            label="Human-in-the-loop"
            onCheckedChange={(checked) =>
              updateConfig({
                ...form.config,
                tools: { ...form.config.tools, human_approval_required: checked },
              })
            }
          />
          <PolicySwitch
            checked={form.config.output_policy.require_citations}
            description="Hiển thị văn bản, Điều/Khoản và trang nguồn."
            label="Bắt buộc trích dẫn"
            onCheckedChange={(checked) =>
              updateConfig({
                ...form.config,
                output_policy: { ...form.config.output_policy, require_citations: checked },
              })
            }
          />
          <Field className="lg:col-span-2" htmlFor="assistant-no-answer" label="No-answer policy">
            <Textarea
              id="assistant-no-answer"
              value={form.config.guardrails.no_answer_message}
              onChange={(event) =>
                updateConfig({
                  ...form.config,
                  guardrails: {
                    ...form.config.guardrails,
                    no_answer_message: event.target.value,
                  },
                })
              }
            />
          </Field>
          <Field
            className="lg:col-span-2"
            htmlFor="assistant-questions"
            hint="Mỗi dòng là một câu hỏi gợi ý."
            label="Câu hỏi mẫu"
          >
            <Textarea
              id="assistant-questions"
              value={form.config.sample_questions.join("\n")}
              onChange={(event) => {
                const questions = event.target.value
                  .split("\n")
                  .map((question) => question.trim())
                  .filter(Boolean);
                updateConfig({ ...form.config, sample_questions: questions });
              }}
            />
          </Field>
          <div className="lg:col-span-2 grid gap-3 sm:grid-cols-3">
            {[
              ["Faithfulness", form.config.evaluation_policy.faithfulness_threshold],
              ["Answer relevance", form.config.evaluation_policy.answer_relevance_threshold],
              ["Context precision", form.config.evaluation_policy.context_precision_threshold],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="mt-1 text-lg font-semibold">≥ {value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quy Trình Điều Phối (Workflow DAG)</CardTitle>
          <CardDescription>
            Đồ thị DAG chịu trách nhiệm điều phối luồng hội thoại và công cụ cho Trợ lý.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Field htmlFor="assistant-workflow" label="Chọn Quy Trình Workflow" required>
            <Select
              value={form.workflow_id}
              onValueChange={(wfId) => setForm((value) => ({ ...value, workflow_id: wfId }))}
            >
              <SelectTrigger id="assistant-workflow">
                <SelectValue placeholder="Chọn quy trình workflow" />
              </SelectTrigger>
              <SelectContent>
                {(workflowsQuery.data ?? []).map((wf) => (
                  <SelectItem key={wf.id} value={wf.id}>
                    {wf.display_name} ({wf.id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </CardContent>
      </Card>
    </form>
  );
}
