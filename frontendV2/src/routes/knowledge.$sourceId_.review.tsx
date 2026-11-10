import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createFileRoute,
  Link,
  useBlocker,
  useNavigate,
} from "@tanstack/react-router";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText,
  Loader2,
  Pencil,
  RotateCcw,
  Save,
  Sparkles,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiProblemError } from "@/api/client";
import {
  getRevisionContentBlob,
  knowledgeKeys,
  useCollectionsQuery,
  useSourceQuery,
  useSourceSummaryQuery,
} from "@/api/knowledge";
import {
  useSaveTextReviewMutation,
  useTextReviewChecksQuery,
  useTextReviewQuery,
} from "@/api/ocr/queries";
import type { ReviewDocument, Suggestion } from "@/api/ocr/requests";
import { useCreatePreparationIntentMutation } from "@/api/preparation/queries";
import { DocxViewer } from "@/components/knowledge/docx-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useBackgroundTasksStore } from "@/lib/background-tasks-store";
import { displayDocumentTitle } from "@/lib/knowledge-studio-helpers";
import {
  buildTextChanges,
  type SuggestionDecision,
  splitTextAtSuggestion,
} from "@/lib/spelling-replacement-helpers";
import {
  preferredSpellingCheck,
  spellingCoverage,
  spellingScope,
} from "@/lib/spelling-review";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

const reviewSearchSchema = z.object({
  collectionId: z.string().optional(),
  revisionId: z.string().optional(),
  runId: z.string().optional(),
  textVersion: z.number().int().nonnegative().optional(),
});

export const Route = createFileRoute("/knowledge/$sourceId_/review")({
  validateSearch: (search) => reviewSearchSchema.parse(search),
  component: SpellingReviewPage,
});

