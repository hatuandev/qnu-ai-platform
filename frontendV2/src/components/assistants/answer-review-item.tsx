import { Check, CircleHelp, Loader2, XCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  type AnswerLabel,
  type AnswerReviewItem,
  type AnswerReviewItemStatus,
  useLabelAnswerReviewItemMutation,
} from "@/api/answer-reviews";
import { ApiProblemError } from "@/api/client";
import { AnswerBody } from "@/components/assistants/answer-body";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STATUS_MAP: Record<
  AnswerReviewItemStatus,
  {
    label: string;
    variant: "success" | "warning" | "destructive" | "secondary";
  }
> = {
  answered: { label: "Đã trả lời", variant: "success" },
  insufficient_evidence: { label: "Thiếu căn cứ", variant: "warning" },
  failed: { label: "Lỗi chạy", variant: "destructive" },
  uncertain: { label: "Chưa xác định", variant: "warning" },
};

const LABEL_TEXT: Record<AnswerLabel, string> = {
  correct: "Đúng",
  missing: "Thiếu ý",
  wrong_source: "Sai nguồn",
  wrong_year: "Sai năm",
};

const NO_LABEL = "none";

function resultBody(item: AnswerReviewItem) {
  if (item.status === "failed") {
    return (
      <p className="flex items-start gap-2 text-xs text-destructive">
        <XCircle className="mt-0.5 size-3.5 shrink-0" />
        <span>
          Lần chạy này lỗi nên không có câu trả lời được tạo. Có thể chạy lại
          bằng nút Hỏi thử.
        </span>
      </p>
    );
  }
  if (item.status === "uncertain" || !item.result) {
    return (
      <p className="flex items-start gap-2 text-xs text-muted-foreground">
        <CircleHelp className="mt-0.5 size-3.5 shrink-0" />
        <span>
          Lần chạy bị gián đoạn trước khi hoàn tất. Không có câu trả lời nào
          được ghi nhận cho câu hỏi này.
        </span>
      </p>
    );
  }

  return <AnswerBody result={item.result} />;
}

function LabelEditor({
  workspaceId,
  assistantId,
  reviewId,
  item,
}: {
  workspaceId: string;
  assistantId: string;
  reviewId: string;
  item: AnswerReviewItem;
}) {
  const mutation = useLabelAnswerReviewItemMutation(workspaceId, assistantId);
  const [labelValue, setLabelValue] = useState<string>(item.label ?? NO_LABEL);
  const [note, setNote] = useState(item.label_note ?? "");

  const isDirty =
    labelValue !== (item.label ?? NO_LABEL) || note !== (item.label_note ?? "");
  const hasLabel = labelValue !== NO_LABEL;

  const handleSave = async () => {
    try {
      await mutation.mutateAsync({
        reviewId,
        itemId: item.id,
        data: {
          label: hasLabel ? (labelValue as AnswerLabel) : null,
          note: hasLabel ? note.trim() : "",
        },
      });
      toast.success("Đã lưu nhãn đánh giá.");
    } catch (err: unknown) {
      if (err instanceof ApiProblemError && err.kind === "forbidden") {
        toast.error(
          "Chỉ quản trị viên, biên tập viên hoặc người duyệt mới có thể gắn nhãn.",
        );
      } else if (
        err instanceof ApiProblemError &&
        err.code === "answer_review_item_not_ready"
      ) {
        toast.error("Chỉ gắn nhãn câu hỏi đã có kết quả trả lời.");
      } else {
        toast.error(
          err instanceof Error ? err.message : "Không thể lưu nhãn đánh giá.",
        );
      }
    }
  };

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <Select value={labelValue} onValueChange={setLabelValue}>
        <SelectTrigger
          className="h-8 w-full text-xs sm:w-40"
          aria-label="Nhãn đánh giá câu trả lời"
        >
          <SelectValue placeholder="Gắn nhãn" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NO_LABEL}>Chưa gắn nhãn</SelectItem>
          {(Object.keys(LABEL_TEXT) as AnswerLabel[]).map((value) => (
            <SelectItem key={value} value={value}>
              {LABEL_TEXT[value]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Input
        value={note}
        onChange={(event) => setNote(event.target.value)}
        maxLength={2000}
        disabled={!hasLabel}
        placeholder="Ghi chú (tùy chọn)"
        aria-label="Ghi chú đánh giá"
        className="h-8 flex-1 text-xs"
      />
      <Button
        size="sm"
        variant="outline"
        className="h-8 shrink-0 gap-1.5 text-xs"
        disabled={!isDirty || mutation.isPending}
        onClick={() => void handleSave()}
      >
        {mutation.isPending ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <Check className="size-3.5" />
        )}
        <span>Lưu nhãn</span>
      </Button>
    </div>
  );
}

export function AnswerReviewItemCard({
  workspaceId,
  assistantId,
  reviewId,
  item,
  labelable,
}: {
  workspaceId: string;
  assistantId: string;
  reviewId: string;
  item: AnswerReviewItem;
  labelable: boolean;
}) {
  const status = STATUS_MAP[item.status];
  const canLabel =
    labelable &&
    (item.status === "answered" || item.status === "insufficient_evidence");

  return (
    <div className="rounded-lg border border-border/60">
      <div className="flex items-start justify-between gap-3 border-b border-border/50 px-3 py-2">
        <div className="flex min-w-0 items-start gap-2">
          <span className="mt-0.5 shrink-0 font-mono text-[11px] text-muted-foreground">
            #{item.ordinal + 1}
          </span>
          <p className="text-xs font-medium leading-relaxed text-foreground">
            {item.question}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {item.label ? (
            <Badge
              variant="info"
              className="h-4 px-1.5 text-[10px] font-normal"
            >
              {LABEL_TEXT[item.label]}
            </Badge>
          ) : null}
          <Badge
            variant={status.variant}
            className="h-4 px-1.5 text-[10px] font-normal"
          >
            {status.label}
          </Badge>
        </div>
      </div>
      <div className="space-y-3 px-3 py-2.5">
        {resultBody(item)}
        {item.label_note ? (
          <p className="rounded-md bg-muted/40 px-2 py-1.5 text-[11px] text-muted-foreground">
            <span className="font-medium text-foreground">Ghi chú: </span>
            {item.label_note}
          </p>
        ) : null}
        {canLabel ? (
          <div className="rounded-md border border-dashed border-border/70 p-2">
            <LabelEditor
              workspaceId={workspaceId}
              assistantId={assistantId}
              reviewId={reviewId}
              item={item}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
