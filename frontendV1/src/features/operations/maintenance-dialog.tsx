import { useForm } from "@tanstack/react-form";
import { useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import { z } from "zod";
import { ApiProblemError, v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Field, FieldLabel } from "@/components/admin/field";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { CleanupInventory } from "./cleanup-inventory";
import {
  acceptCleanup,
  previewBackupDeletion,
  previewCleanup,
} from "./maintenance-requests";
import type { CleanupAction } from "./maintenance-types";
import { acceptRecovery } from "./requests";
import type { OperationAction } from "./types";

type Props = {
  workspaceId: string;
  backupId?: string;
  onClose: () => void;
  onReceipt: (id: string) => void;
};
export function MaintenanceDialog({
  workspaceId,
  backupId,
  onClose,
  onReceipt,
}: Props) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const current = useActionScope();
  const [preview, setPreview] = useState<
    CleanupAction | OperationAction | null
  >(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const active = useRef(false);
  const form = useForm({
    defaultValues: { reason: "", age: "24" },
    onSubmit: async ({ value }) => {
      const parsed = z
        .object({
          reason: z.string().trim().min(1).max(2000),
          age: z.coerce.number().int().min(24).max(8760),
        })
        .safeParse(value);
      if (!parsed.success) {
        setError("Nhập lý do và tuổi tệp từ 24 đến 8760 giờ.");
        return;
      }
      if (active.current || preview) return;
      active.current = true;
      setBusy(true);
      setError(null);
      try {
        const result = backupId
          ? await previewBackupDeletion(
              v1Client,
              workspaceId,
              backupId,
              parsed.data.reason,
            )
          : await previewCleanup(
              v1Client,
              workspaceId,
              parsed.data.reason,
              parsed.data.age,
            );
        if (current()) {
          setPreview(result);
          setConfirmed(false);
        }
      } catch (cause) {
        if (current())
          setError(
            cause instanceof Error
              ? cause.message
              : "Không đọc được bản xem trước.",
          );
      } finally {
        active.current = false;
        if (current()) setBusy(false);
      }
    },
  });
  const accept = async () => {
    if (!preview || !confirmed || active.current || !current()) return;
    if (!hasSubmitted && Date.parse(preview.expires_at) <= Date.now()) {
      setError("Bản xem trước đã hết hạn. Hãy xem trước lại.");
      return;
    }
    active.current = true;
    setBusy(true);
    setError(null);
    setHasSubmitted(true);
    // Pin a durable URL before external deletion, including an ambiguous network result.
    onReceipt(preview.id);
    try {
      const result = backupId
        ? await acceptRecovery(v1Client, workspaceId, preview)
        : await acceptCleanup(v1Client, workspaceId, preview);
      if (!current()) return;
      await client.cancelQueries({
        queryKey: [
          "v1",
          sessionId,
          backupId ? "operations-action" : "storage-cleanup",
          workspaceId,
          result.id,
        ],
      });
      if (!current()) return;
      client.setQueryData(
        [
          "v1",
          sessionId,
          backupId ? "operations-action" : "storage-cleanup",
          workspaceId,
          result.id,
        ],
        result,
      );
      void client.invalidateQueries({
        queryKey: ["v1", sessionId, "backups", workspaceId],
      });
      void client.invalidateQueries({
        queryKey: ["v1", sessionId, "retention", workspaceId],
      });
      onClose();
    } catch (cause) {
      if (!current()) return;
      setError(
        cause instanceof Error
          ? cause.message
          : "Chưa xác định kết quả. Thử lại cùng thao tác.",
      );
      if (
        cause instanceof ApiProblemError &&
        [
          "operation_preview_stale",
          "storage_cleanup_stale",
          "backup_retention_protected",
        ].includes(cause.code)
      ) {
        setPreview(null);
        setConfirmed(false);
        setHasSubmitted(false);
      }
    } finally {
      active.current = false;
      if (current()) setBusy(false);
    }
  };
  const expired =
    preview && !hasSubmitted
      ? Date.parse(preview.expires_at) <= Date.now()
      : false;
  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <ResponsiveDialogContent className="p-0 gap-0 flex flex-col max-h-[min(820px,calc(100vh-2rem))]">
        <ResponsiveDialogHeader className="p-4 border-b bg-muted/20">
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <Trash2 className="size-4" />
            {backupId ? "Xóa bản sao lưu hết hạn" : "Dọn tệp dẫn xuất"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Đọc phạm vi trước khi xác nhận. Server kiểm tra lại điều kiện ngay
            lúc xử lý.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="p-4 min-h-0 flex-1 overflow-y-auto space-y-4">
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          {!preview ? (
            <form
              id="maintenance-preview"
              onSubmit={(e) => {
                e.preventDefault();
                void form.handleSubmit();
              }}
              className="space-y-4"
            >
              <form.Field name="reason">
                {(field) => (
                  <Field>
                    <FieldLabel htmlFor="maintenance-reason">Lý do</FieldLabel>
                    <Textarea
                      id="maintenance-reason"
                      maxLength={2000}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      disabled={busy}
                    />
                  </Field>
                )}
              </form.Field>
              {!backupId ? (
                <form.Field name="age">
                  {(field) => (
                    <Field>
                      <FieldLabel htmlFor="maintenance-age">
                        Tuổi tệp tối thiểu (giờ)
                      </FieldLabel>
                      <Input
                        id="maintenance-age"
                        type="number"
                        min={24}
                        max={8760}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        disabled={busy}
                      />
                    </Field>
                  )}
                </form.Field>
              ) : (
                <p className="text-sm break-all">
                  Bản sao lưu: {backupId}. Chỉ xóa khi hết thời hạn giữ.
                </p>
              )}
            </form>
          ) : (
            <>
              {"files" in preview ? (
                <CleanupInventory action={preview} />
              ) : (
                <div className="space-y-2 text-sm">
                  <p className="break-all">Xóa bản sao lưu: {preview.job_id}</p>
                  <p>Lý do: {preview.reason}</p>
                  <p>
                    Chỉ xóa gói sao lưu này; dữ liệu nguồn trong workspace được
                    giữ lại.
                  </p>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Bản xem trước hết hạn:{" "}
                {new Date(preview.expires_at).toLocaleString("vi-VN")}
              </p>
              {expired ? (
                <p role="alert">Bản xem trước đã hết hạn. Hãy xem trước lại.</p>
              ) : null}
              <div className="flex items-start gap-2">
                <Checkbox
                  id="maintenance-confirm"
                  checked={confirmed}
                  onCheckedChange={(v) => setConfirmed(v === true)}
                  disabled={busy || hasSubmitted}
                />
                <Label
                  htmlFor="maintenance-confirm"
                  className="text-sm leading-relaxed"
                >
                  Tôi đã đọc phạm vi và đồng ý xóa các tệp nêu trên.
                </Label>
              </div>
            </>
          )}
        </div>
        <ResponsiveDialogFooter className="p-4 border-t bg-card grid grid-cols-2 sm:flex sm:justify-end gap-2">
          <Button variant="outline" disabled={busy} onClick={onClose}>
            Đóng
          </Button>
          {preview ? (
            <>
              <Button
                variant="outline"
                disabled={busy || hasSubmitted}
                onClick={() => {
                  setPreview(null);
                  setConfirmed(false);
                }}
              >
                Xem trước lại
              </Button>
              <Button
                variant="destructive"
                disabled={
                  busy ||
                  !confirmed ||
                  expired ||
                  ("files" in preview && preview.files.length === 0)
                }
                onClick={() => void accept()}
              >
                {busy
                  ? "Đang xử lý…"
                  : hasSubmitted
                    ? "Thử lại cùng thao tác"
                    : "Xác nhận xóa"}
              </Button>
            </>
          ) : (
            <Button form="maintenance-preview" type="submit" disabled={busy}>
              {busy ? "Đang xem trước…" : "Xem trước"}
            </Button>
          )}
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
