import { useForm } from "@tanstack/react-form";
import { useQueryClient } from "@tanstack/react-query";
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

type LifecycleActionDialogProps = {
  workspaceId: string;
  target: LifecycleTarget;
  label: string;
  onClose: () => void;
  onCompleted?: (action: LifecycleAction) => void;
  initialAction?: LifecycleAction;
};

export function LifecycleActionDialog(props: LifecycleActionDialogProps) {
  const { sessionId } = useV1Auth();
  return (
    <LifecycleActionForm
      key={JSON.stringify([
        sessionId,
        props.workspaceId,
        props.target.kind,
        props.target.resource_id,
        props.target.action,
        props.target.job_kind,
        props.target.replacement_version_id,
      ])}
      {...props}
    />
  );
}

function LifecycleActionForm({
  workspaceId,
  target,
  label,
  onClose,
  onCompleted,
  initialAction,
}: LifecycleActionDialogProps) {
  const confirmationOnly =
    target.action === "delete" &&
    ["collection", "source", "document"].includes(target.kind);
  const permanent = target.kind === "source" && target.action === "delete";
  const automaticPreviewRequested = useRef(false);
  const { sessionId } = useV1Auth();
  const queryClient = useQueryClient();
  const current = useActionScope();
  const [preview, setPreview] = useState<LifecycleAction | null>(
    initialAction ?? null,
  );
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submitting = useRef(false);
  const [acceptStarted, setAcceptStarted] = useState(
    Boolean(initialAction?.accepted_at),
  );
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
    if (onCompleted) onCompleted(live);
    else onClose();
  }, [live, onCompleted, onClose]);
  const form = useForm({
    defaultValues: {
      reason: confirmationOnly
        ? permanent
          ? "Yêu cầu xóa vĩnh viễn tài liệu từ kho tri thức."
          : "Yêu cầu đưa vào thùng rác từ giao diện."
        : "",
    },
    validators: {
      onSubmit: z.object({
        reason: z.string().trim().min(1, "Nhập lý do thao tác.").max(2000),
      }),
    },
    onSubmit: async ({ value }) => {
      if (!current() || submitting.current) return;
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
  useEffect(() => {
    if (!confirmationOnly || initialAction || automaticPreviewRequested.current)
      return;
    automaticPreviewRequested.current = true;
    void form.handleSubmit();
  }, [confirmationOnly, initialAction, form.handleSubmit]);

  const accept = async () => {
    if (
      !current() ||
      !preview ||
      (!confirmationOnly && !confirmed) ||
      submitting.current ||
      (live?.status !== "preview" && live?.status !== "pending")
    )
      return;
    if (!acceptStarted && Date.parse(preview.expires_at) <= Date.now()) {
      setError(
        confirmationOnly
          ? "Thông tin xác nhận đã hết hạn. Vui lòng thử lại."
          : "Bản xem trước đã hết hạn. Hãy xem trước lại.",
      );
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
            {confirmationOnly ? "Xác nhận xóa" : ACTION_LABEL[target.action]}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {confirmationOnly ? (
              <>Bạn có muốn xóa “{label}” không?</>
            ) : (
              <>{label}. Xem phạm vi ảnh hưởng trước khi xác nhận.</>
            )}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto space-y-4 px-4 py-4 sm:px-6">
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          {confirmationOnly ? (
            <div className="space-y-3 text-sm">
              <p>
                {permanent
                  ? "Xóa vĩnh viễn tệp gốc, các phiên bản và dữ liệu xử lý liên quan. Không thể khôi phục từ QNU."
                  : "Mục này sẽ được đưa vào thùng rác và có thể khôi phục."}
              </p>
              {permanent &&
              preview &&
              Number(preview.impact.compiled_versions_to_delete) > 0 ? (
                <p>
                  Các bản biên soạn phụ thuộc sẽ bị xóa. Những tệp nguồn khác
                  vẫn được giữ.
                </p>
              ) : null}
              {permanent ? (
                <p className="text-muted-foreground">
                  Bản sao lưu đã tạo được quản lý theo chính sách sao lưu riêng.
                </p>
              ) : null}
              {!preview && !error ? (
                <p role="status" className="text-muted-foreground">
                  Đang chuẩn bị xác nhận…
                </p>
              ) : null}
              {preview &&
              typeof preview.impact.jobs_to_cancel === "number" &&
              preview.impact.jobs_to_cancel > 0 ? (
                <p>Các tác vụ liên quan sẽ được dừng.</p>
              ) : null}
              {preview &&
              typeof preview.impact.published_versions_affected === "number" &&
              preview.impact.published_versions_affected > 0 ? (
                <p>Nội dung xuất bản liên quan sẽ ngừng phục vụ.</p>
              ) : null}
              {live &&
              ["pending", "completed", "failed"].includes(live.status) ? (
                permanent ? (
                  <p role="status">
                    {live.status === "completed"
                      ? "Đã xóa vĩnh viễn tài liệu."
                      : live.error_code
                        ? "Xóa chưa hoàn tất. Bạn có thể tiếp tục cùng thao tác."
                        : "Đã nhận yêu cầu xóa. Đang chờ dừng tác vụ và dọn dữ liệu liên quan."}
                  </p>
                ) : (
                  <LifecycleReceiptView
                    workspaceId={workspaceId}
                    action={live}
                  />
                )
              ) : null}
              {detail.isError ? (
                <p role="alert" className="text-destructive">
                  Không đọc được kết quả thao tác. {detail.error.message}
                </p>
              ) : null}
            </div>
          ) : !preview ? (
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
            {confirmationOnly && !acceptStarted ? "Hủy" : "Đóng"}
          </Button>
          {confirmationOnly && !preview && error ? (
            <Button
              variant="outline"
              onClick={() => void form.handleSubmit()}
              disabled={busy}
            >
              Thử lại
            </Button>
          ) : null}
          {preview && !acceptStarted && !confirmationOnly ? (
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
          {(preview && ["preview", "pending"].includes(live?.status ?? "")) ||
          (confirmationOnly && !preview) ? (
            <Button
              variant={target.action === "delete" ? "destructive" : "default"}
              onClick={() => void accept()}
              disabled={busy || !preview || (!confirmationOnly && !confirmed)}
            >
              {busy
                ? "Đang xác nhận…"
                : acceptStarted
                  ? "Thử lại cùng thao tác"
                  : confirmationOnly
                    ? permanent
                      ? "Xóa vĩnh viễn"
                      : "Xóa"
                    : "Xác nhận thao tác"}
            </Button>
          ) : null}
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
