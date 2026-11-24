import {
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  Maximize2,
  Minimize2,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useState } from "react";
import type { DocumentDraft, ExportFormat } from "@/api/conversations";
import { MarkdownContent } from "@/components/knowledge/markdown-content";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const FORMAT_META: Record<
  ExportFormat,
  {
    label: string;
    menuLabel: string;
    subtitleLabel: string;
    icon: typeof FileText;
    colorClass: string;
  }
> = {
  docx: {
    label: "DOCX",
    menuLabel: "Tải Word (.docx)",
    subtitleLabel: "Tài liệu Word",
    icon: FileText,
    colorClass: "text-blue-600 dark:text-blue-400",
  },
  pdf: {
    label: "PDF",
    menuLabel: "Tải PDF (.pdf)",
    subtitleLabel: "Tài liệu PDF",
    icon: FileText,
    colorClass: "text-rose-600 dark:text-rose-400",
  },
  xlsx: {
    label: "Excel",
    menuLabel: "Tải Excel (.xlsx)",
    subtitleLabel: "Bảng tính Excel",
    icon: FileSpreadsheet,
    colorClass: "text-emerald-600 dark:text-emerald-400",
  },
};

const LAYOUT_LABELS: Record<DocumentDraft["layout"], string> = {
  administrative: "Văn bản hành chính",
  spreadsheet: "Bảng biểu",
  standard: "Tài liệu",
};

const DOC_BLOCK_MARKER_RE =
  /<<<\s*DOCUMENT[^>]*>>>[\s\S]*?<<<\s*END_DOCUMENT\s*>>>/gi;
const STRAY_DOC_MARKER_RE = /<<<\s*\/?\s*(?:END_)?DOCUMENT[^>]*>{1,3}/gi;
const HTML_NBSP_RE = /&nbsp;|&#160;|&#xa0;|\u00a0/gi;
const STANDALONE_BR_LINE_RE = /^\s*<\s*br\s*\/?\s*>\s*$/gim;
const INLINE_BR_RE = /<\s*br\s*\/?\s*>/gi;

