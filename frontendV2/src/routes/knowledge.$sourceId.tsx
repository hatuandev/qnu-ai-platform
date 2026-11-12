import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowLeft,
  Columns2,
  Download,
  Eye,
  FileCode,
  FileJson,
  FileText,
  History,
  Loader2,
  MoreVertical,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  StopCircle,
  Table as TableIcon,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import {
  useCommitEditsMutation,
  useCompilationArtifactQuery,
  useCompilationDraftQuery,
  useCreateEditPreviewMutation,
  useEditContextQuery,
} from "@/api/compilation/queries";
import type { DraftContent } from "@/api/compilation/types";
import {
  getRevisionContentBlob,
  useCollectionsQuery,
  useRevisionsQuery,
  useSourceQuery,
  useSourceSummaryQuery,
} from "@/api/knowledge";
import {
  useCancelPreparationIntentMutation,
  useCreatePreparationIntentMutation,
  usePreparationIntentQuery,
} from "@/api/preparation/queries";
import { EmptyState } from "@/components/admin/empty-state";
import { CitationBadge } from "@/components/knowledge/citation-badge";
import { DocxViewer } from "@/components/knowledge/docx-viewer";
import { JsonStructureDialog } from "@/components/knowledge/json-structure-dialog";
import { MarkdownView } from "@/components/knowledge/markdown-view";
import { PublicationDialog } from "@/components/knowledge/publication-dialog";
import { SpellingStatusStrip } from "@/components/knowledge/spelling-status-strip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useBackgroundTasksStore } from "@/lib/background-tasks-store";
import { downloadBlob } from "@/lib/download-blob";
import {
  buildCitationMap,
  displayDocumentTitle,
  findViewedDerivation,
  resolveStudioAction,
} from "@/lib/knowledge-studio-helpers";
import { spellingScope } from "@/lib/spelling-review";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

const sourceStudioSearchSchema = z.object({
  collectionId: z.string().optional(),
});

export const Route = createFileRoute("/knowledge/$sourceId")({
  validateSearch: (search) => sourceStudioSearchSchema.parse(search),
  component: SourceStudioPage,
});

type EditableParagraph = {
  id: string;
  text: string;
  citations: string[];
};

type EditableSection = {
  id: string;
  heading: string;
  paragraphs: EditableParagraph[];
};

type EditableDraft = {
  title: string;
  sections: EditableSection[];
  unknowns: string[];
};

