import { useForm } from "@tanstack/react-form";
import {
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  RefreshCw,
  ShieldOff,
} from "lucide-react";
import { type ReactNode, useState } from "react";
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateProviderKey,
  useRevokeProviderKey,
  useRotateProviderKey,
} from "@/features/modelops/queries";
import {
  keyCreateSchema,
  keyRevokeSchema,
  keyRotateSchema,
} from "@/features/modelops/schemas";
import type { ProviderKey } from "@/features/modelops/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { getFormErrorMessage } from "@/lib/form-errors";

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

/**
 * Secret fields are plain local state: they are never put in the URL, never
 * written to a query key, never logged and never echoed in a toast. The dialog
 * is mounted only while open, so closing it drops the value.
 */
function SecretField({
  id,
  value,
  onChange,
  disabled,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  const [revealed, setRevealed] = useState(false);
  return (
    <div className="relative">
      <Input
        id={id}
        type={revealed ? "text" : "password"}
        className="pr-9 text-xs font-mono"
        placeholder="Dán secret của provider"
        autoComplete="off"
        spellCheck={false}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute right-1 top-1 size-7"
        aria-label={revealed ? "Ẩn secret" : "Hiện secret"}
        disabled={disabled}
        onClick={() => setRevealed((current) => !current)}
      >
        {revealed ? (
          <EyeOff className="size-3.5" />
        ) : (
          <Eye className="size-3.5" />
        )}
      </Button>
    </div>
  );
}

function DialogShell({
  title,
  description,
  icon,
  children,
  footer,
  onSubmit,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  children: ReactNode;
  footer: ReactNode;
  onSubmit?: (event: React.FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <ResponsiveDialogContent className="flex max-h-[min(720px,calc(100vh-2rem))] w-full max-w-lg flex-col gap-0 overflow-hidden p-0">
      <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4">
        <ResponsiveDialogTitle className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
            {icon}
          </span>
          {title}
        </ResponsiveDialogTitle>
        <ResponsiveDialogDescription className="text-xs">
          {description}
        </ResponsiveDialogDescription>
      </ResponsiveDialogHeader>
      <form
        className="flex min-h-0 flex-1 flex-col overflow-hidden"
        onSubmit={(event) => {
          if (onSubmit) {
            onSubmit(event);
          } else {
            event.preventDefault();
          }
        }}
      >
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {children}
        </div>
        {footer}
      </form>
    </ResponsiveDialogContent>
  );
}

export function KeyCreateDialog({
  providerId,
  onClose,
}: {
  providerId: string;
  onClose: () => void;
}) {
  const mutation = useCreateProviderKey(providerId);
  const [serverError, setServerError] = useState<string | null>(null);

  const handleClose = () => {
    form.reset();
    mutation.reset();
    setServerError(null);
    onClose();
  };

  const form = useForm({
    defaultValues: { name: "", secret: "", priority: "5" },
    validators: { onSubmit: keyCreateSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      try {
        await mutation.mutateAsync({
          name: value.name.trim(),
          secret: value.secret,
          priority: Number(value.priority),
        });
        toast.success("Đã thêm key. Secret không hiển thị lại được.");
        handleClose();
      } catch (error) {
        setServerError(
          error instanceof ApiProblemError
            ? error.message
            : "Không thêm được key. Vui lòng thử lại.",
        );
      }
    },
  });

  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogShell
        title="Thêm key"
        description="Secret được gửi một lần tới backendV1 và mã hóa trong DB ModelOps. Sau khi lưu, chỉ còn masked_hint."
        icon={<KeyRound className="size-4" />}
        onSubmit={(event) => {
          event.preventDefault();
          event.stopPropagation();
          void form.handleSubmit();
        }}
        footer={
          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              disabled={mutation.isPending}
              onClick={handleClose}
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
                  disabled={!canSubmit || formSubmitting || mutation.isPending}
                >
                  {mutation.isPending ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" />
                      <span>Đang lưu...</span>
                    </>
                  ) : (
                    <>
                      <KeyRound className="size-3.5" />
                      <span>Thêm key</span>
                    </>
                  )}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        }
      >
        <div className="grid gap-4">
          {serverError ? (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              {serverError}
            </p>
          ) : null}
          <form.Field name="name">
            {(field) => {
              const error = fieldError(field.state.meta.errors);
              return (
                <Field>
                  <FieldLabel htmlFor="key-name">Tên key</FieldLabel>
                  <Input
                    id="key-name"
                    className="text-xs"
                    placeholder="key-chat-01"
                    value={field.state.value}
                    disabled={mutation.isPending}
                    onBlur={field.handleBlur}
                    onChange={(event) => field.handleChange(event.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>
          <form.Field name="secret">
            {(field) => {
              const error = fieldError(field.state.meta.errors);
              return (
                <Field>
                  <FieldLabel htmlFor="key-secret">Secret</FieldLabel>
                  <SecretField
                    id="key-secret"
                    value={field.state.value}
                    onChange={field.handleChange}
                    disabled={mutation.isPending}
                  />
                  <FieldDescription className="text-[11px]">
                    Không dán secret vào .env, không gửi qua chat hay báo cáo.
                    Giá trị này không được lưu ở trình duyệt.
                  </FieldDescription>
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>
          <form.Field name="priority">
            {(field) => {
              const error = fieldError(field.state.meta.errors);
              return (
                <Field>
                  <FieldLabel htmlFor="key-priority">Priority</FieldLabel>
                  <Input
                    id="key-priority"
                    inputMode="numeric"
                    className="text-xs sm:max-w-[140px]"
                    value={field.state.value}
                    disabled={mutation.isPending}
                    onBlur={field.handleBlur}
                    onChange={(event) => field.handleChange(event.target.value)}
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
        </div>
      </DialogShell>
    </ResponsiveDialog>
  );
}

export function KeyRotateDialog({
  providerId,
  providerKey,
  onClose,
}: {
  providerId: string;
  providerKey: ProviderKey;
  onClose: () => void;
}) {
  const mutation = useRotateProviderKey(providerId);
  const [serverError, setServerError] = useState<string | null>(null);

  const handleClose = () => {
    form.reset();
    mutation.reset();
    setServerError(null);
    onClose();
  };

  const form = useForm({
    defaultValues: {
      name: `${providerKey.name} (rotated)`,
      secret: "",
      priority: String(providerKey.priority),
      reason: "",
    },
    validators: { onSubmit: keyRotateSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      try {
        await mutation.mutateAsync({
          keyId: providerKey.id,
          input: {
            name: value.name.trim(),
            secret: value.secret,
            priority: Number(value.priority),
            reason: value.reason.trim() || null,
          },
        });
        toast.success("Đã xoay key. Key cũ được đánh dấu thu hồi.");
        handleClose();
      } catch (error) {
        setServerError(
          error instanceof ApiProblemError
            ? error.message
            : "Không xoay được key. Vui lòng thử lại.",
        );
      }
    },
  });

  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogShell
        title={`Xoay key "${providerKey.name}"`}
        description="Backend tạo một key thay thế và thu hồi key hiện tại trong cùng một thao tác. Secret cũ không xem lại được."
        icon={<RefreshCw className="size-4" />}
        onSubmit={(event) => {
          event.preventDefault();
          event.stopPropagation();
          void form.handleSubmit();
        }}
        footer={
          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              disabled={mutation.isPending}
              onClick={handleClose}
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
                  disabled={!canSubmit || formSubmitting || mutation.isPending}
                >
                  {mutation.isPending ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" />
                      <span>Đang xoay...</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw className="size-3.5" />
                      <span>Xoay key</span>
                    </>
                  )}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        }
      >
        <div className="grid gap-4">
          {serverError ? (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              {serverError}
            </p>
          ) : null}
          <form.Field name="name">
            {(field) => {
              const error = fieldError(field.state.meta.errors);
              return (
                <Field>
                  <FieldLabel htmlFor="rotate-key-name">Tên key mới</FieldLabel>
                  <Input
                    id="rotate-key-name"
                    className="text-xs"
                    value={field.state.value}
                    disabled={mutation.isPending}
                    onBlur={field.handleBlur}
                    onChange={(event) => field.handleChange(event.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>
          <form.Field name="secret">
            {(field) => {
              const error = fieldError(field.state.meta.errors);
              return (
                <Field>
                  <FieldLabel htmlFor="rotate-key-secret">
                    Secret mới
                  </FieldLabel>
                  <SecretField
                    id="rotate-key-secret"
                    value={field.state.value}
                    onChange={field.handleChange}
                    disabled={mutation.isPending}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>
          <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
            <form.Field name="priority">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="rotate-key-priority">
                      Priority
                    </FieldLabel>
                    <Input
                      id="rotate-key-priority"
                      inputMode="numeric"
                      className="text-xs"
                      value={field.state.value}
                      disabled={mutation.isPending}
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
            <form.Field name="reason">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="rotate-key-reason">
                      Lý do (tùy chọn)
                    </FieldLabel>
                    <Input
                      id="rotate-key-reason"
                      className="text-xs"
                      placeholder="Rò rỉ key ở môi trường staging"
                      value={field.state.value}
                      disabled={mutation.isPending}
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
          </div>
        </div>
      </DialogShell>
    </ResponsiveDialog>
  );
}

export function KeyRevokeDialog({
  providerId,
  providerKey,
  onClose,
}: {
  providerId: string;
  providerKey: ProviderKey;
  onClose: () => void;
}) {
  const mutation = useRevokeProviderKey(providerId);
  const [reason, setReason] = useState("");
  const [serverError, setServerError] = useState<string | null>(null);
  const reasonError = keyRevokeSchema.safeParse({ reason });

  const handleClose = () => {
    setReason("");
    setServerError(null);
    mutation.reset();
    onClose();
  };

  const handleRevoke = () => {
    if (mutation.isPending) return;
    setServerError(null);
    void mutation
      .mutateAsync({
        keyId: providerKey.id,
        input: { reason: reason.trim() || null },
      })
      .then(() => {
        toast.success("Đã thu hồi key.");
        handleClose();
      })
      .catch((error: unknown) =>
        setServerError(
          error instanceof ApiProblemError
            ? error.message
            : "Không thu hồi được key.",
        ),
      );
  };

  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogShell
        title={`Thu hồi key "${providerKey.name}"`}
        description="Key bị đánh dấu thu hồi và không dùng được nữa. Hành động này được ghi vào nhật ký key."
        icon={<ShieldOff className="size-4" />}
        onSubmit={(event) => {
          event.preventDefault();
          event.stopPropagation();
          handleRevoke();
        }}
        footer={
          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              disabled={mutation.isPending}
              onClick={handleClose}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              variant="destructive"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang xử lý...</span>
                </>
              ) : (
                <>
                  <ShieldOff className="size-3.5" />
                  <span>Thu hồi key</span>
                </>
              )}
            </Button>
          </ResponsiveDialogFooter>
        }
      >
        <div className="grid gap-4">
          {serverError ? (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              {serverError}
            </p>
          ) : null}
          <div className="rounded-md border bg-muted/40 px-3 py-2 text-xs">
            <p className="font-mono">{providerKey.masked_hint}</p>
            <p className="mt-1 text-muted-foreground">
              Tạo lúc {formatDateTimeValue(providerKey.created_at)}
            </p>
          </div>
          <Field>
            <FieldLabel htmlFor="revoke-key-reason">
              Lý do (tùy chọn)
            </FieldLabel>
            <Textarea
              id="revoke-key-reason"
              rows={2}
              className="text-xs"
              placeholder="Ngừng dùng nhà cung cấp này"
              value={reason}
              disabled={mutation.isPending}
              onChange={(event) => setReason(event.target.value)}
            />
            <FieldDescription className="text-[11px]">
              Lý do được lưu vào bản ghi audit của key, tối đa 512 ký tự.
            </FieldDescription>
            {!reasonError.success ? (
              <FieldError>{reasonError.error.issues[0]?.message}</FieldError>
            ) : null}
          </Field>
        </div>
      </DialogShell>
    </ResponsiveDialog>
  );
}
