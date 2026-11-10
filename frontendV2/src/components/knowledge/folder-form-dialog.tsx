import { FolderPlus, Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  useCreateFolderMutation,
  useUpdateFolderMutation,
} from "@/api/knowledge/queries";
import type { FolderResponse } from "@/api/knowledge/types";
import { Field, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export function FolderFormDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  parentFolderId,
  folder,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  parentFolderId?: string | null;
  folder?: FolderResponse | null;
  onSuccess?: (folder: FolderResponse) => void;
}) {
  const isEdit = Boolean(folder);
  const createMutation = useCreateFolderMutation(workspaceId, collectionId);
  const updateMutation = useUpdateFolderMutation(workspaceId, collectionId);

  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setName(folder?.name ?? "");
      setError(null);
    }
  }, [open, folder]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Vui lòng nhập tên thư mục");
      return;
    }
    setError(null);

    try {
      if (isEdit && folder) {
        const res = await updateMutation.mutateAsync({
          folderId: folder.id,
          data: { name: name.trim() },
        });
        toast.success(`Đã đổi tên thư mục thành "${res.name}"`);
        onOpenChange(false);
        onSuccess?.(res);
      } else {
        const res = await createMutation.mutateAsync({
          name: name.trim(),
          parent_id: parentFolderId || null,
        });
        toast.success(`Đã tạo thư mục "${res.name}"`);
        onOpenChange(false);
        onSuccess?.(res);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Có lỗi xảy ra";
      setError(msg);
      toast.error(msg);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <FolderPlus className="size-4 text-primary" />
              <span>{isEdit ? "Đổi tên thư mục" : "Tạo thư mục mới"}</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Thư mục dùng để phân loại tài liệu theo năm hoặc chủ đề.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="p-2.5 rounded-md bg-destructive/10 border border-destructive/20 text-xs text-destructive">
              {error}
            </div>
          )}

          <Field>
            <FieldLabel required>Tên thư mục</FieldLabel>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="VD: Năm 2026, Biểu mẫu, Quy chế..."
              className="h-8 text-xs"
              disabled={isPending}
              autoFocus
            />
          </Field>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
              className="h-8 text-xs"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isPending}
              className="h-8 text-xs gap-1.5"
            >
              {isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Save className="size-3.5" />
              )}
              <span>{isEdit ? "Lưu" : "Tạo thư mục"}</span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
