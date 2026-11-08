import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  Database,
  FlaskConical,
  Loader2,
  Play,
  Plus,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { AnswerReviewResult } from "@/features/answer-review/answer-review-result";
import {
  ANSWER_REVIEW_STATUS_META,
  formatAnswerReviewError,
} from "@/features/answer-review/format";
import {
  useAnswerReviewsQuery,
  useCreateAnswerReview,
  useLabelAnswerReviewItem,
} from "@/features/answer-review/queries";
import type {
  AnswerReviewItem,
  AnswerReviewLabel,
} from "@/features/answer-review/types";
import {
  READINESS_BADGE,
  readinessDetail,
} from "@/features/assistants/readiness";
import type {
  Assistant,
  AssistantReadiness,
} from "@/features/assistants/types";
import { CitationSheet } from "@/features/conversations/citation-sheet";
import { generateIdempotencyKey } from "@/features/conversations/schemas";
import type { EvidenceSource, Statement } from "@/features/conversations/types";
import { DEFAULT_PAGE_SEARCH } from "@/features/workspaces/search";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

type QuestionField = { id: string; text: string };

type CitationTarget = {
  statement: Statement | null;
  sources: EvidenceSource[];
};

function createQuestionField(): QuestionField {
  return { id: generateIdempotencyKey(), text: "" };
}

