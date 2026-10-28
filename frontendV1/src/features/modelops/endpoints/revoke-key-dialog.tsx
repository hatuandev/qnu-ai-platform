import { AlertTriangle, Trash2 } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
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
import { Label } from "@/components/ui/label";
import { useRevokeAppApiKeyMutation } from "@/features/modelops/queries";
import type { AppApiKey } from "@/features/modelops/types";

interface RevokeKeyDialogProps {
  keyItem: AppApiKey | null;
  workspaceId: string;
  onClose: () => void;
}

export function RevokeKeyDialog({
  keyItem,
  workspaceId,
  onClose,
}: RevokeKeyDialogProps) {
  const [reason, setReason] = React.useState("Thu hồi bởi quản trị viên");
  const revokeMutation = useRevokeAppApiKeyMutation(workspaceId);

  React.useEffect(() => {
    if (keyItem) {
      setReason("Thu hồi bởi quản trị viên");
    }
  }, [keyItem]);

  if (!keyItem) return null;

  const handleRevoke = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await revokeMutation.mutateAsync({
        keyId: keyItem.id,
        input: { reason: reason.trim() || "Thu hồi bởi quản trị viên" },
      });
      toast.success(`Đã thu hồi khóa "${keyItem.name}".`);
      onClose();
    } catch (err: unknown) {
      toast.error((err as Error)?.message || "Không thể thu hồi khóa.");
    }
  };

  return (
    <Dialog open={Boolean(keyItem)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md" role="alertdialog">
        <DialogHeader>
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="size-5" />
            <DialogTitle className="text-base text-foreground">
              Thu Hồi Khóa API?
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground pt-1">
            Bạn có chắc chắn muốn thu hồi khóa <strong>{keyItem.name}</strong> (
            {keyItem.key_prefix}...) của ứng dụng{" "}
            <strong>{keyItem.app_name}</strong>?
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleRevoke} className="space-y-4 py-2 text-xs">
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-[11px] text-destructive leading-relaxed">
            Hành động này <strong>không thể hoàn tác</strong>. Mọi ứng dụng sử
            dụng khóa này sẽ bị từ chối truy cập ngay lập tức kể từ request tiếp
            theo.
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="revoke_reason" className="text-xs font-medium">
              Lý do thu hồi (Lưu vào nhật ký kiểm toán)
            </Label>
            <Input
              id="revoke_reason"
              placeholder="VD: Nghi ngờ lộ secret, ứng dụng ngưng hoạt động..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="h-8 text-xs"
              required
            />
          </div>

          <DialogFooter className="gap-2 pt-2 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={revokeMutation.isPending}
              onClick={onClose}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              variant="destructive"
              size="sm"
              disabled={revokeMutation.isPending}
              className="gap-1.5"
            >
              <Trash2 className="size-3.5" />
              <span>
                {revokeMutation.isPending
                  ? "Đang thu hồi..."
                  : "Thu hồi khóa vĩnh viễn"}
              </span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
