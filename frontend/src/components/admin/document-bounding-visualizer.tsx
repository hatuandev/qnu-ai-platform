import {
  CheckSquare,
  FileText,
  Maximize2,
  Minus,
  Plus,
  RotateCcw,
  Square,
  ZoomIn,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import type { DocumentBoundingBox } from "../../services/api-client";
import { Button } from "../ui/button";

export interface DocumentBoundingVisualizerProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  boundingBoxes: DocumentBoundingBox[];
  selectedFilter: "all" | "table" | "text" | "stamp";
  onFilterChange: (filter: "all" | "table" | "text" | "stamp") => void;
  showBoxes: boolean;
  onToggleShowBoxes: (show: boolean) => void;
  activeBoxId?: string | null;
  onSelectBox?: (boxId: string | null) => void;
  imageUrl?: string;
}

export const DocumentBoundingVisualizer: React.FC<DocumentBoundingVisualizerProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  boundingBoxes,
  selectedFilter,
  onFilterChange,
  showBoxes,
  onToggleShowBoxes,
  activeBoxId,
  onSelectBox,
  imageUrl,
}) => {
  const [zoomLevel, setZoomLevel] = useState<number>(96);
  const [imageError, setImageError] = useState<boolean>(false);

  const filteredBoxes = useMemo(() => {
    return boundingBoxes.filter((box) => {
      if (box.page_number !== currentPage) return false;
      if (selectedFilter === "all") return true;
      if (selectedFilter === "table") return box.type === "table";
      if (selectedFilter === "text") return box.type === "text" || box.type === "header";
      if (selectedFilter === "stamp") return box.type === "stamp";
      return true;
    });
  }, [boundingBoxes, currentPage, selectedFilter]);

  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 10, 160));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 10, 60));
  const handleResetZoom = () => setZoomLevel(96);
  const handleFitPage = () => setZoomLevel(70);

  const currentImageSrc = imageUrl || `/ocr-cache/doc_ts_2026/page_${currentPage}.jpg`;

  return (
    <div className="flex flex-col h-full bg-muted/20 border-r border-border select-none">
      {/* Visualizer Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-card border-b border-border/70 text-xs shrink-0">
        {/* Filter Pills */}
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground font-medium mr-1 text-[11px]">Lọc:</span>
          <button
            type="button"
            onClick={() => onFilterChange("all")}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
              selectedFilter === "all"
                ? "bg-foreground text-background font-semibold"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            Tất cả
          </button>
          <button
            type="button"
            onClick={() => onFilterChange("table")}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium flex items-center gap-1 transition-colors ${
              selectedFilter === "table"
                ? "bg-amber-600 text-white font-semibold"
                : "bg-amber-500/10 text-amber-600 hover:bg-amber-500/20"
            }`}
          >
            <span className="size-1.5 rounded-full bg-amber-500 inline-block" />
            Bảng
          </button>
          <button
            type="button"
            onClick={() => onFilterChange("text")}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium flex items-center gap-1 transition-colors ${
              selectedFilter === "text"
                ? "bg-purple-600 text-white font-semibold"
                : "bg-purple-500/10 text-purple-600 hover:bg-purple-500/20"
            }`}
          >
            <span className="size-1.5 rounded-full bg-purple-500 inline-block" />
            Văn bản
          </button>
          <button
            type="button"
            onClick={() => onFilterChange("stamp")}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium flex items-center gap-1 transition-colors ${
              selectedFilter === "stamp"
                ? "bg-rose-600 text-white font-semibold"
                : "bg-rose-500/10 text-rose-600 hover:bg-rose-500/20"
            }`}
          >
            <span className="size-1.5 rounded-full bg-rose-500 inline-block" />
            Dấu & Ký
          </button>
        </div>

        {/* View Controls: Toggle Boxes, Zoom Slider */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onToggleShowBoxes(!showBoxes)}
            className="flex items-center gap-1 text-[11px] font-medium text-foreground hover:text-primary transition-colors cursor-pointer"
          >
            {showBoxes ? (
              <CheckSquare className="size-3.5 text-primary" />
            ) : (
              <Square className="size-3.5 text-muted-foreground" />
            )}
            <span>Khung</span>
          </button>

          <div className="h-3 w-px bg-border/80 mx-1" />

          <div className="flex items-center gap-1 bg-muted/60 rounded px-1 py-0.5">
            <Button
              variant="ghost"
              size="icon"
              className="size-5 h-5 w-5 p-0"
              onClick={handleZoomOut}
              title="Thu nhỏ (-10%)"
            >
              <Minus className="size-3" />
            </Button>
            <span className="font-mono text-[11px] min-w-8 text-center">{zoomLevel}%</span>
            <Button
              variant="ghost"
              size="icon"
              className="size-5 h-5 w-5 p-0"
              onClick={handleZoomIn}
              title="Phóng to (+10%)"
            >
              <Plus className="size-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="size-5 h-5 w-5 p-0"
              onClick={handleResetZoom}
              title="Đặt lại 100%"
            >
              <RotateCcw className="size-3" />
            </Button>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleFitPage}
            className="h-6 px-1.5 text-[11px] gap-1"
            title="Vừa trang"
          >
            <ZoomIn className="size-3" />
            <span>Vừa trang</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleResetZoom}
            className="h-6 px-1.5 text-[11px] gap-1"
            title="Toàn màn hình"
          >
            <Maximize2 className="size-3" />
            <span>Mở rộng</span>
          </Button>
        </div>
      </div>

      {/* Document View Canvas Area */}
      <div className="flex-1 overflow-auto p-4 flex justify-center items-start">
        <div
          className="relative bg-white shadow-2xl rounded-sm overflow-hidden transition-all select-none border border-border/80"
          style={{
            width: `${zoomLevel}%`,
            maxWidth: "880px",
            minWidth: "320px",
          }}
        >
          {/* Real High-Fidelity Scanned Document Page Image */}
          {!imageError ? (
            <img
              src={currentImageSrc}
              alt={`Trang scan ${currentPage}`}
              className="w-full h-auto block select-none pointer-events-none"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="p-12 text-center flex flex-col items-center justify-center gap-3 bg-card min-h-[500px]">
              <FileText className="size-12 text-primary/60" />
              <p className="text-sm font-semibold text-foreground">
                Tài liệu số hóa — Trang {currentPage} / {totalPages}
              </p>
              <p className="text-xs text-muted-foreground max-w-sm leading-relaxed">
                Đang đối soát trực quan trang số {currentPage}. Vui lòng xem văn bản và bảng biểu
                bóc tách ở cột Markdown bên phải.
              </p>
            </div>
          )}

          {/* Overlaid Visual Bounding Boxes */}
          {showBoxes &&
            filteredBoxes.map((box) => {
              const isActive = activeBoxId === box.id;
              const isTable = box.type === "table";
              const isStamp = box.type === "stamp";

              let borderColor = "border-purple-600 bg-purple-500/10 text-purple-700";
              let badgeBg = "bg-purple-600 text-white";

              if (isTable) {
                borderColor = "border-amber-500 bg-amber-500/15 text-amber-800";
                badgeBg = "bg-amber-600 text-white";
              } else if (isStamp) {
                borderColor = "border-rose-600 bg-rose-500/15 text-rose-800";
                badgeBg = "bg-rose-600 text-white";
              }

              return (
                <button
                  type="button"
                  key={box.id}
                  onClick={() => onSelectBox?.(isActive ? null : box.id)}
                  title={`${box.label.toUpperCase()}: ${box.content_snippet || ""}`}
                  className={`absolute border-2 transition-all cursor-pointer group p-0 text-left ${borderColor} ${
                    isActive ? "ring-2 ring-primary ring-offset-1 z-20" : "z-10"
                  }`}
                  style={{
                    left: `${box.coordinates.x}%`,
                    top: `${box.coordinates.y}%`,
                    width: `${box.coordinates.width}%`,
                    height: `${box.coordinates.height}%`,
                  }}
                >
                  <span
                    className={`absolute -top-3 left-1 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded-xs uppercase tracking-wider shadow-sm ${badgeBg}`}
                  >
                    {box.label}
                  </span>
                </button>
              );
            })}
        </div>
      </div>

      {/* Page Navigation Footer */}
      <div className="flex items-center justify-between px-4 py-2 bg-card border-t border-border text-xs text-muted-foreground shrink-0">
        <span className="text-[11px]">Định dạng: Chuẩn BGDĐT / Nghị định 30</span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-6 w-6 p-0 text-xs"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
          >
            &lt;
          </Button>
          <span className="font-medium text-foreground text-[11px]">
            Trang {currentPage} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-6 w-6 p-0 text-xs"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
          >
            &gt;
          </Button>
        </div>
        <span className="text-[11px]">Độ phân giải: 300 DPI</span>
      </div>
    </div>
  );
};
