import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Layers,
  RotateCcw,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import type React from "react";
import { OCR_ENGINE_OPTIONS, type OcrToolbarProps } from "./types";

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
  regionFilter,
  onRegionFilterChange,
  selectedEngine,
  onSelectEngine,
  disabled,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 border-b border-border bg-card/80 backdrop-blur-xs text-xs">
      {/* Pagination Controls */}
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onPageChange(1)}
          disabled={disabled || currentPage <= 1}
          className="size-7"
          title="Trang đầu"
          aria-label="Trang đầu"
        >
          <ChevronsLeft className="size-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={disabled || currentPage <= 1}
          className="size-7"
          title="Trang trước"
          aria-label="Trang trước"
        >
          <ChevronLeft className="size-3.5" />
        </Button>

        <div className="flex items-center gap-1 px-1.5 font-medium text-muted-foreground text-xs">
          <span>Trang</span>
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
            className="w-10 h-6 text-center font-mono font-semibold text-foreground bg-background border border-border rounded text-xs"
            aria-label="Nhập số trang"
          />
          <span>/ {totalPages}</span>
        </div>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={disabled || currentPage >= totalPages}
          className="size-7"
          title="Trang sau"
          aria-label="Trang sau"
        >
          <ChevronRight className="size-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onPageChange(totalPages)}
          disabled={disabled || currentPage >= totalPages}
          className="size-7"
          title="Trang cuối"
          aria-label="Trang cuối"
        >
          <ChevronsRight className="size-3.5" />
        </Button>
      </div>

      {/* Right: Engine Selector + Zoom & Bounding Box Controls */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Engine selector */}
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground text-xs hidden sm:inline">Bộ máy OCR:</span>
          <Select value={selectedEngine} onValueChange={onSelectEngine} disabled={disabled}>
            <SelectTrigger sizeVariant="sm" className="h-7 text-xs w-44">
              <SelectValue placeholder="Chọn bộ máy OCR" />
            </SelectTrigger>
            <SelectContent>
              {OCR_ENGINE_OPTIONS.map((engine) => (
                <SelectItem key={engine.value} value={engine.value} className="text-xs">
                  {engine.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center rounded-md border border-border bg-background">
          <Button
            variant="ghost"
            size="icon"
            onClick={onZoomOut}
            disabled={disabled}
            className="size-6 rounded-none text-muted-foreground"
            title="Thu nhỏ"
            aria-label="Thu nhỏ"
          >
            <ZoomOut className="size-3" />
          </Button>
          <span className="px-1.5 font-mono text-[11px] text-muted-foreground w-11 text-center">
            {zoomLevel}%
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={onZoomIn}
            disabled={disabled}
            className="size-6 rounded-none text-muted-foreground"
            title="Phóng to"
            aria-label="Phóng to"
          >
            <ZoomIn className="size-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onZoomReset}
            disabled={disabled}
            className="size-6 rounded-none border-l border-border text-muted-foreground"
            title="Tỷ lệ chuẩn 100%"
            aria-label="Tỷ lệ chuẩn 100%"
          >
            <RotateCcw className="size-3" />
          </Button>
        </div>

        {/* Toggle Boxes */}
        <Button
          variant={showBoxes ? "default" : "outline"}
          size="sm"
          onClick={() => onToggleBoxes(!showBoxes)}
          disabled={disabled}
          className={`h-7 px-2 text-xs gap-1 ${showBoxes ? "bg-primary text-primary-foreground" : ""}`}
          title="Bật/Tắt hiển thị khung bóc tách"
        >
          <Layers className="size-3" />
          <span>Khung</span>
        </Button>

        {/* Filter dropdown */}
        <div className="w-28">
          <Select value={regionFilter} onValueChange={onRegionFilterChange} disabled={disabled}>
            <SelectTrigger sizeVariant="sm" className="h-7 text-xs px-2 w-full">
              <SelectValue placeholder="Tất cả" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả vùng</SelectItem>
              <SelectItem value="table">Bảng biểu</SelectItem>
              <SelectItem value="signature">Dấu / Ký</SelectItem>
              <SelectItem value="text">Văn bản</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
};
