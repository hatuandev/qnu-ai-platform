import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Field } from "@/components/admin/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { AssistantItem } from "@/services/api-client";
import {
  deactivateAssistant,
  exportAssistantBundle,
  getAssistant,
  updateAssistant,
} from "@/services/assistants-api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Bot,
  Download,
  Library,
  MessageSquare,
  Network,
  Power,
  Save,
  ShieldCheck,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

interface AssistantDetailPageProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

interface AssistantEditForm {
  name: string;
  description: string;
  category: string;
  system_prompt: string;
  workflow_id: string;
  collection_id: string;
  primary_model: string;
  fallback_model: string;
  temperature: number;
  max_tokens: number;
  no_answer_message: string;
}

function getReferenceFromPath(currentPath: string): string {
  return decodeURIComponent(currentPath.split("/").filter(Boolean).at(-1) ?? "");
}

function toEditForm(item: AssistantItem): AssistantEditForm {
  return {
    name: item.name,
    description: item.description,
    category: item.category,
    system_prompt: item.system_prompt,
    workflow_id: item.workflow_id,
    collection_id: item.collection_id,
    primary_model: item.config.model_policy.primary_model,
    fallback_model: item.config.model_policy.fallback_model,
    temperature: item.config.model_policy.temperature,
    max_tokens: item.config.model_policy.max_tokens,
    no_answer_message: item.config.guardrails.no_answer_message,
  };
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Không thể hoàn thành thao tác trợ lý.";
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

function PolicySummary({ item }: { item: AssistantItem }) {
  const config = item.config;
  const policies = [
    ["Prompt injection", config.guardrails.block_prompt_injection],
    ["Che dữ liệu cá nhân", config.guardrails.mask_pii],
    ["Grounded answer", config.guardrails.require_grounded_answer],
    ["Bảo vệ system prompt", config.guardrails.protect_system_prompt],
    ["Human-in-the-loop", config.tools.human_approval_required],
    ["Bắt buộc trích dẫn", config.output_policy.require_citations],
  ] as const;
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {policies.map(([label, enabled]) => (
        <div
          key={label}
          className="flex items-center justify-between rounded-md border p-3 text-xs"
        >
          <span>{label}</span>
          <Badge variant={enabled ? "success" : "secondary"}>{enabled ? "Bật" : "Tắt"}</Badge>
        </div>
      ))}
    </div>
  );
}

