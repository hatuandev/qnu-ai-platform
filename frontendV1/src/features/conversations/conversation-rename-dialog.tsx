import { Pencil } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { ResponsiveDialogContent } from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUpdateConversation } from "./queries";
import { formatConversationError } from "./schemas";
import type { Conversation } from "./types";

export function ConversationRenameDialog({
  workspaceId,
  conversation,
  open,
  onOpenChange,
}: {
  workspaceId: string;
  conversation: Conversation;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const updateMutation = useUpdateConversation(workspaceId, conversation.id);
  const [title, setTitle] = useState(conversation.title);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setTitle(conversation.title);
      setError(null);
    }
  }, [open, conversation.title]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError("Tiêu đề không được để trống");
      return;
    }
    if (trimmedTitle.length > 160) {
      setError("Tiêu đề tối đa 160 ký tự");
      return;
    }

    setError(null);
    try {
      await updateMutation.mutateAsync({
        title: trimmedTitle,
        status: conversation.status, // preserve status
      });
      toast.success("Đã đổi tên cuộc trò chuyện");
      onOpenChange(false);
    } catch (err) {
      if (err instanceof ApiProblemError) {
        setError(formatConversationError(err.code, err.message));
      } else {
        setError("Không thể cập nhật tên cuộc trò chuyện. Vui lòng thử lại.");
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="p-0 gap-0 max-w-md">
        <form onSubmit={handleSubmit} className="flex flex-col min-h-0">
          <DialogHeader className="border-b bg-muted/20 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                <Pencil className="size-4" />
              </div>
              <div>
                <DialogTitle className="text-base font-semibold">
                  Đổi tên cuộc trò chuyện
                </DialogTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Cập nhật tiêu đề hiển thị trong danh sách hội thoại
                </p>
              </div>
            </div>
          </DialogHeader>

          <div className="p-6 space-y-4">
            {error && (
              <Alert variant="destructive" className="py-2.5">
                <AlertDescription className="text-xs">{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="rename-title" className="text-xs font-medium">
                Tiêu đề mới <span className="text-destructive">*</span>
              </Label>
              <Input
                id="rename-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={160}
                placeholder="Nhập tiêu đề hội thoại..."
                className="text-xs"
                autoFocus
              />
              <p className="text-[11px] text-muted-foreground">
                Tối đa 160 ký tự.
              </p>
            </div>
          </div>

          <div className="border-t bg-card px-6 py-3 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={updateMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={updateMutation.isPending || !title.trim()}
            >
              {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
          </div>
        </form>
      </ResponsiveDialogContent>
    </Dialog>
  );
}
