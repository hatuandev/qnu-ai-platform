import { useQueryClient } from "@tanstack/react-query";
import {
  Eye,
  FilePlus2,
  FileSpreadsheet,
  FileText,
  Loader2,
  Pencil,
  Save,
  Sparkles,
  Undo2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  type AssistantReadiness,
  type AssistantResponse,
  assistantKeys,
  useUpdateAssistantMutation,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import { useCollectionsQuery } from "@/api/knowledge";
import { useCatalogQuery } from "@/api/modelops";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { MarkdownContent } from "@/components/knowledge/markdown-content";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn, sanitizeDisplayText } from "@/lib/utils";
import {
  ContextFields,
  FieldHelpTooltip,
  type RagPolicyFormState,
  RetrievalFields,
  VERIFICATION_OPTIONS,
  VerificationFields,
} from "./assistant-advanced-fields";
import {
  AssistantCollectionPicker,
  type CollectionOption,
} from "./assistant-collection-picker";
import { AssistantPersonaCraftDialog } from "./assistant-persona-craft-dialog";
import {
  type AssistantFormState,
  AUTO_MODEL,
  buildAssistantPayload,
  collectionIdsOf,
  initialState,
  NAME_MAX_CHARS,
  PERSONA_MAX_CHARS,
  validateAssistantForm,
} from "./assistant-form-state";
import { localityLabel, providerLabel } from "./model-label";
import { READINESS_MAP } from "./readiness";

const FLEXIBLE_DRAFTING_PERSONA_SNIPPET = `## Nguyên tắc soạn thảo văn bản & tạo mẫu linh hoạt
- Tự nắm bắt mục đích người dùng để dựng bố cục phù hợp từng loại văn bản (kế hoạch, tờ trình, báo cáo, quy chế/quy định, thông báo, đơn xin/giấy nghỉ phép, bảng biểu tổng hợp...).
- Chỉ dùng kiến thức nền để tổ chức bố cục, văn phong và khung mẫu văn bản.
- Tuyệt đối không tự suy đoán hoặc bịa thông tin thực tế của đơn vị/nhà trường (cơ cấu tổ chức, khoa/viện, ngành đào tạo, số liệu, quy định, mốc thời gian) nếu không có trong ngữ cảnh hoặc người dùng chưa cung cấp; sử dụng chỗ giữ chỗ dạng [...] cho phần cần điền hoặc đề nghị người dùng bổ sung dữ kiện.
- Tách bạch rõ lời trao đổi ngắn gọn với thân văn bản chính để bản thảo sạch sẽ, sẵn sàng xem trước và xuất tệp.`;

type Baseline = { revision: number; data: AssistantResponse };

function formatTokenK(tokens: number): string {
  if (tokens >= 1024) {
    const k = tokens / 1024;
    return Number.isInteger(k) ? `~${k}K` : `~${k.toFixed(1)}K`;
  }
  return `${tokens}`;
}

