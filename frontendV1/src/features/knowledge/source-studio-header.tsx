import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  ClipboardList,
  Download,
  FilePlus2,
  FileSpreadsheet,
  FileText,
  History,
  Loader2,
  MoreHorizontal,
  Play,
  RotateCcw,
  Save,
  Sparkles,
  Undo2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ReviewDocument } from "@/features/knowledge/ocr-types";
import type { ProcessingStatusDescriptor } from "@/features/knowledge/schemas";
import type { KBSource } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

export function SourceTypeIcon({
  source,
  isDocxFile,
  className,
}: {
  source: KBSource;
  isDocxFile?: boolean;
  className?: string;
}) {
  const fileName = (source.file_name || source.title || "").toLowerCase();
  const contentType = (source.content_type || "").toLowerCase();

  const isWord =
    Boolean(isDocxFile) ||
    fileName.endsWith(".docx") ||
    fileName.endsWith(".doc") ||
    contentType.includes("word") ||
    contentType.includes("officedocument.wordprocessingml");

  const isPdf = fileName.endsWith(".pdf") || contentType === "application/pdf";

  const isExcel =
    fileName.endsWith(".xlsx") ||
    fileName.endsWith(".xls") ||
    fileName.endsWith(".csv") ||
    contentType.includes("spreadsheet") ||
    contentType.includes("excel");

  if (isWord) {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={cn(
          "size-4.5 text-blue-600 dark:text-blue-400 shrink-0",
          className,
        )}
        aria-label="Tệp Word (.docx)"
        role="img"
      >
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
        <polyline points="14 2 14 8 20 8" />
        <path d="m9 12.5 1.2 5 1.8-4.5 1.8 4.5 1.2-5" strokeWidth="2.2" />
      </svg>
    );
  }

  if (isPdf) {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={cn(
          "size-4.5 text-rose-600 dark:text-rose-400 shrink-0",
          className,
        )}
        aria-label="Tệp PDF"
        role="img"
      >
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
        <polyline points="14 2 14 8 20 8" />
        <path d="M10 12h2a1.5 1.5 0 0 1 0 3h-2v3" strokeWidth="2" />
      </svg>
    );
  }

  if (isExcel) {
    return (
      <FileSpreadsheet
        className={cn(
          "size-4.5 text-emerald-600 dark:text-emerald-400 shrink-0",
          className,
        )}
        aria-label="Bảng tính Excel"
      />
    );
  }

  return (
    <FileText
      className={cn("size-4.5 text-primary shrink-0", className)}
      aria-label="Tệp tài liệu"
    />
  );
}

export interface SourceStudioHeaderProps {
  source: KBSource;
  collectionName?: string;
  workspaceId: string;
  collectionId: string;
  activeRevisionNo: number;
  statusInfo: ProcessingStatusDescriptor;
  doc: ReviewDocument | null;
  selectedVersion: number | null;
  hasUnsavedDraft: boolean;
  draftCount: number;
  baseMovedOn: boolean;
  canManage: boolean;
  canCompile: boolean;
  selectedRunId: string | null;
  downloadingType: "raw" | "md" | "json" | "zip" | "pdf" | null;
  isDocxFile: boolean;
  isExtractionPending: boolean;
  isSpellCheckRunning: boolean;
  isSaving: boolean;
  onVersionChange: (version: number | null) => void;
  onDiscardAllDrafts: () => void;
  onStartExtraction: () => void;
  onOpenSpellCheck: () => void;
  onOpenSaveModal: () => void;
  onOpenCompileDialog: () => void;
  onDownload: (format: "raw" | "md" | "json" | "zip" | "pdf") => void;
  onOpenReRunDialog: () => void;
  onOpenUploadRevision: () => void;
  onOpenRenameDialog?: () => void;
  onLifecycleAction?: (action: "archive" | "delete") => void;
  canArchive?: boolean;
  canDelete?: boolean;
}