export function AnswerReviewSheet({
  workspaceId,
  assistant,
  readiness,
  isReadinessPending,
  isReadinessError,
  canLabel,
  open,
  onOpenChange,
}: {
  workspaceId: string;
  assistant: Assistant;
  readiness?: AssistantReadiness | null;
  isReadinessPending: boolean;
  isReadinessError: boolean;
  canLabel: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [questions, setQuestions] = useState<QuestionField[]>([
    createQuestionField(),
  ]);
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [citation, setCitation] = useState<CitationTarget | null>(null);
  const [durationMs, setDurationMs] = useState<number | null>(null);
  const submissionRef = useRef<{ signature: string; key: string } | null>(null);

  const reviewsQuery = useAnswerReviewsQuery(workspaceId, assistant.id, {
    enabled: open,
  });
  const createMutation = useCreateAnswerReview(workspaceId, assistant.id);
  const labelMutation = useLabelAnswerReviewItem(workspaceId, assistant.id);

  useEffect(() => {
    if (!open) return;
    setQuestions([createQuestionField()]);
    setSelectedReviewId(null);
    setCitation(null);
    setDurationMs(null);
    submissionRef.current = null;
  }, [open]);

  const reviews = useMemo(
    () =>
      [...(reviewsQuery.data ?? [])].sort((left, right) =>
        right.created_at.localeCompare(left.created_at),
      ),
    [reviewsQuery.data],
  );

  const currentReview = useMemo(() => {
    if (selectedReviewId) {
      const cached = reviews.find((review) => review.id === selectedReviewId);
      if (cached) return cached;
      return createMutation.data?.id === selectedReviewId
        ? createMutation.data
        : null;
    }
    return createMutation.data ?? reviews[0] ?? null;
  }, [selectedReviewId, reviews, createMutation.data]);

  const runQuestions = useMemo(
    () =>
      questions
        .map((field) => field.text.trim())
        .filter((question) => question.length > 0),
    [questions],
  );
  const hasDuplicateQuestions =
    new Set(runQuestions).size !== runQuestions.length;
  const isRunBlocked = !assistant.is_active || readiness?.status === "empty";
  const canRun =
    runQuestions.length > 0 &&
    runQuestions.length <= 3 &&
    !hasDuplicateQuestions &&
    !isRunBlocked &&
    !createMutation.isPending;

  const handleQuestionChange = (id: string, text: string) => {
    setQuestions((current) =>
      current.map((field) => (field.id === id ? { ...field, text } : field)),
    );
  };

  const handleAddQuestion = () => {
    setQuestions((current) =>
      current.length >= 3 ? current : [...current, createQuestionField()],
    );
  };

  const handleRemoveQuestion = (id: string) => {
    setQuestions((current) =>
      current.length <= 1
        ? current
        : current.filter((field) => field.id !== id),
    );
  };

  const handleRun = () => {
    if (!canRun) return;
    const signature = runQuestions.join("\n");
    if (submissionRef.current?.signature !== signature) {
      submissionRef.current = {
        signature,
        key: generateIdempotencyKey(),
      };
    }
    const idempotencyKey = submissionRef.current.key;
    const startedAt = performance.now();
    createMutation.mutate(
      { input: { questions: runQuestions }, idempotencyKey },
      {
        onSuccess: (review) => {
          submissionRef.current = null;
          setDurationMs(Math.round(performance.now() - startedAt));
          setSelectedReviewId(review.id);
          toast.success("Đã chạy kiểm thử trên tài liệu đã xuất bản.");
        },
      },
    );
  };

  const handleSaveLabel = (
    reviewId: string,
    item: AnswerReviewItem,
    label: AnswerReviewLabel | null,
    note: string,
  ) => {
    labelMutation.mutate(
      { reviewId, itemId: item.id, input: { label, note } },
      {
        onSuccess: () => toast.success("Đã lưu nhãn đánh giá."),
        onError: (error) => {
          toast.error(
            error instanceof ApiProblemError
              ? formatAnswerReviewError(error.code, error.message)
              : "Không lưu được nhãn đánh giá.",
          );
        },
      },
    );
  };

  const createError = createMutation.error;
  const createErrorCode =
    createError instanceof ApiProblemError ? createError.code : null;
  const savingItemId = labelMutation.isPending
    ? (labelMutation.variables?.itemId ?? null)
    : null;

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          side="right"
          className="w-full max-w-none sm:max-w-3xl p-0 flex flex-col h-full bg-background border-l"
        >
          <SheetHeader className="border-b bg-muted/20 px-5 py-4 shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                <FlaskConical className="size-4" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">
                  Kiểm thử trả lời
                </SheetTitle>
                <SheetDescription className="text-xs text-muted-foreground mt-0.5">
                  Hỏi tối đa 3 câu qua pipeline hội thoại thật để kiểm tra căn
                  cứ và dẫn nguồn.
                </SheetDescription>
              </div>
            </div>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto min-h-0 p-4 sm:p-5 space-y-6">
            <ReadinessNotice
              workspaceId={workspaceId}
              assistant={assistant}
              readiness={readiness}
              isPending={isReadinessPending}
              isError={isReadinessError}
            />

            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-foreground">
                  Bộ câu hỏi kiểm thử
                </h3>
                <span className="text-[11px] text-muted-foreground">
                  {questions.length}/3
                </span>
              </div>

              {questions.map((field, index) => (
                <div key={field.id} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <Label htmlFor={field.id} className="text-xs font-medium">
                      Câu hỏi {index + 1}
                    </Label>
                    {questions.length > 1 ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-1.5 text-muted-foreground"
                        aria-label={`Xoá câu hỏi ${index + 1}`}
                        onClick={() => handleRemoveQuestion(field.id)}
                      >
                        <X className="size-3.5" />
                      </Button>
                    ) : null}
                  </div>
                  <Textarea
                    id={field.id}
                    value={field.text}
                    onChange={(event) =>
                      handleQuestionChange(field.id, event.target.value)
                    }
                    rows={2}
                    maxLength={8000}
                    className="text-sm"
                    placeholder="Ví dụ: Điều kiện xét tuyển ngành Công nghệ thông tin năm 2026 là gì?"
                  />
                </div>
              ))}

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  disabled={questions.length >= 3}
                  onClick={handleAddQuestion}
                >
                  <Plus className="size-3.5" />
                  Thêm câu hỏi
                </Button>
                <Button
                  size="sm"
                  className="gap-1.5"
                  disabled={!canRun}
                  onClick={handleRun}
                >
                  {createMutation.isPending ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Play className="size-3.5" />
                  )}
                  {createMutation.isPending
                    ? "Đang trả lời..."
                    : "Chạy kiểm thử"}
                </Button>
              </div>

              {hasDuplicateQuestions ? (
                <p className="text-[11px] text-destructive">
                  Các câu hỏi trong cùng bộ kiểm thử không được trùng nhau.
                </p>
              ) : null}

              {!assistant.is_active ? (
                <p className="text-[11px] text-destructive">
                  Trợ lý đang tạm dừng nên không thể chạy kiểm thử mới. Bạn vẫn
                  xem được lịch sử bên dưới.
                </p>
              ) : null}

              {createMutation.isPending ? (
                <p className="text-[11px] text-muted-foreground">
                  Đang chạy từng câu qua pipeline; thời gian phụ thuộc model và
                  số câu hỏi.
                </p>
              ) : null}

              {createMutation.isError ? (
                <Alert variant="destructive">
                  <AlertCircle className="size-4" />
                  <AlertDescription className="text-xs leading-relaxed">
                    {formatAnswerReviewError(
                      createErrorCode,
                      createError?.message,
                    )}
                    <span className="block text-[11px] mt-1">
                      Nếu lỗi do mạng, chạy lại cùng bộ câu hỏi để dùng đúng
                      khóa idempotency.
                    </span>
                  </AlertDescription>
                </Alert>
              ) : null}
            </section>

            {currentReview ? (
              <AnswerReviewResult
                review={currentReview}
                canLabel={canLabel}
                savingItemId={savingItemId}
                durationMs={durationMs}
                onSaveLabel={handleSaveLabel}
                onOpenCitation={(statement, sources) =>
                  setCitation({ statement, sources })
                }
              />
            ) : reviewsQuery.isPending && open ? (
              <div className="space-y-2">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : reviewsQuery.isError ? (
              <Alert variant="destructive">
                <AlertCircle className="size-4" />
                <AlertDescription className="text-xs">
                  Không tải được lịch sử kiểm thử. Thử mở lại ngăn này để tải
                  lại.
                </AlertDescription>
              </Alert>
            ) : (
              <div className="rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground">
                Chưa có lần kiểm thử nào cho trợ lý này.
              </div>
            )}

            {reviews.length > 0 ? (
              <section className="space-y-2">
                <h3 className="text-sm font-semibold text-foreground">
                  Lịch sử kiểm thử
                </h3>
                <div className="space-y-1.5">
                  {reviews.slice(0, 10).map((review) => {
                    const statusMeta = ANSWER_REVIEW_STATUS_META[review.status];
                    const isSelected = currentReview?.id === review.id;
                    return (
                      <Button
                        key={review.id}
                        variant="outline"
                        className={cn(
                          "h-auto w-full justify-between gap-3 px-3 py-2 text-left",
                          isSelected && "border-primary/50 bg-primary/5",
                        )}
                        onClick={() => {
                          setSelectedReviewId(review.id);
                          setDurationMs(null);
                        }}
                      >
                        <span className="flex flex-col items-start gap-0.5 min-w-0">
                          <span className="text-xs font-medium">
                            {formatDateTimeValue(review.created_at)}
                          </span>
                          <span className="text-[11px] text-muted-foreground">
                            {review.question_count} câu · cấu hình v
                            {review.assistant_revision}
                          </span>
                        </span>
                        <Badge
                          variant={statusMeta.variant}
                          className="text-[10px] shrink-0"
                        >
                          {statusMeta.label}
                        </Badge>
                      </Button>
                    );
                  })}
                </div>
              </section>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>

      <CitationSheet
        open={citation !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setCitation(null);
        }}
        statement={citation?.statement}
        sources={citation?.sources ?? []}
        workspaceId={workspaceId}
        collectionId={assistant.collection_id}
      />
    </>
  );
}

