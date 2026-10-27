import { useForm } from "@tanstack/react-form";
import { useRef, useState } from "react";
import { z } from "zod";
import { v1Client } from "@/app/api/v1";
import { Field, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { createIdempotencyKey } from "@/lib/idempotency-key";
import { createBackup } from "./maintenance-requests";

export function BackupCreate({
  workspaceId,
  onCreated,
}: {
  workspaceId: string;
  onCreated: (id: string) => void;
}) {
  const current = useActionScope();
  const [key, setKey] = useState(createIdempotencyKey);
  const [hasStarted, setHasStarted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef(false);
  const form = useForm({
    defaultValues: { days: "" },
    onSubmit: async ({ value }) => {
      const parsed = z
        .number()
        .int()
        .min(1)
        .max(36500)
        .nullable()
        .safeParse(value.days.trim() === "" ? null : Number(value.days));
      if (!parsed.success) {
        setError("Nhập từ 1 đến 36500 ngày, hoặc để trống để giữ lâu dài.");
        return;
      }
      if (active.current) return;
      active.current = true;
      setBusy(true);
      setHasStarted(true);
      setError(null);
      try {
        const backup = await createBackup(
          v1Client,
          workspaceId,
          parsed.data,
          key,
        );
        if (!current()) return;
        setKey(createIdempotencyKey());
        setHasStarted(false);
        onCreated(backup.id);
      } catch (cause) {
        if (current())
          setError(
            cause instanceof Error
              ? cause.message
              : "Chưa xác định kết quả. Thử lại cùng yêu cầu.",
          );
      } finally {
        active.current = false;
        if (current()) setBusy(false);
      }
    },
  });
  return (
    <form
      className="space-y-3 rounded-lg border p-4"
      onSubmit={(e) => {
        e.preventDefault();
        void form.handleSubmit();
      }}
    >
      <h2 className="text-sm font-semibold">Tạo bản sao lưu bằng chứng</h2>
      <p className="text-sm text-muted-foreground">
        Gồm tệp gốc, kết quả OCR, Compiler và bằng chứng liên quan. Khôi phục
        toàn hệ thống vẫn thực hiện qua công cụ vận hành riêng.
      </p>
      <div className="flex flex-col sm:flex-row sm:items-end gap-3">
        <form.Field name="days">
          {(field) => (
            <Field className="sm:w-60">
              <FieldLabel htmlFor="backup-retention">
                Giữ tối thiểu (ngày)
              </FieldLabel>
              <Input
                id="backup-retention"
                type="number"
                min={1}
                max={36500}
                placeholder="Để trống: giữ lâu dài"
                value={field.state.value}
                disabled={hasStarted}
                onChange={(e) => field.handleChange(e.target.value)}
              />
            </Field>
          )}
        </form.Field>
        <Button type="submit" disabled={busy}>
          {busy
            ? "Đang tạo yêu cầu…"
            : hasStarted
              ? "Thử lại cùng yêu cầu"
              : "Tạo bản sao lưu"}
        </Button>
      </div>
      {hasStarted && !busy ? (
        <p className="text-sm text-warning">
          Giữ nguyên yêu cầu để tránh tạo trùng. Có thể kiểm tra danh sách trước
          khi thử lại.
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </form>
  );
}
