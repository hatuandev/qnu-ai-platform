import { useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  AlertTriangle,
  BookOpen,
  Check,
  Download,
  Edit3,
  History,
  Loader2,
  RotateCcw,
  Save,
  ScanSearch,
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
import { Checkbox } from "@/components/ui/checkbox";
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
  OcrSaveConfirmDialog,
  OcrSpellCheckDialog,
} from "@/features/knowledge/ocr-review-dialogs";
import {
  applySuggestionsToText,
  formatOcrError,
  formatUnitLocator,
  generateIdempotencyKey,
  MAX_SPELL_CHECK_UNITS,
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
  onLocateUnit?: (target: { evidenceId: string; page?: number }) => void;
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
  onLocateUnit,
}: OcrTextReviewProps) {
  const navigate = useNavigate();
  const current = useActionScope();
  // Selected version: null means latest saved; 0 means original OCR; 1, 2...
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

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
    if (!canManage) return;
    const currentDraft = draftChanges.get(unit.evidence_id) ?? unit.text;
    setEditingEvidenceId(unit.evidence_id);
    setEditingInputText(currentDraft);
  };

  // Handle inline edit save into local draft
  const handleApplyLocalEdit = () => {
    if (!canManage || !editingEvidenceId) return;
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
    setActiveSaveKey(generateIdempotencyKey());

    setEditingEvidenceId(null);
    setEditingInputText("");
    toast.info("Đã cập nhật vào bản nháp trên màn hình.");
  };

  // Revert a single unit draft back to loaded version
  const handleRevertUnitDraft = (evidenceId: string) => {
    if (!canManage) return;
    draft.update((prev) => {
      const next = new Map(prev);
      next.delete(evidenceId);
      return next;
    });
    setActiveSaveKey(generateIdempotencyKey());
    if (editingEvidenceId === evidenceId) {
      setEditingEvidenceId(null);
    }
  };

  // Discard all pending drafts
  const handleDiscardAllDrafts = () => {
    if (!canManage) return;
    draft.clear();
    setActiveSaveKey(generateIdempotencyKey());
    setEditingEvidenceId(null);
    setConflictError(null);
    toast.info("Đã hủy bỏ toàn bộ thay đổi nháp.");
  };

  // Save changes to backend
  const handleConfirmSave = async () => {
    if (!canManage || !doc || pendingChanges.length === 0) return;
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
      toast.success(
        `Đã lưu thành công phiên bản dẫn xuất mới (v${updated.version}).`,
      );
      draft.clear();
      setSaveModalOpen(false);
      setConflictError(null);
      setActiveSaveKey(generateIdempotencyKey());
    } catch (error: unknown) {
      if (!current()) return;
      if (error instanceof ApiProblemError) {
        if (error.code === "ocr_text_version_conflict") {
          setConflictError(
            "Xung đột phiên bản: Nội dung đã có bản mới được lưu trên máy chủ. Bạn vẫn đang giữ bản nháp hiện tại, vui lòng tải lại để đối chiếu.",
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
    if (!canManage || !doc) return;
    const ids = Array.from(selectedUnitsForCheck);
    if (ids.length === 0 || ids.length > MAX_SPELL_CHECK_UNITS) {
      toast.error(
        `Vui lòng chọn từ 1 đến ${MAX_SPELL_CHECK_UNITS} đoạn văn bản để kiểm tra.`,
      );
      return;
    }

    try {
      const res = await detectMutation.mutateAsync({
        body: {
          ...(selectedVersion !== null
            ? { source_version: selectedVersion }
            : {}),
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
      setActiveSpellKey(generateIdempotencyKey());

      if (res.status === "failed") {
        toast.error(
          `Lượt kiểm tra chính tả thất bại: ${formatOcrError(res.error_code)}`,
        );
        return;
      }
      if (res.status !== "completed") {
        toast.warning(
          "Lần kiểm tra chưa hoàn tất (quá thời gian chờ hoặc đang xử lý). Hệ thống không tự gọi lại mô hình.",
        );
        return;
      }

      if (res.withheld_suggestions?.length) {
        toast.info(
          `Có ${res.withheld_suggestions.length} chỗ cần đối chiếu ảnh; ${res.suggestions.length} gợi ý sửa chữ để xem xét.`,
        );
      } else if (res.suggestions.length === 0) {
        toast.info(
          `Hoàn tất kiểm tra ${res.checked_evidence_ids.length} đoạn: Không có đề xuất sửa nào.`,
        );
      } else {
        toast.success(
          `Tìm thấy ${res.suggestions.length} đề xuất sửa chính tả.`,
        );
      }
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
    setActiveSaveKey(generateIdempotencyKey());

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

  const firstPage = units[0]?.page ?? 1;

  return (
    <div className="space-y-4">
      {/* Top Action Toolbar */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-3 sm:p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Version Switcher & Draft Status */}
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

            {pendingChanges.length > 0 ? (
              <Badge variant="warning" className="text-[11px] py-0">
                Đang có {pendingChanges.length} đoạn nháp chưa lưu
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-[11px] py-0">
                Đã lưu trên máy chủ (v{doc.version})
              </Badge>
            )}

            {!canManage ? (
              <Badge variant="outline" className="text-[11px] py-0">
                Chế độ chỉ xem
              </Badge>
            ) : null}
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
                  if (selectedUnitsForCheck.size === 0) {
                    const defaultPageUnits = units.filter(
                      (u) =>
                        u.page === firstPage &&
                        u.kind !== "image" &&
                        u.kind !== "figure" &&
                        u.text.trim().length > 0,
                    );
                    setSelectedUnitsForCheck(
                      new Set(defaultPageUnits.map((u) => u.evidence_id)),
                    );
                  }
                  setActiveSpellKey(generateIdempotencyKey());
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
                title="Sử dụng lượt OCR và phiên bản văn bản đã lưu để tạo bản biên soạn"
                onClick={() => {
                  if (pendingChanges.length > 0) {
                    toast.warning(
                      "Bạn đang có thay đổi nháp chưa lưu. Trình biên soạn chỉ dùng phiên bản đã lưu trên máy chủ — vui lòng bấm Lưu trước khi dùng để biên soạn.",
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
                    setActiveSaveKey(generateIdempotencyKey());
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
          onLocateUnit={onLocateUnit}
          onManualEditUnit={(evidenceId) => {
            const unit = units.find((u) => u.evidence_id === evidenceId);
            if (unit) handleStartEdit(unit);
          }}
          onRevertUnitDraft={handleRevertUnitDraft}
        />
      ) : null}

      {/* Text Units List */}
      <div className="space-y-3">
        {units.map((unit) => {
          const isEditing = editingEvidenceId === unit.evidence_id;
          const hasDraft =
            draftChanges.has(unit.evidence_id) &&
            draftChanges.get(unit.evidence_id) !== unit.text;
          const currentText = draftChanges.get(unit.evidence_id) ?? unit.text;
          const wasModifiedFromOriginal = unit.text !== unit.original_text;
          const locator = formatUnitLocator(unit, units);
          const isSelectedForCheck = selectedUnitsForCheck.has(
            unit.evidence_id,
          );

          return (
            <Card
              key={unit.evidence_id}
              className={`rounded-xl shadow-2xs transition-colors ${
                hasDraft ? "border-warning/60 bg-warning/5" : ""
              }`}
            >
              <CardContent className="p-3 sm:p-4 space-y-2">
                {/* Unit Header */}
                <div className="flex items-center justify-between text-xs flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    {canManage && currentText.trim().length > 0 ? (
                      <Checkbox
                        checked={isSelectedForCheck}
                        onCheckedChange={() => {
                          setSelectedUnitsForCheck((prev) => {
                            const next = new Set(prev);
                            if (next.has(unit.evidence_id)) {
                              next.delete(unit.evidence_id);
                            } else {
                              next.add(unit.evidence_id);
                            }
                            return next;
                          });
                          setActiveSpellKey(generateIdempotencyKey());
                        }}
                        aria-label={`Chọn ${locator} để kiểm tra chính tả`}
                      />
                    ) : null}
                    <span className="font-semibold text-foreground">
                      {locator}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    {hasDraft ? (
                      <Badge variant="warning" className="text-[10px] py-0">
                        Bản nháp chưa lưu
                      </Badge>
                    ) : wasModifiedFromOriginal ? (
                      <Badge variant="secondary" className="text-[10px] py-0">
                        Đã sửa so với OCR gốc
                      </Badge>
                    ) : null}

                    {onLocateUnit ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-1.5 text-[11px] gap-1 text-muted-foreground hover:text-primary"
                        onClick={() =>
                          onLocateUnit({
                            evidenceId: unit.evidence_id,
                            page: unit.page,
                          })
                        }
                      >
                        <ScanSearch className="size-3" />
                        <span>Đối chiếu ảnh</span>
                      </Button>
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
                      className="min-h-[80px] text-sm font-sans leading-relaxed"
                      placeholder="Nhập nội dung chỉnh sửa..."
                      autoFocus
                    />
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="text-xs text-muted-foreground">
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
                  <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap font-sans">
                    {currentText}
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Save Diff Confirmation Dialog */}
      <OcrSaveConfirmDialog
        open={saveModalOpen}
        onOpenChange={setSaveModalOpen}
        doc={doc}
        pendingChanges={pendingChanges}
        baseMovedOn={baseMovedOn}
        isSaving={saveMutation.isPending}
        onConfirmSave={() => void handleConfirmSave()}
      />

      {/* AI Spell Check Range & Provider Dialog */}
      <OcrSpellCheckDialog
        open={spellCheckModalOpen}
        onOpenChange={setSpellCheckModalOpen}
        workspaceId={workspaceId}
        doc={doc}
        activePage={firstPage}
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
        isSubmitting={detectMutation.isPending}
        onSubmit={() => void handleRunSpellCheck()}
      />
    </div>
  );
}
