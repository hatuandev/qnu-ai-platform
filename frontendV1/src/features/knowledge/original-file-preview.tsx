import { AlertCircle, FileText, Loader2, RefreshCw } from "lucide-react";
import { Component, type ReactNode, useEffect, useRef, useState } from "react";
import { Document as PdfDocument, Page as PdfPage, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import { Button } from "@/components/ui/button";

if (typeof window !== "undefined") {
  try {
    pdfjs.GlobalWorkerOptions.workerSrc = new URL(
      "/pdf.worker.min.mjs",
      window.location.origin,
    ).toString();
  } catch {
    pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
  }
}

export type OriginalPreviewZoomMode = "fit-width" | "fit-page" | "custom";

/**
 * Sanitizes the DOM tree produced by `docx-preview` to:
 * 1. Block any external network requests (img/image src, link, script, iframe, CSS url()).
 * 2. Scope generated <style> rules inside `[data-docx-scope="true"]` so they cannot leak globally.
 */
export function sanitizeDocxPreviewContainer(container: HTMLElement): {
  blockedExternalCount: number;
} {
  let blockedExternalCount = 0;

  // 1. Remove active/external resource tags completely
  const forbiddenTags = container.querySelectorAll(
    "script, iframe, frame, object, embed, link, meta, base",
  );
  for (const node of Array.from(forbiddenTags)) {
    node.remove();
    blockedExternalCount += 1;
  }

  // 2. Inspect media elements for external URLs (only allow blob: or data:)
  const mediaNodes = container.querySelectorAll(
    "img, image, audio, video, source, track",
  );
  for (const node of Array.from(mediaNodes)) {
    for (const attr of ["src", "href", "xlink:href", "srcset"]) {
      const val = node.getAttribute(attr)?.trim();
      if (!val) continue;
      const isSafeLocal =
        val.startsWith("data:") ||
        val.startsWith("blob:") ||
        val.startsWith("#");
      if (!isSafeLocal) {
        node.removeAttribute(attr);
        node.setAttribute("data-blocked-external-resource", "true");
        blockedExternalCount += 1;
      }
    }
  }

  // 3. Sanitize anchor links
  const anchors = container.querySelectorAll("a[href]");
  for (const anchor of Array.from(anchors)) {
    const href = anchor.getAttribute("href")?.trim() ?? "";
    const lower = href.toLowerCase();
    if (
      lower.startsWith("javascript:") ||
      lower.startsWith("vbscript:") ||
      lower.startsWith("data:")
    ) {
      anchor.removeAttribute("href");
      blockedExternalCount += 1;
    } else if (!href.startsWith("#")) {
      anchor.setAttribute("rel", "noopener noreferrer");
      anchor.setAttribute("target", "_blank");
    }
  }

  // 4. Strip external url(...) from inline styles and <style> elements
  const externalCssUrlPattern =
    /url\(\s*(['"]?)\s*(?:https?:|ftp:|\/\/)[^)]*\1\s*\)/gi;

  const styledNodes = container.querySelectorAll("[style]");
  for (const node of Array.from(styledNodes)) {
    const styleVal = node.getAttribute("style");
    if (styleVal && externalCssUrlPattern.test(styleVal)) {
      externalCssUrlPattern.lastIndex = 0;
      node.setAttribute(
        "style",
        styleVal.replace(externalCssUrlPattern, "none"),
      );
      blockedExternalCount += 1;
    }
  }

  const styleTags = container.querySelectorAll("style");
  for (const styleTag of Array.from(styleTags)) {
    const cssText = styleTag.textContent ?? "";
    let sanitizedCss = cssText;
    if (externalCssUrlPattern.test(sanitizedCss)) {
      externalCssUrlPattern.lastIndex = 0;
      sanitizedCss = sanitizedCss.replace(externalCssUrlPattern, "none");
      blockedExternalCount += 1;
    }
    // Prevent global body/html selector leakage from docx-preview styles
    sanitizedCss = sanitizedCss.replace(
      /(^|\}|\s)(body|html)(?=\s*\{)/g,
      "$1.qnu-docx-preview-wrapper",
    );
    if (sanitizedCss !== cssText) {
      styleTag.textContent = sanitizedCss;
    }
  }

  return { blockedExternalCount };
}

export interface DocxOriginalViewerProps {
  blob: Blob;
  revisionKey: string;
  zoomPercent: number;
  zoomMode: OriginalPreviewZoomMode;
}

export function DocxOriginalViewer({
  blob,
  revisionKey,
  zoomPercent,
  zoomMode,
}: DocxOriginalViewerProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const renderTargetRef = useRef<HTMLDivElement>(null);
  const [isRendering, setIsRendering] = useState(true);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    void revisionKey;
    void retryCount;
    const container = renderTargetRef.current;
    if (!container || !blob) return;

    let cancelled = false;
    container.innerHTML = "";
    setIsRendering(true);
    setRenderError(null);

    (async () => {
      try {
        const docxPreview = await import("docx-preview");
        if (cancelled || !renderTargetRef.current) return;

        await docxPreview.renderAsync(
          blob,
          renderTargetRef.current,
          undefined,
          {
            className: "qnu-docx-preview",
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            ignoreFonts: false,
            breakPages: true,
            renderHeaders: true,
            renderFooters: true,
            renderFootnotes: true,
            renderEndnotes: true,
            renderAltChunks: false,
            useBase64URL: true,
          },
        );

        if (cancelled || !renderTargetRef.current) {
          if (renderTargetRef.current) {
            renderTargetRef.current.innerHTML = "";
          }
          return;
        }

        sanitizeDocxPreviewContainer(renderTargetRef.current);
        setIsRendering(false);
        if (scrollContainerRef.current) {
          scrollContainerRef.current.scrollTop = 0;
        }
      } catch (err: unknown) {
        if (cancelled) return;
        setIsRendering(false);
        setRenderError(
          err instanceof Error
            ? err.message
            : "Không thể hiển thị trực tiếp tệp Word (.docx) này.",
        );
      }
    })();

    return () => {
      cancelled = true;
      if (renderTargetRef.current) {
        renderTargetRef.current.innerHTML = "";
      }
    };
  }, [blob, revisionKey, retryCount]);

  const effectiveScale =
    zoomMode === "custom"
      ? Math.max(0.5, Math.min(2.5, zoomPercent / 100))
      : zoomMode === "fit-page"
        ? 0.85
        : 1;

  return (
    <div
      className="flex h-full w-full flex-col overflow-hidden bg-muted/30"
      data-testid="docx-original-viewer"
    >
      {/* Independent scroll viewport */}
      <div
        ref={scrollContainerRef}
        className="relative flex-1 overflow-auto p-3 sm:p-5"
        data-testid="docx-original-scroll-container"
      >
        {isRendering && (
          <div className="flex flex-col items-center justify-center gap-2.5 py-16 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span className="text-xs font-medium">
              Đang dựng nội dung tệp Word (.docx)...
            </span>
          </div>
        )}

        {renderError && !isRendering && (
          <div
            role="alert"
            className="mx-auto flex max-w-md flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-background p-6 text-center shadow-xs"
          >
            <AlertCircle className="h-8 w-8 text-destructive" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">
                Không thể hiển thị tệp Word (.docx)
              </p>
              <p className="text-xs text-muted-foreground">{renderError}</p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setRetryCount((c) => c + 1)}
              className="gap-1.5 text-xs"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Thử lại
            </Button>
          </div>
        )}

        {/* Scoped CSS & isolated DOM container for docx-preview */}
        <div
          data-docx-scope="true"
          className="qnu-docx-preview-scope mx-auto flex justify-center"
          style={{
            isolation: "isolate",
            display: renderError ? "none" : "flex",
          }}
        >
          <style>{`
            .qnu-docx-preview-scope .qnu-docx-preview-wrapper {
              background: transparent !important;
              padding: 0 !important;
              display: flex;
              flex-direction: column;
              align-items: center;
              gap: 1rem;
            }
            .qnu-docx-preview-scope section.qnu-docx-preview {
              box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.12), 0 1px 2px -1px rgb(0 0 0 / 0.1) !important;
              border-radius: 4px;
              margin-bottom: 0.5rem !important;
              max-width: 100%;
              overflow-x: auto;
            }
          `}</style>
          <div
            ref={renderTargetRef}
            data-testid="docx-original-render-target"
            style={{
              transform:
                effectiveScale !== 1 ? `scale(${effectiveScale})` : undefined,
              transformOrigin: "top center",
            }}
          />
        </div>
      </div>
    </div>
  );
}

interface PdfErrorBoundaryProps {
  children: ReactNode;
  fallback: (error: Error) => ReactNode;
}

interface PdfErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class PdfViewerErrorBoundary extends Component<
  PdfErrorBoundaryProps,
  PdfErrorBoundaryState
> {
  constructor(props: PdfErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): PdfErrorBoundaryState {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error) {
    console.warn("Lỗi dựng PDF gốc qua react-pdf:", error);
  }

  override render() {
    if (this.state.hasError && this.state.error) {
      return this.props.fallback(this.state.error);
    }
    return this.props.children;
  }
}

export interface PdfOriginalViewerProps {
  blob?: Blob | null;
  blobUrl?: string | null;
  revisionKey: string;
  pageNumber: number;
  onPageChange: (page: number) => void;
  onTotalPagesDetected?: (numPages: number) => void;
  zoomPercent: number;
  zoomMode: OriginalPreviewZoomMode;
}

export function PdfOriginalViewer({
  blob,
  blobUrl,
  revisionKey,
  pageNumber,
  onPageChange,
  onTotalPagesDetected,
  zoomPercent,
  zoomMode,
}: PdfOriginalViewerProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState<{
    width: number;
    height: number;
  }>({ width: 680, height: 820 });
  const [numPages, setNumPages] = useState<number | null>(null);
  const [docError, setDocError] = useState<string | null>(null);

  // Reset state when switching revision or blobUrl (skipping initial mount)
  const prevDocKeyRef = useRef<string>(`${revisionKey}:${blobUrl ?? ""}`);
  useEffect(() => {
    const currentKey = `${revisionKey}:${blobUrl ?? ""}`;
    if (prevDocKeyRef.current !== currentKey) {
      prevDocKeyRef.current = currentKey;
      setNumPages(null);
      setDocError(null);
    }
  }, [revisionKey, blobUrl]);

  // Observe viewport dimensions for fit-width / fit-page
  useEffect(() => {
    const el = viewportRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const updateSize = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        setContainerSize({ width: rect.width, height: rect.height });
      }
    };
    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const clampedPage =
    numPages && numPages > 0
      ? Math.max(1, Math.min(numPages, pageNumber))
      : Math.max(1, pageNumber);

  useEffect(() => {
    if (numPages && numPages > 0 && pageNumber > numPages) {
      onPageChange(numPages);
    }
  }, [numPages, pageNumber, onPageChange]);

  const baseFitWidth = Math.max(280, Math.floor(containerSize.width - 40));
  const baseFitPageWidth = Math.max(
    240,
    Math.floor(
      Math.min(containerSize.width - 40, (containerSize.height - 40) * 0.71),
    ),
  );

  const computedPageWidth =
    zoomMode === "fit-page"
      ? baseFitPageWidth
      : zoomMode === "custom"
        ? Math.round(baseFitWidth * (zoomPercent / 100))
        : baseFitWidth;

  return (
    <div
      ref={viewportRef}
      className="relative flex h-full w-full flex-1 items-start justify-center overflow-auto bg-muted/30 p-3 sm:p-5"
      data-testid="pdf-original-viewer"
    >
      {docError ? (
        <div
          role="alert"
          className="my-auto flex max-w-md flex-col items-center justify-center gap-2.5 rounded-lg border border-destructive/30 bg-background p-6 text-center shadow-xs"
        >
          <AlertCircle className="h-8 w-8 text-destructive" />
          <p className="text-sm font-medium text-foreground">
            Không thể đọc tệp PDF gốc
          </p>
          <p className="text-xs text-muted-foreground">{docError}</p>
        </div>
      ) : (
        <PdfViewerErrorBoundary
          fallback={(err) => (
            <div
              role="alert"
              className="my-auto flex max-w-md flex-col items-center justify-center gap-2.5 rounded-lg border border-destructive/30 bg-background p-6 text-center shadow-xs"
            >
              <AlertCircle className="h-8 w-8 text-destructive" />
              <p className="text-sm font-medium text-foreground">
                Không thể hiển thị trang PDF gốc
              </p>
              <p className="text-xs text-muted-foreground">{err.message}</p>
            </div>
          )}
        >
          <PdfDocument
            suspense={false}
            key={`${revisionKey}:${blobUrl ?? ""}`}
            file={blobUrl ?? blob}
            onLoadSuccess={({ numPages: loadedPages }) => {
              setNumPages(loadedPages);
              setDocError(null);
              onTotalPagesDetected?.(loadedPages);
            }}
            onLoadError={(err) => {
              setDocError(
                err instanceof Error
                  ? err.message
                  : "Tệp PDF gốc bị hỏng hoặc không đúng định dạng.",
              );
            }}
            loading={
              <div className="flex flex-col items-center justify-center gap-2.5 py-16 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <span className="text-xs font-medium">
                  Đang tải tệp PDF gốc...
                </span>
              </div>
            }
            noData={
              <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground">
                <FileText className="h-8 w-8 text-muted-foreground/50" />
                <span className="text-xs">Chưa có dữ liệu tệp PDF gốc.</span>
              </div>
            }
            className="mx-auto flex justify-center"
          >
            <div className="overflow-hidden rounded-sm bg-background shadow-sm ring-1 ring-border/60">
              <PdfPage
                suspense={false}
                pageNumber={clampedPage}
                width={computedPageWidth}
                renderTextLayer={true}
                renderAnnotationLayer={false}
                loading={
                  <div
                    style={{ width: computedPageWidth, minHeight: 420 }}
                    className="flex flex-col items-center justify-center gap-2 bg-background text-muted-foreground"
                  >
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    <span className="text-xs">
                      Đang hiển thị trang {clampedPage}...
                    </span>
                  </div>
                }
              />
            </div>
          </PdfDocument>
        </PdfViewerErrorBoundary>
      )}
    </div>
  );
}