export function AssistantDetailPage({ currentPath, onNavigate }: AssistantDetailPageProps) {
  const reference = getReferenceFromPath(currentPath);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AssistantEditForm | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const assistantQuery = useQuery({
    queryKey: ["assistants", reference],
    queryFn: () => getAssistant(reference),
    enabled: Boolean(reference),
  });

  useEffect(() => {
    if (assistantQuery.data) setForm(toEditForm(assistantQuery.data));
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
          model_policy: {
            ...current.config.model_policy,
            primary_model: value.primary_model,
            fallback_model: value.fallback_model,
            temperature: value.temperature,
            max_tokens: value.max_tokens,
          },
          guardrails: {
            ...current.config.guardrails,
            no_answer_message: value.no_answer_message,
          },
        },
      });
    },
    onSuccess: (assistant) => {
      queryClient.setQueryData(["assistants", reference], assistant);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      setForm(toEditForm(assistant));
      setFeedback("Đã cập nhật cấu hình trợ lý.");
    },
  });
  const deactivateMutation = useMutation({
    mutationFn: () => deactivateAssistant(reference),
    onSuccess: (assistant) => {
      queryClient.setQueryData(["assistants", reference], assistant);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      setFeedback("Đã vô hiệu hóa trợ lý. Lịch sử và workflow vẫn được giữ nguyên.");
    },
  });
  const exportMutation = useMutation({
    mutationFn: () => exportAssistantBundle(reference),
    onSuccess: (bundle) => {
      downloadBundle(`${bundle.assistant.code}.qnu.bundle.json`, bundle);
      setFeedback("Đã xuất bundle trợ lý.");
    },
  });

  const item = assistantQuery.data;
  const error =
    assistantQuery.error ||
    updateMutation.error ||
    deactivateMutation.error ||
    exportMutation.error;
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form) return;
    setFeedback(null);
    updateMutation.mutate(form);
  };

  if (assistantQuery.isLoading) {
    return (
      <div className="py-16 text-center text-sm text-muted-foreground">Đang tải trợ lý...</div>
    );
  }
  if (!item || !form) {
    return (
      <Card>
        <CardContent className="space-y-4 p-8">
          <p className="font-medium">Không tải được trợ lý</p>
          <p className="text-xs text-muted-foreground">
            {error ? getErrorMessage(error) : "Mã trợ lý không hợp lệ."}
          </p>
          <Button variant="outline" onClick={() => onNavigate("/assistants")}>
            <ArrowLeft className="size-4" />
            Quay lại danh mục
          </Button>
        </CardContent>
      </Card>
    );
  }

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
            <span>Trợ lý AI / {item.code}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{item.name}</h1>
            <Badge variant={item.is_active ? "success" : "secondary"}>
              {item.is_active ? "Hoạt động" : "Đã tắt"}
            </Badge>
            <Badge variant="info">{item.category}</Badge>
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{item.id}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onNavigate(`/chat?assistant=${encodeURIComponent(item.code)}`)}
          >
            <MessageSquare className="size-4" />
            Thử chat
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => onNavigate(`/canvas?assistant=${encodeURIComponent(item.code)}`)}
          >
            <Network className="size-4" />
            Mở DAG
          </Button>
          <Button type="button" variant="outline" onClick={() => exportMutation.mutate()}>
            <Download className="size-4" />
            Xuất bundle
          </Button>
          <Button disabled={updateMutation.isPending} type="submit">
            <Save className="size-4" />
            {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
          </Button>
        </div>
      </div>

      {feedback ? (
        <div className="rounded-md border border-success/30 bg-success/10 px-4 py-3 text-xs text-success">
          {feedback}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-xs text-destructive">
          {getErrorMessage(error)}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(20rem,0.8fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Thông tin & persona</CardTitle>
            <CardDescription>
              Cấu hình nhận diện, phạm vi và system prompt của trợ lý.
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
            <Field htmlFor="detail-assistant-category" label="Lĩnh vực" required>
              <Input
                id="detail-assistant-category"
                required
                value={form.category}
                onChange={(event) => setForm({ ...form, category: event.target.value })}
              />
            </Field>
            <Field className="sm:col-span-2" htmlFor="detail-assistant-description" label="Mô tả">
              <Textarea
                id="detail-assistant-description"
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </Field>
            <Field
              className="sm:col-span-2"
              htmlFor="detail-assistant-prompt"
              label="System prompt"
            >
              <Textarea
                className="min-h-48"
                id="detail-assistant-prompt"
                value={form.system_prompt}
                onChange={(event) => setForm({ ...form, system_prompt: event.target.value })}
              />
            </Field>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Liên kết vận hành</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field htmlFor="detail-assistant-collection" label="Collection ID">
                <Input
                  id="detail-assistant-collection"
                  value={form.collection_id}
                  onChange={(event) => setForm({ ...form, collection_id: event.target.value })}
                />
              </Field>
              <Field htmlFor="detail-assistant-workflow" label="Workflow ID">
                <Input
                  id="detail-assistant-workflow"
                  value={form.workflow_id}
                  onChange={(event) => setForm({ ...form, workflow_id: event.target.value })}
                />
              </Field>
              <Button
                className="w-full"
                type="button"
                variant="outline"
                onClick={() => onNavigate(`/knowledge/${encodeURIComponent(item.collection_id)}`)}
              >
                <Library className="size-4" />
                Mở kho tri thức
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Câu hỏi gợi ý</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {item.sample_questions.map((question) => (
                <div
                  key={question}
                  className="rounded-md border border-border bg-muted/20 p-3 text-xs"
                >
                  {question}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>ModelOps & fallback</CardTitle>
            <CardDescription>
              Chỉ tham chiếu model ID; khóa bí mật vẫn do Provider quản lý.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field htmlFor="detail-primary-model" label="Mô hình chính">
              <Input
                id="detail-primary-model"
                value={form.primary_model}
                onChange={(event) => setForm({ ...form, primary_model: event.target.value })}
              />
            </Field>
            <Field htmlFor="detail-fallback-model" label="Mô hình dự phòng">
              <Input
                id="detail-fallback-model"
                value={form.fallback_model}
                onChange={(event) => setForm({ ...form, fallback_model: event.target.value })}
              />
            </Field>
            <Field htmlFor="detail-temperature" label="Temperature">
              <Input
                id="detail-temperature"
                max="2"
                min="0"
                step="0.1"
                type="number"
                value={form.temperature}
                onChange={(event) => setForm({ ...form, temperature: Number(event.target.value) })}
              />
            </Field>
            <Field htmlFor="detail-max-tokens" label="Max tokens">
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

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-primary" />
              <CardTitle>Guardrails & đánh giá</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <PolicySummary item={item} />
            <Field htmlFor="detail-no-answer" label="No-answer policy">
              <Textarea
                id="detail-no-answer"
                value={form.no_answer_message}
                onChange={(event) => setForm({ ...form, no_answer_message: event.target.value })}
              />
            </Field>
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded-md border p-3 text-center text-xs">
                Faithfulness ≥ {item.config.evaluation_policy.faithfulness_threshold}
              </div>
              <div className="rounded-md border p-3 text-center text-xs">
                Relevance ≥ {item.config.evaluation_policy.answer_relevance_threshold}
              </div>
              <div className="rounded-md border p-3 text-center text-xs">
                Precision ≥ {item.config.evaluation_policy.context_precision_threshold}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle>Vùng nguy hiểm</CardTitle>
          <CardDescription>
            Vô hiệu hóa trợ lý nhưng giữ lại workflow và lịch sử kiểm toán.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ConfirmDialog
            confirmText="Vô hiệu hóa"
            description={`Trợ lý “${item.name}” sẽ không còn nhận hội thoại mới.`}
            isPending={deactivateMutation.isPending}
            title="Vô hiệu hóa trợ lý?"
            trigger={
              <Button disabled={!item.is_active} type="button" variant="destructive">
                <Power className="size-4" />
                Vô hiệu hóa
              </Button>
            }
            onConfirm={() => deactivateMutation.mutate()}
          />
        </CardContent>
      </Card>
    </form>
  );
}
