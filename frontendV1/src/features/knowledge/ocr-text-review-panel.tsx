import { useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  AlertTriangle,
  BookOpen,
  Check,
  Download,
  Edit3,
  History,
  Info,
  Loader2,
  RotateCcw,
  Save,
  Sparkles,
  Undo2,
} from "lucide-react";
import { useMemo, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";
import {
  ApiProblemError,
  getTokenState,
  subscribeToken,
  v1Client,
} from "@/app/api/v1";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useOcrDraft } from "@/features/knowledge/ocr-draft-store";
import {
  useDetectCheckMutation,
  useSaveTextReviewMutation,
  useTextReviewQuery,
} from "@/features/knowledge/ocr-queries";
import {
  downloadReviewDocumentBlob,
  downloadReviewMarkdownBlob,
} from "@/features/knowledge/ocr-requests";
import {
  applySuggestionsToText,
  formatOcrError,
  generateIdempotencyKey,
  validateSuggestionSpan,
} from "@/features/knowledge/ocr-schemas";
import type {
  DetectionResponse,
  ProcessingRunResponse,
  Suggestion,
  TextChange,
  TextUnit,
} from "@/features/knowledge/ocr-types";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { useCatalogQuery } from "@/features/modelops/queries";
import { SpellingResultPanel } from "./spelling-result-panel";

