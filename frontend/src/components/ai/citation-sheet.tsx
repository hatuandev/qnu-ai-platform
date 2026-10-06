import {
  BookOpen,
  ExternalLink,
  FileCheck2,
  Layers,
  Quote,
  ShieldCheck,
} from "lucide-react";
import type React from "react";
import type { ChatCitation } from "../../hooks/use-rag-stream";
import { Badge } from "../ui/badge";
import { Separator } from "../ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "../ui/sheet";

export interface CitationSheetProps {
  citation: ChatCitation | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export const CitationSheet: React.FC<CitationSheetProps> = ({
  citation,
  isOpen,
  onOpenChange,
}) => {
  if (!citation) return null;

  const scorePct =
    citation.score !== undefined ? Math.round(citation.score * 100) : undefined;

  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg flex flex-col gap-0 p-0 overflow-hidden bg-card"
      >
        <SheetHeader className="p-5 border-b border-border bg-muted/30">
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-control bg-primary/10 text-primary">
              <ShieldCheck className="h-4 w-4" />
            </span>
            <Badge variant="outline" className="text-[11px] font-mono">
              Minh chứng đối chiếu RAG
            </Badge>
            {scorePct !== undefined && (
              <Badge variant="success" className="text-[11px] ml-auto">
                Độ tương đồng: {scorePct}%
              </Badge>
            )}
          </div>
          <SheetTitle className="text-base font-bold text-foreground text-left leading-snug">
            {citation.title}
          </SheetTitle>
          <SheetDescription className="text-xs text-muted-foreground text-left">
            Căn cứ pháp lý chính thức lưu trữ tại Trung tâm Tri thức QNU
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-5 space-y-5 text-sm">
          {/* Metadata Block */}
          <div className="grid grid-cols-2 gap-3 p-3.5 rounded-control bg-muted/50 border border-border/80 text-xs">
            <div className="space-y-1">
              <span className="text-muted-foreground flex items-center gap-1.5 font-medium">
                <FileCheck2 className="h-3.5 w-3.5 text-primary" />
                Tệp văn bản gốc
              </span>
              <p
                className="font-semibold text-foreground truncate"
                title={citation.document_name}
              >
                {citation.document_name}
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-muted-foreground flex items-center gap-1.5 font-medium">
                <BookOpen className="h-3.5 w-3.5 text-info" />
                Vị trí Điều / Khoản
              </span>
              <p className="font-semibold text-foreground">
                {[citation.article, citation.clause]
                  .filter(Boolean)
                  .join(", ") || "Điều khoản chung"}
              </p>
            </div>

            {citation.page !== undefined && (
              <div className="space-y-1">
                <span className="text-muted-foreground flex items-center gap-1.5 font-medium">
                  <Layers className="h-3.5 w-3.5 text-warning" />
                  Trang tài liệu
                </span>
                <p className="font-semibold text-foreground">
                  Trang {citation.page}
                </p>
              </div>
            )}

            <div className="space-y-1">
              <span className="text-muted-foreground font-medium">
                Thuật toán trích xuất
              </span>
              <p className="font-semibold text-primary font-mono text-[11px]">
                Dense + Sparse RRF (k=60)
              </p>
            </div>
          </div>

          <Separator />

          {/* Excerpt Block */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
              <Quote className="h-4 w-4 text-primary" />
              Đoạn trích đối chiếu từ tài liệu gốc (Grounding Excerpt)
            </div>
            <div className="p-4 rounded-surface bg-primary/5 border border-primary/20 text-xs leading-relaxed text-foreground/90 select-text whitespace-pre-wrap font-sans relative">
              <p className="italic">"{citation.excerpt}"</p>
            </div>
          </div>

          {/* Policy Banner */}
          <div className="p-3 rounded-control bg-muted/80 border border-border/80 text-[11px] text-muted-foreground leading-relaxed">
            <span className="font-semibold text-foreground">
              Cam kết Zero-Hallucination:
            </span>{" "}
            Mọi câu trả lời của Trợ lý AI QNU đều được kiểm tra tính xác thực
            qua bộ lọc Guardrails trước khi chuyển tiếp tới người dùng. Nếu
            thông tin không có trong tài liệu, hệ thống tự động điều hướng tới
            Phòng ban phụ trách.
          </div>
        </div>

        {citation.url && (
          <div className="p-4 border-t border-border bg-muted/20 flex justify-end">
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
            >
              Mở văn bản gốc đầy đủ
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};
