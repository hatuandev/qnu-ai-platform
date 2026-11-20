import { Check, Copy, ExternalLink, FileText } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface CitationBadgeProps {
  index: number;
  rawKey: string;
  sourceFile?: string;
  location?: string;
  excerpt?: string;
  fullText?: string;
  className?: string;
  onSelect?: (index: number, rawKey: string) => void;
}

/**
 * Renders a clean, accessible sequential citation chip (e.g. [1], [2]).
 * Clicking reveals the source provenance and location in a popover,
 * keeping raw technical evidence keys tucked away cleanly.
 * Supports viewing full table rows / long excerpts with expandable toggle.
 */
export function CitationBadge({
  index,
  rawKey,
  sourceFile,
  location,
  excerpt,
  fullText,
  className,
  onSelect,
}: CitationBadgeProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const targetText = (fullText || excerpt || "").trim();
  const isLong = targetText.length > 240;
  const displayText =
    isLong && !expanded ? `${targetText.slice(0, 240)}…` : targetText;

  const handleCopy = async () => {
    if (!targetText) return;
    try {
      await navigator.clipboard.writeText(targetText);
      setCopied(true);
      toast.success("Đã sao chép nội dung đối chiếu.");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Không thể sao chép văn bản.");
    }
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Xem nguồn trích dẫn số [${index}]`}
          onClick={() => {
            if (onSelect) {
              onSelect(index, rawKey);
            }
          }}
          className={cn(
            "inline-flex items-center justify-center font-mono text-[11px] font-semibold text-primary bg-primary/10 hover:bg-primary/20 hover:text-primary px-1.5 py-0.5 rounded transition-colors ml-1 align-baseline cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary shadow-2xs",
            className,
          )}
          title={`Căn cứ [${index}]: Bấm để mở ngăn đối soát nguồn trích dẫn`}
        >
          [{index}]
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        sideOffset={6}
        className="w-84 sm:w-96 max-w-[92vw] p-3.5 space-y-2.5 text-xs bg-card border border-border/70 shadow-md rounded-xl select-text z-50"
      >
        <div className="flex items-center justify-between border-b border-border/50 pb-2">
          <div className="font-semibold text-foreground flex items-center gap-1.5">
            <FileText className="size-4 text-primary" />
            <span>Căn cứ trích dẫn [{index}]</span>
          </div>
          <div className="flex items-center gap-1.5">
            {onSelect && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-5 px-1.5 text-[10px] gap-1 text-primary hover:bg-primary/10 cursor-pointer"
                onClick={() => onSelect(index, rawKey)}
                title="Mở ngăn đối chiếu bên phải"
              >
                <ExternalLink className="size-2.5" />
                <span>Xem chi tiết</span>
              </Button>
            )}
            {location && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 font-medium max-w-[150px] truncate"
                title={location}
              >
                {location}
              </Badge>
            )}
          </div>
        </div>

        <div className="space-y-1.5 text-muted-foreground">
          <div>
            <span className="font-medium text-foreground">Tệp nguồn: </span>
            <span className="break-all">{sourceFile || "Tài liệu gốc"}</span>
          </div>

          {targetText && (
            <div className="pt-1 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-medium text-foreground">
                  Nội dung đối chiếu:
                </span>
                <div className="flex items-center gap-1.5">
                  {isLong && (
                    <button
                      type="button"
                      onClick={() => setExpanded((prev) => !prev)}
                      className="text-[10px] text-primary hover:underline font-medium cursor-pointer"
                    >
                      {expanded
                        ? "Thu gọn"
                        : `Xem trọn vẹn (${targetText.length} ký tự)`}
                    </button>
                  )}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-5 px-1 text-[10px] text-muted-foreground hover:text-foreground cursor-pointer"
                    onClick={handleCopy}
                    title="Sao chép trích đoạn"
                  >
                    {copied ? (
                      <Check className="size-3 text-emerald-600" />
                    ) : (
                      <Copy className="size-3" />
                    )}
                    <span className="sr-only">Sao chép</span>
                  </Button>
                </div>
              </div>

              <div
                className={cn(
                  "p-2 rounded-md bg-muted/40 text-foreground/90 text-[11px] leading-relaxed border border-border/40 select-text",
                  expanded
                    ? "max-h-60 overflow-y-auto whitespace-pre-wrap font-mono text-[10.5px]"
                    : "italic whitespace-pre-wrap",
                )}
              >
                "{displayText}"
              </div>
            </div>
          )}
        </div>

        <details className="text-[10px] text-muted-foreground">
          <summary className="cursor-pointer">Thông tin đối chiếu</summary>
          <code className="break-all">{rawKey}</code>
        </details>
      </PopoverContent>
    </Popover>
  );
}
