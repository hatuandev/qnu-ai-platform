import {
  CircleHelp,
  Loader2,
  Sparkles,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import type { ConversationTurn, DirectReply } from "@/api/conversations";
import { AnswerBody } from "@/components/assistants/answer-body";
import { stripDocumentMarkers } from "@/components/assistants/document-preview-pane";
import { MarkdownContent } from "@/components/knowledge/markdown-content";
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
  answer_context_budget_exceeded:
    "Bằng chứng bắt buộc vượt ngân sách ngữ cảnh của lượt hỏi; hãy hỏi cụ thể hơn theo từng mục.",
};

const DIRECT_ROUTE_TEXT: Record<DirectReply["route"], string> = {
  greeting: "Chào hỏi",
  courtesy: "Xã giao",
  identity: "Giới thiệu",
  protected_request: "Yêu cầu cần bảo vệ",
  guardrail: "Ngoài phạm vi hỗ trợ",
  direct_chat: "Hội thoại trực tiếp",
};

export function ResolvedContextNotice({
  originalQuestion,
  resolvedQuestion,
}: {
  originalQuestion: string;
  resolvedQuestion?: string | null;
}) {
  if (!resolvedQuestion) return null;
  const orig = originalQuestion.trim().toLowerCase();
  const res = resolvedQuestion.trim().toLowerCase();
  if (!res || orig === res) return null;

  return (
    <div className="flex items-center gap-2 rounded-md border border-primary/20 bg-primary/5 px-2.5 py-1 text-[11px] text-muted-foreground animate-in fade-in-50 duration-200">
      <Sparkles className="size-3 text-primary shrink-0" />
      <span className="font-medium text-foreground">Ngữ cảnh làm rõ:</span>{" "}
      <span
        className="italic text-foreground/80 truncate max-w-[500px]"
        title={resolvedQuestion}
      >
        "{resolvedQuestion}"
      </span>
    </div>
  );
}

function directReplyBody(
  reply: DirectReply,
  onPromptClick?: (prompt: string) => void,
) {
  const isSocial = reply.route === "greeting" || reply.route === "courtesy";
  const isDirectChat = reply.route === "direct_chat";
  const rawAnswer = stripDocumentMarkers(reply.answer?.trim() || "");
  const displayAnswer =
    rawAnswer && rawAnswer !== "{}"
      ? rawAnswer
      : "Tôi đã ghi nhận câu hỏi của bạn. Về nội dung này, bạn có thể diễn đạt cụ thể hơn hoặc cung cấp thêm chi tiết để mình hỗ trợ chính xác nhất nhé.";

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <Badge variant="secondary" className="h-4 px-1.5 text-[10px] font-normal">
          {isDirectChat
            ? "Hội thoại trực tiếp với mô hình AI"
            : `Trả lời trực tiếp · ${DIRECT_ROUTE_TEXT[reply.route]}`}
        </Badge>
        {isDirectChat ? (
          <div className="text-sm leading-relaxed text-foreground">
            <MarkdownContent content={displayAnswer} />
          </div>
        ) : (
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
            {displayAnswer}
          </p>
        )}
      </div>

      {isSocial && onPromptClick && (
        <div className="pt-1.5 space-y-1.5 border-t border-border/40">
          <p className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
            <Sparkles className="size-3 text-primary" />
            <span>Chủ đề nổi bật bạn có thể tra cứu ngay:</span>
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() =>
                onPromptClick(
                  "Chỉ tiêu tuyển sinh ngành Sư phạm Lịch sử - Địa lý năm 2024 và 2025 là bao nhiêu?",
                )
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/40 px-2.5 py-1 text-xs text-foreground/90 hover:bg-muted hover:border-primary/40 transition-colors cursor-pointer shadow-2xs"
            >
              <span>Chỉ tiêu tuyển sinh SP Lịch sử - Địa lý</span>
            </button>
            <button
              type="button"
              onClick={() =>
                onPromptClick(
                  "Tiêu chí chấm điểm LMS/LCMS theo Quyết định 4740 gồm những chức năng nào?",
                )
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/40 px-2.5 py-1 text-xs text-foreground/90 hover:bg-muted hover:border-primary/40 transition-colors cursor-pointer shadow-2xs"
            >
              <span>Tiêu chí LMS/LCMS (QĐ 4740)</span>
            </button>
            <button
              type="button"
              onClick={() =>
                onPromptClick(
                  "Phương thức xét tuyển bằng học bạ năm 2025 có những điều kiện gì?",
                )
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/40 px-2.5 py-1 text-xs text-foreground/90 hover:bg-muted hover:border-primary/40 transition-colors cursor-pointer shadow-2xs"
            >
              <span>Điều kiện xét tuyển học bạ 2025</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function TurnResult({
  turn,
  onSelectEvidence,
  onPromptClick,
}: {
  turn: ConversationTurn;
  onSelectEvidence?: (evidenceId: string, index: number) => void;
  onPromptClick?: (prompt: string) => void;
}) {
  if (turn.status === "running") {
    return (
      <div className="flex items-center gap-2.5 py-1 text-xs text-muted-foreground animate-pulse">
        <Loader2 className="size-3.5 animate-spin text-primary shrink-0" />
        <span>Đang phân tích câu hỏi & đối soát kho tri thức...</span>
      </div>
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

  const replyContent =
    turn.result.status === "direct_reply" ? (
      directReplyBody(turn.result, onPromptClick)
    ) : (
      <AnswerBody result={turn.result} onSelectEvidence={onSelectEvidence} />
    );

  return (
    <div className="space-y-2">
      <ResolvedContextNotice
        originalQuestion={turn.question}
        resolvedQuestion={turn.resolved_question}
      />
      {replyContent}
    </div>
  );
}
