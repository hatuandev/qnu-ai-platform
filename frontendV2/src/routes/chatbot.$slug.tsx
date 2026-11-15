import { createFileRoute } from "@tanstack/react-router";
import {
  BookOpen,
  Bot,
  Loader2,
  RotateCcw,
  Send,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiProblemError } from "@/api/client";
import {
  type PublicChatSession,
  type PublicCitation,
  useCreatePublicChatSessionMutation,
  usePublicChatbotInfoQuery,
  useSendPublicTurnMutation,
} from "@/api/publications";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

export const Route = createFileRoute("/chatbot/$slug")({
  validateSearch: (
    search: Record<string, unknown>,
  ): { embed?: boolean; q?: string } => {
    // The router JSON-parses search values, so "?embed=1" arrives as number 1.
    const value = search.embed;
    const question = typeof search.q === "string" ? search.q.trim() : "";
    return {
      embed:
        value === true || value === 1 || value === "1" || value === "true"
          ? true
          : undefined,
      q: question ? question.slice(0, 1000) : undefined,
    };
  },
  component: PublicChatbotPage,
});

type PublicMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: PublicCitation[];
  tone?: "normal" | "insufficient" | "error";
};

function newMessageId(): string {
  return crypto.randomUUID();
}

function turnErrorMessage(err: unknown): string {
  if (err instanceof ApiProblemError) {
    if (err.code === "public_chat_session_expired") {
      return "Phiên trò chuyện đã hết hạn. Hãy gửi lại câu hỏi để mở phiên mới.";
    }
    if (err.code === "public_chat_session_limit") {
      return "Bạn đã dùng hết số lượt hỏi của phiên này. Bấm Phiên mới để bắt đầu lại.";
    }
    if (err.code === "public_chat_rate_limited") {
      return "Bạn thao tác hơi nhanh. Vui lòng đợi ít phút rồi thử lại.";
    }
    if (err.code === "public_chat_budget_exhausted") {
      return "Trợ lý đã chạm giới hạn phục vụ trong ngày. Vui lòng quay lại sau.";
    }
    if (err.code === "public_chatbot_unavailable") {
      return "Trợ lý đang tạm ngưng phục vụ. Vui lòng quay lại sau.";
    }
    if (err.status === 0) {
      return "Không kết nối được máy chủ. Vui lòng kiểm tra mạng và thử lại.";
    }
    if (err.status >= 500) {
      return "Trợ lý gặp sự cố khi tạo câu trả lời. Vui lòng thử lại sau ít phút.";
    }
    return err.message;
  }
  return "Không gửi được câu hỏi. Vui lòng thử lại.";
}

function isRetryable(err: unknown): boolean {
  return (
    err instanceof ApiProblemError && (err.status === 0 || err.status >= 500)
  );
}

function CitationChips({ citations }: { citations: PublicCitation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {citations.map((citation) => (
        <Badge
          key={`citation-${citation.index}-${citation.title}`}
          variant="secondary"
          className="h-auto max-w-full items-start gap-1 px-1.5 py-0.5 text-[10px] font-normal"
        >
          <BookOpen className="mt-0.5 size-3 shrink-0" />
          <span className="break-words">
            [{citation.index}] {citation.title}
            {citation.page !== null ? ` · tr. ${citation.page}` : ""}
          </span>
        </Badge>
      ))}
    </div>
  );
}

function MessageBubble({ message }: { message: PublicMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg rounded-br-sm bg-primary px-3.5 py-2.5 text-sm leading-relaxed text-primary-foreground">
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
      </div>
    );
  }

  if (message.tone === "error") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3.5 py-2.5 text-xs leading-relaxed text-destructive">
        <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
        <p className="whitespace-pre-wrap">{message.text}</p>
      </div>
    );
  }

  return (
    <div className="max-w-[92%] space-y-1.5">
      <div className="rounded-lg rounded-bl-sm border border-border/60 bg-card px-3.5 py-2.5 shadow-2xs">
        <p
          className={
            message.tone === "insufficient"
              ? "whitespace-pre-wrap text-sm italic leading-relaxed text-muted-foreground"
              : "whitespace-pre-wrap text-sm leading-relaxed text-foreground"
          }
        >
          {message.text}
        </p>
        {message.citations ? (
          <CitationChips citations={message.citations} />
        ) : null}
      </div>
    </div>
  );
}

