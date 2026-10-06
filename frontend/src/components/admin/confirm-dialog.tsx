import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export interface ConfirmDialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: ReactNode;
  title: string;
  description: ReactNode;
  confirmText?: string;
  confirmLabel?: string;
  cancelText?: string;
  variant?: "default" | "destructive";
  confirmVariant?: "default" | "destructive";
  isPending?: boolean;
  isLoading?: boolean;
  onConfirm?: (() => unknown) | null;
}

export function ConfirmDialog({
  open = false,
  onOpenChange,
  trigger,
  title,
  description,
  confirmText,
  confirmLabel,
  cancelText = "Hủy",
  variant,
  confirmVariant,
  isPending,
  isLoading,
  onConfirm,
}: ConfirmDialogProps) {
  const finalConfirmLabel = confirmText || confirmLabel || "Xác nhận";
  const finalVariant = variant || confirmVariant || "destructive";
  const loading = isPending ?? isLoading ?? false;

  return (
    <>
      {trigger}
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-md" role="alertdialog">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription asChild>
              <div className="text-sm text-muted-foreground">{description}</div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={loading}
              onClick={() => onOpenChange?.(false)}
            >
              {cancelText}
            </Button>
            <Button
              variant={finalVariant}
              disabled={loading || !onConfirm}
              onClick={() => {
                if (onConfirm) void onConfirm();
              }}
            >
              {loading ? "Đang xử lý..." : finalConfirmLabel}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
