import {
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
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
  showBoxes,
  onToggleBoxes,
  disabled,
}) => {
  return (
    <div
      role="toolbar"
      aria-label="Thanh điều khiển trang tài liệu"
      className="h-10 shrink-0 w-full px-4 border-b border-border bg-card dark:bg-zinc-900/90 flex items-center justify-center gap-4 text-xs select-none z-10"
    >
      {/* 1. PAGINATION CONTROLS (Mistral style: < 1 / 14 >) */}
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={disabled || currentPage <= 1}
          className="size-7 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md"
          title="Trang trước"
          aria-label="Trang trước"
        >
          <ChevronLeft className="size-3.5" />
        </Button>

        <div className="flex items-center gap-1.5 px-1 font-medium text-foreground text-xs">
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
            className="w-8 h-6 text-center font-mono font-medium text-foreground bg-background dark:bg-muted/40 border border-border rounded text-xs focus:outline-hidden focus:ring-1 focus:ring-ring"
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
          title="Trang sau"
          aria-label="Trang sau"
        >
          <ChevronRight className="size-3.5" />
        </Button>
      </div>

      <div className="h-4 w-px bg-border/70" />

      {/* 2. ZOOM CONTROLS (Mistral style: - 100% +) */}
      <div className="flex items-center gap-1">
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
          className="px-1.5 font-mono text-[11px] font-medium text-foreground hover:text-primary transition-colors min-w-11 text-center cursor-pointer"
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
      </div>

      <div className="h-4 w-px bg-border/70" />

      {/* 3. BOUNDING BOXES TOGGLE */}
      <button
        type="button"
        onClick={() => onToggleBoxes(!showBoxes)}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer border ${
          showBoxes
            ? "bg-primary/12 text-primary border-primary/20 shadow-2xs"
            : "text-muted-foreground hover:text-foreground hover:bg-muted border-transparent"
        }`}
        title={
          showBoxes ? "Ẩn khung nhận diện scan" : "Hiện khung nhận diện scan"
        }
      >
        {showBoxes ? (
          <Eye className="size-3.5 text-primary" />
        ) : (
          <EyeOff className="size-3.5" />
        )}
        <span>Khung scan</span>
      </button>
    </div>
  );
};
