import { ChevronLeft, ChevronRight, FileText } from "lucide-react";
import type React from "react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { type OcrCanvasProps, REGION_COLORS } from "./types";

export const OcrCanvas: React.FC<OcrCanvasProps> = ({
  pageData,
  allPages,
  layoutMode = "continuous",
  zoomLevel,
  showBoxes,
  filteredRegions,
  selectedRegion,
  onSelectRegion,
  documentTitle,
  onPageChange,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(800);
  const [loadedImages, setLoadedImages] = useState<Record<number, boolean>>({});
  const [pageDimensions, setPageDimensions] = useState<
    Record<
      number,
      {
        width: number;
        height: number;
        isLandscape: boolean;
        aspectRatio: number;
      }
    >
  >({});

  // Fit-to-Width dynamic calculation
  useEffect(() => {
    if (!containerRef.current) return;
    const updateWidth = () => {
      if (containerRef.current) {
        const padding = window.innerWidth < 768 ? 24 : 48;
        const availableW = Math.max(
          320,
          containerRef.current.clientWidth - padding,
        );
        setContainerWidth(availableW);
      }
    };
    updateWidth();
    const resizeObserver = new ResizeObserver(updateWidth);
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // IntersectionObserver to sync current page when scrolling in continuous mode
  useEffect(() => {
    if (
      layoutMode !== "continuous" ||
      !allPages ||
      allPages.length === 0 ||
      !onPageChange
    ) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const pageNum = Number.parseInt(
              entry.target.getAttribute("data-page-number") || "1",
              10,
            );
            if (!Number.isNaN(pageNum)) {
              onPageChange(pageNum);
            }
          }
        }
      },
      {
        root: containerRef.current,
        threshold: 0.35,
      },
    );

    const pageElements =
      containerRef.current?.querySelectorAll("[data-page-number]");
    if (pageElements) {
      for (const el of pageElements) {
        observer.observe(el);
      }
    }

    return () => observer.disconnect();
  }, [layoutMode, allPages, onPageChange]);

  const activePage =
    pageData || (allPages && allPages.length > 0 ? allPages[0] : null);

  const displayPages =
    layoutMode === "continuous" && allPages && allPages.length > 0
      ? allPages
      : activePage
        ? [activePage]
        : [];

  const totalPagesCount = allPages?.length || (pageData ? 1 : 0);

  if (displayPages.length === 0) {
    return (
      <div className="flex-1 overflow-auto p-6 flex items-center justify-center bg-zinc-950 text-zinc-400">
        <div className="text-center py-20">
          <FileText className="size-12 mx-auto mb-2 opacity-30 text-zinc-500" />
          <p className="text-xs">Không có dữ liệu trang tài liệu</p>
        </div>
      </div>
    );
  }

  const renderPageContent = (page: (typeof displayPages)[0]) => {
    const imageUrl =
      page.imageUrl ||
      `/platform/v1alpha1/knowledge/documents/${documentTitle || "demo"}/pages/${page.pageNumber}/image`;

    const pageRegions =
      layoutMode === "continuous" ? page.regions : filteredRegions;
    const isLoaded = Boolean(loadedImages[page.pageNumber]);

    // Nhận diện hướng giấy tự động: Landscape (khổ ngang) vs Portrait (khổ dọc)
    const pageDim = pageDimensions[page.pageNumber];
    const naturalW = pageDim?.width ?? page.dimensions?.width ?? 800;
    const naturalH = pageDim?.height ?? page.dimensions?.height ?? 1131;
    const isLandscape = pageDim?.isLandscape ?? naturalW > naturalH;
    const aspectRatio =
      pageDim?.aspectRatio ??
      (naturalW > 0 && naturalH > 0 ? naturalW / naturalH : 1);

    const idealBaseWidth = isLandscape
      ? Math.min(containerWidth, 1200)
      : Math.min(containerWidth, 840);
    const pageRenderWidth = Math.round((idealBaseWidth * zoomLevel) / 100);

    return (
      <div
        key={`page-wrapper-${page.pageNumber}`}
        data-page-number={page.pageNumber}
        className="flex flex-col items-center shrink-0 my-3 sm:my-5 relative"
        style={{
          width: `${pageRenderWidth}px`,
        }}
      >
        {/* Page Container with Dynamic Aspect-Ratio Matching */}
        <div
          id={`page-canvas-${page.pageNumber}`}
          className="relative bg-white shadow-2xl rounded-xs border border-zinc-700/60 transition-transform select-none overflow-hidden"
          style={{
            width: `${pageRenderWidth}px`,
            aspectRatio: `${aspectRatio}`,
          }}
        >
          {/* Shimmer Placeholder khi trang đang tải */}
          {!isLoaded && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-zinc-100 dark:bg-zinc-900/60 animate-pulse z-0">
              <FileText className="size-8 text-zinc-400/50 mb-2 animate-bounce" />
              <span className="text-[11px] font-medium text-zinc-400 font-mono">
                Đang nạp trang {page.pageNumber}...
              </span>
            </div>
          )}

          {/* Tầng 1: Render trực tiếp ảnh trang phân giải cao từ Backend */}
          <img
            src={imageUrl}
            alt={`Trang ${page.pageNumber}`}
            className={`w-full h-full object-contain block rounded-xs select-none pointer-events-none transition-opacity duration-300 ${
              isLoaded ? "opacity-100" : "opacity-0"
            }`}
            onLoad={(e) => {
              const nw = e.currentTarget.naturalWidth;
              const nh = e.currentTarget.naturalHeight;
              if (nw > 0 && nh > 0) {
                setPageDimensions((prev) => ({
                  ...prev,
                  [page.pageNumber]: {
                    width: nw,
                    height: nh,
                    isLandscape: nw > nh,
                    aspectRatio: nw / nh,
                  },
                }));
              }
              setLoadedImages((prev) => ({
                ...prev,
                [page.pageNumber]: true,
              }));
            }}
            onError={() => {
              setLoadedImages((prev) => ({
                ...prev,
                [page.pageNumber]: true,
              }));
            }}
          />

          {/* Tầng 2: Visual Document AI Bounding Boxes Layer */}
          {showBoxes && (
            <div className="absolute inset-0 pointer-events-none z-10">
              {pageRegions.map((region) => {
                const colorStyle =
                  REGION_COLORS[region.type] || REGION_COLORS.text;
                const isSelected = selectedRegion === region;

                // Mapper supplies percentages; never infer coordinate units by magnitude.
                const safeLeft = Math.max(0, Math.min(100, region.left));
                const safeTop = Math.max(0, Math.min(100, region.top));
                const safeWidth = Math.max(
                  0,
                  Math.min(100 - safeLeft, region.width),
                );
                const safeHeight = Math.max(
                  0,
                  Math.min(100 - safeTop, region.height),
                );

                const boxKey =
                  region.id ||
                  `box-${page.pageNumber}-${region.type}-${safeTop}-${safeLeft}`;

                return (
                  <Button
                    variant="ghost"
                    type="button"
                    key={boxKey}
                    onClick={() => onSelectRegion(region)}
                    aria-label={`Vùng ${region.label}: ${region.text.slice(0, 30)}`}
                    className={`absolute border-[1.5px] transition-all cursor-pointer group text-left p-0 rounded-[2px] pointer-events-auto ${
                      isSelected
                        ? "ring-2 ring-primary ring-offset-1 z-30 shadow-md brightness-105"
                        : "z-10 hover:ring-1 hover:ring-primary/80 hover:brightness-95"
                    }`}
                    style={{
                      top: `${safeTop}%`,
                      left: `${safeLeft}%`,
                      width: `${safeWidth}%`,
                      height: `${safeHeight}%`,
                      borderColor: colorStyle.border,
                      backgroundColor: isSelected
                        ? "rgba(13, 148, 136, 0.18)"
                        : colorStyle.bg,
                    }}
                    title={`${region.label}: ${region.text}`}
                  >
                    {/* Pill Badge Document AI */}
                    <span
                      className="absolute -top-[13px] left-[-1px] px-1 py-0 text-[8px] font-mono font-medium lowercase rounded-t-[2px] rounded-br-[2px] text-white shadow-xs pointer-events-none leading-[13px] h-[13px] z-20 select-none whitespace-nowrap"
                      style={{ backgroundColor: colorStyle.badge }}
                    >
                      {region.type || region.label}
                    </span>
                  </Button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-auto p-4 md:p-6 bg-zinc-950 relative select-none scroll-smooth flex flex-col items-center justify-start min-h-0"
    >
      {/* Document Pages Container */}
      <div className="w-fit min-w-full flex flex-col items-center">
        {displayPages.map(renderPageContent)}
      </div>

      {/* Floating Single Page Navigation Controls */}
      {layoutMode === "single" && activePage && totalPagesCount > 1 && (
        <>
          {/* Floating Prev Button */}
          <Button
            variant="ghost"
            type="button"
            onClick={() => onPageChange?.(activePage.pageNumber - 1)}
            disabled={activePage.pageNumber <= 1}
            className="absolute left-3 top-1/2 -translate-y-1/2 size-9 rounded-full bg-zinc-900/80 hover:bg-zinc-800 text-zinc-200 border border-zinc-700/80 shadow-lg flex items-center justify-center disabled:opacity-30 disabled:pointer-events-none cursor-pointer transition-all hover:scale-105 active:scale-95 z-20 backdrop-blur-xs"
            title="Trang trước (Phím J hoặc ←)"
            aria-label="Trang trước"
          >
            <ChevronLeft className="size-4.5" />
          </Button>

          {/* Floating Next Button */}
          <Button
            variant="ghost"
            type="button"
            onClick={() => onPageChange?.(activePage.pageNumber + 1)}
            disabled={activePage.pageNumber >= totalPagesCount}
            className="absolute right-3 top-1/2 -translate-y-1/2 size-9 rounded-full bg-zinc-900/80 hover:bg-zinc-800 text-zinc-200 border border-zinc-700/80 shadow-lg flex items-center justify-center disabled:opacity-30 disabled:pointer-events-none cursor-pointer transition-all hover:scale-105 active:scale-95 z-20 backdrop-blur-xs"
            title="Trang sau (Phím K hoặc →)"
            aria-label="Trang sau"
          >
            <ChevronRight className="size-4.5" />
          </Button>

          {/* Floating Bottom Page Indicator Pill */}
          <div className="sticky bottom-3 mx-auto px-3 py-1 rounded-full bg-zinc-900/90 border border-zinc-700/80 shadow-md text-zinc-200 text-xs font-mono font-medium flex items-center gap-2 z-20 backdrop-blur-xs">
            <span>Trang {activePage.pageNumber}</span>
            <span className="text-zinc-500">/</span>
            <span>{totalPagesCount}</span>
          </div>
        </>
      )}
    </div>
  );
};
