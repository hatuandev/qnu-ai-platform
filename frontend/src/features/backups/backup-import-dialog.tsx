import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { FileUpload } from "@/components/admin/file-upload";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { backupKeys, importBackup } from "@/features/backups/api";

export function BackupImportDialog({ onClose }: { onClose: () => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => importBackup(files[0], setProgress),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: backupKeys });
      toast.success(
        "Đã nhập file. Mở chi tiết để kiểm tra mật khẩu và toàn vẹn.",
      );
      onClose();
    },
    onError: (error: Error) => toast.error(error.message),
  });
  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => {
        if (!open && !mutation.isPending) onClose();
      }}
    >
      <ResponsiveDialogContent className="max-w-lg gap-0 p-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <Upload className="size-5" />
            Nhập bản sao lưu
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Chỉ tải file mã hóa lên máy chủ. Chưa giải nén, chưa khôi phục và
            không thay dữ liệu đang dùng.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="max-h-[55vh] space-y-4 overflow-y-auto p-5">
          <FileUpload
            accept=".qnubak"
            maxFiles={1}
            maxSize={20 * 1024 ** 3}
            value={files}
            onFilesChange={setFiles}
            disabled={mutation.isPending}
            progress={mutation.isPending ? progress : undefined}
            progressLabel="Đã gửi file; máy chủ còn kiểm tra và lưu"
          />
          <p className="text-sm text-muted-foreground">
            File được ghim để tránh dọn nhầm. Sau khi nhập, cần bấm Kiểm tra rồi
            Khôi phục thử trong môi trường riêng. Không có khôi phục ghi đè.
          </p>
        </div>
        <ResponsiveDialogFooter className="border-t bg-card p-4">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={mutation.isPending}
          >
            Hủy
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!files.length || mutation.isPending}
          >
            {mutation.isPending ? "Đang nhập…" : "Nhập file"}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
