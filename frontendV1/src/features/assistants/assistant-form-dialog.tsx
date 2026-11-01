import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  Bot,
  ChevronDown,
  Cpu,
  Database,
  ExternalLink,
  Layers,
  Loader2,
  RefreshCw,
  Save,
  Sliders,
  Sparkles,
} from "lucide-react";
import { useEffect, useId, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
import {
  useCreateAssistant,
  useUpdateAssistant,
} from "@/features/assistants/queries";
import { assistantFormSchema } from "@/features/assistants/schemas";
import type {
  Assistant,
  AssistantCreateInput,
  AssistantUpdateInput,
} from "@/features/assistants/types";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import { ConsumerModelBudgetNotice } from "@/features/modelops/capacity-badge";
import { useCatalogQuery } from "@/features/modelops/queries";
import { toRagPolicy, toRagPolicyForm } from "@/features/rag/schemas";
import {
  RETRIEVAL_MODE_LABEL,
  type RetrievalMode,
  VERIFICATION_MODE_LABEL,
  type VerificationMode,
} from "@/features/rag/types";
import { DEFAULT_PAGE_SEARCH } from "@/features/workspaces/search";
import { getFormErrorMessage } from "@/lib/form-errors";

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

const WORKSPACE_DEFAULT_PROVIDER = "__workspace_default__";
const NO_PROVIDER_VALUE = "__none__";

const asRetrievalMode = (value: string): RetrievalMode =>
  value === "hybrid" || value === "hybrid_rerank" ? value : "dense";

const asVerificationMode = (value: string): VerificationMode =>
  value === "observe" || value === "enforce" ? value : "off";

export function AssistantFormDialog({
  open,
  onOpenChange,
  workspaceId,
  assistant,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  assistant?: Assistant | null;
  onSuccess?: (assistant: Assistant) => void;
}) {
  const isEdit = Boolean(assistant);
  const createMutation = useCreateAssistant(workspaceId);
  const updateMutation = useUpdateAssistant(workspaceId, assistant?.id ?? "");

  const [serverError, setServerError] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const [ragOpen, setRagOpen] = useState(false);

  // Queries for dynamic dependencies: collections & model catalog
  const collectionsQuery = useCollectionsQuery(workspaceId, {
    page: 1,
    pageSize: 100,
  });
  const catalogQuery = useCatalogQuery(workspaceId);

  const collections = collectionsQuery.data?.items ?? [];
  const chatCatalog = (catalogQuery.data ?? []).filter((item) =>
    item.capabilities.includes("chat"),
  );
  // Rerank and judge providers must come from the workspace catalog with the
  // matching capability; the backend rejects anything else.
  const rerankCatalog = (catalogQuery.data ?? []).filter((item) =>
    item.capabilities.includes("rerank"),
  );

  const form = useForm({
    defaultValues: {
      name: assistant?.name ?? "",
      description: assistant?.description ?? "",
      persona: assistant?.persona ?? "",
      collection_id: assistant?.collection_id ?? "",
      chat_provider_id: assistant?.chat_provider_id ?? null,
      top_k: assistant?.top_k ?? 5,
      history_turns: assistant?.history_turns ?? 3,
      max_output_tokens: assistant?.max_output_tokens ?? 2048,
      is_active: assistant?.is_active ?? true,
      rag_policy: toRagPolicyForm(assistant?.rag_policy),
      expected_revision: assistant?.revision ?? 1,
    },
    validators: {
      onSubmit: assistantFormSchema as never,
    },
    onSubmit: async ({ value }) => {
      setServerError(null);
      setConflictError(null);

      try {
        if (isEdit && assistant) {
          const payload: AssistantUpdateInput = {
            name: value.name.trim(),
            description: value.description ?? "",
            persona: value.persona ?? "",
            collection_id: assistant.collection_id, // Immutable on update
            chat_provider_id: value.chat_provider_id ?? null,
            top_k: Number(value.top_k),
            history_turns: Number(value.history_turns),
            max_output_tokens: Number(value.max_output_tokens),
            is_active: Boolean(value.is_active),
            rag_policy: toRagPolicy(value.rag_policy),
            expected_revision: assistant.revision,
          };

          const res = await updateMutation.mutateAsync(payload);
          toast.success(`Đã cập nhật trợ lý "${res.name}".`);
          onOpenChange(false);
          onSuccess?.(res);
        } else {
          const payload: AssistantCreateInput = {
            name: value.name.trim(),
            description: value.description ?? "",
            persona: value.persona ?? "",
            collection_id: value.collection_id,
            chat_provider_id: value.chat_provider_id ?? null,
            top_k: Number(value.top_k),
            history_turns: Number(value.history_turns),
            max_output_tokens: Number(value.max_output_tokens),
            is_active: Boolean(value.is_active),
            rag_policy: toRagPolicy(value.rag_policy),
          };

          const res = await createMutation.mutateAsync(payload);
          toast.success(`Đã tạo trợ lý "${res.name}".`);
          onOpenChange(false);
          onSuccess?.(res);
        }
      } catch (error) {
        if (error instanceof ApiProblemError) {
          if (
            error.status === 409 ||
            error.code === "assistant_revision_conflict"
          ) {
            setConflictError(
              "Cấu hình trợ lý đã bị thay đổi bởi phiên làm việc khác (Xung đột Revision). Bản nháp của bạn vẫn được giữ nguyên; bạn có thể chọn nạp lại dữ liệu mới nhất để cập nhật.",
            );
          } else if (error.code === "assistant_collection_immutable") {
            setServerError(
              "Không thể thay đổi bộ sưu tập của trợ lý đã tạo. Vui lòng tạo trợ lý mới nếu muốn gắn bộ sưu tập khác.",
            );
          } else {
            setServerError(error.message);
          }
        } else {
          setServerError(
            "Đã xảy ra lỗi không xác định khi lưu trợ lý. Vui lòng thử lại.",
          );
        }
      }
    },
  });

  // Reset form when dialog opens or assistant changes
  useEffect(() => {
    if (open) {
      setServerError(null);
      setConflictError(null);
      form.reset({
        name: assistant?.name ?? "",
        description: assistant?.description ?? "",
        persona: assistant?.persona ?? "",
        collection_id: assistant?.collection_id ?? "",
        chat_provider_id: assistant?.chat_provider_id ?? null,
        top_k: assistant?.top_k ?? 5,
        history_turns: assistant?.history_turns ?? 3,
        max_output_tokens: assistant?.max_output_tokens ?? 2048,
        is_active: assistant?.is_active ?? true,
        rag_policy: toRagPolicyForm(assistant?.rag_policy),
        expected_revision: assistant?.revision ?? 1,
      });
    }
  }, [open, assistant, form.reset]);

  const handleReloadFreshData = () => {
    if (assistant) {
      form.reset({
        name: assistant.name,
        description: assistant.description,
        persona: assistant.persona,
        collection_id: assistant.collection_id,
        chat_provider_id: assistant.chat_provider_id,
        top_k: assistant.top_k,
        history_turns: assistant.history_turns,
        max_output_tokens: assistant.max_output_tokens,
        is_active: assistant.is_active,
        rag_policy: toRagPolicyForm(assistant.rag_policy),
        expected_revision: assistant.revision,
      });
      setConflictError(null);
      setServerError(null);
      toast.info("Đã đồng bộ lại dữ liệu mới nhất từ máy chủ.");
    }
  };

  const isSubmitting = createMutation.isPending || updateMutation.isPending;
  const noCollections =
    !collectionsQuery.isPending &&
    !collectionsQuery.isError &&
    collections.length === 0;

  // Check if current assistant's provider is missing from catalog
  const savedProviderMissing =
    isEdit &&
    Boolean(assistant?.chat_provider_id) &&
    !chatCatalog.some((c) => c.id === assistant?.chat_provider_id);

  const boundCollection = collections.find(
    (c) =>
      c.id ===
      (assistant?.collection_id ?? form.getFieldValue("collection_id")),
  );

  const nameInputId = useId();
  const descInputId = useId();
  const personaInputId = useId();
  const topKInputId = useId();
  const turnsInputId = useId();
  const tokensInputId = useId();
  const activeSwitchId = useId();
  const retrievalModeId = useId();
  const candidateKId = useId();
  const rrfKId = useId();
  const rerankProviderId = useId();
  const contextWindowId = useId();
  const contextBytesId = useId();
  const verificationModeId = useId();
  const verificationProviderId = useId();
  const verificationTokensId = useId();
  const dataYearId = useId();
  const issuedYearId = useId();
  const effectiveOnId = useId();
  const programId = useId();
  const intakeId = useId();

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-h-[min(900px,calc(100vh-2rem))] max-w-2xl p-0 gap-0 flex flex-col">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              {isEdit ? (
                <Save className="size-4" />
              ) : (
                <Bot className="size-4" />
              )}
            </span>
            {isEdit
              ? `Sửa cấu hình trợ lý (v${assistant?.revision})`
              : "Tạo trợ lý AI mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            {isEdit
              ? "Cập nhật thông tin trợ lý, hướng dẫn persona, model chat và tham số tạo phản hồi."
              : "Tạo trợ lý mới gắn với một bộ sưu tập kho tri thức và model chat được cấp phép."}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            void form.handleSubmit();
          }}
          className="flex flex-1 flex-col overflow-hidden"
        >
          <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
            {/* Conflict banner */}
            {conflictError && (
              <Alert variant="destructive">
                <AlertCircle className="size-4" />
                <AlertTitle>Xung đột phiên bản (Revision Conflict)</AlertTitle>
                <AlertDescription className="space-y-2 text-xs">
                  <p>{conflictError}</p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs gap-1.5"
                    onClick={handleReloadFreshData}
                  >
                    <RefreshCw className="size-3" />
                    Tải lại dữ liệu mới nhất
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* General server error */}
            {serverError && (
              <Alert variant="destructive">
                <AlertCircle className="size-4" />
                <AlertTitle>Lỗi lưu trợ lý</AlertTitle>
                <AlertDescription className="text-xs">
                  {serverError}
                </AlertDescription>
              </Alert>
            )}

            {/* No collections warning for create mode */}
            {!isEdit && noCollections && (
              <Alert className="border-amber-500/40 bg-amber-500/5 text-amber-900 dark:text-amber-200">
                <AlertCircle className="size-4 text-amber-600 dark:text-amber-400" />
                <AlertTitle className="text-xs font-semibold">
                  Chưa có bộ sưu tập tri thức
                </AlertTitle>
                <AlertDescription className="text-xs space-y-1.5">
                  <p>
                    Workspace này chưa có bộ sưu tập tri thức nào. Trợ lý AI bắt
                    buộc phải gắn với một bộ sưu tập.
                  </p>
                  <Link
                    to="/workspaces/$workspaceId/collections"
                    params={{ workspaceId }}
                    search={DEFAULT_PAGE_SEARCH}
                    className="inline-flex items-center gap-1 font-medium underline hover:text-amber-700"
                    onClick={() => onOpenChange(false)}
                  >
                    Đi đến trang Kho tri thức để tạo bộ sưu tập
                    <ExternalLink className="size-3" />
                  </Link>
                </AlertDescription>
              </Alert>
            )}

            {/* Section 1: Basic Information */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground border-b pb-1.5">
                <Bot className="size-3.5" />
                Thông tin chung
              </div>

              {/* Name */}
              <form.Field name="name">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  return (
                    <Field>
                      <FieldLabel htmlFor={nameInputId}>
                        Tên trợ lý <span className="text-destructive">*</span>
                      </FieldLabel>
                      <Input
                        id={nameInputId}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        placeholder="VD: Trợ lý Tuyển sinh 2026, Cố vấn Học tập..."
                        maxLength={160}
                        aria-invalid={Boolean(error)}
                        autoFocus={!isEdit}
                      />
                      <FieldDescription>
                        Tên định danh hiển thị của trợ lý (1–160 ký tự).
                      </FieldDescription>
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>

              {/* Description */}
              <form.Field name="description">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  return (
                    <Field>
                      <FieldLabel htmlFor={descInputId}>
                        Mô tả trợ lý
                      </FieldLabel>
                      <Textarea
                        id={descInputId}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        placeholder="Mô tả mục đích sử dụng, đối tượng phục vụ..."
                        rows={2}
                        maxLength={2000}
                        aria-invalid={Boolean(error)}
                      />
                      <FieldDescription>
                        Mô tả ngắn gọn mục đích sử dụng (tối đa 2000 ký tự).
                      </FieldDescription>
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Section 2: Knowledge Binding */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground border-b pb-1.5">
                <Database className="size-3.5" />
                Kho tri thức gắn kết
              </div>

              {isEdit ? (
                // In Edit mode: collection is IMMUTABLE
                <div className="rounded-lg border bg-muted/30 p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-foreground">
                      Bộ sưu tập đang gắn
                    </span>
                    <span className="text-[11px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">
                      Bất biến
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-foreground">
                    {boundCollection?.name ??
                      assistant?.collection_id ??
                      "Đang tải..."}
                  </div>
                  {boundCollection?.description && (
                    <p className="text-xs text-muted-foreground line-clamp-1">
                      {boundCollection.description}
                    </p>
                  )}
                  <p className="text-[11px] text-muted-foreground italic pt-1 border-t">
                    Lưu ý: Bộ sưu tập không thể thay đổi sau khi tạo. Muốn đổi
                    bộ sưu tập, vui lòng tạo trợ lý mới.
                  </p>
                </div>
              ) : (
                // In Create mode: select collection
                <form.Field name="collection_id">
                  {(field) => {
                    const error = fieldError(field.state.meta.errors);
                    return (
                      <Field>
                        <FieldLabel>
                          Chọn bộ sưu tập{" "}
                          <span className="text-destructive">*</span>
                        </FieldLabel>
                        <Select
                          value={field.state.value}
                          onValueChange={(val) => field.handleChange(val)}
                          disabled={collectionsQuery.isPending || noCollections}
                        >
                          <SelectTrigger
                            aria-invalid={Boolean(error)}
                            className="w-full"
                          >
                            <SelectValue placeholder="-- Chọn bộ sưu tập kho tri thức --" />
                          </SelectTrigger>
                          <SelectContent>
                            {collections.map((col) => (
                              <SelectItem key={col.id} value={col.id}>
                                {col.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FieldDescription>
                          Mỗi trợ lý được gắn cố định với một bộ sưu tập tri
                          thức của workspace.
                        </FieldDescription>
                        {error ? <FieldError>{error}</FieldError> : null}
                      </Field>
                    );
                  }}
                </form.Field>
              )}
            </div>

            {/* Section 3: ModelOps Chat Model Selection */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground border-b pb-1.5">
                <Cpu className="size-3.5" />
                Model hội thoại (ModelOps)
              </div>

              {savedProviderMissing && (
                <Alert className="border-amber-500/40 bg-amber-500/5 text-amber-900 dark:text-amber-200">
                  <AlertCircle className="size-4 text-amber-600 dark:text-amber-400" />
                  <AlertTitle className="text-xs font-semibold">
                    Provider cấu hình không còn trong Catalog
                  </AlertTitle>
                  <AlertDescription className="text-xs">
                    Provider ID{" "}
                    <code className="font-mono">
                      {assistant?.chat_provider_id}
                    </code>{" "}
                    đã được lưu trước đó hiện không còn trong danh mục chat khả
                    dụng của workspace. Bạn có thể giữ nguyên hoặc chọn model
                    khác.
                  </AlertDescription>
                </Alert>
              )}

              <form.Field name="chat_provider_id">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  const selectedVal =
                    field.state.value === null || field.state.value === ""
                      ? WORKSPACE_DEFAULT_PROVIDER
                      : field.state.value;

                  return (
                    <Field>
                      <FieldLabel>Model Chat</FieldLabel>
                      <Select
                        value={selectedVal}
                        onValueChange={(val) => {
                          field.handleChange(
                            val === WORKSPACE_DEFAULT_PROVIDER ? null : val,
                          );
                        }}
                        disabled={catalogQuery.isPending}
                      >
                        <SelectTrigger
                          aria-invalid={Boolean(error)}
                          className="w-full"
                        >
                          <SelectValue placeholder="Chọn model..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={WORKSPACE_DEFAULT_PROVIDER}>
                            <span className="font-medium">
                              Theo mặc định workspace
                            </span>
                            <span className="ml-2 text-xs text-muted-foreground">
                              (Giải quyết động qua cấu hình ModelOps)
                            </span>
                          </SelectItem>
                          {chatCatalog.map((item) => (
                            <SelectItem key={item.id} value={item.id}>
                              <span>{item.name}</span>
                              <span className="ml-2 font-mono text-xs text-muted-foreground">
                                [{item.model_name}]
                              </span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FieldDescription>
                        {field.state.value === null
                          ? "Hệ thống sẽ dùng model chat mặc định được gán cho workspace này."
                          : "Chỉ định provider cụ thể trong số các provider có capability chat được cấp phép."}
                      </FieldDescription>
                      <ConsumerModelBudgetNotice
                        model={chatCatalog.find(
                          (item) => item.id === field.state.value,
                        )}
                        defaultModel={chatCatalog.find((item) =>
                          item.default_capabilities?.includes("chat"),
                        )}
                        isDefaultSelection={
                          field.state.value === null || field.state.value === ""
                        }
                        capability="chat"
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Section 4: System Persona / Instructions */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground border-b pb-1.5">
                <Layers className="size-3.5" />
                Chỉ dẫn hệ thống (Persona)
              </div>

              <form.Field name="persona">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  return (
                    <Field>
                      <FieldLabel htmlFor={personaInputId}>
                        Persona / Lời nhắc hệ thống
                      </FieldLabel>
                      <Textarea
                        id={personaInputId}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        placeholder="Bạn là trợ lý tư vấn tuyển sinh của Trường Đại học Quy Nhơn. Trả lời lịch sự, chính xác căn cứ trên tài liệu được cung cấp..."
                        rows={4}
                        maxLength={4000}
                        aria-invalid={Boolean(error)}
                      />
                      <FieldDescription>
                        Định hướng phong cách, vai trò và giới hạn trả lời của
                        trợ lý (tối đa 4000 ký tự).
                      </FieldDescription>
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Section 5: Retrieval & Generation Parameters */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground border-b pb-1.5">
                <Sliders className="size-3.5" />
                Tham số truy xuất & cấu hình phản hồi
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* top_k */}
                <form.Field name="top_k">
                  {(field) => {
                    const error = fieldError(field.state.meta.errors);
                    return (
                      <Field>
                        <FieldLabel htmlFor={topKInputId}>
                          Top K Chunks{" "}
                          <span className="text-destructive">*</span>
                        </FieldLabel>
                        <Input
                          id={topKInputId}
                          type="number"
                          min={1}
                          max={20}
                          value={field.state.value}
                          onChange={(e) =>
                            field.handleChange(
                              e.target.value === ""
                                ? 5
                                : Number(e.target.value),
                            )
                          }
                          onBlur={field.handleBlur}
                          aria-invalid={Boolean(error)}
                        />
                        <FieldDescription>
                          Số đoạn trích (1–20, mặc định 5).
                        </FieldDescription>
                        {error ? <FieldError>{error}</FieldError> : null}
                      </Field>
                    );
                  }}
                </form.Field>

                {/* history_turns */}
                <form.Field name="history_turns">
                  {(field) => {
                    const error = fieldError(field.state.meta.errors);
                    return (
                      <Field>
                        <FieldLabel htmlFor={turnsInputId}>
                          Lượt ngữ cảnh{" "}
                          <span className="text-destructive">*</span>
                        </FieldLabel>
                        <Input
                          id={turnsInputId}
                          type="number"
                          min={0}
                          max={10}
                          value={field.state.value}
                          onChange={(e) =>
                            field.handleChange(
                              e.target.value === ""
                                ? 3
                                : Number(e.target.value),
                            )
                          }
                          onBlur={field.handleBlur}
                          aria-invalid={Boolean(error)}
                        />
                        <FieldDescription>
                          Lịch sử hội thoại (0–10, mặc định 3).
                        </FieldDescription>
                        {error ? <FieldError>{error}</FieldError> : null}
                      </Field>
                    );
                  }}
                </form.Field>

                {/* max_output_tokens */}
                <form.Field name="max_output_tokens">
                  {(field) => {
                    const error = fieldError(field.state.meta.errors);
                    return (
                      <Field>
                        <FieldLabel htmlFor={tokensInputId}>
                          Max Output Tokens{" "}
                          <span className="text-destructive">*</span>
                        </FieldLabel>
                        <Input
                          id={tokensInputId}
                          type="number"
                          min={1}
                          step={128}
                          value={field.state.value}
                          onChange={(e) =>
                            field.handleChange(
                              e.target.value === ""
                                ? 2048
                                : Number(e.target.value),
                            )
                          }
                          onBlur={field.handleBlur}
                          aria-invalid={Boolean(error)}
                        />
                        <FieldDescription>
                          Giới hạn token xuất (mặc định 2048).
                        </FieldDescription>
                        {error ? <FieldError>{error}</FieldError> : null}
                      </Field>
                    );
                  }}
                </form.Field>
              </div>

              {/* RAG policy: retrieval mode, budgets, context and verification */}
              <div className="space-y-4 rounded-lg border p-3.5 bg-muted/10">
                <Collapsible open={ragOpen} onOpenChange={setRagOpen}>
                  <CollapsibleTrigger asChild>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between gap-2 text-left"
                    >
                      <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        <Sparkles className="size-3.5" />
                        Truy xuất &amp; kiểm chứng nâng cao (RAG)
                      </span>
                      <ChevronDown
                        className={`size-3.5 shrink-0 text-muted-foreground transition-transform ${
                          ragOpen ? "rotate-180" : ""
                        }`}
                      />
                    </button>
                  </CollapsibleTrigger>

                  <CollapsibleContent className="pt-4 space-y-4">
                    <p className="text-[11px] leading-relaxed text-muted-foreground">
                      Mặc định giữ tương thích backend: dense, không mở rộng ngữ
                      cảnh, không kiểm chứng. Thay đổi ở đây làm tăng revision
                      và chỉ áp dụng cho hội thoại mới; hội thoại đang chạy giữ
                      nguyên snapshot cũ.
                    </p>

                    <form.Field name="rag_policy.scope_resolution">
                      {(field) => (
                        <Field>
                          <FieldLabel htmlFor="assistant-scope-resolution">
                            Phạm vi câu hỏi
                          </FieldLabel>
                          <Select
                            value={field.state.value}
                            onValueChange={(value) =>
                              field.handleChange(
                                value === "catalog" ? "catalog" : "explicit",
                              )
                            }
                          >
                            <SelectTrigger id="assistant-scope-resolution">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="explicit">
                                Theo bộ lọc đã chọn
                              </SelectItem>
                              <SelectItem value="catalog">
                                Nhận diện từ dữ liệu đã xuất bản
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          <FieldDescription>
                            Khi chưa rõ ngành, khóa hoặc năm, hệ thống yêu cầu
                            làm rõ trước khi trả lời. Chỉ nhận diện giá trị có
                            căn cứ; giữ nguyên bộ lọc đã chọn.
                          </FieldDescription>
                        </Field>
                      )}
                    </form.Field>
                    <form.Field name="rag_policy.retrieval_mode">
                      {(field) => {
                        const error = fieldError(field.state.meta.errors);
                        return (
                          <Field>
                            <FieldLabel htmlFor={retrievalModeId}>
                              Chế độ truy xuất
                            </FieldLabel>
                            <Select
                              value={field.state.value}
                              onValueChange={(value) =>
                                field.handleChange(asRetrievalMode(value))
                              }
                            >
                              <SelectTrigger
                                id={retrievalModeId}
                                className="w-full text-xs"
                                aria-invalid={Boolean(error)}
                              >
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {(
                                  Object.keys(
                                    RETRIEVAL_MODE_LABEL,
                                  ) as RetrievalMode[]
                                ).map((mode) => (
                                  <SelectItem
                                    key={mode}
                                    value={mode}
                                    className="text-xs"
                                  >
                                    {RETRIEVAL_MODE_LABEL[mode]}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FieldDescription className="text-[11px]">
                              Dense chỉ dùng vector. Hybrid thêm tìm từ khóa
                              PostgreSQL và hợp nhất RRF. Hybrid + Rerank cần
                              thêm provider rerank được workspace cấp phép.
                            </FieldDescription>
                            {error ? <FieldError>{error}</FieldError> : null}
                          </Field>
                        );
                      }}
                    </form.Field>

                    <form.Subscribe
                      selector={(state) =>
                        state.values.rag_policy.retrieval_mode
                      }
                    >
                      {(mode) =>
                        mode === "dense" ? null : (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <form.Field name="rag_policy.candidate_k">
                              {(field) => {
                                const error = fieldError(
                                  field.state.meta.errors,
                                );
                                return (
                                  <Field>
                                    <FieldLabel htmlFor={candidateKId}>
                                      Ngân sách ứng viên (candidate_k)
                                    </FieldLabel>
                                    <Input
                                      id={candidateKId}
                                      type="number"
                                      min={1}
                                      max={100}
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(
                                          e.target.value === ""
                                            ? 30
                                            : Number(e.target.value),
                                        )
                                      }
                                      onBlur={field.handleBlur}
                                      aria-invalid={Boolean(error)}
                                      className="text-xs"
                                    />
                                    <FieldDescription className="text-[11px]">
                                      Số ứng viên trước khi cắt Top K (1–100).
                                    </FieldDescription>
                                    {error ? (
                                      <FieldError>{error}</FieldError>
                                    ) : null}
                                  </Field>
                                );
                              }}
                            </form.Field>

                            <form.Field name="rag_policy.rrf_k">
                              {(field) => {
                                const error = fieldError(
                                  field.state.meta.errors,
                                );
                                return (
                                  <Field>
                                    <FieldLabel htmlFor={rrfKId}>
                                      Hằng số RRF (rrf_k)
                                    </FieldLabel>
                                    <Input
                                      id={rrfKId}
                                      type="number"
                                      min={1}
                                      max={1000}
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(
                                          e.target.value === ""
                                            ? 60
                                            : Number(e.target.value),
                                        )
                                      }
                                      onBlur={field.handleBlur}
                                      aria-invalid={Boolean(error)}
                                      className="text-xs"
                                    />
                                    <FieldDescription className="text-[11px]">
                                      Dùng khi hợp nhất thứ hạng dense và từ
                                      khóa (1–1000).
                                    </FieldDescription>
                                    {error ? (
                                      <FieldError>{error}</FieldError>
                                    ) : null}
                                  </Field>
                                );
                              }}
                            </form.Field>
                          </div>
                        )
                      }
                    </form.Subscribe>

                    <form.Subscribe
                      selector={(state) =>
                        state.values.rag_policy.retrieval_mode
                      }
                    >
                      {(mode) =>
                        mode === "hybrid_rerank" ? (
                          <form.Field name="rag_policy.rerank_provider_id">
                            {(field) => {
                              const error = fieldError(field.state.meta.errors);
                              return (
                                <Field>
                                  <FieldLabel htmlFor={rerankProviderId}>
                                    Provider rerank
                                  </FieldLabel>
                                  <Select
                                    value={
                                      field.state.value ?? NO_PROVIDER_VALUE
                                    }
                                    onValueChange={(value) =>
                                      field.handleChange(
                                        value === NO_PROVIDER_VALUE
                                          ? null
                                          : value,
                                      )
                                    }
                                    disabled={catalogQuery.isPending}
                                  >
                                    <SelectTrigger
                                      id={rerankProviderId}
                                      className="w-full text-xs"
                                      aria-invalid={Boolean(error)}
                                    >
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem
                                        value={NO_PROVIDER_VALUE}
                                        className="text-xs"
                                      >
                                        Không dùng rerank
                                      </SelectItem>
                                      {rerankCatalog.map((item) => (
                                        <SelectItem
                                          key={item.id}
                                          value={item.id}
                                          className="text-xs"
                                        >
                                          {item.name}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <FieldDescription className="text-[11px]">
                                    Chỉ liệt kê provider có capability rerank
                                    trong danh mục workspace. Điểm rerank là
                                    thang riêng, không phải xác suất đúng.
                                  </FieldDescription>
                                  {rerankCatalog.length === 0 &&
                                  !catalogQuery.isPending ? (
                                    <p className="text-[11px] text-muted-foreground">
                                      Workspace chưa có provider rerank được cấp
                                      phép.
                                    </p>
                                  ) : null}
                                  {error ? (
                                    <FieldError>{error}</FieldError>
                                  ) : null}
                                </Field>
                              );
                            }}
                          </form.Field>
                        ) : null
                      }
                    </form.Subscribe>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <form.Field name="rag_policy.context_window">
                        {(field) => {
                          const error = fieldError(field.state.meta.errors);
                          return (
                            <Field>
                              <FieldLabel htmlFor={contextWindowId}>
                                Cửa sổ ngữ cảnh (context_window)
                              </FieldLabel>
                              <Input
                                id={contextWindowId}
                                type="number"
                                min={0}
                                max={5}
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(
                                    e.target.value === ""
                                      ? 0
                                      : Number(e.target.value),
                                  )
                                }
                                onBlur={field.handleBlur}
                                aria-invalid={Boolean(error)}
                                className="text-xs"
                              />
                              <FieldDescription className="text-[11px]">
                                Số chunk kề cùng tài liệu lấy thêm sau rerank
                                (0–5). 0 giữ hành vi cũ.
                              </FieldDescription>
                              {error ? <FieldError>{error}</FieldError> : null}
                            </Field>
                          );
                        }}
                      </form.Field>

                      <form.Field name="rag_policy.context_max_bytes">
                        {(field) => {
                          const error = fieldError(field.state.meta.errors);
                          return (
                            <Field>
                              <FieldLabel htmlFor={contextBytesId}>
                                Ngân sách ngữ cảnh (byte)
                              </FieldLabel>
                              <Input
                                id={contextBytesId}
                                type="number"
                                min={256}
                                max={128000}
                                step={256}
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(
                                    e.target.value === ""
                                      ? 16000
                                      : Number(e.target.value),
                                  )
                                }
                                onBlur={field.handleBlur}
                                aria-invalid={Boolean(error)}
                                className="text-xs"
                              />
                              <FieldDescription className="text-[11px]">
                                Giới hạn JSON evidence gửi model (256–128000
                                byte), không phải số token.
                              </FieldDescription>
                              {error ? <FieldError>{error}</FieldError> : null}
                            </Field>
                          );
                        }}
                      </form.Field>
                    </div>

                    <form.Field name="rag_policy.verification_mode">
                      {(field) => {
                        const error = fieldError(field.state.meta.errors);
                        return (
                          <Field>
                            <FieldLabel htmlFor={verificationModeId}>
                              Kiểm chứng câu trả lời
                            </FieldLabel>
                            <Select
                              value={field.state.value}
                              onValueChange={(value) =>
                                field.handleChange(asVerificationMode(value))
                              }
                            >
                              <SelectTrigger
                                id={verificationModeId}
                                className="w-full text-xs"
                                aria-invalid={Boolean(error)}
                              >
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {(
                                  Object.keys(
                                    VERIFICATION_MODE_LABEL,
                                  ) as VerificationMode[]
                                ).map((mode) => (
                                  <SelectItem
                                    key={mode}
                                    value={mode}
                                    className="text-xs"
                                  >
                                    {VERIFICATION_MODE_LABEL[mode]}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FieldDescription className="text-[11px]">
                              Quan sát chỉ gắn cảnh báo vào câu trả lời. Chặn
                              giữ câu trả lời lại khi nguồn không xác nhận. Nên
                              chạy quan sát trước khi bật chặn cho dữ liệu thật.
                            </FieldDescription>
                            {error ? <FieldError>{error}</FieldError> : null}
                          </Field>
                        );
                      }}
                    </form.Field>

                    <form.Subscribe
                      selector={(state) =>
                        state.values.rag_policy.verification_mode
                      }
                    >
                      {(mode) =>
                        mode === "off" ? null : (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <form.Field name="rag_policy.verification_provider_id">
                              {(field) => {
                                const error = fieldError(
                                  field.state.meta.errors,
                                );
                                return (
                                  <Field>
                                    <FieldLabel
                                      htmlFor={verificationProviderId}
                                    >
                                      Provider kiểm chứng
                                    </FieldLabel>
                                    <Select
                                      value={
                                        field.state.value ?? NO_PROVIDER_VALUE
                                      }
                                      onValueChange={(value) =>
                                        field.handleChange(
                                          value === NO_PROVIDER_VALUE
                                            ? null
                                            : value,
                                        )
                                      }
                                      disabled={catalogQuery.isPending}
                                    >
                                      <SelectTrigger
                                        id={verificationProviderId}
                                        className="w-full text-xs"
                                        aria-invalid={Boolean(error)}
                                      >
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem
                                          value={NO_PROVIDER_VALUE}
                                          className="text-xs"
                                        >
                                          Dùng model chat của yêu cầu
                                        </SelectItem>
                                        {chatCatalog.map((item) => (
                                          <SelectItem
                                            key={item.id}
                                            value={item.id}
                                            className="text-xs"
                                          >
                                            {item.name}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                    <FieldDescription className="text-[11px]">
                                      Chỉ provider có capability chat. Bỏ trống
                                      để dùng model chat mặc định.
                                    </FieldDescription>
                                    {error ? (
                                      <FieldError>{error}</FieldError>
                                    ) : null}
                                  </Field>
                                );
                              }}
                            </form.Field>

                            <form.Field name="rag_policy.verification_max_output_tokens">
                              {(field) => {
                                const error = fieldError(
                                  field.state.meta.errors,
                                );
                                return (
                                  <Field>
                                    <FieldLabel htmlFor={verificationTokensId}>
                                      Token xuất tối đa cho kiểm chứng
                                    </FieldLabel>
                                    <Input
                                      id={verificationTokensId}
                                      type="number"
                                      min={128}
                                      max={16000}
                                      step={128}
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(
                                          e.target.value === ""
                                            ? 2048
                                            : Number(e.target.value),
                                        )
                                      }
                                      onBlur={field.handleBlur}
                                      aria-invalid={Boolean(error)}
                                      className="text-xs"
                                    />
                                    <FieldDescription className="text-[11px]">
                                      Ngân sách riêng của lượt judge
                                      (128–16000), tách khỏi ngân sách sinh câu
                                      trả lời.
                                    </FieldDescription>
                                    {error ? (
                                      <FieldError>{error}</FieldError>
                                    ) : null}
                                  </Field>
                                );
                              }}
                            </form.Field>
                          </div>
                        )
                      }
                    </form.Subscribe>

                    <div className="space-y-3 border-t pt-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Phạm vi metadata mặc định
                      </p>
                      <p className="text-[11px] leading-relaxed text-muted-foreground">
                        Lọc theo metadata đã được người duyệt gắn cho tài liệu.
                        Bỏ trống nghĩa là không giới hạn. Trường nào cũng phải
                        khớp trên cùng một đơn vị được annotation; giá trị
                        unknown không khớp bộ lọc đã đặt.
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <form.Field name="rag_policy.filter_data_year">
                          {(field) => (
                            <Field>
                              <FieldLabel htmlFor={dataYearId}>
                                Năm dữ liệu
                              </FieldLabel>
                              <Input
                                id={dataYearId}
                                type="number"
                                min={1000}
                                max={9999}
                                placeholder="Không giới hạn"
                                value={field.state.value ?? ""}
                                onChange={(e) =>
                                  field.handleChange(
                                    e.target.value === ""
                                      ? null
                                      : Number(e.target.value),
                                  )
                                }
                                onBlur={field.handleBlur}
                                className="text-xs"
                              />
                            </Field>
                          )}
                        </form.Field>

                        <form.Field name="rag_policy.filter_issued_year">
                          {(field) => (
                            <Field>
                              <FieldLabel htmlFor={issuedYearId}>
                                Năm ban hành
                              </FieldLabel>
                              <Input
                                id={issuedYearId}
                                type="number"
                                min={1000}
                                max={9999}
                                placeholder="Không giới hạn"
                                value={field.state.value ?? ""}
                                onChange={(e) =>
                                  field.handleChange(
                                    e.target.value === ""
                                      ? null
                                      : Number(e.target.value),
                                  )
                                }
                                onBlur={field.handleBlur}
                                className="text-xs"
                              />
                            </Field>
                          )}
                        </form.Field>

                        <form.Field name="rag_policy.filter_effective_on">
                          {(field) => (
                            <Field>
                              <FieldLabel htmlFor={effectiveOnId}>
                                Hiệu lực tại ngày
                              </FieldLabel>
                              <Input
                                id={effectiveOnId}
                                type="date"
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(e.target.value)
                                }
                                onBlur={field.handleBlur}
                                className="text-xs"
                              />
                              <FieldDescription className="text-[11px]">
                                Chỉ khớp khi tài liệu có đủ cả ngày bắt đầu và
                                kết thúc hiệu lực.
                              </FieldDescription>
                            </Field>
                          )}
                        </form.Field>

                        <form.Field name="rag_policy.filter_program">
                          {(field) => (
                            <Field>
                              <FieldLabel htmlFor={programId}>Ngành</FieldLabel>
                              <Input
                                id={programId}
                                maxLength={160}
                                placeholder="VD: Kỹ thuật phần mềm"
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(e.target.value)
                                }
                                onBlur={field.handleBlur}
                                className="text-xs"
                              />
                            </Field>
                          )}
                        </form.Field>

                        <form.Field name="rag_policy.filter_intake">
                          {(field) => (
                            <Field>
                              <FieldLabel htmlFor={intakeId}>Đợt</FieldLabel>
                              <Input
                                id={intakeId}
                                maxLength={160}
                                placeholder="VD: Đợt 1 - 2026"
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(e.target.value)
                                }
                                onBlur={field.handleBlur}
                                className="text-xs"
                              />
                            </Field>
                          )}
                        </form.Field>
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </div>

              {/* is_active */}
              <form.Field name="is_active">
                {(field) => (
                  <div className="flex items-center justify-between rounded-lg border p-3.5 bg-muted/10">
                    <div className="space-y-0.5">
                      <FieldLabel htmlFor={activeSwitchId}>
                        Trạng thái kích hoạt (Active)
                      </FieldLabel>
                      <p className="text-xs text-muted-foreground">
                        Bật trợ lý cho phép sử dụng trong workspace. Lưu ý: Cần
                        đảm bảo tài liệu trong kho tri thức đã được xử lý và
                        model chat sẵn sàng.
                      </p>
                    </div>
                    <Switch
                      id={activeSwitchId}
                      checked={field.state.value}
                      onCheckedChange={(checked) => field.handleChange(checked)}
                    />
                  </div>
                )}
              </form.Field>
            </div>
          </div>

          <ResponsiveDialogFooter className="border-t bg-muted/20 px-4 py-3 sm:px-6 flex items-center justify-between">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting || (!isEdit && noCollections)}
              className="gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Đang lưu...
                </>
              ) : isEdit ? (
                <>
                  <Save className="size-4" />
                  Lưu cấu hình
                </>
              ) : (
                <>
                  <Bot className="size-4" />
                  Tạo trợ lý
                </>
              )}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