export function AssistantConfigForm({
  workspaceId,
  assistant,
  readiness,
}: {
  workspaceId: string;
  assistant: AssistantResponse;
  readiness?: AssistantReadiness;
}) {
  const queryClient = useQueryClient();
  const updateMutation = useUpdateAssistantMutation(workspaceId);
  const { data: collectionsPage } = useCollectionsQuery(workspaceId, {
    page: 1,
    pageSize: 100,
  });
  const { data: catalog = [] } = useCatalogQuery(workspaceId);
  const chatModels = useMemo(
    () => catalog.filter((item) => item.capabilities.includes("chat")),
    [catalog],
  );
  const rerankModels = useMemo(
    () => catalog.filter((item) => item.capabilities.includes("rerank")),
    [catalog],
  );
  const collections = collectionsPage?.items ?? [];

  const [baseline, setBaseline] = useState<Baseline>({
    revision: assistant.revision,
    data: assistant,
  });
  const [form, setForm] = useState<AssistantFormState>(() =>
    initialState(assistant),
  );
  const [error, setError] = useState<string | null>(null);
  const [isCollectionConfirmOpen, setIsCollectionConfirmOpen] = useState(false);
  const [isPersonaCraftOpen, setIsPersonaCraftOpen] = useState(false);
  const [personaMode, setPersonaMode] = useState<"edit" | "preview">("edit");

  const handleApplyCraftedPersona = (crafted: {
    name?: string;
    description?: string;
    persona?: string;
    suggestedPrompts?: string[];
  }) => {
    patch({
      ...(crafted.name ? { name: crafted.name } : {}),
      ...(crafted.description ? { description: crafted.description } : {}),
      ...(crafted.persona ? { persona: crafted.persona } : {}),
      ...(crafted.suggestedPrompts
        ? { suggestedPrompts: crafted.suggestedPrompts }
        : {}),
    });
  };

  const baselineCollectionIds = useMemo(
    () => collectionIdsOf(baseline.data),
    [baseline.data],
  );
  const collectionOptions = useMemo<CollectionOption[]>(() => {
    const options: CollectionOption[] = collections.map((item) => ({
      id: item.id,
      name: sanitizeDisplayText(item.name),
      source_count: item.source_count,
    }));
    const missing = form.collectionIds
      .filter((id) => !options.some((item) => item.id === id))
      .map((id) => ({
        id,
        name: "Kho ngoài danh sách tải",
        source_count: 0,
      }));
    return [...missing, ...options];
  }, [collections, form.collectionIds]);
  const isCollectionChanged =
    form.collectionIds.length !== baselineCollectionIds.length ||
    form.collectionIds.some((id, index) => id !== baselineCollectionIds[index]);
  const selectedCollectionNames =
    form.collectionIds
      .map((id) => collectionOptions.find((item) => item.id === id)?.name)
      .filter((name): name is string => Boolean(name))
      .join(", ") || "bộ kho đã chọn";
  const degradedCollections = (readiness?.collections ?? []).filter(
    (item) =>
      item.status !== "ready" &&
      form.collectionIds.includes(item.collection_id),
  );

  const initialForm = useMemo(() => initialState(baseline.data), [baseline]);
  const isDirty = useMemo(
    () => JSON.stringify(form) !== JSON.stringify(initialForm),
    [form, initialForm],
  );
  const isStale = assistant.revision !== baseline.revision;
  const isPending = updateMutation.isPending;

  useEffect(() => {
    if (assistant.revision === baseline.revision) return;
    if (isDirty) return;
    setBaseline({ revision: assistant.revision, data: assistant });
    setForm(initialState(assistant));
  }, [assistant, baseline.revision, isDirty]);

  const patch = (values: Partial<AssistantFormState>) =>
    setForm((prev) => ({ ...prev, ...values }));
  const patchPolicy = (values: Partial<RagPolicyFormState>) =>
    setForm((prev) => ({ ...prev, policy: { ...prev.policy, ...values } }));

  const handleReset = () => {
    setForm(initialForm);
    setError(null);
  };

  const handleReload = () => {
    setBaseline({ revision: assistant.revision, data: assistant });
    setForm(initialState(assistant));
    setError(null);
  };

  const runSave = async () => {
    try {
      const updated = await updateMutation.mutateAsync({
        assistantId: assistant.id,
        data: {
          ...buildAssistantPayload(form, baseline.data.rag_policy),
          expected_revision: baseline.revision,
        },
      });
      setBaseline({ revision: updated.revision, data: updated });
      setForm(initialState(updated));
      setIsCollectionConfirmOpen(false);
      toast.success(`Đã lưu cấu hình "${updated.name}"`);
    } catch (err: unknown) {
      setIsCollectionConfirmOpen(false);
      if (err instanceof ApiProblemError) {
        if (err.code === "assistant_revision_conflict") {
          await queryClient.invalidateQueries({
            queryKey: assistantKeys.detail(workspaceId, assistant.id),
          });
          setError(
            "Cấu hình trợ lý vừa được người khác cập nhật. Bản chỉnh sửa của bạn vẫn được giữ; hãy tải lại cấu hình để đối chiếu trước khi lưu tiếp.",
          );
          return;
        }
        if (err.kind === "forbidden") {
          setError("Chỉ quản trị viên của đơn vị mới có thể thay đổi trợ lý.");
          return;
        }
        if (err.problem?.errors) {
          const fieldMsgs = Object.entries(err.problem.errors)
            .map(([field, msgs]) => `${field}: ${msgs.join(", ")}`)
            .join("; ");
          setError(`${err.message} (${fieldMsgs})`);
          return;
        }
        setError(err.message);
        return;
      }
      setError("Có lỗi xảy ra. Vui lòng thử lại.");
    }
  };

  const handleSave = () => {
    const message = validateAssistantForm(form);
    if (message) {
      setError(message);
      return;
    }
    setError(null);
    if (isCollectionChanged) {
      setIsCollectionConfirmOpen(true);
      return;
    }
    void runSave();
  };

  const verificationLabel =
    VERIFICATION_OPTIONS.find(
      (option) => option.value === assistant.rag_policy.verification_mode,
    )?.label ?? "Tắt";

  return (
    <TooltipProvider delayDuration={180}>
      <div className="space-y-4">
      {isStale ? (
        <Alert variant="warning">
          <AlertTitle>Cấu hình đã thay đổi ở nơi khác</AlertTitle>
          <AlertDescription>
            <span>
              Phiên bản hiện tại là {assistant.revision}, bản bạn đang sửa dựa
              trên phiên bản {baseline.revision}. Lưu sẽ bị chặn cho tới khi bạn
              tải lại.
            </span>
            <Button
              variant="outline"
              size="sm"
              className="mt-2 h-7 text-xs"
              disabled={isPending}
              onClick={handleReload}
            >
              Tải lại cấu hình
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Chưa lưu được cấu hình</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {isCollectionChanged ? (
        <Alert variant="warning">
          <AlertTitle>Trợ lý sẽ đổi bộ kho tri thức</AlertTitle>
          <AlertDescription>
            {`Sau khi lưu, lượt hỏi mới sẽ tra cứu trong: ${selectedCollectionNames}. Hội thoại đã có giữ bộ kho cũ, vẫn đọc lại được, nhưng hỏi tiếp cần hội thoại mới.`}
          </AlertDescription>
        </Alert>
      ) : null}

      {form.collectionIds.length === 0 ? (
        <Alert variant="info">
          <AlertTitle>Chế độ Hội thoại trực tiếp theo Persona</AlertTitle>
          <AlertDescription>
            Trợ lý hiện chưa liên kết kho tri thức nên đang hoạt động ở chế độ
            hội thoại trực tiếp theo Persona — vẫn trả lời, hỏi thử, soạn thảo /
            tạo mẫu và xuất tệp bình thường. Chỉ cần liên kết kho tri thức khi
            muốn trợ lý tra cứu bám sát tài liệu nội bộ.
          </AlertDescription>
        </Alert>
      ) : null}

      {degradedCollections.length > 0 ? (
        <Alert variant="warning">
          <AlertTitle>Có kho tri thức chưa sẵn sàng</AlertTitle>
          <AlertDescription>
            <span className="block">
              {degradedCollections
                .map(
                  (item) =>
                    `${item.collection_name}: ${READINESS_MAP[item.status].label.toLowerCase()}`,
                )
                .join(" · ")}
            </span>
            <span className="mt-1 block text-[11px]">
              Trợ lý vẫn trả lời bằng các kho còn lại; câu hỏi chỉ có đáp án
              trong kho chưa sẵn sàng sẽ được báo là thiếu căn cứ.
            </span>
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid grid-cols-1 items-stretch gap-6 lg:grid-cols-12">
        {/* Cột trái (7/12): Tên trợ lý & Chỉ dẫn ứng xử (Persona) */}
        <div className="flex flex-col rounded-xl border border-border/60 bg-card p-5 shadow-2xs space-y-4 lg:col-span-7">
          <Field>
            <FieldLabel required className="text-xs font-medium">
              Tên trợ lý
            </FieldLabel>
            <Input
              value={form.name}
              onChange={(event) => patch({ name: event.target.value })}
              maxLength={NAME_MAX_CHARS}
              placeholder="VD: Trợ lý Tuyển sinh 2026..."
              className="h-9 bg-background text-xs"
              disabled={isPending}
            />
          </Field>

          <Field className="flex flex-1 flex-col border-t border-border/50 pt-4">
            <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
              <FieldLabel className="text-xs font-medium">
                Chỉ dẫn cho trợ lý (Persona)
              </FieldLabel>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 rounded-md border border-border/70 bg-muted/50 p-0.5 text-[11px]">
                  <button
                    type="button"
                    onClick={() => setPersonaMode("edit")}
                    className={cn(
                      "inline-flex cursor-pointer items-center gap-1 rounded px-2 py-0.5 font-medium transition-colors",
                      personaMode === "edit"
                        ? "bg-card text-foreground shadow-2xs"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <Pencil className="size-3" />
                    <span>Soạn thảo</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPersonaMode("preview")}
                    className={cn(
                      "inline-flex cursor-pointer items-center gap-1 rounded px-2 py-0.5 font-medium transition-colors",
                      personaMode === "preview"
                        ? "bg-card text-foreground shadow-2xs"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <Eye className="size-3" />
                    <span>Xem Markdown</span>
                  </button>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1 px-2 text-[11px] cursor-pointer"
                  disabled={isPending}
                  onClick={() => {
                    if (form.persona.includes("Nguyên tắc soạn thảo văn bản")) {
                      toast.info("Quy tắc soạn thảo đã có trong chỉ dẫn.");
                      return;
                    }
                    const nextPersona = form.persona.trim()
                      ? `${form.persona.trim()}\n\n${FLEXIBLE_DRAFTING_PERSONA_SNIPPET}`
                      : FLEXIBLE_DRAFTING_PERSONA_SNIPPET;
                    patch({
                      persona: nextPersona.slice(0, PERSONA_MAX_CHARS),
                    });
                    setPersonaMode("edit");
                    toast.success("Đã chèn quy tắc soạn thảo linh hoạt.");
                  }}
                >
                  <FilePlus2 className="size-3 text-primary" />
                  <span>Quy tắc soạn thảo</span>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1 px-2 text-[11px] cursor-pointer"
                  disabled={isPending}
                  onClick={() => setIsPersonaCraftOpen(true)}
                >
                  <Sparkles className="size-3 text-primary" />
                  <span>Soạn bằng AI</span>
                </Button>
              </div>
            </div>

            {personaMode === "edit" ? (
              <Textarea
                value={form.persona}
                onChange={(event) => patch({ persona: event.target.value })}
                maxLength={PERSONA_MAX_CHARS}
                placeholder="Định hình vai trò, phong cách xưng hô và nguyên tắc trả lời (hỗ trợ Markdown)..."
                rows={16}
                className="min-h-[360px] flex-1 max-h-[640px] resize-y bg-background text-xs leading-relaxed"
                disabled={isPending}
              />
            ) : (
              <div className="min-h-[360px] flex-1 max-h-[640px] overflow-y-auto rounded-md border border-input bg-muted/20 px-4 py-3 text-xs">
                {form.persona.trim() ? (
                  <MarkdownContent content={form.persona} />
                ) : (
                  <p className="text-muted-foreground italic">
                    Chưa có chỉ dẫn nào. Chuyển sang Soạn thảo để nhập nội dung.
                  </p>
                )}
              </div>
            )}

            <div className="flex items-center justify-between gap-2">
              <FieldDescription>
                Định hình văn phong và nguyên tắc trả lời (hỗ trợ Markdown).
              </FieldDescription>
              <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
                {form.persona.length.toLocaleString("vi-VN")}/
                {PERSONA_MAX_CHARS.toLocaleString("vi-VN")}
              </span>
            </div>
          </Field>
        </div>

        {/* Cột phải (5/12): Trạng thái, Kho tri thức, Mô hình, Tham số & Nâng cao */}
        <div className="rounded-xl border border-border/60 bg-card divide-y divide-border/60 shadow-2xs lg:col-span-5">
          {/* 1. Trạng thái phục vụ */}
          <div className="flex items-center justify-between gap-3 px-4 py-3.5">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Label
                  htmlFor="assistant-active-switch"
                  className="text-xs font-semibold text-foreground cursor-pointer"
                >
                  Tiếp nhận câu hỏi
                </Label>
                {form.isActive ? (
                  <Badge
                    variant="success"
                    className="h-5 gap-1.5 px-2 text-[10px] font-medium"
                  >
                    <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Đang hoạt động
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="h-5 px-2 text-[10px] font-medium text-muted-foreground"
                  >
                    Tạm dừng
                  </Badge>
                )}
              </div>
              <p
                className="mt-0.5 text-[11px] text-muted-foreground truncate"
                title={
                  form.isActive
                    ? "Trợ lý đang sẵn sàng tiếp nhận câu hỏi qua các kênh được phân quyền."
                    : "Các yêu cầu mới sẽ bị từ chối khi tạm dừng."
                }
              >
                {form.isActive
                  ? "Sẵn sàng phục vụ các kênh được phân quyền."
                  : "Đang tạm dừng tiếp nhận yêu cầu mới."}
              </p>
            </div>
            <Switch
              id="assistant-active-switch"
              checked={form.isActive}
              onCheckedChange={(checked) => patch({ isActive: checked })}
              disabled={isPending}
            />
          </div>

          {/* 2. Kho tri thức & Mô hình trả lời */}
          <div className="space-y-3.5 px-4 py-4">
            <Field className="min-w-0">
              <div className="flex items-center gap-1.5">
                <FieldLabel className="text-xs font-medium">
                  Kho tri thức liên kết
                </FieldLabel>
                <FieldHelpTooltip text="Chọn các kho tài liệu trợ lý được phép tra cứu. Nếu để trống, trợ lý trò chuyện trực tiếp theo Persona mà không đối soát tài liệu." />
              </div>
              <AssistantCollectionPicker
                collections={collectionOptions}
                selectedIds={form.collectionIds}
                onChange={(ids) => patch({ collectionIds: ids })}
                disabled={isPending}
                readiness={readiness}
              />
              {form.collectionIds.length === 0 ? (
                <FieldDescription className="text-[11px]">
                  Chế độ hội thoại trực tiếp theo Persona.
                </FieldDescription>
              ) : null}
            </Field>

            <Field className="min-w-0">
              <div className="flex items-center gap-1.5">
                <FieldLabel className="text-xs font-medium">
                  Mô hình trả lời
                </FieldLabel>
                <FieldHelpTooltip text="Mô hình ngôn ngữ dùng để tổng hợp câu trả lời. Chọn 'Tự động' để dùng mô hình mặc định của hệ thống qua ModelOps." />
              </div>
              <Select
                value={form.providerId}
                onValueChange={(value) => patch({ providerId: value })}
                disabled={isPending}
              >
                <SelectTrigger className="h-9 bg-background text-xs">
                  <SelectValue placeholder="Chọn mô hình" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={AUTO_MODEL} description="Mặc định">
                    Tự động theo hệ thống
                  </SelectItem>
                  <SelectSeparator />
                  {chatModels.map((item) => (
                    <SelectItem
                      key={item.id}
                      value={item.id}
                      description={
                        localityLabel(item.provider_type)
                          ? `${providerLabel(item)} · ${localityLabel(item.provider_type)}`
                          : providerLabel(item)
                      }
                    >
                      {item.model_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          {/* 3. Tham số cơ bản (Top-K & Lượt nhớ) */}
          <div className="space-y-4 px-4 py-4">
            {/* Số đoạn trích dẫn */}
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <FieldLabel className="text-xs font-medium text-foreground">
                    Đoạn trích dẫn (Top-K)
                  </FieldLabel>
                  <FieldHelpTooltip text="Số đoạn tài liệu tối đa được chọn làm căn cứ trả lời. Tăng lên 8–12 đoạn khi tài liệu có bảng biểu dài hoặc cần so sánh nhiều nguồn." />
                </div>
                <span className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary tabular-nums">
                  {form.topK || 5} đoạn
                </span>
              </div>
              <Slider
                min={1}
                max={20}
                step={1}
                value={[Number(form.topK) || 5]}
                onValueChange={([val]) => patch({ topK: String(val) })}
                disabled={isPending}
              />
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { label: "5 (chuẩn)", val: "5" },
                  { label: "8 (bảng biểu)", val: "8" },
                  { label: "12 (đa văn bản)", val: "12" },
                ].map((preset) => (
                  <button
                    key={preset.val}
                    type="button"
                    disabled={isPending}
                    onClick={() => patch({ topK: preset.val })}
                    className={cn(
                      "h-5 cursor-pointer rounded px-1.5 text-[10px] font-medium transition-colors",
                      form.topK === preset.val
                        ? "bg-primary font-semibold text-primary-foreground shadow-2xs"
                        : "border border-input bg-background text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Lượt nhớ lịch sử */}
            <div className="space-y-2 border-t border-border/40 pt-3.5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <FieldLabel className="text-xs font-medium text-foreground">
                    Lượt nhớ lịch sử
                  </FieldLabel>
                  <FieldHelpTooltip text="Số lượt hỏi đáp gần nhất trong cuộc trò chuyện được đưa vào ngữ cảnh để trợ lý hiểu các câu hỏi nối tiếp." />
                </div>
                <span className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary tabular-nums">
                  {Number(form.historyTurns) === 0
                    ? "Không nhớ"
                    : `${form.historyTurns} lượt`}
                </span>
              </div>
              <Slider
                min={0}
                max={10}
                step={1}
                value={[Number(form.historyTurns) || 0]}
                onValueChange={([val]) => patch({ historyTurns: String(val) })}
                disabled={isPending}
              />
              <div className="flex justify-between text-[10px] text-muted-foreground/70">
                <span>0 lượt</span>
                <span>5 lượt</span>
                <span>10 lượt</span>
              </div>
            </div>
          </div>

          {/* 4. Xuất tài liệu & Tạo mẫu (3 toggle độc lập) */}
          <div className="space-y-2.5 p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <Label className="text-xs font-semibold text-foreground">
                  Xuất tài liệu & Tạo mẫu
                </Label>
                <FieldHelpTooltip text="Bật từng định dạng cho phép trợ lý soạn thảo văn bản/mẫu linh hoạt, xem trước trực tiếp bên cạnh khung chat và tải tệp thực tế." />
              </div>
              <span className="text-[11px] text-muted-foreground">
                {[
                  form.allowExportDocx && "DOCX",
                  form.allowExportPdf && "PDF",
                  form.allowExportXlsx && "Excel",
                ]
                  .filter(Boolean)
                  .join(" · ") || "Đang tắt"}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <label
                htmlFor="export-docx-switch"
                className={cn(
                  "flex cursor-pointer items-center justify-between gap-2 rounded-lg border px-2.5 py-2 transition-colors",
                  form.allowExportDocx
                    ? "border-primary/40 bg-primary/5"
                    : "border-border/60 bg-background hover:bg-muted/30",
                )}
              >
                <span className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                  <FileText className="size-3.5 shrink-0 text-blue-600 dark:text-blue-400" />
                  <span>DOCX</span>
                </span>
                <Switch
                  id="export-docx-switch"
                  checked={form.allowExportDocx}
                  onCheckedChange={(checked) =>
                    patch({ allowExportDocx: checked })
                  }
                  disabled={isPending}
                />
              </label>

              <label
                htmlFor="export-pdf-switch"
                className={cn(
                  "flex cursor-pointer items-center justify-between gap-2 rounded-lg border px-2.5 py-2 transition-colors",
                  form.allowExportPdf
                    ? "border-primary/40 bg-primary/5"
                    : "border-border/60 bg-background hover:bg-muted/30",
                )}
              >
                <span className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                  <FileText className="size-3.5 shrink-0 text-rose-600 dark:text-rose-400" />
                  <span>PDF</span>
                </span>
                <Switch
                  id="export-pdf-switch"
                  checked={form.allowExportPdf}
                  onCheckedChange={(checked) =>
                    patch({ allowExportPdf: checked })
                  }
                  disabled={isPending}
                />
              </label>

              <label
                htmlFor="export-xlsx-switch"
                className={cn(
                  "flex cursor-pointer items-center justify-between gap-2 rounded-lg border px-2.5 py-2 transition-colors",
                  form.allowExportXlsx
                    ? "border-primary/40 bg-primary/5"
                    : "border-border/60 bg-background hover:bg-muted/30",
                )}
              >
                <span className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                  <FileSpreadsheet className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  <span>Excel</span>
                </span>
                <Switch
                  id="export-xlsx-switch"
                  checked={form.allowExportXlsx}
                  onCheckedChange={(checked) =>
                    patch({ allowExportXlsx: checked })
                  }
                  disabled={isPending}
                />
              </label>
            </div>
          </div>

          {/* 5. Thông tin phiên bản gọn ở cuối cột */}
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 bg-muted/20 px-4 py-2.5 text-[11px] text-muted-foreground">
            <span>
              Phiên bản{" "}
              <strong className="font-semibold text-foreground">
                v{baseline.revision}
              </strong>{" "}
              · Kiểm chứng: {verificationLabel}
            </span>
            <span
              className={cn(
                "font-medium",
                isDirty
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-emerald-600 dark:text-emerald-400",
              )}
            >
              {isDirty ? "Chưa lưu thay đổi" : "Đã đồng bộ"}
            </span>
          </div>
        </div>
      </div>

      {/* Khối Cấu hình kỹ thuật nâng cao (Full-width, luôn hiển thị) */}
      <div className="w-full rounded-xl border border-border/60 bg-card shadow-2xs overflow-hidden">
        <div className="px-5 py-3.5">
          <p className="text-xs font-semibold text-foreground">
            Cấu hình kỹ thuật nâng cao
          </p>
          <p className="text-[11px] text-muted-foreground">
            Truy xuất, ngữ cảnh, giới hạn đầu ra, độ linh hoạt và kiểm chứng
          </p>
        </div>
        <div className="space-y-5 border-t border-border/50 px-5 py-4">
              {/* 1. Truy xuất */}
              <section className="space-y-3">
                <h4 className="text-xs font-semibold text-foreground">
                  Chiến lược truy xuất & Xếp hạng lại
                </h4>
                <RetrievalFields
                  form={form.policy}
                  onChange={patchPolicy}
                  rerankModels={rerankModels}
                  disabled={isPending}
                />
              </section>

              {/* 2. Ngữ cảnh */}
              <section className="space-y-3 border-t border-border/50 pt-4">
                <h4 className="text-xs font-semibold text-foreground">
                  Ngữ cảnh & Đoạn liền kề
                </h4>
                <ContextFields
                  form={form.policy}
                  onChange={patchPolicy}
                  disabled={isPending}
                />
              </section>

              {/* 3. Đầu ra & Độ linh hoạt */}
              <section className="space-y-3 border-t border-border/50 pt-4">
                <h4 className="text-xs font-semibold text-foreground">
                  Giới hạn đầu ra & Độ linh hoạt mô hình
                </h4>
                <div className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-2">
                  <Field className="space-y-2 rounded-lg border border-border/60 bg-muted/20 p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <FieldLabel className="text-xs font-medium">
                          Giới hạn token đầu ra
                        </FieldLabel>
                        <FieldHelpTooltip text="Độ dài tối đa của câu trả lời sinh ra. Để trống để hệ thống tự điều chỉnh theo năng lực mô hình." />
                      </div>
                      <span className="text-[11px] font-semibold text-primary">
                        {form.maxOutputTokens
                          ? `${Number(form.maxOutputTokens).toLocaleString("vi-VN")} (${formatTokenK(Number(form.maxOutputTokens))})`
                          : "Tự động"}
                      </span>
                    </div>
                    <Input
                      type="number"
                      min={1}
                      value={form.maxOutputTokens}
                      onChange={(event) =>
                        patch({ maxOutputTokens: event.target.value })
                      }
                      placeholder="Để trống: tự động"
                      className="h-8 bg-background text-xs"
                      disabled={isPending}
                    />
                    <div className="flex flex-wrap items-center gap-1 pt-0.5">
                      {[
                        { label: "Tự động", val: "" },
                        { label: "2K", val: "2048" },
                        { label: "4K", val: "4096" },
                        { label: "8K", val: "8192" },
                        { label: "16K", val: "16384" },
                        { label: "32K", val: "32768" },
                        { label: "64K", val: "65536" },
                        { label: "128K", val: "131072" },
                      ].map((preset) => {
                        const isSelected =
                          preset.val === ""
                            ? !form.maxOutputTokens
                            : form.maxOutputTokens === preset.val;
                        return (
                          <button
                            key={preset.label}
                            type="button"
                            disabled={isPending}
                            onClick={() =>
                              patch({ maxOutputTokens: preset.val })
                            }
                            className={cn(
                              "h-6 cursor-pointer rounded px-2 text-[11px] font-medium transition-colors",
                              isSelected
                                ? "bg-primary font-semibold text-primary-foreground shadow-2xs"
                                : "border border-input bg-background text-muted-foreground hover:bg-muted hover:text-foreground",
                            )}
                          >
                            {preset.label}
                          </button>
                        );
                      })}
                    </div>
                  </Field>

                  <div className="space-y-2 rounded-lg border border-border/60 bg-muted/20 p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <FieldLabel className="text-xs font-medium text-foreground">
                          Độ linh hoạt (Temperature)
                        </FieldLabel>
                        <FieldHelpTooltip text="Mức độ sáng tạo của câu trả lời (0.0 bám sát dữ kiện nhất, cao hơn thì diễn đạt tự nhiên hơn). Khuyến nghị 0.0 – 0.2 cho văn bản hành chính và số liệu." />
                      </div>
                      <span className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                        {form.temperature === "auto" ||
                        !form.temperature.trim()
                          ? "Tự động"
                          : Number(form.temperature).toFixed(2)}
                      </span>
                    </div>
                    <Slider
                      min={0}
                      max={1}
                      step={0.05}
                      value={[
                        form.temperature === "auto" ||
                        !form.temperature.trim()
                          ? 0.2
                          : Number(form.temperature),
                      ]}
                      onValueChange={([val]) =>
                        patch({
                          temperature: String(val),
                          policy: {
                            ...form.policy,
                            temperature: String(val),
                          },
                        })
                      }
                      disabled={isPending || form.temperature === "auto"}
                    />
                    <div className="flex flex-wrap items-center gap-1 pt-0.5">
                      {[
                        { label: "Tự động", val: "auto" },
                        { label: "0.0", val: "0" },
                        { label: "0.2 (RAG)", val: "0.2" },
                        { label: "0.5", val: "0.5" },
                        { label: "0.7", val: "0.7" },
                      ].map((preset) => {
                        const isSelected =
                          preset.val === "auto"
                            ? form.temperature === "auto" ||
                              !form.temperature.trim()
                            : form.temperature === preset.val;
                        return (
                          <button
                            key={preset.label}
                            type="button"
                            disabled={isPending}
                            onClick={() =>
                              patch({
                                temperature: preset.val,
                                policy: {
                                  ...form.policy,
                                  temperature: preset.val,
                                },
                              })
                            }
                            className={cn(
                              "h-6 cursor-pointer rounded px-2 text-[11px] font-medium transition-colors",
                              isSelected
                                ? "bg-primary font-semibold text-primary-foreground shadow-2xs"
                                : "border border-input bg-background text-muted-foreground hover:bg-muted hover:text-foreground",
                            )}
                          >
                            {preset.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </section>

              {/* 4. Kiểm chứng */}
              <section className="space-y-3 border-t border-border/50 pt-4">
                <h4 className="text-xs font-semibold text-foreground">
                  Kiểm chứng câu trả lời
                </h4>
                <VerificationFields
                  form={form.policy}
                  onChange={patchPolicy}
                  chatModels={chatModels}
                  disabled={isPending}
                />
              </section>
        </div>
      </div>

      <div className="sticky bottom-4 z-10 flex flex-col gap-2 rounded-lg border border-border/70 bg-card/95 px-4 py-3 shadow-sm backdrop-blur sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium text-foreground">
            {isDirty
              ? "Có thay đổi chưa lưu"
              : `Đã lưu · phiên bản ${baseline.revision}`}
          </p>
          <p className="text-[11px] text-muted-foreground">
            {isDirty
              ? `Đang dựa trên phiên bản ${baseline.revision}. Kiểm chứng: ${verificationLabel}.`
              : "Thay đổi chỉ có hiệu lực sau khi lưu."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            disabled={!isDirty || isPending}
            onClick={handleReset}
          >
            <Undo2 className="size-3.5" />
            <span>Hoàn tác</span>
          </Button>
          <Button
            size="sm"
            className="h-8 gap-1.5 text-xs"
            disabled={!isDirty || isPending || isStale}
            onClick={() => void handleSave()}
          >
            {isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Save className="size-3.5" />
            )}
            <span>{isPending ? "Đang lưu..." : "Lưu thay đổi"}</span>
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={isCollectionConfirmOpen}
        onOpenChange={setIsCollectionConfirmOpen}
        title={
          form.collectionIds.length === 0
            ? "Chuyển trợ lý sang chế độ hội thoại trực tiếp?"
            : "Đổi bộ kho tri thức của trợ lý?"
        }
        description={
          form.collectionIds.length === 0
            ? "Sau khi lưu, trợ lý sẽ hoạt động ở chế độ hội thoại LLM trực tiếp (không dùng kho tri thức). Các câu hỏi sẽ được trả lời dựa trên Persona cấu hình mà không cần đối soát tài liệu."
            : `Trợ lý sẽ tra cứu trong ${form.collectionIds.length} kho (${selectedCollectionNames}) ngay sau khi lưu. Hội thoại đã có vẫn giữ bộ kho cũ; muốn hỏi tiếp cần tạo hội thoại mới.`
        }
        confirmLabel={
          form.collectionIds.length === 0 ? "Chuyển sang hội thoại trực tiếp" : "Đổi kho và lưu"
        }
        isLoading={isPending}
        onConfirm={() => void runSave()}
      />

      <AssistantPersonaCraftDialog
        open={isPersonaCraftOpen}
        onOpenChange={setIsPersonaCraftOpen}
        workspaceId={workspaceId}
        providerId={form.providerId === AUTO_MODEL ? null : form.providerId}
        currentName={form.name}
        onApply={handleApplyCraftedPersona}
      />
      </div>
    </TooltipProvider>
  );
}
