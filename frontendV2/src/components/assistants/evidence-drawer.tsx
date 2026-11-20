import { Check, Copy, FileText, Layers, Quote, Table } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import type { AnswerSource } from "@/api/answer-reviews";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

export interface EvidenceDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sources: AnswerSource[];
  selectedEvidenceId?: string | null;
  selectedIndex?: number | null;
  turnNo?: number;
  question?: string;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function sourceLocation(source: AnswerSource): string | undefined {
  const structure = asRecord(source.structure);
  const context = structure ? asRecord(structure.context) : null;
  const heading =
    context && typeof context.heading === "string" ? context.heading : null;
  const title =
    context && typeof context.title === "string" ? context.title : null;
  const citation =
    structure && typeof structure.source_table_citation === "string"
      ? structure.source_table_citation
      : null;
  const pageNo =
    structure && typeof structure.page_number === "number"
      ? `Trang ${structure.page_number}`
      : null;

  const parts = [pageNo, heading ?? title ?? citation].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : undefined;
}

function sourceDocumentTitle(source: AnswerSource): string {
  const citations = asRecord(source.citations);
  if (citations) {
    if (typeof citations.document_title === "string" && citations.document_title.trim()) {
      return citations.document_title.trim();
    }
    if (typeof citations.title === "string" && citations.title.trim()) {
      return citations.title.trim();
    }
    if (typeof citations.filename === "string" && citations.filename.trim()) {
      return citations.filename.trim();
    }
  }
  const structure = asRecord(source.structure);
  const context = structure ? asRecord(structure.context) : null;
  if (context && typeof context.document_title === "string") {
    return context.document_title.trim();
  }
  return source.document_id || "Tài liệu lưu trữ";
}

function sourceFullText(source: AnswerSource): string {
  const passage = source.source_passages?.[0]?.text;
  return (passage ?? source.text ?? "").trim();
}

