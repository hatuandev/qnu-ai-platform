import { Link } from "@tanstack/react-router";
import {
  Archive,
  ArrowLeft,
  ClipboardList,
  Download,
  FilePlus2,
  FileText,
  History,
  Loader2,
  MoreHorizontal,
  Pencil,
  Play,
  RotateCcw,
  Save,
  Sparkles,
  Trash2,
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
  onOpenRenameDialog: () => void;
  onLifecycleAction: (action: "archive" | "delete") => void;
  canArchive: boolean;
  canDelete: boolean;
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
  onOpenRenameDialog,
  onLifecycleAction,
  canArchive,
  canDelete,
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
            <FileText className="size-4.5 text-primary shrink-0" />
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

          <Badge
            variant={statusInfo.variant}
            className="text-xs font-normal h-5 shrink-0"
          >
            {statusInfo.status === "running" ? (
              <Loader2 className="size-3 animate-spin mr-1 inline" />
            ) : null}
            {statusInfo.label}
          </Badge>

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
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <History className="size-3 text-primary" />
                <span className="hidden sm:inline">Bản văn bản:</span>
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
              ) : (
                <Badge
                  variant="secondary"
                  className="text-[11px] py-0 h-6 hidden md:inline-flex"
                >
                  Đã lưu (v{doc.version})
                </Badge>
              )}
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
            >
              {isExtractionPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Play className="size-3.5" />
              )}
              <span>Bắt đầu bóc tách</span>
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
            >
              {isSpellCheckRunning ? (
                <Loader2 className="size-3.5 animate-spin text-primary" />
              ) : (
                <Sparkles className="size-3.5 text-primary" />
              )}
              <span>Kiểm tra chính tả</span>
            </Button>
          ) : null}

          {/* Save changes (Primary when unsaved drafts exist) */}
          {canManage && statusInfo.status === "completed" ? (
            <Button
              type="button"
              size="sm"
              variant={hasUnsavedDraft ? "default" : "outline"}
              className="h-8 text-xs gap-1.5"
              disabled={!hasUnsavedDraft || isSaving || baseMovedOn}
              onClick={onOpenSaveModal}
            >
              <Save className="size-3.5" />
              <span>Lưu thay đổi</span>
              {hasUnsavedDraft ? (
                <Badge
                  variant="warning"
                  className="ml-0.5 text-[10px] py-0 px-1 font-mono"
                >
                  {draftCount}
                </Badge>
              ) : null}
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
            >
              <ClipboardList className="size-3.5" />
              <span>Dùng để biên soạn</span>
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
            <DropdownMenuContent align="end" className="w-60 text-xs">
              <DropdownMenuItem
                className="gap-2"
                disabled={downloadingType !== null}
                onClick={() => onDownload("raw")}
              >
                <Download className="size-3.5 text-muted-foreground" />
                <span className="truncate">
                  Tải tệp gốc ({source.file_name})
                </span>
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
              <DropdownMenuItem
                className="gap-2"
                disabled={
                  statusInfo.status !== "completed" || downloadingType !== null
                }
                onClick={() => onDownload("json")}
              >
                <Download className="size-3.5 text-muted-foreground" />
                <span>Tải bản JSON cấu trúc (.json)</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="gap-2"
                disabled={
                  statusInfo.status !== "completed" || downloadingType !== null
                }
                onClick={() => onDownload("zip")}
              >
                <Download className="size-3.5 text-muted-foreground" />
                <span>Tải gói ZIP kèm ảnh (.zip)</span>
              </DropdownMenuItem>
              {isDocxFile && statusInfo.status === "completed" && (
                <DropdownMenuItem
                  className="gap-2"
                  disabled={downloadingType !== null}
                  onClick={() => onDownload("pdf")}
                >
                  <Download className="size-3.5 text-muted-foreground" />
                  <span>Tải PDF kết xuất từ Word (.pdf)</span>
                </DropdownMenuItem>
              )}

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
                    <span>Tải phiên bản mới</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="gap-2"
                    onClick={onOpenRenameDialog}
                  >
                    <Pencil className="size-3.5 text-muted-foreground" />
                    <span>Đổi tên tài liệu</span>
                  </DropdownMenuItem>
                </>
              ) : null}

              {canArchive && (
                <DropdownMenuItem
                  className="gap-2"
                  onClick={() => onLifecycleAction("archive")}
                >
                  <Archive className="size-3.5 text-muted-foreground" />
                  <span>Lưu trữ tài liệu</span>
                </DropdownMenuItem>
              )}

              {canDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="gap-2 text-destructive focus:text-destructive"
                    onClick={() => onLifecycleAction("delete")}
                  >
                    <Trash2 className="size-3.5" />
                    <span>Xóa vĩnh viễn tài liệu</span>
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
