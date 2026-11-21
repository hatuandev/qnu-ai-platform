import { Link } from "@tanstack/react-router";
import { Database, Loader2, MessageSquare, Play } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import type { AnswerReview } from "@/api/answer-reviews";
import { useCreateAnswerReviewMutation } from "@/api/answer-reviews";
import {
  type AssistantResponse,
  useAssistantReadinessQuery,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { AnswerReviewCard } from "./answer-review-card";

export function AskTestPanel({
  workspaceId,
  assistant,
}: {
  workspaceId: string;
  assistant: AssistantResponse;
}) {
  const { data: readiness } = useAssistantReadinessQuery(
    workspaceId,
    assistant.id,
  );
  const createMutation = useCreateAnswerReviewMutation(
    workspaceId,
    assistant.id,
  );
  const [question, setQuestion] = useState("");
  const [lastReview, setLastReview] = useState<AnswerReview | null>(null);

  const isInactive = !assistant.is_active;
  const isUnbound = (assistant.collection_ids?.length ?? 0) === 0;
  const isEmptyCollection = !isUnbound && readiness?.status === "empty";
  const isBlocked = isInactive || isUnbound || isEmptyCollection;
  const isPending = createMutation.isPending;

  const handleRun = async () => {
    const trimmed = question.trim();
    if (!trimmed) {
      toast.error("Vui lòng nhập câu hỏi trước khi chạy thử.");
      return;
    }
    try {
      const review = await createMutation.mutateAsync({
        data: { questions: [trimmed] },
        idempotencyKey: `ask_${crypto.randomUUID()}`,
      });
      setLastReview(review);
      const answered = review.items.filter(
        (item) => item.status === "answered",
      ).length;
      if (review.status === "completed" && answered > 0) {
        toast.success("Đã chạy thử xong. Xem câu trả lời và nguồn bên dưới.");
      } else if (review.status === "completed") {
        toast.warning(
          "Lượt chạy hoàn tất nhưng chưa tìm được căn cứ để trả lời.",
        );
      } else {
        toast.warning(
          "Lượt chạy hoàn tất nhưng có câu hỏi lỗi hoặc chưa xác định.",
        );
      }
    } catch (err: unknown) {
      if (
        err instanceof ApiProblemError &&
        err.code === "assistant_no_published_sources"
      ) {
        toast.error(
          "Kho tri thức chưa có tài liệu xuất bản nên không thể hỏi thử.",
        );
      } else if (
        err instanceof ApiProblemError &&
        err.code === "assistant_inactive"
      ) {
        toast.error("Trợ lý đang tạm dừng; hãy bật lại trước khi hỏi thử.");
      } else {
        toast.error(
          err instanceof Error ? err.message : "Không chạy được lượt hỏi thử.",
        );
      }
    }
  };

  return (
    <div className="space-y-4">
      {isInactive ? (
        <Alert variant="warning">
          <AlertTitle>Trợ lý đang tạm dừng</AlertTitle>
          <AlertDescription>
            Bật lại trợ lý trong tab Cấu hình trước khi hỏi thử để câu trả lời
            dùng đúng cấu hình đang phục vụ.
          </AlertDescription>
        </Alert>
      ) : null}

      {!isInactive && isUnbound ? (
        <Alert variant="info">
          <AlertTitle>Chế độ hội thoại trực tiếp</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>
              Trợ lý đang hoạt động ở chế độ hội thoại LLM trực tiếp (không gắn kho tri thức). Bạn có thể trò chuyện trực tiếp với trợ lý trong màn hình Hội thoại.
            </p>
            <Button size="sm" variant="outline" asChild className="h-7 text-xs gap-1.5 mt-1">
              <Link to="/chat">
                <MessageSquare className="size-3 text-primary" />
                <span>Mở màn hình Hội thoại để trò chuyện</span>
              </Link>
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {!isInactive && isEmptyCollection ? (
        <Alert variant="warning">
          <AlertTitle>Kho tri thức chưa có tài liệu xuất bản</AlertTitle>
          <AlertDescription>
            <span>
              Trợ lý chỉ trả lời từ nội dung đã xuất bản. Hãy xuất bản ít nhất
              một tài liệu trong kho trước khi hỏi thử.
            </span>
            <Button
              asChild
              variant="outline"
              size="sm"
              className="mt-2 h-7 gap-1.5 text-xs"
            >
              <Link
                to="/knowledge"
                search={{ collectionId: assistant.collection_id ?? undefined }}
              >
                <Database className="size-3.5" />
                <span>Mở kho tri thức</span>
              </Link>
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {!isInactive &&
      readiness &&
      (readiness.status === "outdated" ||
        readiness.status === "not_indexed" ||
        readiness.status === "failed") ? (
        <Alert variant="info">
          <AlertTitle>Chỉ mục chưa sẵn sàng</AlertTitle>
          <AlertDescription>
            Kho có thể đang chờ nạp lại chỉ mục; câu trả lời thử có thể thiếu
            nguồn cho tới khi quá trình này hoàn tất.
          </AlertDescription>
        </Alert>
      ) : null}

      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="pb-3 border-b border-border/50">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <MessageSquare className="size-4 text-primary" />
            <span>Thử nghiệm câu trả lời</span>
          </CardTitle>
          <CardDescription>
            Đặt câu hỏi để kiểm tra chất lượng truy xuất và văn phong trả lời
            của trợ lý theo cấu hình hiện hành.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="space-y-2">
            <Textarea
              id="assistant-ask-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              maxLength={8000}
              disabled={isBlocked || isPending}
              placeholder="Nhập câu hỏi thử nghiệm tại đây (VD: Điều kiện xét học bổng khuyến khích học tập năm 2025 là gì?)..."
              rows={4}
              className="resize-none bg-background text-xs leading-relaxed"
            />
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[11px] text-muted-foreground mr-1">
                Gợi ý nhanh:
              </span>
              {[
                "Điều kiện xét học bổng khuyến khích học tập?",
                "Quy chế đào tạo và chuẩn đầu ra mới nhất?",
                "Thông tin tuyển sinh và điểm chuẩn năm gần nhất?",
              ].map((sample) => (
                <button
                  key={sample}
                  type="button"
                  disabled={isBlocked || isPending}
                  onClick={() => setQuestion(sample)}
                  className="rounded-md border border-border/70 bg-muted/40 hover:bg-muted px-2 py-0.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between pt-2 border-t border-border/50">
            <p className="text-[11px] text-muted-foreground">
              Sử dụng đúng mô hình ngôn ngữ, chính sách truy xuất và trích dẫn
              dẫn chứng thực tế từ kho.
            </p>
            <Button
              size="sm"
              className="h-8 shrink-0 gap-1.5 text-xs font-medium shadow-2xs"
              disabled={isBlocked || isPending || !question.trim()}
              onClick={() => void handleRun()}
            >
              {isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Play className="size-3.5" />
              )}
              <span>{isPending ? "Đang chạy..." : "Chạy thử"}</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {isPending ? (
        <div className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3">
          <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-primary" />
          <div className="min-w-0 text-xs">
            <p className="font-medium text-foreground">
              Đang chạy pipeline trả lời thật
            </p>
            <p className="text-muted-foreground">
              Hệ thống đang truy xuất nguồn, gọi mô hình và kiểm chứng câu trả
              lời. Không đóng tab trong khi chờ.
            </p>
          </div>
        </div>
      ) : null}

      {lastReview && !isPending ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-xs font-semibold text-foreground">
              Kết quả hỏi thử
            </h2>
            <Button
              asChild
              variant="link"
              size="sm"
              className="h-6 px-0 text-xs"
            >
              <Link
                to="/assistants/$assistantId"
                params={{ assistantId: assistant.id }}
                search={{ tab: "reviews" }}
              >
                Xem lịch sử kiểm thử
              </Link>
            </Button>
          </div>
          <AnswerReviewCard
            workspaceId={workspaceId}
            assistantId={assistant.id}
            review={lastReview}
            labelable={false}
            defaultOpen
          />
        </div>
      ) : null}
    </div>
  );
}
