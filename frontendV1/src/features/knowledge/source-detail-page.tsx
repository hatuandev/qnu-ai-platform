import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  Archive,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Download,
  FilePlus2,
  FileText,
  Loader2,
  MoreHorizontal,
  Pencil,
  Play,
  RotateCcw,
  Save,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError, v1Client } from "@/app/api/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { CompilationDialog } from "@/features/knowledge/compilation-dialog";
import { OcrComparisonView } from "@/features/knowledge/ocr-comparison-view";
import {
  type OcrDraftScope,
  useOcrDraft,
} from "@/features/knowledge/ocr-draft-store";
import {
  useDetectCheckMutation,
  useProcessingRunDetailQuery,
  useProcessingRunsQuery,
  useRequestProcessingRunMutation,
  useSaveTextReviewMutation,
  useTextReviewQuery,
} from "@/features/knowledge/ocr-queries";
import {
  downloadReviewDocumentBlob,
  downloadReviewMarkdownBlob,
  downloadRunBundleBlob,
  readRenderedPdfBlob,
} from "@/features/knowledge/ocr-requests";
import {
  applySuggestionsToText,
  formatOcrError,
  generateIdempotencyKey,
  isDocx,
  validateSuggestionSpan,
} from "@/features/knowledge/ocr-schemas";
import type {
  DetectionResponse,
  Suggestion,
  TextChange,
} from "@/features/knowledge/ocr-types";
import {
  canCreateOrEditCompilation,
  canManageKnowledge,
} from "@/features/knowledge/permissions";
import {
  useCollectionQuery,
  useRevisionsQuery,
  useSourceQuery,
} from "@/features/knowledge/queries";
import { downloadRevisionContent } from "@/features/knowledge/requests";
import { RevisionUploadDialog } from "@/features/knowledge/revision-upload-dialog";
import { formatProcessingStatus } from "@/features/knowledge/schemas";
import { SourceRenameDialog } from "@/features/knowledge/source-rename-dialog";
import { SpellingResultPanel } from "@/features/knowledge/spelling-result-panel";
import type { KBRevision } from "@/features/knowledge/types";
import { LifecycleActionDialog } from "@/features/lifecycle/action-dialog";
import { canLifecycleAction } from "@/features/lifecycle/permissions";
import type { LifecycleOperation } from "@/features/lifecycle/types";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";

export interface SourceDetailSearchParams {
  revisionId?: string;
  runId?: string;
  checkId?: string;
  page?: number;
  tab?: "preview" | "ocr";
  subTab?: "runs" | "comparison" | "review" | "artifacts";
}

