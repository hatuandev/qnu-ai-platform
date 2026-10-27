import { useForm } from "@tanstack/react-form";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { z } from "zod";
import { ApiProblemError, v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Field, FieldError, FieldLabel } from "@/components/admin/field";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTimeValue } from "@/lib/date-utils";
import { LifecycleReceiptView } from "./action-receipt";
import { useActionScope } from "./action-scope";
import { ImpactView } from "./impact-view";
import { useLifecycleAction } from "./queries";
import { acceptLifecycle, previewLifecycle } from "./requests";
import {
  ACTION_LABEL,
  type LifecycleAction,
  type LifecycleTarget,
} from "./types";

export function LifecycleActionDialog({
  workspaceId,
  target,
  label,
  onClose,
}: {
  workspaceId: string;
  target: LifecycleTarget;
  label: string;
  onClose: () => void;
}) {
  const { sessionId } = useV1Auth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const current = useActionScope();
  const [preview, setPreview] = useState<LifecycleAction | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submitting = useRef(false);
  const [acceptStarted, setAcceptStarted] = useState(false);
  const detail = useLifecycleAction(workspaceId, preview?.id);
  const live = detail.data ?? preview;
  const navigated = useRef(false);
  useEffect(() => {
    if (
      live?.status !== "completed" ||
      navigated.current ||
      !["archive", "delete", "restore"].includes(live.action)
    )
      return;
    navigated.current = true;
    void navigate({
      to: "/workspaces/$workspaceId/resources",
      params: { workspaceId },
      search: { page: 1, actionId: live.id },
    });
  }, [live, navigate, workspaceId]);
  const form = useForm({
    defaultValues: { reason: "" },
    validators: {
      onSubmit: z.object({
        reason: z.string().trim().min(1, "Nhập lý do thao tác.").max(2000),
      }),
    },
    onSubmit: async ({ value }) => {
      if (submitting.current) return;
      submitting.current = true;
      setBusy(true);
      setError(null);
      try {
        const result = await previewLifecycle(v1Client, workspaceId, {
          ...target,
          reason: value.reason.trim(),
        });
        if (!current()) return;
        setPreview(result);
        setConfirmed(false);
        queryClient.setQueryData(
          ["v1", sessionId, "lifecycle-action", workspaceId, result.id],
          result,
        );
      } catch (cause) {
        if (current())
          setError(
            cause instanceof Error
              ? cause.message
              : "Không xem trước được thao tác.",
          );
      } finally {
        submitting.current = false;
        if (current()) setBusy(false);
      }
    },
  });
  const accept = async () => {
    if (
      !preview ||
      !confirmed ||
      submitting.current ||
      (live?.status !== "preview" && live?.status !== "pending")
    )
      return;
    if (!acceptStarted && Date.parse(preview.expires_at) <= Date.now()) {
      setError("Bản xem trước đã hết hạn. Hãy xem trước lại.");
      setPreview(null);
      setConfirmed(false);
      return;
    }
    submitting.current = true;
    setBusy(true);
    setError(null);
    setAcceptStarted(true);
    try {
      const result = await acceptLifecycle(v1Client, workspaceId, preview);
      if (!current()) return;
      await queryClient.cancelQueries({
        queryKey: ["v1", sessionId, "lifecycle-action", workspaceId, result.id],
      });
      if (!current()) return;
      setPreview(result);
      queryClient.setQueryData(
        ["v1", sessionId, "lifecycle-action", workspaceId, result.id],
        result,
      );
      void queryClient.invalidateQueries({ queryKey: ["v1", sessionId] });
    } catch (cause) {
      if (!current()) return;
      setError(
        cause instanceof Error
          ? cause.message
          : "Chưa xác định được kết quả. Kiểm tra biên nhận hoặc thử lại cùng thao tác.",
      );
      if (
        cause instanceof ApiProblemError &&
        cause.code === "lifecycle_preview_stale"
      ) {
        setPreview(null);
        setConfirmed(false);
        setAcceptStarted(false);
      } else void detail.refetch();
    } finally {
      submitting.current = false;
      if (current()) setBusy(false);
    }
  };
  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <ResponsiveDialogContent className="max-w-xl p-0 gap-0 flex flex-col max-h-[min(820px,calc(100vh-2rem))]">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle>
            {ACTION_LABEL[target.action]}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {label}. Xem phạm vi ảnh hưởng trước khi xác nhận.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto space-y-4 px-4 py-4 sm:px-6">
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          {!preview ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void form.handleSubmit();
              }}
            >
              <form.Field name="reason">
                {(field) => (
                  <Field>
                    <FieldLabel htmlFor="lifecycle-reason">Lý do</FieldLabel>
                    <Textarea
                      id="lifecycle-reason"
                      value={field.state.value}
                      maxLength={2000}
                      disabled={busy}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                    />
                    {field.state.meta.errors.map((err) => (
                      <FieldError key={err?.message}>{err?.message}</FieldError>
                    ))}
                  </Field>
                )}
              </form.Field>
              <Button type="submit" className="mt-3" disabled={busy}>
                {busy ? "Đang đọc tác động…" : "Xem trước tác động"}
              </Button>
            </form>
          ) : (
            <>
              <p className="text-sm">Lý do: {preview.reason}</p>
              <ImpactView impact={preview.impact} />
              <p className="text-xs text-muted-foreground">
                Hạn xác nhận: {formatDateTimeValue(preview.expires_at)}
              </p>
              {live ? (
                <LifecycleReceiptView workspaceId={workspaceId} action={live} />
              ) : null}
              {detail.isError ? (
                <p role="alert" className="text-sm text-destructive">
                  Không đọc được biên nhận. {detail.error.message}
                </p>
              ) : null}
              {live?.status === "preview" || live?.status === "pending" ? (
                <div className="flex items-start gap-2">
                  <Checkbox
                    id="lifecycle-confirm"
                    checked={confirmed}
                    onCheckedChange={(checked) =>
                      setConfirmed(checked === true)
                    }
                    disabled={busy || acceptStarted}
                  />
                  <Label
                    htmlFor="lifecycle-confirm"
                    className="text-sm leading-relaxed"
                  >
                    Tôi đã xem và đồng ý phạm vi ảnh hưởng trên.
                  </Label>
                </div>
              ) : null}
            </>
          )}
        </div>
        <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6">
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Đóng
          </Button>
          {preview && !acceptStarted ? (
            <Button
              variant="ghost"
              onClick={() => {
                setPreview(null);
                setConfirmed(false);
                setError(null);
              }}
              disabled={busy}
            >
              Xem trước lại
            </Button>
          ) : null}
          {preview && ["preview", "pending"].includes(live?.status ?? "") ? (
            <Button
              variant={target.action === "delete" ? "destructive" : "default"}
              onClick={() => void accept()}
              disabled={busy || !confirmed}
            >
              {busy
                ? "Đang xác nhận…"
                : acceptStarted
                  ? "Thử lại cùng thao tác"
                  : "Xác nhận thao tác"}
            </Button>
          ) : null}
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
