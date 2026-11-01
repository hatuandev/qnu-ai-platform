import {
  BookOpen,
  Check,
  Cpu,
  Info,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ConsumerModelBudgetNotice } from "@/features/modelops/capacity-badge";
import { useCatalogQuery } from "@/features/modelops/queries";
import { useCreateCompilationMutation } from "./compilation-queries";
import {
  formatCompilationError,
  generateIdempotencyKey,
} from "./compilation-schemas";
import type { CompilationRequestInput } from "./compilation-types";
import { useProcessingRunsQuery, useTextReviewQuery } from "./ocr-queries";
import { useRevisionsQuery, useSourcesQuery } from "./queries";

export type SelectedOcrRunItem = {
  runId: string;
  sourceId: string;
  sourceTitle: string;
  revisionId: string;
  revisionNo: number;
  generation: number;
  textVersion: number;
};

export function CompilationDialog({
  workspaceId,
  collectionId,
  isOpen,
  onClose,
  initialRun,
  onSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  isOpen: boolean;
  onClose: () => void;
  initialRun?: {
    runId: string;
    sourceId: string;
    sourceTitle: string;
    revisionId: string;
    revisionNo: number;
    generation: number;
    textVersion?: number;
  } | null;
  onSuccess?: (runId: string) => void;
}) {
  const [topic, setTopic] = useState("");
  const [selectedRuns, setSelectedRuns] = useState<SelectedOcrRunItem[]>([]);
  const [providerId, setProviderId] = useState<string>("default");
  const [maxOutputTokens, setMaxOutputTokens] = useState<string>("");
  const [structuredOutput, setStructuredOutput] = useState(false);

  // Auto-review settings
  const [autoReview, setAutoReview] = useState(true);
  const [reviewProviderId, setReviewProviderId] = useState<string>("default");
  const [reviewMaxTokens, setReviewMaxTokens] = useState<string>("");
  const [reviewStructuredOutput, setReviewStructuredOutput] = useState(false);

  // Idempotency & submission
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() =>
    generateIdempotencyKey(),
  );

  // Add OCR Run picker state
  const [pickerSourceId, setPickerSourceId] = useState<string>("");
  const [pickerRevisionId, setPickerRevisionId] = useState<string>("");

  const catalogQuery = useCatalogQuery(workspaceId, { enabled: isOpen });
  const sourcesQuery = useSourcesQuery(workspaceId, collectionId, {
    page: 1,
    pageSize: 100,
  });

  const revisionsQuery = useRevisionsQuery(
    workspaceId,
    collectionId,
    pickerSourceId,
  );

  const availableRunsQuery = useProcessingRunsQuery(
    workspaceId,
    collectionId,
    pickerSourceId,
    pickerRevisionId,
    1,
    50,
    { enabled: Boolean(isOpen && pickerSourceId && pickerRevisionId) },
  );

  const createMutation = useCreateCompilationMutation(
    workspaceId,
    collectionId,
  );

  // Chat providers from catalog
  const chatProviders = useMemo(() => {
    return (catalogQuery.data ?? []).filter((p) =>
      p.capabilities.includes("chat"),
    );
  }, [catalogQuery.data]);

  // Prepopulate initial run if provided
  useEffect(() => {
    if (isOpen) {
      if (initialRun) {
        setSelectedRuns([
          {
            runId: initialRun.runId,
            sourceId: initialRun.sourceId,
            sourceTitle: initialRun.sourceTitle,
            revisionId: initialRun.revisionId,
            revisionNo: initialRun.revisionNo,
            generation: initialRun.generation,
            textVersion: initialRun.textVersion ?? 0,
          },
        ]);
      } else {
        setSelectedRuns([]);
      }
      setTopic("");
      setProviderId("default");
      setMaxOutputTokens("");
      setStructuredOutput(false);
      setAutoReview(true);
      setReviewProviderId("default");
      setReviewMaxTokens("");
      setReviewStructuredOutput(false);
      setIdempotencyKey(generateIdempotencyKey());
      setPickerSourceId("");
      setPickerRevisionId("");
    }
  }, [isOpen, initialRun]);

  const handleTopicChange = (value: string) => {
    setTopic(value);
    setIdempotencyKey(generateIdempotencyKey());
  };

  const handleAddRun = (run: { id: string; generation: number }) => {
    if (selectedRuns.some((r) => r.runId === run.id)) {
      toast.error("Lượt OCR này đã được chọn.");
      return;
    }
    if (selectedRuns.length >= 20) {
      toast.error("Tối đa 20 lượt xử lý OCR cho một lần biên soạn.");
      return;
    }
    const sourceObj = sourcesQuery.data?.items.find(
      (s) => s.id === pickerSourceId,
    );
    const revObj = revisionsQuery.data?.find((r) => r.id === pickerRevisionId);

    setSelectedRuns((prev) => [
      ...prev,
      {
        runId: run.id,
        sourceId: pickerSourceId,
        sourceTitle: sourceObj?.title ?? "Tài liệu",
        revisionId: pickerRevisionId,
        revisionNo: revObj?.revision_no ?? 1,
        generation: run.generation,
        textVersion: 0, // default v0 OCR raw
      },
    ]);
    setIdempotencyKey(generateIdempotencyKey());
    toast.success(`Đã thêm OCR Gen #${run.generation}`);
  };

  const handleRemoveRun = (runId: string) => {
    setSelectedRuns((prev) => prev.filter((r) => r.runId !== runId));
    setIdempotencyKey(generateIdempotencyKey());
  };

  const handleTextVersionChange = (runId: string, version: number) => {
    setSelectedRuns((prev) =>
      prev.map((r) => (r.runId === runId ? { ...r, textVersion: version } : r)),
    );
    setIdempotencyKey(generateIdempotencyKey());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      toast.error("Vui lòng nhập chủ đề biên soạn.");
      return;
    }
    if (selectedRuns.length === 0) {
      toast.error("Vui lòng chọn ít nhất 1 lượt xử lý OCR.");
      return;
    }
    if (selectedRuns.length > 20) {
      toast.error("Tối đa 20 lượt xử lý OCR.");
      return;
    }

    const ocr_run_ids = selectedRuns.map((r) => r.runId);
    const text_versions: Record<string, number> = {};
    for (const item of selectedRuns) {
      if (item.textVersion > 0) {
        text_versions[item.runId] = item.textVersion;
      }
    }

    const payload: CompilationRequestInput = {
      topic: topic.trim(),
      ocr_run_ids,
      text_versions,
      provider_id: providerId === "default" ? null : providerId,
      max_output_tokens: maxOutputTokens ? Number(maxOutputTokens) : null,
      structured_output: structuredOutput,
      auto_review: autoReview,
      review_provider_id:
        reviewProviderId === "default" ? null : reviewProviderId,
      review_max_output_tokens: reviewMaxTokens
        ? Number(reviewMaxTokens)
        : null,
      review_structured_output: reviewStructuredOutput,
    };

    try {
      const outcome = await createMutation.mutateAsync({
        input: payload,
        idempotencyKey,
      });

      toast.success(
        outcome.created
          ? "Đã tạo lượt biên soạn mới."
          : "Đã nạp lại lượt biên soạn trùng lặp (replay).",
      );
      onClose();
      onSuccess?.(outcome.run.id);
    } catch (error: unknown) {
      if (error instanceof ApiProblemError) {
        toast.error(formatCompilationError(error.code, error.message));
      } else {
        toast.error("Không thể tạo lượt biên soạn.");
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-3xl max-h-[min(860px,calc(100vh-2rem))] flex flex-col p-0 gap-0">
        <DialogHeader className="p-4 sm:p-5 border-b bg-muted/20">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <BookOpen className="size-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Tạo lượt biên soạn tri thức (Compiler)
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Tổng hợp nội dung từ các lượt xử lý OCR trong kho tri thức thành
                bản nháp chuẩn mực có dẫn chứng.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5 text-xs">
            {/* Topic Field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label
                  htmlFor="compiler-topic"
                  className="text-xs font-semibold"
                >
                  Chủ đề biên soạn <span className="text-destructive">*</span>
                </Label>
                <span className="text-[11px] text-muted-foreground font-mono">
                  {topic.length} / 2000 ký tự
                </span>
              </div>
              <Textarea
                id="compiler-topic"
                rows={3}
                className="text-xs resize-none"
                placeholder="Ví dụ: Tổng hợp quy định tuyển sinh đại học chính quy, tiêu chuẩn xét tuyển và học phí năm 2026..."
                value={topic}
                onChange={(e) => handleTopicChange(e.target.value)}
                maxLength={2000}
                required
              />
              <p className="text-[11px] text-muted-foreground">
                Chủ đề xác định phạm vi trích xuất và tổng hợp. Mô hình chỉ sử
                dụng các bằng chứng được cung cấp.
              </p>
            </div>

            {/* OCR Runs Selection Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-xs font-semibold">
                    Nguồn OCR & Phiên bản văn bản đã chọn ({selectedRuns.length}{" "}
                    / 20)
                  </Label>
                  <p className="text-[11px] text-muted-foreground">
                    Chỉ sử dụng các lượt OCR đã hoàn tất (`completed`). Mỗi
                    nguồn có thể chọn dùng OCR gốc (v0) hoặc phiên bản rà soát
                    hậu OCR (v1, v2...).
                  </p>
                </div>
              </div>

              {selectedRuns.length === 0 ? (
                <Card className="rounded-lg border-dashed p-4 text-center text-muted-foreground">
                  <p className="text-xs">Chưa có lượt OCR nào được chọn.</p>
                  <p className="text-[11px] text-muted-foreground/70">
                    Chọn tài liệu và lượt OCR ở khung bên dưới để thêm vào danh
                    sách biên soạn.
                  </p>
                </Card>
              ) : (
                <div className="space-y-2 border rounded-lg p-2.5 bg-muted/10">
                  {selectedRuns.map((item) => (
                    <SelectedRunRow
                      key={item.runId}
                      item={item}
                      workspaceId={workspaceId}
                      collectionId={collectionId}
                      onRemove={() => handleRemoveRun(item.runId)}
                      onTextVersionChange={(v) =>
                        handleTextVersionChange(item.runId, v)
                      }
                    />
                  ))}
                </div>
              )}

              {/* Source & OCR Run Picker */}
              <div className="border rounded-lg p-3 bg-card space-y-3">
                <div className="flex items-center gap-1.5 font-medium text-foreground text-xs">
                  <Plus className="size-3.5 text-primary" />
                  <span>Thêm nguồn OCR từ kho tài liệu</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div className="space-y-1">
                    <Label className="text-[11px] text-muted-foreground">
                      Tài liệu nguồn
                    </Label>
                    <Select
                      value={pickerSourceId}
                      onValueChange={(val) => {
                        setPickerSourceId(val);
                        setPickerRevisionId("");
                      }}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Chọn tài liệu nguồn..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(sourcesQuery.data?.items ?? []).map((s) => (
                          <SelectItem
                            key={s.id}
                            value={s.id}
                            className="text-xs"
                          >
                            {s.title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-[11px] text-muted-foreground">
                      Phiên bản tệp (Revision)
                    </Label>
                    <Select
                      value={pickerRevisionId}
                      onValueChange={(val) => setPickerRevisionId(val)}
                      disabled={!pickerSourceId || revisionsQuery.isLoading}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Chọn revision..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(revisionsQuery.data ?? []).map((r) => (
                          <SelectItem
                            key={r.id}
                            value={r.id}
                            className="text-xs"
                          >
                            v{r.revision_no} · {r.file_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {pickerRevisionId && (
                  <div className="pt-2 border-t space-y-1.5">
                    <Label className="text-[11px] text-muted-foreground">
                      Các lượt OCR đã hoàn thành của phiên bản này:
                    </Label>
                    {availableRunsQuery.isLoading ? (
                      <Skeleton className="h-8 w-full" />
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {(availableRunsQuery.data?.items ?? [])
                          .filter((r) => r.status === "completed")
                          .map((r) => {
                            const isAdded = selectedRuns.some(
                              (s) => s.runId === r.id,
                            );
                            return (
                              <Button
                                key={r.id}
                                type="button"
                                size="sm"
                                variant={isAdded ? "secondary" : "outline"}
                                className="h-7 text-xs gap-1.5"
                                disabled={isAdded}
                                onClick={() =>
                                  handleAddRun({
                                    id: r.id,
                                    generation: r.generation,
                                  })
                                }
                              >
                                {isAdded ? (
                                  <Check className="size-3 text-primary" />
                                ) : (
                                  <Plus className="size-3" />
                                )}
                                <span>
                                  Gen #{r.generation} (
                                  {r.provider_id || "Mặc định"})
                                </span>
                              </Button>
                            );
                          })}
                        {(availableRunsQuery.data?.items ?? []).filter(
                          (r) => r.status === "completed",
                        ).length === 0 && (
                          <p className="text-[11px] text-muted-foreground italic">
                            Chưa có lượt OCR completed nào cho phiên bản này.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Model & Output Settings */}
            <div className="space-y-3 pt-2 border-t">
              <Label className="text-xs font-semibold">
                Cấu hình mô hình biên soạn
              </Label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label
                    htmlFor="compiler-provider"
                    className="text-[11px] text-muted-foreground"
                  >
                    Model biên soạn (Capability Chat)
                  </Label>
                  <Select
                    value={providerId}
                    onValueChange={(val) => {
                      setProviderId(val);
                      setIdempotencyKey(generateIdempotencyKey());
                    }}
                  >
                    <SelectTrigger
                      id="compiler-provider"
                      className="h-8 text-xs"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default" className="text-xs">
                        Theo mặc định workspace (Khuyên dùng)
                      </SelectItem>
                      {chatProviders.map((p) => (
                        <SelectItem key={p.id} value={p.id} className="text-xs">
                          {p.name} ({p.model_name})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-[11px] text-muted-foreground">
                    Để trống sẽ dùng model Chat mặc định của workspace.
                  </p>
                  <ConsumerModelBudgetNotice
                    model={chatProviders.find((p) => p.id === providerId)}
                    defaultModel={chatProviders.find((p) =>
                      p.default_capabilities?.includes("chat"),
                    )}
                    isDefaultSelection={!providerId}
                    capability="chat"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label
                    htmlFor="compiler-max-tokens"
                    className="text-[11px] text-muted-foreground"
                  >
                    Giới hạn Output Tokens (Tùy chọn)
                  </Label>
                  <Input
                    id="compiler-max-tokens"
                    type="number"
                    min={1}
                    className="h-8 text-xs font-mono"
                    placeholder="Mặc định theo mô hình"
                    value={maxOutputTokens}
                    onChange={(e) => {
                      setMaxOutputTokens(e.target.value);
                      setIdempotencyKey(generateIdempotencyKey());
                    }}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <Checkbox
                  id="compiler-structured"
                  checked={structuredOutput}
                  onCheckedChange={(checked) => {
                    setStructuredOutput(Boolean(checked));
                    setIdempotencyKey(generateIdempotencyKey());
                  }}
                />
                <Label
                  htmlFor="compiler-structured"
                  className="text-xs font-normal text-muted-foreground cursor-pointer"
                >
                  Bật Structured Output nâng cao (JSON Schema strict)
                </Label>
              </div>
            </div>

            {/* Auto-Review Section */}
            <div className="space-y-3 pt-3 border-t">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-xs font-semibold">
                    Đánh giá & Rà soát tự động (Auto-Review)
                  </Label>
                  <p className="text-[11px] text-muted-foreground">
                    Tự động gửi yêu cầu đánh giá độc lập hai chiều ngay khi
                    Compiler hoàn tất.
                  </p>
                </div>
                <Switch
                  checked={autoReview}
                  onCheckedChange={(checked) => {
                    setAutoReview(checked);
                    setIdempotencyKey(generateIdempotencyKey());
                  }}
                />
              </div>

              {autoReview ? (
                <div className="rounded-lg border p-3 bg-muted/10 space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-[11px] text-muted-foreground">
                        Reviewer Provider (Tùy chọn)
                      </Label>
                      <Select
                        value={reviewProviderId}
                        onValueChange={(val) => {
                          setReviewProviderId(val);
                          setIdempotencyKey(generateIdempotencyKey());
                        }}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="default" className="text-xs">
                            Dùng provider Compiler ghim (Khuyên dùng)
                          </SelectItem>
                          {chatProviders.map((p) => (
                            <SelectItem
                              key={p.id}
                              value={p.id}
                              className="text-xs"
                            >
                              {p.name} ({p.model_name})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-[10px] text-muted-foreground">
                        Với auto-review, để trống sẽ dùng đúng provider được
                        ghim của Compiler.
                      </p>
                      <ConsumerModelBudgetNotice
                        model={chatProviders.find(
                          (p) => p.id === reviewProviderId,
                        )}
                        defaultModel={
                          chatProviders.find((p) => p.id === providerId) ??
                          chatProviders.find((p) =>
                            p.default_capabilities?.includes("chat"),
                          )
                        }
                        isDefaultSelection={!reviewProviderId}
                        capability="chat"
                      />
                    </div>

                    <div className="space-y-1">
                      <Label className="text-[11px] text-muted-foreground">
                        Giới hạn Output Tokens Review
                      </Label>
                      <Input
                        type="number"
                        min={1}
                        className="h-8 text-xs font-mono"
                        value={reviewMaxTokens}
                        onChange={(e) => {
                          setReviewMaxTokens(e.target.value);
                          setIdempotencyKey(generateIdempotencyKey());
                        }}
                      />
                      <p className="text-[10px] text-muted-foreground">
                        Để trống để tự chọn theo giới hạn model và dung lượng
                        đầu vào.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="compiler-review-structured"
                      checked={reviewStructuredOutput}
                      onCheckedChange={(checked) => {
                        setReviewStructuredOutput(Boolean(checked));
                        setIdempotencyKey(generateIdempotencyKey());
                      }}
                    />
                    <Label
                      htmlFor="compiler-review-structured"
                      className="text-xs font-normal text-muted-foreground cursor-pointer"
                    >
                      Bật Review Structured Output (Keyed contract)
                    </Label>
                  </div>
                </div>
              ) : null}
            </div>

            {/* Warning Note */}
            <Alert className="rounded-lg border-info/30 bg-info/5 text-xs py-2.5">
              <Info className="size-3.5 text-info shrink-0" />
              <AlertDescription className="text-muted-foreground text-[11px] leading-relaxed">
                Biên soạn tài liệu sẽ tiêu tốn tokens theo định mức của mô hình
                đã chọn. Bản hoàn tất là bản nháp chưa được duyệt và chưa tự
                động đưa vào phục vụ Trò chuyện.
              </AlertDescription>
            </Alert>
          </div>

          <DialogFooter className="p-3 sm:p-4 border-t bg-card flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground font-mono truncate max-w-[200px]">
              Khóa: {idempotencyKey.slice(0, 16)}...
            </span>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={onClose}
                disabled={createMutation.isPending}
              >
                Hủy
              </Button>
              <Button
                type="submit"
                size="sm"
                className="h-8 text-xs gap-1.5"
                disabled={
                  createMutation.isPending ||
                  !topic.trim() ||
                  selectedRuns.length === 0
                }
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="size-3 animate-spin" />
                    <span>Đang gửi...</span>
                  </>
                ) : (
                  <>
                    <Cpu className="size-3.5" />
                    <span>Bắt đầu biên soạn</span>
                  </>
                )}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function SelectedRunRow({
  item,
  workspaceId,
  collectionId,
  onRemove,
  onTextVersionChange,
}: {
  item: SelectedOcrRunItem;
  workspaceId: string;
  collectionId: string;
  onRemove: () => void;
  onTextVersionChange: (version: number) => void;
}) {
  // Query text review to check available text versions
  const textReviewQuery = useTextReviewQuery(
    workspaceId,
    collectionId,
    item.sourceId,
    item.revisionId,
    item.runId,
    null,
    { enabled: true },
  );

  const reviewDoc = textReviewQuery.data;
  const maxVersion = reviewDoc?.version ?? 0;

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 rounded-md bg-card border text-xs">
      <div className="space-y-0.5 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-medium text-foreground truncate max-w-[200px]">
            {item.sourceTitle}
          </span>
          <Badge variant="outline" className="font-mono text-[10px] py-0">
            Rev v{item.revisionNo}
          </Badge>
          <Badge variant="secondary" className="font-mono text-[10px] py-0">
            Gen #{item.generation}
          </Badge>
        </div>
        <div className="text-[11px] text-muted-foreground font-mono truncate">
          Run ID: {item.runId}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground whitespace-nowrap">
            Văn bản:
          </span>
          <Select
            value={String(item.textVersion)}
            onValueChange={(val) => onTextVersionChange(Number(val))}
          >
            <SelectTrigger className="h-7 text-xs w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="0" className="text-xs">
                v0 (OCR gốc)
              </SelectItem>
              {maxVersion > 0 &&
                Array.from({ length: maxVersion }, (_, i) => i + 1).map((v) => (
                  <SelectItem key={v} value={String(v)} className="text-xs">
                    v{v} (Bản rà soát #{v})
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
          onClick={onRemove}
          title="Xóa khỏi danh sách biên soạn"
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>
    </div>
  );
}
