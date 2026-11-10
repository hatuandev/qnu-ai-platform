import { FolderInput, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  useFoldersQuery,
  useMoveFolderMutation,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function FolderMoveDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  folder,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  folder: FolderResponse | null;
  onSuccess?: () => void;
}) {
  const { data: allFolders = [] } = useFoldersQuery(workspaceId, collectionId);
  const moveMutation = useMoveFolderMutation(workspaceId, collectionId);

  const [targetParentId, setTargetParentId] = useState<string>("root");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && folder) {
      setTargetParentId(folder.parent_id || "root");
      setError(null);
    }
  }, [open, folder]);

  if (!folder) return null;

  // Filter out the folder itself to avoid self-nesting
  const availableParents = allFolders.filter((f) => f.id !== folder.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newParentId = targetParentId === "root" ? null : targetParentId;
    if (newParentId === folder.parent_id) {
      onOpenChange(false);
      return;
    }

    try {
      await moveMutation.mutateAsync({
        folderId: folder.id,
        data: { target_parent_id: newParentId },
      });
      toast.success(`Đã di chuyển thư mục "${folder.name}"`);
      onOpenChange(false);
      onSuccess?.();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Có lỗi xảy ra khi di chuyển";
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
              <FolderInput className="size-4 text-primary" />
              <span>Di chuyển thư mục</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Chọn vị trí thư mục cha mới cho <strong>{folder.name}</strong>.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="p-2.5 rounded-md bg-destructive/10 border border-destructive/20 text-xs text-destructive">
              {error}
            </div>
          )}

          <Field>
            <FieldLabel>Thư mục cha đích</FieldLabel>
            <Select
              value={targetParentId}
              onValueChange={setTargetParentId}
              disabled={moveMutation.isPending}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Chọn thư mục cha..." />
              </SelectTrigger>
              <SelectContent className="text-xs">
                <SelectItem value="root">
                  Gốc kho tri thức (Cấp cao nhất)
                </SelectItem>
                {availableParents.map((f) => (
                  <SelectItem key={f.id} value={f.id}>
                    {f.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={moveMutation.isPending}
              className="h-8 text-xs"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={moveMutation.isPending}
              className="h-8 text-xs gap-1.5"
            >
              {moveMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <FolderInput className="size-3.5" />
              )}
              <span>Di chuyển</span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
