import { useForm } from "@tanstack/react-form";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useRef, useState } from "react";
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
import { useActionScope } from "@/features/lifecycle/action-scope";
import { useOperationAction } from "./queries";
import { acceptRecovery, previewRecovery } from "./requests";
import {
  JOB_LABEL,
  type JobView,
  type OperationAction,
  statusLabel,
} from "./types";

export function RecoveryDialog({
  workspaceId,
  job,
  onClose,
}: {
  workspaceId: string;
  job: JobView;
  onClose: () => void;
}) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const current = useActionScope();
  const [preview, setPreview] = useState<OperationAction | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef(false);
  const detail = useOperationAction(workspaceId, preview?.id);
  const live = detail.data ?? preview;
  const form = useForm({
    defaultValues: { reason: "" },
    validators: {
      onSubmit: z.object({
        reason: z.string().trim().min(1, "Nhập lý do giao lại.").max(2000),
      }),
    },
    onSubmit: async ({ value }) => {
      if (active.current) return;
      active.current = true;
      setBusy(true);
      setError(null);
      try {
        const result = await previewRecovery(
          v1Client,
          workspaceId,
          job.kind,
          job.id,
          value.reason.trim(),
        );
        if (current()) {
          setPreview(result);
          setConfirmed(false);
          client.setQueryData(
            ["v1", sessionId, "operations-action", workspaceId, result.id],
            result,
          );
        }
      } catch (cause) {
        if (current())
          setError(
            cause instanceof Error
              ? cause.message
              : "Không xem trước được việc giao lại.",
          );
      } finally {
        active.current = false;
        if (current()) setBusy(false);
      }
    },
  });
  const accept = async () => {
    if (
      !preview ||
      !confirmed ||
      active.current ||
      !["preview", "pending"].includes(live?.status ?? "")
    )
      return;
    active.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await acceptRecovery(v1Client, workspaceId, preview);
      if (!current()) return;
      await client.cancelQueries({
        queryKey: [
          "v1",
          sessionId,
          "operations-action",
          workspaceId,
          result.id,
        ],
      });
      if (!current()) return;
      setPreview(result);
      client.setQueryData(
        ["v1", sessionId, "operations-action", workspaceId, result.id],
        result,
      );
      void client.invalidateQueries({
        queryKey: ["v1", sessionId, "operations-jobs", workspaceId],
      });
    } catch (cause) {
      if (!current()) return;
      setError(
        cause instanceof Error
          ? cause.message
          : "Chưa xác định được kết quả; dùng lại cùng thao tác.",
      );
      if (
        cause instanceof ApiProblemError &&
        cause.code === "operation_preview_stale"
      ) {
        setPreview(null);
        setConfirmed(false);
      } else void detail.refetch();
    } finally {
      active.current = false;
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
      <ResponsiveDialogContent className="max-w-lg p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4">
          <ResponsiveDialogTitle>Giao lại tác vụ</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {JOB_LABEL[job.kind]} · {job.id}. Chỉ server quyết định tác vụ có
            thể giao lại.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="space-y-3 px-4 py-4 max-h-[60vh] overflow-y-auto">
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
                    <FieldLabel htmlFor="recovery-reason">Lý do</FieldLabel>
                    <Textarea
                      id="recovery-reason"
                      value={field.state.value}
                      maxLength={2000}
                      disabled={busy}
                      onChange={(e) => field.handleChange(e.target.value)}
                    />
                    {field.state.meta.errors.map((err) => (
                      <FieldError key={err?.message}>{err?.message}</FieldError>
                    ))}
                  </Field>
                )}
              </form.Field>
              <Button type="submit" className="mt-3" disabled={busy}>
                Xem trước giao lại
              </Button>
            </form>
          ) : (
            <>
              <p className="text-sm">Lý do: {preview.reason}</p>
              <p className="text-sm">
                Trạng thái: {statusLabel(live?.status ?? "preview")}
              </p>
              <p className="text-xs text-muted-foreground">
                Giao lại giữ ID và checkpoint của tác vụ. Không tự gửi lại lượt
                model có kết quả chưa rõ.
              </p>
              <Button asChild size="sm" variant="outline">
                <Link
                  to="/workspaces/$workspaceId/operations"
                  params={{ workspaceId }}
                  search={{
                    page: 1,
                    pageSize: 20,
                    operationActionId: preview.id,
                  }}
                >
                  Liên kết biên nhận
                </Link>
              </Button>
              {detail.isError ? (
                <p role="alert">
                  Không đọc được biên nhận: {detail.error.message}
                </p>
              ) : null}
              {live?.status === "preview" ? (
                <div className="flex gap-2">
                  <Checkbox
                    id="recovery-confirm"
                    checked={confirmed}
                    onCheckedChange={(value) => setConfirmed(value === true)}
                  />
                  <Label htmlFor="recovery-confirm">
                    Tôi đồng ý giao lại tác vụ theo bản xem trước này.
                  </Label>
                </div>
              ) : null}
            </>
          )}
        </div>
        <ResponsiveDialogFooter className="border-t bg-card px-4 py-3">
          <Button variant="outline" disabled={busy} onClick={onClose}>
            Đóng
          </Button>
          {preview && ["preview", "pending"].includes(live?.status ?? "") ? (
            <Button disabled={!confirmed || busy} onClick={() => void accept()}>
              {busy
                ? "Đang xác nhận…"
                : live?.status === "pending"
                  ? "Thử giao lại cùng thao tác"
                  : "Xác nhận giao lại"}
            </Button>
          ) : null}
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
