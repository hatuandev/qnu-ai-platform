import {
  CheckSquare,
  FileText,
  Maximize2,
  Minus,
  Plus,
  RotateCcw,
  Sparkles,
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
  isRescanning?: boolean;
  onRescanLayout?: () => void;
}

const REGION_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  header: { bg: "rgba(59, 130, 246, 0.12)", border: "#3b82f6", text: "#1d4ed8", badge: "#2563eb" },
  title: { bg: "rgba(139, 92, 246, 0.14)", border: "#8b5cf6", text: "#6d28d9", badge: "#7c3aed" },
  text: { bg: "rgba(168, 85, 247, 0.10)", border: "#a855f7", text: "#7e22ce", badge: "#9333ea" },
  list: { bg: "rgba(16, 185, 129, 0.12)", border: "#10b981", text: "#047857", badge: "#059669" },
  table: { bg: "rgba(245, 158, 11, 0.14)", border: "#f59e0b", text: "#b45309", badge: "#d97706" },
  signature: {
    bg: "rgba(244, 63, 94, 0.16)",
    border: "#f43f5e",
    text: "#be123c",
    badge: "#e11d48",
  },
  stamp: { bg: "rgba(244, 63, 94, 0.16)", border: "#f43f5e", text: "#be123c", badge: "#e11d48" },
};

const REGION_BADGE_LABELS: Record<string, string> = {
  header: "tiêu đề đầu",
  title: "tiêu đề",
  text: "văn bản",
  list: "danh sách",
  table: "bảng biểu",
  signature: "chữ ký",
  stamp: "con dấu & ký",
};

function getEffectiveType(box: DocumentBoundingBox): string {
  const lbl = (box.label || "").toLowerCase();
  if (["table", "title", "header", "text", "list", "signature", "stamp"].includes(lbl)) {
    return lbl;
  }
  return box.type;
}

function getDisplayBadge(box: DocumentBoundingBox): string {
  const effectiveType = getEffectiveType(box);
  if (REGION_BADGE_LABELS[effectiveType]) {
    return REGION_BADGE_LABELS[effectiveType];
  }
  const clean = (box.label || box.type || "")
    .replace(/[#*`_~|]/g, "")
    .trim()
    .toLowerCase();
  if (!clean || clean.length > 20) {
    return REGION_BADGE_LABELS[box.type] || box.type || "khối";
  }
  return clean;
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
  isRescanning,
  onRescanLayout,
}) => {
  const [zoomLevel, setZoomLevel] = useState<number>(96);
  const [imageError, setImageError] = useState<boolean>(false);

  const filteredBoxes = useMemo(() => {
    return boundingBoxes.filter((box) => {
      if (box.page_number !== currentPage) return false;
      if (selectedFilter === "all") return true;
      const effectiveType = getEffectiveType(box);
      if (selectedFilter === "table") return effectiveType === "table";
      if (selectedFilter === "text")
        return ["text", "header", "title", "list"].includes(effectiveType);
      if (selectedFilter === "stamp") return ["stamp", "signature"].includes(effectiveType);
      return true;
    });
  }, [boundingBoxes, currentPage, selectedFilter]);

  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 10, 160));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 10, 60));
  const handleResetZoom = () => setZoomLevel(96);
  const handleFitPage = () => setZoomLevel(70);

  // Honest image source: real scan URL only. Documents without a rendered
  // page image show the placeholder panel instead of another doc's image.
  const currentImageSrc = imageUrl;

  // Reset a stale image error whenever the viewed page/source changes
  // (React-endorsed adjust-state-during-render pattern, no effect needed).
  const visualKey = `${currentPage}|${imageUrl ?? ""}`;
  const [lastVisualKey, setLastVisualKey] = useState<string>(visualKey);
  if (visualKey !== lastVisualKey) {
    setLastVisualKey(visualKey);
    if (imageError) {
      setImageError(false);
    }
  }

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

          {/* Smart Re-scan Button */}
          {onRescanLayout && (
            <button
              type="button"
              onClick={onRescanLayout}
              disabled={isRescanning}
              className="flex items-center gap-1 text-[11px] font-medium transition-colors cursor-pointer px-2 py-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
              title="Quét lại bố cục thông minh bằng OpenCV (nhận diện con dấu đỏ, chữ ký, bảng biểu)"
            >
              <Sparkles className={`size-3.5 ${isRescanning ? "animate-spin text-primary" : ""}`} />
              <span>{isRescanning ? "Đang quét..." : "Quét lại"}</span>
            </button>
          )}

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
          {currentImageSrc && !imageError ? (
            <img
              src={currentImageSrc}
              alt={`Trang scan ${currentPage}`}
              className="w-full h-auto block select-none pointer-events-none"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="p-12 text-center flex flex-col items-center justify-center gap-3 bg-card min-h-[640px] aspect-[1/1.414] w-full">
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
              const effectiveType = getEffectiveType(box);
              const styleColor = REGION_COLORS[effectiveType] || REGION_COLORS.text;

              const displayBadge = getDisplayBadge(box);

              return (
                <button
                  type="button"
                  key={box.id}
                  onClick={() => onSelectBox?.(isActive ? null : box.id)}
                  title={`${displayBadge.toUpperCase()}: ${box.content_snippet || ""}`}
                  className="absolute transition-all cursor-pointer group p-0 text-left"
                  style={{
                    left: `${box.coordinates.x}%`,
                    top: `${box.coordinates.y}%`,
                    width: `${box.coordinates.width}%`,
                    height: `${box.coordinates.height}%`,
                    border: `${isActive ? "2px" : "1.5px"} solid ${isActive ? "#ec4899" : styleColor.border}`,
                    backgroundColor: isActive ? "rgba(236, 72, 153, 0.18)" : styleColor.bg,
                    zIndex: isActive ? 20 : 10,
                    borderRadius: "2px",
                  }}
                >
                  <span
                    style={{
                      position: "absolute",
                      top: "-10px",
                      left: "4px",
                      background: isActive ? "#ec4899" : styleColor.badge,
                      color: "#ffffff",
                      fontSize: "8px",
                      fontWeight: 700,
                      padding: "1px 5px",
                      borderRadius: "2px",
                      textTransform: "lowercase",
                      lineHeight: 1.15,
                      fontFamily: "Inter, sans-serif",
                      boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
                      maxWidth: "120px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      pointerEvents: "none",
                    }}
                  >
                    {displayBadge}
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
