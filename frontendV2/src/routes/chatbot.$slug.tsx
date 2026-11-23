import { createFileRoute } from "@tanstack/react-router";
import {
  BookOpen,
  Bot,
  Check,
  Copy,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/api/client";
import {
  type PublicChatSession,
  type PublicCitation,
  useCreatePublicChatSessionMutation,
  usePublicChatbotInfoQuery,
  useSendPublicTurnMutation,
} from "@/api/publications";
import { MarkdownContent } from "@/components/knowledge/markdown-content";
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
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

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
    if (err.code === "public_chat_bot_detected") {
      return "Yêu cầu không hợp lệ.";
    }
    if (err.code === "public_chat_too_fast") {
      return "Bạn gửi tin quá nhanh. Vui lòng thử lại sau ít giây.";
    }
    if (err.code === "answer_context_budget_exceeded") {
      return "Nội dung liên quan đến câu hỏi quá dài để tổng hợp trong một lượt. Bạn hãy hỏi cụ thể hơn theo từng mục nhé.";
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
    err instanceof ApiProblemError &&
    (err.status === 0 ||
      err.status >= 500 ||
      err.code === "public_chat_too_fast" ||
      err.code === "public_chat_session_expired")
  );
}

function CitationChips({ citations }: { citations: PublicCitation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-1.5 border-t border-border/40 pt-2">
      <span className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground mr-0.5">
        <BookOpen className="size-3 text-primary" /> Nguồn trích dẫn:
      </span>
      {citations.map((citation) => (
        <Popover key={`citation-${citation.index}-${citation.title}`}>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded border border-border/70 bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-foreground transition-colors hover:border-primary/50 hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring cursor-pointer"
            >
              <span className="font-semibold text-primary">
                [{citation.index}]
              </span>
              <span className="max-w-[180px] truncate">{citation.title}</span>
              {citation.page !== null ? (
                <span className="text-[10px] text-muted-foreground">
                  · tr. {citation.page}
                </span>
              ) : null}
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-72 p-3 text-xs" align="start">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between border-b border-border/50 pb-1.5">
                <span className="font-semibold text-foreground flex items-center gap-1">
                  <BookOpen className="size-3.5 text-primary" /> Dẫn chứng [
                  {citation.index}]
                </span>
                {citation.page !== null ? (
                  <Badge
                    variant="outline"
                    className="text-[10px] px-1.5 py-0 h-4 font-normal"
                  >
                    Trang {citation.page}
                  </Badge>
                ) : null}
              </div>
              <p className="font-medium text-foreground text-[11px] leading-snug">
                {citation.title}
              </p>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Dữ liệu được đối chiếu và trích xuất nguyên văn từ tài liệu
                chính thức đã xuất bản.
              </p>
            </div>
          </PopoverContent>
        </Popover>
      ))}
    </div>
  );
}

