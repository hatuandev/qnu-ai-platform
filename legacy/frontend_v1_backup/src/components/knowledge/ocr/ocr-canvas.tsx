import { FileText } from "lucide-react";
import type React from "react";
import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { type OcrCanvasProps, REGION_COLORS } from "./types";

// Cấu hình Worker cho PDF.js trong môi trường Vite / Web
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

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
  pdfUrl,
  onPageChange,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(800);
  const [loadedImages, setLoadedImages] = useState<Record<number, boolean>>({});
  const [pageDimensions, setPageDimensions] = useState<
    Record<number, { width: number; height: number; isLandscape: boolean; aspectRatio: number }>
  >({});
  const [pdfError, setPdfError] = useState(false);

  // Đo đạc kích thước thực tế của container để tự động Fit-to-Width (chống che khuất lề trang)
  useEffect(() => {
    if (!containerRef.current) return;
    const updateWidth = () => {
      if (containerRef.current) {
        const padding = window.innerWidth < 768 ? 24 : 48;
        const availableW = Math.max(320, containerRef.current.clientWidth - padding);
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
    if (layoutMode !== "continuous" || !allPages || allPages.length === 0 || !onPageChange) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const pageNum = Number.parseInt(
              entry.target.getAttribute("data-page-number") || "1",
              10
            );
            if (!Number.isNaN(pageNum)) {
              onPageChange(pageNum);
            }
          }
        }
      },
      {
        root: containerRef.current,
        threshold: 0.4,
      }
    );

    const pageElements = containerRef.current?.querySelectorAll("[data-page-number]");
    if (pageElements) {
      for (const el of pageElements) {
        observer.observe(el);
      }
    }

    return () => observer.disconnect();
  }, [layoutMode, allPages, onPageChange]);

  const displayPages =
    layoutMode === "continuous" && allPages && allPages.length > 0
      ? allPages
      : pageData
        ? [pageData]
        : [];

  if (displayPages.length === 0) {
    return (
      <div className="flex-1 overflow-auto p-6 flex items-center justify-center bg-[#18181b] text-zinc-400">
        <div className="text-center py-20">
          <FileText className="size-12 mx-auto mb-2 opacity-30 text-zinc-500" />
          <p className="text-xs">Không có dữ liệu trang tài liệu</p>
        </div>
      </div>
    );
  }

  const shouldUsePdf = Boolean(pdfUrl && !pdfError);

  const renderPageContent = (page: (typeof displayPages)[0]) => {
    const imageUrl = page.imageUrl?.startsWith("/")
      ? page.imageUrl
      : `/api/v1/ocr/studio/page-image/${documentTitle || "demo"}/page_${page.pageNumber}.jpg`;

    const pageRegions = layoutMode === "continuous" ? page.regions : filteredRegions;
    const isLoaded = Boolean(loadedImages[page.pageNumber]);

    // Nhận diện hướng giấy tự động: Landscape (khổ ngang) vs Portrait (khổ dọc)
    const pageDim = pageDimensions[page.pageNumber];
    const naturalW = pageDim?.width ?? page.dimensions?.width ?? 800;
    const naturalH = pageDim?.height ?? page.dimensions?.height ?? 1131;
    const isLandscape = pageDim?.isLandscape ?? naturalW > naturalH;
    const aspectRatio = pageDim?.aspectRatio ?? (isLandscape ? Math.SQRT2 : 1 / Math.SQRT2);

    // Tính toán chiều rộng render vừa vặn với container (Fit-to-Width) có áp dụng zoomLevel
    // Trang ngang tự động tận dụng tối đa containerWidth để không bị che mất cột
    const idealBaseWidth = isLandscape
      ? Math.min(containerWidth, 1200)
      : Math.min(containerWidth, 800);
    const pageRenderWidth = Math.round((idealBaseWidth * zoomLevel) / 100);

    const baseW = isLandscape ? 1131 : 800;
    const baseH = isLandscape ? 800 : 1131;

    return (
      <div
        key={`page-wrapper-${page.pageNumber}`}
        data-page-number={page.pageNumber}
        className="flex flex-col items-center shrink-0 my-4"
        style={{
          width: `${pageRenderWidth}px`,
        }}
      >
        {/* Page Container with Dynamic Aspect-Ratio Matching (Khớp 100% kích thước với Page PDF) */}
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

          {/* Tầng 1: Render PDF thật qua react-pdf HOẶC Fallback ảnh scan */}
          {shouldUsePdf ? (
            <div className="w-full h-full block">
              <Page
                pageNumber={page.pageNumber}
                width={pageRenderWidth}
                renderTextLayer={true}
                renderAnnotationLayer={false}
                className="select-text block"
                onLoadSuccess={(pageObj) => {
                  const ow = pageObj.originalWidth;
                  const oh = pageObj.originalHeight;
                  if (ow > 0 && oh > 0) {
                    setPageDimensions((prev) => ({
                      ...prev,
                      [page.pageNumber]: {
                        width: ow,
                        height: oh,
                        isLandscape: ow > oh,
                        aspectRatio: ow / oh,
                      },
                    }));
                  }
                  setLoadedImages((prev) => ({ ...prev, [page.pageNumber]: true }));
                }}
                onError={() => {
                  setPdfError(true);
                }}
              />
            </div>
          ) : (
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
                setLoadedImages((prev) => ({ ...prev, [page.pageNumber]: true }));
              }}
              onError={(e) => {
                const target = e.currentTarget;
                if (!target.src.includes("/ocr-cache/doc_ts_2026/")) {
                  target.src = `/ocr-cache/doc_ts_2026/page_${page.pageNumber}.jpg`;
                } else {
                  setLoadedImages((prev) => ({ ...prev, [page.pageNumber]: true }));
                }
              }}
            />
          )}

          {/* Tầng 3: Visual Document AI Bounding Boxes Layer */}
          {showBoxes && (
            <div className="absolute inset-0 pointer-events-none z-10">
              {pageRegions.map((region, idx) => {
                const colorStyle = REGION_COLORS[region.type] || REGION_COLORS.text;
                const isSelected = selectedRegion === region;

                // Safe coordinate normalization thích ứng với hướng giấy
                const safeLeft = Math.max(
                  0,
                  Math.min(99, region.left > 100 ? (region.left / baseW) * 100 : region.left)
                );
                const safeTop = Math.max(
                  0,
                  Math.min(99, region.top > 100 ? (region.top / baseH) * 100 : region.top)
                );
                const rawWidth = region.width > 100 ? (region.width / baseW) * 100 : region.width;
                const rawHeight =
                  region.height > 100 ? (region.height / baseH) * 100 : region.height;
                const safeWidth = Math.max(1, Math.min(100 - safeLeft, rawWidth));
                const safeHeight = Math.max(1, Math.min(100 - safeTop, rawHeight));

                const boxKey = `box-${page.pageNumber}-${region.type}-${idx}-${safeTop.toFixed(1)}-${safeLeft.toFixed(1)}`;

                return (
                  <button
                    type="button"
                    key={boxKey}
                    onClick={() => onSelectRegion(region)}
                    aria-label={`Vùng ${region.label}: ${region.text.slice(0, 30)}`}
                    className={`absolute border-[1.5px] transition-all cursor-pointer group text-left p-0 rounded-[2px] pointer-events-auto ${
                      isSelected
                        ? "ring-2 ring-teal-400 ring-offset-1 z-30"
                        : "z-10 hover:ring-1 hover:ring-teal-400/80 hover:brightness-95"
                    }`}
                    style={{
                      top: `${safeTop}%`,
                      left: `${safeLeft}%`,
                      width: `${safeWidth}%`,
                      height: `${safeHeight}%`,
                      borderColor: colorStyle.border,
                      backgroundColor: isSelected ? "rgba(13, 148, 136, 0.18)" : colorStyle.bg,
                    }}
                    title={`${region.label}: ${region.text}`}
                  >
                    {/* Pill Badge Nhãn Chuẩn Mistral Document AI */}
                    <span
                      className="absolute -top-[13px] left-[-1px] px-1 py-0 text-[8px] font-mono font-medium lowercase rounded-t-[2px] rounded-br-[2px] text-white shadow-xs pointer-events-none leading-[13px] h-[13px] z-20 select-none whitespace-nowrap"
                      style={{ backgroundColor: colorStyle.badge }}
                    >
                      {region.type || region.label}
                    </span>
                  </button>
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
      className="flex-1 overflow-auto p-4 md:p-6 bg-[#18181b] relative select-none scroll-smooth"
    >
      <div className="w-fit min-w-full flex flex-col items-center">
        {shouldUsePdf ? (
          <Document
            file={pdfUrl}
            onLoadSuccess={() => setPdfError(false)}
            onError={() => setPdfError(true)}
            loading={null}
            className="w-fit min-w-full flex flex-col items-center"
          >
            {displayPages.map(renderPageContent)}
          </Document>
        ) : (
          displayPages.map(renderPageContent)
        )}
      </div>
    </div>
  );
};
