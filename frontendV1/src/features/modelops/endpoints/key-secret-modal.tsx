import { AlertTriangle, Check, Copy, ShieldAlert } from "lucide-react";
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
import type { AppApiKeySecretResponse } from "@/features/modelops/types";

interface KeySecretModalProps {
  data: AppApiKeySecretResponse | null;
  onClose: () => void;
}

export function KeySecretModal({ data, onClose }: KeySecretModalProps) {
  const [copied, setCopied] = React.useState(false);

  if (!data) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(data.secret_key);
      setCopied(true);
      toast.success("Đã sao chép khóa API vào clipboard!");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error(
        "Không thể tự động sao chép. Vui lòng chọn và copy thủ công.",
      );
    }
  };

  return (
    <Dialog open={Boolean(data)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md sm:max-w-lg" role="alertdialog">
        <DialogHeader>
          <div className="flex items-center gap-2 text-warning">
            <ShieldAlert className="size-5" />
            <DialogTitle className="text-base text-foreground">
              Lưu Khóa Bí Mật Của Bạn
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground pt-1">
            Khóa API cho ứng dụng <strong>{data.app_name}</strong> ({data.name})
            đã được tạo thành công.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Security Banner */}
          <div className="rounded-lg border border-warning/40 bg-warning/10 p-3 text-xs text-warning-foreground space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-warning">
              <AlertTriangle className="size-4 shrink-0" />
              <span>Chỉ hiển thị một lần duy nhất</span>
            </div>
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Vì lý do an toàn, máy chủ chỉ lưu mã băm SHA-256 của khóa này. Bạn
              sẽ <strong>không thể xem lại</strong> khóa bí mật sau khi đóng cửa
              sổ này.
            </p>
          </div>

          {/* Secret Key Box */}
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-foreground">
              Khóa bí mật (API Key):
            </p>
            <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/60 p-2.5 font-mono text-xs">
              <span className="flex-1 break-all select-all font-semibold text-primary">
                {data.secret_key}
              </span>
              <Button
                type="button"
                size="sm"
                variant={copied ? "default" : "secondary"}
                className="h-8 gap-1.5 px-3 shrink-0 text-xs"
                onClick={handleCopy}
              >
                {copied ? (
                  <>
                    <Check className="size-3.5" />
                    <span>Đã chép</span>
                  </>
                ) : (
                  <>
                    <Copy className="size-3.5" />
                    <span>Sao chép</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter className="sm:justify-between gap-2 border-t pt-3">
          <p className="text-[11px] text-muted-foreground self-center">
            Hãy chắc chắn bạn đã sao chép trước khi hoàn tất.
          </p>
          <Button
            type="button"
            onClick={onClose}
            className="text-xs font-semibold"
          >
            Tôi đã lưu khóa an toàn
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