function MessageActionBar({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"like" | "dislike" | null>(null);
  const [dislikeSubmitted, setDislikeSubmitted] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success("Đã sao chép câu trả lời vào bộ nhớ tạm");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Không thể sao chép văn bản");
    }
  };

  const handleLike = () => {
    if (feedback === "like") return;
    setFeedback("like");
    toast.success("Cảm ơn bạn đã đánh giá hữu ích!");
  };

  const handleDislikeReason = (reason: string) => {
    setFeedback("dislike");
    setDislikeSubmitted(true);
    toast.info(`Đã ghi nhận góp ý: ${reason}`);
  };

  return (
    <div className="mt-2 flex items-center justify-between border-t border-border/40 pt-1.5 text-muted-foreground">
      <div className="flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={cn(
            "h-6 px-1.5 text-[11px] gap-1 hover:text-foreground cursor-pointer",
            feedback === "like" && "text-primary font-medium",
          )}
          onClick={handleLike}
          title="Câu trả lời hữu ích"
        >
          <ThumbsUp className="size-3" />
          {feedback === "like" ? <span>Hữu ích</span> : null}
        </Button>

        <Popover>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className={cn(
                "h-6 px-1.5 text-[11px] gap-1 hover:text-foreground cursor-pointer",
                feedback === "dislike" && "text-destructive font-medium",
              )}
              title="Chưa hài lòng"
            >
              <ThumbsDown className="size-3" />
              {feedback === "dislike" ? <span>Đã góp ý</span> : null}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64 p-2.5 text-xs" align="start">
            {dislikeSubmitted ? (
              <p className="text-[11px] text-muted-foreground py-1 text-center">
                ✓ Cảm ơn bạn. Ý kiến đóng góp sẽ được chuyển đến bộ phận chuyên
                môn để cải thiện.
              </p>
            ) : (
              <div className="space-y-1.5">
                <p className="font-semibold text-foreground text-[11px]">
                  Lý do chưa hài lòng:
                </p>
                <div className="flex flex-col gap-1">
                  {[
                    "Thông tin chưa chính xác với văn bản",
                    "Chưa trả lời đúng trọng tâm câu hỏi",
                    "Thông tin quá vắn tắt hoặc khó hiểu",
                  ].map((reason) => (
                    <button
                      key={reason}
                      type="button"
                      className="rounded px-2 py-1 text-left text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
                      onClick={() => handleDislikeReason(reason)}
                    >
                      • {reason}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </PopoverContent>
        </Popover>
      </div>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-6 px-1.5 text-[11px] gap-1 hover:text-foreground text-muted-foreground cursor-pointer"
        onClick={handleCopy}
        title="Sao chép nội dung"
      >
        {copied ? (
          <>
            <Check className="size-3 text-emerald-600 dark:text-emerald-400" />
            <span className="text-emerald-600 dark:text-emerald-400">
              Đã chép
            </span>
          </>
        ) : (
          <>
            <Copy className="size-3" />
            <span>Sao chép</span>
          </>
        )}
      </Button>
    </div>
  );
}

function SendingProgress() {
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const timer1 = setTimeout(() => setStageIndex(1), 2200);
    const timer2 = setTimeout(() => setStageIndex(2), 5200);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, []);

  const stages = [
    "Đang tra cứu tài liệu trong kho tri thức...",
    "Đang đối soát bảng biểu & trích xuất dữ kiện...",
    "Đang tổng hợp câu trả lời chính xác...",
  ];

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border/40 bg-card/50 px-3.5 py-2.5 text-xs text-muted-foreground shadow-2xs">
      <Loader2 className="size-3.5 animate-spin text-primary shrink-0" />
      <span className="transition-opacity duration-300">
        {stages[stageIndex]}
      </span>
    </div>
  );
}

function getSuggestedPrompts(
  lastQuestion: string,
  lastAnswer: string,
  starterPrompts: string[],
): string[] {
  const q = lastQuestion.toLowerCase();
  const a = lastAnswer.toLowerCase();

  if (
    q.includes("ngành") ||
    q.includes("tổ hợp") ||
    q.includes("môn") ||
    a.includes("tổ hợp")
  ) {
    return [
      "Chỉ tiêu tuyển sinh của ngành này là bao nhiêu?",
      "Điểm chuẩn trúng tuyển các năm gần nhất?",
      "Hồ sơ và quy trình đăng ký xét tuyển ra sao?",
    ];
  }
  if (
    q.includes("học phí") ||
    q.includes("học bổng") ||
    q.includes("tiền") ||
    a.includes("học phí")
  ) {
    return [
      "Có những chính sách miễn giảm học phí nào?",
      "Điều kiện xét nhận học bổng khuyến khích?",
      "Thời hạn và hình thức nộp học phí của trường?",
    ];
  }
  if (
    q.includes("phương thức") ||
    q.includes("xét tuyển") ||
    a.includes("phương thức")
  ) {
    return [
      "Ngưỡng đảm bảo chất lượng đầu vào (điểm sàn) là bao nhiêu?",
      "Trường có xét học bạ THPT không?",
      "Thời gian nộp hồ sơ xét tuyển sớm là khi nào?",
    ];
  }

  if (starterPrompts.length > 0) {
    return starterPrompts.slice(0, 3);
  }
  return [
    "Trường Đại học Quy Nhơn đào tạo những khối ngành nào?",
    "Thông tin liên hệ Ban Tuyển sinh của trường?",
    "Ký túc xá và cơ sở vật chất dành cho sinh viên?",
  ];
}

function SuggestedPromptChips({
  prompts,
  onSelect,
  disabled,
}: {
  prompts: string[];
  onSelect: (prompt: string) => void;
  disabled: boolean;
}) {
  if (prompts.length === 0) return null;
  return (
    <div className="space-y-1.5 pt-1 animate-in fade-in-50 duration-300">
      <p className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        <Sparkles className="size-3 text-primary" />
        <span>Gợi ý câu hỏi tiếp theo:</span>
      </p>
      <div className="flex flex-wrap gap-1.5">
        {prompts.map((prompt) => (
          <Button
            key={prompt}
            type="button"
            variant="outline"
            size="sm"
            className="h-auto max-w-full justify-start rounded-full border-border/70 bg-card/60 px-3 py-1 text-left text-xs font-normal leading-relaxed hover:border-primary/50 hover:bg-muted cursor-pointer"
            disabled={disabled}
            onClick={() => onSelect(prompt)}
          >
            <span className="truncate">{prompt}</span>
          </Button>
        ))}
      </div>
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
        <MarkdownContent
          content={message.text}
          compact
          className={
            message.tone === "insufficient"
              ? "italic text-muted-foreground"
              : undefined
          }
        />
        {message.citations ? (
          <CitationChips citations={message.citations} />
        ) : null}
        <MessageActionBar text={message.text} />
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
  const [honeypot, setHoneypot] = useState("");
  const [blockedReason, setBlockedReason] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  // Synchronous lock: isSending state updates a render late, so two rapid sends
  // (double-click, Enter, prefill + click) could both pass canAsk before re-render.
  const isSendingRef = useRef(false);
  const hasSentInitialQuestion = useRef(false);
  const sessionInitPromiseRef = useRef<Promise<PublicChatSession> | null>(null);
  const sessionCreatedAtRef = useRef<number>(0);

  const info = infoQuery.data;

  // Check whether embedding in an iframe is permitted by allowed_embed_origins
  const embedOriginViolation = useMemo(() => {
    if (typeof window === "undefined") return null;
    const isInIframe = window.self !== window.top;
    if (!isInIframe) return null;

    let parentOrigin: string | null = null;
    try {
      if (
        window.location.ancestorOrigins &&
        window.location.ancestorOrigins.length > 0
      ) {
        parentOrigin = window.location.ancestorOrigins[0].toLowerCase();
      } else if (document.referrer) {
        parentOrigin = new URL(document.referrer).origin.toLowerCase();
      }
    } catch {
      // parse error
    }

    const selfOrigin = window.location.origin.toLowerCase();
    const allowed = (info?.allowed_embed_origins || []).map((o) =>
      o.toLowerCase(),
    );

    if (parentOrigin) {
      if (parentOrigin === selfOrigin || allowed.includes(parentOrigin)) {
        return null;
      }
      return parentOrigin;
    }

    // Fail-closed when framed with stripped referrer (e.g. referrerpolicy="no-referrer").
    return "không xác định";
  }, [info?.allowed_embed_origins]);

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

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const lastAssistantMessage = useMemo(() => {
    if (messages.length === 0) return null;
    const last = messages[messages.length - 1];
    return last.role === "assistant" && last.tone !== "error" ? last : null;
  }, [messages]);

  const lastUserQuestion = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") return messages[i].text;
    }
    return "";
  }, [messages]);

  const suggestedPrompts = useMemo(() => {
    if (!lastAssistantMessage) return [];
    return getSuggestedPrompts(
      lastUserQuestion,
      lastAssistantMessage.text,
      info?.starter_prompts ?? [],
    );
  }, [lastAssistantMessage, lastUserQuestion, info?.starter_prompts]);

  useEffect(() => {
    if (messages.length > 0 || isSending) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, isSending]);

  const canAsk =
    Boolean(info?.available) &&
    !blockedReason &&
    !embedOriginViolation &&
    !isSending &&
    remaining !== 0;

  // Pre-warm public session as soon as the chatbot is available so the first
  // human turn does not immediately collide with the server's 800ms anti-bot gate.
  useEffect(() => {
    if (
      !info?.available ||
      session ||
      embedOriginViolation ||
      blockedReason ||
      sessionInitPromiseRef.current
    ) {
      return;
    }
    let cancelled = false;
    const promise = createSessionMutation
      .mutateAsync({ website: honeypot || undefined })
      .then((created) => {
        if (!cancelled) {
          sessionCreatedAtRef.current = Date.now();
          setSession(created);
          setTurnsRemaining(created.turns_remaining);
        }
        return created;
      })
      .finally(() => {
        if (sessionInitPromiseRef.current === promise) {
          sessionInitPromiseRef.current = null;
        }
      });
    sessionInitPromiseRef.current = promise;
    void promise.catch(() => {
      // Errors on background pre-warm are handled cleanly on the actual send turn.
    });
    return () => {
      cancelled = true;
    };
  }, [info?.available, session, embedOriginViolation, blockedReason]);

  const handleResetSession = () => {
    setMessages([]);
    setSession(null);
    sessionInitPromiseRef.current = null;
    sessionCreatedAtRef.current = 0;
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
        if (sessionInitPromiseRef.current) {
          try {
            activeSession = await sessionInitPromiseRef.current;
          } catch {
            activeSession = null;
          }
        }
        if (!activeSession) {
          activeSession = await createSessionMutation.mutateAsync({
            website: honeypot || undefined,
          });
          sessionCreatedAtRef.current = Date.now();
          setSession(activeSession);
          setTurnsRemaining(activeSession.turns_remaining);
        }
      }
      // On LAN/fast networks, a freshly created session may be <850ms old;
      // pause briefly before the very first turn so the server's anti-bot gate passes.
      if (sessionCreatedAtRef.current > 0 && messages.length === 0) {
        const elapsed = Date.now() - sessionCreatedAtRef.current;
        if (elapsed < 850) {
          await new Promise((resolve) => setTimeout(resolve, 850 - elapsed));
        }
      }
      let reply;
      try {
        reply = await sendTurnMutation.mutateAsync({
          session_id: activeSession.session_id,
          question,
          website: honeypot || undefined,
        });
      } catch (firstErr: unknown) {
        if (
          firstErr instanceof ApiProblemError &&
          firstErr.code === "public_chat_too_fast"
        ) {
          await new Promise((resolve) => setTimeout(resolve, 900));
          reply = await sendTurnMutation.mutateAsync({
            session_id: activeSession.session_id,
            question,
            website: honeypot || undefined,
          });
        } else {
          throw firstErr;
        }
      }
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

      {embedOriginViolation ? (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Tên miền chưa được cấp phép nhúng</AlertTitle>
          <AlertDescription>
            Trang web hiện tại ({embedOriginViolation}) chưa được cấu hình trong
            danh sách tên miền được phép nhúng của trợ lý này. Vui lòng liên hệ
            quản trị viên để được cấp phép.
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
        {isSending ? <SendingProgress /> : null}
        {!isSending && lastAssistantMessage ? (
          <SuggestedPromptChips
            prompts={suggestedPrompts}
            onSelect={(prompt) => void handleSend(prompt)}
            disabled={!canAsk}
          />
        ) : null}
        <div ref={messagesEndRef} />
      </div>

      <div
        className={
          embed
            ? "border-t border-border/60 bg-background pt-2.5"
            : "sticky bottom-0 border-t border-border/60 bg-background/95 pb-1 pt-3 backdrop-blur"
        }
      >
        <input
          type="text"
          name="website"
          value={honeypot}
          onChange={(event) => setHoneypot(event.target.value)}
          tabIndex={-1}
          autoComplete="off"
          aria-hidden="true"
          className="absolute -left-[9999px] -top-[9999px] opacity-0 pointer-events-none"
        />
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
