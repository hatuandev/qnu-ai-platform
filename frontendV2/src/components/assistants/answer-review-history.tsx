import { ListChecks } from "lucide-react";
import { useAnswerReviewsQuery } from "@/api/answer-reviews";
import { EmptyState } from "@/components/admin/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { AnswerReviewCard } from "./answer-review-card";

export function AnswerReviewHistory({
  workspaceId,
  assistantId,
  onGoToAsk,
}: {
  workspaceId: string;
  assistantId: string;
  onGoToAsk?: () => void;
}) {
  const {
    data: reviews = [],
    isLoading,
    isError,
    refetch,
  } = useAnswerReviewsQuery(workspaceId, assistantId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {["first", "second", "third"].map((slot) => (
          <Skeleton
            key={`answer-review-skeleton-${slot}`}
            className="h-20 rounded-lg"
          />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <EmptyState
        icon={ListChecks}
        title="Không tải được lịch sử kiểm thử"
        description="Kết nối tới máy chủ không thành công hoặc phiên đăng nhập đã hết hạn."
        action={{ label: "Tải lại", onClick: () => void refetch() }}
      />
    );
  }

  if (reviews.length === 0) {
    return (
      <EmptyState
        icon={ListChecks}
        title="Chưa có lần kiểm thử nào"
        description="Chạy Hỏi thử để lưu lại câu trả lời thật của trợ lý, sau đó quay lại đây để gắn nhãn đúng, thiếu ý, sai nguồn hoặc sai năm."
        action={
          onGoToAsk
            ? {
                label: "Chạy hỏi thử ngay",
                onClick: onGoToAsk,
              }
            : undefined
        }
      />
    );
  }

  return (
    <div className="space-y-3">
      {reviews.map((review, index) => (
        <AnswerReviewCard
          key={review.id}
          workspaceId={workspaceId}
          assistantId={assistantId}
          review={review}
          labelable
          defaultOpen={index === 0}
        />
      ))}
      <p className="text-[11px] text-muted-foreground">
        Hiển thị 20 lần kiểm thử gần nhất. Nhãn đánh giá chỉ lưu trên câu trả
        lời quan sát, không thay đổi kho tri thức.
      </p>
    </div>
  );
}
