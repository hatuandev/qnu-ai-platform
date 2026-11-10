import { Loader2, Pencil } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useRenameSourceMutation } from "@/api/knowledge/queries";
import type { SourceResponse } from "@/api/knowledge/types";
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

export function SourceRenameDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  source,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  source: SourceResponse | null;
  onSuccess?: () => void;
}) {
  const renameMutation = useRenameSourceMutation(workspaceId, collectionId);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && source) {
      setTitle(source.title);
      setError(null);
    }
  }, [open, source]);

  if (!source) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Vui lòng nhập tiêu đề tài liệu");
      return;
    }

    try {
      await renameMutation.mutateAsync({
        sourceId: source.id,
        data: { title: title.trim() },
      });
      toast.success("Đã cập nhật tiêu đề tài liệu.");
      onOpenChange(false);
      onSuccess?.();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Có lỗi xảy ra khi đổi tên";
      setError(msg);
      toast.error(msg);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Pencil className="size-4 text-primary" />
              <span>Đổi tiêu đề tài liệu</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Tên hiển thị nhận diện tài liệu trong kho và trích dẫn.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="p-2.5 rounded-md bg-destructive/10 border border-destructive/20 text-xs text-destructive">
              {error}
            </div>
          )}

          <Field>
            <FieldLabel required>Tiêu đề tài liệu</FieldLabel>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="h-8 text-xs"
              disabled={renameMutation.isPending}
              autoFocus
            />
          </Field>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={renameMutation.isPending}
              className="h-8 text-xs"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={renameMutation.isPending}
              className="h-8 text-xs gap-1.5"
            >
              {renameMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Pencil className="size-3.5" />
              )}
              <span>Lưu</span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