export function SourceStudioHeader({
  source,
  collectionName,
  workspaceId,
  collectionId,
  activeRevisionNo,
  statusInfo,
  doc,
  selectedVersion,
  hasUnsavedDraft,
  draftCount,
  baseMovedOn,
  canManage,
  canCompile,
  selectedRunId,
  downloadingType,
  isDocxFile,
  isExtractionPending,
  isSpellCheckRunning,
  isSaving,
  onVersionChange,
  onDiscardAllDrafts,
  onStartExtraction,
  onOpenSpellCheck,
  onOpenSaveModal,
  onOpenCompileDialog,
  onDownload,
  onOpenReRunDialog,
  onOpenUploadRevision,
  onOpenRenameDialog: _onOpenRenameDialog,
  onLifecycleAction: _onLifecycleAction,
  canArchive: _canArchive,
  canDelete: _canDelete,
}: SourceStudioHeaderProps) {
  return (
    <header className="border-b border-border/60 pb-2.5">
      {/* Studio Topbar: Back Button, Title, Badges, Version Selector & Action Buttons */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5">
        {/* Left: Back button + Title + Badges + Integrated Version Selector */}
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          {/* Back button to collection */}
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="size-8 p-0 text-muted-foreground hover:text-foreground shrink-0 rounded-lg"
            title={`Quay lại ${collectionName ?? "Kho tri thức"}`}
          >
            <Link
              to="/workspaces/$workspaceId/knowledge/$knowledgeId"
              params={{ workspaceId, knowledgeId: collectionId }}
              search={{ page: 1, pageSize: 20 }}
            >
              <ArrowLeft className="size-4" />
            </Link>
          </Button>

          <div className="flex items-center gap-1.5 min-w-0">
            <SourceTypeIcon source={source} isDocxFile={isDocxFile} />
            <h1
              className="text-base sm:text-lg font-bold tracking-tight text-foreground truncate max-w-[280px] sm:max-w-[420px]"
              title={source.title}
            >
              {source.title}
            </h1>
          </div>

          <Badge variant="outline" className="text-xs font-mono h-5 shrink-0">
            Tệp v{activeRevisionNo}
          </Badge>

          {statusInfo.status !== "completed" ? (
            <Badge
              variant={statusInfo.variant}
              className="text-xs font-normal h-5 shrink-0"
            >
              {statusInfo.status === "running" ? (
                <Loader2 className="size-3 animate-spin mr-1 inline" />
              ) : null}
              {statusInfo.label}
            </Badge>
          ) : null}

          {!canManage ? (
            <Badge
              variant="outline"
              className="text-xs font-normal h-5 shrink-0"
            >
              Chế độ chỉ xem
            </Badge>
          ) : null}

          {/* Integrated Version & Draft Selector */}
          {statusInfo.status === "completed" && doc ? (
            <div className="flex items-center gap-1.5 pl-1.5 border-l border-border/60 shrink-0">
              <div className="flex items-center text-muted-foreground" title="Phiên bản văn bản">
                <History className="size-3.5 text-muted-foreground" />
              </div>
              <Select
                value={
                  selectedVersion === null ? "latest" : String(selectedVersion)
                }
                onValueChange={(val) => {
                  if (hasUnsavedDraft) {
                    if (
                      !window.confirm(
                        "Bạn đang có thay đổi nháp chưa lưu. Chuyển phiên bản xem sẽ xóa các thay đổi nháp này. Tiếp tục?",
                      )
                    ) {
                      return;
                    }
                  }
                  onVersionChange(val === "latest" ? null : Number(val));
                }}
              >
                <SelectTrigger
                  aria-label="Phiên bản văn bản"
                  className="h-7 text-xs w-[130px] sm:w-[155px] bg-background"
                >
                  <SelectValue placeholder="Chọn phiên bản" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="latest" className="text-xs">
                    Mới nhất (v{doc.version})
                  </SelectItem>
                  <SelectItem value="0" className="text-xs">
                    v0 (OCR gốc)
                  </SelectItem>
                  {doc.version > 0
                    ? Array.from({ length: doc.version }, (_, i) => i + 1).map(
                        (v) => (
                          <SelectItem
                            key={`v_${v}`}
                            value={String(v)}
                            className="text-xs"
                          >
                            Phiên bản v{v}{" "}
                            {v === doc.version ? "(Hiện hành)" : ""}
                          </SelectItem>
                        ),
                      )
                    : null}
                </SelectContent>
              </Select>

              {hasUnsavedDraft ? (
                <div className="flex items-center gap-1">
                  <Badge variant="warning" className="text-[11px] py-0 h-6">
                    Nháp: {draftCount} đoạn
                  </Badge>
                  {canManage ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="h-6 px-1.5 text-xs text-muted-foreground hover:text-destructive"
                      onClick={onDiscardAllDrafts}
                      title="Hủy toàn bộ thay đổi nháp chưa lưu"
                    >
                      <Undo2 className="size-3 mr-0.5" />
                      <span className="hidden sm:inline">Hủy</span>
                    </Button>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        {/* Right: Action Buttons Group */}
        <div className="flex items-center gap-1.5 flex-wrap shrink-0">
          {/* Unprocessed action */}
          {canManage && statusInfo.status === "unprocessed" ? (
            <Button
              size="sm"
              className="h-8 text-xs gap-1.5 shadow-xs"
              disabled={isExtractionPending}
              onClick={onStartExtraction}
              aria-label="Bắt đầu bóc tách"
            >
              {isExtractionPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Play className="size-3.5" />
              )}
              <span>Bóc tách</span>
            </Button>
          ) : null}

          {/* Spell check trigger */}
          {canManage && statusInfo.status === "completed" && doc ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 text-xs gap-1.5"
              disabled={isSpellCheckRunning}
              onClick={onOpenSpellCheck}
              aria-label="Kiểm tra chính tả"
            >
              {isSpellCheckRunning ? (
                <Loader2 className="size-3.5 animate-spin text-primary" />
              ) : (
                <Sparkles className="size-3.5 text-primary" />
              )}
              <span>Soát chính tả</span>
            </Button>
          ) : null}

          {/* Save changes (Only visible when unsaved drafts exist) */}
          {canManage && statusInfo.status === "completed" && hasUnsavedDraft ? (
            <Button
              type="button"
              size="sm"
              variant="default"
              className="h-8 text-xs gap-1.5 shadow-xs"
              disabled={isSaving || baseMovedOn}
              onClick={onOpenSaveModal}
              aria-label="Lưu thay đổi"
            >
              <Save className="size-3.5" />
              <span>Lưu</span>
              <Badge
                variant="warning"
                className="ml-0.5 text-[10px] py-0 px-1 font-mono"
              >
                {draftCount}
              </Badge>
            </Button>
          ) : null}

          {/* Compilation trigger */}
          {canCompile && statusInfo.status === "completed" && selectedRunId ? (
            <Button
              type="button"
              size="sm"
              variant={hasUnsavedDraft ? "outline" : "default"}
              className="h-8 text-xs gap-1.5"
              onClick={onOpenCompileDialog}
              aria-label="Biên soạn (Dùng để biên soạn)"
            >
              <ClipboardList className="size-3.5" />
              <span>Biên soạn</span>
            </Button>
          ) : null}

          {/* Single ⋯ More Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="size-8 p-0 text-muted-foreground hover:text-foreground"
                aria-label="Thao tác tài liệu"
              >
                {downloadingType ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <MoreHorizontal className="size-4" />
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52 text-xs">
              <DropdownMenuItem
                className="gap-2"
                disabled={downloadingType !== null}
                onClick={() => onDownload("raw")}
              >
                <Download className="size-3.5 text-muted-foreground" />
                {(() => {
                  const extMatch = source.file_name?.match(/\.([a-zA-Z0-9]+)$/);
                  const ext = extMatch ? `.${extMatch[1]}` : "";
                  return (
                    <span className="truncate">
                      Tải tệp gốc {ext ? `(${ext})` : ""}
                    </span>
                  );
                })()}
              </DropdownMenuItem>
              <DropdownMenuItem
                className="gap-2"
                disabled={
                  statusInfo.status !== "completed" || downloadingType !== null
                }
                onClick={() => onDownload("md")}
              >
                <Download className="size-3.5 text-muted-foreground" />
                <span>Tải bản Markdown (.md)</span>
              </DropdownMenuItem>

              {canManage ? (
                <>
                  <DropdownMenuSeparator />

                  {statusInfo.status !== "unprocessed" &&
                  statusInfo.status !== "running" ? (
                    <DropdownMenuItem
                      className="gap-2"
                      onClick={onOpenReRunDialog}
                    >
                      <RotateCcw className="size-3.5 text-muted-foreground" />
                      <span>Bóc tách lại</span>
                    </DropdownMenuItem>
                  ) : null}

                  <DropdownMenuItem
                    className="gap-2"
                    onClick={onOpenUploadRevision}
                  >
                    <FilePlus2 className="size-3.5 text-muted-foreground" />
                    <span>Tải tệp mới</span>
                  </DropdownMenuItem>
                </>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