function SourceStudioPage() {
  const { sourceId } = Route.useParams();
  const searchParams = Route.useSearch();

  const activeWorkspaceId = useUiStore((s) => s.activeWorkspaceId);
  const registerBackgroundTask = useBackgroundTasksStore(
    (s) => s.registerPreparationTask,
  );

  // 1. Resolve collectionId
  const { data: collectionsPage } = useCollectionsQuery(activeWorkspaceId);
  const resolvedCollectionId = useMemo(() => {
    if (searchParams.collectionId) return searchParams.collectionId;
    return collectionsPage?.items?.[0]?.id || "";
  }, [searchParams.collectionId, collectionsPage]);

  // 2. Load Source & Summary
  const {
    data: source,
    isLoading: isSourceLoading,
    isError: isSourceError,
    error: sourceError,
    refetch: refetchSource,
  } = useSourceQuery(activeWorkspaceId, resolvedCollectionId, sourceId);

  const { data: summary, refetch: refetchSummary } = useSourceSummaryQuery(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
  );

  const { data: revisions } = useRevisionsQuery(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
  );

  // 3. Monitor active preparation intent
  const activeIntentId = summary?.preparation?.intent_id;
  const { data: intentData } = usePreparationIntentQuery(
    activeWorkspaceId,
    resolvedCollectionId,
    activeIntentId,
    { enabled: Boolean(activeIntentId) },
  );

  const createIntentMutation = useCreatePreparationIntentMutation(
    activeWorkspaceId,
    resolvedCollectionId,
  );
  const cancelIntentMutation = useCancelPreparationIntentMutation(
    activeWorkspaceId,
    resolvedCollectionId,
  );

  // 4. Resolve active Compilation Run ID
  const [activeRunIdOverride, setActiveRunIdOverride] = useState<string | null>(
    null,
  );
  const compilationRunId = useMemo(() => {
    if (activeRunIdOverride) return activeRunIdOverride;
    if (intentData?.compilation_run_id) return intentData.compilation_run_id;
    if (summary?.derivations && summary.derivations.length > 0) {
      return summary.derivations[0].compilation_run_id;
    }
    return null;
  }, [activeRunIdOverride, intentData, summary]);

  // 5. Load Compilation Draft & Markdown
  const {
    data: draftData,
    isLoading: isDraftLoading,
    refetch: refetchDraft,
  } = useCompilationDraftQuery(
    activeWorkspaceId,
    resolvedCollectionId,
    compilationRunId,
  );

  // 6. Edit Context & Mutations
  const { data: editContext, refetch: refetchEditContext } =
    useEditContextQuery(
      activeWorkspaceId,
      resolvedCollectionId,
      compilationRunId,
    );

  const createEditPreviewMutation = useCreateEditPreviewMutation(
    activeWorkspaceId,
    resolvedCollectionId,
  );
  const commitEditsMutation = useCommitEditsMutation(
    activeWorkspaceId,
    resolvedCollectionId,
  );

  // UI View States
  const [isEditing, setIsEditing] = useState(false);
  const [editableDraft, setEditableDraft] = useState<EditableDraft | null>(
    null,
  );
  const [editReason, setEditReason] = useState("");
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  const [activeTab, setActiveTab] = useState<
    "content" | "markdown" | "details"
  >("content");
  const [splitMode, setSplitMode] = useState<
    "split" | "editor-only" | "preview-only"
  >("split");
  const [mobileTab, setMobileTab] = useState<"original" | "prepared">(
    "prepared",
  );
  const [publicationOpen, setPublicationOpen] = useState(false);
  const [jsonDialogOpen, setJsonDialogOpen] = useState(false);
  const markdown = useCompilationArtifactQuery(
    "markdown",
    activeWorkspaceId,
    resolvedCollectionId,
    compilationRunId,
    activeTab === "markdown" && Boolean(draftData),
  );
  const json = useCompilationArtifactQuery(
    "json",
    activeWorkspaceId,
    resolvedCollectionId,
    compilationRunId,
    jsonDialogOpen && Boolean(draftData),
  );
  const exportName = (source?.file_name || "document").replace(/\.[^.]+$/, "");

  const handleDownloadJson = async () => {
    const result = await json.refetch();
    if (result.isSuccess) downloadBlob(result.data.blob, `${exportName}.json`);
    else toast.error("Không tải được tệp JSON.");
  };

  // Original Document Blob URL & loading
  const [docBlob, setDocBlob] = useState<Blob | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [blobLoading, setBlobLoading] = useState(false);
  const [blobError, setBlobError] = useState<string | null>(null);

  // Safe revision ID resolution
  const activeRevisionId = useMemo(() => {
    if (summary?.revision?.id) return summary.revision.id;
    if (revisions && revisions.length > 0) return revisions[0].id;
    return null;
  }, [summary?.revision?.id, revisions]);

  useEffect(() => {
    let active = true;
    let currentUrl: string | null = null;

    if (
      activeWorkspaceId &&
      resolvedCollectionId &&
      sourceId &&
      activeRevisionId
    ) {
      setBlobLoading(true);
      setBlobError(null);

      getRevisionContentBlob(
        activeWorkspaceId,
        resolvedCollectionId,
        sourceId,
        activeRevisionId,
      )
        .then((res) => {
          if (!active) return;
          currentUrl = URL.createObjectURL(res.blob);
          setDocBlob(res.blob);
          setBlobUrl(currentUrl);
          setBlobLoading(false);
        })
        .catch((err) => {
          if (active) {
            setBlobLoading(false);
            setBlobError(
              err instanceof Error ? err.message : "Không thể tải tệp gốc.",
            );
          }
        });
    }

    return () => {
      active = false;
      if (currentUrl) {
        URL.revokeObjectURL(currentUrl);
      }
    };
  }, [activeWorkspaceId, resolvedCollectionId, sourceId, activeRevisionId]);

  const isDocx = Boolean(source?.file_name.toLowerCase().endsWith(".docx"));
  const isPdf = Boolean(source?.file_name.toLowerCase().endsWith(".pdf"));

  const isPreparing =
    intentData?.status === "queued" ||
    intentData?.status === "waiting_ocr" ||
    intentData?.status === "compiling";

  const hasDraft = Boolean(draftData && draftData.sections?.length > 0);

  // Current derivation matching currently viewed compilation run
  const currentDerivation = useMemo(() => {
    return findViewedDerivation(summary?.derivations, compilationRunId);
  }, [summary?.derivations, compilationRunId]);
  const reviewScope = spellingScope(
    summary,
    currentDerivation?.ocr_run_id ?? intentData?.ocr_run_id,
  );

  // Resolve Studio action state and user-friendly status badge
  const actionState = useMemo(() => {
    return resolveStudioAction({
      source,
      summary,
      intentSummary:
        summary?.preparation ||
        (intentData
          ? {
              intent_id: intentData.id,
              status: intentData.status,
              step: intentData.step || "",
              error_code: intentData.error_code,
            }
          : null),
      hasDraft,
      isEditing,
      currentDerivation,
    });
  }, [source, summary, intentData, hasDraft, isEditing, currentDerivation]);

  // Sequential citation mapping for clean [1], [2] badges
  const citationIndexMap = useMemo(() => {
    return buildCitationMap(draftData);
  }, [draftData]);

  // Handler: Trigger preparation
  const handleStartPreparation = async () => {
    if (!activeRevisionId) {
      toast.error("Không tìm thấy thông tin phiên bản tệp để chuẩn bị.");
      return;
    }
    try {
      const idempotencyKey = `prep_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      const res = await createIntentMutation.mutateAsync({
        sourceId,
        input: {
          mode: "auto",
          revision_id: activeRevisionId,
          ...(reviewScope?.revisionId === activeRevisionId &&
          reviewScope.textVersion > 0
            ? {
                ocr_run_id: reviewScope.runId,
                text_version: reviewScope.textVersion,
              }
            : {}),
        },
        idempotencyKey,
      });

      registerBackgroundTask({
        id: res.intent.id,
        workspaceId: activeWorkspaceId || "",
        collectionId: resolvedCollectionId,
        sourceId,
        sourceTitle: source?.title || "Tài liệu",
        fileName: source?.file_name || "Tệp",
      });

      toast.success(
        "Đã khởi tạo chuẩn bị nội dung! Hệ thống đang xử lý tự động trong nền.",
      );
      void refetchSummary();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Không thể khởi tạo chuẩn bị";
      toast.error(msg);
    }
  };

  const handleCancelPreparation = async () => {
    if (!activeIntentId) return;
    try {
      await cancelIntentMutation.mutateAsync(activeIntentId);
      toast.info("Đã gửi yêu cầu dừng chuẩn bị nội dung.");
      void refetchSummary();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể dừng xử lý";
      toast.error(msg);
    }
  };

  // Structured Editor controls
  const handleStartEdit = () => {
    const baseContent = editContext?.content ||
      draftData || {
        title: source?.title || "Bản biên soạn",
        sections: [
          {
            heading: "Nội dung chính",
            paragraphs: [{ text: "", citations: [] }],
          },
        ],
        unknowns: [],
      };

    const formatted: EditableDraft = {
      title: baseContent.title,
      sections: baseContent.sections.map((s, sIdx) => ({
        id: `sec_${sIdx}_${Math.random().toString(36).substring(2, 7)}`,
        heading: s.heading,
        paragraphs: s.paragraphs.map((p, pIdx) => ({
          id: `p_${sIdx}_${pIdx}_${Math.random().toString(36).substring(2, 7)}`,
          text: p.text,
          citations: p.citations || [],
        })),
      })),
      unknowns: baseContent.unknowns || [],
    };

    setEditableDraft(formatted);
    setEditReason("");
    setIsEditing(true);
    setActiveTab("content");
  };

  const handleSaveEdits = async () => {
    if (!compilationRunId || !editContext || !editableDraft) return;

    if (!editableDraft.title.trim()) {
      toast.error("Tiêu đề tài liệu không được để trống.");
      return;
    }

    setIsSavingEdit(true);
    try {
      const draftContent: DraftContent = {
        title: editableDraft.title,
        sections: editableDraft.sections.map((s) => ({
          heading: s.heading,
          paragraphs: s.paragraphs.map((p) => ({
            text: p.text,
            citations: p.citations,
          })),
        })),
        unknowns: editableDraft.unknowns,
      };

      // Step 1: Create preview
      const preview = await createEditPreviewMutation.mutateAsync({
        runId: compilationRunId,
        data: {
          expected_bundle_sha256: editContext.bundle_sha256,
          reason:
            editReason.trim() || "Chỉnh sửa văn bản và hiệu đính số liệu.",
          content: draftContent,
        },
      });

      // Step 2: Commit edit with idempotency key
      const idempotencyKey = `edit_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      const commitRes = await commitEditsMutation.mutateAsync({
        runId: compilationRunId,
        data: {
          preview_id: preview.preview_id,
          preview_sha256: preview.preview_sha256,
        },
        idempotencyKey,
      });

      // Step 3: Switch to newly created child run
      setActiveRunIdOverride(commitRes.run.id);
      setIsEditing(false);
      setEditableDraft(null);
      toast.success("Đã lưu bản hiệu đính mới thành công!");

      void refetchDraft();
      void refetchEditContext();
      void refetchSummary();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Không thể lưu chỉnh sửa";
      toast.error(msg);
    } finally {
      setIsSavingEdit(false);
    }
  };

  if (isSourceLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="size-6 animate-spin text-primary" />
        <span>Đang tải thông tin chi tiết tài liệu...</span>
      </div>
    );
  }

  if (isSourceError || !source) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <EmptyState
          title="Không tìm thấy tài liệu"
          description={
            sourceError instanceof Error
              ? sourceError.message
              : "Tài liệu không tồn tại hoặc bạn không có quyền truy cập."
          }
          action={{
            label: "Quay lại Kho tri thức",
            onClick: () => {
              window.location.href = `/knowledge?collectionId=${resolvedCollectionId}`;
            },
          }}
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-background overflow-hidden min-h-0">
      {/* 1. Header Toolbar */}
      <header className="flex min-h-14 items-center justify-between border-b border-border/60 bg-card px-3 py-2 sm:py-0 gap-2 shrink-0">
        {/* Left: Back button + Truncated Title with Tooltip + Status Badge */}
        <div className="flex flex-1 items-center gap-2 min-w-0">
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="size-8 p-0 text-muted-foreground hover:text-foreground shrink-0"
          >
            <Link
              to="/knowledge"
              search={{ collectionId: resolvedCollectionId }}
              aria-label="Quay lại kho tri thức"
            >
              <ArrowLeft className="size-4" />
            </Link>
          </Button>

          <div className="flex flex-wrap sm:flex-nowrap items-center gap-x-2 gap-y-0.5 min-w-0">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <h1 className="text-sm font-semibold text-foreground tracking-tight truncate max-w-[200px] sm:max-w-[320px] md:max-w-[450px] cursor-default">
                    {displayDocumentTitle(source.title)}
                  </h1>
                </TooltipTrigger>
                <TooltipContent side="bottom" align="start">
                  <p className="max-w-md break-words">
                    {displayDocumentTitle(source.title)}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <Badge
              variant={actionState.displayStatus.variant}
              className="text-[10px] h-4 px-1.5 font-medium shrink-0"
              title={actionState.displayStatus.hint}
            >
              {actionState.displayStatus.label}
            </Badge>

            {actionState.displayStatus.servingNote && (
              <span className="text-[10px] text-muted-foreground hidden xl:inline truncate">
                ({actionState.displayStatus.servingNote})
              </span>
            )}
          </div>
        </div>

        {/* Right: Dynamic Primary Action + Outline Edit + Menu ⋯ + Split Switcher */}
        <div className="flex justify-end items-center gap-2 shrink-0">
          {/* STATE: Editing Mode */}
          {actionState.primaryAction === "save_edits" && (
            <div className="flex items-center gap-1.5">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setIsEditing(false);
                  setEditableDraft(null);
                }}
                disabled={isSavingEdit}
                className="h-8 text-xs"
              >
                Hủy
              </Button>
              <Button
                size="sm"
                onClick={handleSaveEdits}
                disabled={isSavingEdit}
                className="h-8 gap-1.5 text-xs shadow-2xs"
              >
                {isSavingEdit ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Save className="size-3.5" />
                )}
                <span>Lưu thay đổi</span>
              </Button>
            </div>
          )}

          {/* STATE: Preparing Active -> Cancel */}
          {actionState.primaryAction === "cancel_prep" && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancelPreparation}
              disabled={
                cancelIntentMutation.isPending ||
                summary?.actions?.can_stop !== true
              }
              className="h-8 text-xs text-destructive hover:bg-destructive/10 gap-1.5"
            >
              <StopCircle className="size-3.5" />
              <span>Dừng xử lý</span>
            </Button>
          )}

          {/* STATE: No draft -> Prepare */}
          {actionState.primaryAction === "prepare" && (
            <Button
              size="sm"
              onClick={handleStartPreparation}
              disabled={
                createIntentMutation.isPending ||
                summary?.capabilities?.can_prepare !== true
              }
              className="h-8 gap-1.5 text-xs shadow-2xs"
            >
              {createIntentMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Sparkles className="size-3.5" />
              )}
              <span>Chuẩn bị nội dung</span>
            </Button>
          )}

          {/* STATE: Draft ready for Approval */}
          {actionState.primaryAction === "approve" && (
            <>
              {actionState.canEdit && summary?.capabilities?.can_prepare && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleStartEdit}
                  className="h-8 gap-1.5 text-xs hidden sm:inline-flex"
                >
                  <Pencil className="size-3.5" />
                  <span>Chỉnh sửa</span>
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => setPublicationOpen(true)}
                disabled={
                  summary?.capabilities?.can_approve !== true &&
                  summary?.capabilities?.can_register !== true
                }
                className="h-8 gap-1.5 text-xs shadow-2xs"
              >
                <ShieldCheck className="size-3.5" />
                <span>Duyệt</span>
              </Button>
            </>
          )}

          {/* STATE: Approved ready for Publication */}
          {actionState.primaryAction === "publish" && (
            <>
              {actionState.canEdit && summary?.capabilities?.can_prepare && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleStartEdit}
                  className="h-8 gap-1.5 text-xs hidden sm:inline-flex"
                >
                  <Pencil className="size-3.5" />
                  <span>Chỉnh sửa</span>
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => setPublicationOpen(true)}
                disabled={summary?.capabilities?.can_publish !== true}
                className="h-8 gap-1.5 text-xs shadow-2xs"
              >
                <ShieldCheck className="size-3.5" />
                <span>Phát hành</span>
              </Button>
            </>
          )}

          {(actionState.primaryAction === "syncing" ||
            actionState.primaryAction === "served") &&
            actionState.canEdit &&
            summary?.capabilities?.can_prepare && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleStartEdit}
                className="h-8 gap-1.5 text-xs hidden sm:inline-flex"
              >
                <Pencil className="size-3.5" />
                Chỉnh sửa
              </Button>
            )}

          {/* More Actions Menu ⋯ */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="size-8 p-0 text-muted-foreground hover:text-foreground"
                aria-label="Thao tác phụ"
              >
                <MoreVertical className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              {actionState.canEdit && summary?.capabilities?.can_prepare && (
                <DropdownMenuItem
                  onClick={handleStartEdit}
                  className="sm:hidden cursor-pointer"
                >
                  <Pencil className="size-4 text-muted-foreground" />
                  <span>Chỉnh sửa nội dung</span>
                </DropdownMenuItem>
              )}

              {blobUrl && (
                <DropdownMenuItem asChild>
                  <a
                    href={blobUrl}
                    download={source.file_name}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <Download className="size-4 text-muted-foreground" />
                    <span>Tải tệp gốc về máy</span>
                  </a>
                </DropdownMenuItem>
              )}

              <DropdownMenuItem
                onClick={() => setActiveTab("markdown")}
                className="cursor-pointer"
              >
                <FileCode className="size-4 text-muted-foreground" />
                <span>Xem bản Markdown</span>
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => setActiveTab("details")}
                className="cursor-pointer"
              >
                <History className="size-4 text-muted-foreground" />
                <span>Lịch sử & Vòng đời</span>
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              {reviewScope && (
                <DropdownMenuItem asChild>
                  <Link
                    to="/knowledge/$sourceId/review"
                    params={{ sourceId }}
                    search={{
                      collectionId: resolvedCollectionId,
                      revisionId: reviewScope.revisionId,
                      runId: reviewScope.runId,
                    }}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <Sparkles className="size-4 text-amber-500" />
                    <span>Rà soát chính tả</span>
                  </Link>
                </DropdownMenuItem>
              )}

              <DropdownMenuItem
                onClick={() => setJsonDialogOpen(true)}
                disabled={!hasDraft}
                className="cursor-pointer"
              >
                <FileJson className="size-4 text-muted-foreground" />
                <span>Xem cấu trúc JSON</span>
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={handleDownloadJson}
                disabled={!hasDraft || json.isFetching}
                className="cursor-pointer"
              >
                <Download className="size-4 text-muted-foreground" />
                <span>Tải tệp JSON</span>
              </DropdownMenuItem>

              {summary?.serving?.served_revision_no && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={handleStartPreparation}
                    disabled={
                      createIntentMutation.isPending ||
                      summary?.capabilities?.can_prepare !== true
                    }
                    className="cursor-pointer"
                  >
                    <RefreshCw className="size-4 text-muted-foreground" />
                    <span>Chuẩn bị lại bản mới</span>
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* View Mode Switcher (Desktop only >= lg) */}
          <div className="hidden lg:flex items-center border border-border/70 rounded-md p-0.5 ml-1 bg-muted/30">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSplitMode("preview-only")}
              className={cn(
                "size-7 p-0",
                splitMode === "preview-only" &&
                  "bg-background shadow-2xs font-bold",
              )}
              title="Chỉ xem tệp gốc"
              aria-label="Chỉ xem tệp gốc"
            >
              <Eye className="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSplitMode("split")}
              className={cn(
                "size-7 p-0",
                splitMode === "split" && "bg-background shadow-2xs font-bold",
              )}
              title="Xem song song đối chiếu"
              aria-label="Xem song song đối chiếu"
            >
              <Columns2 className="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSplitMode("editor-only")}
              className={cn(
                "size-7 p-0",
                splitMode === "editor-only" &&
                  "bg-background shadow-2xs font-bold",
              )}
              title="Chỉ xem nội dung biên soạn"
              aria-label="Chỉ xem nội dung biên soạn"
            >
              <FileText className="size-3.5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Mobile Tab Switcher (< lg) */}
      <div className="flex lg:hidden items-center justify-center p-2 bg-muted/30 border-b border-border/60 shrink-0">
        <div className="grid grid-cols-2 w-full max-w-xs p-0.5 bg-muted rounded-lg text-xs font-medium">
          <button
            type="button"
            onClick={() => setMobileTab("original")}
            className={cn(
              "py-1 rounded-md transition-all text-center cursor-pointer",
              mobileTab === "original"
                ? "bg-card text-foreground shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Tệp gốc ({isDocx ? "Word" : isPdf ? "PDF" : "Tệp"})
          </button>
          <button
            type="button"
            onClick={() => setMobileTab("prepared")}
            className={cn(
              "py-1 rounded-md transition-all text-center cursor-pointer",
              mobileTab === "prepared"
                ? "bg-card text-foreground shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Nội dung đã chuẩn bị
          </button>
        </div>
      </div>

      {/* 2. Main Split Workspace Canvas */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left Pane: Tệp gốc (Original Document Preview) */}
        <div
          className={cn(
            "flex flex-col border-r border-border/70 bg-muted/20 overflow-hidden min-h-0 min-w-0",
            // Desktop visibility based on splitMode
            splitMode === "editor-only" && "lg:hidden",
            splitMode === "preview-only" && "lg:w-full",
            splitMode === "split" && "lg:w-1/2",
            // Mobile visibility (< lg) based on mobileTab
            mobileTab === "original" ? "w-full flex" : "hidden lg:flex",
          )}
        >
          {/* Header bar of Left Column */}
          {!(isDocx && docBlob && !blobLoading && !blobError) && (
            <div className="h-8 border-b border-border/60 px-3 bg-muted/40 flex items-center justify-between text-xs text-muted-foreground shrink-0">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <FileText className="size-3.5 text-primary" />
                <span>Tệp gốc</span>
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono h-4 px-1 py-0 uppercase"
                >
                  {isDocx ? "DOCX" : isPdf ? "PDF" : "FILE"}
                </Badge>
              </span>

              {blobUrl && (
                <a
                  href={blobUrl}
                  download={source.file_name}
                  className="hover:text-primary transition-colors flex items-center gap-1 text-[11px]"
                  title="Tải tệp gốc về máy"
                >
                  <Download className="size-3" />
                  <span>Tải về</span>
                </a>
              )}
            </div>
          )}

          {/* Left Column Content Viewport */}
          <div className="flex-1 min-h-0 min-w-0 overflow-hidden flex justify-center items-start">
            {blobLoading ? (
              <div className="py-24 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="size-5 animate-spin text-primary" />
                <span>Đang tải dữ liệu tệp gốc...</span>
              </div>
            ) : blobError ? (
              <div className="p-6 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive text-xs max-w-md my-8 text-center space-y-2">
                <p className="font-semibold">Không thể tải nội dung tệp gốc:</p>
                <p className="text-muted-foreground">{blobError}</p>
              </div>
            ) : isPdf && blobUrl ? (
              <iframe
                src={blobUrl}
                title="Xem trước tài liệu PDF"
                className="w-full h-full border-0 bg-white"
              />
            ) : isDocx && docBlob ? (
              <DocxViewer
                blob={docBlob}
                fileName={source.file_name}
                blobUrl={blobUrl}
              />
            ) : (
              <div className="text-center py-20 text-xs text-muted-foreground max-w-md space-y-3">
                <FileText className="size-10 text-muted-foreground/40 mx-auto" />
                <p>
                  Định dạng dữ liệu này không hỗ trợ xem trực tiếp trong trình
                  duyệt.
                </p>
                {blobUrl && (
                  <div>
                    <a
                      href={blobUrl}
                      download={source.file_name}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-card border border-border/70 text-primary font-medium hover:bg-muted transition-colors text-xs shadow-2xs"
                    >
                      <Download className="size-3.5" />
                      <span>Tải tệp về máy để xem</span>
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Pane: Mặt giấy hiệu đính liền mạch (Document Sheet Canvas) */}
        <div
          className={cn(
            "flex flex-col bg-background overflow-hidden min-h-0 min-w-0",
            // Desktop visibility based on splitMode
            splitMode === "preview-only" && "lg:hidden",
            splitMode === "editor-only" && "lg:w-full",
            splitMode === "split" && "lg:w-1/2",
            // Mobile visibility (< lg) based on mobileTab
            mobileTab === "prepared" ? "w-full flex" : "hidden lg:flex",
          )}
        >
          {/* Tab header bar */}
          <div className="h-8 border-b border-border/60 px-3 bg-muted/20 flex items-center justify-between text-xs shrink-0">
            <Tabs
              value={activeTab}
              onValueChange={(v) => setActiveTab(v as typeof activeTab)}
              className="w-auto"
            >
              <TabsList className="h-7 bg-transparent p-0 gap-1">
                <TabsTrigger
                  value="content"
                  className="h-6 text-xs px-2.5 data-[state=active]:bg-card"
                >
                  Nội dung
                </TabsTrigger>
                <TabsTrigger
                  value="markdown"
                  className="h-6 text-xs px-2.5 data-[state=active]:bg-card"
                >
                  Markdown
                </TabsTrigger>
                <TabsTrigger
                  value="details"
                  className="h-6 text-xs px-2.5 data-[state=active]:bg-card"
                >
                  Lịch sử
                </TabsTrigger>
              </TabsList>
            </Tabs>

            {currentDerivation && (
              <span className="text-[11px] text-muted-foreground">
                Lượt #{currentDerivation.compilation_generation}
              </span>
            )}
          </div>

          {/* Right Column Content Viewport */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 flex justify-center">
            <div className="w-full max-w-3xl space-y-6">
              {/* Spelling Check Status Info Banner */}
              {reviewScope && (
                <SpellingStatusStrip
                  workspaceId={activeWorkspaceId}
                  collectionId={resolvedCollectionId}
                  sourceId={sourceId}
                  {...reviewScope}
                />
              )}

              {/* STATE 1: Preparation is actively running */}
              {isPreparing && (
                <div className="p-8 rounded-xl border border-primary/30 bg-primary/5 text-center space-y-3.5">
                  <Loader2 className="size-8 text-primary animate-spin mx-auto" />
                  <div className="space-y-1">
                    <h3 className="font-semibold text-sm text-foreground">
                      {intentData?.step ||
                        "Hệ thống đang tự động chuẩn bị nội dung..."}
                    </h3>
                    <p className="text-xs text-muted-foreground leading-relaxed max-w-md mx-auto">
                      Đang đọc hiểu văn bản, trích xuất cấu trúc và gán căn cứ
                      truy vết. Quá trình xử lý diễn ra an toàn trong nền.
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancelPreparation}
                    className="h-7 text-xs text-destructive hover:bg-destructive/10 gap-1.5"
                  >
                    <StopCircle className="size-3" />
                    <span>Dừng xử lý</span>
                  </Button>
                </div>
              )}

              {/* STATE 2: No draft and not running -> CTA to start preparation */}
              {!hasDraft && !isPreparing && (
                <div className="p-8 rounded-xl border border-dashed border-border/80 bg-card/60 text-center space-y-4 my-8">
                  <div className="size-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
                    <Sparkles className="size-6" />
                  </div>
                  <div className="space-y-1.5 max-w-md mx-auto">
                    <h3 className="font-semibold text-sm text-foreground">
                      Tài liệu sẵn sàng để chuẩn bị nội dung
                    </h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      Khởi tạo chuẩn bị để đọc hiểu nội dung có cấu trúc, trích
                      xuất bảng biểu và gán căn cứ đối chiếu từ tệp gốc.
                    </p>
                  </div>
                  <Button
                    size="sm"
                    onClick={handleStartPreparation}
                    disabled={
                      createIntentMutation.isPending ||
                      summary?.capabilities?.can_prepare !== true
                    }
                    className="h-8 gap-1.5 text-xs shadow-2xs"
                  >
                    {createIntentMutation.isPending ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="size-3.5" />
                    )}
                    <span>Chuẩn bị nội dung ngay</span>
                  </Button>
                </div>
              )}

              {/* STATE 3: Loading draft data */}
              {isDraftLoading && (
                <div className="py-24 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="size-5 animate-spin text-primary" />
                  <span>Đang tải dữ liệu nội dung đã chuẩn bị...</span>
                </div>
              )}

              {/* STATE 4: Editing Mode */}
              {hasDraft && isEditing && editableDraft && (
                <div className="space-y-4 bg-card border border-border/70 rounded-xl p-6 shadow-2xs">
                  <div className="flex items-center justify-between border-b border-border/60 pb-3">
                    <div>
                      <h3 className="font-semibold text-sm text-foreground">
                        Chỉnh sửa nội dung bản biên soạn
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        Hiệu đính câu chữ, bổ sung hoặc điều chỉnh đoạn văn
                        trước khi duyệt.
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setIsEditing(false);
                        setEditableDraft(null);
                      }}
                      className="size-7 p-0"
                      aria-label="Đóng chỉnh sửa"
                    >
                      <X className="size-4" />
                    </Button>
                  </div>

                  {/* Document Title Input */}
                  <div className="space-y-1">
                    <label
                      htmlFor="doc-title"
                      className="text-xs font-semibold text-foreground"
                    >
                      Tiêu đề tài liệu
                    </label>
                    <input
                      id="doc-title"
                      type="text"
                      value={editableDraft.title}
                      onChange={(e) =>
                        setEditableDraft({
                          ...editableDraft,
                          title: e.target.value,
                        })
                      }
                      className="w-full h-9 px-3 rounded-md border border-border/70 text-xs bg-background focus:ring-1 focus:ring-primary focus:outline-hidden"
                    />
                  </div>

                  {/* Sections list */}
                  <div className="space-y-4 pt-2">
                    {editableDraft.sections.map((section) => (
                      <div
                        key={section.id}
                        className="p-4 rounded-lg border border-border/60 bg-muted/20 space-y-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <input
                            type="text"
                            value={section.heading}
                            onChange={(e) => {
                              setEditableDraft({
                                ...editableDraft,
                                sections: editableDraft.sections.map((s) =>
                                  s.id === section.id
                                    ? { ...s, heading: e.target.value }
                                    : s,
                                ),
                              });
                            }}
                            placeholder="Tiêu đề mục..."
                            className="font-semibold text-xs text-foreground bg-transparent border-b border-border/50 pb-1 focus:outline-hidden focus:border-primary flex-1"
                          />
                          {editableDraft.sections.length > 1 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditableDraft({
                                  ...editableDraft,
                                  sections: editableDraft.sections.filter(
                                    (s) => s.id !== section.id,
                                  ),
                                });
                              }}
                              className="size-6 p-0 text-muted-foreground hover:text-destructive"
                              title="Xóa mục này"
                              aria-label="Xóa mục này"
                            >
                              <Trash2 className="size-3" />
                            </Button>
                          )}
                        </div>

                        {/* Paragraphs in section */}
                        <div className="space-y-2">
                          {section.paragraphs.map((p) => (
                            <div key={p.id} className="space-y-1">
                              <div className="flex items-start gap-2">
                                <Textarea
                                  value={p.text}
                                  onChange={(e) => {
                                    setEditableDraft({
                                      ...editableDraft,
                                      sections: editableDraft.sections.map(
                                        (s) =>
                                          s.id === section.id
                                            ? {
                                                ...s,
                                                paragraphs: s.paragraphs.map(
                                                  (para) =>
                                                    para.id === p.id
                                                      ? {
                                                          ...para,
                                                          text: e.target.value,
                                                        }
                                                      : para,
                                                ),
                                              }
                                            : s,
                                      ),
                                    });
                                  }}
                                  rows={3}
                                  className="text-xs leading-relaxed bg-background"
                                  placeholder="Nội dung đoạn văn..."
                                />
                                {section.paragraphs.length > 1 && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      setEditableDraft({
                                        ...editableDraft,
                                        sections: editableDraft.sections.map(
                                          (s) =>
                                            s.id === section.id
                                              ? {
                                                  ...s,
                                                  paragraphs:
                                                    s.paragraphs.filter(
                                                      (para) =>
                                                        para.id !== p.id,
                                                    ),
                                                }
                                              : s,
                                        ),
                                      });
                                    }}
                                    className="size-6 p-0 text-muted-foreground hover:text-destructive shrink-0 mt-1"
                                    title="Xóa đoạn này"
                                    aria-label="Xóa đoạn này"
                                  >
                                    <Trash2 className="size-3" />
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))}

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const newPId = `p_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
                              setEditableDraft({
                                ...editableDraft,
                                sections: editableDraft.sections.map((s) =>
                                  s.id === section.id
                                    ? {
                                        ...s,
                                        paragraphs: [
                                          ...s.paragraphs,
                                          {
                                            id: newPId,
                                            text: "",
                                            citations: [],
                                          },
                                        ],
                                      }
                                    : s,
                                ),
                              });
                            }}
                            className="h-6 text-[11px] gap-1 text-primary hover:bg-primary/10"
                          >
                            <Plus className="size-3" />
                            <span>Thêm đoạn văn</span>
                          </Button>
                        </div>
                      </div>
                    ))}

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const newSecId = `sec_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
                        const newPId = `p_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
                        setEditableDraft({
                          ...editableDraft,
                          sections: [
                            ...editableDraft.sections,
                            {
                              id: newSecId,
                              heading: `Mục mới ${editableDraft.sections.length + 1}`,
                              paragraphs: [
                                {
                                  id: newPId,
                                  text: "",
                                  citations: [],
                                },
                              ],
                            },
                          ],
                        });
                      }}
                      className="h-7 text-xs gap-1.5"
                    >
                      <Plus className="size-3.5" />
                      <span>Thêm mục mới</span>
                    </Button>
                  </div>

                  {/* Edit Reason */}
                  <div className="space-y-1 pt-2 border-t border-border/60">
                    <label
                      htmlFor="doc-edit-reason"
                      className="text-[11px] font-medium text-muted-foreground"
                    >
                      Lý do chỉnh sửa
                    </label>
                    <input
                      id="doc-edit-reason"
                      type="text"
                      value={editReason}
                      onChange={(e) => setEditReason(e.target.value)}
                      placeholder="VD: Cập nhật chỉ tiêu tuyển sinh, đính chính số liệu bảng học phí..."
                      className="w-full h-8 px-2.5 rounded-md border border-border/70 text-xs bg-background"
                    />
                  </div>
                </div>
              )}

              {/* STATE 5: Active tab is Markdown */}
              {hasDraft && !isEditing && activeTab === "markdown" && (
                <MarkdownView
                  content={markdown.data?.text}
                  artifact={markdown.data?.blob}
                  isLoading={markdown.isLoading}
                  isError={markdown.isError}
                  fileName={`${exportName}.md`}
                  sourceTitle={displayDocumentTitle(source?.title)}
                  lifecycleStatus={actionState.displayStatus.label}
                  citations={citationIndexMap}
                />
              )}

              {/* STATE 6: Active tab is Details (Lifecycle History) */}
              {hasDraft && !isEditing && activeTab === "details" && (
                <div className="space-y-4 text-xs">
                  <div className="p-4 rounded-xl border border-border/70 bg-card space-y-3">
                    <div className="font-semibold text-foreground text-sm">
                      Tình trạng phục vụ Trợ lý AI
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-muted-foreground">
                          Phiên bản đang phục vụ:
                        </span>
                        <div className="font-mono font-medium mt-0.5">
                          {summary?.serving?.served_revision_no
                            ? `v${summary.serving.served_revision_no}`
                            : "Chưa phục vụ"}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          Phiên bản đang chuẩn bị:
                        </span>
                        <div className="font-mono font-medium mt-0.5">
                          {summary?.serving?.preparing_revision_no
                            ? `v${summary.serving.preparing_revision_no}`
                            : "Không có"}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl border border-border/70 bg-card space-y-2">
                    <div className="font-semibold text-foreground">
                      Lịch sử các lượt chuẩn bị & biên soạn
                    </div>
                    {summary?.derivations && summary.derivations.length > 0 ? (
                      <div className="space-y-2 pt-1">
                        {summary.derivations.map((d, i) => (
                          <div
                            key={d.compilation_run_id || i}
                            className="p-2.5 rounded-lg border border-border/60 bg-muted/20 flex items-center justify-between text-xs"
                          >
                            <div>
                              <div className="font-medium">
                                Lượt biên soạn #{d.compilation_generation}
                              </div>
                              <div className="text-[10px] text-muted-foreground font-mono">
                                Mã: {d.compilation_run_id}
                              </div>
                            </div>
                            <Badge
                              variant={d.is_serving ? "default" : "secondary"}
                              className="text-[10px] h-4"
                            >
                              {d.is_serving
                                ? "Đang phục vụ"
                                : d.compilation_status}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-muted-foreground text-xs py-2">
                        Chưa có lượt biên soạn nào được ghi nhận.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* STATE 7: Standard Seamless Document Sheet Canvas */}
              {hasDraft &&
                !isEditing &&
                activeTab === "content" &&
                draftData && (
                  <article className="bg-card border border-border/60 rounded-xl p-6 sm:p-10 shadow-xs max-w-3xl w-full mx-auto select-text space-y-6">
                    {/* Document Title Header */}
                    {displayDocumentTitle(draftData.title) !==
                      displayDocumentTitle(source.title) && (
                      <header className="border-b border-border/50 pb-4">
                        <h2 className="text-xl font-bold tracking-tight text-foreground">
                          {displayDocumentTitle(draftData.title)}
                        </h2>
                      </header>
                    )}

                    {/* Unknowns Callout if any */}
                    {draftData.unknowns && draftData.unknowns.length > 0 && (
                      <div className="p-4 rounded-lg border border-amber-500/30 bg-amber-500/5 text-amber-900 dark:text-amber-200 text-xs space-y-1.5">
                        <div className="flex items-center gap-1.5 font-semibold text-amber-800 dark:text-amber-300">
                          <AlertTriangle className="size-4" />
                          <span>Dữ kiện cần làm rõ:</span>
                        </div>
                        <ul className="list-disc list-inside space-y-1 pl-1 text-[13px] text-amber-950 dark:text-amber-100">
                          {draftData.unknowns.map((u) => (
                            <li key={u}>{u}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Sections & Paragraphs */}
                    <div className="space-y-6">
                      {draftData.sections.map((section) => (
                        <div key={section.heading} className="space-y-3">
                          <h3 className="font-medium text-sm text-muted-foreground border-b border-border/40 pb-1.5 mt-6 first:mt-0">
                            {section.heading}
                          </h3>

                          <div className="space-y-3">
                            {section.paragraphs.map((para) => {
                              const uniqueCitations = Array.from(
                                new Set(para.citations || []),
                              );

                              return (
                                <p
                                  key={para.text}
                                  className="text-[15px] leading-relaxed text-foreground/90 font-normal"
                                >
                                  <span>{para.text}</span>
                                  {uniqueCitations.map((c) => {
                                    const citInfo = citationIndexMap.get(c);
                                    const idx = citInfo?.index ?? 1;
                                    return (
                                      <CitationBadge
                                        key={c}
                                        index={idx}
                                        rawKey={c}
                                        sourceFile={
                                          citInfo?.sourceId === sourceId &&
                                          citInfo?.revisionId ===
                                            activeRevisionId
                                            ? source.file_name
                                            : undefined
                                        }
                                        location={citInfo?.location}
                                      />
                                    );
                                  })}
                                </p>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Source Tables with Citation Badges */}
                    {draftData.source_tables &&
                      draftData.source_tables.length > 0 && (
                        <div className="space-y-4 pt-6 border-t border-border/50">
                          <div className="flex items-center gap-2 font-semibold text-sm text-foreground">
                            <TableIcon className="size-4 text-primary" />
                            <span>Bảng dữ liệu trích xuất từ tệp gốc</span>
                          </div>

                          {draftData.source_tables.map((tbl) => {
                            const citInfo = citationIndexMap.get(tbl.citation);
                            const citIdx = citInfo?.index ?? 1;

                            return (
                              <div
                                key={tbl.citation}
                                className="rounded-lg border border-border/70 overflow-hidden shadow-2xs space-y-1 bg-background"
                              >
                                <div className="bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground border-b border-border/60 flex items-center justify-between">
                                  <span className="font-medium text-foreground">
                                    Bảng dữ liệu
                                  </span>
                                  <CitationBadge
                                    index={citIdx}
                                    rawKey={tbl.citation}
                                    sourceFile={
                                      citInfo?.sourceId === sourceId &&
                                      citInfo?.revisionId === activeRevisionId
                                        ? source.file_name
                                        : undefined
                                    }
                                    location={citInfo?.location}
                                  />
                                </div>
                                <div className="overflow-x-auto p-2">
                                  <table className="w-full text-xs text-left border-collapse">
                                    <tbody>
                                      {tbl.table?.rows?.map((row) => {
                                        const rowKey = `${tbl.citation}_${row.map((cell) => cell.text).join("::")}`;
                                        return (
                                          <tr
                                            key={rowKey}
                                            className="border-b border-border/40 last:border-0 hover:bg-muted/30"
                                          >
                                            {row.map((cell) => {
                                              const CellTag = cell.header
                                                ? "th"
                                                : "td";
                                              const cellKey = `${rowKey}_${cell.text}_${cell.row_span}_${cell.col_span}`;
                                              return (
                                                <CellTag
                                                  key={cellKey}
                                                  rowSpan={cell.row_span || 1}
                                                  colSpan={cell.col_span || 1}
                                                  className={cn(
                                                    "p-2.5 border border-border/40 text-foreground/90",
                                                    cell.header &&
                                                      "bg-muted/50 font-semibold text-foreground",
                                                  )}
                                                >
                                                  {cell.text}
                                                </CellTag>
                                              );
                                            })}
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                  </article>
                )}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Publication & Approval Dialog */}
      {compilationRunId && (
        <PublicationDialog
          open={publicationOpen}
          onOpenChange={setPublicationOpen}
          workspaceId={activeWorkspaceId || ""}
          collectionId={resolvedCollectionId}
          sourceTitle={displayDocumentTitle(source.title)}
          key={compilationRunId}
          compilationRunId={compilationRunId}
          existingVersion={currentDerivation?.version}
          canRegister={summary?.capabilities?.can_register === true}
          existingDocumentId={
            currentDerivation?.version?.document_id ||
            summary?.serving?.served_document_id
          }
          onSuccess={() => {
            void refetchSource();
            void refetchSummary();
          }}
        />
      )}
      {/* 4. JSON Structure Inspection Dialog */}
      <JsonStructureDialog
        open={jsonDialogOpen}
        onOpenChange={setJsonDialogOpen}
        title={`Cấu trúc dữ liệu JSON - ${displayDocumentTitle(source?.title || "Tài liệu")}`}
        artifact={json.data}
        isLoading={json.isLoading}
        isError={json.isError}
        fileName={`${exportName}.json`}
      />
    </div>
  );
}
