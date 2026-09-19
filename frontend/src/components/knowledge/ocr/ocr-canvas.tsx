import { FileText } from "lucide-react";
import type React from "react";
import { type OcrCanvasProps, REGION_COLORS } from "./types";

export const OcrCanvas: React.FC<OcrCanvasProps> = ({
  pageData,
  zoomLevel,
  showBoxes,
  filteredRegions,
  selectedRegion,
  onSelectRegion,
  documentTitle,
}) => {
  if (!pageData) {
    return (
      <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-muted/20 relative">
        <div className="text-center py-20 text-muted-foreground">
          <FileText className="size-12 mx-auto mb-2 opacity-30" />
          <p className="text-xs">Không có dữ liệu trang</p>
        </div>
      </div>
    );
  }

  const imageUrl = pageData.imageUrl?.startsWith("/")
    ? pageData.imageUrl
    : `/api/v1/ocr/studio/page-image/${documentTitle || "demo"}/page_${pageData.pageNumber}.jpg`;

  return (
    <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-muted/20 relative">
      <div
        className="relative bg-white shadow-lg border border-border rounded-sm transition-transform duration-100 select-none origin-top"
        style={{
          width: `${(800 * zoomLevel) / 100}px`,
          height: `${(1131 * zoomLevel) / 100}px`,
        }}
      >
        {/* Page Image */}
        <img
          src={imageUrl}
          alt={`Trang ${pageData.pageNumber}`}
          className="w-full h-full object-contain pointer-events-none"
          onError={(e) => {
            const target = e.currentTarget;
            if (!target.src.includes("/ocr-cache/doc_ts_2026/")) {
              target.src = `/ocr-cache/doc_ts_2026/page_${pageData.pageNumber}.jpg`;
            }
          }}
        />

        {/* Bounding Boxes Layer */}
        {showBoxes &&
          filteredRegions.map((region, idx) => {
            const colorStyle = REGION_COLORS[region.type] || REGION_COLORS.text;
            const isSelected = selectedRegion === region;
            const boxKey = `box-${region.type}-${idx}-${region.top}-${region.left}`;
            return (
              <button
                type="button"
                key={boxKey}
                onClick={() => onSelectRegion(region)}
                aria-label={`Vùng ${region.label}: ${region.text.slice(0, 30)}`}
                className={`absolute border-2 transition-all cursor-pointer group text-left p-0 ${
                  isSelected ? "ring-2 ring-primary ring-offset-1 z-20" : "z-10"
                }`}
                style={{
                  top: `${region.top}%`,
                  left: `${region.left}%`,
                  width: `${region.width}%`,
                  height: `${region.height}%`,
                  backgroundColor: colorStyle.bg,
                  borderColor: colorStyle.border,
                }}
                title={`${region.label}: ${region.text}`}
              >
                {/* Tag Label */}
                <div
                  className="absolute -top-5 left-0 px-1 py-0.5 text-[10px] font-bold rounded-t text-white whitespace-nowrap opacity-90 group-hover:opacity-100 shadow-xs"
                  style={{ backgroundColor: colorStyle.border }}
                >
                  {region.label}
                </div>
              </button>
            );
          })}
      </div>
    </div>
  );
};
