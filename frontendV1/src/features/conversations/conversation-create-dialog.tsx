import { useNavigate } from "@tanstack/react-router";
import { Bot, MessageSquarePlus } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { ResponsiveDialogContent } from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAssistantsQuery } from "@/features/assistants/queries";
import type { Assistant } from "@/features/assistants/types";
import { useCreateConversation } from "./queries";
import { formatConversationError } from "./schemas";

export function ConversationCreateDialog({
  workspaceId,
  open,
  onOpenChange,
  preselectedAssistant,
}: {
  workspaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  preselectedAssistant?: Assistant | null;
}) {
  const navigate = useNavigate();
  const assistantsQuery = useAssistantsQuery(workspaceId, {
    limit: 100,
    offset: 0,
  });
  const createMutation = useCreateConversation(workspaceId);

  const [title, setTitle] = useState("Hội thoại mới");
  const [assistantId, setAssistantId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Active assistants available for selection
  const activeAssistants = (assistantsQuery.data ?? []).filter(
    (item) => item.is_active,
  );

  const defaultAssistantId =
    preselectedAssistant?.id ?? activeAssistants[0]?.id ?? "";

  useEffect(() => {
    if (open) {
      setTitle("Hội thoại mới");
      setError(null);
      setAssistantId(defaultAssistantId);
    }
  }, [open, defaultAssistantId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assistantId) {
      setError("Vui lòng chọn trợ lý AI");
      return;
    }

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
      const created = await createMutation.mutateAsync({
        assistant_id: assistantId,
        title: trimmedTitle,
      });
      toast.success("Đã tạo hội thoại mới");
      onOpenChange(false);
      void navigate({
        to: "/workspaces/$workspaceId/conversations/$conversationId",
        params: { workspaceId, conversationId: created.id },
      });
    } catch (err) {
      if (err instanceof ApiProblemError) {
        setError(formatConversationError(err.code, err.message));
      } else {
        setError(
          "Không nhận được phản hồi từ máy chủ. Vui lòng kiểm tra danh sách hội thoại trước khi thử lại.",
        );
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="p-0 gap-0 max-w-lg">
        <form onSubmit={handleSubmit} className="flex flex-col min-h-0">
          <DialogHeader className="border-b bg-muted/20 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                <MessageSquarePlus className="size-4" />
              </div>
              <div>
                <DialogTitle className="text-base font-semibold">
                  Tạo cuộc trò chuyện mới
                </DialogTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Bắt đầu phiên hỏi đáp với Trợ lý AI có dẫn nguồn chứng minh
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
              <Label htmlFor="conv-assistant" className="text-xs font-medium">
                Trợ lý AI <span className="text-destructive">*</span>
              </Label>
              {preselectedAssistant ? (
                <div className="flex items-center gap-2 p-2.5 rounded-md border bg-muted/20 text-xs">
                  <Bot className="size-4 text-primary shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-foreground truncate">
                      {preselectedAssistant.name}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      v{preselectedAssistant.revision} • Đang hoạt động
                    </p>
                  </div>
                </div>
              ) : activeAssistants.length === 0 ? (
                <div className="rounded-md border border-dashed p-3 text-center text-xs text-muted-foreground">
                  Chưa có trợ lý AI nào đang hoạt động trong workspace này.
                </div>
              ) : (
                <Select value={assistantId} onValueChange={setAssistantId}>
                  <SelectTrigger id="conv-assistant" className="text-xs">
                    <SelectValue placeholder="Chọn trợ lý AI..." />
                  </SelectTrigger>
                  <SelectContent>
                    {activeAssistants.map((ast) => (
                      <SelectItem
                        key={ast.id}
                        value={ast.id}
                        className="text-xs"
                      >
                        {ast.name} (v{ast.revision})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="conv-title" className="text-xs font-medium">
                Tiêu đề hội thoại
              </Label>
              <Input
                id="conv-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={160}
                placeholder="Nhập tiêu đề hội thoại..."
                className="text-xs"
              />
              <p className="text-[11px] text-muted-foreground">
                Tối đa 160 ký tự. Có thể đổi tên sau trong quá trình trò chuyện.
              </p>
            </div>
          </div>

          <div className="border-t bg-card px-6 py-3 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={
                createMutation.isPending ||
                (!preselectedAssistant && activeAssistants.length === 0)
              }
            >
              {createMutation.isPending ? "Đang tạo..." : "Bắt đầu trò chuyện"}
            </Button>
          </div>
        </form>
      </ResponsiveDialogContent>
    </Dialog>
  );
}
