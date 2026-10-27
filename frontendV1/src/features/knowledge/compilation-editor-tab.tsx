import { useBlocker, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  FileEdit,
  GitBranch,
  Loader2,
  Plus,
  Tag,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
import { formatDateTimeValue } from "@/lib/date-utils";
import {
  useAcceptEditMutation,
  useCompilationReviewsQuery,
  useCreateEditPreviewMutation,
  useEditContextQuery,
} from "./compilation-queries";
import {
  formatCompilationError,
  generateIdempotencyKey,
} from "./compilation-schemas";
import type {
  DraftContent,
  DraftParagraph,
  DraftSection,
  EditContextResponse,
  EditPreviewResponse,
} from "./compilation-types";

type EditorParagraph = DraftParagraph & { editorId: string };
type EditorSection = Omit<DraftSection, "paragraphs"> & {
  editorId: string;
  paragraphs: EditorParagraph[];
};
function editableSection(section: DraftSection): EditorSection {
  return {
    ...section,
    editorId: crypto.randomUUID(),
    paragraphs: section.paragraphs.map((p) => ({
      ...p,
      citations: [...p.citations],
      editorId: crypto.randomUUID(),
    })),
  };
}
type EditorProps = {
  workspaceId: string;
  collectionId: string;
  runId: string;
  canEdit: boolean;
  onNavigateToChild?: (childRunId: string) => void;
};

export function CompilationEditorTab(props: EditorProps) {
  const { sessionId } = useV1Auth();
  return (
    <CompilationEditorSession
      key={`${sessionId}:${props.workspaceId}:${props.collectionId}:${props.runId}`}
      {...props}
    />
  );
}

function CompilationEditorSession({
  workspaceId,
  collectionId,
  runId,
  canEdit,
  onNavigateToChild,
}: EditorProps) {
  const navigate = useNavigate();

  const editContextQuery = useEditContextQuery(
    workspaceId,
    collectionId,
    runId,
    { enabled: canEdit },
  );

  const reviewsQuery = useCompilationReviewsQuery(
    workspaceId,
    collectionId,
    runId,
    50,
    0,
    { enabled: canEdit },
  );

  const previewMutation = useCreateEditPreviewMutation(
    workspaceId,
    collectionId,
    runId,
  );

  const acceptMutation = useAcceptEditMutation(
    workspaceId,
    collectionId,
    runId,
  );

  // Form local state
  const [baseContext, setBaseContext] = useState<EditContextResponse | null>(
    null,
  );
  const [title, setTitle] = useState("");
  const [sections, setSections] = useState<EditorSection[]>([]);
  const [unknowns, setUnknowns] = useState<string[]>([]);
  const [reason, setReason] = useState("");
  const [reviewId, setReviewId] = useState<string>("none");

  // Active preview & idempotency
  const [activePreview, setActivePreview] =
    useState<EditPreviewResponse | null>(null);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [acceptIdempotencyKey, setAcceptIdempotencyKey] = useState<string>(() =>
    generateIdempotencyKey(),
  );
  const savedRef = useRef(false);
  const mountedRef = useRef(true);
  const revisionRef = useRef(0);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);
  const content = {
    title,
    sections: sections.map((s) => ({
      heading: s.heading,
      paragraphs: s.paragraphs.map((p) => ({
        text: p.text,
        citations: p.citations,
      })),
    })),
    unknowns,
  };
  const hasUnsavedChanges = Boolean(
    baseContext &&
      (JSON.stringify(content) !== JSON.stringify(baseContext.content) ||
        reason ||
        reviewId !== "none"),
  );
  const blocker = useBlocker({
    shouldBlockFn: () => hasUnsavedChanges && !savedRef.current,
    disabled: !hasUnsavedChanges,
    enableBeforeUnload: () => hasUnsavedChanges && !savedRef.current,
    withResolver: true,
  });

  // Initialize draft from context once
  useEffect(() => {
    if (editContextQuery.data && !baseContext) {
      const content = editContextQuery.data.content;
      setTitle(content.title || "");
      setSections(content.sections.map(editableSection));
      setUnknowns(content.unknowns ? [...content.unknowns] : []);
      setReason("");
      setReviewId("none");
      setBaseContext(editContextQuery.data);
    }
  }, [editContextQuery.data, baseContext]);

  // Invalidate active preview whenever user changes any input
  const invalidatePreview = () => {
    revisionRef.current += 1;
    if (activePreview) {
      setActivePreview(null);
    }
  };

  const handleTitleChange = (val: string) => {
    setTitle(val);
    invalidatePreview();
  };

  const handleReasonChange = (val: string) => {
    setReason(val);
    invalidatePreview();
  };

  const handleReviewIdChange = (val: string) => {
    setReviewId(val);
    invalidatePreview();
  };

  // Section manipulation
  const handleAddSection = () => {
    setSections((prev) => [
      ...prev,
      editableSection({
        heading: "Mục mới",
        paragraphs: [{ text: "", citations: [] }],
      }),
    ]);
    invalidatePreview();
  };

  const handleRemoveSection = (sectionIndex: number) => {
    setSections((prev) => prev.filter((_, idx) => idx !== sectionIndex));
    invalidatePreview();
  };

  const handleSectionHeadingChange = (
    sectionIndex: number,
    heading: string,
  ) => {
    setSections((prev) =>
      prev.map((s, idx) => (idx === sectionIndex ? { ...s, heading } : s)),
    );
    invalidatePreview();
  };

  // Paragraph manipulation
  const handleAddParagraph = (sectionIndex: number) => {
    setSections((prev) =>
      prev.map((s, idx) =>
        idx === sectionIndex
          ? {
              ...s,
              paragraphs: [
                ...s.paragraphs,
                { editorId: crypto.randomUUID(), text: "", citations: [] },
              ],
            }
          : s,
      ),
    );
    invalidatePreview();
  };

  const handleRemoveParagraph = (
    sectionIndex: number,
    paragraphIndex: number,
  ) => {
    setSections((prev) =>
      prev.map((s, idx) =>
        idx === sectionIndex
          ? {
              ...s,
              paragraphs: s.paragraphs.filter(
                (_, pIdx) => pIdx !== paragraphIndex,
              ),
            }
          : s,
      ),
    );
    invalidatePreview();
  };

  const handleParagraphTextChange = (
    sectionIndex: number,
    paragraphIndex: number,
    text: string,
  ) => {
    setSections((prev) =>
      prev.map((s, sIdx) =>
        sIdx === sectionIndex
          ? {
              ...s,
              paragraphs: s.paragraphs.map((p, pIdx) =>
                pIdx === paragraphIndex ? { ...p, text } : p,
              ),
            }
          : s,
      ),
    );
    invalidatePreview();
  };

  const handleToggleCitation = (
    sectionIndex: number,
    paragraphIndex: number,
    citationId: string,
  ) => {
    setSections((prev) =>
      prev.map((s, sIdx) =>
        sIdx === sectionIndex
          ? {
              ...s,
              paragraphs: s.paragraphs.map((p, pIdx) => {
                if (pIdx !== paragraphIndex) return p;
                const has = p.citations.includes(citationId);
                const next = has
                  ? p.citations.filter((c) => c !== citationId)
                  : [...p.citations, citationId];
                return { ...p, citations: next };
              }),
            }
          : s,
      ),
    );
    invalidatePreview();
  };

  // Unknowns manipulation
  const handleAddUnknown = () => {
    setUnknowns((prev) => [...prev, ""]);
    invalidatePreview();
  };

  const handleRemoveUnknown = (index: number) => {
    setUnknowns((prev) => prev.filter((_, idx) => idx !== index));
    invalidatePreview();
  };

  const handleUnknownTextChange = (index: number, text: string) => {
    setUnknowns((prev) =>
      prev.map((item, idx) => (idx === index ? text : item)),
    );
    invalidatePreview();
  };

  const availableCitationIds = useMemo(() => {
    if (!editContextQuery.data?.citations) return [];
    return Object.keys(editContextQuery.data.citations);
  }, [editContextQuery.data?.citations]);

  // Completed reviews of this bundle for linking
  const completedReviews = useMemo(() => {
    return (reviewsQuery.data ?? []).filter((r) => r.status === "completed");
  }, [reviewsQuery.data]);

  const handleRequestPreview = async () => {
    if (!baseContext || !editContextQuery.data) return;
    if (baseContext.bundle_sha256 !== editContextQuery.data.bundle_sha256) {
      toast.error(
        "Nguồn biên soạn đã thay đổi. Hãy mở lại bản mới trước khi lưu.",
      );
      return;
    }
    if (!title.trim()) {
      toast.error("Vui lòng nhập tiêu đề bản biên soạn.");
      return;
    }
    if (!reason.trim()) {
      toast.error("Vui lòng nhập lý do chỉnh sửa.");
      return;
    }

    const payloadContent: DraftContent = {
      title: title.trim(),
      sections: sections.map((s) => ({
        heading: s.heading.trim(),
        paragraphs: s.paragraphs.map((p) => ({
          text: p.text.trim(),
          citations: p.citations,
        })),
      })),
      unknowns: unknowns.map((u) => u.trim()).filter(Boolean),
    };

    try {
      const revision = revisionRef.current;
      const preview = await previewMutation.mutateAsync({
        expected_bundle_sha256: baseContext.bundle_sha256,
        reason: reason.trim(),
        review_id: reviewId === "none" ? null : reviewId,
        content: payloadContent,
      });
      if (!mountedRef.current) return;
      if (revision !== revisionRef.current) {
        toast.info(
          "Bản nháp đã đổi. Vui lòng xem trước lại nội dung mới nhất.",
        );
        return;
      }

      setActivePreview(preview);
      setPreviewModalOpen(true);
      setAcceptIdempotencyKey(generateIdempotencyKey());
      toast.success("Đã tạo bản xem trước thay đổi.");
    } catch (err: unknown) {
      if (!mountedRef.current) return;
      if (err instanceof ApiProblemError) {
        toast.error(formatCompilationError(err.code, err.message));
      } else {
        toast.error("Không thể tạo bản xem trước thay đổi.");
      }
    }
  };

  const handleAcceptEdit = async () => {
    if (!activePreview) return;

    try {
      const outcome = await acceptMutation.mutateAsync({
        input: {
          preview_id: activePreview.preview_id,
          preview_sha256: activePreview.preview_sha256,
        },
        idempotencyKey: acceptIdempotencyKey,
      });
      if (!mountedRef.current) return;

      toast.success("Đã tạo bản biên soạn mới.");
      savedRef.current = true;
      setPreviewModalOpen(false);

      if (outcome.run?.id) {
        onNavigateToChild?.(outcome.run.id);
        void navigate({
          to: "/workspaces/$workspaceId/collections/$collectionId/compilations/$runId",
          params: {
            workspaceId,
            collectionId,
            runId: outcome.run.id,
          },
        });
      }
    } catch (err: unknown) {
      if (!mountedRef.current) return;
      if (err instanceof ApiProblemError) {
        toast.error(formatCompilationError(err.code, err.message));
      } else {
        toast.error("Không thể xác nhận lưu bản sửa.");
      }
    }
  };

  if (!canEdit) {
    return (
      <Card className="rounded-xl p-8 text-center text-xs text-muted-foreground">
        <AlertCircle className="size-6 text-muted-foreground mx-auto mb-2" />
        <p className="font-semibold text-foreground">
          Không có quyền chỉnh sửa
        </p>
        <p className="text-[11px] text-muted-foreground/80 mt-1">
          Chỉ quản trị viên hoặc biên tập viên (admin/editor) của workspace mới
          có quyền tạo bản sửa Compiler.
        </p>
      </Card>
    );
  }

  if (editContextQuery.isLoading) {
    return (
      <Card className="rounded-xl shadow-2xs p-5 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full" />
      </Card>
    );
  }

  if (editContextQuery.isError || !editContextQuery.data) {
    return (
      <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-4 text-xs">
        <div className="flex items-center gap-2 text-destructive font-semibold">
          <AlertCircle className="size-4 shrink-0" />
          <span>Không thể tải ngữ cảnh chỉnh sửa</span>
        </div>
        <p className="text-muted-foreground mt-1">
          {editContextQuery.error instanceof Error
            ? editContextQuery.error.message
            : "Lỗi kết nối máy chủ hoặc bản ghi không hợp lệ."}
        </p>
      </Card>
    );
  }

  const context = editContextQuery.data;

  return (
    <div className="space-y-6">
      <ConfirmDialog
        open={blocker.status === "blocked"}
        onOpenChange={(open) => {
          if (!open) blocker.reset?.();
        }}
        title="Rời bản nháp chưa lưu?"
        description="Thay đổi đang soạn sẽ bị bỏ. Bạn có thể ở lại để tiếp tục chỉnh sửa."
        confirmLabel="Rời bản nháp"
        onConfirm={() => blocker.proceed?.()}
      />
      {/* Editor Header Info */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-4 sm:p-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <FileEdit className="size-4 text-primary" />
                <span className="font-semibold text-sm text-foreground">
                  Trình chỉnh sửa bản biên soạn có cấu trúc
                </span>
                <Badge variant="outline" className="font-mono text-[10px]">
                  Số bản sửa con: {context.edit_count}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Chỉnh sửa tiêu đề, các mục, đoạn văn và gắn citation nguồn. Bảng
                nguồn và siêu dữ liệu được bảo vệ nguyên vẹn.
              </p>
            </div>

            <Button
              size="sm"
              className="h-8 text-xs gap-1.5 shrink-0"
              onClick={handleRequestPreview}
              disabled={
                previewMutation.isPending || !reason.trim() || !title.trim()
              }
            >
              {previewMutation.isPending ? (
                <>
                  <Loader2 className="size-3 animate-spin" />
                  <span>Đang kiểm tra...</span>
                </>
              ) : (
                <>
                  <GitBranch className="size-3.5" />
                  <span>Xem trước thay đổi (Preview)</span>
                </>
              )}
            </Button>
          </div>

          <div className="pt-2 border-t flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground font-mono">
            <span>Bundle SHA: {context.bundle_sha256.slice(0, 16)}...</span>
            <span>Citations sẵn có: {availableCitationIds.length}</span>
            <span>Bảng nguồn: {context.source_tables?.length ?? 0}</span>
          </div>
        </CardContent>
      </Card>

      {/* Editor Body */}
      <div className="space-y-4">
        {/* Title */}
        <div className="space-y-1.5">
          <Label htmlFor="editor-title" className="text-xs font-semibold">
            Tiêu đề bản biên soạn <span className="text-destructive">*</span>
          </Label>
          <Input
            id="editor-title"
            className="text-xs font-medium"
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            placeholder="Nhập tiêu đề tài liệu..."
          />
        </div>

        {/* Sections */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-semibold">
              Các mục nội dung ({sections.length})
            </Label>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1"
              onClick={handleAddSection}
            >
              <Plus className="size-3" />
              <span>Thêm mục</span>
            </Button>
          </div>

          {sections.map((section, sIdx) => (
            <Card
              key={section.editorId}
              className="rounded-xl shadow-2xs border"
            >
              <CardHeader className="p-3 sm:p-4 bg-muted/20 border-b flex flex-row items-center justify-between gap-2">
                <div className="flex-1 flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-muted-foreground">
                    #{sIdx + 1}
                  </span>
                  <Input
                    className="h-7 text-xs font-semibold bg-background"
                    value={section.heading}
                    onChange={(e) =>
                      handleSectionHeadingChange(sIdx, e.target.value)
                    }
                    placeholder="Tiêu đề mục..."
                  />
                </div>

                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive"
                    onClick={() => handleRemoveSection(sIdx)}
                    title="Xóa mục này"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="p-3 sm:p-4 space-y-3">
                {section.paragraphs.map((p, pIdx) => (
                  <div
                    key={p.editorId}
                    className="p-3 rounded-lg border bg-card space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-muted-foreground">
                        Đoạn #{pIdx + 1}
                      </span>
                      {section.paragraphs.length > 1 && (
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                          onClick={() => handleRemoveParagraph(sIdx, pIdx)}
                        >
                          <X className="size-3" />
                        </Button>
                      )}
                    </div>

                    <Textarea
                      rows={2}
                      className="text-xs resize-none"
                      value={p.text}
                      onChange={(e) =>
                        handleParagraphTextChange(sIdx, pIdx, e.target.value)
                      }
                      placeholder="Nội dung đoạn văn..."
                    />

                    {/* Citations multiselect from server index */}
                    <div className="space-y-1">
                      <span className="text-[11px] text-muted-foreground font-semibold block">
                        Citations đính kèm (chọn từ bằng chứng nguồn):
                      </span>
                      <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto p-1.5 border rounded bg-muted/10">
                        {availableCitationIds.map((cId) => {
                          const isSelected = p.citations.includes(cId);
                          return (
                            <button
                              key={cId}
                              type="button"
                              onClick={() =>
                                handleToggleCitation(sIdx, pIdx, cId)
                              }
                              className={`px-1.5 py-0.5 rounded text-[10px] font-mono border transition-colors flex items-center gap-1 ${
                                isSelected
                                  ? "bg-primary text-primary-foreground border-primary"
                                  : "bg-background text-muted-foreground hover:bg-muted border-border"
                              }`}
                            >
                              {isSelected ? (
                                <Check className="size-2.5" />
                              ) : (
                                <Tag className="size-2.5 opacity-60" />
                              )}
                              <span>{cId}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                ))}

                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs gap-1"
                  onClick={() => handleAddParagraph(sIdx)}
                >
                  <Plus className="size-3" />
                  <span>Thêm đoạn văn vào mục #{sIdx + 1}</span>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Unknowns */}
        <div className="space-y-2 pt-2 border-t">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-semibold">
              Các điểm chưa xác định (Unknowns)
            </Label>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1"
              onClick={handleAddUnknown}
            >
              <Plus className="size-3" />
              <span>Thêm unknown</span>
            </Button>
          </div>

          {unknowns.length === 0 ? (
            <p className="text-[11px] text-muted-foreground italic">
              Không có điểm chưa xác định nào.
            </p>
          ) : (
            unknowns.map((uText, uIdx) => (
              <div
                // biome-ignore lint/suspicious/noArrayIndexKey: unknowns list ordered sequentially
                key={`unknown-${uIdx}`}
                className="flex items-center gap-2"
              >
                <Input
                  className="h-7 text-xs flex-1"
                  value={uText}
                  onChange={(e) =>
                    handleUnknownTextChange(uIdx, e.target.value)
                  }
                  placeholder="Ghi nhận điều chưa đủ căn cứ hoặc còn mâu thuẫn..."
                />
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                  onClick={() => handleRemoveUnknown(uIdx)}
                >
                  <Trash2 className="size-3" />
                </Button>
              </div>
            ))
          )}
        </div>

        {/* Reason & Review Linking Section */}
        <div className="space-y-3 pt-3 border-t">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="editor-reason" className="text-xs font-semibold">
                Lý do chỉnh sửa <span className="text-destructive">*</span>
              </Label>
              <span className="text-[11px] text-muted-foreground font-mono">
                {reason.length} / 2000 ký tự
              </span>
            </div>
            <Textarea
              id="editor-reason"
              rows={2}
              className="text-xs resize-none"
              placeholder="Giải thích lý do điều chỉnh bản biên soạn (ví dụ: Bổ sung điều kiện trúng tuyển bị bỏ sót sau đối chiếu nguồn)..."
              value={reason}
              onChange={(e) => handleReasonChange(e.target.value)}
              maxLength={2000}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">
              Gắn kết quả Review liên quan (Tùy chọn)
            </Label>
            <Select value={reviewId} onValueChange={handleReviewIdChange}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none" className="text-xs">
                  Không gắn báo cáo review
                </SelectItem>
                {completedReviews.map((r) => (
                  <SelectItem
                    key={r.id}
                    value={r.id}
                    className="text-xs font-mono"
                  >
                    {r.id.slice(0, 12)}... · {r.verdict} (
                    {formatDateTimeValue(r.created_at)})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              Chỉ được chọn các lượt review đã hoàn tất của chính bản gốc này.
            </p>
          </div>
        </div>
      </div>

      {/* Preview Diff Modal */}
      {activePreview && (
        <Dialog open={previewModalOpen} onOpenChange={setPreviewModalOpen}>
          <DialogContent className="sm:max-w-3xl max-h-[min(820px,calc(100vh-2rem))] flex flex-col p-0 gap-0">
            <DialogHeader className="p-4 border-b bg-muted/20">
              <div className="flex items-center gap-2">
                <GitBranch className="size-4 text-primary" />
                <DialogTitle className="text-base font-semibold">
                  Xem trước thay đổi (Edit Preview)
                </DialogTitle>
              </div>
              <DialogDescription className="text-xs text-muted-foreground">
                Đối chiếu nội dung trước và sau do máy chủ trả về. Bản xem trước
                có hiệu lực trong thời gian giới hạn.
              </DialogDescription>
            </DialogHeader>

            <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 text-xs">
              {/* Preview meta */}
              <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-lg bg-muted/20 border text-[11px]">
                <div className="space-y-0.5">
                  <span className="text-muted-foreground block">
                    Preview ID:
                  </span>
                  <span className="font-mono text-foreground">
                    {activePreview.preview_id}
                  </span>
                </div>
                <div className="space-y-0.5">
                  <span className="text-muted-foreground block">
                    Preview SHA-256:
                  </span>
                  <span className="font-mono text-foreground">
                    {activePreview.preview_sha256.slice(0, 16)}...
                  </span>
                </div>
                <div className="space-y-0.5">
                  <span className="text-muted-foreground block">
                    Hạn xác nhận:
                  </span>
                  <span className="font-mono text-warning font-semibold">
                    {formatDateTimeValue(activePreview.expires_at)}
                  </span>
                </div>
              </div>

              {/* Reason */}
              <div className="p-2.5 rounded-lg border bg-primary/5 space-y-0.5">
                <span className="text-[11px] font-semibold text-primary block">
                  Lý do lưu:
                </span>
                <p className="text-foreground text-xs">
                  {activePreview.reason}
                </p>
              </div>

              {/* Side-by-side or stacked diff */}
              <div className="space-y-3">
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-foreground">
                    Tiêu đề:
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2 rounded bg-muted/30 border">
                      <span className="text-[10px] text-muted-foreground block">
                        Trước:
                      </span>
                      {activePreview.before.title}
                    </div>
                    <div className="p-2 rounded bg-primary/10 border border-primary/30">
                      <span className="text-[10px] text-primary block">
                        Sau:
                      </span>
                      {activePreview.after.title}
                    </div>
                  </div>
                </div>

                {/* Sections count diff */}
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-foreground">
                    Cấu trúc mục ({activePreview.after.sections.length} mục sau
                    chỉnh sửa):
                  </span>
                  <div className="space-y-2">
                    {activePreview.after.sections.map((sec, idx) => (
                      <div
                        // biome-ignore lint/suspicious/noArrayIndexKey: preview sections diff
                        key={idx}
                        className="p-2.5 rounded border bg-card text-xs space-y-1.5"
                      >
                        <span className="font-semibold text-primary block">
                          Mục {idx + 1}: {sec.heading}
                        </span>
                        <div className="space-y-1 pl-2 border-l-2 border-primary/30">
                          {sec.paragraphs.map((p, pIdx) => (
                            <div
                              // biome-ignore lint/suspicious/noArrayIndexKey: preview paragraphs diff
                              key={pIdx}
                              className="text-muted-foreground font-sans"
                            >
                              {p.text}
                              {p.citations.length > 0 && (
                                <span className="ml-1 text-[10px] text-primary font-mono">
                                  [{p.citations.join(", ")}]
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter className="p-3 sm:p-4 border-t bg-card flex items-center justify-between gap-2">
              <span className="text-[10px] text-muted-foreground font-mono">
                Key: {acceptIdempotencyKey.slice(0, 16)}...
              </span>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => setPreviewModalOpen(false)}
                  disabled={acceptMutation.isPending}
                >
                  Quay lại sửa
                </Button>
                <Button
                  type="button"
                  size="sm"
                  className="h-8 text-xs gap-1.5"
                  onClick={handleAcceptEdit}
                  disabled={acceptMutation.isPending}
                >
                  {acceptMutation.isPending ? (
                    <>
                      <Loader2 className="size-3 animate-spin" />
                      <span>Đang lưu...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="size-3.5" />
                      <span>Xác nhận tạo bản mới</span>
                    </>
                  )}
                </Button>
              </div>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
