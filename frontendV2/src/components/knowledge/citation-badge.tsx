import { FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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
  className?: string;
}

/**
 * Renders a clean, accessible sequential citation chip (e.g. [1], [2]).
 * Clicking reveals the source provenance and location in a popover,
 * keeping raw technical evidence keys tucked away cleanly.
 */
export function CitationBadge({
  index,
  rawKey,
  sourceFile,
  location,
  excerpt,
  className,
}: CitationBadgeProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Xem nguồn trích dẫn số [${index}]`}
          className={cn(
            "inline-flex items-center justify-center font-mono text-[11px] font-semibold text-primary bg-primary/10 hover:bg-primary/20 hover:text-primary px-1.5 py-0.5 rounded transition-colors ml-1 align-baseline cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary shadow-2xs",
            className,
          )}
          title={`Căn cứ [${index}]: Bấm để xem nguồn trích dẫn`}
        >
          [{index}]
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        sideOffset={6}
        className="w-80 p-3.5 space-y-2.5 text-xs bg-card border border-border/70 shadow-md rounded-xl select-text"
      >
        <div className="flex items-center justify-between border-b border-border/50 pb-2">
          <div className="font-semibold text-foreground flex items-center gap-1.5">
            <FileText className="size-4 text-primary" />
            <span>Căn cứ trích dẫn [{index}]</span>
          </div>
          {location && (
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 font-medium"
            >
              {location}
            </Badge>
          )}
        </div>

        <div className="space-y-1.5 text-muted-foreground">
          <div>
            <span className="font-medium text-foreground">Tệp nguồn: </span>
            <span className="break-all">{sourceFile || "Tài liệu gốc"}</span>
          </div>

          {excerpt && (
            <div className="pt-1">
              <div className="font-medium text-foreground mb-1">
                Nội dung đối chiếu:
              </div>
              <p className="p-2 rounded-md bg-muted/40 italic text-foreground/80 text-[11px] leading-relaxed border border-border/40">
                "{excerpt}"
              </p>
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
