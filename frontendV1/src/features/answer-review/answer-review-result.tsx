import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { formatDateTimeValue } from "@/lib/date-utils";
import {
  AnswerReviewItemCard,
  type OpenCitationHandler,
} from "./answer-review-item-card";
import { ANSWER_REVIEW_STATUS_META, formatAnswerReviewError } from "./format";
import type {
  AnswerReview,
  AnswerReviewItem,
  AnswerReviewLabel,
} from "./types";

export function AnswerReviewResult({
  review,
  canLabel,
  savingItemId,
  durationMs,
  onSaveLabel,
  onOpenCitation,
}: {
  review: AnswerReview;
  canLabel: boolean;
  savingItemId: string | null;
  durationMs: number | null;
  onSaveLabel: (
    reviewId: string,
    item: AnswerReviewItem,
    label: AnswerReviewLabel | null,
    note: string,
  ) => void;
  onOpenCitation: OpenCitationHandler;
}) {
  const statusMeta = ANSWER_REVIEW_STATUS_META[review.status];

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">
          Kết quả lần kiểm thử
        </h3>
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
          <span>{formatDateTimeValue(review.created_at)}</span>
          <Badge variant={statusMeta.variant} className="text-[10px]">
            {statusMeta.label}
          </Badge>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <Badge variant="outline" className="text-[10px]">
          Cấu hình trợ lý v{review.assistant_revision}
        </Badge>
        <span>{review.question_count} câu hỏi</span>
        {durationMs !== null ? (
          <span>
            Thời gian chạy đo tại trình duyệt: {(durationMs / 1000).toFixed(1)}{" "}
            giây
          </span>
        ) : null}
      </div>

      {review.error_code ? (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription className="text-xs">
            {formatAnswerReviewError(review.error_code)}
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="space-y-3">
        {review.items.map((item) => (
          <AnswerReviewItemCard
            key={`${review.id}:${item.id}:${item.label ?? "none"}:${item.label_note ?? ""}`}
            item={item}
            assistantRevision={review.assistant_revision}
            canLabel={canLabel}
            isSavingLabel={savingItemId === item.id}
            onSaveLabel={(target, label, note) =>
              onSaveLabel(review.id, target, label, note)
            }
            onOpenCitation={onOpenCitation}
          />
        ))}
      </div>

      <p className="text-[11px] text-muted-foreground leading-relaxed">
        Kết quả phản ánh tài liệu đã xuất bản tại thời điểm chạy. Nhãn do người
        kiểm thử gắn không phải nhãn vàng retrieval và không tự động thay đổi
        benchmark.
      </p>
    </section>
  );
}
