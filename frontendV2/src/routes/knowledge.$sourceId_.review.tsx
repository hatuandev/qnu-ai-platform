import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createFileRoute,
  Link,
  useBlocker,
  useNavigate,
} from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText,
  Loader2,
  Pencil,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { useMeQuery } from "@/api/auth/queries";
import { ApiProblemError } from "@/api/client";
import {
  getRevisionContentBlob,
  knowledgeKeys,
  useCollectionsQuery,
  useSourceQuery,
  useSourceSummaryQuery,
} from "@/api/knowledge";
import {
  useAcknowledgeOcrWarningsMutation,
  useBulkIgnoreTextReviewSuggestionsMutation,
  useRerunTextReviewMutation,
  useSaveTextReviewMutation,
  useSetTextReviewDispositionMutation,
  useTextReviewChecksQuery,
  useTextReviewQuery,
} from "@/api/ocr/queries";
import type { ReviewDocument, Suggestion } from "@/api/ocr/requests";
import { useCreatePreparationIntentMutation } from "@/api/preparation/queries";
import { useWorkspaceMembersQuery } from "@/api/workspaces/queries";
import { DocxViewer } from "@/components/knowledge/docx-viewer";
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
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { useBackgroundTasksStore } from "@/lib/background-tasks-store";
import { displayDocumentTitle } from "@/lib/knowledge-studio-helpers";
import { isPlatformAdmin } from "@/lib/permissions";
import {
  buildTextChanges,
  type SuggestionDecision,
  splitTextAtSuggestion,
} from "@/lib/spelling-replacement-helpers";
import {
  currentSpellingCheck,
  formatSpellingMoment,
  spellingCoverage,
  spellingPercent,
  spellingScope,
} from "@/lib/spelling-review";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

const reviewSearchSchema = z.object({
  collectionId: z.string().optional(),
  revisionId: z.string().optional(),
  runId: z.string().optional(),
});

export const Route = createFileRoute("/knowledge/$sourceId_/review")({
  validateSearch: (search) => reviewSearchSchema.parse(search),
  component: SpellingReviewPage,
});

function SpellingReviewPage() {
  const { sourceId } = Route.useParams();
  const { collectionId, revisionId, runId } = Route.useSearch();
  const workspaceId = useUiStore((s) => s.activeWorkspaceId);
  return (
    <SpellingReviewWorkspace
      key={JSON.stringify([
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
      ])}
    />
  );
}

