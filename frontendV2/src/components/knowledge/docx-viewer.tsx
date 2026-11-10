import { renderAsync } from "docx-preview";
import { Download, Loader2, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

export interface DocxViewerProps {
  blob: Blob;
  fileName?: string;
  blobUrl?: string | null;
  className?: string;
}

const ZOOM_STEPS = [0.4, 0.5, 0.6, 0.75, 0.9, 1.0, 1.15, 1.25, 1.5, 1.75, 2.0];

/**
 * Isolated DOCX Viewer with automatic "Fit-to-Width" responsive scaling,
 * manual zoom controls, and seamless full-height scrolling.
 */
export function DocxViewer({
  blob,
  fileName,
  blobUrl,
  className,
}: DocxViewerProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const docxTargetRef = useRef<HTMLDivElement>(null);

  const [isRendering, setIsRendering] = useState(true);
  const [renderError, setRenderError] = useState<string | null>(null);

  const [naturalDimensions, setNaturalDimensions] = useState<{
    width: number;
    height: number;
  } | null>(null);

  const [containerWidth, setContainerWidth] = useState<number>(0);
  const [zoomMode, setZoomMode] = useState<"fit" | "manual">("fit");
  const [manualScale, setManualScale] = useState<number>(1.0);

  // 1. Render docx blob
  useEffect(() => {
    let active = true;
    const target = docxTargetRef.current;
    if (!target) return;

    target.replaceChildren();
    setIsRendering(true);
    setRenderError(null);
    setNaturalDimensions(null);
    setZoomMode("fit");
    // Each render owns its staging node. A late previous render cannot write
    // into the visible target after the user changes documents.
    const staging = document.createElement("div");

    renderAsync(blob, staging, undefined, {
      className: "docx-preview-content",
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: false,
    })
      .then(() => {
        if (!active) return;
        target.replaceChildren(...Array.from(staging.childNodes));

        // Measure natural dimensions of the rendered page layout
        const wrapper = target.querySelector(
          ".docx-preview-content-wrapper",
        ) as HTMLElement | null;
        const pages = Array.from(
          target.querySelectorAll<HTMLElement>("section.docx-preview-content"),
        );
        if (!pages.length)
          throw new Error("Tệp Word không có trang có thể hiển thị.");

        const renderedWidth =
          Math.max(...pages.map((page) => page.offsetWidth)) ||
          wrapper?.offsetWidth ||
          target.scrollWidth ||
          816;

        const renderedHeight =
          wrapper?.offsetHeight || target.scrollHeight || 1056;

        setNaturalDimensions({
          width: renderedWidth,
          height: renderedHeight,
        });
        setIsRendering(false);
      })
      .catch((err) => {
        if (!active) return;
        setIsRendering(false);
        target.replaceChildren();
        setRenderError(
          err instanceof Error
            ? err.message
            : "Không thể hiển thị xem trước tệp Word.",
        );
      });

    return () => {
      active = false;
      if (target) target.innerHTML = "";
    };
  }, [blob]);

  // 2. Observe scroll container size for responsive fit-to-width
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          setContainerWidth(entry.contentRect.width + 32);
        }
      }
    });

    observer.observe(container);
    setContainerWidth(container.clientWidth);

    return () => observer.disconnect();
  }, []);

  // 3. Compute fit-to-width scale and effective scale
  const fitScale = useMemo(() => {
    if (!naturalDimensions || naturalDimensions.width <= 0) return 1.0;
    // Available width minus 32px padding (16px left + 16px right)
    const availableWidth = Math.max(160, containerWidth - 32);
    const fit = availableWidth / naturalDimensions.width;
    // Cap between 0.2 and 1.5
    return Math.min(1.5, Math.max(0.2, fit));
  }, [naturalDimensions, containerWidth]);

  const effectiveScale = zoomMode === "fit" ? fitScale : manualScale;

  // 4. Zoom handlers
  const handleZoomIn = () => {
    setZoomMode("manual");
    const nextStep =
      ZOOM_STEPS.find((s) => s > effectiveScale + 0.05) ||
      Math.min(2.0, effectiveScale + 0.15);
    setManualScale(Number(nextStep.toFixed(2)));
  };

  const handleZoomOut = () => {
    setZoomMode("manual");
    const prevSteps = ZOOM_STEPS.filter((s) => s < effectiveScale - 0.05);
    const prevStep =
      prevSteps.length > 0
        ? prevSteps[prevSteps.length - 1]
        : Math.max(0.3, effectiveScale - 0.15);
    setManualScale(Number(prevStep.toFixed(2)));
  };

  const handleResetFit = () => {
    setZoomMode("fit");
  };

  return (
    <div
      className={cn(
        "flex flex-col h-full w-full overflow-hidden bg-muted/20",
        className,
      )}
    >
      {/* Scoped CSS to eliminate default docx-preview wrapper padding & gray background */}
      <style>{`
        .docx-viewer-scope .docx-preview-content-wrapper {
          background: transparent !important;
          padding: 0 !important;
          display: block !important;
          width: max-content;
        }
        .docx-viewer-scope section.docx-preview-content {
          margin-left: auto !important;
          margin-right: auto !important;
          margin-bottom: 20px !important;
          box-shadow: 0 1px 4px 0 rgb(0 0 0 / 0.12), 0 1px 2px -1px rgb(0 0 0 / 0.08) !important;
          border: 1px solid var(--border) !important;
          border-radius: 4px !important;
          background-color: #ffffff !important;
        }
      `}</style>

      {/* Top Controls Toolbar */}
      <div className="h-9 border-b border-border/60 px-3 bg-muted/40 flex items-center justify-between text-xs shrink-0">
        <div className="flex items-center gap-1.5 text-muted-foreground font-medium">
          <span className="text-foreground">Tệp gốc · DOCX</span>
        </div>

        {/* Zoom & Action Controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleZoomOut}
            disabled={effectiveScale <= 0.35}
            className="size-6 p-0 text-muted-foreground hover:text-foreground"
            title="Thu nhỏ (-)"
            aria-label="Thu nhỏ"
          >
            <ZoomOut className="size-3" />
          </Button>

          <button
            type="button"
            onClick={handleResetFit}
            className={cn(
              "text-[11px] font-medium px-2 py-0.5 rounded transition-colors cursor-pointer",
              zoomMode === "fit"
                ? "bg-primary/10 text-primary font-semibold"
                : "text-muted-foreground hover:text-foreground hover:bg-muted",
            )}
            title="Bấm để trở về Vừa chiều ngang"
          >
            {zoomMode === "fit"
              ? "Vừa ngang"
              : `${Math.round(effectiveScale * 100)}%`}
          </button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleZoomIn}
            disabled={effectiveScale >= 2.0}
            className="size-6 p-0 text-muted-foreground hover:text-foreground"
            title="Phóng to (+)"
            aria-label="Phóng to"
          >
            <ZoomIn className="size-3" />
          </Button>

          {zoomMode !== "fit" && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetFit}
              className="size-6 p-0 text-muted-foreground hover:text-foreground ml-0.5"
              title="Đặt lại vừa trang"
              aria-label="Đặt lại vừa trang"
            >
              <RotateCcw className="size-3" />
            </Button>
          )}

          {blobUrl && (
            <>
              <Separator orientation="vertical" className="h-3.5 mx-1" />
              <a
                href={blobUrl}
                download={fileName || "tai_lieu.docx"}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] text-muted-foreground hover:text-primary transition-colors rounded hover:bg-muted"
                title="Tải tệp gốc về máy"
              >
                <Download className="size-3" />
                <span className="hidden sm:inline">Tải về</span>
              </a>
            </>
          )}
        </div>
      </div>

      {/* Main Scrollable Viewport */}
      <div
        ref={scrollContainerRef}
        className="relative flex-1 overflow-auto p-4 min-h-0 min-w-0"
      >
        {isRendering && (
          <div className="py-24 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-5 animate-spin text-primary" />
            <span>Đang chuẩn bị xem trước tài liệu Word...</span>
          </div>
        )}

        {renderError && (
          <div className="p-6 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive text-xs max-w-md my-8 text-center space-y-3">
            <p className="font-semibold text-sm">
              Không thể hiển thị xem trước trực tiếp:
            </p>
            <p className="text-muted-foreground">{renderError}</p>
            {blobUrl && (
              <a
                href={blobUrl}
                download={fileName || "tai_lieu.docx"}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-card border border-border/70 text-primary font-medium hover:bg-muted transition-colors shadow-2xs"
              >
                <Download className="size-3.5" />
                <span>Tải tệp về máy để xem</span>
              </a>
            )}
          </div>
        )}

        {/* Scaled paper canvas */}
        <div
          className={cn("relative mx-auto")}
          style={{
            width: naturalDimensions
              ? `${naturalDimensions.width * effectiveScale}px`
              : "max-content",
            height: naturalDimensions
              ? `${naturalDimensions.height * effectiveScale}px`
              : 0,
            visibility: isRendering || renderError ? "hidden" : "visible",
          }}
        >
          <div
            className="docx-viewer-scope origin-top-left"
            style={{
              width: naturalDimensions
                ? `${naturalDimensions.width}px`
                : "max-content",
              transform: `scale(${effectiveScale})`,
            }}
          >
            <div ref={docxTargetRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