type OcrTextReviewProps = {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  run: ProcessingRunResponse;
  canManage: boolean;
  checkId?: string;
  onCheckChange?: (checkId: string) => void;
};
export function OcrTextReviewPanel(props: OcrTextReviewProps) {
  const { sessionId } = useSyncExternalStore(
    subscribeToken,
    getTokenState,
    getTokenState,
  );
  return (
    <OcrTextReviewSession
      key={`${sessionId}:${props.workspaceId}:${props.collectionId}:${props.sourceId}:${props.revisionId}:${props.run.id}`}
      {...props}
    />
  );
}
function OcrTextReviewSession({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  run,
  canManage,
  checkId,
  onCheckChange,
}: OcrTextReviewProps) {
  const navigate = useNavigate();
  const current = useActionScope();
  // Selected version: null means latest saved; 0 means original OCR; 1, 2...
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

  // Draft changes live in a store keyed by
  // session/workspace/collection/source/revision/run, so switching to the
  // scan-comparison tab (which unmounts this panel) does not lose them.
  const draftScope = useMemo(
    () => ({ workspaceId, collectionId, sourceId, revisionId, runId: run.id }),
    [workspaceId, collectionId, sourceId, revisionId, run.id],
  );

  // Active unit being edited inline
  const [editingEvidenceId, setEditingEvidenceId] = useState<string | null>(
    null,
  );
  const [editingInputText, setEditingInputText] = useState<string>("");

  // Save Diff Confirmation Modal
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [activeSaveKey, setActiveSaveKey] = useState<string>(() =>
    generateIdempotencyKey(),
  );

  // AI Spell Check Modal State
  const [spellCheckModalOpen, setSpellCheckModalOpen] = useState(false);
  const [selectedUnitsForCheck, setSelectedUnitsForCheck] = useState<
    Set<string>
  >(() => new Set());
  const [spellCheckProviderId, setSpellCheckProviderId] =
    useState<string>("default");
  const [activeSpellKey, setActiveSpellKey] = useState<string>(() =>
    generateIdempotencyKey(),
  );
  const [localCheck, setLocalCheck] = useState<DetectionResponse | null>(null);

  // Version Conflict Alert State
  const [conflictError, setConflictError] = useState<string | null>(null);

  // Downloading derivative state
  const [downloadingType, setDownloadingType] = useState<"json" | "md" | null>(
    null,
  );

  // Fetch current ReviewDocument from backend
  const reviewQuery = useTextReviewQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    run.id,
    selectedVersion,
  );

  const saveMutation = useSaveTextReviewMutation(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    run.id,
  );

  const detectMutation = useDetectCheckMutation(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    run.id,
  );

  // Catalog for chat providers for spelling check
  const catalogQuery = useCatalogQuery(workspaceId, {
    enabled: spellCheckModalOpen,
  });
  const chatProviders = (catalogQuery.data ?? []).filter((p) =>
    p.capabilities.includes("chat"),
  );

  const doc = reviewQuery.data;
  const units = useMemo(() => doc?.units ?? [], [doc]);

  const draft = useOcrDraft(
    draftScope,
    doc ? { version: doc.version, sha256: doc.canonical_sha256 } : null,
  );
  const draftChanges = draft.changes;
  const baseMovedOn = doc
    ? draft.baseMovedOn({ version: doc.version, sha256: doc.canonical_sha256 })
    : false;

  // Compute pending changes compared to loaded version text
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

  // Handle inline edit start
  const handleStartEdit = (unit: TextUnit) => {
    const currentDraft = draftChanges.get(unit.evidence_id) ?? unit.text;
    setEditingEvidenceId(unit.evidence_id);
    setEditingInputText(currentDraft);
  };

  // Handle inline edit save into local draft
  const handleApplyLocalEdit = () => {
    if (!editingEvidenceId) return;
    const trimmed = editingInputText.trim();
    if (!trimmed) {
      toast.error("Không được để trống nội dung đoạn.");
      return;
    }

    draft.update((prev) => {
      const next = new Map(prev);
      next.set(editingEvidenceId, editingInputText);
      return next;
    });

    setEditingEvidenceId(null);
    setEditingInputText("");
    toast.info("Đã cập nhật vào bản nháp trên màn hình.");
  };

  // Revert a single unit draft back to loaded version
  const handleRevertUnitDraft = (evidenceId: string) => {
    draft.update((prev) => {
      const next = new Map(prev);
      next.delete(evidenceId);
      return next;
    });
    if (editingEvidenceId === evidenceId) {
      setEditingEvidenceId(null);
    }
  };

  // Discard all pending drafts
  const handleDiscardAllDrafts = () => {
    draft.clear();
    setEditingEvidenceId(null);
    setConflictError(null);
    toast.info("Đã hủy bỏ toàn bộ thay đổi nháp.");
  };

  // Save changes to backend
  const handleConfirmSave = async () => {
    if (!doc || pendingChanges.length === 0) return;
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
      await saveMutation.mutateAsync({
        body: {
          expected_version: draft.draft?.baseVersion ?? doc.version,
          expected_sha256: draft.draft?.baseSha256 ?? doc.canonical_sha256,
          changes: pendingChanges,
        },
        idempotencyKey: activeSaveKey,
      });

      toast.success(
        `Đã lưu thành công phiên bản dẫn xuất mới (v${doc.version + 1}).`,
      );
      draft.clear();
      setSaveModalOpen(false);
      setConflictError(null);
      // Generate fresh key for next mutation
      setActiveSaveKey(generateIdempotencyKey());
    } catch (error: unknown) {
      if (error instanceof ApiProblemError) {
        if (error.code === "ocr_text_version_conflict") {
          setConflictError(
            "Xung đột phiên bản: Nội dung đã có bản mới được lưu trên server. Bạn vẫn đang giữ bản nháp hiện tại, vui lòng tải lại để đối chiếu.",
          );
        } else {
          toast.error(formatOcrError(error.code, error.message));
        }
      } else {
        toast.error("Không thể lưu bản sửa đổi.");
      }
    }
  };

  // Trigger AI Spell Check
  const handleRunSpellCheck = async () => {
    if (!doc) return;
    const ids = Array.from(selectedUnitsForCheck);
    if (ids.length === 0 || ids.length > 100) {
      toast.error("Vui lòng chọn từ 1 đến 100 đoạn văn bản.");
      return;
    }

    try {
      const res = await detectMutation.mutateAsync({
        body: {
          expected_version: doc.version,
          expected_sha256: doc.canonical_sha256,
          evidence_ids: ids,
          provider_id:
            spellCheckProviderId === "default" ? null : spellCheckProviderId,
          max_output_tokens: 4096,
        },
        idempotencyKey: activeSpellKey,
      });

      if (!current()) return;
      setLocalCheck(res);
      onCheckChange?.(res.id);
      setSpellCheckModalOpen(false);
      if (res.status !== "completed") {
        toast.info(
          "Lần kiểm tra chưa hoàn tất. Đọc lại trạng thái từ biên nhận; chưa có kết luận chính tả.",
        );
        return;
      }

      if (res.suggestions.length === 0) {
        toast.info(
          `Hoàn tất kiểm tra ${res.checked_evidence_ids.length} đoạn: Không có đề xuất sửa nào.`,
        );
      } else {
        toast.success(
          `Tìm thấy ${res.suggestions.length} đề xuất sửa chính tả.`,
        );
      }

      // Generate next key for fresh check intent
      setActiveSpellKey(generateIdempotencyKey());
    } catch (error: unknown) {
      if (!current()) return;
      if (error instanceof ApiProblemError) {
        toast.error(formatOcrError(error.code, error.message));
      } else {
        toast.error("Không thể hoàn tất kiểm tra chính tả bằng AI.");
      }
    }
  };

  // Apply a specific AI suggestion into the local unit draft
  const handleApplySuggestion = (s: Suggestion) => {
    const unit = units.find((u) => u.evidence_id === s.evidence_id);
    if (!unit || !canManage || baseMovedOn || !current()) return false;

    const currentText = draftChanges.get(s.evidence_id) ?? unit.text;

    // Validate span with code points
    if (!validateSuggestionSpan(currentText, s)) {
      toast.error(
        "Gợi ý không còn khớp với văn bản hiện hành (có thể đoạn này đã được chỉnh sửa).",
      );
      return false;
    }

    const { updatedText, error } = applySuggestionsToText(currentText, [s]);
    if (error) {
      toast.error(error);
      return false;
    }

    draft.update((prev) => {
      const next = new Map(prev);
      next.set(s.evidence_id, updatedText);
      return next;
    });

    toast.success("Đã áp dụng gợi ý vào bản nháp. Vui lòng bấm Lưu thay đổi.");
    return true;
  };

  // Download exact version derivative
  const handleDownloadDerivative = async (type: "json" | "md") => {
    if (!doc) return;
    setDownloadingType(type);
    try {
      const versionParam = selectedVersion ?? doc.version;
      const res =
        type === "json"
          ? await downloadReviewDocumentBlob(
              v1Client,
              workspaceId,
              collectionId,
              sourceId,
              revisionId,
              run.id,
              versionParam,
            )
          : await downloadReviewMarkdownBlob(
              v1Client,
              workspaceId,
              collectionId,
              sourceId,
              revisionId,
              run.id,
              versionParam,
            );

      const downloadUrl = URL.createObjectURL(res.blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download =
        res.fileName ||
        `source_${sourceId}_v${doc.version}.${type === "json" ? "json" : "md"}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 5000);
      toast.success(
        `Đã tải tệp ${type.toUpperCase()} phiên bản v${doc.version}.`,
      );
    } catch (error: unknown) {
      if (error instanceof ApiProblemError) {
        toast.error(formatOcrError(error.code, error.message));
      } else {
        toast.error("Không tải được tệp dẫn xuất.");
      }
    } finally {
      setDownloadingType(null);
    }
  };

  if (reviewQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (reviewQuery.isError || !doc) {
    return (
      <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-6 text-xs text-destructive">
        <AlertCircle className="size-5 mb-2" />
        <p className="font-semibold">
          Không tải được nội dung văn bản để rà soát.
        </p>
        <p className="mt-1 text-muted-foreground">
          Lượt xử lý OCR có thể chưa hoàn tất thành công hoặc tệp dữ liệu không
          khả dụng.
        </p>
        <Button
          size="sm"
          variant="outline"
          className="mt-3 text-xs"
          onClick={() => void reviewQuery.refetch()}
        >
          Tải lại
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Action Toolbar */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-3 sm:p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Version Switcher */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <History className="size-3.5 text-primary" />
              Phiên bản hiển thị:
            </span>
            <Select
              value={
                selectedVersion === null ? "latest" : String(selectedVersion)
              }
              onValueChange={(val) => {
                if (pendingChanges.length > 0) {
                  if (
                    !window.confirm(
                      "Bạn có thay đổi nháp chưa lưu. Chuyển phiên bản sẽ hủy các thay đổi này. Tiếp tục?",
                    )
                  ) {
                    return;
                  }
                  draft.clear();
                }
                setSelectedVersion(val === "latest" ? null : Number(val));
              }}
            >
              <SelectTrigger className="h-8 text-xs w-[160px]">
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
                          v{v} {v === doc.version ? "(Hiện hành)" : ""}
                        </SelectItem>
                      ),
                    )
                  : null}
              </SelectContent>
            </Select>

            <span className="text-muted-foreground font-mono text-[11px] hidden sm:inline">
              SHA: {doc.canonical_sha256.slice(0, 10)}...
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* AI Spell Check trigger */}
            {canManage ? (
              <Button
                size="sm"
                variant="outline"
                className="h-8 text-xs gap-1.5 text-primary border-primary/30 hover:bg-primary/5"
                onClick={() => {
                  if (pendingChanges.length > 0) {
                    toast.warning(
                      "Vui lòng Lưu hoặc Hủy các thay đổi nháp trước khi chạy kiểm tra chính tả bằng AI.",
                    );
                    return;
                  }
                  // Default select all prose units on current review doc
                  setSelectedUnitsForCheck(
                    new Set(units.map((u) => u.evidence_id)),
                  );
                  setSpellCheckModalOpen(true);
                }}
              >
                <Sparkles className="size-3.5" />
                <span>Kiểm tra chính tả AI</span>
              </Button>
            ) : null}

            {/* Save Draft Button */}
            {canManage && pendingChanges.length > 0 ? (
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-8 text-xs gap-1 text-muted-foreground hover:text-destructive"
                  onClick={handleDiscardAllDrafts}
                >
                  <Undo2 className="size-3.5" />
                  <span>Hủy ({pendingChanges.length})</span>
                </Button>

                <Button
                  size="sm"
                  variant="default"
                  className="h-8 text-xs gap-1.5 shadow-2xs font-semibold"
                  disabled={baseMovedOn}
                  title={
                    baseMovedOn
                      ? "Bản nháp thuộc phiên bản cũ. Áp dụng nháp lên phiên bản hiện tại trước khi lưu."
                      : undefined
                  }
                  onClick={() => setSaveModalOpen(true)}
                >
                  <Save className="size-3.5" />
                  <span>Lưu ({pendingChanges.length} thay đổi)</span>
                </Button>
              </>
            ) : null}

            {/* Download Buttons */}
            <div className="flex items-center gap-1 border-l pl-2">
              <Button
                size="sm"
                variant="outline"
                className="h-8 text-xs gap-1"
                disabled={downloadingType === "json"}
                onClick={() => void handleDownloadDerivative("json")}
                title="Tải tệp Canonical JSON"
              >
                {downloadingType === "json" ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <Download className="size-3" />
                )}
                <span>JSON</span>
              </Button>

              <Button
                size="sm"
                variant="outline"
                className="h-8 text-xs gap-1"
                disabled={downloadingType === "md"}
                onClick={() => void handleDownloadDerivative("md")}
                title="Tải tệp Markdown dẫn xuất"
              >
                {downloadingType === "md" ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <Download className="size-3" />
                )}
                <span>Markdown</span>
              </Button>
            </div>

            {/* Compile with this text version button */}
            {canManage && (
              <Button
                size="sm"
                variant="outline"
                className="h-8 text-xs gap-1.5 text-primary border-primary/30 hover:bg-primary/5"
                title="Sử dụng lượt OCR và phiên bản văn bản đang xem để tạo bản biên soạn"
                onClick={() => {
                  if (pendingChanges.length > 0) {
                    toast.warning(
                      "Bạn đang có thay đổi chưa lưu. Vui lòng lưu thay đổi hậu OCR trước khi dùng để biên soạn.",
                    );
                    return;
                  }
                  void navigate({
                    to: "/workspaces/$workspaceId/collections/$collectionId/compilations",
                    params: { workspaceId, collectionId },
                    search: {
                      create: true,
                      ocrRunId: run.id,
                      sourceId,
                      revisionId,
                      revisionNo: run.revision_no,
                      generation: run.generation,
                      version: selectedVersion ?? doc.version,
                    },
                  });
                }}
              >
                <BookOpen className="size-3.5" />
                <span>Dùng để biên soạn</span>
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Draft was written against an older server version: never rebase it
          silently, ask the reviewer to choose. */}
      {baseMovedOn && doc ? (
        <Alert className="border-warning/50 bg-warning/10 text-foreground py-3">
          <AlertTriangle className="size-4 text-warning" />
          <AlertTitle className="text-xs font-semibold">
            Bản nháp thuộc phiên bản v{draft.draft?.baseVersion} nhưng server đã
            có v{doc.version}
          </AlertTitle>
          <AlertDescription className="text-xs mt-1 space-y-2">
            <p>
              Nội dung trên server đã thay đổi sau khi bạn bắt đầu sửa. Hệ thống
              không tự đổi căn cứ của bản nháp để tránh ghi đè thay đổi của
              người khác.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => {
                  if (
                    window.confirm(
                      `Áp dụng bản nháp hiện tại lên phiên bản v${doc.version}? Các đoạn đã bị xóa ở phiên bản mới sẽ không được áp dụng.`,
                    )
                  ) {
                    draft.rebase({
                      version: doc.version,
                      sha256: doc.canonical_sha256,
                    });
                  }
                }}
              >
                Áp dụng nháp lên v{doc.version}
              </Button>
              <Button
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

      {/* Version Conflict Warning */}
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
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => void reviewQuery.refetch()}
              >
                Tải lại dữ liệu mới nhất
              </Button>
              <Button
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

      {doc && (checkId || localCheck) ? (
        <SpellingResultPanel
          workspaceId={workspaceId}
          collectionId={collectionId}
          sourceId={sourceId}
          revisionId={revisionId}
          runId={run.id}
          checkId={checkId}
          localCheck={localCheck}
          doc={doc}
          draftChanges={draftChanges}
          canManage={canManage && !baseMovedOn}
          onApply={handleApplySuggestion}
        />
      ) : null}

      {/* Text Units List */}
      <div className="space-y-3">
        {units.map((unit) => {
          const isEditing = editingEvidenceId === unit.evidence_id;
          const hasDraft = draftChanges.has(unit.evidence_id);
          const currentText = draftChanges.get(unit.evidence_id) ?? unit.text;
          const wasModifiedFromOriginal = unit.text !== unit.original_text;

          return (
            <Card
              key={unit.evidence_id}
              className={`rounded-xl shadow-2xs transition-colors ${
                hasDraft ? "border-primary/50 bg-primary/2" : ""
              }`}
            >
              <CardContent className="p-3 sm:p-4 space-y-2">
                {/* Unit Header */}
                <div className="flex items-center justify-between text-xs flex-wrap gap-2">
                  <div className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
                    <Badge variant="outline" className="text-[10px] py-0">
                      Trang {unit.page}
                    </Badge>
                    <span>·</span>
                    <span className="capitalize">{unit.kind}</span>
                    {unit.row !== null ? (
                      <>
                        <span>·</span>
                        <span>
                          R{unit.row}:C{unit.column}
                        </span>
                      </>
                    ) : null}
                    <span>·</span>
                    <span
                      className="truncate max-w-[120px]"
                      title={unit.evidence_id}
                    >
                      {unit.evidence_id.slice(0, 16)}...
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {hasDraft ? (
                      <Badge variant="warning" className="text-[10px] py-0">
                        Bản nháp chưa lưu
                      </Badge>
                    ) : wasModifiedFromOriginal ? (
                      <Badge variant="secondary" className="text-[10px] py-0">
                        Đã sửa so với OCR gốc
                      </Badge>
                    ) : null}

                    {canManage && !isEditing ? (
                      <>
                        {hasDraft ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-1.5 text-[11px] text-muted-foreground hover:text-destructive"
                            onClick={() =>
                              handleRevertUnitDraft(unit.evidence_id)
                            }
                            title="Khôi phục về nội dung trước khi sửa nháp"
                          >
                            <RotateCcw className="size-3 mr-1" />
                            Hoàn tác
                          </Button>
                        ) : null}

                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-[11px] gap-1 text-primary hover:bg-primary/5"
                          onClick={() => handleStartEdit(unit)}
                        >
                          <Edit3 className="size-3" />
                          <span>Chỉnh sửa</span>
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>

                {/* Unit Content: Editing mode or Display mode */}
                {isEditing ? (
                  <div className="space-y-2 pt-1">
                    <Textarea
                      value={editingInputText}
                      onChange={(e) => setEditingInputText(e.target.value)}
                      className="min-h-[80px] text-xs font-sans leading-relaxed"
                      placeholder="Nhập nội dung chỉnh sửa..."
                      autoFocus
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-muted-foreground">
                        Ban đầu: &ldquo;{unit.text}&rdquo;
                      </span>
                      <div className="flex items-center gap-1.5">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs"
                          onClick={() => setEditingEvidenceId(null)}
                        >
                          Hủy
                        </Button>
                        <Button
                          size="sm"
                          className="h-7 text-xs gap-1"
                          onClick={handleApplyLocalEdit}
                        >
                          <Check className="size-3" />
                          <span>Áp dụng vào nháp</span>
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-foreground leading-relaxed whitespace-pre-wrap font-sans">
                    {currentText}
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Save Diff Confirmation Dialog */}
      <Dialog open={saveModalOpen} onOpenChange={setSaveModalOpen}>
        <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Save className="size-4 text-primary" />
              Xác nhận lưu thay đổi ({pendingChanges.length} đoạn)
            </DialogTitle>
            <DialogDescription className="text-xs">
              Lưu các thay đổi vào server sẽ sinh phiên bản văn bản dẫn xuất mới
              (v
              {doc.version + 1}). Tệp OCR gốc và tài liệu nguồn được bảo toàn
              bất biến.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-auto space-y-3 py-2 pr-1">
            {pendingChanges.map((change) => (
              <div
                key={change.evidence_id}
                className="p-3 rounded-lg border text-xs space-y-1.5 bg-muted/10"
              >
                <span className="font-mono text-[10px] text-muted-foreground block">
                  Đoạn: {change.evidence_id.slice(0, 24)}...
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-destructive/5 border border-destructive/20 text-destructive">
                    <span className="font-semibold block text-[10px] uppercase mb-0.5">
                      Trước khi sửa:
                    </span>
                    <p className="whitespace-pre-wrap">{change.before}</p>
                  </div>
                  <div className="p-2 rounded bg-success/5 border border-success/20 text-success">
                    <span className="font-semibold block text-[10px] uppercase mb-0.5">
                      Sau khi sửa:
                    </span>
                    <p className="whitespace-pre-wrap">{change.after}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <DialogFooter className="gap-2 sm:gap-0 border-t pt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSaveModalOpen(false)}
              disabled={saveMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={() => void handleConfirmSave()}
              disabled={saveMutation.isPending || baseMovedOn}
              className="gap-1.5"
            >
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang lưu...</span>
                </>
              ) : (
                <>
                  <Check className="size-3.5" />
                  <span>Xác nhận lưu v{doc.version + 1}</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* AI Spell Check Range & Provider Dialog */}
      <Dialog open={spellCheckModalOpen} onOpenChange={setSpellCheckModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              Kiểm tra chính tả bằng AI
            </DialogTitle>
            <DialogDescription className="text-xs">
              Gửi một tập hợp các đoạn văn bản đến mô hình ngôn ngữ (Chat) để đề
              xuất các lỗi chính tả tiếng Việt nghi ngờ.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            {/* Provider Selector */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">
                Mô hình kiểm tra (Chat)
              </Label>
              <Select
                value={spellCheckProviderId}
                onValueChange={setSpellCheckProviderId}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Chọn model chat" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default" className="text-xs">
                    Theo mặc định workspace
                  </SelectItem>
                  {chatProviders.map((p) => (
                    <SelectItem key={p.id} value={p.id} className="text-xs">
                      {p.name} ({p.id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Scope selection summary */}
            <div className="rounded-lg border p-3 space-y-2 bg-muted/20">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-foreground">
                  Số đoạn được chọn: {selectedUnitsForCheck.size} /{" "}
                  {units.length}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 text-[11px]"
                  onClick={() => {
                    if (selectedUnitsForCheck.size === units.length) {
                      setSelectedUnitsForCheck(new Set());
                    } else {
                      setSelectedUnitsForCheck(
                        new Set(units.slice(0, 100).map((u) => u.evidence_id)),
                      );
                    }
                  }}
                >
                  {selectedUnitsForCheck.size === units.length
                    ? "Bỏ chọn tất cả"
                    : "Chọn tối đa 100 đoạn"}
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Backend giới hạn từ 1 đến tối đa 100 đoạn cho mỗi lượt kiểm tra
                để đảm bảo ngân sách token và hiệu năng.
              </p>
            </div>

            <Alert className="text-xs py-2 border-info/40 bg-info/5 text-info">
              <Info className="size-3.5" />
              <AlertDescription className="text-[11px]">
                Thao tác này sẽ gọi API model và có thể tiêu hao hạn mức token
                trong workspace của bạn.
              </AlertDescription>
            </Alert>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSpellCheckModalOpen(false)}
              disabled={detectMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={() => void handleRunSpellCheck()}
              disabled={
                detectMutation.isPending ||
                selectedUnitsForCheck.size === 0 ||
                selectedUnitsForCheck.size > 100
              }
              className="gap-1.5"
            >
              {detectMutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang phân tích...</span>
                </>
              ) : (
                <>
                  <Sparkles className="size-3.5" />
                  <span>
                    Bắt đầu kiểm tra ({selectedUnitsForCheck.size} đoạn)
                  </span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
