import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CloudUpload, Pin, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  type BackupRecord,
  backupKeys,
  copyBackup,
  pinBackup,
  removeBackup,
} from "@/features/backups/api";

export function BackupManageActions({
  record,
  busy,
}: {
  record: BackupRecord;
  busy: boolean;
}) {
  const [confirm, setConfirm] = useState(false);
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (action: "pin" | "copy" | "delete") =>
      action === "pin"
        ? pinBackup(record.id, !record.pinned)
        : action === "copy"
          ? copyBackup(record.id)
          : removeBackup(record.id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: backupKeys });
      setConfirm(false);
      toast.success("Đã cập nhật bản sao lưu.");
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const disabled = busy || mutation.isPending;
  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={() => mutation.mutate("pin")}
        >
          <Pin className="size-3.5" />
          {record.pinned ? "Bỏ ghim" : "Ghim"}
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={disabled || !record.verified_at}
          onClick={() => mutation.mutate("copy")}
        >
          <CloudUpload className="size-3.5" />
          Chuyển S3
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={disabled || record.pinned}
          onClick={() => setConfirm(true)}
        >
          <Trash2 className="size-3.5 text-destructive" />
          Xóa
        </Button>
      </div>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Gỡ bản sao lưu?"
        description="Bản được chuyển vào thư mục phục hồi tạm, không xóa dữ liệu app. Không được xóa bản tốt cuối cùng. Thao tác này chưa giải phóng dung lượng ổ đĩa."
        isPending={mutation.isPending}
        confirmText="Gỡ bản"
        onConfirm={() => mutation.mutate("delete")}
      />
    </>
  );
}
