import { useForm } from "@tanstack/react-form";
import {
  ChevronDown,
  Loader2,
  Plus,
  RotateCcw,
  Save,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
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
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  buildClearTokenLimitsPatch,
  buildProviderPatch,
  draftFromProvider,
  EMPTY_CAPACITY_DRAFT,
  embeddingDimensionFromDraft,
  isEmptyProviderPatch,
  type ProviderFormValues,
  tokenLimitsFromDraft,
  validateCapacityDraft,
} from "@/features/modelops/capacity-patch";
import {
  useCreateProvider,
  useUpdateProvider,
} from "@/features/modelops/queries";
import {
  providerFormSchema,
  providerUpdateSchema,
} from "@/features/modelops/schemas";
import {
  CAPABILITIES,
  CAPABILITY_LABELS,
  type Capability,
  type Provider,
  type ProviderType,
} from "@/features/modelops/types";
import { getFormErrorMessage } from "@/lib/form-errors";
import { useTransportRegistry } from "./resilience-queries";

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

export function ProviderFormDialog({
  open,
  onOpenChange,
  provider,
  suggestedModel,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider?: Provider | null;
  suggestedModel?: string;
}) {
  const isEdit = Boolean(provider);
  const isChildModel = Boolean(provider?.parent_id);
  const registry = useTransportRegistry();
  const createMutation = useCreateProvider();
  const updateMutation = useUpdateProvider(provider?.id ?? "");
  const [serverError, setServerError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [confirmClearLimits, setConfirmClearLimits] = useState(false);
  const [providerType, setProviderType] = useState<ProviderType>(
    provider?.provider_type ?? "openai_compatible",
  );

  const transport = registry.data?.find(
    (item) => item.provider_type === providerType,
  );

  const initialCapacity = provider
    ? draftFromProvider(provider)
    : EMPTY_CAPACITY_DRAFT;

  const form = useForm({
    defaultValues: {
      name: provider?.name ?? "",
      baseUrl: provider?.base_url ?? "",
      modelName: provider?.model_name ?? "",
      capabilities: (provider?.capabilities ?? []) as Capability[],
      priority: String(provider?.priority ?? 5),
      timeoutSeconds: String(provider?.timeout_seconds ?? 30),
      ...initialCapacity,
    },
    validators: {
      onSubmit: isEdit ? providerUpdateSchema : providerFormSchema,
    },
    onSubmit: async ({ value }) => {
      setServerError(null);
      const capacity = {
        contextWindowTokens: value.contextWindowTokens,
        maxInputTokens: value.maxInputTokens,
        maxOutputTokens: value.maxOutputTokens,
        embeddingDimension: value.embeddingDimension,
        ocrMaxImageWidth: value.ocrMaxImageWidth,
        ocrMaxImageHeight: value.ocrMaxImageHeight,
        ocrInputTokensUpperBound: value.ocrInputTokensUpperBound,
        ocrPromptSha256: value.ocrPromptSha256,
      };
      const capacityProblem = validateCapacityDraft(capacity);
      if (capacityProblem) {
        setServerError(capacityProblem);
        return;
      }

      const values: ProviderFormValues = {
        name: value.name,
        baseUrl: value.baseUrl,
        modelName: value.modelName,
        capabilities: value.capabilities as Capability[],
        priority: value.priority,
        timeoutSeconds: value.timeoutSeconds,
        capacity,
      };

      try {
        if (provider) {
          const patch = buildProviderPatch(provider, values);
          if (isEmptyProviderPatch(patch)) {
            toast.info("Không có thay đổi nào để lưu.");
            onOpenChange(false);
            return;
          }
          await updateMutation.mutateAsync(patch);
          toast.success("Đã cập nhật provider.");
        } else {
          const limits = tokenLimitsFromDraft(capacity);
          const dimension = embeddingDimensionFromDraft(capacity);
          await createMutation.mutateAsync({
            name: values.name.trim(),
            provider_type: providerType,
            base_url: values.baseUrl.trim(),
            model_name: values.modelName.trim(),
            capabilities: values.capabilities,
            priority: Number(values.priority),
            timeout_seconds: Number(values.timeoutSeconds),
            ...(limits !== null ? { token_limits: limits } : {}),
            ...(dimension !== null ? { embedding_dimension: dimension } : {}),
          });
          toast.success("Đã tạo provider.");
        }
        onOpenChange(false);
      } catch (error) {
        setServerError(
          error instanceof ApiProblemError
            ? error.message
            : "Không lưu được provider. Vui lòng thử lại.",
        );
      }
    },
  });

  useEffect(() => {
    if (open) {
      const cap = provider ? draftFromProvider(provider) : EMPTY_CAPACITY_DRAFT;
      setProviderType(provider?.provider_type ?? "openai_compatible");
      setAdvancedOpen(false);
      setConfirmClearLimits(false);
      form.reset({
        name: provider?.name ?? "",
        baseUrl: provider?.base_url ?? "",
        modelName: suggestedModel ?? provider?.model_name ?? "",
        capabilities: (provider?.capabilities ?? []) as Capability[],
        priority: String(provider?.priority ?? 5),
        timeoutSeconds: String(provider?.timeout_seconds ?? 30),
        ...cap,
      });
      setServerError(null);
    }
  }, [open, provider, suggestedModel, form.reset]);

  const handleConfirmClearDeclaredLimits = async () => {
    if (!provider) return;
    setServerError(null);
    try {
      await updateMutation.mutateAsync(buildClearTokenLimitsPatch());
      toast.success(
        "Đã xóa khai báo giới hạn; model chuyển sang dùng ngân sách vận hành tự động.",
      );
      setConfirmClearLimits(false);
      onOpenChange(false);
    } catch (error) {
      setConfirmClearLimits(false);
      setServerError(
        error instanceof ApiProblemError
          ? error.message
          : "Không thể xóa khai báo giới hạn.",
      );
    }
  };

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setServerError(null);
        onOpenChange(next);
      }}
    >
      <ResponsiveDialogContent className="flex max-h-[min(860px,calc(100vh-2rem))] w-full max-w-2xl flex-col gap-0 overflow-hidden p-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4">
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
              {isEdit ? (
                <Save className="size-4" />
              ) : (
                <Plus className="size-4" />
              )}
            </span>
            {isChildModel
              ? "Cấu hình model"
              : isEdit
                ? "Sửa provider"
                : "Thêm provider"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            {isChildModel ? (
              "Khai báo giới hạn xử lý theo cấu hình server thực tế. Sau khi lưu, chạy lại kiểm tra model trước khi dùng trong quy trình."
            ) : (
              <>
                Một bản ghi provider là một endpoint gắn với đúng một
                <code className="mx-1 font-mono">model_name</code>. Có thể lấy
                danh sách và chạy thử trên trang chi tiết sau khi lưu provider
                và khóa.
              </>
            )}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          <div className="grid gap-4 px-4 py-4">
            {serverError ? (
              <p
                role="alert"
                className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
              >
                {serverError}
              </p>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <form.Field name="name">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  return (
                    <Field>
                      <FieldLabel htmlFor="provider-name">
                        Tên provider
                      </FieldLabel>
                      <Input
                        id="provider-name"
                        className="text-xs"
                        placeholder="Nemotron local"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                        aria-invalid={Boolean(error)}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>

              <Field>
                <FieldLabel htmlFor="provider-type">Loại provider</FieldLabel>
                <Select
                  value={providerType}
                  onValueChange={(value) =>
                    setProviderType(value as ProviderType)
                  }
                  disabled={isEdit || isSubmitting || !registry.data}
                >
                  <SelectTrigger id="provider-type" className="h-9 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(
                      registry.data ?? [
                        { provider_type: providerType, label: providerType },
                      ]
                    ).map((item) => (
                      <SelectItem
                        key={item.provider_type}
                        value={item.provider_type}
                        className="text-xs"
                      >
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldDescription className="text-[11px]">
                  {isEdit
                    ? "PATCH không nhận provider_type nên không đổi được sau khi tạo."
                    : "Chỉ gửi khi tạo mới."}
                </FieldDescription>
              </Field>
            </div>

            {registry.isError && (
              <p role="alert" className="text-sm text-destructive">
                Không lấy được thông tin giao thức. Hãy thử mở lại cấu hình.
              </p>
            )}
            {transport && (
              <p className="text-xs text-muted-foreground">
                Adapter hỗ trợ:{" "}
                {Object.keys(transport.protocols).join(", ") ||
                  "chưa có runtime"}
                . Responses API:{" "}
                {transport.responses_api ? "có" : "chưa hỗ trợ"}.
              </p>
            )}
            <form.Field name="baseUrl">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="provider-base-url">
                      Base URL
                    </FieldLabel>
                    <Input
                      id="provider-base-url"
                      className="text-xs font-mono"
                      placeholder="http://127.0.0.1:11434/v1"
                      value={field.state.value}
                      disabled={isSubmitting || Boolean(provider?.parent_id)}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                    />
                    <FieldDescription className="text-[11px]">
                      Đổi base URL hoặc model name sẽ khiến năng lực đã khai báo
                      chuyển sang trạng thái cần khai báo lại.
                    </FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>

            <form.Field name="modelName">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="provider-model-name">
                      Model name
                    </FieldLabel>
                    <Input
                      id="provider-model-name"
                      className="text-xs font-mono"
                      placeholder="nvidia/nemotron-3-nano"
                      value={field.state.value}
                      disabled={isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                    />
                    <FieldDescription className="text-[11px]">
                      Giá trị gửi nguyên văn tới provider. Bạn cũng có thể chọn
                      từ danh sách model ở trang chi tiết provider.
                    </FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>

            <form.Field name="capabilities">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel>Capabilities</FieldLabel>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {CAPABILITIES.map((capability) => {
                        const checked = field.state.value.includes(capability);
                        const id = `provider-capability-${capability}`;
                        return (
                          <div
                            key={capability}
                            className="flex items-center gap-2 rounded-md border px-3 py-2"
                          >
                            <Checkbox
                              id={id}
                              checked={checked}
                              disabled={isSubmitting}
                              onCheckedChange={(next) => {
                                field.handleChange(
                                  next
                                    ? [...field.state.value, capability]
                                    : field.state.value.filter(
                                        (item) => item !== capability,
                                      ),
                                );
                              }}
                            />
                            <label
                              htmlFor={id}
                              className="text-xs font-medium leading-none"
                            >
                              {CAPABILITY_LABELS[capability]}
                            </label>
                          </div>
                        );
                      })}
                    </div>
                    <FieldDescription className="text-[11px]">
                      Chỉ capability được khai báo mới dùng được làm model mặc
                      định.
                    </FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>

            <div className="grid gap-4 sm:grid-cols-2">
              <form.Field name="priority">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  return (
                    <Field>
                      <FieldLabel htmlFor="provider-priority">
                        Priority
                      </FieldLabel>
                      <Input
                        id="provider-priority"
                        inputMode="numeric"
                        className="text-xs"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                        aria-invalid={Boolean(error)}
                      />
                      <FieldDescription className="text-[11px]">
                        1–10, số nhỏ được ưu tiên hơn.
                      </FieldDescription>
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>

              <form.Field name="timeoutSeconds">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  return (
                    <Field>
                      <FieldLabel htmlFor="provider-timeout">
                        Timeout (giây)
                      </FieldLabel>
                      <Input
                        id="provider-timeout"
                        inputMode="numeric"
                        className="text-xs"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                        aria-invalid={Boolean(error)}
                      />
                      <FieldDescription className="text-[11px]">
                        1–600 giây.
                      </FieldDescription>
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Vùng Nâng cao thu gọn mặc định */}
            <div className="rounded-lg border bg-muted/15 p-3.5">
              <button
                type="button"
                aria-expanded={advancedOpen}
                onClick={() => setAdvancedOpen((prev) => !prev)}
                className="flex w-full items-center justify-between gap-2 text-left text-xs font-semibold text-foreground"
              >
                <span>
                  Nâng cao (Giới hạn token & thông số kỹ thuật tùy chọn)
                </span>
                <ChevronDown
                  className={`size-4 text-muted-foreground transition-transform ${
                    advancedOpen ? "rotate-180" : ""
                  }`}
                />
              </button>
              <p className="mt-1 text-[11px] leading-5 text-muted-foreground">
                Không bắt buộc trong chế độ thông thường. Nếu chưa công bố giới
                hạn, backend tự áp dụng ngân sách vận hành tạm tính. Bỏ trống
                nghĩa là <strong>Chưa công bố</strong> (đơn vị: token).
              </p>

              <div
                hidden={!advancedOpen}
                className={
                  advancedOpen ? "mt-3 space-y-4 border-t pt-3" : "hidden"
                }
              >
                {isEdit && provider?.token_limits !== null ? (
                  <div className="flex flex-col gap-2 rounded-md bg-muted/40 p-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="space-y-0.5 text-xs">
                      <p className="font-medium text-foreground">
                        Đang có giới hạn token đã khai báo
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        Bạn có thể xóa khai báo thủ công/công bố hiện tại để
                        model chuyển sang dùng ngân sách vận hành tự động của hệ
                        thống.
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 shrink-0 gap-1.5 text-xs"
                      disabled={isSubmitting}
                      onClick={() => setConfirmClearLimits(true)}
                    >
                      <RotateCcw className="size-3.5" />
                      <span>Xóa khai báo giới hạn</span>
                    </Button>
                  </div>
                ) : null}

                <div className="grid gap-4 sm:grid-cols-3">
                  {(
                    [
                      ["contextWindowTokens", "context_window_tokens"],
                      ["maxInputTokens", "max_input_tokens"],
                      ["maxOutputTokens", "max_output_tokens"],
                    ] as const
                  ).map(([fieldName, label]) => (
                    <form.Field key={fieldName} name={fieldName}>
                      {(field) => {
                        const error = fieldError(field.state.meta.errors);
                        return (
                          <Field>
                            <FieldLabel htmlFor={`provider-${fieldName}`}>
                              {label}
                            </FieldLabel>
                            <Input
                              id={`provider-${fieldName}`}
                              inputMode="numeric"
                              className="text-xs font-mono"
                              placeholder="Chưa công bố"
                              value={field.state.value}
                              disabled={isSubmitting}
                              onBlur={field.handleBlur}
                              onChange={(event) => {
                                setAdvancedOpen(true);
                                field.handleChange(event.target.value);
                              }}
                              aria-invalid={Boolean(error)}
                            />
                            {error ? <FieldError>{error}</FieldError> : null}
                          </Field>
                        );
                      }}
                    </form.Field>
                  ))}
                </div>

                <form.Field name="embeddingDimension">
                  {(field) => {
                    const error = fieldError(field.state.meta.errors);
                    return (
                      <Field>
                        <FieldLabel htmlFor="provider-embedding-dimension">
                          embedding_dimension
                        </FieldLabel>
                        <Input
                          id="provider-embedding-dimension"
                          inputMode="numeric"
                          className="text-xs font-mono sm:max-w-[220px]"
                          placeholder="Chưa công bố"
                          value={field.state.value}
                          disabled={isSubmitting}
                          onBlur={field.handleBlur}
                          onChange={(event) => {
                            setAdvancedOpen(true);
                            field.handleChange(event.target.value);
                          }}
                          aria-invalid={Boolean(error)}
                        />
                        <FieldDescription className="text-[11px]">
                          Số chiều vector của model embedding. Để trống nếu chưa
                          công bố.
                        </FieldDescription>
                        {error ? <FieldError>{error}</FieldError> : null}
                      </Field>
                    );
                  }}
                </form.Field>

                <fieldset className="grid gap-3 border-t pt-3">
                  <legend className="px-1 text-xs font-semibold">
                    ocr_page_input
                  </legend>
                  <p className="text-[11px] leading-5 text-muted-foreground">
                    Ngân sách token cho một trang ảnh. Cần khai báo cùng ít nhất
                    một giới hạn token của model. Không suy ra từ độ dài Base64
                    hay từ một mẫu thử.
                  </p>
                  <div className="grid gap-4 sm:grid-cols-3">
                    {(
                      [
                        ["ocrMaxImageWidth", "max_image_width"],
                        ["ocrMaxImageHeight", "max_image_height"],
                        [
                          "ocrInputTokensUpperBound",
                          "input_tokens_upper_bound",
                        ],
                      ] as const
                    ).map(([fieldName, label]) => (
                      <form.Field key={fieldName} name={fieldName}>
                        {(field) => (
                          <Field>
                            <FieldLabel htmlFor={`provider-${fieldName}`}>
                              {label}
                            </FieldLabel>
                            <Input
                              id={`provider-${fieldName}`}
                              inputMode="numeric"
                              className="text-xs font-mono"
                              placeholder="Chưa công bố"
                              value={field.state.value}
                              disabled={isSubmitting}
                              onBlur={field.handleBlur}
                              onChange={(event) => {
                                setAdvancedOpen(true);
                                field.handleChange(event.target.value);
                              }}
                            />
                          </Field>
                        )}
                      </form.Field>
                    ))}
                  </div>
                  <form.Field name="ocrPromptSha256">
                    {(field) => (
                      <Field>
                        <FieldLabel htmlFor="provider-ocr-prompt-sha256">
                          prompt_sha256
                        </FieldLabel>
                        <Input
                          id="provider-ocr-prompt-sha256"
                          className="text-xs font-mono"
                          placeholder="64 ký tự hex thường"
                          value={field.state.value}
                          disabled={isSubmitting}
                          onBlur={field.handleBlur}
                          onChange={(event) => {
                            setAdvancedOpen(true);
                            field.handleChange(event.target.value);
                          }}
                        />
                      </Field>
                    )}
                  </form.Field>
                </fieldset>

                {isEdit && provider ? (
                  <p className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-[11px] leading-5">
                    <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
                    <span>
                      Đổi <code className="font-mono">base_url</code> hoặc{" "}
                      <code className="font-mono">model_name</code> sẽ làm năng
                      lực hiện tại thành cũ (stale) cho tới khi khai báo lại.
                    </span>
                  </p>
                ) : null}
              </div>
            </div>
          </div>

          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              disabled={isSubmitting}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, formSubmitting]) => (
                <Button
                  type="submit"
                  size="sm"
                  className="gap-1.5 text-xs font-semibold"
                  disabled={
                    !canSubmit ||
                    formSubmitting ||
                    isSubmitting ||
                    (!isEdit && !registry.data)
                  }
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" />
                      <span>Đang lưu...</span>
                    </>
                  ) : (
                    <>
                      <Save className="size-3.5" />
                      <span>{isEdit ? "Lưu thay đổi" : "Tạo provider"}</span>
                    </>
                  )}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>

        <ConfirmDialog
          open={confirmClearLimits}
          onOpenChange={(next) => {
            if (!isSubmitting) setConfirmClearLimits(next);
          }}
          title="Xóa giới hạn token đã khai báo?"
          description={
            <div className="space-y-2 text-xs">
              <p>
                Thao tác này gửi{" "}
                <code className="font-mono">token_limits: null</code> để xóa
                giới hạn đã khai báo của model{" "}
                <strong className="font-mono">{provider?.model_name}</strong>.
              </p>
              <p>
                Sau khi xóa, model sẽ chuyển sang dùng ngân sách vận hành tự
                động (tạm tính) của hệ thống cho đến khi được đồng bộ từ server
                hoặc khai báo lại.
              </p>
            </div>
          }
          confirmLabel="Xác nhận xóa khai báo"
          isLoading={isSubmitting}
          onConfirm={() => void handleConfirmClearDeclaredLimits()}
        />
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
