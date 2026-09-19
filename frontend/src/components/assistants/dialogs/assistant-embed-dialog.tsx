import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Check, Copy, Sparkles } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

interface AssistantEmbedDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assistantCode: string;
  assistantName: string;
}

export function AssistantEmbedDialog({
  open,
  onOpenChange,
  assistantCode,
  assistantName,
}: AssistantEmbedDialogProps) {
  const [copied, setCopied] = React.useState(false);

  const originUrl = typeof window !== "undefined" ? window.location.origin : "";
  const embedSnippet = React.useMemo(() => {
    return `<!-- QNU AI Platform Chat Widget -->
<script 
  src="${originUrl}/widget/qnu-chat-widget.js" 
  data-assistant="${assistantCode}"
  data-api-base="${originUrl}"
  data-title="${assistantName}"
  defer>
</script>`;
  }, [originUrl, assistantCode, assistantName]);

  const handleCopy = () => {
    navigator.clipboard.writeText(embedSnippet);
    setCopied(true);
    toast.success("Đã sao chép mã nhúng widget vào clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="size-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Mã Nhúng Web Chat Widget
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Dán đoạn mã này trước thẻ &lt;/body&gt; trên trang web của Trường ĐH Quy Nhơn để
                tích hợp trợ lý.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="mt-3 space-y-3">
          <div className="relative rounded-lg border border-border bg-muted/40 p-3 font-mono text-xs text-foreground">
            <pre className="overflow-x-auto whitespace-pre-wrap">{embedSnippet}</pre>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Widget hỗ trợ phản hồi Streaming thời gian thực (SSE), hiển thị trích dẫn tài liệu chính
            thức và tự động nhận diện thương hiệu QNU Academic Teal.
          </p>
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Đóng
          </Button>
          <Button size="sm" onClick={handleCopy} className="gap-1.5">
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
            {copied ? "Đã sao chép" : "Sao chép mã nhúng"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
