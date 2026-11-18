import { CircleHelp, Loader2, TriangleAlert, XCircle } from "lucide-react";
import type { ConversationTurn, DirectReply } from "@/api/conversations";
import { AnswerBody } from "@/components/assistants/answer-body";
import { Badge } from "@/components/ui/badge";

export const TURN_ERROR_TEXT: Record<string, string> = {
  conversation_turn_failed:
    "Lượt hỏi lỗi khi chạy mô hình hoặc truy xuất nguồn.",
  conversation_turn_interrupted:
    "Lượt hỏi bị gián đoạn (máy chủ xử lý dừng hoặc quá hạn).",
  conversation_turn_expired: "Lượt hỏi đã quá hạn xử lý.",
  assistant_inactive: "Trợ lý đã tạm dừng khi lượt hỏi được gửi.",
  assistant_no_published_sources:
    "Kho tri thức chưa có tài liệu xuất bản để trả lời.",
  index_not_ready:
    "Kho tri thức chưa có chỉ mục đang hoạt động nên chưa thể trả lời.",
  conversation_clarification_required:
    "Trợ lý cần bạn làm rõ thêm câu hỏi trước khi trả lời.",
  answer_scope_clarification_required:
    "Trợ lý cần bạn nêu rõ phạm vi (ngành/khóa/năm dữ liệu) trước khi trả lời.",
  chat_provider_changed:
    "Mô hình của trợ lý đã thay đổi trong khi xử lý; hãy gửi lại câu hỏi.",
  conversation_route_invalid:
    "Bước điều phối câu hỏi trả về kết quả không hợp lệ.",
};

const DIRECT_ROUTE_TEXT: Record<DirectReply["route"], string> = {
  greeting: "Chào hỏi",
  courtesy: "Xã giao",
  identity: "Giới thiệu",
  protected_request: "Yêu cầu cần bảo vệ",
  guardrail: "Ngoài phạm vi hỗ trợ",
};

function directReplyBody(reply: DirectReply) {
  return (
    <div className="space-y-2">
      <Badge variant="secondary" className="h-4 px-1.5 text-[10px] font-normal">
        Trả lời trực tiếp · {DIRECT_ROUTE_TEXT[reply.route]}
      </Badge>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
        {reply.answer}
      </p>
    </div>
  );
}

export function TurnResult({ turn }: { turn: ConversationTurn }) {
  if (turn.status === "running") {
    return (
      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" />
        <span>Đang xử lý câu trả lời.</span>
      </p>
    );
  }

  if (turn.status === "failed") {
    const message = turn.error_code
      ? TURN_ERROR_TEXT[turn.error_code]
      : undefined;
    return (
      <p className="flex items-start gap-2 text-xs text-destructive">
        <XCircle className="mt-0.5 size-3.5 shrink-0" />
        <span>
          {message ?? "Lượt hỏi thất bại."}
          {message && turn.error_code ? (
            <span className="ml-1 font-mono text-[10px] text-muted-foreground">
              {turn.error_code}
            </span>
          ) : null}
        </span>
      </p>
    );
  }

  if (turn.status === "uncertain") {
    return (
      <p className="flex items-start gap-2 text-xs text-muted-foreground">
        <CircleHelp className="mt-0.5 size-3.5 shrink-0" />
        <span>
          Lượt hỏi bị gián đoạn trước khi hoàn tất; không có câu trả lời.
        </span>
      </p>
    );
  }

  if (turn.status === "cancelled") {
    return (
      <p className="text-xs text-muted-foreground">
        Lượt hỏi đã bị hủy, không có câu trả lời.
      </p>
    );
  }

  if (turn.source_status !== "current") {
    return (
      <p className="flex items-start gap-2 text-xs text-warning">
        <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
        <span>
          {turn.source_status_reason ??
            "Nguồn của câu trả lời không còn khả dụng."}
        </span>
      </p>
    );
  }

  if (!turn.result) {
    return (
      <p className="text-xs text-muted-foreground">
        Lượt hỏi hoàn tất nhưng không có nội dung trả lời được ghi nhận.
      </p>
    );
  }

  if (turn.result.status === "direct_reply") {
    return directReplyBody(turn.result);
  }

  return <AnswerBody result={turn.result} />;
}
