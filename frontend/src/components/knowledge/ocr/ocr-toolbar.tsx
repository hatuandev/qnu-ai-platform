import {
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Maximize2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import type React from "react";
import { Button } from "@/components/ui/button";
import type { OcrToolbarProps } from "./types";

export const OcrToolbar: React.FC<OcrToolbarProps> = ({
  currentPage,
  totalPages,
  pageInput,
  onPageInputChange,
  onPageChange,
  zoomLevel,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onFitWidth,
  showBoxes,
  onToggleBoxes,
  disabled,
}) => {
  return (
    <div
      role="toolbar"
      aria-label="Thanh điều khiển trang tài liệu"
      className="h-10 shrink-0 w-full px-3 border-b border-border bg-card/95 dark:bg-zinc-900/90 backdrop-blur-xs flex items-center justify-between text-xs select-none z-10 gap-2"
    >
      {/* 1. PAGINATION & VIEW MODE TOGGLE */}
      <div className="flex items-center gap-1.5 shrink-0">
        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={disabled || currentPage <= 1}
            className="size-7 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md"
            title="Trang trước (Phím J hoặc ←)"
            aria-label="Trang trước"
          >
            <ChevronLeft className="size-3.5" />
          </Button>

          <div className="flex items-center gap-1 px-1 font-medium text-foreground text-xs">
            <input
              type="text"
              value={pageInput}
              disabled={disabled}
              onChange={(e) => onPageInputChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  const p = Number.parseInt(pageInput, 10);
                  if (!Number.isNaN(p) && p >= 1 && p <= totalPages) {
                    onPageChange(p);
                  } else {
                    onPageInputChange(String(currentPage));
                  }
                }
              }}
              className="w-8 h-6 text-center font-mono font-medium text-foreground bg-background dark:bg-muted/40 border border-border rounded text-xs focus:outline-hidden focus:ring-1 focus:ring-primary"
              aria-label="Số trang hiện tại"
            />
            <span className="text-muted-foreground text-xs font-mono">
              / {totalPages}
            </span>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={disabled || currentPage >= totalPages}
            className="size-7 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md"
            title="Trang sau (Phím K hoặc →)"
            aria-label="Trang sau"
          >
            <ChevronRight className="size-3.5" />
          </Button>
        </div>
      </div>

      {/* 3. ZOOM & DISPLAY ACTIONS */}
      <div className="flex items-center gap-1.5 shrink-0">
        {/* Zoom Controls */}
        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            onClick={onZoomOut}
            disabled={disabled || zoomLevel <= 50}
            className="size-7 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md"
            title="Thu nhỏ"
            aria-label="Thu nhỏ"
          >
            <ZoomOut className="size-3.5" />
          </Button>
          <button
            type="button"
            onClick={onZoomReset}
            className="px-1 font-mono text-[11px] font-medium text-foreground hover:text-primary transition-colors min-w-8 text-center cursor-pointer"
            title="Đặt lại zoom 100%"
          >
            {zoomLevel}%
          </button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onZoomIn}
            disabled={disabled || zoomLevel >= 200}
            className="size-7 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md"
            title="Phóng to"
            aria-label="Phóng to"
          >
            <ZoomIn className="size-3.5" />
          </Button>
          {onFitWidth && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onFitWidth}
              disabled={disabled}
              className="size-7 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md"
              title="Vừa khít chiều rộng"
              aria-label="Vừa khít chiều rộng"
            >
              <Maximize2 className="size-3.5" />
            </Button>
          )}
        </div>

        <div className="h-4 w-px bg-border/70" />

        {/* Bounding Boxes Toggle (Icon-only) */}
        <button
          type="button"
          onClick={() => onToggleBoxes(!showBoxes)}
          className={`flex items-center justify-center size-7 rounded-md text-xs transition-all cursor-pointer border shrink-0 ${
            showBoxes
              ? "bg-primary/15 text-primary border-primary/30 shadow-2xs font-semibold"
              : "text-muted-foreground hover:text-foreground hover:bg-muted border-transparent"
          }`}
          title={
            showBoxes ? "Ẩn khung nhận diện scan" : "Hiện khung nhận diện scan"
          }
          aria-label={showBoxes ? "Ẩn khung scan" : "Hiện khung scan"}
        >
          {showBoxes ? (
            <Eye className="size-3.5 text-primary" />
          ) : (
            <EyeOff className="size-3.5" />
          )}
        </button>
      </div>
    </div>
  );
};