function SpellingReviewPage() {
  const { sourceId } = Route.useParams();
  const { collectionId, revisionId, runId, textVersion } = Route.useSearch();
  const workspaceId = useUiStore((s) => s.activeWorkspaceId);
  return (
    <SpellingReviewWorkspace
      key={JSON.stringify([
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        textVersion,
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
  const latestTextVersion = search.textVersion ?? scope?.textVersion;

  // 2. Load Review Document & Checks
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
    latestTextVersion,
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
    latestTextVersion,
    { refetchInterval: 5000 },
  );

  const hasLoadError = hasReviewError || Boolean(checksError);
  const isLoadingReview = isReviewDocLoading || isChecksLoading;
  const isChecksUnsupported =
    checksError instanceof ApiProblemError && checksError.status === 405;

  const selectedCheck = preferredSpellingCheck(checks);
  const latestCheck =
    selectedCheck?.canonical_sha256 === reviewDoc?.canonical_sha256
      ? selectedCheck
      : undefined;
  const coverage = latestCheck ? spellingCoverage(latestCheck) : null;

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

  // Saving state
  const [isSaving, setIsSaving] = useState(false);
  const [savedReview, setSavedReview] = useState<ReviewDocument | null>(null);
  const [preparationError, setPreparationError] = useState(false);
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

  const createIntentMutation = useCreatePreparationIntentMutation(
    activeWorkspaceId,
    resolvedCollectionId,
  );

  useEffect(() => {
    if (!docBlob) return;
    const url = URL.createObjectURL(docBlob);
    setPreview({ blob: docBlob, url });
    return () => URL.revokeObjectURL(url);
  }, [docBlob]);

  // Filtered list of suggestions
  const filteredSuggestions = useMemo(() => {
    if (filter === "withheld") {
      return withheldSuggestions;
    }

    return allSuggestions.filter((s) => {
      const key = `${s.evidence_id}:${s.start}:${s.end}`;
      const d = decisions.get(key);
      const status = d?.status || "pending";

      if (filter === "pending") return status === "pending";
      if (filter === "applied")
        return status === "applied" || status === "custom";
      if (filter === "ignored") return status === "ignored";
      return true; // "all"
    });
  }, [allSuggestions, withheldSuggestions, decisions, filter]);

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
    let ignored = 0;

    for (const s of allSuggestions) {
      const key = `${s.evidence_id}:${s.start}:${s.end}`;
      const d = decisions.get(key);
      const status = d?.status || "pending";
      if (status === "pending") pending++;
      else if (status === "applied" || status === "custom") applied++;
      else if (status === "ignored") ignored++;
    }

    return {
      pending,
      applied,
      ignored,
      withheld: withheldSuggestions.length,
      total: allSuggestions.length,
    };
  }, [allSuggestions, withheldSuggestions, decisions]);

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
    if (!activeSuggestion) return;
    makeDecision(activeSuggestion, { status: "ignored" });
    toast.info("Đã bỏ qua gợi ý.");
  }, [activeSuggestion, makeDecision]);

  const handleCustomSubmit = useCallback(() => {
    if (!activeSuggestion || !manualEditText.trim()) return;
    makeDecision(activeSuggestion, {
      status: "custom",
      customReplacement: manualEditText.trim(),
    });
    toast.success(`Đã cập nhật sửa tay: "${manualEditText.trim()}"`);
  }, [activeSuggestion, manualEditText, makeDecision]);

  const handleUndo = useCallback(() => {
    if (!activeSuggestion) return;
    const key = `${activeSuggestion.evidence_id}:${activeSuggestion.start}:${activeSuggestion.end}`;
    setDecisions((prev) => {
      const next = new Map(prev);
      next.delete(key);
      return next;
    });
    setIsEditingManually(false);
    toast.info("Đã hoàn tác quyết định.");
  }, [activeSuggestion]);

  // Unit lookup for displaying full sentence context
  const activeUnit = useMemo(() => {
    if (!activeSuggestion || !reviewDoc?.units) return null;
    return (
      reviewDoc.units.find(
        (u) => u.evidence_id === activeSuggestion.evidence_id,
      ) || null
    );
  }, [activeSuggestion, reviewDoc]);

  // Unsaved changes check
  const hasUnsavedChanges = useMemo(() => {
    if (savedReview) return false;
    for (const d of decisions.values()) {
      if (d.status === "applied" || d.status === "custom") return true;
    }
    return false;
  }, [decisions, savedReview]);

  useBlocker({
    shouldBlockFn: () =>
      hasUnsavedChanges &&
      !isSaving &&
      !window.confirm("Bạn có thay đổi chính tả chưa lưu. Rời trang?"),
    enableBeforeUnload: hasUnsavedChanges && !isSaving,
  });

  const prepareSavedReview = async (saved: ReviewDocument) => {
    if (!activeWorkspaceId || !activeRevisionId || !saved.version_id) return;
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
      toast.success("Đã lưu bản sửa và gửi yêu cầu chuẩn bị lại.");
      await navigate({
        to: "/knowledge/$sourceId",
        params: { sourceId },
        search: { collectionId: resolvedCollectionId },
        ignoreBlocker: true,
      });
    } catch {
      setPreparationError(true);
    }
  };

  const handleSaveAll = async () => {
    if (!reviewDoc || !ocrRunId) {
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

    if (changes.length === 0) {
      toast.info("Chưa có thay đổi nào được chọn để lưu.");
      return;
    }

    try {
      setIsSaving(true);
      const body = {
        expected_version: reviewDoc.version,
        expected_sha256: reviewDoc.canonical_sha256,
        changes,
      };
      const signature = JSON.stringify([ocrRunId, body]);
      if (saveAttempt.current?.signature !== signature) {
        saveAttempt.current = {
          signature,
          key: `save:spelling:${crypto.randomUUID()}`,
        };
      }
      const savedDoc = await saveReviewMutation.mutateAsync({
        body,
        idempotencyKey: saveAttempt.current.key,
      });
      setSavedReview(savedDoc);
      await prepareSavedReview(savedDoc);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Không thể lưu các thay đổi chính tả.",
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

            {counts.pending > 0 && (
              <Badge
                variant="secondary"
                className="text-xs h-5 px-2 bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30"
              >
                {counts.pending} vị trí chưa duyệt
              </Badge>
            )}
          </div>
        </div>

        {/* Right: Toggle Original Preview + Save Button */}
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

          <Button
            size="sm"
            onClick={() =>
              savedReview
                ? void prepareSavedReview(savedReview)
                : void handleSaveAll()
            }
            disabled={
              isSaving ||
              createIntentMutation.isPending ||
              (!savedReview && !hasUnsavedChanges)
            }
            className="h-8 gap-1.5 text-xs shadow-2xs"
          >
            {isSaving ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Save className="size-3.5" />
            )}
            <span>{savedReview ? "Chuẩn bị lại" : "Lưu thay đổi"}</span>
          </Button>
        </div>
      </header>
      {preparationError && (
        <p
          className="border-b border-border px-4 py-2 text-sm text-destructive"
          role="alert"
        >
          Bản sửa đã được lưu. Chọn “Chuẩn bị lại” để gửi lại yêu cầu.
        </p>
      )}
      {coverage && !coverage.complete && (
        <p
          className="border-b border-border px-4 py-2 text-xs text-muted-foreground"
          role="status"
        >
          {latestCheck?.status === "running"
            ? "Đang soát chính tả"
            : "Chưa soát xong toàn bộ văn bản"}
          {" · "}
          {coverage.checked}
          {coverage.total === null ? "" : `/${coverage.total}`} đoạn đã soát.
        </p>
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
          </div>

          {/* Suggestions List Viewport */}
          <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-border/50">
            {filteredSuggestions.length === 0 ? (
              <div className="py-20 text-center text-xs text-muted-foreground px-4 space-y-2">
                <CheckCircle2 className="size-8 mx-auto text-muted-foreground/40" />
                <p className="font-medium text-foreground">
                  {!latestCheck
                    ? "Chưa có kết quả cho bản văn bản này."
                    : filter === "pending" && coverage?.complete
                      ? "Tất cả gợi ý đã được xử lý xong!"
                      : "Không có mục nào trong danh sách này."}
                </p>
                {filter === "pending" && counts.applied > 0 && (
                  <p className="text-[11px]">
                    Hãy nhấn nút <strong>Lưu thay đổi</strong> ở góc phải để ghi
                    nhận các điểm đã sửa.
                  </p>
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
                      <span className="font-mono text-[10px] text-muted-foreground">
                        #{idx + 1} • Đoạn {s.evidence_id}
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

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setSelectedIndex((i) => Math.max(0, i - 1))
                      }
                      disabled={selectedIndex === 0}
                      className="size-7 p-0"
                      title="Gợi ý trước"
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
                      title="Gợi ý sau"
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
                          disabled={isSaving || Boolean(savedReview)}
                          className="h-8 text-xs"
                        >
                          Lưu sửa tay
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/60">
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={handleApply}
                          disabled={
                            filter === "withheld" ||
                            isSaving ||
                            Boolean(savedReview)
                          }
                          className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs"
                        >
                          <Check className="size-3.5" />
                          <span>Áp dụng</span>
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleIgnore}
                          disabled={isSaving || Boolean(savedReview)}
                          className="h-8 gap-1.5 text-xs"
                        >
                          <X className="size-3.5" />
                          <span>Bỏ qua</span>
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isSaving || Boolean(savedReview)}
                          onClick={() => {
                            setManualEditText(
                              filter === "withheld"
                                ? activeSuggestion.original
                                : activeSuggestion.replacement,
                            );
                            setIsEditingManually(true);
                          }}
                          className="h-8 gap-1.5 text-xs"
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
                          disabled={isSaving || Boolean(savedReview)}
                          className="h-8 text-xs text-muted-foreground gap-1.5"
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
          ) : (
            <div className="flex-1 flex items-center justify-center p-8 text-center text-xs text-muted-foreground">
              <div className="space-y-2 max-w-sm">
                <CheckCircle2 className="size-10 mx-auto text-muted-foreground/30" />
                <p className="font-semibold text-foreground text-sm">
                  {coverage?.complete
                    ? "Không còn gợi ý ở mục này"
                    : "Chưa có gợi ý để hiển thị"}
                </p>
                {hasUnsavedChanges && (
                  <p>Chọn “Lưu thay đổi” để ghi nhận các gợi ý đã áp dụng.</p>
                )}
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
    </div>
  );
}
