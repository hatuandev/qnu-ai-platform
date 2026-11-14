import { useQueryClient } from "@tanstack/react-query";
import { Bot, Loader2, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import type { AssistantResponse } from "@/api/assistants";
import {
  assistantKeys,
  useCreateAssistantMutation,
  useUpdateAssistantMutation,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import { useCollectionsQuery } from "@/api/knowledge";
import { useCatalogQuery } from "@/api/modelops";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  AssistantAdvancedFields,
  ModelOption,
  NEW_ASSISTANT_POLICY,
  type RagPolicyFormState,
} from "./assistant-advanced-fields";
import {
  type AssistantFormState,
  AUTO_MODEL,
  buildAssistantPayload,
  initialState,
  validateAssistantForm,
} from "./assistant-form-state";

export function AssistantFormDialog({
  open,
  onOpenChange,
  workspaceId,
  assistant,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  assistant?: AssistantResponse | null;
}) {
  const isEdit = Boolean(assistant);
  const queryClient = useQueryClient();
  const createMutation = useCreateAssistantMutation(workspaceId);
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

  const [form, setForm] = useState<AssistantFormState>(() =>
    initialState(assistant),
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setForm(initialState(assistant));
      setError(null);
    }
  }, [open, assistant]);

  const patch = (values: Partial<AssistantFormState>) =>
    setForm((prev) => ({ ...prev, ...values }));
  const patchPolicy = (values: Partial<RagPolicyFormState>) =>
    setForm((prev) => ({ ...prev, policy: { ...prev.policy, ...values } }));

  const isPending = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const message = validateAssistantForm(form);
    if (message) {
      setError(message);
      return;
    }
    setError(null);
    const payload = buildAssistantPayload(
      form,
      assistant?.rag_policy ?? NEW_ASSISTANT_POLICY,
    );
    try {
      if (assistant) {
        await updateMutation.mutateAsync({
          assistantId: assistant.id,
          data: { ...payload, expected_revision: assistant.revision },
        });
        toast.success(`Đã lưu cấu hình "${payload.name}"`);
      } else {
        await createMutation.mutateAsync(payload);
        toast.success(`Đã tạo trợ lý "${payload.name}"`);
      }
      onOpenChange(false);
    } catch (err: unknown) {
      if (err instanceof ApiProblemError) {
        if (err.code === "assistant_revision_conflict") {
          await queryClient.invalidateQueries({
            queryKey: assistantKeys.list(workspaceId),
          });
          toast.error(
            "Cấu hình trợ lý vừa được người khác cập nhật. Danh sách đã được tải lại, vui lòng mở lại để chỉnh sửa.",
          );
          onOpenChange(false);
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader className="space-y-1">
            <DialogTitle className="flex items-center gap-2 text-base font-semibold text-foreground">
              <Bot className="size-4.5 shrink-0 text-primary" />
              <span>{isEdit ? "Chỉnh sửa trợ lý" : "Tạo trợ lý mới"}</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Trợ lý trả lời trong phạm vi một kho tri thức và chỉ dẫn được nêu
              bên dưới.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-destructive/20 bg-destructive/10 p-2.5 text-xs text-destructive"
            >
              {error}
            </div>
          )}

          <Tabs defaultValue="basic">
            <TabsList>
              <TabsTrigger value="basic">Cơ bản</TabsTrigger>
              <TabsTrigger value="advanced">Nâng cao</TabsTrigger>
            </TabsList>
            <div className="max-h-[60vh] overflow-y-auto pr-1">
              <TabsContent value="basic" className="mt-0 space-y-3.5 pt-1">
                <Field>
                  <FieldLabel required className="text-xs font-medium">
                    Tên trợ lý
                  </FieldLabel>
                  <Input
                    value={form.name}
                    onChange={(event) => patch({ name: event.target.value })}
                    placeholder="VD: Trợ lý Tuyển sinh 2026"
                    className="h-9 bg-background text-xs"
                    disabled={isPending}
                    autoFocus
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
                    placeholder="Mục đích hoạt động của trợ lý"
                    rows={2}
                    className="resize-none bg-background text-xs"
                    disabled={isPending}
                  />
                </Field>

                <Field>
                  <FieldLabel className="text-xs font-medium">
                    Chỉ dẫn cho trợ lý
                  </FieldLabel>
                  <Textarea
                    value={form.persona}
                    onChange={(event) => patch({ persona: event.target.value })}
                    placeholder="VD: Bạn là trợ lý tư vấn tuyển sinh của Trường Đại học Quy Nhơn..."
                    rows={3}
                    className="resize-none bg-background text-xs"
                    disabled={isPending}
                  />
                  <FieldDescription>
                    Áp dụng cho mọi câu trả lời; nội dung dẫn chứng vẫn lấy từ
                    kho tri thức.
                  </FieldDescription>
                </Field>

                <div className="grid gap-3.5 sm:grid-cols-2">
                  <Field>
                    <FieldLabel required className="text-xs font-medium">
                      Kho tri thức
                    </FieldLabel>
                    <Select
                      value={form.collectionId}
                      onValueChange={(value) => patch({ collectionId: value })}
                      disabled={isPending || isEdit}
                    >
                      <SelectTrigger className="h-9 bg-background text-xs">
                        <SelectValue placeholder="Chọn kho tri thức" />
                      </SelectTrigger>
                      <SelectContent>
                        {collections.map((collection) => (
                          <SelectItem key={collection.id} value={collection.id}>
                            {collection.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FieldDescription>
                      {isEdit
                        ? "Không thể đổi kho sau khi tạo; hãy tạo trợ lý mới nếu cần."
                        : "Phạm vi tài liệu trợ lý được phép trả lời."}
                    </FieldDescription>
                  </Field>

                  <Field>
                    <FieldLabel className="text-xs font-medium">
                      Mô hình
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
                  </Field>
                </div>

                <div className="grid gap-3.5 sm:grid-cols-3">
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
                  </Field>
                  <Field>
                    <FieldLabel className="text-xs font-medium">
                      Token đầu ra
                    </FieldLabel>
                    <Input
                      type="number"
                      min={1}
                      value={form.maxOutputTokens}
                      onChange={(event) =>
                        patch({ maxOutputTokens: event.target.value })
                      }
                      placeholder="Tự động"
                      className="h-9 bg-background text-xs"
                      disabled={isPending}
                    />
                  </Field>
                </div>

                <div className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2.5">
                  <div>
                    <p className="text-xs font-medium text-foreground">
                      Đang hoạt động
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Tắt để tạm dừng nhận câu hỏi mới từ người dùng.
                    </p>
                  </div>
                  <Switch
                    checked={form.isActive}
                    onCheckedChange={(checked) => patch({ isActive: checked })}
                    disabled={isPending}
                  />
                </div>
              </TabsContent>

              <TabsContent value="advanced" className="mt-0 pt-1">
                <AssistantAdvancedFields
                  form={form.policy}
                  onChange={patchPolicy}
                  chatModels={chatModels}
                  rerankModels={rerankModels}
                  disabled={isPending}
                />
                <p className="mt-4 border-t border-border/60 pt-3 text-[11px] text-muted-foreground">
                  Cấu hình nâng cao áp dụng cho hội thoại mới; hội thoại đã bắt
                  đầu giữ cấu hình tại thời điểm mở.
                </p>
              </TabsContent>
            </div>
          </Tabs>

          <DialogFooter className="gap-2 pt-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 text-xs"
              disabled={isPending}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-9 gap-1 text-xs"
              disabled={isPending}
            >
              {isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Save className="size-3.5" />
              )}
              <span>{isEdit ? "Lưu thay đổi" : "Tạo trợ lý"}</span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
