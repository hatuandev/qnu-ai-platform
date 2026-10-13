import { useForm } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LockKeyhole } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type BackupAction,
  backupKeys,
  runBackup,
} from "@/features/backups/api";

const titles: Record<BackupAction, string> = {
  create: "Sao lưu toàn hệ thống",
  verify: "Kiểm tra bản sao lưu",
  drill: "Khôi phục thử tách biệt",
};

export function BackupActionDialog({
  action,
  backupId,
  onClose,
}: {
  action: BackupAction;
  backupId?: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (password: string) => runBackup(action, password, backupId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: backupKeys });
      toast.success("Đã bắt đầu. Bạn có thể xem tiến độ trong lịch sử.");
      onClose();
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const form = useForm({
    defaultValues: { password: "", repeat: "", confirmation: "" },
    validators: {
      onSubmit: z
        .object({
          password: z.string().min(12).max(256),
          repeat: z.string(),
          confirmation: z.literal("XÁC NHẬN"),
        })
        .refine(
          (value) => action !== "create" || value.password === value.repeat,
          { message: "Mật khẩu xác nhận không khớp.", path: ["repeat"] },
        ),
    },
    onSubmit: async ({ value }) => {
      await mutation.mutateAsync(value.password).catch(() => undefined);
    },
  });
  const field = (
    name: "password" | "repeat" | "confirmation",
    label: string,
  ) => (
    <form.Field name={name}>
      {(current) => (
        <div className="space-y-2">
          <Label htmlFor={`backup-${name}`}>{label}</Label>
          <Input
            id={`backup-${name}`}
            type={name === "confirmation" ? "text" : "password"}
            autoComplete={name === "confirmation" ? "off" : "new-password"}
            value={current.state.value}
            onBlur={current.handleBlur}
            onChange={(event) => current.handleChange(event.target.value)}
            disabled={mutation.isPending}
            aria-invalid={current.state.meta.errors.length > 0}
          />
          {current.state.meta.errors.length > 0 && (
            <p className="text-xs text-destructive">
              {name === "confirmation"
                ? "Nhập đúng XÁC NHẬN."
                : name === "repeat"
                  ? "Mật khẩu xác nhận không khớp."
                  : "Mật khẩu cần 12–256 ký tự."}
            </p>
          )}
        </div>
      )}
    </form.Field>
  );
  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open && !mutation.isPending) onClose();
      }}
    >
      <ResponsiveDialogContent className="max-w-lg p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <LockKeyhole className="size-5" />
            {titles[action]}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {action === "create"
              ? "Bao gồm mọi tenant, tài liệu và cấu hình ModelOps. API/worker sẽ tạm chờ trong lúc chụp dữ liệu."
              : action === "drill"
                ? "Chỉ phục hồi vào container mới. Không thay dữ liệu đang dùng; không bật chatbot/worker sandbox."
                : "Kiểm tra mật khẩu, mã hóa và checksum từng thành phần; không khôi phục dữ liệu."}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit();
          }}
          className="flex min-h-0 flex-col"
        >
          <div className="max-h-[55vh] space-y-4 overflow-y-auto p-5">
            {action === "create" && (
              <Alert>
                <AlertDescription>
                  Lưu mật khẩu ở nơi an toàn riêng. App không lưu mật khẩu này;
                  mất mật khẩu thì không mở được bản sao lưu. Cần khởi động lại
                  toàn bộ BE và worker với phiên bản mới trước lần sao lưu đầu
                  tiên.
                </AlertDescription>
              </Alert>
            )}
            {field(
              "password",
              action === "create"
                ? "Mật khẩu mã hóa"
                : "Mật khẩu của bản sao lưu",
            )}
            {action === "create" && field("repeat", "Nhập lại mật khẩu")}
            {field("confirmation", "Nhập XÁC NHẬN để tiếp tục")}
          </div>
          <ResponsiveDialogFooter className="border-t bg-card p-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={mutation.isPending}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Đang gửi…" : "Bắt đầu"}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
