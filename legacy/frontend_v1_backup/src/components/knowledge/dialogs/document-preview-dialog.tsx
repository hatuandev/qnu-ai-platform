import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { KnowledgeDocument } from "@/types";
import { FileText } from "lucide-react";
import { formatFileSize } from "../types";

interface DocumentPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  document: KnowledgeDocument | null;
  collectionName: string;
}

export function DocumentPreviewDialog({
  open,
  onOpenChange,
  document,
  collectionName,
}: DocumentPreviewDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md text-xs">
        <DialogHeader>
          <DialogTitle className="text-sm font-bold flex items-center gap-2">
            <FileText className="size-4 text-primary" />
            <span>{document?.title}</span>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="flex justify-between text-muted-foreground font-mono text-xs pb-2 border-b border-border">
            <span>Tên tệp: {document?.filename}</span>
            <span>{document ? formatFileSize(document.file_size) : ""}</span>
          </div>
          <p className="text-muted-foreground text-xs leading-relaxed">
            Tài liệu đã được bóc tách và phân đoạn thành công qua engine{" "}
            <strong className="text-foreground">{document?.ocr_method}</strong> với{" "}
            <strong className="text-primary">{document?.chunk_count} vector chunks</strong> trong
            kho tri thức <strong className="text-foreground">{collectionName}</strong>.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
