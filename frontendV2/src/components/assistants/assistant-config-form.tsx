import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Loader2, Save, Undo2 } from "lucide-react";
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
import { cn } from "@/lib/utils";
import {
  ContextFields,
  MetadataScopeFields,
  type RagPolicyFormState,
  RetrievalFields,
  VERIFICATION_OPTIONS,
  VerificationFields,
} from "./assistant-advanced-fields";
import {
  AssistantCollectionPicker,
  type CollectionOption,
} from "./assistant-collection-picker";
import {
  type AssistantFormState,
  AUTO_MODEL,
  buildAssistantPayload,
  collectionIdsOf,
  DESCRIPTION_MAX_CHARS,
  initialState,
  NAME_MAX_CHARS,
  PERSONA_MAX_CHARS,
  validateAssistantForm,
} from "./assistant-form-state";
import { localityLabel, providerLabel } from "./model-label";
import { READINESS_MAP } from "./readiness";

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
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [isCollectionConfirmOpen, setIsCollectionConfirmOpen] = useState(false);

  const baselineCollectionIds = useMemo(
    () => collectionIdsOf(baseline.data),
    [baseline.data],
  );
  const collectionOptions = useMemo<CollectionOption[]>(() => {
    const options: CollectionOption[] = collections.map((item) => ({
      id: item.id,
      name: item.name,
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
        <Alert variant="warning">
          <AlertTitle>Trợ lý chưa gắn kho tri thức</AlertTitle>
          <AlertDescription>
            Vẫn lưu được để hoàn thiện chỉ dẫn và mô hình, nhưng trợ lý chưa trả
            lời được, chưa hỏi thử được và không thể bật kênh công khai cho tới
            khi gắn lại ít nhất một kho tri thức.
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

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Cột chính: Thông tin, Mô hình & Cấu hình RAG */}
        <div className="space-y-5 lg:col-span-2">
          {/* Khối 1: Thông tin trợ lý */}
          <Card className="border-border/60 shadow-2xs">
            <CardHeader className="border-b border-border/50 pb-3">
              <CardTitle className="text-sm font-semibold">
                Thông tin & Chỉ dẫn ứng xử
              </CardTitle>
              <CardDescription>
                Định danh, mô tả phạm vi phục vụ và văn phong giao tiếp của trợ
                lý.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
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

              <Field>
                <FieldLabel className="text-xs font-medium">
                  Mô tả ngắn
                </FieldLabel>
                <Textarea
                  value={form.description}
                  onChange={(event) =>
                    patch({ description: event.target.value })
                  }
                  maxLength={DESCRIPTION_MAX_CHARS}
                  placeholder="Mô tả phạm vi hỗ trợ và đối tượng sử dụng trợ lý..."
                  rows={2}
                  className="resize-none bg-background text-xs leading-relaxed"
                  disabled={isPending}
                />
                <FieldDescription>
                  Hiển thị tóm tắt trong danh sách trợ lý và cổng thông tin.
                </FieldDescription>
              </Field>

              <Field>
                <FieldLabel className="text-xs font-medium">
                  Chỉ dẫn cho trợ lý (Persona)
                </FieldLabel>
                <Textarea
                  value={form.persona}
                  onChange={(event) => patch({ persona: event.target.value })}
                  maxLength={PERSONA_MAX_CHARS}
                  placeholder="Định hình vai trò, phong cách xưng hô và nguyên tắc trả lời..."
                  rows={4}
                  className="resize-none bg-background text-xs leading-relaxed"
                  disabled={isPending}
                />
                <FieldDescription>
                  Định hình văn phong và nguyên tắc trả lời; mọi căn cứ thực tế
                  luôn được trích xuất từ kho tri thức.
                </FieldDescription>
              </Field>
            </CardContent>
          </Card>

          {/* Khối 2: Kho tri thức & Mô hình cốt lõi */}
          <Card className="border-border/60 shadow-2xs">
            <CardHeader className="border-b border-border/50 pb-3">
              <CardTitle className="text-sm font-semibold">
                Kho tri thức & Mô hình ngôn ngữ
              </CardTitle>
              <CardDescription>
                Kho dữ liệu tham chiếu và các tham số điều phối sinh câu trả
                lời.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field>
                  <FieldLabel className="text-xs font-medium">
                    Kho tri thức liên kết
                  </FieldLabel>
                  <AssistantCollectionPicker
                    collections={collectionOptions}
                    selectedIds={form.collectionIds}
                    onChange={(ids) => patch({ collectionIds: ids })}
                    disabled={isPending}
                    readiness={readiness}
                  />
                  <FieldDescription>
                    Trợ lý tra cứu trong tất cả kho đã chọn. Đổi bộ kho áp dụng
                    ngay khi lưu; hội thoại đã có giữ bộ kho cũ và cần hội thoại
                    mới để hỏi tiếp.
                  </FieldDescription>
                </Field>

                <Field>
                  <FieldLabel className="text-xs font-medium">
                    Mô hình trả lời
                  </FieldLabel>
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
                  <FieldDescription>
                    Mô hình điều phối qua ModelOps; tự động sẽ dùng cấu hình
                    trường.
                  </FieldDescription>
                </Field>
              </div>

              <div className="grid gap-4 pt-2 sm:grid-cols-2">
                {/* Thanh kéo Đoạn trích dẫn */}
                <div className="space-y-2.5 rounded-lg border border-border/60 bg-muted/20 p-3.5">
                  <div className="flex items-center justify-between">
                    <div>
                      <FieldLabel className="text-xs font-medium text-foreground">
                        Đoạn trích dẫn (Top-K)
                      </FieldLabel>
                      <p className="text-[11px] text-muted-foreground">
                        Dẫn chứng tối đa đưa vào câu trả lời
                      </p>
                    </div>
                    <span className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
                      {form.topK || 5} đoạn
                    </span>
                  </div>

                  <div className="pt-2">
                    <Slider
                      min={1}
                      max={20}
                      step={1}
                      value={[Number(form.topK) || 5]}
                      onValueChange={([val]) => patch({ topK: String(val) })}
                      disabled={isPending}
                    />
                  </div>

                  <div className="flex justify-between text-[10px] font-medium text-muted-foreground/60">
                    <span>1 đoạn (ngắn gọn)</span>
                    <span>10 đoạn</span>
                    <span>20 đoạn (chi tiết)</span>
                  </div>
                </div>

                {/* Thanh kéo Lượt ghi nhớ */}
                <div className="space-y-2.5 rounded-lg border border-border/60 bg-muted/20 p-3.5">
                  <div className="flex items-center justify-between">
                    <div>
                      <FieldLabel className="text-xs font-medium text-foreground">
                        Lượt nhớ lịch sử
                      </FieldLabel>
                      <p className="text-[11px] text-muted-foreground">
                        Số lượt trao đổi trước được ghi nhớ
                      </p>
                    </div>
                    <span className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
                      {Number(form.historyTurns) === 0
                        ? "Không nhớ"
                        : `${form.historyTurns} lượt`}
                    </span>
                  </div>

                  <div className="pt-2">
                    <Slider
                      min={0}
                      max={10}
                      step={1}
                      value={[Number(form.historyTurns) || 0]}
                      onValueChange={([val]) =>
                        patch({ historyTurns: String(val) })
                      }
                      disabled={isPending}
                    />
                  </div>

                  <div className="flex justify-between text-[10px] font-medium text-muted-foreground/60">
                    <span>0 (Chỉ câu hiện tại)</span>
                    <span>5 lượt</span>
                    <span>10 lượt</span>
                  </div>
                </div>
              </div>

              {/* Giới hạn token với Quick Presets (hỗ trợ tới 128K) */}
              <Field className="pt-1">
                <div className="flex items-center justify-between">
                  <FieldLabel className="text-xs font-medium">
                    Giới hạn token đầu ra
                  </FieldLabel>
                  <span className="text-[11px] font-semibold text-primary">
                    {form.maxOutputTokens
                      ? `${Number(form.maxOutputTokens).toLocaleString("vi-VN")} tokens (${formatTokenK(Number(form.maxOutputTokens))})`
                      : "Tự động theo năng lực mô hình"}
                  </span>
                </div>
                <div className="pt-1">
                  <Input
                    type="number"
                    min={1}
                    value={form.maxOutputTokens}
                    onChange={(event) =>
                      patch({ maxOutputTokens: event.target.value })
                    }
                    placeholder="VD: 131072 (để trống: tự động)"
                    className="h-9 bg-background text-xs"
                    disabled={isPending}
                  />
                </div>
                <div className="flex flex-wrap items-center gap-1.5 pt-2">
                  <span className="mr-1 text-[11px] font-medium text-muted-foreground">
                    Mốc gợi ý:
                  </span>
                  {[
                    { label: "Tự động", val: "" },
                    { label: "2K", val: "2048" },
                    { label: "4K", val: "4096" },
                    { label: "8K", val: "8192" },
                    { label: "16K", val: "16384" },
                    { label: "32K", val: "32768" },
                    { label: "64K", val: "65536" },
                    { label: "128K (Tối đa)", val: "131072" },
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
                        onClick={() => patch({ maxOutputTokens: preset.val })}
                        className={cn(
                          "h-7 cursor-pointer rounded-md px-2 text-xs font-medium transition-colors",
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
                <FieldDescription>
                  Hỗ trợ đầy đủ từ câu trả lời ngắn gọn đến các mô hình thế hệ
                  mới có đầu ra siêu lớn (như GPT-6 Luna, Claude 3.7, Gemini 2.5
                  với đầu ra lên tới 128K tokens). Bạn có thể chọn mốc 128K hoặc
                  nhập số cụ thể tùy ý.
                </FieldDescription>
              </Field>
            </CardContent>
          </Card>

          {/* Khối 3: Cấu hình RAG & Kiểm chứng nâng cao (Thu gọn) */}
          <Collapsible open={isAdvancedOpen} onOpenChange={setIsAdvancedOpen}>
            <Card className="border-border/60 shadow-2xs">
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 p-4 text-left transition-colors hover:bg-muted/30"
                >
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      Cấu hình RAG & Kiểm chứng nâng cao
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Chiến lược tìm kiếm, ngân sách ngữ cảnh, bộ lọc metadata
                      và kiểm chứng chống suy diễn.
                    </p>
                  </div>
                  <ChevronDown
                    className={`size-4 shrink-0 text-muted-foreground transition-transform ${
                      isAdvancedOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="space-y-6 border-t border-border/60 pt-5">
                  <section className="space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
                        1
                      </span>
                      <h4 className="text-xs font-semibold text-foreground">
                        Chiến lược truy xuất & Xếp hạng lại
                      </h4>
                    </div>
                    <RetrievalFields
                      form={form.policy}
                      onChange={patchPolicy}
                      rerankModels={rerankModels}
                      disabled={isPending}
                    />
                  </section>

                  <section className="space-y-3 border-t border-border/60 pt-5">
                    <div className="flex items-center gap-2">
                      <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
                        2
                      </span>
                      <h4 className="text-xs font-semibold text-foreground">
                        Ngân sách ngữ cảnh & Đoạn liền kề
                      </h4>
                    </div>
                    <ContextFields
                      form={form.policy}
                      onChange={patchPolicy}
                      disabled={isPending}
                    />
                  </section>

                  <section className="space-y-3 border-t border-border/60 pt-5">
                    <div className="flex items-center gap-2">
                      <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
                        3
                      </span>
                      <h4 className="text-xs font-semibold text-foreground">
                        Bộ lọc tài liệu theo tiêu chí (Metadata)
                      </h4>
                    </div>
                    <MetadataScopeFields
                      form={form.policy}
                      onChange={patchPolicy}
                      disabled={isPending}
                    />
                  </section>

                  <section className="space-y-3 border-t border-border/60 pt-5">
                    <div className="flex items-center gap-2">
                      <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
                        4
                      </span>
                      <h4 className="text-xs font-semibold text-foreground">
                        Kiểm chứng câu trả lời & Chống suy diễn
                      </h4>
                    </div>
                    <VerificationFields
                      form={form.policy}
                      onChange={patchPolicy}
                      chatModels={chatModels}
                      disabled={isPending}
                    />
                  </section>

                  <p className="text-[11px] text-muted-foreground">
                    Cấu hình nâng cao áp dụng cho hội thoại mới; hội thoại đã
                    bắt đầu giữ cấu hình tại thời điểm mở.
                  </p>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        </div>

        {/* Cột phụ: Trạng thái phục vụ & Bảng tóm tắt quản trị */}
        <div className="space-y-4 lg:col-span-1">
          {/* Card Trạng thái phục vụ */}
          <Card className="border-border/60 shadow-2xs">
            <CardHeader className="border-b border-border/50 pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Trạng thái phục vụ
                </CardTitle>
                {form.isActive ? (
                  <Badge
                    variant="success"
                    className="h-5 gap-1.5 px-2 text-[11px] font-medium"
                  >
                    <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Đang hoạt động
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="h-5 px-2 text-[11px] font-medium text-muted-foreground"
                  >
                    Tạm dừng
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3 pt-4">
              <div className="flex items-center justify-between">
                <Label
                  htmlFor="assistant-active-switch"
                  className="text-xs font-medium text-foreground cursor-pointer"
                >
                  Tiếp nhận câu hỏi
                </Label>
                <Switch
                  id="assistant-active-switch"
                  checked={form.isActive}
                  onCheckedChange={(checked) => patch({ isActive: checked })}
                  disabled={isPending}
                />
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                {form.isActive
                  ? "Trợ lý đang sẵn sàng tiếp nhận câu hỏi từ sinh viên và người dùng qua các kênh được phân quyền."
                  : "Trợ lý đang tạm dừng. Các yêu cầu mới sẽ bị từ chối và các phiên xử lý đang chạy sẽ được dừng an toàn."}
              </p>
            </CardContent>
          </Card>

          {/* Card Tóm tắt phiên bản & Chỉ số */}
          <Card className="border-border/60 shadow-2xs">
            <CardHeader className="border-b border-border/50 pb-3">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Thông tin phiên bản
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 pt-3 text-xs">
              <div className="flex items-center justify-between border-b border-border/40 py-1.5">
                <span className="text-muted-foreground">Phiên bản</span>
                <span className="font-semibold text-foreground">
                  v{baseline.revision}
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-border/40 py-1.5">
                <span className="text-muted-foreground">Mô hình</span>
                <span
                  className="max-w-[140px] truncate font-medium text-foreground text-right"
                  title={
                    form.providerId === AUTO_MODEL
                      ? "Tự động theo hệ thống"
                      : form.providerId
                  }
                >
                  {form.providerId === AUTO_MODEL
                    ? "Tự động"
                    : (chatModels.find((m) => m.id === form.providerId)
                        ?.model_name ?? form.providerId)}
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-border/40 py-1.5">
                <span className="text-muted-foreground">Kiểm chứng</span>
                <span className="font-medium text-foreground">
                  {verificationLabel}
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-border/40 py-1.5">
                <span className="text-muted-foreground">Trích dẫn (Top-K)</span>
                <span className="font-medium text-foreground">
                  {form.topK} đoạn
                </span>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <span className="text-muted-foreground">Trạng thái lưu</span>
                <span
                  className={cn(
                    "font-medium",
                    isDirty
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-emerald-600 dark:text-emerald-400",
                  )}
                >
                  {isDirty ? "Có thay đổi chưa lưu" : "Đã đồng bộ"}
                </span>
              </div>
            </CardContent>
          </Card>
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
            ? "Bỏ toàn bộ kho tri thức của trợ lý?"
            : "Đổi bộ kho tri thức của trợ lý?"
        }
        description={
          form.collectionIds.length === 0
            ? "Sau khi lưu, trợ lý không còn kho tri thức nào: mọi lượt hỏi mới và lượt kiểm thử sẽ bị chặn, kênh công khai phải tắt, cho tới khi bạn gắn lại ít nhất một kho."
            : `Trợ lý sẽ tra cứu trong ${form.collectionIds.length} kho (${selectedCollectionNames}) ngay sau khi lưu. Hội thoại đã có vẫn giữ bộ kho cũ; muốn hỏi tiếp cần tạo hội thoại mới.`
        }
        confirmLabel={
          form.collectionIds.length === 0 ? "Bỏ kho và lưu" : "Đổi kho và lưu"
        }
        isLoading={isPending}
        onConfirm={() => void runSave()}
      />
    </div>
  );
}