function SpellingReviewWorkspace() {
  const { sourceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const registerBackgroundTask = useBackgroundTasksStore(
    (s) => s.registerPreparationTask,
  );
  const activeWorkspaceId = useUiStore((s) => s.activeWorkspaceId);

  // 1. Resolve collection & source
  const { data: collections } = useCollectionsQuery(activeWorkspaceId);
  const resolvedCollectionId = useMemo(() => {
    if (search.collectionId) return search.collectionId;
    if (collections?.items && collections.items.length > 0) {
      return collections.items[0].id;
    }
    return "";
  }, [search.collectionId, collections]);

  const { data: source } = useSourceQuery(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
  );

  const { data: summary } = useSourceSummaryQuery(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
  );

  const scope = spellingScope(summary, search.runId);
  const activeRevisionId = search.revisionId ?? scope?.revisionId;
  const ocrRunId = search.runId ?? scope?.runId;
  const [isRecheckPending, setIsRecheckPending] = useState(false);

  // 2. One working text per source: always the latest saved text.
  const {
    data: reviewDoc,
    isLoading: isReviewDocLoading,
    isFetching: isReviewFetching,
    isError: hasReviewError,
    refetch: refetchReview,
  } = useTextReviewQuery(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
    activeRevisionId,
    ocrRunId,
  );

  const {
    data: checks,
    isLoading: isChecksLoading,
    isFetching: isChecksFetching,
    error: checksError,
    refetch: refetchChecks,
  } = useTextReviewChecksQuery(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
    activeRevisionId,
    ocrRunId,
    undefined,
    {
      shouldPoll: (items) =>
        isRecheckPending ||
        Boolean(
          items?.some(
            (check) =>
              check.status === "running" &&
              (reviewDoc?.version === undefined ||
                check.version === reviewDoc.version),
          ),
        ),
    },
  );

  const hasLoadError = hasReviewError || Boolean(checksError);
  const isLoadingReview = isReviewDocLoading || isChecksLoading;
  const isChecksUnsupported =
    checksError instanceof ApiProblemError && checksError.status === 405;

  const latestCheck = useMemo(
    () => currentSpellingCheck(checks, reviewDoc?.version),
    [checks, reviewDoc?.version],
  );
  const isReviewed = latestCheck?.reviewed_at != null;
  const coverage = latestCheck ? spellingCoverage(latestCheck) : null;
  const percent = coverage
    ? spellingPercent(coverage.checked, coverage.total)
    : null;

  // All suggestions from the check
  const allSuggestions: Suggestion[] = useMemo(() => {
    return latestCheck?.suggestions || [];
  }, [latestCheck]);

  // Withheld suggestions (cần đối chiếu bản gốc)
  const withheldSuggestions: Suggestion[] = useMemo(() => {
    return latestCheck?.withheld_suggestions || [];
  }, [latestCheck]);

  // Decisions map: key = `${evidence_id}:${start}:${end}`
  const [decisions, setDecisions] = useState<Map<string, SuggestionDecision>>(
    new Map(),
  );

  // Filters: "pending" | "applied" | "ignored" | "withheld" | "all"
  const [filter, setFilter] = useState<
    "pending" | "applied" | "ignored" | "withheld" | "all"
  >("pending");

  // Selection
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Manual editing state
  const [isEditingManually, setIsEditingManually] = useState(false);
  const [manualEditText, setManualEditText] = useState("");

  // Server-persisted "Bỏ qua" is restored whenever the shown check changes.
  const seededCheckIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (!latestCheck) return;
    if (seededCheckIdRef.current === latestCheck.id) return;
    seededCheckIdRef.current = latestCheck.id;
    const restored = new Map<string, SuggestionDecision>();
    for (const ignored of latestCheck.ignored_suggestions ?? []) {
      restored.set(`${ignored.evidence_id}:${ignored.start}:${ignored.end}`, {
        status: "ignored",
      });
    }
    setDecisions(restored);
    setSelectedIndex(0);
    setIsEditingManually(false);
  }, [latestCheck]);

  // Completion state
  const [isSaving, setIsSaving] = useState(false);
  const [isCompleteDialogOpen, setIsCompleteDialogOpen] = useState(false);
  const [recheckRetry, setRecheckRetry] = useState<boolean | null>(null);
  const saveAttempt = useRef<{ signature: string; key: string } | null>(null);

  // Original document preview (toggleable panel)
  const [showOriginalFile, setShowOriginalFile] = useState(false);
  const [preview, setPreview] = useState<{ blob: Blob; url: string } | null>(
    null,
  );
  const { data: originalFile, isLoading: blobLoading } = useQuery({
    queryKey: [
      "revision-content",
      activeWorkspaceId,
      resolvedCollectionId,
      sourceId,
      activeRevisionId,
    ],
    queryFn: ({ signal }) => {
      if (!activeWorkspaceId || !activeRevisionId)
        throw new Error("Thiếu phiên bản tệp.");
      return getRevisionContentBlob(
        activeWorkspaceId,
        resolvedCollectionId,
        sourceId,
        activeRevisionId,
        { signal },
      );
    },
    enabled: Boolean(
      showOriginalFile &&
        activeWorkspaceId &&
        resolvedCollectionId &&
        activeRevisionId,
    ),
  });
  const docBlob = originalFile?.blob;
  const blobUrl = preview?.blob === docBlob ? preview?.url : undefined;

  // Mutations
  const saveReviewMutation = useSaveTextReviewMutation(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
    activeRevisionId,
    ocrRunId,
  );

  const rerunReviewMutation = useRerunTextReviewMutation(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
    activeRevisionId,
    ocrRunId,
  );

  const dispositionMutation = useSetTextReviewDispositionMutation(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
    activeRevisionId,
    ocrRunId,
  );

  const bulkIgnoreMutation = useBulkIgnoreTextReviewSuggestionsMutation(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
    activeRevisionId,
    ocrRunId,
  );

  const createIntentMutation = useCreatePreparationIntentMutation(
    activeWorkspaceId,
    resolvedCollectionId,
  );

  const ackWarningsMutation = useAcknowledgeOcrWarningsMutation(
    activeWorkspaceId,
    resolvedCollectionId,
    sourceId,
    activeRevisionId,
    ocrRunId,
  );
  const meQuery = useMeQuery();
  const membersQuery = useWorkspaceMembersQuery(activeWorkspaceId);
  const [isAckDialogOpen, setIsAckDialogOpen] = useState(false);
  const [ackReason, setAckReason] = useState("");

  const imageFailures = useMemo(
    () => reviewDoc?.image_ocr_failures ?? [],
    [reviewDoc],
  );
  const failedPages = useMemo(
    () =>
      [...new Set(imageFailures.map((failure) => failure.page))].sort(
        (a, b) => a - b,
      ),
    [imageFailures],
  );
  const canAcknowledgeWarnings = useMemo(() => {
    const actor = meQuery.data?.actor;
    if (isPlatformAdmin(actor)) return true;
    if (!actor) return false;
    const members = membersQuery.data?.items ?? [];
    return members.some(
      (member) =>
        member.actor_ref === actor.actor_id &&
        member.role === "admin" &&
        member.status === "active",
    );
  }, [meQuery.data, membersQuery.data]);

  const handleAcknowledgeWarnings = async () => {
    if (!activeWorkspaceId) return;
    const reason = ackReason.trim();
    if (reason.length < 5) {
      toast.error("Vui lòng nhập lý do ít nhất 5 ký tự.");
      return;
    }
    try {
      const result = await ackWarningsMutation.mutateAsync({ reason });
      toast.success(
        result.created
          ? "Đã ghi nhận xác nhận cảnh báo."
          : "Cảnh báo này đã được xác nhận trước đó.",
      );
      setIsAckDialogOpen(false);
      setAckReason("");
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: knowledgeKeys.sourceSummary(
            activeWorkspaceId,
            resolvedCollectionId,
            sourceId,
          ),
        }),
        queryClient.invalidateQueries({
          queryKey: knowledgeKeys.source(
            activeWorkspaceId,
            resolvedCollectionId,
            sourceId,
          ),
        }),
      ]);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Không thể xác nhận cảnh báo ảnh OCR.",
      );
    }
  };

  useEffect(() => {
    if (!docBlob) return;
    const url = URL.createObjectURL(docBlob);
    setPreview({ blob: docBlob, url });
    return () => URL.revokeObjectURL(url);
  }, [docBlob]);

  // After approval every remaining suggestion was applied or ignored; show it
  // as handled instead of pretending it is still waiting for a decision.
  const viewDecisions = useMemo(() => {
    if (!isReviewed) return decisions;
    const next = new Map(decisions);
    for (const s of [...allSuggestions, ...withheldSuggestions]) {
      const key = `${s.evidence_id}:${s.start}:${s.end}`;
      if (!next.has(key)) next.set(key, { status: "applied" });
    }
    return next;
  }, [allSuggestions, decisions, isReviewed, withheldSuggestions]);

  // Filtered list of suggestions
  const filteredSuggestions = useMemo(() => {
    if (filter === "withheld") {
      return withheldSuggestions.filter(
        (s) =>
          viewDecisions.get(`${s.evidence_id}:${s.start}:${s.end}`)?.status !==
          "ignored",
      );
    }

    if (filter === "ignored") {
      const seen = new Set<string>();
      const result: Suggestion[] = [];
      for (const s of [...withheldSuggestions, ...allSuggestions]) {
        const key = `${s.evidence_id}:${s.start}:${s.end}`;
        if (seen.has(key)) continue;
        seen.add(key);
        if (viewDecisions.get(key)?.status === "ignored") result.push(s);
      }
      return result;
    }

    return allSuggestions.filter((s) => {
      const key = `${s.evidence_id}:${s.start}:${s.end}`;
      const d = viewDecisions.get(key);
      const status = d?.status || "pending";

      if (filter === "pending") return status === "pending";
      if (filter === "applied")
        return status === "applied" || status === "custom";
      return true; // "all"
    });
  }, [allSuggestions, withheldSuggestions, viewDecisions, filter]);

  // Clamp selected index when list changes
  useEffect(() => {
    if (selectedIndex >= filteredSuggestions.length) {
      setSelectedIndex(Math.max(0, filteredSuggestions.length - 1));
    }
    setIsEditingManually(false);
  }, [filteredSuggestions.length, selectedIndex]);

  const activeSuggestion = filteredSuggestions[selectedIndex] || null;

  // Counts for tabs
  const counts = useMemo(() => {
    let pending = 0;
    let applied = 0;

    for (const s of allSuggestions) {
      const key = `${s.evidence_id}:${s.start}:${s.end}`;
      const d = viewDecisions.get(key);
      const status = d?.status || "pending";
      if (status === "pending") pending++;
      else if (status === "applied" || status === "custom") applied++;
    }

    const ignoredKeys = new Set<string>();
    for (const s of [...allSuggestions, ...withheldSuggestions]) {
      const key = `${s.evidence_id}:${s.start}:${s.end}`;
      if (viewDecisions.get(key)?.status === "ignored") ignoredKeys.add(key);
    }

    return {
      pending,
      applied,
      ignored: ignoredKeys.size,
      withheld: withheldSuggestions.filter(
        (s) =>
          viewDecisions.get(`${s.evidence_id}:${s.start}:${s.end}`)?.status !==
          "ignored",
      ).length,
      total: allSuggestions.length,
    };
  }, [allSuggestions, withheldSuggestions, viewDecisions]);

  // Every suggestion must be applied, hand-edited or ignored before approval.
  const openSuggestions = useMemo(() => {
    const seen = new Set<string>();
    const result: Suggestion[] = [];
    for (const s of [...allSuggestions, ...withheldSuggestions]) {
      const key = `${s.evidence_id}:${s.start}:${s.end}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (!decisions.has(key)) result.push(s);
    }
    return result;
  }, [allSuggestions, withheldSuggestions, decisions]);

  const remaining = openSuggestions.length;
  const isCheckComplete =
    latestCheck?.status === "completed" && coverage?.complete === true;
  const canComplete =
    Boolean(latestCheck) && !isReviewed && isCheckComplete && remaining === 0;

  // Unsaved changes check
  const hasUnsavedChanges = useMemo(() => {
    for (const d of decisions.values()) {
      if (d.status === "applied" || d.status === "custom") return true;
    }
    return false;
  }, [decisions]);

  // Decision actions
  const makeDecision = useCallback(
    (s: Suggestion, decision: SuggestionDecision) => {
      const key = `${s.evidence_id}:${s.start}:${s.end}`;
      setDecisions((prev) => {
        const next = new Map(prev);
        next.set(key, decision);
        return next;
      });
      setIsEditingManually(false);

      // Auto-advance to next item if available
      if (
        filter !== "pending" &&
        selectedIndex < filteredSuggestions.length - 1
      ) {
        setSelectedIndex((idx) => idx + 1);
      }
    },
    [filter, selectedIndex, filteredSuggestions.length],
  );

  const handleApply = useCallback(() => {
    if (!activeSuggestion) return;
    makeDecision(activeSuggestion, { status: "applied" });
    toast.success(`Đã áp dụng: "${activeSuggestion.replacement}"`);
  }, [activeSuggestion, makeDecision]);

  const handleIgnore = useCallback(() => {
    if (!activeSuggestion || !latestCheck) return;
    const suggestion = activeSuggestion;
    const key = `${suggestion.evidence_id}:${suggestion.start}:${suggestion.end}`;
    const previous = decisions.get(key);
    makeDecision(suggestion, { status: "ignored" });
    dispositionMutation.mutate(
      {
        checkId: latestCheck.id,
        body: {
          evidence_id: suggestion.evidence_id,
          start: suggestion.start,
          end: suggestion.end,
          ignored: true,
        },
      },
      {
        onSuccess: () => {
          toast.info("Đã bỏ qua gợi ý và lưu trạng thái cho lượt soát này.");
        },
        onError: (err) => {
          setDecisions((prev) => {
            const next = new Map(prev);
            if (previous) next.set(key, previous);
            else next.delete(key);
            return next;
          });
          toast.error(
            err instanceof Error
              ? err.message
              : "Không lưu được trạng thái bỏ qua.",
          );
        },
      },
    );
  }, [
    activeSuggestion,
    decisions,
    dispositionMutation,
    latestCheck,
    makeDecision,
  ]);

  const handleCustomSubmit = useCallback(() => {
    const replacement = manualEditText.trim();
    if (!activeSuggestion || !replacement) return;
    if (replacement === activeSuggestion.original) {
      toast.info("Chọn Bỏ qua để giữ nguyên văn.");
      return;
    }
    makeDecision(activeSuggestion, {
      status: "custom",
      customReplacement: replacement,
    });
    toast.success("Đã ghi nhận sửa tay.");
  }, [activeSuggestion, manualEditText, makeDecision]);

  const handleUndo = useCallback(() => {
    if (!activeSuggestion) return;
    const suggestion = activeSuggestion;
    const key = `${suggestion.evidence_id}:${suggestion.start}:${suggestion.end}`;
    const previous = decisions.get(key);
    setDecisions((prev) => {
      const next = new Map(prev);
      next.delete(key);
      return next;
    });
    setIsEditingManually(false);
    if (previous?.status !== "ignored" || !latestCheck) {
      toast.info("Đã hoàn tác quyết định.");
      return;
    }
    dispositionMutation.mutate(
      {
        checkId: latestCheck.id,
        body: {
          evidence_id: suggestion.evidence_id,
          start: suggestion.start,
          end: suggestion.end,
          ignored: false,
        },
      },
      {
        onSuccess: () => {
          toast.info("Đã hoàn tác bỏ qua gợi ý.");
        },
        onError: (err) => {
          setDecisions((prev) => {
            const next = new Map(prev);
            next.set(key, previous);
            return next;
          });
          toast.error(
            err instanceof Error
              ? err.message
              : "Không hoàn tác được trạng thái bỏ qua.",
          );
        },
      },
    );
  }, [activeSuggestion, decisions, dispositionMutation, latestCheck]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.isComposing ||
        event.repeat ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey
      ) {
        return;
      }
      const target = event.target as HTMLElement | null;
      if (
        target?.closest(
          "input, textarea, select, [contenteditable='true'], [role='dialog'], [role='listbox'], [role='menu'], [role='combobox']",
        )
      ) {
        return;
      }
      if (isEditingManually) {
        if (event.key === "Escape") {
          event.preventDefault();
          setIsEditingManually(false);
        }
        return;
      }
      switch (event.key.toLowerCase()) {
        case "j":
        case "arrowright":
          if (filteredSuggestions.length === 0) return;
          event.preventDefault();
          setSelectedIndex((index) =>
            Math.min(filteredSuggestions.length - 1, index + 1),
          );
          break;
        case "k":
        case "arrowleft":
          if (filteredSuggestions.length === 0) return;
          event.preventDefault();
          setSelectedIndex((index) => Math.max(0, index - 1));
          break;
        case "a":
          if (
            !activeSuggestion ||
            filter === "withheld" ||
            isSaving ||
            isReviewed
          ) {
            return;
          }
          event.preventDefault();
          handleApply();
          break;
        case "x":
          if (
            !activeSuggestion ||
            isReviewed ||
            dispositionMutation.isPending
          ) {
            return;
          }
          event.preventDefault();
          handleIgnore();
          break;
        case "e":
          if (!activeSuggestion || isSaving || isReviewed) return;
          event.preventDefault();
          setManualEditText(
            filter === "withheld"
              ? activeSuggestion.original
              : activeSuggestion.replacement,
          );
          setIsEditingManually(true);
          break;
        case "u":
          if (
            !activeSuggestion ||
            !decisions.has(
              `${activeSuggestion.evidence_id}:${activeSuggestion.start}:${activeSuggestion.end}`,
            ) ||
            isSaving ||
            isReviewed ||
            dispositionMutation.isPending
          ) {
            return;
          }
          event.preventDefault();
          handleUndo();
          break;
        case "s":
          if (!canComplete || isSaving) return;
          event.preventDefault();
          setIsCompleteDialogOpen(true);
          break;
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [
    activeSuggestion,
    canComplete,
    decisions,
    dispositionMutation.isPending,
    filter,
    filteredSuggestions.length,
    handleApply,
    handleIgnore,
    handleUndo,
    isEditingManually,
    isReviewed,
    isSaving,
  ]);

  // Unit lookup for displaying full sentence context
  const activeUnit = useMemo(() => {
    if (!activeSuggestion || !reviewDoc?.units) return null;
    return (
      reviewDoc.units.find(
        (u) => u.evidence_id === activeSuggestion.evidence_id,
      ) || null
    );
  }, [activeSuggestion, reviewDoc]);

  const unitPageById = useMemo(() => {
    const pages = new Map<string, number>();
    for (const unit of reviewDoc?.units ?? []) {
      pages.set(unit.evidence_id, unit.page);
    }
    return pages;
  }, [reviewDoc]);

  useBlocker({
    shouldBlockFn: () =>
      hasUnsavedChanges &&
      !isSaving &&
      !window.confirm("Bạn có thay đổi chính tả chưa lưu. Rời trang?"),
    enableBeforeUnload: hasUnsavedChanges && !isSaving,
  });

  useEffect(() => {
    if (
      latestCheck?.status === "running" ||
      latestCheck?.status === "completed"
    ) {
      setIsRecheckPending(false);
    }
  }, [latestCheck?.status]);

  const prepareAfterSave = async (saved: ReviewDocument) => {
    if (!activeWorkspaceId || !activeRevisionId || !saved.version_id) {
      return true;
    }
    try {
      const { intent } = await createIntentMutation.mutateAsync({
        sourceId,
        input: {
          revision_id: activeRevisionId,
          ocr_run_id: saved.run_id,
          text_version: saved.version,
          mode: "auto",
        },
        idempotencyKey: `prepare:spelling:${saved.version_id}`,
      });
      registerBackgroundTask({
        id: intent.id,
        workspaceId: activeWorkspaceId,
        collectionId: resolvedCollectionId,
        sourceId,
        sourceTitle: source?.title || "Tài liệu",
        fileName: source?.file_name || "Tệp",
      });
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.sourceSummary(
          activeWorkspaceId,
          resolvedCollectionId,
          sourceId,
        ),
      });
      return true;
    } catch {
      return false;
    }
  };

  const openRecheckDialog = (retry: boolean) => {
    setRecheckRetry(retry);
  };

  const handleConfirmRecheck = async () => {
    if (recheckRetry === null || !reviewDoc) return;
    try {
      setIsRecheckPending(true);
      const result = await rerunReviewMutation.mutateAsync({
        version: reviewDoc.version,
        retry: recheckRetry,
      });
      setRecheckRetry(null);
      if (result.status === "queued") {
        toast.success("Đã gửi yêu cầu soát chính tả.");
      } else if (result.status === "running") {
        toast.info("Lượt soát đang chạy.");
      } else if (result.status === "completed") {
        toast.info("Văn bản này đã có kết quả soát.");
      } else {
        toast.info(`Trạng thái lượt soát: ${result.status}.`);
      }
      await refetchChecks();
    } catch (err) {
      setIsRecheckPending(false);
      toast.error(
        err instanceof Error ? err.message : "Không gửi được yêu cầu soát lại.",
      );
    }
  };

  const openCompleteDialog = () => {
    if (!latestCheck) {
      toast.info("Chưa có kết quả soát chính tả để duyệt.");
      return;
    }
    if (isReviewed) {
      toast.info("Văn bản này đã được duyệt chính tả.");
      return;
    }
    if (!isCheckComplete) {
      toast.info("Cần soát xong toàn bộ văn bản trước khi duyệt.");
      return;
    }
    if (remaining > 0) {
      toast.info(`Còn ${remaining} vị trí chưa xử lý.`);
      return;
    }
    setIsCompleteDialogOpen(true);
  };

  const handleIgnoreAll = async () => {
    if (!latestCheck || openSuggestions.length === 0) return;
    const batch = openSuggestions.map((item) => ({
      evidence_id: item.evidence_id,
      start: item.start,
      end: item.end,
    }));
    try {
      await bulkIgnoreMutation.mutateAsync({
        checkId: latestCheck.id,
        body: { suggestions: batch },
      });
      setDecisions((prev) => {
        const next = new Map(prev);
        for (const item of batch) {
          next.set(`${item.evidence_id}:${item.start}:${item.end}`, {
            status: "ignored",
          });
        }
        return next;
      });
      toast.info(`Đã bỏ qua ${batch.length} vị trí còn lại.`);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Không lưu được trạng thái bỏ qua.",
      );
    }
  };

  const handleComplete = async () => {
    if (!reviewDoc || !ocrRunId || !latestCheck) {
      toast.error("Không tìm thấy thông tin bản đọc văn bản.");
      return;
    }
    const { changes, errors } = buildTextChanges(
      reviewDoc.units,
      [...allSuggestions, ...withheldSuggestions],
      decisions,
    );
    if (errors.length > 0) {
      toast.error(`Có lỗi định vị: ${errors[0]}`);
      return;
    }
    try {
      setIsSaving(true);
      const body = {
        expected_version: reviewDoc.version,
        expected_sha256: reviewDoc.canonical_sha256,
        changes,
        review_check_id: latestCheck.id,
      };
      const signature = JSON.stringify([ocrRunId, body]);
      if (saveAttempt.current?.signature !== signature) {
        saveAttempt.current = {
          signature,
          key: `review:spelling:${crypto.randomUUID()}`,
        };
      }
      const savedDoc = await saveReviewMutation.mutateAsync({
        body,
        idempotencyKey: saveAttempt.current.key,
      });
      const needsPreparation = savedDoc.version_id != null;
      const prepared = await prepareAfterSave(savedDoc);
      setIsCompleteDialogOpen(false);
      if (!needsPreparation) {
        toast.success("Đã duyệt chính tả cho văn bản.");
      } else if (prepared) {
        toast.success("Đã duyệt chính tả và gửi yêu cầu chuẩn bị nội dung.");
      } else {
        toast.warning(
          "Đã duyệt chính tả nhưng chưa gửi được yêu cầu chuẩn bị nội dung; hãy thử lại ở trang tài liệu.",
        );
      }
      await navigate({
        to: "/knowledge/$sourceId",
        params: { sourceId },
        search: { collectionId: resolvedCollectionId },
        ignoreBlocker: true,
      });
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Không thể hoàn tất duyệt chính tả.",
      );
    } finally {
      setIsSaving(false);
    }
  };

  const isDocx = Boolean(source?.file_name.toLowerCase().endsWith(".docx"));
  const isPdf = Boolean(source?.file_name.toLowerCase().endsWith(".pdf"));
  const activeText =
    activeUnit && activeSuggestion
      ? splitTextAtSuggestion(
          activeUnit.text,
          activeSuggestion.start,
          activeSuggestion.end,
        )
      : null;
  const isFailed =
    latestCheck?.status === "failed" || latestCheck?.status === "uncertain";

  return (
    <div className="flex h-full flex-col bg-background overflow-hidden min-h-0">
      {/* 1. Header Toolbar */}
      <header className="flex min-h-14 items-center justify-between border-b border-border/60 bg-card px-4 py-2 shrink-0 gap-3">
        {/* Left: Back + Title + Badges */}
        <div className="flex items-center gap-2.5 min-w-0">
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="size-8 p-0 text-muted-foreground hover:text-foreground shrink-0"
          >
            <Link
              to="/knowledge/$sourceId"
              params={{ sourceId }}
              search={{ collectionId: resolvedCollectionId }}
              aria-label="Quay lại chi tiết tài liệu"
            >
              <ArrowLeft className="size-4" />
            </Link>
          </Button>

          <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 min-w-0">
            <h1 className="text-sm font-semibold text-foreground tracking-tight truncate max-w-[200px] sm:max-w-[350px]">
              {displayDocumentTitle(source?.title || "Tài liệu")}
            </h1>
            <Badge variant="outline" className="text-xs h-5 px-2 font-medium">
              Rà soát chính tả
            </Badge>

            {isReviewed && (
              <Badge
                variant="outline"
                className="text-xs h-5 px-2 font-medium border-success/40 bg-success/10 text-success"
              >
                Đã duyệt chính tả
              </Badge>
            )}

            {remaining > 0 && !isReviewed && (
              <Badge
                variant="secondary"
                className="text-xs h-5 px-2 bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30"
              >
                {remaining} vị trí chưa xử lý
              </Badge>
            )}
          </div>
        </div>

        {/* Right: Toggle Original Preview + Complete Button */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant={showOriginalFile ? "secondary" : "outline"}
            size="sm"
            onClick={() => setShowOriginalFile(!showOriginalFile)}
            className="h-8 text-xs gap-1.5"
            title="Mở tệp gốc để đối chiếu"
            aria-label={showOriginalFile ? "Đóng tệp gốc" : "Đối chiếu tệp gốc"}
          >
            <Eye className="size-3.5" />
            <span className="hidden md:inline">
              {showOriginalFile ? "Đóng tệp gốc" : "Đối chiếu tệp gốc"}
            </span>
          </Button>

          {isReviewed ? (
            <Badge
              variant="outline"
              className="h-8 gap-1.5 border-success/40 bg-success/10 px-2.5 text-xs font-medium text-success"
            >
              <BadgeCheck className="size-3.5" />
              Đã duyệt
            </Badge>
          ) : (
            <Button
              size="sm"
              onClick={openCompleteDialog}
              disabled={!canComplete || isSaving}
              className="h-8 gap-1.5 text-xs shadow-2xs"
              title={
                canComplete
                  ? "Hoàn tất duyệt chính tả (S)"
                  : "Cần soát xong và xử lý hết gợi ý trước khi duyệt"
              }
              aria-keyshortcuts="S"
            >
              {isSaving ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <BadgeCheck className="size-3.5" />
              )}
              <span>Hoàn tất duyệt</span>
            </Button>
          )}
        </div>
      </header>
      {isReviewed && latestCheck?.reviewed_at && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-success/30 bg-success/5 px-4 py-2">
          <p
            className="flex items-center gap-1.5 text-xs text-foreground/80"
            role="status"
          >
            <BadgeCheck className="size-3.5 text-success" />
            <span>
              Đã duyệt chính tả lúc{" "}
              {formatSpellingMoment(latestCheck.reviewed_at)}.
            </span>
          </p>
          <Button asChild variant="outline" size="sm" className="h-7 text-xs">
            <Link
              to="/knowledge/$sourceId"
              params={{ sourceId }}
              search={{ collectionId: resolvedCollectionId }}
            >
              Về trang tài liệu
            </Link>
          </Button>
        </div>
      )}
      {imageFailures.length > 0 && (
        <div className="border-b border-border/60 bg-warning/5 px-4 py-2.5">
          <Alert
            variant="warning"
            className="border-0 bg-transparent px-0 py-0 [&>svg]:top-0.5"
          >
            <ShieldAlert />
            <AlertTitle className="text-sm">
              Một số ảnh trong tệp chưa đọc được
            </AlertTitle>
            <AlertDescription className="space-y-2 text-xs text-foreground/80">
              <p>
                {failedPages.length > 0
                  ? `Ảnh trên trang ${failedPages.join(", ")} chưa đọc được. `
                  : "Một số ảnh chưa đọc được. "}
                Phần văn bản còn lại vẫn được giữ để rà soát; nội dung trong ảnh
                lỗi không được dùng làm bằng chứng trả lời.
              </p>
              {reviewDoc?.image_ocr_acknowledged ? (
                <p className="flex items-center gap-1.5 font-medium text-success">
                  <CheckCircle2 className="size-3.5" />
                  Quản trị viên đã xác nhận cảnh báo này.
                </p>
              ) : canAcknowledgeWarnings ? (
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 gap-1.5 text-xs"
                    onClick={() => setIsAckDialogOpen(true)}
                  >
                    <ShieldAlert className="size-3.5" />
                    <span>Xác nhận cảnh báo</span>
                  </Button>
                  <span className="text-[11px] text-muted-foreground">
                    Cần thiết để mở khóa xuất bản khi chấp nhận thiếu nội dung
                    ảnh.
                  </span>
                </div>
              ) : (
                <p className="text-[11px] text-muted-foreground">
                  Quản trị viên của đơn vị cần xác nhận trước khi xuất bản, hoặc
                  đọc lại tệp để bổ sung nội dung ảnh.
                </p>
              )}
            </AlertDescription>
          </Alert>
        </div>
      )}
      {coverage && !coverage.complete && (
        <div
          className="border-b border-border px-4 py-2 space-y-1.5"
          role="status"
        >
          <p className="text-xs text-muted-foreground">
            {latestCheck?.status === "running"
              ? "Đang soát chính tả"
              : latestCheck?.status === "failed"
                ? "Soát chính tả gặp lỗi"
                : latestCheck?.status === "uncertain"
                  ? "Soát chính tả bị gián đoạn"
                  : "Chưa soát xong toàn bộ văn bản"}
            {percent !== null
              ? ` · ${percent}% (${coverage.checked}/${coverage.total} đoạn)`
              : ` · ${coverage.checked} đoạn đã soát`}
            .
          </p>
          {percent !== null && (
            <Progress
              value={percent}
              className={
                latestCheck?.status === "failed" ||
                latestCheck?.status === "uncertain"
                  ? "h-1 max-w-sm bg-destructive/15 [&>[data-slot=progress-indicator]]:bg-destructive"
                  : "h-1 max-w-sm"
              }
              aria-label={`Tiến độ soát chính tả ${percent}%`}
            />
          )}
        </div>
      )}

      {/* 2. Main Workspace Layout */}
      <div className="flex-1 min-h-0 flex flex-col sm:flex-row overflow-hidden">
        {/* Left Column: Filter Tabs + Suggestions List */}
        <div
          className={cn(
            "w-full max-h-[32%] sm:max-h-none sm:w-80 md:w-96 border-r border-border/70 bg-card/60 flex flex-col min-h-0 shrink-0",
            (hasLoadError || isLoadingReview) && "hidden",
          )}
        >
          {/* Filter Bar */}
          <div className="p-2.5 border-b border-border/60 bg-muted/20 shrink-0">
            <div className="grid grid-cols-4 gap-1 p-0.5 bg-muted rounded-lg text-xs font-medium text-center">
              <button
                type="button"
                onClick={() => setFilter("pending")}
                className={cn(
                  "py-1 rounded-md transition-all cursor-pointer truncate px-1",
                  filter === "pending"
                    ? "bg-card text-foreground shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                Chờ duyệt ({counts.pending})
              </button>
              <button
                type="button"
                onClick={() => setFilter("applied")}
                className={cn(
                  "py-1 rounded-md transition-all cursor-pointer truncate px-1",
                  filter === "applied"
                    ? "bg-card text-foreground shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                Đã nhận ({counts.applied})
              </button>
              <button
                type="button"
                onClick={() => setFilter("ignored")}
                className={cn(
                  "py-1 rounded-md transition-all cursor-pointer truncate px-1",
                  filter === "ignored"
                    ? "bg-card text-foreground shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                Bỏ qua ({counts.ignored})
              </button>
              <button
                type="button"
                onClick={() => setFilter("withheld")}
                className={cn(
                  "py-1 rounded-md transition-all cursor-pointer truncate px-1",
                  filter === "withheld"
                    ? "bg-card text-foreground shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
                title="Các vị trí cần đối chiếu trực tiếp với tệp gốc"
              >
                Cần dò ({counts.withheld})
              </button>
            </div>
            {remaining > 0 && !isReviewed && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void handleIgnoreAll()}
                disabled={bulkIgnoreMutation.isPending}
                className="mt-1.5 h-7 w-full gap-1.5 text-xs text-muted-foreground"
              >
                {bulkIgnoreMutation.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <X className="size-3.5" />
                )}
                <span>Bỏ qua tất cả còn lại ({remaining})</span>
              </Button>
            )}
          </div>

          {/* Suggestions List Viewport */}
          <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-border/50">
            {filteredSuggestions.length === 0 ? (
              <div className="py-20 text-center text-xs text-muted-foreground px-4 space-y-2">
                <CheckCircle2 className="size-8 mx-auto text-muted-foreground/40" />
                <p className="font-medium text-foreground">
                  {!latestCheck
                    ? "Văn bản này chưa có kết quả soát."
                    : filter === "pending" && counts.pending === 0
                      ? "Tất cả gợi ý đã được xử lý xong!"
                      : "Không có mục nào trong danh sách này."}
                </p>
                {!latestCheck ? (
                  <p className="text-[11px]">
                    Dùng nút “Soát chính tả” ở khung bên phải để bắt đầu.
                  </p>
                ) : (
                  filter === "pending" &&
                  counts.pending === 0 &&
                  !isReviewed && (
                    <p className="text-[11px]">
                      Nhấn <strong>Hoàn tất duyệt</strong> ở góc phải để ghi
                      nhận kết quả.
                    </p>
                  )
                )}
              </div>
            ) : (
              filteredSuggestions.map((s, idx) => {
                const key = `${s.evidence_id}:${s.start}:${s.end}`;
                const decision = decisions.get(key);
                const isSelected = idx === selectedIndex;

                return (
                  <button
                    type="button"
                    key={key}
                    onClick={() => setSelectedIndex(idx)}
                    className={cn(
                      "w-full text-left p-3 text-xs transition-colors cursor-pointer flex flex-col gap-1.5",
                      isSelected
                        ? "bg-primary/10 border-l-3 border-primary"
                        : "hover:bg-muted/30",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] text-muted-foreground tabular-nums">
                        #{idx + 1}
                        {unitPageById.has(s.evidence_id)
                          ? ` · Trang ${unitPageById.get(s.evidence_id)}`
                          : ""}
                      </span>
                      {decision?.status === "applied" && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-4 px-1.5 text-emerald-600 border-emerald-500/30 bg-emerald-500/10"
                        >
                          Đã áp dụng
                        </Badge>
                      )}
                      {decision?.status === "custom" && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-4 px-1.5 text-primary border-primary/30 bg-primary/10"
                        >
                          Sửa tay
                        </Badge>
                      )}
                      {decision?.status === "ignored" && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-4 px-1.5 text-muted-foreground"
                        >
                          Bỏ qua
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className="line-through text-destructive font-medium truncate max-w-[120px]">
                        {s.original}
                      </span>
                      <span className="text-muted-foreground">→</span>
                      <span className="text-emerald-700 dark:text-emerald-400 font-semibold truncate max-w-[140px]">
                        {decision?.status === "custom"
                          ? decision.customReplacement
                          : s.replacement}
                      </span>
                    </div>

                    <p className="text-[11px] text-muted-foreground line-clamp-1">
                      {s.reason}
                    </p>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Center/Right Column: Detail Card & Context */}
        <div className="flex-1 min-h-0 flex flex-col bg-background overflow-hidden">
          {hasLoadError ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
              <div role="alert" className="space-y-1">
                <p className="text-sm font-semibold text-destructive">
                  {hasReviewError
                    ? "Không tải được văn bản để rà soát"
                    : "Không tải được kết quả soát chính tả"}
                </p>
                {isChecksUnsupported && (
                  <p className="text-xs text-muted-foreground">
                    Máy chủ đang chạy chưa hỗ trợ đọc danh sách gợi ý. Hãy cập
                    nhật dịch vụ rồi thử lại.
                  </p>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={isReviewFetching || isChecksFetching}
                onClick={() => {
                  if (hasReviewError) void refetchReview();
                  if (checksError) void refetchChecks();
                }}
              >
                Thử tải lại
              </Button>
            </div>
          ) : isLoadingReview ? (
            <div
              role="status"
              className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-xs text-muted-foreground"
            >
              <Loader2 className="size-5 animate-spin text-primary" />
              Đang tải kết quả soát chính tả…
            </div>
          ) : activeSuggestion ? (
            <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 lg:p-8 flex justify-center">
              <div className="w-full max-w-2xl space-y-6">
                {/* Navigation Pills */}
                <div className="flex items-center justify-between text-xs text-muted-foreground border-b border-border/60 pb-3">
                  <span>
                    Gợi ý <strong>{selectedIndex + 1}</strong> trên tổng số{" "}
                    <strong>{filteredSuggestions.length}</strong>
                  </span>

                  <span className="hidden md:inline text-[11px] text-muted-foreground/80">
                    J/K chuyển · A áp dụng · X bỏ qua · E sửa tay · U hoàn tác
                  </span>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setSelectedIndex((i) => Math.max(0, i - 1))
                      }
                      disabled={selectedIndex === 0}
                      className="size-7 p-0"
                      title="Gợi ý trước (K)"
                      aria-keyshortcuts="K ArrowLeft"
                    >
                      <ChevronLeft className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setSelectedIndex((i) =>
                          Math.min(filteredSuggestions.length - 1, i + 1),
                        )
                      }
                      disabled={selectedIndex >= filteredSuggestions.length - 1}
                      className="size-7 p-0"
                      title="Gợi ý sau (J)"
                      aria-keyshortcuts="J ArrowRight"
                    >
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                </div>

                {/* Primary Suggestion Card */}
                <div className="rounded-xl border border-border/70 bg-card p-5 sm:p-6 space-y-5 shadow-2xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="size-4 text-amber-500" />
                      <span className="text-xs font-semibold text-foreground">
                        Đề xuất chỉnh sửa chính tả
                      </span>
                    </div>
                  </div>

                  {/* Context sentence with highlighted word */}
                  <div className="p-4 rounded-lg bg-muted/30 border border-border/60 text-sm leading-relaxed text-foreground">
                    {activeText ? (
                      <>
                        <span>{activeText.before}</span>
                        <mark className="bg-amber-400/30 text-amber-900 dark:text-amber-200 font-bold px-1 py-0.5 rounded border border-amber-500/40">
                          {activeText.original}
                        </mark>
                        <span>{activeText.after}</span>
                      </>
                    ) : (
                      <span>{activeSuggestion.context_before}</span>
                    )}
                  </div>

                  {/* Comparison Row */}
                  <div className="grid grid-cols-2 gap-4 p-4 rounded-lg bg-card border border-border/60">
                    <div>
                      <span className="text-[11px] font-medium text-muted-foreground block mb-1">
                        Nguyên văn:
                      </span>
                      <div className="text-sm font-semibold text-destructive line-through">
                        {activeSuggestion.original}
                      </div>
                    </div>
                    <div>
                      <span className="text-[11px] font-medium text-muted-foreground block mb-1">
                        Đề xuất sửa:
                      </span>
                      <div className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                        {activeSuggestion.replacement}
                      </div>
                    </div>
                  </div>

                  {/* Reason */}
                  <div className="text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">Lý do: </span>
                    {activeSuggestion.reason}
                  </div>

                  {/* Decision Actions Bar */}
                  {isEditingManually ? (
                    <div className="space-y-3 pt-2 border-t border-border/60">
                      <div className="space-y-1">
                        <label
                          htmlFor="custom-spelling-edit-input"
                          className="text-xs font-medium text-foreground"
                        >
                          Nhập văn bản sửa tay:
                        </label>
                        <Textarea
                          id="custom-spelling-edit-input"
                          value={manualEditText}
                          onChange={(e) => setManualEditText(e.target.value)}
                          className="text-xs"
                          rows={2}
                          autoFocus
                        />
                      </div>
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setIsEditingManually(false)}
                          className="h-8 text-xs"
                        >
                          Hủy
                        </Button>
                        <Button
                          size="sm"
                          onClick={handleCustomSubmit}
                          disabled={isSaving || isReviewed}
                          className="h-8 text-xs"
                        >
                          Lưu sửa tay
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/60">
                      {isReviewed && (
                        <p className="flex basis-full items-center gap-1.5 text-xs text-muted-foreground">
                          <BadgeCheck className="size-3.5 text-success" />
                          Lượt soát này đã được duyệt; không thể sửa thêm.
                        </p>
                      )}
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={handleApply}
                          disabled={
                            filter === "withheld" || isSaving || isReviewed
                          }
                          className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs"
                          title="Áp dụng (A)"
                          aria-keyshortcuts="A"
                        >
                          <Check className="size-3.5" />
                          <span>Áp dụng</span>
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleIgnore}
                          disabled={
                            isSaving ||
                            isReviewed ||
                            dispositionMutation.isPending
                          }
                          className="h-8 gap-1.5 text-xs"
                          title="Bỏ qua (X)"
                          aria-keyshortcuts="X"
                        >
                          <X className="size-3.5" />
                          <span>Bỏ qua</span>
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isSaving || isReviewed}
                          onClick={() => {
                            setManualEditText(
                              filter === "withheld"
                                ? activeSuggestion.original
                                : activeSuggestion.replacement,
                            );
                            setIsEditingManually(true);
                          }}
                          className="h-8 gap-1.5 text-xs"
                          title="Sửa tay (E)"
                          aria-keyshortcuts="E"
                        >
                          <Pencil className="size-3.5" />
                          <span>Sửa tay</span>
                        </Button>
                      </div>

                      {decisions.has(
                        `${activeSuggestion.evidence_id}:${activeSuggestion.start}:${activeSuggestion.end}`,
                      ) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleUndo}
                          disabled={
                            isSaving ||
                            isReviewed ||
                            dispositionMutation.isPending
                          }
                          className="h-8 text-xs text-muted-foreground gap-1.5"
                          title="Hoàn tác (U)"
                          aria-keyshortcuts="U"
                        >
                          <RotateCcw className="size-3.5" />
                          <span>Hoàn tác</span>
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : !latestCheck ? (
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="w-full max-w-md space-y-4 text-center text-xs text-muted-foreground">
                <Sparkles className="size-10 mx-auto text-muted-foreground/30" />
                <div className="space-y-1">
                  <p className="font-semibold text-foreground text-sm">
                    Chưa có kết quả soát chính tả
                  </p>
                  <p>
                    Hệ thống sẽ soát toàn bộ {reviewDoc?.units.length ?? 0} đoạn
                    văn của văn bản này. Kết quả xuất hiện khi worker hoàn tất;
                    trang tự cập nhật.
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-center gap-2">
                  <Button
                    size="sm"
                    className="h-8 gap-1.5 text-xs"
                    disabled={isRecheckPending || rerunReviewMutation.isPending}
                    onClick={() => openRecheckDialog(false)}
                  >
                    {isRecheckPending ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="size-3.5" />
                    )}
                    <span>Soát chính tả</span>
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="w-full max-w-md space-y-4 text-center text-xs text-muted-foreground">
                {isFailed ? (
                  <AlertTriangle className="size-10 mx-auto text-destructive/50" />
                ) : latestCheck.status === "running" ? (
                  <Loader2 className="size-10 mx-auto animate-spin text-primary/60" />
                ) : isReviewed ? (
                  <BadgeCheck className="size-10 mx-auto text-success/60" />
                ) : (
                  <CheckCircle2 className="size-10 mx-auto text-muted-foreground/30" />
                )}
                <div className="space-y-1">
                  <p className="font-semibold text-foreground text-sm">
                    {latestCheck.status === "failed"
                      ? "Lần soát gặp lỗi"
                      : latestCheck.status === "uncertain"
                        ? "Lần soát bị gián đoạn"
                        : latestCheck.status === "running"
                          ? "Đang soát văn bản"
                          : isReviewed
                            ? "Văn bản đã được duyệt chính tả"
                            : filter === "pending" && remaining === 0
                              ? counts.total === 0
                                ? "Không phát hiện lỗi chính tả"
                                : "Đã xử lý hết gợi ý"
                              : "Không có mục nào trong danh sách này."}
                  </p>
                  <p>
                    {latestCheck.status === "running"
                      ? "Kết quả sẽ xuất hiện khi model hoàn tất."
                      : isFailed
                        ? "Có thể soát tiếp các đoạn còn thiếu."
                        : isReviewed
                          ? "Mọi thay đổi tiếp theo cần một lượt soát mới."
                          : remaining > 0
                            ? `Còn ${remaining} vị trí chưa xử lý.`
                            : canComplete
                              ? "Chọn “Hoàn tất duyệt” để ghi nhận kết quả."
                              : "Chuyển bộ lọc để xem các mục khác."}
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-center gap-2">
                  {isFailed && !isReviewed && (
                    <Button
                      size="sm"
                      className="h-8 gap-1.5 text-xs"
                      disabled={
                        isRecheckPending || rerunReviewMutation.isPending
                      }
                      onClick={() => openRecheckDialog(true)}
                    >
                      {isRecheckPending ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <RotateCcw className="size-3.5" />
                      )}
                      <span>Soát lại</span>
                    </Button>
                  )}
                  {canComplete && (
                    <Button
                      size="sm"
                      className="h-8 gap-1.5 text-xs"
                      onClick={openCompleteDialog}
                    >
                      <BadgeCheck className="size-3.5" />
                      <span>Hoàn tất duyệt</span>
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Toggleable Original File Dock (< 50% width when open) */}
          {showOriginalFile && (
            <div className="h-72 border-t border-border/70 bg-muted/20 flex flex-col shrink-0">
              <div className="h-8 border-b border-border/60 px-3 bg-muted/40 flex items-center justify-between text-xs text-muted-foreground shrink-0">
                <span className="font-semibold text-foreground flex items-center gap-1.5">
                  <FileText className="size-3.5 text-primary" />
                  <span>Bản gốc đối chiếu ({source?.file_name})</span>
                </span>
                <button
                  type="button"
                  onClick={() => setShowOriginalFile(false)}
                  className="hover:text-foreground cursor-pointer text-xs"
                >
                  Đóng ✕
                </button>
              </div>

              <div className="flex-1 min-h-0 overflow-hidden flex justify-center items-center">
                {blobLoading ? (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="size-4 animate-spin text-primary" />
                    <span>Đang nạp tệp gốc...</span>
                  </div>
                ) : isPdf && blobUrl ? (
                  <iframe
                    src={
                      activeUnit
                        ? `${blobUrl}#page=${activeUnit.page}`
                        : blobUrl
                    }
                    title="Bản gốc PDF"
                    className="w-full h-full border-0 bg-white"
                  />
                ) : isDocx && docBlob ? (
                  <DocxViewer
                    blob={docBlob}
                    fileName={source?.file_name || "document.docx"}
                    blobUrl={blobUrl}
                  />
                ) : (
                  <div className="text-xs text-muted-foreground">
                    Không thể hiển thị xem trước tệp gốc này.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <Dialog
        open={isCompleteDialogOpen}
        onOpenChange={setIsCompleteDialogOpen}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Hoàn tất duyệt chính tả</DialogTitle>
            <DialogDescription>
              {counts.applied > 0
                ? `${counts.applied} vị trí đã áp dụng sẽ được ghi vào văn bản. `
                : "Nội dung văn bản được giữ nguyên. "}
              {counts.ignored > 0
                ? `${counts.ignored} vị trí đã bỏ qua không thay đổi văn bản. `
                : ""}
              Lượt soát này sẽ được đánh dấu đã duyệt.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5 rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground">
            <p>Toàn bộ gợi ý của lượt soát đã được xử lý.</p>
            {counts.applied > 0 && (
              <p>
                Sau khi duyệt, hệ thống chuẩn bị nội dung từ văn bản đã sửa để
                dùng cho trả lời.
              </p>
            )}
          </div>
          <DialogFooter className="gap-2">
            <Button
              variant="ghost"
              onClick={() => setIsCompleteDialogOpen(false)}
              disabled={isSaving}
            >
              Tiếp tục xem
            </Button>
            <Button onClick={() => void handleComplete()} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <BadgeCheck className="size-3.5" />
              )}
              Hoàn tất duyệt
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={recheckRetry !== null}
        onOpenChange={(open) => {
          if (!open) setRecheckRetry(null);
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {recheckRetry ? "Soát lại chính tả" : "Soát chính tả"}
            </DialogTitle>
            <DialogDescription>
              {recheckRetry
                ? "Hệ thống sẽ soát các đoạn còn thiếu. Nếu cấu hình soát đã đổi, hệ thống sẽ kiểm tra lại toàn bộ."
                : `Hệ thống sẽ soát toàn bộ ${reviewDoc?.units.length ?? 0} đoạn văn.`}
            </DialogDescription>
          </DialogHeader>
          {recheckRetry && (
            <p className="text-xs text-muted-foreground">
              Lần soát lỗi trước được giữ lại trong lịch sử; kết quả mới sẽ hiển
              thị khi hoàn tất.
            </p>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRecheckRetry(null)}
              disabled={rerunReviewMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              onClick={() => void handleConfirmRecheck()}
              disabled={rerunReviewMutation.isPending}
            >
              {rerunReviewMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Sparkles className="size-3.5" />
              )}
              Bắt đầu soát
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isAckDialogOpen} onOpenChange={setIsAckDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Xác nhận cảnh báo ảnh OCR</DialogTitle>
            <DialogDescription>
              Xác nhận cho phép xuất bản tài liệu dù còn ảnh chưa đọc được. Hành
              động này được ghi nhật ký cùng lý do.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <label
              htmlFor="ocr-warning-ack-reason"
              className="text-xs font-medium text-foreground"
            >
              Lý do xác nhận
            </label>
            <Textarea
              id="ocr-warning-ack-reason"
              value={ackReason}
              onChange={(event) => setAckReason(event.target.value)}
              placeholder="Ví dụ: Ảnh lỗi chỉ là logo hoặc trang trí, không chứa nội dung cần trả lời."
              rows={3}
              maxLength={500}
              className="text-xs"
            />
            <p className="text-[11px] text-muted-foreground">
              Tối thiểu 5 ký tự.
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={ackWarningsMutation.isPending}
              onClick={() => setIsAckDialogOpen(false)}
            >
              Hủy
            </Button>
            <Button
              disabled={
                ackWarningsMutation.isPending || ackReason.trim().length < 5
              }
              onClick={() => void handleAcknowledgeWarnings()}
            >
              {ackWarningsMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <ShieldAlert className="size-3.5" />
              )}
              Xác nhận
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
