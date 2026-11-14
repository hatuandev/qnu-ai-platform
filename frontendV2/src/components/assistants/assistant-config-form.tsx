import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Loader2, Save, Undo2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  type AssistantResponse,
  assistantKeys,
  useUpdateAssistantMutation,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import { useCollectionsQuery } from "@/api/knowledge";
import { useCatalogQuery } from "@/api/modelops";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  ContextFields,
  MetadataScopeFields,
  ModelOption,
  type RagPolicyFormState,
  RetrievalFields,
  VERIFICATION_OPTIONS,
  VerificationFields,
} from "./assistant-advanced-fields";
import {
  type AssistantFormState,
  AUTO_MODEL,
  buildAssistantPayload,
  DESCRIPTION_MAX_CHARS,
  initialState,
  NAME_MAX_CHARS,
  PERSONA_MAX_CHARS,
  validateAssistantForm,
} from "./assistant-form-state";

type Baseline = { revision: number; data: AssistantResponse };

export function AssistantConfigForm({
  workspaceId,
  assistant,
}: {
  workspaceId: string;
  assistant: AssistantResponse;
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
  const currentCollectionName =
    collections.find((item) => item.id === assistant.collection_id)?.name ??
    assistant.collection_id;

  const [baseline, setBaseline] = useState<Baseline>({
    revision: assistant.revision,
    data: assistant,
  });
  const [form, setForm] = useState<AssistantFormState>(() =>
    initialState(assistant),
  );
  const [error, setError] = useState<string | null>(null);
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

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

  const handleSave = async () => {
    const message = validateAssistantForm(form);
    if (message) {
      setError(message);
      return;
    }
    setError(null);
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
      toast.success(`Đã lưu cấu hình "${updated.name}"`);
    } catch (err: unknown) {
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

      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="pb-4 border-b border-border/50">
          <CardTitle className="text-sm font-semibold">
            Cấu hình chung
          </CardTitle>
          <CardDescription>
            Tên, mô tả, chỉ dẫn ứng xử, kho dữ liệu và mô hình phục vụ.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-5">
          {/* Nhóm 1: Thông tin cơ bản */}
          <div className="space-y-4">
            <h4 className="text-xs font-semibold text-foreground tracking-tight">
              Thông tin trợ lý
            </h4>
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
                onChange={(event) => patch({ description: event.target.value })}
                maxLength={DESCRIPTION_MAX_CHARS}
                placeholder="Mô tả phạm vi hỗ trợ và đối tượng sử dụng trợ lý..."
                rows={2}
                className="resize-none bg-background text-xs leading-relaxed"
                disabled={isPending}
              />
              <FieldDescription>
                Hiển thị tóm tắt trong danh sách trợ lý.
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
          </div>

          <Separator />

          {/* Nhóm 2: Phạm vi tri thức & mô hình */}
          <div className="space-y-4">
            <h4 className="text-xs font-semibold text-foreground tracking-tight">
              Kho tri thức & Mô hình ngôn ngữ
            </h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field>
                <FieldLabel className="text-xs font-medium">
                  Kho tri thức liên kết
                </FieldLabel>
                <Select value={assistant.collection_id} disabled>
                  <SelectTrigger className="h-9 bg-background text-xs opacity-90">
                    <SelectValue>{currentCollectionName}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={assistant.collection_id}>
                      {currentCollectionName}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Không thể đổi kho sau khi tạo; hãy tạo trợ lý mới nếu muốn đổi
                  kho.
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
                    <SelectItem value={AUTO_MODEL}>
                      <span className="flex flex-col items-start">
                        <span>Tự động theo hệ thống</span>
                        <span className="text-[11px] text-muted-foreground">
                          Dùng mô hình trò chuyện mặc định
                        </span>
                      </span>
                    </SelectItem>
                    {chatModels.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        <ModelOption item={item} />
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Mô hình được điều phối qua ModelOps; tự động sẽ dùng cấu hình
                  mặc định toàn trường.
                </FieldDescription>
              </Field>
            </div>
          </div>

          <Separator />

          {/* Nhóm 3: Hành vi trả lời & Trạng thái */}
          <div className="space-y-4">
            <h4 className="text-xs font-semibold text-foreground tracking-tight">
              Hành vi trả lời & Trạng thái
            </h4>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field>
                <FieldLabel className="text-xs font-medium">
                  Đoạn trích dẫn
                </FieldLabel>
                <Input
                  type="number"
                  min={1}
                  max={20}
                  value={form.topK}
                  onChange={(event) => patch({ topK: event.target.value })}
                  className="h-9 bg-background text-xs"
                  disabled={isPending}
                />
                <FieldDescription>
                  Từ 1 đến 20 đoạn trích dẫn đưa vào ngữ cảnh.
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel className="text-xs font-medium">
                  Lượt ghi nhớ
                </FieldLabel>
                <Input
                  type="number"
                  min={0}
                  max={10}
                  value={form.historyTurns}
                  onChange={(event) =>
                    patch({ historyTurns: event.target.value })
                  }
                  className="h-9 bg-background text-xs"
                  disabled={isPending}
                />
                <FieldDescription>
                  Số lượt hội thoại trước được đưa vào làm ngữ cảnh.
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel className="text-xs font-medium">
                  Giới hạn token đầu ra
                </FieldLabel>
                <Input
                  type="number"
                  min={1}
                  value={form.maxOutputTokens}
                  onChange={(event) =>
                    patch({ maxOutputTokens: event.target.value })
                  }
                  placeholder="VD: 2048 (để trống: tự động)"
                  className="h-9 bg-background text-xs"
                  disabled={isPending}
                />
                <FieldDescription>
                  Để trống để hệ thống dùng ngân sách tối ưu của mô hình.
                </FieldDescription>
              </Field>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="space-y-0.5">
                <Label
                  htmlFor="assistant-active-switch"
                  className="text-xs font-medium text-foreground cursor-pointer"
                >
                  Trạng thái hoạt động
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  Bật để tiếp nhận câu hỏi; tắt sẽ tạm dừng phục vụ và hủy các
                  lượt đang chạy.
                </p>
              </div>
              <Switch
                id="assistant-active-switch"
                checked={form.isActive}
                onCheckedChange={(checked) => patch({ isActive: checked })}
                disabled={isPending}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Collapsible open={isAdvancedOpen} onOpenChange={setIsAdvancedOpen}>
        <Card className="border-border/60 shadow-2xs">
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-3 p-5 text-left"
            >
              <div>
                <p className="text-sm font-semibold text-foreground">
                  Truy xuất nâng cao
                </p>
                <p className="text-[11px] text-muted-foreground">
                  Cách tìm, xếp hạng và giới hạn dẫn chứng. Mặc định đã phù hợp
                  phần lớn trợ lý.
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
            <CardContent className="space-y-5 border-t border-border/60 pt-4">
              <section className="space-y-3">
                <h4 className="text-xs font-semibold text-foreground">
                  Truy xuất
                </h4>
                <RetrievalFields
                  form={form.policy}
                  onChange={patchPolicy}
                  rerankModels={rerankModels}
                  disabled={isPending}
                />
              </section>
              <section className="space-y-3 border-t border-border/60 pt-4">
                <h4 className="text-xs font-semibold text-foreground">
                  Ngữ cảnh trả lời
                </h4>
                <ContextFields
                  form={form.policy}
                  onChange={patchPolicy}
                  disabled={isPending}
                />
              </section>
              <section className="space-y-3 border-t border-border/60 pt-4">
                <h4 className="text-xs font-semibold text-foreground">
                  Phạm vi dữ kiện
                </h4>
                <MetadataScopeFields
                  form={form.policy}
                  onChange={patchPolicy}
                  disabled={isPending}
                />
              </section>
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Kiểm chứng câu trả lời</CardTitle>
          <CardDescription>
            Đối chiếu câu trả lời với dẫn chứng trước khi gửi cho người dùng.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <VerificationFields
            form={form.policy}
            onChange={patchPolicy}
            chatModels={chatModels}
            disabled={isPending}
          />
          <p className="mt-3 text-[11px] text-muted-foreground">
            Cấu hình nâng cao áp dụng cho hội thoại mới; hội thoại đã bắt đầu
            giữ cấu hình tại thời điểm mở.
          </p>
        </CardContent>
      </Card>

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
    </div>
  );
}
