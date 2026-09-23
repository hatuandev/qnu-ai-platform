import { type ReactNode, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

const NOTE_MAX = 500;

export function NoteConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  noteLabel = "Lý do / Ghi chú",
  notePlaceholder,
  confirmLabel = "Xác nhận",
  confirmVariant = "destructive",
  requireNote = true,
  isLoading = false,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  noteLabel?: string;
  notePlaceholder?: string;
  confirmLabel?: string;
  confirmVariant?: "default" | "destructive";
  requireNote?: boolean;
  isLoading?: boolean;
  onConfirm: (note: string) => void;
}) {
  const [note, setNote] = useState("");

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setNote("");
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-md" role="alertdialog">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription asChild>
            <div className="text-sm text-muted-foreground">{description}</div>
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <label
            htmlFor="note-confirm-input"
            className="type-supporting font-medium text-foreground"
          >
            {noteLabel}
            {requireNote ? (
              <span className="ml-1 text-destructive">*</span>
            ) : null}
          </label>
          <Textarea
            id="note-confirm-input"
            value={note}
            placeholder={notePlaceholder}
            rows={3}
            maxLength={NOTE_MAX}
            disabled={isLoading}
            onChange={(event) => setNote(event.target.value)}
          />
          <p className="type-supporting text-muted-foreground">
            {note.length}/{NOTE_MAX}
          </p>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            disabled={isLoading}
            onClick={() => onOpenChange(false)}
          >
            Hủy
          </Button>
          <Button
            variant={confirmVariant}
            disabled={isLoading || (requireNote && !note.trim())}
            onClick={() => {
              onConfirm(note.trim());
              setNote("");
            }}
          >
            {isLoading ? "Đang xử lý..." : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