function ReadinessNotice({
  workspaceId,
  assistant,
  readiness,
  isPending,
  isError,
}: {
  workspaceId: string;
  assistant: Assistant;
  readiness?: AssistantReadiness | null;
  isPending: boolean;
  isError: boolean;
}) {
  const isEmpty = readiness?.status === "empty";

  return (
    <Alert
      className={cn(
        "border-border bg-muted/20",
        isEmpty && "border-warning/40 bg-warning/5",
      )}
    >
      <Database className="size-4 text-primary" />
      <AlertTitle className="text-xs font-semibold flex flex-wrap items-center gap-2">
        Phạm vi kiểm thử: tài liệu đã xuất bản
        {readiness ? (
          <Badge
            variant={READINESS_BADGE[readiness.status].variant}
            className="text-[10px]"
          >
            {READINESS_BADGE[readiness.status].label}
          </Badge>
        ) : null}
      </AlertTitle>
      <AlertDescription className="text-xs space-y-1.5">
        <p>
          {readiness?.collection_name
            ? `Bộ sưu tập “${readiness.collection_name}”. `
            : ""}
          {isPending
            ? "Đang kiểm tra tài liệu xuất bản và chỉ mục đang phục vụ..."
            : isError
              ? "Không kiểm tra được trạng thái tài liệu; kết quả có thể báo thiếu bằng chứng."
              : readiness
                ? readinessDetail(readiness)
                : "Chưa có thông tin trạng thái tài liệu phục vụ."}
        </p>
        <p className="text-muted-foreground">
          Trợ lý không dùng bản nháp và không bổ sung kiến thức ngoài kho. Câu
          trả lời thiếu căn cứ sẽ được báo là thiếu bằng chứng.
        </p>
        {isEmpty ? (
          <Link
            to="/workspaces/$workspaceId/collections/$collectionId"
            params={{ workspaceId, collectionId: assistant.collection_id }}
            search={DEFAULT_PAGE_SEARCH}
            className="inline-flex text-[11px] font-medium text-primary hover:underline"
          >
            Mở kho tri thức để xuất bản tài liệu
          </Link>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}
