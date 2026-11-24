import { createFileRoute } from "@tanstack/react-router";
import {
  Bot,
  Check,
  Copy,
  Cpu,
  Info,
  Loader2,
  Menu,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  RotateCcw,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/api/client";
import type { ExportFormat } from "@/api/conversations";
import {
  downloadPublicDraft,
  type PublicChatSession,
  type PublicCitation,
  type PublicDocumentDraft,
  useCreatePublicChatSessionMutation,
  usePublicChatbotInfoQuery,
  useSendPublicTurnMutation,
} from "@/api/publications";
import {
  DocumentDraftCard,
  DocumentPreviewPane,
  stripDocumentMarkers,
} from "@/components/assistants/document-preview-pane";
import { MarkdownContent } from "@/components/knowledge/markdown-content";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
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
  documentDraft?: PublicDocumentDraft | null;
};

type StoredThread = {
  id: string;
  title: string;
  updatedAt: number;
  messages: PublicMessage[];
};

const MAX_STORED_THREADS = 20;

function threadsStorageKey(slug: string): string {
  return `qnu_public_chat_threads_v1:${slug}`;
}

function loadStoredThreads(slug: string): StoredThread[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(threadsStorageKey(slug));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (item): item is StoredThread =>
          Boolean(item) &&
          typeof item.id === "string" &&
          typeof item.title === "string" &&
          typeof item.updatedAt === "number" &&
          Array.isArray(item.messages),
      )
      .slice(0, MAX_STORED_THREADS);
  } catch {
    return [];
  }
}

function saveStoredThreads(slug: string, threads: StoredThread[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      threadsStorageKey(slug),
      JSON.stringify(threads.slice(0, MAX_STORED_THREADS)),
    );
  } catch {
    // Ignore storage quota / private mode errors
  }
}

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

