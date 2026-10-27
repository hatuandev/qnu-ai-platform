import { X } from "lucide-react";
import type { ReactNode } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function DataTableBulkActions({
  selectedCount,
  selectedLabel = "mục",
  onClear,
  children,
}: {
  selectedCount: number;
  selectedLabel?: string;
  onClear: () => void;
  children?: ReactNode;
}) {
  return (
    <TooltipProvider delayDuration={150}>
      <div
        aria-hidden={selectedCount === 0}
        data-visible={selectedCount > 0}
        className="pointer-events-none fixed inset-x-0 bottom-5 z-40 flex translate-y-3 justify-center px-4 opacity-0 transition-[opacity,transform] duration-[var(--motion-base)] ease-out data-[visible=true]:translate-y-0 data-[visible=true]:opacity-100 data-[visible=false]:duration-[var(--motion-fast)]"
      >
        <div className="pointer-events-auto flex max-w-[calc(100vw-32px)] items-center gap-2.5 overflow-x-auto rounded-2xl border border-border/80 bg-background/95 px-3 py-1.5 shadow-lg backdrop-blur-md">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="flex size-7 shrink-0 items-center justify-center rounded-full border border-border/80 bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
                aria-label="Bỏ chọn tất cả"
                onClick={onClear}
              >
                <X className="size-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top">Bỏ chọn tất cả</TooltipContent>
          </Tooltip>

          <span className="h-4 w-px shrink-0 bg-border/80" />

          <div className="flex items-center gap-2 shrink-0">
            <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-foreground px-2 py-0.5 font-mono text-xs font-bold text-background shadow-xs">
              {selectedCount}
            </span>
            <span className="text-xs font-medium text-foreground">
              <span className="hidden sm:inline">{selectedLabel} đã chọn</span>
              <span className="sm:hidden">đã chọn</span>
            </span>
          </div>

          {children ? (
            <>
              <span className="h-4 w-px shrink-0 bg-border/80" />
              <div className="flex items-center gap-1.5">{children}</div>
            </>
          ) : null}
        </div>
      </div>
    </TooltipProvider>
  );
}
