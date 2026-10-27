import {
  AlertCircle,
  AlertTriangle,
  Ban,
  Bot,
  Clock,
  ExternalLink,
  Info,
  Loader2,
  RefreshCw,
  SlidersHorizontal,
  User,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  describeAnswerReason,
  describeMetadataFilter,
  hasMetadataFilter,
  type VerificationFinding,
} from "@/features/rag/types";
import {
  formatUsage,
  VerificationPanel,
} from "@/features/rag/verification-panel";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { formatConversationError } from "./schemas";
import type { Statement, TurnResponse } from "./types";

export function ChatMessageItem({
  turn,
  onOpenCitation,
  onRetry,
}: {
  turn: TurnResponse;
  onOpenCitation: (statement: Statement, turn: TurnResponse) => void;
  onRetry?: (turn: TurnResponse) => void;
}) {
  const isRunning = turn.status === "running";
  const isFailed = turn.status === "failed";
  const isUncertain = turn.status === "uncertain";
  const isCompleted = turn.status === "completed";
  // Terminal, not an error: the turn was stopped on purpose (assistant stop or
  // conversation archived) and keeps its idempotency key.
  const isCancelled = turn.status === "cancelled";
  const isUnavailable =
    turn.source_status === "unavailable" || turn.result === null;

  const result = turn.result;
  const trace = result?.trace;
  const verification = trace?.verification;
  const scope = turn.metadata_filter;

  // Enforce mode blocks an answer the judge did not confirm. That is a
  // verification outcome with its own cause, not a connection failure.
  const verificationBlocked =
    result?.status === "insufficient_evidence" &&
    (result.reason === "answer_not_supported" ||
      result.reason === "answer_verification_uncertain");

  const openEvidenceById = (evidenceId: string) => {
    if (!result) return;
    const statement =
      result.statements.find((item) =>
        item.evidence_ids.includes(evidenceId),
      ) ?? result.statements[0];
    const source = result.sources.find(
      (item) => item.evidence_id === evidenceId,
    );
    if (statement) {
      onOpenCitation(statement, turn);
    } else if (source) {
      // Enforce-blocked turns have no statements; still let the reader open the
      // report's evidence through the citation drawer.
      onOpenCitation({ text: "", evidence_ids: [source.evidence_id] }, turn);
    }
  };

  return (
    <div className="space-y-4 py-4 border-b last:border-b-0">
      {/* 1. User Message Row */}
      <div className="flex gap-3 justify-end items-start pl-8 sm:pl-16">
        <div className="flex flex-col items-end gap-1.5 max-w-[85%] sm:max-w-[75%]">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="font-mono font-medium">#{turn.turn_no}</span>
            <span>•</span>
            <Clock className="size-3" />
            <span>{formatDateTimeValue(turn.created_at)}</span>
          </div>

          <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-primary-foreground text-sm shadow-xs whitespace-pre-wrap break-words leading-relaxed">
            {turn.question}
          </div>

          {turn.resolved_question &&
            turn.resolved_question !== turn.question && (
              <p className="text-[11px] text-muted-foreground italic flex items-center gap-1">
                <Info className="size-3 shrink-0" />
                Làm rõ: {turn.resolved_question}
              </p>
            )}

          {hasMetadataFilter(scope) ? (
            <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <SlidersHorizontal className="size-3 shrink-0" />
              Phạm vi metadata: {describeMetadataFilter(scope)}
            </p>
          ) : null}
        </div>

        <div className="size-8 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
          <User className="size-4" />
        </div>
      </div>

      {/* 2. Assistant Message Row */}
      <div className="flex gap-3 justify-start items-start pr-8 sm:pr-16">
        <div className="size-8 rounded-full bg-primary/15 text-primary flex items-center justify-center shrink-0 mt-0.5 border border-primary/20">
          <Bot className="size-4" />
        </div>

        <div className="flex flex-col items-start gap-2 max-w-[90%] sm:max-w-[85%] w-full">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="font-semibold text-foreground">Trợ lý AI</span>
            {turn.finished_at && (
              <>
                <span>•</span>
                <span>{formatDateTimeValue(turn.finished_at)}</span>
              </>
            )}
          </div>

          {/* Running State: Honest spinner, NO fake typing */}
          {isRunning && (
            <div className="flex items-center gap-2.5 p-4 rounded-xl border bg-muted/20 text-xs text-muted-foreground animate-pulse">
              <Loader2 className="size-4 animate-spin text-primary" />
              <span>
                Trợ lý đang tìm kiếm tài liệu và tổng hợp câu trả lời...
              </span>
            </div>
          )}

          {/* Cancelled State: terminal, no answer body, no resend suggestion */}
          {isCancelled && (
            <Alert className="border-border bg-muted/30 text-foreground py-3">
              <Ban className="size-4 text-muted-foreground" />
              <div className="space-y-1">
                <AlertDescription className="text-xs">
                  {turn.error_code === "operation_cancelled"
                    ? "Lượt hỏi đã bị hủy trước khi trợ lý trả lời xong (do dừng trợ lý hoặc hội thoại được lưu trữ)."
                    : formatConversationError(
                        turn.error_code,
                        "Lượt hỏi đã bị hủy trước khi hoàn tất.",
                      )}
                </AlertDescription>
                <p className="text-[11px] text-muted-foreground">
                  Không có câu trả lời nào được ghi nhận cho lượt này. Lượt này
                  giữ nguyên khóa idempotency nên không gửi lại như một yêu cầu
                  mới; hãy đặt câu hỏi mới nếu vẫn cần.
                </p>
              </div>
            </Alert>
          )}

          {/* Failed State */}
          {isFailed && (
            <Alert variant="destructive" className="py-3">
              <AlertCircle className="size-4" />
              <div className="space-y-2">
                <AlertDescription className="text-xs">
                  {formatConversationError(
                    turn.error_code,
                    "Không thể tạo câu trả lời cho lượt hỏi này.",
                  )}
                </AlertDescription>
                {onRetry && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs gap-1.5"
                    onClick={() => onRetry(turn)}
                  >
                    <RefreshCw className="size-3" />
                    Thử lại với cùng khóa
                  </Button>
                )}
              </div>
            </Alert>
          )}

          {/* Uncertain State */}
          {isUncertain && (
            <Alert className="border-warning/50 bg-warning/10 text-foreground py-3">
              <AlertTriangle className="size-4 text-warning" />
              <AlertDescription className="text-xs">
                Lượt hỏi chưa thể xác định kết quả (quá thời hạn xử lý lease).
                Vui lòng kiểm tra lại trước khi gửi câu hỏi tiếp theo.
              </AlertDescription>
            </Alert>
          )}

          {/* Completed State */}
          {isCompleted &&
            (isUnavailable ? (
              <Alert variant="destructive" className="py-3">
                <AlertCircle className="size-4" />
                <AlertDescription className="text-xs">
                  Nguồn tài liệu chứng minh cho lượt hỏi này đã thay đổi hoặc
                  không còn khả dụng. Câu trả lời cũ không còn hiệu lực.
                </AlertDescription>
              </Alert>
            ) : result?.status === "insufficient_evidence" ? (
              <div className="w-full space-y-2">
                <div
                  className={cn(
                    "rounded-xl border p-4 space-y-2",
                    verificationBlocked
                      ? "border-warning/40 bg-warning/5"
                      : "border-warning/40 bg-warning/5",
                  )}
                >
                  <div className="flex items-center gap-2 text-warning text-xs font-semibold">
                    <AlertTriangle className="size-4 shrink-0" />
                    <span>
                      {verificationBlocked
                        ? "Câu trả lời không được phát hành"
                        : "Không đủ bằng chứng để trả lời"}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {describeAnswerReason(result.reason)}
                  </p>
                </div>

                <VerificationPanel
                  trace={verification}
                  onOpenEvidence={openEvidenceById}
                />

                {/* Sources stay available so the reader can compare even when
                    no answer was released. */}
                {result.sources.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-[11px] gap-1"
                    onClick={() =>
                      onOpenCitation(
                        result.statements[0] ?? {
                          text: "",
                          evidence_ids: [result.sources[0].evidence_id],
                        },
                        turn,
                      )
                    }
                  >
                    <ExternalLink className="size-3" />
                    Đối chiếu nguồn ({result.sources.length})
                  </Button>
                )}
              </div>
            ) : result?.status === "answered" &&
              result.statements.length > 0 ? (
              <div className="w-full space-y-2">
                <div className="rounded-xl border bg-card p-4 text-sm text-foreground shadow-2xs space-y-3 w-full">
                  {/* Statements with inline citations */}
                  <div className="space-y-2.5 leading-relaxed">
                    {result.statements.map((statement) => (
                      <div
                        key={`${turn.id}_stmt_${statement.evidence_ids.join("-")}`}
                        className="flex flex-wrap items-baseline gap-1.5"
                      >
                        <span className="text-foreground">
                          {statement.text}
                        </span>
                        <span className="inline-flex items-center gap-1 shrink-0">
                          {statement.evidence_ids.map((evId) => (
                            <button
                              key={evId}
                              type="button"
                              onClick={() => onOpenCitation(statement, turn)}
                              className={cn(
                                "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-mono font-medium",
                                "bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground",
                                "transition-colors cursor-pointer border border-primary/20",
                              )}
                              title={`Xem dẫn nguồn cho ${evId}`}
                            >
                              <span>{evId}</span>
                              <ExternalLink className="size-2.5" />
                            </button>
                          ))}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Summary / Trace footer */}
                  {trace && (
                    <div className="border-t pt-2.5 mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground font-mono">
                      <div className="flex items-center gap-2">
                        {trace.model_name && (
                          <Badge
                            variant="outline"
                            className="text-[10px] font-normal"
                          >
                            {trace.model_name}
                          </Badge>
                        )}
                        {/* Generation usage only; the judge reports its own. */}
                        <span title="Token của bước sinh câu trả lời, không phải tổng toàn pipeline">
                          Token sinh: {formatUsage(trace.total_tokens)}
                        </span>
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-[11px] text-primary gap-1 px-2"
                        onClick={() =>
                          onOpenCitation(result.statements[0], turn)
                        }
                      >
                        Xem tất cả nguồn ({result.sources.length})
                      </Button>
                    </div>
                  )}
                </div>

                <VerificationPanel
                  trace={verification}
                  onOpenEvidence={openEvidenceById}
                />
              </div>
            ) : (
              <div className="rounded-xl border bg-card p-4 text-sm text-muted-foreground">
                {result?.answer || "(Không có nội dung phản hồi)"}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

/** Re-exported for tests that assert the judge report shape. */
export type { VerificationFinding };