function PublicChatbotPage() {
  const { slug } = Route.useParams();
  const { embed = false, q } = Route.useSearch();
  const navigate = Route.useNavigate();
  const infoQuery = usePublicChatbotInfoQuery(slug);
  const createSessionMutation = useCreatePublicChatSessionMutation(slug);
  const sendTurnMutation = useSendPublicTurnMutation(slug);

  const [messages, setMessages] = useState<PublicMessage[]>([]);
  const [session, setSession] = useState<PublicChatSession | null>(null);
  const [turnsRemaining, setTurnsRemaining] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [blockedReason, setBlockedReason] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  // Synchronous lock: isSending state updates a render late, so two rapid sends
  // (double-click, Enter, prefill + click) could both pass canAsk before re-render.
  const isSendingRef = useRef(false);
  const hasSentInitialQuestion = useRef(false);

  const info = infoQuery.data;

  useEffect(() => {
    if (info?.display_name) {
      document.title = `${info.display_name} · Trợ lý công khai`;
    }
    return () => {
      document.title = "QNU AI Platform";
    };
  }, [info?.display_name]);

  const remaining = useMemo(
    () => turnsRemaining ?? info?.max_turns_per_session ?? null,
    [turnsRemaining, info?.max_turns_per_session],
  );

  const canAsk =
    Boolean(info?.available) && !blockedReason && !isSending && remaining !== 0;

  const handleResetSession = () => {
    setMessages([]);
    setSession(null);
    setTurnsRemaining(null);
    setBlockedReason(null);
    setDraft("");
    void infoQuery.refetch();
  };

  const handleSend = async (raw: string) => {
    const question = raw.trim();
    if (!question || !canAsk || isSendingRef.current) return;
    isSendingRef.current = true;
    setDraft("");
    setMessages((prev) => [
      ...prev,
      { id: newMessageId(), role: "user", text: question },
    ]);
    setIsSending(true);
    try {
      let activeSession = session;
      if (!activeSession) {
        activeSession = await createSessionMutation.mutateAsync();
        setSession(activeSession);
        setTurnsRemaining(activeSession.turns_remaining);
      }
      const reply = await sendTurnMutation.mutateAsync({
        session_id: activeSession.session_id,
        question,
      });
      setTurnsRemaining(reply.turns_remaining);
      setMessages((prev) => [
        ...prev,
        {
          id: newMessageId(),
          role: "assistant",
          text: reply.answer ?? reply.message ?? "Trợ lý chưa có câu trả lời.",
          citations: reply.citations,
          tone:
            reply.status === "insufficient_evidence"
              ? "insufficient"
              : "normal",
        },
      ]);
    } catch (err: unknown) {
      if (
        err instanceof ApiProblemError &&
        err.code === "public_chat_session_expired"
      ) {
        setSession(null);
        setTurnsRemaining(null);
      }
      if (
        err instanceof ApiProblemError &&
        (err.code === "public_chat_budget_exhausted" ||
          err.code === "public_chatbot_unavailable")
      ) {
        setBlockedReason(turnErrorMessage(err));
        void infoQuery.refetch();
      }
      if (isRetryable(err)) {
        // Put the question back so the visitor can resend with one click.
        setDraft(question);
      }
      setMessages((prev) => [
        ...prev,
        {
          id: newMessageId(),
          role: "assistant",
          tone: "error",
          text: turnErrorMessage(err),
        },
      ]);
    } finally {
      isSendingRef.current = false;
      setIsSending(false);
    }
  };

  // Keep the prefill effect independent of handleSend's per-render identity.
  const sendMessageRef = useRef(handleSend);
  useEffect(() => {
    sendMessageRef.current = handleSend;
  });

  useEffect(() => {
    if (!q || hasSentInitialQuestion.current || !info?.available) return;
    hasSentInitialQuestion.current = true;
    void sendMessageRef.current(q);
    // Drop the question from the URL so reloading the page starts clean.
    void navigate({
      to: "/chatbot/$slug",
      params: { slug },
      search: { embed },
      replace: true,
    });
  }, [q, info?.available, navigate, slug, embed]);

  if (infoQuery.isLoading) {
    return (
      <div
        className={
          embed
            ? "mx-auto flex h-dvh w-full max-w-3xl flex-col gap-3 p-3"
            : "mx-auto flex min-h-dvh w-full max-w-3xl flex-col gap-4 p-4 sm:p-6"
        }
      >
        <Skeleton className="h-14 w-full rounded-lg" />
        <Skeleton className="h-40 w-full rounded-lg" />
        <Skeleton className="h-24 w-full rounded-lg" />
      </div>
    );
  }

  if (infoQuery.isError || !info) {
    const isGone =
      infoQuery.error instanceof ApiProblemError &&
      infoQuery.error.kind === "not_found";
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-xl flex-col items-center justify-center gap-4 p-6">
        <div className="flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
          <Bot className="size-6" />
        </div>
        <div className="space-y-1 text-center">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">
            {isGone
              ? "Liên kết không còn hoạt động"
              : "Không tải được trợ lý công khai"}
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
            {isGone
              ? "Trợ lý đã tắt chế độ công khai hoặc đường dẫn không đúng. Vui lòng liên hệ đơn vị đã chia sẻ liên kết này."
              : "Kết nối tới máy chủ không thành công. Vui lòng kiểm tra mạng và thử lại."}
          </p>
        </div>
        {!isGone ? (
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => void infoQuery.refetch()}
          >
            Thử lại
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className={
        embed
          ? "mx-auto flex h-dvh w-full max-w-3xl flex-col p-3 sm:p-4"
          : "mx-auto flex min-h-dvh w-full max-w-3xl flex-col p-4 sm:p-6"
      }
    >
      <header
        className={
          embed
            ? "flex items-center gap-2.5 pb-3"
            : "flex items-center gap-3 pb-4"
        }
      >
        <div
          className={
            embed
              ? "flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
              : "flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"
          }
        >
          <Bot className={embed ? "size-4" : "size-5"} />
        </div>
        <div className="min-w-0">
          <h1
            className={
              embed
                ? "truncate text-sm font-semibold tracking-tight text-foreground"
                : "truncate text-base font-semibold tracking-tight text-foreground"
            }
          >
            {info.display_name}
          </h1>
          <p className="text-[11px] text-muted-foreground">
            {embed
              ? "Trợ lý công khai · Không cần đăng nhập"
              : "Trợ lý công khai · Đại học Quy Nhơn · Không cần đăng nhập"}
          </p>
        </div>
      </header>

      {!info.available ? (
        <Alert variant="warning" className="mb-4">
          <AlertTitle>Trợ lý đang tạm ngưng phục vụ</AlertTitle>
          <AlertDescription>
            {info.unavailable_reason ??
              "Đơn vị đang cập nhật nội dung. Vui lòng quay lại sau."}
          </AlertDescription>
        </Alert>
      ) : null}

      {blockedReason ? (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Trợ lý tạm ngưng nhận câu hỏi</AlertTitle>
          <AlertDescription>{blockedReason}</AlertDescription>
        </Alert>
      ) : null}

      <div
        className={
          embed
            ? "min-h-0 flex-1 space-y-3 overflow-y-auto pb-3"
            : "flex-1 space-y-4 pb-4"
        }
        role="log"
        aria-live="polite"
        aria-label="Hội thoại"
      >
        {messages.length === 0 ? (
          <Card className="border-border/60 shadow-2xs">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">
                Bắt đầu trò chuyện
              </CardTitle>
              <CardDescription>
                {info.welcome_message ||
                  "Đặt câu hỏi về thông tin do đơn vị cung cấp; câu trả lời luôn kèm nguồn tham chiếu."}
              </CardDescription>
            </CardHeader>
            {info.available && info.starter_prompts.length > 0 ? (
              <CardContent className="space-y-2">
                {info.starter_prompts.map((prompt) => (
                  <Button
                    key={prompt}
                    variant="outline"
                    size="sm"
                    className="h-auto w-full justify-start whitespace-normal px-3 py-2 text-left text-xs font-normal leading-relaxed"
                    disabled={!canAsk}
                    onClick={() => void handleSend(prompt)}
                  >
                    {prompt}
                  </Button>
                ))}
              </CardContent>
            ) : null}
          </Card>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
        {isSending ? (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            <span>Trợ lý đang soạn câu trả lời.</span>
          </p>
        ) : null}
      </div>

      <div
        className={
          embed
            ? "border-t border-border/60 bg-background pt-2.5"
            : "sticky bottom-0 border-t border-border/60 bg-background/95 pb-1 pt-3 backdrop-blur"
        }
      >
        <Textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void handleSend(draft);
            }
          }}
          maxLength={1000}
          rows={2}
          placeholder={
            info.available
              ? "Nhập câu hỏi của bạn... (Enter để gửi, Shift+Enter xuống dòng)"
              : "Trợ lý đang tạm ngưng phục vụ."
          }
          className="resize-none bg-background text-sm leading-relaxed"
          disabled={!canAsk}
          aria-label="Câu hỏi của bạn"
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[11px] text-muted-foreground">
            {remaining !== null && info.available
              ? `Còn ${remaining}/${info.max_turns_per_session} lượt trong phiên này`
              : "Hội thoại chỉ lưu trong phiên trình duyệt của bạn"}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              disabled={isSending}
              onClick={handleResetSession}
            >
              <RotateCcw className="size-3.5" />
              <span>Phiên mới</span>
            </Button>
            <Button
              size="sm"
              className="h-8 gap-1.5 text-xs"
              disabled={!canAsk || !draft.trim()}
              onClick={() => void handleSend(draft)}
            >
              {isSending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Send className="size-3.5" />
              )}
              <span>Gửi</span>
            </Button>
          </div>
        </div>
        {embed ? null : (
          <p className="mt-1 text-[11px] text-muted-foreground">
            Câu trả lời dựa trên kho tri thức đã xuất bản của đơn vị; khi thiếu
            căn cứ, trợ lý sẽ nói rõ thay vì suy đoán.
          </p>
        )}
      </div>
    </div>
  );
}
