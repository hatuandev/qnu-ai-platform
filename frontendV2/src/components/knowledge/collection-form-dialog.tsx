import { FolderPlus, Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  useCreateCollectionMutation,
  useUpdateCollectionMutation,
} from "@/api/knowledge/queries";
import type { CollectionResponse } from "@/api/knowledge/types";
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
import { Textarea } from "@/components/ui/textarea";

export function CollectionFormDialog({
  open,
  onOpenChange,
  workspaceId,
  collection,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collection?: CollectionResponse | null;
  onSuccess?: (item: CollectionResponse) => void;
}) {
  const isEdit = Boolean(collection);
  const createMutation = useCreateCollectionMutation(workspaceId);
  const updateMutation = useUpdateCollectionMutation(
    workspaceId,
    collection?.id,
  );

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setName(collection?.name ?? "");
      setDescription(collection?.description ?? "");
      setError(null);
    }
  }, [open, collection]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Vui lòng nhập tên kho tri thức");
      return;
    }
    setError(null);

    try {
      if (isEdit && collection) {
        const res = await updateMutation.mutateAsync({
          name: name.trim(),
          description: description.trim() || null,
        });
        toast.success(`Đã cập nhật kho tri thức "${res.name}"`);
        onOpenChange(false);
        onSuccess?.(res);
      } else {
        const res = await createMutation.mutateAsync({
          name: name.trim(),
          description: description.trim() || null,
        });
        toast.success(`Đã tạo kho tri thức "${res.name}"`);
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
          <DialogHeader className="space-y-1">
            <DialogTitle className="flex items-center gap-2 text-base font-semibold text-foreground">
              <FolderPlus className="size-4.5 text-primary shrink-0" />
              <span>
                {isEdit ? "Chỉnh sửa kho tri thức" : "Tạo kho tri thức mới"}
              </span>
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              {isEdit
                ? "Cập nhật tên và mô tả phạm vi lưu trữ tài liệu của kho."
                : "Thiết lập không gian lưu trữ và bóc tách tài liệu mới."}
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="p-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive">
              {error}
            </div>
          )}

          <div className="space-y-3.5 pt-1">
            <Field>
              <FieldLabel
                required
                className="text-xs font-medium text-foreground"
              >
                Tên kho tri thức
              </FieldLabel>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="VD: Tuyển sinh 2026, Đào tạo & Khảo thí..."
                className="h-9 text-xs bg-background"
                disabled={isPending}
                autoFocus
              />
            </Field>

            <Field>
              <FieldLabel className="text-xs font-medium text-foreground">
                Mô tả mục đích
              </FieldLabel>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Mô tả phạm vi văn bản lưu trữ trong kho này (tùy chọn)..."
                className="text-xs resize-none bg-background leading-relaxed"
                rows={3}
                disabled={isPending}
              />
            </Field>
          </div>

          <DialogFooter className="gap-2 sm:gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
              className="h-8 text-xs font-medium"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isPending || !name.trim()}
              className="h-8 text-xs font-medium gap-1.5 shadow-2xs"
            >
              {isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : isEdit ? (
                <Save className="size-3.5" />
              ) : (
                <FolderPlus className="size-3.5" />
              )}
              <span>{isEdit ? "Lưu thay đổi" : "Tạo kho"}</span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