function sourceKindBadge(kind: string) {
  if (kind === "table") {
    return (
      <Badge variant="outline" className="h-4 px-1.5 text-[10px] gap-1 font-medium border-primary/30 bg-primary/10 text-primary">
        <Table className="size-2.5" />
        <span>Bảng dữ liệu</span>
      </Badge>
    );
  }
  if (kind === "row_card") {
    return (
      <Badge variant="outline" className="h-4 px-1.5 text-[10px] gap-1 font-medium border-teal-500/30 bg-teal-500/10 text-teal-700 dark:text-teal-300">
        <Layers className="size-2.5" />
        <span>Thẻ dòng dữ liệu</span>
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="h-4 px-1.5 text-[10px] gap-1 font-medium text-muted-foreground">
      <FileText className="size-2.5" />
      <span>Đoạn văn</span>
    </Badge>
  );
}

export function EvidenceDrawer({
  open,
  onOpenChange,
  sources,
  selectedEvidenceId,
  selectedIndex,
  turnNo,
  question,
}: EvidenceDrawerProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);
  const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!open) return;
    const targetKey = selectedEvidenceId || (selectedIndex ? `index-${selectedIndex}` : null);
    if (!targetKey) return;

    const timer = setTimeout(() => {
      const element = itemRefs.current[targetKey];
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 150);
    return () => clearTimeout(timer);
  }, [open, selectedEvidenceId, selectedIndex]);

  const handleCopySingle = async (source: AnswerSource, idx: number) => {
    const text = sourceFullText(source);
    const doc = sourceDocumentTitle(source);
    const loc = sourceLocation(source);
    const clip = `[Căn cứ ${idx}] ${doc}${loc ? ` (${loc})` : ""}:\n${text}`;
    try {
      await navigator.clipboard.writeText(clip);
      setCopiedId(source.evidence_id);
      toast.success(`Đã sao chép căn cứ [${idx}].`);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      toast.error("Không thể sao chép nội dung.");
    }
  };

  const handleCopyAll = async () => {
    if (sources.length === 0) return;
    const allText = sources
      .map((s, idx) => {
        const text = sourceFullText(s);
        const doc = sourceDocumentTitle(s);
        const loc = sourceLocation(s);
        return `[Căn cứ ${idx + 1}] ${doc}${loc ? ` (${loc})` : ""}:\n${text}`;
      })
      .join("\n\n---\n\n");

    try {
      await navigator.clipboard.writeText(allText);
      setCopiedAll(true);
      toast.success("Đã sao chép tất cả các căn cứ dẫn chứng.");
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      toast.error("Không thể sao chép nội dung.");
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg p-0 flex flex-col bg-background border-l border-border/70 shadow-2xl z-50"
      >
        <SheetHeader className="p-4 pb-3 border-b border-border/60 bg-muted/20 shrink-0">
          <div className="flex items-center justify-between pr-8">
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
                <Quote className="size-3.5" />
              </div>
              <div>
                <SheetTitle className="text-sm font-semibold flex items-center gap-2">
                  <span>Nguồn dẫn chứng & Đối soát</span>
                  <Badge variant="secondary" className="h-4 px-1.5 text-[10px] font-mono">
                    {sources.length} căn cứ
                  </Badge>
                </SheetTitle>
                <SheetDescription className="text-[11px] text-muted-foreground truncate max-w-[340px]">
                  {turnNo ? `Lượt hỏi ${turnNo}` : "Câu trả lời hiện tại"}
                  {question ? `: "${question}"` : ""}
                </SheetDescription>
              </div>
            </div>
            {sources.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyAll}
                className="h-7 px-2 text-[11px] gap-1 text-muted-foreground hover:text-foreground cursor-pointer"
                title="Sao chép toàn bộ căn cứ"
              >
                {copiedAll ? (
                  <Check className="size-3 text-emerald-600" />
                ) : (
                  <Copy className="size-3" />
                )}
                <span>{copiedAll ? "Đã chép" : "Chép hết"}</span>
              </Button>
            )}
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {sources.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center text-muted-foreground space-y-2">
              <Quote className="size-8 stroke-1 text-muted-foreground/40" />
              <p className="text-xs">Không có nguồn dẫn chứng nào được ghi nhận cho lượt hỏi này.</p>
            </div>
          ) : (
            sources.map((source, index) => {
              const idx = index + 1;
              const isTarget =
                (selectedEvidenceId && source.evidence_id === selectedEvidenceId) ||
                (selectedIndex && selectedIndex === idx);
              const docTitle = sourceDocumentTitle(source);
              const location = sourceLocation(source);
              const text = sourceFullText(source);
              const isTable = source.kind === "table" || source.kind === "row_card";

              return (
                <div
                  key={source.evidence_id || `source-${idx}`}
                  ref={(el) => {
                    itemRefs.current[source.evidence_id] = el;
                    itemRefs.current[`index-${idx}`] = el;
                  }}
                  className={cn(
                    "rounded-xl border p-3.5 space-y-2.5 transition-all duration-200 bg-card text-card-foreground shadow-2xs",
                    isTarget
                      ? "border-primary ring-2 ring-primary/20 bg-primary/5"
                      : "border-border/60 hover:border-border",
                  )}
                >
                  <div className="flex items-start justify-between gap-2 border-b border-border/40 pb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="inline-flex items-center justify-center font-mono text-[11px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-md">
                        [{idx}]
                      </span>
                      {sourceKindBadge(source.kind)}
                      {location && (
                        <span className="text-[11px] font-medium text-foreground/80 truncate max-w-[220px]" title={location}>
                          {location}
                        </span>
                      )}
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopySingle(source, idx)}
                      className="size-6 p-0 text-muted-foreground hover:text-foreground cursor-pointer shrink-0"
                      title="Sao chép căn cứ này"
                    >
                      {copiedId === source.evidence_id ? (
                        <Check className="size-3 text-emerald-600" />
                      ) : (
                        <Copy className="size-3" />
                      )}
                      <span className="sr-only">Sao chép</span>
                    </Button>
                  </div>

                  <div className="text-[11px] space-y-1">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <FileText className="size-3 text-primary/70 shrink-0" />
                      <span className="font-semibold text-foreground line-clamp-1" title={docTitle}>
                        {docTitle}
                      </span>
                    </div>

                    <div
                      className={cn(
                        "mt-1.5 p-2.5 rounded-lg border leading-relaxed select-text",
                        isTable
                          ? "font-mono text-[10.5px] bg-muted/40 border-border/50 max-h-64 overflow-y-auto whitespace-pre-wrap"
                          : "text-xs italic bg-muted/20 border-border/30 whitespace-pre-wrap text-foreground/90",
                      )}
                    >
                      "{text}"
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-muted-foreground/75 pt-1">
                    <span className="font-mono truncate max-w-[200px]" title={source.evidence_id}>
                      Mã căn cứ: {source.evidence_id.slice(0, 16)}...
                    </span>
                    {typeof source.score === "number" && (
                      <span className="font-mono">
                        Độ tương quan: {(source.score * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="p-3 border-t border-border/60 bg-muted/20 text-center text-[10px] text-muted-foreground shrink-0">
          Căn cứ được đối chiếu nguyên văn từ bản xuất bản chính thức trong kho tri thức.
        </div>
      </SheetContent>
    </Sheet>
  );
}
