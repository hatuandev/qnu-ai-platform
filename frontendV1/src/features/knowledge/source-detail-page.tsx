import { Link, useBlocker, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  AlertTriangle,
  Archive,
  ArrowLeft,
  ChevronRight,
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
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";
import { toast } from "sonner";
import {
  ApiProblemError,
  getTokenState,
  subscribeToken,
  v1Client,
} from "@/app/api/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { CompilationDialog } from "@/features/knowledge/compilation-dialog";
import {
  type MobileReviewPane,
  OcrComparisonView,
} from "@/features/knowledge/ocr-comparison-view";
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
  OcrSaveConfirmDialog,
  OcrSpellCheckDialog,
} from "@/features/knowledge/ocr-review-dialogs";
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
import { ProcessingProgress } from "@/features/knowledge/processing-progress";
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
import { useActionScope } from "@/features/lifecycle/action-scope";
import { canLifecycleAction } from "@/features/lifecycle/permissions";
import type { LifecycleOperation } from "@/features/lifecycle/types";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import {
  DocumentSpellingProgress,
  DocumentSpellingReport,
} from "./document-spelling-report";
import { selectableSpellingUnits } from "./ocr-spelling-batch";
import { useDocumentSpelling } from "./use-document-spelling";

export interface SourceDetailSearchParams {
  revisionId?: string;
  runId?: string;
  checkId?: string;
  page?: number;
  tab?: "preview" | "ocr";
  subTab?: "runs" | "comparison" | "review" | "artifacts";
}

export function SourceDetailPage(props: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  search?: SourceDetailSearchParams;
  onSearchChange?: (params: Partial<SourceDetailSearchParams>) => void;
}) {
  const { sessionId } = useSyncExternalStore(
    subscribeToken,
    getTokenState,
    getTokenState,
  );
  return (
    <SourceDetailSession
      key={`${sessionId}:${props.workspaceId}:${props.collectionId}:${props.sourceId}`}
      {...props}
    />
  );
}

