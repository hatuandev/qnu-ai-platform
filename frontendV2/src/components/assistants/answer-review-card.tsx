import { ChevronDown, ListChecks } from "lucide-react";
import { type ReactNode, useState } from "react";
import type { AnswerReview, AnswerReviewStatus } from "@/api/answer-reviews";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { AnswerReviewItemCard } from "./answer-review-item";

const STATUS_MAP: Record<
  AnswerReviewStatus,
  {
    label: string;
    variant: "success" | "info" | "warning" | "destructive" | "secondary";
  }
> = {
  running: { label: "Đang chạy", variant: "info" },
  completed: { label: "Hoàn tất", variant: "success" },
  failed: { label: "Có câu lỗi", variant: "destructive" },
  uncertain: { label: "Chưa xác định", variant: "warning" },
};

const dateFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function labelledCount(review: AnswerReview): number {
  return review.items.filter((item) => item.label !== null).length;
}

export function AnswerReviewCard({
  workspaceId,
  assistantId,
  review,
  labelable,
  defaultOpen = false,
  headerExtra,
}: {
  workspaceId: string;
  assistantId: string;
  review: AnswerReview;
  labelable: boolean;
  defaultOpen?: boolean;
  headerExtra?: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const status = STATUS_MAP[review.status];
  const labelled = labelledCount(review);

  return (
    <Collapsible open={open} onOpenChange={setOpen} asChild>
      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="p-0">
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
              aria-label="Mở rộng chi tiết lần kiểm thử"
            >
              <div className="flex min-w-0 items-center gap-2.5">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <ListChecks className="size-4" />
                </div>
                <div className="min-w-0">
                  <CardTitle className="truncate text-sm font-semibold">
                    Kiểm thử lúc{" "}
                    {dateFormatter.format(new Date(review.created_at))}
                  </CardTitle>
                  <p className="truncate text-[11px] text-muted-foreground">
                    {review.question_count} câu hỏi · Phiên bản trợ lý{" "}
                    {review.assistant_revision}
                    {labelled > 0
                      ? ` · ${labelled}/${review.items.length} câu đã gắn nhãn`
                      : null}
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {headerExtra}
                <Badge
                  variant={status.variant}
                  className="h-4 px-1.5 text-[10px] font-normal"
                >
                  {status.label}
                </Badge>
                <ChevronDown
                  className={`size-3.5 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
                />
              </div>
            </button>
          </CollapsibleTrigger>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="space-y-2 px-4 pb-4 pt-0">
            {review.items.map((item) => (
              <AnswerReviewItemCard
                key={item.id}
                workspaceId={workspaceId}
                assistantId={assistantId}
                reviewId={review.id}
                item={item}
                labelable={labelable}
              />
            ))}
            {review.items.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Lần kiểm thử này chưa có câu hỏi nào được ghi nhận.
              </p>
            ) : null}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
