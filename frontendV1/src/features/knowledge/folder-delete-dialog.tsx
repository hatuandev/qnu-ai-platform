import { AlertTriangle, Loader2, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import {
  useDeleteFolder,
  useFolderImpactQuery,
} from "@/features/knowledge/queries";
import type { KBFolder } from "@/features/knowledge/types";

export function FolderDeleteDialog({
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
  folder: KBFolder | null;
  onSuccess?: () => void;
}) {
  const folderId = folder?.id ?? "";
  const impactQuery = useFolderImpactQuery(workspaceId, collectionId, folderId);
  const deleteMutation = useDeleteFolder(workspaceId, collectionId);

  const [serverError, setServerError] = useState<string | null>(null);

  const impact = impactQuery.data;
  const isLoadingImpact = impactQuery.isPending;

  const handleDelete = async () => {
    if (!folder) return;
    setServerError(null);
    try {
      await deleteMutation.mutateAsync(folder.id);
      toast.success(`Đã đưa thư mục "${folder.name}" vào thùng rác.`);
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setServerError(error.message);
      } else {
        setServerError("Không thể xóa thư mục. Vui lòng thử lại.");
      }
    }
  };

  const isSubmitting = deleteMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-w-md p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold text-destructive">
            <span className="flex size-8 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
              <Trash2 className="size-4" />
            </span>
            Xác nhận xóa thư mục
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Đưa thư mục <span className="font-semibold text-foreground">"{folder?.name}"</span> vào thùng rác.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <div className="grid gap-3 px-4 py-4 sm:px-6">
          {serverError ? (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              {serverError}
            </p>
          ) : null}

          {isLoadingImpact ? (
            <div className="flex items-center gap-2 py-4 text-xs text-muted-foreground">
              <Loader2 className="size-4 animate-spin text-primary" />
              <span>Đang kiểm tra phạm vi ảnh hưởng...</span>
            </div>
          ) : impact ? (
            <div className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs space-y-2">
              <div className="flex items-start gap-2 text-warning font-medium">
                <AlertTriangle className="size-4 shrink-0 mt-0.5" />
                <span>Phạm vi ảnh hưởng khi xóa:</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground pl-1">
                <li>
                  Thư mục con bị ảnh hưởng:{" "}
                  <strong className="text-foreground">{impact.subfolder_count}</strong> thư mục
                </li>
                <li>
                  Tài liệu bị ảnh hưởng:{" "}
                  <strong className="text-foreground">{impact.source_count}</strong> tài liệu
                </li>
              </ul>
              <p className="text-[11px] text-muted-foreground pt-1 border-t border-warning/20">
                Toàn bộ thư mục con và tài liệu bên trong sẽ được đưa vào thùng rác theo chính sách vòng đời.
              </p>
            </div>
          ) : null}
        </div>

        <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isSubmitting}
            onClick={() => onOpenChange(false)}
          >
            Hủy
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            disabled={isSubmitting || isLoadingImpact}
            className="gap-1.5"
            onClick={handleDelete}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                <span>Đang xóa...</span>
              </>
            ) : (
              <>
                <Trash2 className="size-3.5" />
                <span>Xác nhận xóa</span>
              </>
            )}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

