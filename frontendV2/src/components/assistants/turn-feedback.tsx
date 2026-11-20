import { Check, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

type FeedbackState = {
  rating: "like" | "dislike";
  reason?: string;
};

const DISLIKE_REASONS = [
  "Thiếu ý / thiếu tiểu mục từ văn bản",
  "Sai nguồn trích dẫn hoặc bảng đối chiếu",
  "Sai năm / mốc chu kỳ triển khai",
  "Chưa trả lời đúng trọng tâm câu hỏi",
  "Thông tin chưa chính xác với văn bản gốc",
];

function getStoredFeedback(turnId: string): FeedbackState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(`qnu_feedback_${turnId}`);
    return raw ? (JSON.parse(raw) as FeedbackState) : null;
  } catch {
    return null;
  }
}

function saveFeedback(turnId: string, feedback: FeedbackState | null) {
  if (typeof window === "undefined") return;
  try {
    if (feedback) {
      localStorage.setItem(`qnu_feedback_${turnId}`, JSON.stringify(feedback));
    } else {
      localStorage.removeItem(`qnu_feedback_${turnId}`);
    }
  } catch {
    // ignore localStorage errors
  }
}

export function TurnFeedback({ turnId }: { turnId: string }) {
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [popoverOpen, setPopoverOpen] = useState(false);

  useEffect(() => {
    setFeedback(getStoredFeedback(turnId));
  }, [turnId]);

  const handleLike = () => {
    if (feedback?.rating === "like") {
      setFeedback(null);
      saveFeedback(turnId, null);
      toast.info("Đã bỏ đánh giá.");
      return;
    }
    const next: FeedbackState = { rating: "like" };
    setFeedback(next);
    saveFeedback(turnId, next);
    toast.success("Cảm ơn bạn đã đánh giá câu trả lời hữu ích!");
  };

  const handleSelectDislikeReason = (reason: string) => {
    const next: FeedbackState = { rating: "dislike", reason };
    setFeedback(next);
    saveFeedback(turnId, next);
    setPopoverOpen(false);
    toast.info(`Đã ghi nhận phản hồi kiểm thử: ${reason}`);
  };

  return (
    <div className="flex items-center gap-0.5">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={cn(
          "h-6 px-1.5 text-[11px] gap-1 hover:text-foreground cursor-pointer text-muted-foreground",
          feedback?.rating === "like" &&
            "text-primary font-medium bg-primary/10 hover:bg-primary/15",
        )}
        onClick={handleLike}
        title="Câu trả lời đúng / hữu ích"
      >
        <ThumbsUp className="size-3" />
        {feedback?.rating === "like" ? (
          <span className="text-[10px]">Hữu ích</span>
        ) : null}
      </Button>

      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn(
              "h-6 px-1.5 text-[11px] gap-1 hover:text-foreground cursor-pointer text-muted-foreground",
              feedback?.rating === "dislike" &&
                "text-destructive font-medium bg-destructive/10 hover:bg-destructive/15",
            )}
            title="Đánh giá câu trả lời cần cải thiện"
          >
            <ThumbsDown className="size-3" />
            {feedback?.rating === "dislike" ? (
              <span className="text-[10px] text-destructive">
                {feedback.reason ? "Đã góp ý" : "Chưa hài lòng"}
              </span>
            ) : null}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-68 p-2.5 text-xs space-y-2" align="end">
          <p className="font-semibold text-foreground text-[11px]">
            Đóng góp ý kiến cho kiểm thử:
          </p>
          <div className="flex flex-col gap-1">
            {DISLIKE_REASONS.map((reason) => (
              <button
                key={reason}
                type="button"
                className={cn(
                  "flex items-center justify-between rounded px-2 py-1 text-left text-[11px] transition-colors cursor-pointer text-muted-foreground hover:bg-muted hover:text-foreground",
                  feedback?.reason === reason &&
                    "bg-primary/10 text-primary font-medium",
                )}
                onClick={() => handleSelectDislikeReason(reason)}
              >
                <span>{reason}</span>
                {feedback?.reason === reason ? (
                  <Check className="size-3 text-primary shrink-0" />
                ) : null}
              </button>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