function stripPublicCitations(text: string): string {
  return text
    .replace(/[ \t]*\[\d+(?:\s*,\s*\d+)*\]/g, "")
    .replace(/[ \t]+([.,;:!?])/g, "$1")
    .trim();
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
                    "Thông tin chưa chính xác",
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
    "Đang tìm thông tin phù hợp...",
    "Đang kiểm tra chi tiết...",
    "Đang hoàn thiện câu trả lời...",
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
  hasKnowledge: boolean,
): string[] {
  if (!hasKnowledge) {
    return starterPrompts.slice(0, 3);
  }
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

function MessageBubble({
  message,
  enabledExportFormats = [],
  isActivePreview = false,
  downloadingFormat = null,
  onOpenPreview,
  onDownloadExport,
}: {
  message: PublicMessage;
  enabledExportFormats?: ExportFormat[];
  isActivePreview?: boolean;
  downloadingFormat?: ExportFormat | null;
  onOpenPreview?: (draft: PublicDocumentDraft) => void;
  onDownloadExport?: (format: ExportFormat, draft: PublicDocumentDraft) => void;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[82%] rounded-2xl rounded-tr-xs bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-2xs">
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
      </div>
    );
  }

  if (message.tone === "error") {
    return (
      <div className="flex items-start gap-2.5">
        <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg border border-destructive/30 bg-destructive/10 text-destructive">
          <TriangleAlert className="size-3.5" />
        </div>
        <div className="max-w-[88%] rounded-2xl rounded-tl-xs border border-destructive/30 bg-destructive/5 px-3.5 py-2.5 text-xs leading-relaxed text-destructive">
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
      </div>
    );
  }

  const cleanText = stripDocumentMarkers(stripPublicCitations(message.text));

  return (
    <div className="flex items-start gap-2.5">
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
        <Bot className="size-3.5" />
      </div>
      <div className="min-w-0 flex-1 max-w-[90%] rounded-2xl rounded-tl-xs border border-border/60 bg-card px-4 py-3 shadow-2xs">
        <MarkdownContent
          content={cleanText}
          compact
          className={
            message.tone === "insufficient"
              ? "italic text-muted-foreground"
              : undefined
          }
        />
        {message.documentDraft && enabledExportFormats.length > 0 ? (
          <DocumentDraftCard
            draft={message.documentDraft}
            enabledFormats={enabledExportFormats}
            isActivePreview={isActivePreview}
            downloadingFormat={downloadingFormat}
            onOpenPreview={() => onOpenPreview?.(message.documentDraft!)}
            onDownload={(fmt) =>
              onDownloadExport?.(fmt, message.documentDraft!)
            }
          />
        ) : null}
        <MessageActionBar text={cleanText} />
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
  const [threads, setThreads] = useState<StoredThread[]>(() =>
    loadStoredThreads(slug),
  );
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
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

  // Reload stored threads if slug changes
  useEffect(() => {
    setThreads(loadStoredThreads(slug));
    setActiveThreadId(null);
    setMessages([]);
  }, [slug]);

  // Persist active conversation messages to localStorage (guest browser-only)
  useEffect(() => {
    if (embed || messages.length === 0) return;
    const firstUserMsg = messages.find((m) => m.role === "user");
    const title = firstUserMsg
      ? firstUserMsg.text.trim().slice(0, 64)
      : "Hội thoại mới";
    const threadId = activeThreadId ?? newMessageId();
    if (!activeThreadId) {
      setActiveThreadId(threadId);
    }
    setThreads((prev) => {
      const existing = prev.find((t) => t.id === threadId);
      const updated: StoredThread = {
        id: threadId,
        title: existing?.title || title,
        updatedAt: Date.now(),
        messages,
      };
      const next = [updated, ...prev.filter((t) => t.id !== threadId)].slice(
        0,
        MAX_STORED_THREADS,
      );
      saveStoredThreads(slug, next);
      return next;
    });
  }, [messages, activeThreadId, slug, embed]);

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

  const availableModels = useMemo(
    () => info?.models ?? [],
    [info?.models],
  );
  const enabledExportFormats = useMemo<ExportFormat[]>(
    () => info?.export_formats ?? [],
    [info?.export_formats],
  );
  const hasKnowledge = info?.has_knowledge !== false;
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [previewDraft, setPreviewDraft] = useState<PublicDocumentDraft | null>(
    null,
  );
  const [isPreviewExpanded, setIsPreviewExpanded] = useState(false);
  const [downloadingState, setDownloadingState] = useState<{
    draftId: string;
    format: ExportFormat;
  } | null>(null);

  useEffect(() => {
    if (availableModels.length === 0) {
      setSelectedModel("");
      return;
    }
    const stillValid = availableModels.some(
      (item) => item.model_name === selectedModel,
    );
    if (!stillValid) {
      setSelectedModel(
        info?.default_model_name ?? availableModels[0]?.model_name ?? "",
      );
    }
  }, [availableModels, info?.default_model_name, selectedModel]);

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
      hasKnowledge,
    );
  }, [lastAssistantMessage, lastUserQuestion, info?.starter_prompts, hasKnowledge]);

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
    setActiveThreadId(null);
    setSession(null);
    setPreviewDraft(null);
    setIsPreviewExpanded(false);
    sessionInitPromiseRef.current = null;
    sessionCreatedAtRef.current = 0;
    setTurnsRemaining(null);
    setBlockedReason(null);
    setDraft("");
    setMobileSidebarOpen(false);
    void infoQuery.refetch();
  };

  const handleDownloadDraft = async (
    format: ExportFormat,
    docDraft: PublicDocumentDraft,
  ) => {
    if (!session?.session_id) {
      toast.error("Phiên trò chuyện đã hết hạn. Vui lòng tạo phiên mới để tải tệp.");
      return;
    }
    if (downloadingState !== null) return;
    setDownloadingState({ draftId: docDraft.draft_id, format });
    try {
      const filename = await downloadPublicDraft(
        slug,
        session.session_id,
        docDraft.draft_id,
        format,
        docDraft.title,
      );
      toast.success(`Đã tải xuống ${filename}`);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        toast.error(error.message);
      } else {
        toast.error(`Chưa xuất được tệp ${format.toUpperCase()}.`);
      }
    } finally {
      setDownloadingState(null);
    }
  };

  const handleSelectThread = (thread: StoredThread) => {
    if (isSending) return;
    setActiveThreadId(thread.id);
    setMessages(thread.messages);
    setMobileSidebarOpen(false);
  };

  const handleDeleteThread = (threadId: string) => {
    setThreads((prev) => {
      const next = prev.filter((t) => t.id !== threadId);
      saveStoredThreads(slug, next);
      return next;
    });
    if (activeThreadId === threadId) {
      setActiveThreadId(null);
      setMessages([]);
    }
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
          model_name: selectedModel || undefined,
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
            model_name: selectedModel || undefined,
          });
        } else {
          throw firstErr;
        }
      }
      setTurnsRemaining(reply.turns_remaining);
      const replyDraft = reply.document_draft ?? null;
      if (replyDraft && enabledExportFormats.length > 0) {
        setPreviewDraft(replyDraft);
      }
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
          documentDraft: replyDraft,
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
        err.code === "public_chat_model_unavailable"
      ) {
        void infoQuery.refetch();
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

  const sidebarContent = (
    <div className="flex h-full flex-col bg-card">
      {/* Sidebar Header */}
      <div className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-border/60 px-3.5">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-2xs">
            <Bot className="size-4" />
          </div>
          <div className="min-w-0">
            <p
              className="truncate text-xs font-semibold text-foreground"
              title={info.display_name}
            >
              {info.display_name}
            </p>
            <p className="truncate text-[10px] text-muted-foreground">
              Đại học Quy Nhơn
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="hidden size-7 p-0 text-muted-foreground hover:text-foreground lg:inline-flex"
          onClick={() => setSidebarOpen(false)}
          title="Thu gọn thanh bên"
          aria-label="Thu gọn thanh bên"
        >
          <PanelLeftClose className="size-4" />
        </Button>
      </div>

      {/* Primary CTA: Hội thoại mới */}
      <div className="p-3">
        <Button
          type="button"
          size="sm"
          className="h-9 w-full justify-start gap-2 text-xs font-medium shadow-2xs cursor-pointer"
          disabled={isSending}
          onClick={handleResetSession}
        >
          <Plus className="size-4" />
          <span>Hội thoại mới</span>
        </Button>
      </div>

      {/* Recent Threads */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2.5 pb-3">
        <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Gần đây
        </p>
        {threads.length === 0 ? (
          <p className="px-2 py-3 text-xs text-muted-foreground/80">
            Chưa có hội thoại nào.
          </p>
        ) : (
          <div className="space-y-1">
            {threads.map((thread) => {
              const isActive = thread.id === activeThreadId;
              return (
                <div
                  key={thread.id}
                  className={cn(
                    "group flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs transition-colors",
                    isActive
                      ? "bg-primary/10 font-medium text-primary"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                  )}
                >
                  <button
                    type="button"
                    disabled={isSending}
                    onClick={() => handleSelectThread(thread)}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left cursor-pointer"
                    title={thread.title}
                  >
                    <MessageSquare className="size-3.5 shrink-0 opacity-75" />
                    <span className="truncate">{thread.title}</span>
                  </button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={isSending}
                    onClick={() => handleDeleteThread(thread.id)}
                    className="size-6 shrink-0 p-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100 focus-visible:opacity-100"
                    aria-label={`Xóa hội thoại ${thread.title}`}
                    title="Xóa hội thoại"
                  >
                    <Trash2 className="size-3" />
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Info Footer */}
      <div className="shrink-0 space-y-2 border-t border-border/60 bg-muted/20 p-3.5 text-[11px] text-muted-foreground">
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 font-medium text-foreground">
            <Info className="size-3.5 text-primary shrink-0" />
            <span>Kênh công khai</span>
          </span>
          <Badge
            variant={info.available ? "success" : "secondary"}
            className="h-4 px-1.5 text-[10px] font-normal"
          >
            {info.available ? "Sẵn sàng" : "Tạm ngưng"}
          </Badge>
        </div>
        {remaining !== null && info.available ? (
          <p className="text-[11px] text-muted-foreground">
            Còn{" "}
            <strong className="font-semibold text-foreground">
              {remaining}/{info.max_turns_per_session}
            </strong>{" "}
            lượt hỏi trong phiên này.
          </p>
        ) : null}
        <p className="leading-relaxed text-[10.5px] text-muted-foreground/85">
          Không cần đăng nhập. Lịch sử hội thoại chỉ lưu cục bộ trên trình duyệt
          của bạn.
        </p>
      </div>
    </div>
  );

  return (
    <div className="relative flex h-dvh w-full overflow-hidden bg-background text-foreground antialiased">
      {/* Desktop Sidebar (ẩn khi embed=1) */}
      {!embed && sidebarOpen ? (
        <aside className="hidden h-full w-72 shrink-0 border-r border-border/60 lg:block">
          {sidebarContent}
        </aside>
      ) : null}

      {/* Mobile Sidebar Drawer (ẩn khi embed=1) */}
      {!embed ? (
        <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
          <SheetContent
            side="left"
            className="w-72 p-0 sm:max-w-xs"
            aria-describedby={undefined}
          >
            <SheetTitle className="sr-only">{info.display_name}</SheetTitle>
            {sidebarContent}
          </SheetContent>
        </Sheet>
      ) : null}

      {/* Main Chat Area */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-background">
        {/* Top Header */}
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border/60 bg-card/85 px-3.5 backdrop-blur sm:px-5">
          <div className="flex min-w-0 items-center gap-2.5">
            {!embed ? (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="size-8 p-0 text-muted-foreground hover:text-foreground lg:hidden"
                  onClick={() => setMobileSidebarOpen(true)}
                  aria-label="Mở danh sách hội thoại"
                >
                  <Menu className="size-4" />
                </Button>
                {!sidebarOpen ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="hidden size-8 p-0 text-muted-foreground hover:text-foreground lg:inline-flex"
                    onClick={() => setSidebarOpen(true)}
                    title="Mở thanh bên"
                    aria-label="Mở thanh bên"
                  >
                    <PanelLeftOpen className="size-4" />
                  </Button>
                ) : null}
              </>
            ) : null}

            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary lg:hidden">
              <Bot className="size-4" />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-sm font-semibold tracking-tight text-foreground">
                  {info.display_name}
                </h1>
                <Badge
                  variant={info.available ? "success" : "secondary"}
                  className="hidden h-4 px-1.5 text-[10px] font-normal sm:inline-flex"
                >
                  {info.available ? "Trực tuyến" : "Tạm ngưng"}
                </Badge>
              </div>
              {embed ? (
                <p className="truncate text-[10.5px] text-muted-foreground">
                  Trợ lý công khai · Không cần đăng nhập
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            {availableModels.length > 0 ? (
              <Select
                value={selectedModel}
                onValueChange={(value) => {
                  setSelectedModel(value);
                  const chosen = availableModels.find(
                    (item) => item.model_name === value,
                  );
                  if (chosen) {
                    toast.success(`Đã chuyển sang mô hình ${chosen.label}`);
                  }
                }}
                disabled={isSending || !info.available}
              >
                <SelectTrigger
                  className="h-8 w-[155px] gap-1.5 px-2.5 text-xs sm:w-[195px]"
                  aria-label="Chọn mô hình AI"
                  title="Chọn mô hình AI trả lời"
                >
                  <Cpu className="size-3.5 shrink-0 text-primary" />
                  <SelectValue placeholder="Chọn mô hình" />
                </SelectTrigger>
                <SelectContent align="end">
                  {availableModels.map((item) => (
                    <SelectItem
                      key={item.model_name}
                      value={item.model_name}
                      className="text-xs"
                    >
                      <span className="flex items-center gap-1.5">
                        <span className="truncate">{item.label}</span>
                        {item.is_default ? (
                          <span className="rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground">
                            Mặc định
                          </span>
                        ) : null}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : null}
            {messages.length > 0 && activeThreadId && !embed ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 gap-1.5 px-2 text-xs text-muted-foreground hover:text-destructive cursor-pointer"
                disabled={isSending}
                onClick={() => handleDeleteThread(activeThreadId)}
                title="Xóa hội thoại này"
              >
                <Trash2 className="size-3.5" />
                <span className="hidden sm:inline">Xóa</span>
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 px-2.5 text-xs cursor-pointer"
              disabled={isSending}
              onClick={handleResetSession}
              title="Bắt đầu phiên hội thoại mới"
            >
              <RotateCcw className="size-3.5" />
              <span className="hidden sm:inline">Làm mới</span>
            </Button>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 overflow-hidden">
          <div
            className={cn(
              "flex min-h-0 flex-1 flex-col overflow-hidden",
              previewDraft && enabledExportFormats.length > 0 && "hidden lg:flex",
            )}
          >
        {/* Scrollable Message Viewport */}
        <div
          className="relative min-h-0 flex-1 overflow-y-auto px-4 py-6"
          role="log"
          aria-live="polite"
          aria-label="Hội thoại"
        >
          <div className="mx-auto w-full max-w-3xl space-y-5">
            {!info.available ? (
              <Alert variant="warning">
                <AlertTitle>Trợ lý đang tạm ngưng phục vụ</AlertTitle>
                <AlertDescription>
                  {info.unavailable_reason ??
                    "Đơn vị đang cập nhật nội dung. Vui lòng quay lại sau."}
                </AlertDescription>
              </Alert>
            ) : null}

            {embedOriginViolation ? (
              <Alert variant="destructive">
                <AlertTitle>Tên miền chưa được cấp phép nhúng</AlertTitle>
                <AlertDescription>
                  Trang web hiện tại ({embedOriginViolation}) chưa được cấu hình
                  trong danh sách tên miền được phép nhúng của trợ lý này. Vui
                  lòng liên hệ quản trị viên để được cấp phép.
                </AlertDescription>
              </Alert>
            ) : null}

            {blockedReason ? (
              <Alert variant="destructive">
                <AlertTitle>Trợ lý tạm ngưng nhận câu hỏi</AlertTitle>
                <AlertDescription>{blockedReason}</AlertDescription>
              </Alert>
            ) : null}

            {messages.length === 0 ? (
              <div className="mx-auto max-w-2xl space-y-6 py-8 sm:py-12">
                <div className="space-y-2.5 text-center">
                  <div className="mx-auto flex size-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary shadow-2xs">
                    <Bot className="size-6" />
                  </div>
                  <div className="space-y-1">
                    <h2 className="text-lg font-semibold tracking-tight text-foreground">
                      {info.display_name}
                    </h2>
                    <p className="mx-auto max-w-lg text-xs leading-relaxed text-muted-foreground">
                      {info.welcome_message ||
                        "Đặt câu hỏi về thông tin do đơn vị cung cấp để được hỗ trợ nhanh chóng."}
                    </p>
                  </div>
                </div>

                {info.available && info.starter_prompts.length > 0 ? (
                  <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                    {info.starter_prompts.map((prompt) => (
                      <button
                        key={prompt}
                        type="button"
                        disabled={!canAsk}
                        onClick={() => void handleSend(prompt)}
                        className="group flex items-start gap-2.5 rounded-xl border border-border/60 bg-card p-3.5 text-left text-xs leading-relaxed text-foreground transition-colors hover:border-primary/50 hover:bg-muted/30 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer shadow-2xs"
                      >
                        <Sparkles className="mt-0.5 size-3.5 shrink-0 text-primary" />
                        <span className="line-clamp-3">{prompt}</span>
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  enabledExportFormats={enabledExportFormats}
                  isActivePreview={
                    Boolean(
                      message.documentDraft &&
                        previewDraft?.draft_id ===
                          message.documentDraft.draft_id,
                    )
                  }
                  downloadingFormat={
                    message.documentDraft &&
                    downloadingState?.draftId ===
                      message.documentDraft.draft_id
                      ? downloadingState.format
                      : null
                  }
                  onOpenPreview={(docDraft) => setPreviewDraft(docDraft)}
                  onDownloadExport={(fmt, docDraft) =>
                    void handleDownloadDraft(fmt, docDraft)
                  }
                />
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
        </div>

        {/* Fixed Bottom Composer */}
        <div className="shrink-0 border-t border-border/60 bg-card/85 px-4 py-3 backdrop-blur">
          <div className="mx-auto w-full max-w-3xl">
            <input
              type="text"
              name="website"
              value={honeypot}
              onChange={(event) => setHoneypot(event.target.value)}
              tabIndex={-1}
              autoComplete="off"
              aria-hidden="true"
              className="pointer-events-none absolute -left-[9999px] -top-[9999px] opacity-0"
            />
            <div className="flex items-end gap-2 rounded-2xl border border-border/70 bg-muted/35 p-1.5 shadow-2xs transition-colors focus-within:border-primary/60 focus-within:bg-background">
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
                rows={1}
                placeholder={
                  info.available
                    ? "Nhập câu hỏi của bạn..."
                    : "Trợ lý đang tạm ngưng phục vụ."
                }
                className="max-h-32 min-h-[38px] flex-1 resize-none border-0 bg-transparent px-3 py-2 text-sm leading-relaxed shadow-none placeholder:text-muted-foreground focus-visible:ring-0"
                disabled={!canAsk}
                aria-label="Câu hỏi của bạn"
              />
              <Button
                type="button"
                size="sm"
                className="h-8 shrink-0 gap-1.5 rounded-xl px-3 text-xs font-medium shadow-2xs cursor-pointer"
                disabled={!canAsk || !draft.trim()}
                onClick={() => void handleSend(draft)}
              >
                {isSending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Send className="size-3.5" />
                )}
                <span className="hidden sm:inline">Gửi</span>
              </Button>
            </div>
            {embed && remaining !== null && info.available ? (
              <p className="mt-1.5 text-right text-[10px] text-muted-foreground">
                Còn {remaining}/{info.max_turns_per_session} lượt
              </p>
            ) : null}
          </div>
        </div>
          </div>

          {previewDraft && enabledExportFormats.length > 0 ? (
            <DocumentPreviewPane
              draft={previewDraft}
              enabledFormats={enabledExportFormats}
              downloadingFormat={
                downloadingState?.draftId === previewDraft.draft_id
                  ? downloadingState.format
                  : null
              }
              isExpanded={isPreviewExpanded}
              onToggleExpand={() => setIsPreviewExpanded((prev) => !prev)}
              onDownload={(fmt) => void handleDownloadDraft(fmt, previewDraft)}
              onClose={() => {
                setPreviewDraft(null);
                setIsPreviewExpanded(false);
              }}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