export function SourceDetailPage({
  workspaceId,
  collectionId,
  sourceId,
  search,
  onSearchChange,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  search?: SourceDetailSearchParams;
  onSearchChange?: (params: Partial<SourceDetailSearchParams>) => void;
}) {
  const navigate = useNavigate();
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);

  // Queries for Source and Collection
  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const sourceQuery = useSourceQuery(workspaceId, collectionId, sourceId);
  const revisionsQuery = useRevisionsQuery(workspaceId, collectionId, sourceId);

  const canManage = !rolePending && canManageKnowledge(role);
  const canCompile = !rolePending && canCreateOrEditCompilation(role);

  const collection = collectionQuery.data;
  const source = sourceQuery.data;
  const revisions = revisionsQuery.data ?? [];

  // Active Revision
  const activeRevision: KBRevision | undefined =
    revisions.find((r) => r.id === search?.revisionId) ?? revisions[0];

  const activeRevisionId = activeRevision?.id ?? "";
  const activeRevisionNo =
    activeRevision?.revision_no ?? source?.current_revision_no ?? 1;

  // Active Run Queries
  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    search?.runId ?? null,
  );
  const [activePage, setActivePage] = useState<number>(search?.page ?? 1);

  // Modals & Dialogs
  const [uploadRevisionOpen, setUploadRevisionOpen] = useState(false);
  const [renameSourceOpen, setRenameSourceOpen] = useState(false);
  const [reRunConfirmOpen, setReRunConfirmOpen] = useState(false);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [spellCheckModalOpen, setSpellCheckModalOpen] = useState(false);
  const [compilationDialogOpen, setCompilationDialogOpen] = useState(false);
  const [lifecycleOp, setLifecycleOp] = useState<LifecycleOperation | null>(
    null,
  );

  // Downloading derivative state
  const [downloadingType, setDownloadingType] = useState<
    "md" | "json" | "zip" | "raw" | "pdf" | null
  >(null);

  // Spell checking state
  const [localCheck, setLocalCheck] = useState<DetectionResponse | null>(null);

  // Fetch runs of current revision
  const runsQuery = useProcessingRunsQuery(
    workspaceId,
    collectionId,
    sourceId,
    activeRevisionId,
    1,
    10,
  );

  const runs = runsQuery.data?.items ?? [];

  // Auto-select latest run if not specified
  useEffect(() => {
    if (!selectedRunId && runs.length > 0) {
      const latest = runs[0];
      setSelectedRunId(latest.id);
      onSearchChange?.({ runId: latest.id });
    }
  }, [selectedRunId, runs, onSearchChange]);

  // Fetch active run details (polling built-in for running/queued status)
  const runDetailQuery = useProcessingRunDetailQuery(
    workspaceId,
    collectionId,
    sourceId,
    activeRevisionId,
    selectedRunId,
  );

  const activeRun = runDetailQuery.data;

  // Text review query for completed runs
  const textReviewQuery = useTextReviewQuery(
    workspaceId,
    collectionId,
    sourceId,
    activeRevisionId,
    selectedRunId,
    null,
    { enabled: Boolean(selectedRunId && activeRun?.status === "completed") },
  );

  const doc = textReviewQuery.data;

  // Draft Store
  const draftScope = useMemo<OcrDraftScope | null>(
    () =>
      selectedRunId
        ? {
            workspaceId,
            collectionId,
            sourceId,
            revisionId: activeRevisionId,
            runId: selectedRunId,
          }
        : null,
    [collectionId, activeRevisionId, selectedRunId, sourceId, workspaceId],
  );

  const draft = useOcrDraft(
    draftScope,
    doc ? { version: doc.version, sha256: doc.canonical_sha256 } : null,
  );
  const draftChanges = draft.changes;
  const draftCount = draftChanges.size;
  const hasUnsavedDraft = draftCount > 0;

  // Mutations
  const requestRunMutation = useRequestProcessingRunMutation(
    workspaceId,
    collectionId,
    sourceId,
    activeRevisionId,
  );

  const saveMutation = useSaveTextReviewMutation(
    workspaceId,
    collectionId,
    sourceId,
    activeRevisionId,
    selectedRunId ?? "",
  );

  const detectMutation = useDetectCheckMutation(
    workspaceId,
    collectionId,
    sourceId,
    activeRevisionId,
    selectedRunId ?? "",
  );

  // Handle Page Change
  const handlePageChange = (newPage: number) => {
    setActivePage(newPage);
    onSearchChange?.({
      revisionId: activeRevisionId,
      runId: selectedRunId ?? undefined,
      page: newPage,
    });
  };

  // Start extraction (native-first)
  const handleStartExtraction = async (force = false) => {
    try {
      const res = await requestRunMutation.mutateAsync({
        strategy: "auto",
        force,
      });

      setSelectedRunId(res.run.id);
      onSearchChange?.({
        revisionId: activeRevisionId,
        runId: res.run.id,
        page: 1,
      });

      toast.success(
        res.created
          ? "Đã gửi yêu cầu bóc tách tài liệu."
          : "Đã mở tiến trình bóc tách hiện có.",
      );
      void runsQuery.refetch();
      void sourceQuery.refetch();
    } catch (err) {
      toast.error(
        err instanceof ApiProblemError
          ? err.message
          : "Không thể bắt đầu bóc tách tài liệu.",
      );
    }
  };

  // Save Review Drafts to Server
  const handleConfirmSave = async () => {
    if (!doc || !selectedRunId) return;

    const changesPayload: TextChange[] = Array.from(draftChanges.entries()).map(
      ([evidence_id, after]) => {
        const unit = doc.units.find((u) => u.evidence_id === evidence_id);
        return { evidence_id, before: unit?.text ?? "", after };
      },
    );
    if (changesPayload.length === 0) return;

    try {
      const updated = await saveMutation.mutateAsync({
        body: {
          expected_version: doc.version,
          expected_sha256: doc.canonical_sha256,
          changes: changesPayload,
        },
        idempotencyKey: generateIdempotencyKey(),
      });

      draft.clear();
      setSaveModalOpen(false);
      toast.success(`Đã lưu phiên bản hiệu đính mới (v${updated.version}).`);
      void textReviewQuery.refetch();
    } catch (err) {
      toast.error(
        err instanceof ApiProblemError
          ? err.message
          : "Không thể lưu thay đổi hiệu đính.",
      );
    }
  };

  // Trigger Spell Check
  const handleStartSpellCheck = async (unitIds: string[]) => {
    if (!doc || !selectedRunId) return;
    if (unitIds.length === 0) {
      toast.error("Vui lòng chọn ít nhất một đoạn văn để kiểm tra.");
      return;
    }

    try {
      const checkRes = await detectMutation.mutateAsync({
        body: {
          expected_version: doc.version,
          expected_sha256: doc.canonical_sha256,
          evidence_ids: unitIds.slice(0, 50), // Respect API limit of 50
        },
        idempotencyKey: generateIdempotencyKey(),
      });

      setLocalCheck(checkRes);
      setSpellCheckModalOpen(true);
      toast.success("Đã hoàn tất kiểm tra chính tả các đoạn đã chọn.");
    } catch (err) {
      toast.error(
        err instanceof ApiProblemError
          ? err.message
          : "Không thể thực hiện kiểm tra chính tả.",
      );
    }
  };

  // Apply suggestion from spell check into draft
  const handleApplySuggestion = (s: Suggestion): boolean => {
    const targetUnit = doc?.units.find((u) => u.evidence_id === s.evidence_id);
    if (!targetUnit) return false;

    const currentText = draftChanges.get(s.evidence_id) ?? targetUnit.text;
    const validated = validateSuggestionSpan(currentText, s);
    if (!validated) {
      toast.error(
        "Đoạn văn đã thay đổi so với khi kiểm tra. Không áp dụng tự động được.",
      );
      return false;
    }

    const result = applySuggestionsToText(currentText, [s]);
    if (result.appliedCount === 0) {
      toast.error(result.error ?? "Không thể áp dụng gợi ý cho từ này.");
      return false;
    }

    draft.update((prev) => {
      const next = new Map(prev);
      next.set(s.evidence_id, result.updatedText);
      return next;
    });
    toast.success(`Đã áp dụng thay đổi cho từ "${s.original}".`);
    return true;
  };

  // Download Handler
  const handleDownload = async (
    type: "md" | "json" | "zip" | "raw" | "pdf",
  ) => {
    if (!selectedRunId) return;
    setDownloadingType(type);

    try {
      let blob: Blob;
      let filename = `${source?.title ?? "document"}`;

      if (type === "md") {
        const res = await downloadReviewMarkdownBlob(
          v1Client,
          workspaceId,
          collectionId,
          sourceId,
          activeRevisionId,
          selectedRunId,
          doc?.version,
        );
        blob = res.blob;
        filename += doc?.version ? `_v${doc.version}.md` : ".md";
      } else if (type === "json") {
        const res = await downloadReviewDocumentBlob(
          v1Client,
          workspaceId,
          collectionId,
          sourceId,
          activeRevisionId,
          selectedRunId,
          doc?.version,
        );
        blob = res.blob;
        filename += doc?.version ? `_v${doc.version}.json` : ".json";
      } else if (type === "zip") {
        const res = await downloadRunBundleBlob(
          v1Client,
          workspaceId,
          collectionId,
          sourceId,
          activeRevisionId,
          selectedRunId,
        );
        blob = res.blob;
        filename += "_bundle.zip";
      } else if (type === "pdf") {
        const res = await readRenderedPdfBlob(
          v1Client,
          workspaceId,
          collectionId,
          sourceId,
          activeRevisionId,
          selectedRunId,
        );
        blob = res.blob;
        filename += "_converted.pdf";
      } else {
        const res = await downloadRevisionContent(
          v1Client,
          workspaceId,
          collectionId,
          sourceId,
          activeRevisionId,
        );
        blob = res.blob;
        filename = res.fileName || activeRevision?.file_name || filename;
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(`Đã tải xuống ${filename}`);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Không tải được tệp tài liệu.",
      );
    } finally {
      setDownloadingType(null);
    }
  };

  // Status computation
  const activeProcessing = activeRun ?? source?.processing;
  const statusInfo = formatProcessingStatus(activeProcessing);
  const isDocxFile = isDocx(
    activeRevision?.content_type ?? source?.content_type,
    activeRevision?.file_name ?? source?.file_name,
  );

  if (sourceQuery.isLoading || collectionQuery.isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (sourceQuery.isError || !source) {
    if (lifecycleOp) return (
      <LifecycleActionDialog workspaceId={workspaceId}
        target={{ kind: "source", resource_id: sourceId, action: lifecycleOp }} label="Tài liệu"
        onClose={() => { setLifecycleOp(null); void navigate({
          to: "/workspaces/$workspaceId/knowledge/$knowledgeId", params: { workspaceId, knowledgeId: collectionId },
          search: { page: 1, pageSize: 20 },
        }); }}
        onCompleted={() => { toast.success("Thao tác tài liệu đã hoàn tất."); void navigate({
          to: "/workspaces/$workspaceId/knowledge/$knowledgeId", params: { workspaceId, knowledgeId: collectionId },
          search: { page: 1, pageSize: 20 },
        }); }} />
    );
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link
            to="/workspaces/$workspaceId/knowledge"
            params={{ workspaceId }}
            search={{ page: 1, pageSize: 20 }}
          >
            <ArrowLeft className="size-3.5" />
            Về kho tri thức
          </Link>
        </Button>
        <ErrorState
          error={sourceQuery.error}
          onRetry={() => void sourceQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 1. Header trên cùng: Tên tài liệu, phiên bản, trạng thái & Hàng hành động */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-border/70">
        <div className="min-w-0 space-y-1">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
            <Link
              to="/workspaces/$workspaceId/knowledge"
              params={{ workspaceId }}
              search={{ page: 1, pageSize: 20 }}
              className="hover:text-foreground transition-colors"
            >
              Kho tri thức
            </Link>
            <ChevronRight className="size-3 text-muted-foreground/60" />
            <Link
              to="/workspaces/$workspaceId/knowledge/$knowledgeId"
              params={{ workspaceId, knowledgeId: collectionId }}
              search={{ page: 1, pageSize: 20 }}
              className="hover:text-foreground transition-colors truncate max-w-[180px]"
            >
              {collection?.name ?? collectionId}
            </Link>
            <ChevronRight className="size-3 text-muted-foreground/60" />
            <span className="font-semibold text-foreground truncate max-w-[220px]">
              {source.title}
            </span>
          </div>

          {/* Tiêu đề, phiên bản & badge trạng thái */}
          <div className="flex items-center gap-2.5 flex-wrap">
            <FileText className="size-5 text-primary shrink-0" />
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground truncate max-w-[400px]">
              {source.title}
            </h1>
            <Badge variant="outline" className="text-xs font-mono h-5">
              v{activeRevisionNo}
            </Badge>

            <Badge
              variant={statusInfo.variant}
              className="text-xs font-normal h-5"
            >
              {statusInfo.status === "running" ? (
                <Loader2 className="size-3 animate-spin mr-1 inline" />
              ) : null}
              {statusInfo.label}
            </Badge>
          </div>
        </div>

        {/* Hàng hành động tinh gọn: Lưu thay đổi · Kiểm tra chính tả · Tải xuống · Menu ⋯ */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          {statusInfo.status === "unprocessed" ? (
            <Button
              size="sm"
              className="h-9 text-xs gap-1.5 shadow-xs"
              disabled={requestRunMutation.isPending}
              onClick={() => void handleStartExtraction(false)}
            >
              {requestRunMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Play className="size-3.5" />
              )}
              <span>Bắt đầu bóc tách</span>
            </Button>
          ) : statusInfo.status === "running" ? (
            <Button
              size="sm"
              variant="outline"
              disabled
              className="h-9 text-xs gap-1.5"
            >
              <Loader2 className="size-3.5 animate-spin text-primary" />
              <span>
                Đang xử lý ({activeRun?.pages_done ?? 0}/
                {activeRun?.pages_total ?? "?"})
              </span>
            </Button>
          ) : null}

          {/* Lưu thay đổi (nổi bật khi có nháp hiệu đính) */}
          {statusInfo.status === "completed" && (
            <Button
              size="sm"
              variant={hasUnsavedDraft ? "default" : "outline"}
              className="h-9 text-xs gap-1.5"
              disabled={!hasUnsavedDraft || saveMutation.isPending}
              onClick={() => setSaveModalOpen(true)}
            >
              <Save className="size-3.5" />
              <span>Lưu thay đổi</span>
              {hasUnsavedDraft ? (
                <Badge
                  variant="warning"
                  className="ml-1 text-[10px] py-0 px-1 font-mono"
                >
                  {draftCount}
                </Badge>
              ) : null}
            </Button>
          )}

          {/* Kiểm tra chính tả (khi đã có kết quả) */}
          {statusInfo.status === "completed" && (
            <Button
              size="sm"
              variant="outline"
              className="h-9 text-xs gap-1.5"
              disabled={detectMutation.isPending}
              onClick={() => {
                const currentUnits = (doc?.units ?? []).filter(
                  (u) => u.page === activePage,
                );
                void handleStartSpellCheck(
                  currentUnits.map((u) => u.evidence_id),
                );
              }}
            >
              {detectMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin text-primary" />
              ) : (
                <Sparkles className="size-3.5 text-primary" />
              )}
              <span>Kiểm tra chính tả</span>
            </Button>
          )}

          {/* Dropdown Tải xuống (Markdown, JSON, ZIP kèm ảnh, Tệp gốc) */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-9 text-xs gap-1 text-muted-foreground hover:text-foreground"
                disabled={downloadingType !== null}
              >
                {downloadingType ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Download className="size-3.5" />
                )}
                <span>Tải xuống</span>
                <ChevronDown className="size-3 opacity-60" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 text-xs">
              <DropdownMenuItem
                disabled={statusInfo.status !== "completed"}
                onClick={() => void handleDownload("md")}
              >
                <span>Bản Markdown dẫn xuất (.md)</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled={statusInfo.status !== "completed"}
                onClick={() => void handleDownload("json")}
              >
                <span>Bản JSON cấu trúc (.json)</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled={statusInfo.status !== "completed"}
                onClick={() => void handleDownload("zip")}
              >
                <span>Gói ZIP kèm ảnh bóc tách (.zip)</span>
              </DropdownMenuItem>
              {isDocxFile && statusInfo.status === "completed" && (
                <DropdownMenuItem onClick={() => void handleDownload("pdf")}>
                  <span>Tệp PDF kết xuất từ Word (.pdf)</span>
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => void handleDownload("raw")}>
                <span>Tệp gốc tải lên ({source.file_name})</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Menu ⋯ gom toàn bộ tác vụ phụ: Dùng để biên soạn, Bóc tách lại, Tải phiên bản mới, Đổi tên, Lưu trữ, Xóa */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="size-9 p-0 text-muted-foreground hover:text-foreground"
                aria-label="Thao tác tài liệu"
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52 text-xs">
              {canCompile &&
              statusInfo.status === "completed" &&
              selectedRunId ? (
                <DropdownMenuItem
                  className="gap-2"
                  onClick={() => setCompilationDialogOpen(true)}
                >
                  <ClipboardList className="size-3.5 text-primary" />
                  <span>Dùng để biên soạn</span>
                </DropdownMenuItem>
              ) : null}

              {statusInfo.status !== "unprocessed" &&
              statusInfo.status !== "running" ? (
                <DropdownMenuItem
                  className="gap-2"
                  onClick={() => setReRunConfirmOpen(true)}
                >
                  <RotateCcw className="size-3.5 text-muted-foreground" />
                  <span>Bóc tách lại</span>
                </DropdownMenuItem>
              ) : null}

              {(canCompile &&
                statusInfo.status === "completed" &&
                selectedRunId) ||
              (statusInfo.status !== "unprocessed" &&
                statusInfo.status !== "running") ? (
                <DropdownMenuSeparator />
              ) : null}

              <DropdownMenuItem
                className="gap-2"
                onClick={() => setUploadRevisionOpen(true)}
              >
                <FilePlus2 className="size-3.5 text-muted-foreground" />
                <span>Tải phiên bản mới</span>
              </DropdownMenuItem>
              {canManage && (
                <DropdownMenuItem
                  className="gap-2"
                  onClick={() => setRenameSourceOpen(true)}
                >
                  <Pencil className="size-3.5 text-muted-foreground" />
                  <span>Đổi tên tài liệu</span>
                </DropdownMenuItem>
              )}
              {canLifecycleAction(role, "source", "archive") && (
                <DropdownMenuItem
                  className="gap-2"
                  onClick={() => setLifecycleOp("archive")}
                >
                  <Archive className="size-3.5 text-muted-foreground" />
                  <span>Lưu trữ tài liệu</span>
                </DropdownMenuItem>
              )}
              {canLifecycleAction(role, "source", "delete") && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="gap-2 text-destructive focus:text-destructive"
                    onClick={() => setLifecycleOp("delete")}
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

      {/* Cảnh báo lỗi bóc tách nếu có */}
      {activeRun && ["failed", "uncertain"].includes(activeRun.status) && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="size-4" />
          <AlertTitle>Bóc tách chưa thành công</AlertTitle>
          <AlertDescription className="text-xs mt-1">
            {formatOcrError(activeRun.error_code, activeRun.error_detail)}
            {activeRun.error_code && (
              <span className="block font-mono text-xs mt-0.5">
                Mã lỗi: {activeRun.error_code}
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* 2. MÀN ĐỐI CHIẾU HAI CỘT: Cột trái: Bản gốc | Cột phải: Kết quả đúng trang */}
      {activeRun ? (
        <OcrComparisonView
          workspaceId={workspaceId}
          collectionId={collectionId}
          sourceId={sourceId}
          revisionId={activeRevisionId}
          run={activeRun}
          pages={activeRun.pages}
          activePageNumber={activePage}
          onPageChange={handlePageChange}
          reviewDoc={doc}
          isDocx={isDocxFile}
          draftChanges={draftChanges}
          onSaveDraftChange={(evidenceId, _before, after) => {
            draft.update((prev) => {
              const next = new Map(prev);
              next.set(evidenceId, after);
              return next;
            });
          }}
          onStartSpellCheck={handleStartSpellCheck}
        />
      ) : (
        /* Trạng thái chưa bóc tách: Giới thiệu & Kêu gọi bóc tách chủ động */
        <Card className="rounded-xl border-dashed p-12 text-center space-y-4 bg-muted/10">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary mx-auto">
            <Play className="size-7" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="text-base font-semibold text-foreground">
              Tài liệu đã được lưu trữ an toàn
            </h3>
            <p className="text-xs text-muted-foreground">
              Tài liệu này chưa được bóc tách. Nhấn &ldquo;Bắt đầu bóc
              tách&rdquo; để tự động trích xuất văn bản, cấu trúc bảng và ảnh
              đối chiếu bằng phương pháp native-first.
            </p>
          </div>
          <Button
            size="sm"
            className="gap-1.5 text-xs shadow-xs"
            disabled={requestRunMutation.isPending}
            onClick={() => void handleStartExtraction(false)}
          >
            {requestRunMutation.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Play className="size-3.5" />
            )}
            <span>Bắt đầu bóc tách ngay</span>
          </Button>
        </Card>
      )}

      {/* 3. MODALS & DIALOGS */}
      {/* Modal xác nhận Bóc tách lại */}
      <Dialog open={reRunConfirmOpen} onOpenChange={setReRunConfirmOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold flex items-center gap-2">
              <RotateCcw className="size-4 text-primary" />
              <span>Xác nhận bóc tách lại</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Thao tác này sẽ tạo một lượt bóc tách mới (generation mới) cho
              phiên bản tài liệu hiện hành. Kết quả và bằng chứng của các lượt
              trước được bảo toàn bất biến trong lịch sử.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setReRunConfirmOpen(false)}
            >
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={() => {
                setReRunConfirmOpen(false);
                void handleStartExtraction(true);
              }}
            >
              Bắt đầu lượt mới
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Xác nhận Lưu thay đổi Hiệu đính */}
      <Dialog open={saveModalOpen} onOpenChange={setSaveModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold flex items-center gap-2">
              <Save className="size-4 text-primary" />
              <span>Lưu phiên bản hiệu đính</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Bạn có {draftCount} thay đổi nháp đang chờ lưu. Hành động này sẽ
              tạo một phiên bản hiệu đính mới trên máy chủ (v
              {(doc?.version ?? 0) + 1}).
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-48 overflow-y-auto space-y-2 p-3 bg-muted/20 rounded-lg border text-xs">
            {Array.from(draftChanges.entries()).map(([evidence_id, after]) => {
              const unit = doc?.units.find(
                (u) => u.evidence_id === evidence_id,
              );
              return (
                <div
                  key={evidence_id}
                  className="space-y-0.5 border-b pb-1.5 last:border-none"
                >
                  <span className="font-mono text-[10px] text-muted-foreground block">
                    {evidence_id}
                  </span>
                  {unit ? (
                    <p className="line-through text-destructive text-[11px] truncate">
                      {unit.text}
                    </p>
                  ) : null}
                  <p className="text-success text-[11px] truncate font-medium">
                    {after}
                  </p>
                </div>
              );
            })}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSaveModalOpen(false)}
            >
              Hủy
            </Button>
            <Button
              size="sm"
              disabled={saveMutation.isPending}
              onClick={() => void handleConfirmSave()}
            >
              {saveMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin mr-1" />
              ) : null}
              <span>Xác nhận lưu</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Kết quả Kiểm tra Chính tả */}
      <Dialog open={spellCheckModalOpen} onOpenChange={setSpellCheckModalOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col p-4">
          <DialogHeader className="pb-2">
            <DialogTitle className="text-sm font-semibold flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              <span>Gợi ý sửa lỗi chính tả</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Rà soát các lỗi nghi ngờ sai chính tả theo mô hình AI. Bạn có thể
              bấm Áp dụng hoặc Bỏ qua từng gợi ý.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto py-2">
            {doc && (
              <SpellingResultPanel
                workspaceId={workspaceId}
                collectionId={collectionId}
                sourceId={sourceId}
                revisionId={activeRevisionId}
                runId={selectedRunId ?? ""}
                localCheck={localCheck}
                doc={doc}
                draftChanges={draftChanges}
                canManage={canManage}
                onApply={handleApplySuggestion}
              />
            )}
          </div>

          <DialogFooter className="pt-2 border-t">
            <Button size="sm" onClick={() => setSpellCheckModalOpen(false)}>
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Upload Phiên bản mới */}
      <RevisionUploadDialog
        open={uploadRevisionOpen}
        onOpenChange={setUploadRevisionOpen}
        workspaceId={workspaceId}
        collectionId={collectionId}
        sourceId={sourceId}
        sourceTitle={source.title}
      />

      {/* Modal Đổi tên Tài liệu */}
      <SourceRenameDialog
        open={renameSourceOpen}
        onOpenChange={setRenameSourceOpen}
        workspaceId={workspaceId}
        collectionId={collectionId}
        source={source}
        onSuccess={() => void sourceQuery.refetch()}
      />

      {/* Compilation Dialog (để nối mượt sang Compiler) */}
      {selectedRunId && (
        <CompilationDialog
          isOpen={compilationDialogOpen}
          onClose={() => setCompilationDialogOpen(false)}
          workspaceId={workspaceId}
          collectionId={collectionId}
          initialRun={{
            runId: selectedRunId,
            sourceId,
            sourceTitle: source.title,
            revisionId: activeRevisionId,
            revisionNo: activeRevisionNo,
            generation: activeRun?.generation ?? 1,
          }}
          onSuccess={(runId) => {
            void navigate({
              to: "/workspaces/$workspaceId/collections/$collectionId/compilations/$runId",
              params: { workspaceId, collectionId, runId },
            });
          }}
        />
      )}

      {/* Lifecycle Actions (Lưu trữ / Xóa) */}
      {lifecycleOp && (
        <LifecycleActionDialog
          workspaceId={workspaceId}
          target={{
            kind: "source",
            resource_id: source.id,
            action: lifecycleOp,
          }}
          label={source.title}
          onClose={() => setLifecycleOp(null)}
          onCompleted={() => {
            toast.success(lifecycleOp === "delete" ? "Đã xóa vĩnh viễn tài liệu." : "Đã lưu trữ tài liệu.");
            void navigate({ to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
              params: { workspaceId, knowledgeId: collectionId }, search: { page: 1, pageSize: 20 } });
          }}
        />
      )}
    </div>
  );
}