function SourceDetailSession({
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
  const current = useActionScope();
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

  // Active Run & Page State
  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    search?.runId ?? null,
  );
  const [activePage, setActivePage] = useState<number>(search?.page ?? 1);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [focusedEvidenceId, setFocusedEvidenceId] = useState<string | null>(
    null,
  );
  const [locateRequestNonce, setLocateRequestNonce] = useState<number>(0);
  const [externalEditUnitId, setExternalEditUnitId] = useState<string | null>(
    null,
  );
  const [mobilePane, setMobilePane] = useState<MobileReviewPane>("content");

  // Sync URL search params when they change externally
  useEffect(() => {
    if (search?.runId) {
      setSelectedRunId(search.runId);
    }
  }, [search?.runId]);

  useEffect(() => {
    if (search?.page) {
      setActivePage(search.page);
    }
  }, [search?.page]);

  // Modals & Dialogs
  const [uploadRevisionOpen, setUploadRevisionOpen] = useState(false);
  const [renameSourceOpen, setRenameSourceOpen] = useState(false);
  const [reRunConfirmOpen, setReRunConfirmOpen] = useState(false);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [spellCheckConfigOpen, setSpellCheckConfigOpen] = useState(false);
  const [wholeDocumentCheck, setWholeDocumentCheck] = useState(true);
  const [compilationDialogOpen, setCompilationDialogOpen] = useState(false);
  const [lifecycleOp, setLifecycleOp] = useState<LifecycleOperation | null>(
    null,
  );

  // Idempotency keys & conflict state
  const [activeSaveKey, setActiveSaveKey] = useState<string>(() =>
    generateIdempotencyKey(),
  );
  const [activeSpellKey, setActiveSpellKey] = useState<string>(() =>
    generateIdempotencyKey(),
  );
  const [conflictError, setConflictError] = useState<string | null>(null);

  // Spell checking state
  const [selectedUnitsForCheck, setSelectedUnitsForCheck] = useState<
    Set<string>
  >(() => new Set());
  const [spellCheckProviderId, setSpellCheckProviderId] =
    useState<string>("default");
  const [localCheck, setLocalCheck] = useState<DetectionResponse | null>(null);

  // Downloading derivative state
  const [downloadingType, setDownloadingType] = useState<
    "md" | "json" | "zip" | "raw" | "pdf" | null
  >(null);

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
    if (!selectedRunId) {
      const fallbackRunId = runs[0]?.id ?? source?.processing?.id ?? null;
      if (fallbackRunId) {
        setSelectedRunId(fallbackRunId);
        onSearchChange?.({ runId: fallbackRunId });
      }
    }
  }, [selectedRunId, runs, source?.processing?.id, onSearchChange]);

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
    selectedVersion,
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
  const baseMovedOn = doc
    ? draft.baseMovedOn({ version: doc.version, sha256: doc.canonical_sha256 })
    : false;

  // Compute pending changes strictly where after !== unit.text
  const pendingChanges = useMemo<TextChange[]>(() => {
    if (!doc) return [];
    const changes: TextChange[] = [];
    for (const unit of doc.units) {
      if (draftChanges.has(unit.evidence_id)) {
        const after = draftChanges.get(unit.evidence_id);
        if (after !== undefined && after !== unit.text) {
          changes.push({
            evidence_id: unit.evidence_id,
            before: unit.text,
            after,
          });
        }
      }
    }
    return changes;
  }, [doc, draftChanges]);

  const draftCount = pendingChanges.length;
  const hasUnsavedDraft = draftCount > 0;

  // Warn before leaving page when unsaved draft exists
  const shouldBlockLeave = useCallback(() => {
    if (!hasUnsavedDraft) return false;
    return !window.confirm(
      "Bạn có thay đổi hiệu đính chưa lưu. Bản nháp vẫn được giữ trong phiên làm việc này nhưng chưa ghi lên máy chủ. Tiếp tục rời trang?",
    );
  }, [hasUnsavedDraft]);

  useBlocker({
    shouldBlockFn: shouldBlockLeave,
    enableBeforeUnload: () => hasUnsavedDraft,
    disabled: !hasUnsavedDraft,
  });

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
  const documentSpelling = useDocumentSpelling(
    `${workspaceId}/${activeRevisionId}/${selectedRunId}/${doc?.version}/${doc?.canonical_sha256}/${selectedVersion}`,
    current,
    detectMutation.mutateAsync,
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
    if (!canManage) return;
    try {
      const res = await requestRunMutation.mutateAsync({
        strategy: "auto",
        force,
      });

      if (!current()) return;
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
      if (!current()) return;
      toast.error(
        err instanceof ApiProblemError
          ? err.message
          : "Không thể bắt đầu bóc tách tài liệu.",
      );
    }
  };

  // Revert single unit draft
  const handleRevertUnitDraft = (evidenceId: string) => {
    if (!canManage) return;
    draft.update((prev) => {
      const next = new Map(prev);
      next.delete(evidenceId);
      return next;
    });
    setActiveSaveKey(generateIdempotencyKey());
  };

  // Discard all drafts
  const handleDiscardAllDrafts = () => {
    if (!canManage) return;
    draft.clear();
    setActiveSaveKey(generateIdempotencyKey());
    setConflictError(null);
    toast.info("Đã hủy toàn bộ thay đổi nháp.");
  };

  // Save Review Drafts to Server
  const handleConfirmSave = async () => {
    if (!canManage || !doc || !selectedRunId || pendingChanges.length === 0) {
      return;
    }
    if (
      draft.baseMovedOn({ version: doc.version, sha256: doc.canonical_sha256 })
    ) {
      setSaveModalOpen(false);
      toast.error(
        "Căn cứ của bản nháp đã thay đổi. Hãy đối chiếu và chọn cách xử lý trước khi lưu.",
      );
      return;
    }

    try {
      const updated = await saveMutation.mutateAsync({
        body: {
          expected_version: draft.draft?.baseVersion ?? doc.version,
          expected_sha256: draft.draft?.baseSha256 ?? doc.canonical_sha256,
          changes: pendingChanges,
        },
        idempotencyKey: activeSaveKey,
      });

      if (!current()) return;
      setSelectedVersion(updated.version);
      draft.clear();
      setSaveModalOpen(false);
      setConflictError(null);
      setActiveSaveKey(generateIdempotencyKey());
      toast.success(`Đã lưu phiên bản hiệu đính mới (v${updated.version}).`);
    } catch (err) {
      if (!current()) return;
      if (err instanceof ApiProblemError) {
        if (err.code === "ocr_text_version_conflict") {
          setConflictError(
            "Xung đột phiên bản: Nội dung đã có bản mới được lưu trên máy chủ. Bản nháp của bạn vẫn được giữ nguyên — vui lòng tải lại dữ liệu mới nhất để đối chiếu.",
          );
        } else {
          toast.error(formatOcrError(err.code, err.message));
        }
      } else {
        toast.error("Không thể lưu thay đổi hiệu đính.");
      }
    }
  };

  // Open Spell Check configuration dialog (never dispatches or slices silently)
  const handleOpenSpellCheckConfig = (initialUnitIds?: string[]) => {
    if (!canManage || !doc || documentSpelling.running) return;
    if (initialUnitIds && initialUnitIds.length > 0) {
      setWholeDocumentCheck(false);
      setSelectedUnitsForCheck(new Set(initialUnitIds));
    } else {
      setWholeDocumentCheck(true);
      setSelectedUnitsForCheck(
        new Set(selectableSpellingUnits(doc).map((u) => u.evidence_id)),
      );
    }
    setActiveSpellKey(generateIdempotencyKey());
    setSpellCheckConfigOpen(true);
  };

  // Execute Spell Check after user confirms scope & model in dialog
  const handleRunSpellCheck = async () => {
    if (!canManage || !doc || !selectedRunId) return;
    const units = wholeDocumentCheck
      ? doc.units
      : doc.units.filter((unit) => selectedUnitsForCheck.has(unit.evidence_id));
    if (units.length === 0) return;
    setMobilePane("spelling");
    const result = await documentSpelling.start(
      { ...doc, units },
      activeSpellKey,
      spellCheckProviderId === "default" ? null : spellCheckProviderId,
      selectedVersion,
    );
    if (!current() || !result) return;
    setSpellCheckConfigOpen(false);
    setActiveSpellKey(generateIdempotencyKey());
    const onlyBatch =
      result.batches.length === 1 ? result.batches[0] : undefined;
    const check = onlyBatch?.check;
    if (!wholeDocumentCheck && onlyBatch?.status === "completed" && check) {
      setLocalCheck(check);
      onSearchChange?.({
        revisionId: activeRevisionId,
        runId: selectedRunId,
        checkId: check.id,
        page: activePage,
      });
    }
    const incomplete = result.batches.filter(
      (batch) => batch.status !== "completed",
    ).length;
    if (incomplete) {
      toast.warning(
        `Còn ${incomplete} nhóm lỗi hoặc chưa chạy. Xem báo cáo chi tiết.`,
      );
    } else {
      toast.success(
        "Đã kiểm tra xong phạm vi đã chọn. Xem báo cáo để đối chiếu gợi ý.",
      );
    }
  };

  // Apply suggestion from spell check into draft
  const handleApplySuggestion = (s: Suggestion): boolean => {
    if (!canManage || !doc || baseMovedOn || !current()) return false;
    const targetUnit = doc.units.find((u) => u.evidence_id === s.evidence_id);
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
    setActiveSaveKey(generateIdempotencyKey());
    toast.success(
      `Đã áp dụng thay đổi "${s.original}" → "${s.replacement}" vào bản nháp.`,
    );
    return true;
  };

  // Locate unit on page and highlight bbox
  const handleLocateUnit = ({
    evidenceId,
    page,
  }: {
    evidenceId: string;
    page?: number;
  }) => {
    const unit = doc?.units.find((u) => u.evidence_id === evidenceId);
    const targetPage = page ?? unit?.page;
    if (targetPage && targetPage !== activePage) {
      handlePageChange(targetPage);
    }
    setFocusedEvidenceId(evidenceId);
    setLocateRequestNonce((n) => n + 1);
    if (mobilePane === "spelling") {
      setMobilePane("image");
    }
  };

  // Jump to unit and open manual edit dialog
  const handleManualEditUnit = (evidenceId: string, page?: number) => {
    if (!canManage) return;
    const unit = doc?.units.find((u) => u.evidence_id === evidenceId);
    const targetPage = page ?? unit?.page;
    if (targetPage && targetPage !== activePage) {
      handlePageChange(targetPage);
    }
    setFocusedEvidenceId(evidenceId);
    setExternalEditUnitId(evidenceId);
    if (mobilePane === "spelling") {
      setMobilePane("content");
    }
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
      const versionParam = selectedVersion ?? doc?.version;

      if (type === "md") {
        const res = await downloadReviewMarkdownBlob(
          v1Client,
          workspaceId,
          collectionId,
          sourceId,
          activeRevisionId,
          selectedRunId,
          versionParam,
        );
        blob = res.blob;
        filename += versionParam !== undefined ? `_v${versionParam}.md` : ".md";
      } else if (type === "json") {
        const res = await downloadReviewDocumentBlob(
          v1Client,
          workspaceId,
          collectionId,
          sourceId,
          activeRevisionId,
          selectedRunId,
          versionParam,
        );
        blob = res.blob;
        filename +=
          versionParam !== undefined ? `_v${versionParam}.json` : ".json";
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
  const activeCheckId = search?.checkId;
  const hasActiveSpellingResult = Boolean(
    doc && (activeCheckId || localCheck || documentSpelling.report),
  );
  const spellingSuggestionsCount = documentSpelling.report
    ? documentSpelling.report.batches.reduce(
        (n, b) =>
          n +
          (b.check?.suggestions.length ?? 0) +
          (b.check?.withheld_suggestions?.length ?? 0),
        0,
      )
    : (localCheck?.suggestions.length ?? 0) +
      (localCheck?.withheld_suggestions?.length ?? 0);

  const lifecycleDialog = lifecycleOp ? (
    <LifecycleActionDialog
      key="source-lifecycle"
      workspaceId={workspaceId}
      target={{ kind: "source", resource_id: sourceId, action: lifecycleOp }}
      label={source?.title ?? "Tài liệu"}
      onClose={() => {
        setLifecycleOp(null);
        if (!source || sourceQuery.isError)
          void navigate({
            to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
            params: { workspaceId, knowledgeId: collectionId },
            search: { page: 1, pageSize: 20 },
          });
      }}
      onCompleted={() => {
        toast.success(
          lifecycleOp === "delete"
            ? "Đã xóa vĩnh viễn tài liệu."
            : "Đã lưu trữ tài liệu.",
        );
        void navigate({
          to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
          params: { workspaceId, knowledgeId: collectionId },
          search: { page: 1, pageSize: 20 },
        });
      }}
    />
  ) : null;

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
    if (lifecycleOp) return <div className="space-y-4">{lifecycleDialog}</div>;
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
      {lifecycleDialog}
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
              {collection?.name ?? "Bộ sưu tập"}
            </Link>
            <ChevronRight className="size-3 text-muted-foreground/60" />
            <span className="font-semibold text-foreground truncate max-w-[220px]">
              {source.title}
            </span>
          </div>

          {/* Tiêu đề, phiên bản tệp & badge trạng thái */}
          <div className="flex items-center gap-2.5 flex-wrap">
            <FileText className="size-5 text-primary shrink-0" />
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground truncate max-w-[400px]">
              {source.title}
            </h1>
            <Badge variant="outline" className="text-xs font-mono h-5">
              Tệp v{activeRevisionNo}
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

            {!canManage ? (
              <Badge variant="outline" className="text-xs font-normal h-5">
                Chế độ chỉ xem
              </Badge>
            ) : null}
          </div>
        </div>

        {/* Hàng hành động tinh gọn: Hành động chính theo ngữ cảnh + Menu phụ ⋯ */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          {canManage && statusInfo.status === "unprocessed" ? (
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
          ) : null}

          {/* Kiểm tra chính tả (mở hộp thoại chọn phạm vi & mô hình) */}
          {canManage && statusInfo.status === "completed" && doc ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-9 text-xs gap-1.5"
              disabled={detectMutation.isPending || documentSpelling.running}
              onClick={() => handleOpenSpellCheckConfig()}
            >
              {detectMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin text-primary" />
              ) : (
                <Sparkles className="size-3.5 text-primary" />
              )}
              <span>Kiểm tra chính tả</span>
            </Button>
          ) : null}

          {/* Lưu thay đổi (nổi bật khi có nháp hiệu đính) */}
          {canManage && statusInfo.status === "completed" ? (
            <Button
              type="button"
              size="sm"
              variant={hasUnsavedDraft ? "default" : "outline"}
              className="h-9 text-xs gap-1.5"
              disabled={
                !hasUnsavedDraft || saveMutation.isPending || baseMovedOn
              }
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
          ) : null}

          {/* Dùng để biên soạn (từ đúng phiên bản đã lưu) */}
          {canCompile && statusInfo.status === "completed" && selectedRunId ? (
            <Button
              type="button"
              size="sm"
              variant={hasUnsavedDraft ? "outline" : "default"}
              className="h-9 text-xs gap-1.5"
              onClick={() => {
                if (hasUnsavedDraft) {
                  toast.warning(
                    `Bạn đang có ${draftCount} đoạn sửa nháp chưa lưu. Trình biên soạn chỉ sử dụng phiên bản đã lưu trên máy chủ (v${doc?.version ?? 0}). Vui lòng bấm "Lưu thay đổi" trước khi biên soạn.`,
                  );
                  return;
                }
                setCompilationDialogOpen(true);
              }}
            >
              <ClipboardList className="size-3.5" />
              <span>Dùng để biên soạn</span>
            </Button>
          ) : null}

          {/* Menu phụ ⋯ gom Tải xuống (bản gốc/MD/JSON/ZIP), Bóc tách lại, Tải phiên bản mới và Thao tác vòng đời */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="size-9 p-0 text-muted-foreground hover:text-foreground"
                aria-label="Thao tác tài liệu"
              >
                {downloadingType ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <MoreHorizontal className="size-4" />
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-60 text-xs">
              <DropdownMenuItem
                className="gap-2"
                disabled={downloadingType !== null}
                onClick={() => void handleDownload("raw")}
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
                onClick={() => void handleDownload("md")}
              >
                <Download className="size-3.5 text-muted-foreground" />
                <span>Tải bản Markdown (.md)</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="gap-2"
                disabled={
                  statusInfo.status !== "completed" || downloadingType !== null
                }
                onClick={() => void handleDownload("json")}
              >
                <Download className="size-3.5 text-muted-foreground" />
                <span>Tải bản JSON cấu trúc (.json)</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="gap-2"
                disabled={
                  statusInfo.status !== "completed" || downloadingType !== null
                }
                onClick={() => void handleDownload("zip")}
              >
                <Download className="size-3.5 text-muted-foreground" />
                <span>Tải gói ZIP kèm ảnh (.zip)</span>
              </DropdownMenuItem>
              {isDocxFile && statusInfo.status === "completed" && (
                <DropdownMenuItem
                  className="gap-2"
                  disabled={downloadingType !== null}
                  onClick={() => void handleDownload("pdf")}
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
                      onClick={() => setReRunConfirmOpen(true)}
                    >
                      <RotateCcw className="size-3.5 text-muted-foreground" />
                      <span>Bóc tách lại</span>
                    </DropdownMenuItem>
                  ) : null}

                  <DropdownMenuItem
                    className="gap-2"
                    onClick={() => setUploadRevisionOpen(true)}
                  >
                    <FilePlus2 className="size-3.5 text-muted-foreground" />
                    <span>Tải phiên bản mới</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="gap-2"
                    onClick={() => setRenameSourceOpen(true)}
                  >
                    <Pencil className="size-3.5 text-muted-foreground" />
                    <span>Đổi tên tài liệu</span>
                  </DropdownMenuItem>
                </>
              ) : null}
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

      {/* Thanh trạng thái Phiên bản Văn bản & Bản nháp Hiệu đính */}
      {statusInfo.status === "completed" && doc ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card px-3.5 py-2.5 text-xs shadow-2xs">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <History className="size-3.5 text-primary" />
              <span>Phiên bản văn bản:</span>
            </span>
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
                  draft.clear();
                }
                setSelectedVersion(val === "latest" ? null : Number(val));
              }}
            >
              <SelectTrigger
                aria-label="Phiên bản văn bản"
                className="h-8 text-xs w-[170px]"
              >
                <SelectValue placeholder="Chọn phiên bản" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="latest" className="text-xs">
                  Mới nhất (v{doc.version})
                </SelectItem>
                <SelectItem value="0" className="text-xs">
                  v0 (OCR gốc ban đầu)
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
              <div className="flex items-center gap-1.5">
                <Badge variant="warning" className="text-[11px] py-0">
                  Bản nháp: {draftCount} đoạn chưa lưu
                </Badge>
                {canManage ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-destructive"
                    onClick={handleDiscardAllDrafts}
                  >
                    <Undo2 className="size-3" />
                    <span>Hủy nháp</span>
                  </Button>
                ) : null}
              </div>
            ) : (
              <Badge variant="secondary" className="text-[11px] py-0">
                Đã lưu (v{doc.version}) · Không có nháp chưa lưu
              </Badge>
            )}
          </div>

          <p className="text-[11px] text-muted-foreground">
            Quy trình: AI gợi ý sửa → Áp dụng vào{" "}
            <strong className="text-foreground">Bản nháp</strong> →{" "}
            <strong className="text-foreground">Lưu thay đổi</strong> tạo phiên
            bản mới →{" "}
            <strong className="text-foreground">Dùng để biên soạn</strong>.
          </p>
        </div>
      ) : null}

      {/* Cảnh báo khi phiên bản trên máy chủ đã tiến lên sau khi tạo nháp */}
      {baseMovedOn && doc ? (
        <Alert className="border-warning/50 bg-warning/10 text-foreground py-3">
          <AlertTriangle className="size-4 text-warning" />
          <AlertTitle className="text-xs font-semibold">
            Bản nháp thuộc phiên bản v{draft.draft?.baseVersion} nhưng máy chủ
            đã có v{doc.version}
          </AlertTitle>
          <AlertDescription className="text-xs mt-1 space-y-2">
            <p>
              Nội dung trên máy chủ đã thay đổi sau khi bạn bắt đầu sửa. Hệ
              thống không tự động đổi căn cứ của bản nháp để tránh ghi đè thay
              đổi của người khác.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => {
                  if (
                    window.confirm(
                      `Áp dụng bản nháp hiện tại lên phiên bản v${doc.version}?`,
                    )
                  ) {
                    draft.rebase({
                      version: doc.version,
                      sha256: doc.canonical_sha256,
                    });
                    setActiveSaveKey(generateIdempotencyKey());
                  }
                }}
              >
                Áp dụng nháp lên v{doc.version}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-7 text-xs text-muted-foreground hover:text-destructive"
                onClick={() => draft.clear()}
              >
                Hủy nháp và dùng bản mới
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ) : null}

      {/* Cảnh báo xung đột phiên bản khi bấm Lưu */}
      {conflictError ? (
        <Alert variant="destructive" className="py-3">
          <AlertCircle className="size-4" />
          <AlertTitle className="text-xs font-semibold">
            Xung đột phiên bản khi lưu
          </AlertTitle>
          <AlertDescription className="text-xs mt-1 space-y-2">
            <p>{conflictError}</p>
            <div className="flex items-center gap-2 pt-1">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => void textReviewQuery.refetch()}
              >
                Tải lại dữ liệu mới nhất
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-7 text-xs"
                onClick={() => setConflictError(null)}
              >
                Đóng
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ) : null}

      {/* Thanh tiến độ dùng chung khi đang bóc tách / chờ xử lý */}
      {activeProcessing &&
      (activeProcessing.status === "queued" ||
        activeProcessing.status === "running" ||
        activeProcessing.dispatch_pending === true ||
        (activeProcessing.status === "completed" &&
          activeProcessing.results_ready === false)) ? (
        <ProcessingProgress
          progress={{
            status: activeProcessing.status,
            pages_total: activeProcessing.pages_total,
            pages_done: activeProcessing.pages_done,
            pages_failed: activeProcessing.pages_failed,
            results_ready:
              "results_ready" in activeProcessing
                ? activeProcessing.results_ready
                : true,
            dispatch_pending:
              "dispatch_pending" in activeProcessing
                ? activeProcessing.dispatch_pending
                : false,
            error_code: activeProcessing.error_code,
            error_detail:
              "error_detail" in activeProcessing
                ? activeProcessing.error_detail
                : null,
          }}
          isPollError={runDetailQuery.isError || sourceQuery.isError}
        />
      ) : null}

      {/* Cảnh báo lỗi bóc tách nếu có */}
      {activeRun && ["failed", "uncertain"].includes(activeRun.status) && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="size-4" />
          <AlertTitle>Bóc tách chưa thành công</AlertTitle>
          <AlertDescription className="text-xs mt-1 space-y-1">
            <p>
              {formatOcrError(activeRun.error_code, activeRun.error_detail)}
            </p>
            {activeRun.error_code && (
              <details className="text-muted-foreground">
                <summary className="cursor-pointer select-none">
                  Chi tiết kỹ thuật
                </summary>
                <span className="block font-mono text-xs mt-0.5">
                  Mã lỗi: {activeRun.error_code}
                </span>
              </details>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* 2. MÀN ĐỐI CHIẾU HAI CỘT: Cột trái: Đối chiếu OCR / Xem tệp gốc | Cột phải: Văn bản & Gợi ý chính tả */}
      <OcrComparisonView
        workspaceId={workspaceId}
        collectionId={collectionId}
        sourceId={sourceId}
        revisionId={activeRevisionId}
        run={activeRun ?? null}
        pages={activeRun?.pages ?? []}
        activePageNumber={activePage}
        onPageChange={handlePageChange}
        reviewDoc={doc}
        isDocx={isDocxFile}
        canManage={canManage}
        draftChanges={draftChanges}
        onSaveDraftChange={(evidenceId, _before, after) => {
          if (!canManage) return;
          draft.update((prev) => {
            const next = new Map(prev);
            next.set(evidenceId, after);
            return next;
          });
          setActiveSaveKey(generateIdempotencyKey());
        }}
        onRevertUnitDraft={handleRevertUnitDraft}
        onStartSpellCheck={(unitIds) => handleOpenSpellCheckConfig(unitIds)}
        selectedUnitIds={selectedUnitsForCheck}
        onToggleUnitSelection={(evidenceId) => {
          if (!canManage) return;
          setSelectedUnitsForCheck((prev) => {
            const next = new Set(prev);
            if (next.has(evidenceId)) {
              next.delete(evidenceId);
            } else {
              next.add(evidenceId);
            }
            return next;
          });
          setActiveSpellKey(generateIdempotencyKey());
        }}
        onSelectPageUnits={(evidenceIds, selected) => {
          if (!canManage) return;
          setSelectedUnitsForCheck((prev) => {
            const next = new Set(prev);
            for (const id of evidenceIds) {
              if (selected) {
                next.add(id);
              } else {
                next.delete(id);
              }
            }
            return next;
          });
          setActiveSpellKey(generateIdempotencyKey());
        }}
        focusedEvidenceId={focusedEvidenceId}
        onFocusUnit={setFocusedEvidenceId}
        locateRequestNonce={locateRequestNonce}
        externalEditUnitId={externalEditUnitId}
        onClearExternalEditUnit={() => setExternalEditUnitId(null)}
        mobilePane={mobilePane}
        onMobilePaneChange={setMobilePane}
        spellingSuggestionsCount={spellingSuggestionsCount}
        unprocessedRightPanel={
          <div className="p-6 text-center space-y-4 max-w-md mx-auto">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary mx-auto">
              <Play className="size-7" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-base font-semibold text-foreground">
                Tài liệu đã được lưu trữ an toàn
              </h3>
              <p className="text-xs text-muted-foreground">
                Tài liệu này chưa được bóc tách. Bạn có thể đọc trực tiếp ở chế
                độ <strong className="text-foreground">Xem tệp gốc</strong> bên
                trái, hoặc nhấn &ldquo;Bắt đầu bóc tách&rdquo; để trích xuất văn
                bản, cấu trúc bảng và ảnh đối chiếu.
              </p>
            </div>
            {canManage ? (
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
            ) : null}
          </div>
        }
        spellingPanel={
          documentSpelling.report && doc ? (
            <DocumentSpellingReport
              report={documentSpelling.report}
              workspaceId={workspaceId}
              collectionId={collectionId}
              sourceId={sourceId}
              revisionId={activeRevisionId}
              runId={selectedRunId ?? ""}
              doc={doc}
              draftChanges={draftChanges}
              canManage={canManage && !baseMovedOn}
              onApply={handleApplySuggestion}
              onLocateUnit={handleLocateUnit}
              onManualEditUnit={handleManualEditUnit}
              onRevertUnitDraft={handleRevertUnitDraft}
              focusedEvidenceId={focusedEvidenceId}
            />
          ) : hasActiveSpellingResult && doc ? (
            <SpellingResultPanel
              workspaceId={workspaceId}
              collectionId={collectionId}
              sourceId={sourceId}
              revisionId={activeRevisionId}
              runId={selectedRunId ?? ""}
              checkId={activeCheckId}
              localCheck={localCheck}
              doc={doc}
              draftChanges={draftChanges}
              canManage={canManage && !baseMovedOn}
              onApply={handleApplySuggestion}
              onLocateUnit={handleLocateUnit}
              onManualEditUnit={handleManualEditUnit}
              onRevertUnitDraft={handleRevertUnitDraft}
              focusedEvidenceId={focusedEvidenceId}
            />
          ) : null
        }
      />

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
              Thao tác này sẽ tạo một lượt bóc tách mới cho phiên bản tài liệu
              hiện hành. Kết quả và bằng chứng của các lượt trước được bảo toàn
              bất biến trong lịch sử.
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
      {doc ? (
        <OcrSaveConfirmDialog
          open={saveModalOpen}
          onOpenChange={setSaveModalOpen}
          doc={doc}
          pendingChanges={pendingChanges}
          baseMovedOn={baseMovedOn}
          isSaving={saveMutation.isPending}
          onConfirmSave={() => void handleConfirmSave()}
        />
      ) : null}

      {/* Modal Cấu hình & Gửi Kiểm tra Chính tả AI */}
      {doc ? (
        <OcrSpellCheckDialog
          open={spellCheckConfigOpen}
          onOpenChange={setSpellCheckConfigOpen}
          workspaceId={workspaceId}
          doc={doc}
          activePage={activePage}
          selectedUnitIds={selectedUnitsForCheck}
          onChangeSelectedUnitIds={(next) => {
            setSelectedUnitsForCheck(next);
            setActiveSpellKey(generateIdempotencyKey());
          }}
          providerId={spellCheckProviderId}
          onChangeProviderId={(nextProvider) => {
            setSpellCheckProviderId(nextProvider);
            setActiveSpellKey(generateIdempotencyKey());
          }}
          pendingDraftCount={pendingChanges.length}
          isSubmitting={detectMutation.isPending || documentSpelling.running}
          wholeDocument={wholeDocumentCheck}
          onChangeWholeDocument={setWholeDocumentCheck}
          progress={
            documentSpelling.running && documentSpelling.report ? (
              <DocumentSpellingProgress
                report={documentSpelling.report}
                stopping={documentSpelling.stopping}
                onStop={documentSpelling.stop}
              />
            ) : undefined
          }
          onSubmit={() => void handleRunSpellCheck()}
        />
      ) : null}

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

      {/* Compilation Dialog (từ đúng phiên bản đã lưu) */}
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
            textVersion: selectedVersion ?? doc?.version ?? 0,
          }}
          onSuccess={(runId) => {
            void navigate({
              to: "/workspaces/$workspaceId/collections/$collectionId/compilations/$runId",
              params: { workspaceId, collectionId, runId },
            });
          }}
        />
      )}
    </div>
  );
}