export function stripDocumentMarkers(text: string): string {
  if (!text || !text.includes("<<<")) return text;
  const withoutBlocks = text.replace(DOC_BLOCK_MARKER_RE, "");
  return withoutBlocks
    .replace(STRAY_DOC_MARKER_RE, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function cleanDraftPreviewMarkdown(markdown: string): string {
  if (!markdown) return "";
  return markdown
    .replace(HTML_NBSP_RE, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(STANDALONE_BR_LINE_RE, "")
    .replace(INLINE_BR_RE, "  \n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function resolveTargetFormat(
  draft: DocumentDraft,
  enabledFormats: ExportFormat[],
): ExportFormat | null {
  if (enabledFormats.length === 0) return null;
  if (
    draft.preferred_format &&
    enabledFormats.includes(draft.preferred_format)
  ) {
    return draft.preferred_format;
  }
  if (draft.layout === "spreadsheet" && enabledFormats.includes("xlsx")) {
    return "xlsx";
  }
  return enabledFormats[0] ?? null;
}

export function extractTurnDocumentDraft(
  rewriteTrace: Record<string, unknown> | null | undefined,
): DocumentDraft | null {
  if (!rewriteTrace || typeof rewriteTrace !== "object") return null;
  const raw = rewriteTrace.document_draft;
  if (!raw || typeof raw !== "object") return null;
  const candidate = raw as Record<string, unknown>;
  if (typeof candidate.markdown !== "string" || !candidate.markdown.trim()) {
    return null;
  }
  const layout =
    candidate.layout === "administrative" ||
    candidate.layout === "spreadsheet" ||
    candidate.layout === "standard"
      ? candidate.layout
      : "standard";
  const preferredFormat =
    candidate.preferred_format === "docx" ||
    candidate.preferred_format === "pdf" ||
    candidate.preferred_format === "xlsx"
      ? candidate.preferred_format
      : null;
  return {
    title:
      typeof candidate.title === "string" && candidate.title.trim()
        ? candidate.title.trim()
        : "Bản thảo văn bản",
    layout,
    markdown: candidate.markdown,
    has_tables: Boolean(candidate.has_tables),
    preferred_format: preferredFormat,
  };
}

function ExportActionControls({
  draft,
  enabledFormats,
  downloadingFormat,
  onDownload,
  variant = "card",
}: {
  draft: DocumentDraft;
  enabledFormats: ExportFormat[];
  downloadingFormat: ExportFormat | null;
  onDownload: (format: ExportFormat) => void;
  variant?: "card" | "toolbar";
}) {
  const targetFormat = resolveTargetFormat(draft, enabledFormats);
  if (!targetFormat) return null;

  const meta = FORMAT_META[targetFormat];
  const isBusy = downloadingFormat === targetFormat;
  const isAnyDownloading = downloadingFormat !== null;

  return (
    <Button
      type="button"
      variant={variant === "toolbar" ? "outline" : "ghost"}
      size="sm"
      className={cn(
        "h-7 gap-1.5 rounded-lg px-2.5 text-xs font-medium cursor-pointer",
        variant === "card" &&
          "text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
      disabled={isAnyDownloading}
      onClick={() => onDownload(targetFormat)}
    >
      {isBusy ? (
        <Loader2 className="size-3.5 animate-spin" />
      ) : (
        <Download className={cn("size-3.5", meta.colorClass)} />
      )}
      <span>{variant === "toolbar" ? `Tải ${meta.label}` : meta.label}</span>
    </Button>
  );
}

export function DocumentDraftCard({
  draft,
  enabledFormats,
  isActivePreview,
  downloadingFormat,
  onOpenPreview,
  onDownload,
}: {
  draft: DocumentDraft;
  enabledFormats: ExportFormat[];
  isActivePreview: boolean;
  downloadingFormat: ExportFormat | null;
  onOpenPreview: () => void;
  onDownload: (format: ExportFormat) => void;
}) {
  const targetFormat = resolveTargetFormat(draft, enabledFormats);
  if (!targetFormat) return null;

  const DocIcon = targetFormat === "xlsx" ? FileSpreadsheet : FileText;
  const subtitleText = FORMAT_META[targetFormat].subtitleLabel;

  return (
    <div
      className={cn(
        "mt-2.5 flex items-center justify-between gap-2 rounded-xl border bg-card px-3 py-2 transition-colors",
        isActivePreview
          ? "border-primary/50 bg-primary/[0.03]"
          : "border-border/70 hover:border-border hover:bg-muted/20",
      )}
    >
      <button
        type="button"
        onClick={onOpenPreview}
        className="flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 text-left"
      >
        <div
          className={cn(
            "flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary",
            targetFormat === "xlsx" &&
              "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
          )}
        >
          <DocIcon className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p
            className="truncate text-[13px] font-medium leading-tight text-foreground"
            title={draft.title}
          >
            {draft.title}
          </p>
          <div className="mt-0.5 flex items-center gap-1.5 whitespace-nowrap text-[11px] text-muted-foreground">
            <span className="truncate">{subtitleText}</span>
            <span aria-hidden="true">·</span>
            <span
              className={cn(
                "shrink-0",
                isActivePreview && "font-medium text-primary",
              )}
            >
              {isActivePreview ? "Đang xem" : "Xem trước"}
            </span>
          </div>
        </div>
      </button>

      <div className="shrink-0">
        <ExportActionControls
          draft={draft}
          enabledFormats={enabledFormats}
          downloadingFormat={downloadingFormat}
          onDownload={onDownload}
          variant="card"
        />
      </div>
    </div>
  );
}

export function DocumentPreviewPane({
  draft,
  enabledFormats,
  downloadingFormat,
  isExpanded,
  onToggleExpand,
  onDownload,
  onClose,
}: {
  draft: DocumentDraft;
  enabledFormats: ExportFormat[];
  downloadingFormat: ExportFormat | null;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onDownload: (format: ExportFormat) => void;
  onClose: () => void;
}) {
  const [zoom, setZoom] = useState(100);

  const previewMarkdown = cleanDraftPreviewMarkdown(draft.markdown);
  const targetFormat = resolveTargetFormat(draft, enabledFormats);
  const HeaderIcon =
    targetFormat === "xlsx" || draft.layout === "spreadsheet"
      ? FileSpreadsheet
      : FileText;

  const hasAdminHeader = previewMarkdown
    .toUpperCase()
    .includes("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM");
  const showAutoAdminHeader =
    draft.layout === "administrative" && !hasAdminHeader;
  const firstNonEmptyLine =
    previewMarkdown
      .split("\n")
      .map((line) => line.trim())
      .find(Boolean) ?? "";
  const showAutoTitle = !firstNonEmptyLine.startsWith("#");

  return (
    <section
      aria-label="Xem trước tài liệu"
      className={cn(
        "flex h-full min-h-0 flex-col border-l border-border/60 bg-muted/25",
        isExpanded
          ? "fixed inset-0 z-50 border-l-0 bg-background"
          : "w-full lg:w-1/2 xl:w-[52%]",
      )}
    >
      {/* Top toolbar */}
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-card px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <HeaderIcon
            className={cn(
              "size-4 shrink-0 text-primary",
              targetFormat === "xlsx" &&
                "text-emerald-600 dark:text-emerald-400",
            )}
          />
          <h3
            className="truncate text-xs font-semibold text-foreground"
            title={draft.title}
          >
            {draft.title}
          </h3>
          <Badge variant="outline" className="hidden h-5 px-1.5 text-[10px] sm:inline-flex">
            {targetFormat
              ? FORMAT_META[targetFormat].subtitleLabel
              : LAYOUT_LABELS[draft.layout]}
          </Badge>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Zoom controls */}
          <div className="flex items-center rounded-md border border-border/60 bg-background">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-7 rounded-r-none cursor-pointer"
              disabled={zoom <= 75}
              onClick={() => setZoom((prev) => Math.max(75, prev - 10))}
              title="Thu nhỏ"
            >
              <ZoomOut className="size-3.5" />
            </Button>
            <button
              type="button"
              onClick={() => setZoom(100)}
              className="px-1.5 text-[11px] font-medium tabular-nums text-muted-foreground hover:text-foreground cursor-pointer"
              title="Đặt lại 100%"
            >
              {zoom}%
            </button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-7 rounded-l-none cursor-pointer"
              disabled={zoom >= 150}
              onClick={() => setZoom((prev) => Math.min(150, prev + 10))}
              title="Phóng to"
            >
              <ZoomIn className="size-3.5" />
            </Button>
          </div>

          <ExportActionControls
            draft={draft}
            enabledFormats={enabledFormats}
            downloadingFormat={downloadingFormat}
            onDownload={onDownload}
            variant="toolbar"
          />

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 cursor-pointer"
            onClick={onToggleExpand}
            title={isExpanded ? "Thu gọn khung xem trước" : "Phóng to toàn màn hình"}
          >
            {isExpanded ? (
              <Minimize2 className="size-3.5" />
            ) : (
              <Maximize2 className="size-3.5" />
            )}
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 cursor-pointer"
            onClick={onClose}
            title="Đóng xem trước"
          >
            <X className="size-3.5" />
          </Button>
        </div>
      </header>

      {/* Scrollable paper canvas */}
      <div className="min-h-0 flex-1 overflow-auto p-3 sm:p-5">
        <div
          className="mx-auto w-full max-w-[720px] origin-top rounded-lg border border-border/70 bg-background px-6 py-6 shadow-xs transition-transform sm:px-8 sm:py-7"
          style={{
            transform: zoom === 100 ? undefined : `scale(${zoom / 100})`,
          }}
        >
          {showAutoAdminHeader ? (
            <div className="mb-4 grid grid-cols-2 gap-4 text-center text-[11px] leading-relaxed text-foreground">
              <div>
                <p className="font-bold uppercase">TRƯỜNG ĐẠI HỌC QUY NHƠN</p>
                <p className="text-muted-foreground">[Đơn vị soạn thảo]</p>
              </div>
              <div>
                <p className="font-bold uppercase">
                  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
                </p>
                <p className="font-semibold underline underline-offset-4">
                  Độc lập - Tự do - Hạnh phúc
                </p>
              </div>
            </div>
          ) : null}

          {showAutoTitle ? (
            <h1 className="mb-3.5 text-center text-sm font-bold text-foreground">
              {draft.layout === "administrative"
                ? draft.title.toUpperCase()
                : draft.title}
            </h1>
          ) : null}

          <div className="text-xs leading-relaxed text-foreground">
            <MarkdownContent content={previewMarkdown} compact />
          </div>
        </div>
      </div>
    </section>
  );
}
