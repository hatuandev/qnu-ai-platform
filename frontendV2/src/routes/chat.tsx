import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  Bot,
  Copy,
  Database,
  Loader2,
  MessageCircle,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  type AssistantResponse,
  useAssistantReadinessQuery,
  useAssistantsQuery,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import {
  type ConversationTurn,
  conversationKeys,
  useAssistantConversationsQuery,
  useConversationTurnsQuery,
  useCreateConversationMutation,
  useSendTurnMutation,
} from "@/api/conversations";
import { useCatalogQuery } from "@/api/modelops";
import { EmptyState } from "@/components/admin/empty-state";
import { providerLabel } from "@/components/assistants/model-label";
import {
  TURN_ERROR_TEXT,
  TurnResult,
} from "@/components/assistants/turn-result";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/chat")({
  component: ChatPage,
  validateSearch: (search: Record<string, unknown>): { q?: string } => {
    const question = typeof search.q === "string" ? search.q.trim() : "";
    return question ? { q: question.slice(0, 500) } : {};
  },
});

const DRAFT_VALUE = "__draft__";

const STARTER_PROMPTS = [
  { icon: MessageCircle, title: "Xin chào", prompt: "Xin chào" },
  { icon: Bot, title: "Bạn là trợ lý gì?", prompt: "Bạn là trợ lý gì?" },
  {
    icon: Sparkles,
    title: "Bạn có thể giúp gì?",
    prompt: "Bạn có thể giúp gì cho tôi?",
  },
];

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function turnAnswerText(turn: ConversationTurn): string | null {
  if (!turn.result) return null;
  if (turn.result.status === "direct_reply") return turn.result.answer;
  const text =
    turn.result.statements.length > 0
      ? turn.result.statements.map((statement) => statement.text).join("\n")
      : (turn.result.answer ?? "");
  return text.trim() ? text : null;
}

function UserBubble({ question }: { question: string }) {
  return (
    <div className="flex justify-end gap-2.5">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-xs bg-primary px-4 py-2.5 text-xs leading-relaxed text-primary-foreground shadow-2xs">
        {question}
      </div>
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-border/50 bg-muted text-muted-foreground">
        <User className="size-4" />
      </div>
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
      <Bot className="size-4" />
    </div>
  );
}

function TurnRow({
  turn,
  onCopy,
}: {
  turn: ConversationTurn;
  onCopy: (text: string) => void;
}) {
  const copyText = turnAnswerText(turn);
  return (
    <div className="space-y-3">
      <UserBubble question={turn.question} />
      <div className="flex gap-2.5">
        <AssistantAvatar />
        <div className="min-w-0 flex-1 space-y-2.5 rounded-2xl rounded-tl-xs border border-border/60 bg-card px-4 py-3 shadow-2xs">
          <TurnResult turn={turn} />
          <div className="flex items-center justify-between border-t border-border/30 pt-1.5 text-[10px] text-muted-foreground">
            <span>
              {formatTime(turn.created_at)} · Lượt {turn.turn_no}
            </span>
            {copyText ? (
              <Button
                variant="ghost"
                size="sm"
                className="size-7 p-0 text-muted-foreground hover:text-foreground"
                title="Sao chép câu trả lời"
                onClick={() => onCopy(copyText)}
              >
                <Copy className="size-3.5" />
                <span className="sr-only">Sao chép câu trả lời</span>
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function PendingRow({ question }: { question: string }) {
  return (
    <div className="space-y-3">
      <UserBubble question={question} />
      <div className="flex gap-2.5">
        <AssistantAvatar />
        <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-2xl rounded-tl-xs border border-border/60 bg-card px-4 py-3 text-xs text-muted-foreground shadow-2xs">
          <Loader2 className="size-3.5 shrink-0 animate-spin text-primary" />
          <span>
            Đang truy xuất nguồn và tổng hợp câu trả lời. Lượt hỏi thường mất
            1–3 phút.
          </span>
        </div>
      </div>
    </div>
  );
}

function WelcomePanel({
  assistant,
  isCollectionEmpty,
  isCollectionUnbound,
  onPick,
}: {
  assistant: AssistantResponse;
  isCollectionEmpty: boolean;
  isCollectionUnbound: boolean;
  onPick: (question: string) => void;
}) {
  return (
    <div className="animate-in space-y-6 py-8 duration-300 fade-in-50">
      <div className="space-y-2 text-center">
        <div className="mx-auto flex size-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary shadow-2xs">
          <Bot className="size-6" />
        </div>
        <h2 className="text-base font-semibold text-foreground">
          {assistant.name}
        </h2>
        <p className="mx-auto max-w-md text-xs leading-relaxed text-muted-foreground">
          {assistant.description ||
            "Đặt câu hỏi để trợ lý tra cứu kho tri thức đã xuất bản và trả lời kèm nguồn trích dẫn."}
        </p>
      </div>
      <div className="space-y-2.5">
        <p className="px-1 text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
          Bắt đầu nhanh
        </p>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          {STARTER_PROMPTS.map((item) => (
            <Button
              key={item.title}
              variant="outline"
              className="h-auto justify-start gap-2 px-3 py-2.5 text-left text-xs font-normal whitespace-normal"
              disabled={isCollectionUnbound}
              onClick={() => onPick(item.prompt)}
            >
              <item.icon className="size-3.5 shrink-0 text-primary" />
              <span>{item.title}</span>
            </Button>
          ))}
        </div>
        <p className="px-1 text-[11px] leading-relaxed text-muted-foreground">
          {isCollectionUnbound
            ? "Trợ lý chưa gắn kho tri thức nên chưa thể trả lời. Gắn kho trong tab Cấu hình của trợ lý trước khi hỏi."
            : isCollectionEmpty
              ? "Kho tri thức chưa có tài liệu xuất bản nên hiện chỉ trả lời được câu hỏi chào hỏi, giới thiệu."
              : "Câu trả lời chỉ dùng nội dung đã xuất bản và kèm nguồn trích dẫn để đối chiếu."}
        </p>
      </div>
    </div>
  );
}

function ChatPage() {
  const workspaceId = useUiStore((state) => state.activeWorkspaceId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);

  const [selectedAssistantId, setSelectedAssistantId] = useState<string | null>(
    null,
  );
  const [selectedConversationId, setSelectedConversationId] = useState<
    string | null
  >(null);
  const [isDraftMode, setIsDraftMode] = useState(false);
  const [localTurn, setLocalTurn] = useState<{
    conversationId: string;
    turnNo: number;
  } | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const { q: presetQuestion } = Route.useSearch();

  // A question handed over from the landing page prefills the composer once,
  // then the query param is dropped so a reload starts a clean conversation.
  useEffect(() => {
    if (!presetQuestion) return;
    setInput(presetQuestion);
    void navigate({ to: "/chat", search: {}, replace: true });
  }, [presetQuestion, navigate]);

  const assistantsQuery = useAssistantsQuery(workspaceId);
  const assistants = assistantsQuery.data ?? [];

  const assistant = useMemo(() => {
    if (selectedAssistantId) {
      const selected = assistants.find(
        (item) => item.id === selectedAssistantId,
      );
      if (selected) return selected;
    }
    return assistants.find((item) => item.is_active) ?? assistants[0] ?? null;
  }, [assistants, selectedAssistantId]);

  const conversationsQuery = useAssistantConversationsQuery(
    workspaceId,
    assistant?.id,
  );
  const conversations = conversationsQuery.data ?? [];

  const activeConversation = useMemo(() => {
    if (isDraftMode) return null;
    const selected = conversations.find(
      (item) => item.id === selectedConversationId,
    );
    return selected ?? conversations[0] ?? null;
  }, [conversations, isDraftMode, selectedConversationId]);

  const turnsQuery = useConversationTurnsQuery(
    workspaceId,
    activeConversation?.id,
    !isDraftMode,
  );
  const turns = turnsQuery.data ?? [];

  const readinessQuery = useAssistantReadinessQuery(workspaceId, assistant?.id);
  const readiness = readinessQuery.data;

  const catalogQuery = useCatalogQuery(
    workspaceId,
    Boolean(workspaceId) && Boolean(assistant?.chat_provider_id),
  );

  const createMutation = useCreateConversationMutation(workspaceId);
  const sendMutation = useSendTurnMutation(workspaceId);

  const isSending = pendingQuestion !== null;
  const isInactive = assistant ? !assistant.is_active : false;
  const isCollectionUnbound =
    Boolean(assistant) && (assistant?.collection_ids?.length ?? 0) === 0;
  const isCollectionEmpty =
    !isCollectionUnbound && readiness?.status === "empty";
  const isIndexWarning =
    readiness?.status === "outdated" ||
    readiness?.status === "not_indexed" ||
    readiness?.status === "failed" ||
    readiness?.status === "uncertain" ||
    readiness?.status === "syncing";
  const isComposerDisabled =
    !assistant ||
    isInactive ||
    isCollectionUnbound ||
    isSending ||
    !workspaceId;

  const modelLabel = useMemo(() => {
    if (!assistant) return "";
    if (!assistant.chat_provider_id) {
      return "Dùng mô hình mặc định của hệ thống";
    }
    const item = catalogQuery.data?.find(
      (entry) => entry.id === assistant.chat_provider_id,
    );
    return item ? `Mô hình: ${providerLabel(item)}` : "Mô hình đã cấu hình";
  }, [assistant, catalogQuery.data]);

  const activeConversationId = activeConversation?.id;
  const turnCount = turns.length;

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    if (turnCount === 0 && !pendingQuestion && !activeConversationId) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [turnCount, pendingQuestion, activeConversationId]);

  const handleAssistantChange = (assistantId: string) => {
    if (isSending) return;
    setSelectedAssistantId(assistantId);
    setSelectedConversationId(null);
    setIsDraftMode(false);
    setLocalTurn(null);
    setInput("");
  };

  const handleConversationChange = (value: string) => {
    if (isSending) return;
    setLocalTurn(null);
    if (value === DRAFT_VALUE) {
      setSelectedConversationId(null);
      setIsDraftMode(true);
      return;
    }
    setSelectedConversationId(value);
    setIsDraftMode(false);
  };

  const handleNewConversation = () => {
    if (isSending) return;
    setSelectedConversationId(null);
    setIsDraftMode(true);
    setLocalTurn(null);
    setInput("");
  };

  const handleRefresh = () => {
    void conversationsQuery.refetch();
    if (activeConversationId) {
      void turnsQuery.refetch();
    }
  };

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Đã sao chép câu trả lời.");
    } catch {
      toast.error("Trình duyệt không cho phép sao chép nội dung.");
    }
  };

  const appendTurnToCache = (
    conversationId: string,
    turn: ConversationTurn,
  ) => {
    if (!workspaceId) return;
    const key = conversationKeys.turns(workspaceId, conversationId);
    queryClient.setQueryData<ConversationTurn[]>(key, (previous) =>
      previous
        ? [...previous.filter((item) => item.id !== turn.id), turn].sort(
            (left, right) => left.turn_no - right.turn_no,
          )
        : [turn],
    );
  };

  const handleSendError = (error: unknown) => {
    setLocalTurn(null);
    if (!(error instanceof ApiProblemError)) {
      toast.error(
        error instanceof Error ? error.message : "Không gửi được câu hỏi.",
      );
      return;
    }
    if (error.code === "conversation_sequence_conflict") {
      toast.error(
        "Hội thoại vừa thay đổi ở nơi khác. Danh sách đã được tải lại; hãy gửi lại câu hỏi.",
      );
      return;
    }
    if (error.code === "conversation_busy") {
      toast.warning(
        "Hội thoại đang xử lý một lượt khác. Chờ lượt đó xong rồi gửi lại.",
      );
      return;
    }
    if (error.code === "idempotency_conflict") {
      toast.error("Yêu cầu bị trùng mã gửi. Hãy gửi lại câu hỏi.");
      return;
    }
    if (error.code === "request_aborted") {
      toast.error("Yêu cầu bị hủy trước khi máy chủ phản hồi.");
      return;
    }
    const mapped = TURN_ERROR_TEXT[error.code];
    if (mapped) {
      toast.error(`${mapped} Lượt hỏi đã được ghi nhận trong hội thoại.`);
      return;
    }
    toast.error(error.message || "Không gửi được câu hỏi.");
  };

  const handleSend = async (questionOverride?: string) => {
    const question = (questionOverride ?? input).trim();
    if (!question || isSending || !assistant) return;
    if (!assistant.is_active) {
      toast.error("Trợ lý đang tạm dừng nên không nhận câu hỏi mới.");
      return;
    }
    if (!workspaceId) return;

    setInput("");
    setPendingQuestion(question);
    const assistantId = assistant.id;

    try {
      let conversation = activeConversation;
      if (!conversation) {
        conversation = await createMutation.mutateAsync({
          assistantId,
          title: question.slice(0, 160),
        });
        setSelectedConversationId(conversation.id);
        setIsDraftMode(false);
      }

      const expectedTurnNo =
        localTurn && localTurn.conversationId === conversation.id
          ? localTurn.turnNo
          : conversation.last_turn_no;

      const conversationId = conversation.id;
      const turn = await sendMutation.mutateAsync({
        conversationId,
        question,
        expectedTurnNo,
      });

      appendTurnToCache(conversationId, turn);
      setLocalTurn({ conversationId, turnNo: turn.turn_no });

      if (turn.status === "failed") {
        toast.error(
          TURN_ERROR_TEXT[turn.error_code ?? ""] ?? "Lượt hỏi thất bại.",
        );
      } else if (turn.status === "uncertain") {
        toast.warning("Lượt hỏi bị gián đoạn trước khi hoàn tất.");
      }
    } catch (error) {
      handleSendError(error);
    } finally {
      setPendingQuestion(null);
    }
  };

  if (!workspaceId) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center bg-background px-4">
        <EmptyState
          icon={MessageCircle}
          title="Chưa chọn đơn vị"
          description="Chọn đơn vị ở thanh bên để sử dụng trợ lý."
        />
      </div>
    );
  }

  if (assistantsQuery.isLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] flex-col gap-3 bg-background p-4">
        <Skeleton className="h-14 w-full" />
        <div className="mx-auto w-full max-w-3xl space-y-3 pt-6">
          <Skeleton className="ml-auto h-12 w-2/3" />
          <Skeleton className="h-36 w-full" />
          <Skeleton className="ml-auto h-12 w-1/2" />
        </div>
      </div>
    );
  }

  if (assistantsQuery.isError) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center bg-background px-4">
        <EmptyState
          icon={Bot}
          title="Không tải được danh sách trợ lý"
          description={
            assistantsQuery.error instanceof Error
              ? assistantsQuery.error.message
              : "Lỗi không xác định."
          }
          action={{
            label: "Thử lại",
            onClick: () => void assistantsQuery.refetch(),
          }}
        />
      </div>
    );
  }

  if (!assistant) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center bg-background px-4">
        <EmptyState
          icon={Bot}
          title="Chưa có trợ lý"
          description="Tạo trợ lý trong mục Trợ lý và gắn kho tri thức trước khi bắt đầu hội thoại."
          action={{
            label: "Mở danh sách trợ lý",
            onClick: () => void navigate({ to: "/assistants" }),
          }}
        />
      </div>
    );
  }

  const conversationValue = isDraftMode
    ? DRAFT_VALUE
    : (activeConversation?.id ?? DRAFT_VALUE);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col bg-background">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-card px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
            <Bot className="size-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-sm font-semibold text-foreground">
                {assistant.name}
              </h1>
              <Badge
                variant={assistant.is_active ? "success" : "secondary"}
                className="h-4 shrink-0 px-1.5 text-[10px] font-normal"
              >
                {assistant.is_active ? "Hoạt động" : "Tạm dừng"}
              </Badge>
            </div>
            <p className="truncate text-[11px] text-muted-foreground">
              {modelLabel}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={assistant.id}
            onValueChange={handleAssistantChange}
            disabled={isSending}
          >
            <SelectTrigger
              className="h-8 w-[170px] text-xs"
              aria-label="Chọn trợ lý"
            >
              <Bot className="size-3.5 text-muted-foreground" />
              <SelectValue placeholder="Chọn trợ lý" />
            </SelectTrigger>
            <SelectContent>
              {assistants.map((item) => (
                <SelectItem key={item.id} value={item.id} className="text-xs">
                  {item.is_active ? item.name : `${item.name} (tạm dừng)`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={conversationValue}
            onValueChange={handleConversationChange}
            disabled={isSending}
          >
            <SelectTrigger
              className="h-8 w-[200px] text-xs"
              aria-label="Chọn hội thoại"
            >
              <MessageCircle className="size-3.5 text-muted-foreground" />
              <SelectValue placeholder="Chọn hội thoại" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={DRAFT_VALUE} className="text-xs">
                Hội thoại mới
              </SelectItem>
              {conversations.map((conversation) => (
                <SelectItem
                  key={conversation.id}
                  value={conversation.id}
                  className="text-xs"
                >
                  {conversation.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            onClick={handleNewConversation}
            disabled={isSending}
          >
            <Plus className="size-3.5" />
            <span className="hidden sm:inline">Hội thoại mới</span>
            <span className="sr-only sm:hidden">Hội thoại mới</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className="size-8 p-0 text-muted-foreground hover:text-foreground"
            title="Tải lại hội thoại"
            onClick={handleRefresh}
            disabled={
              isSending ||
              conversationsQuery.isFetching ||
              turnsQuery.isFetching
            }
          >
            <RefreshCw
              className={cn(
                "size-4",
                (conversationsQuery.isFetching || turnsQuery.isFetching) &&
                  "animate-spin",
              )}
            />
            <span className="sr-only">Tải lại hội thoại</span>
          </Button>
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto w-full max-w-3xl space-y-5">
          {isInactive ? (
            <Alert variant="warning">
              <AlertTitle>Trợ lý đang tạm dừng</AlertTitle>
              <AlertDescription>
                Bật lại trợ lý trong trang Trợ lý trước khi tiếp tục hội thoại.
              </AlertDescription>
            </Alert>
          ) : null}

          {!isInactive && isCollectionUnbound ? (
            <Alert variant="warning">
              <AlertTitle>Trợ lý chưa gắn kho tri thức</AlertTitle>
              <AlertDescription>
                Trợ lý chưa có kho tri thức nào nên chưa thể trả lời. Mở tab Cấu
                hình của trợ lý trong trang Trợ lý để gắn ít nhất một kho.
              </AlertDescription>
            </Alert>
          ) : null}

          {!isInactive && isCollectionEmpty ? (
            <Alert variant="warning">
              <AlertTitle>Kho tri thức chưa có tài liệu xuất bản</AlertTitle>
              <AlertDescription>
                <span>
                  Trợ lý chỉ trả lời từ nội dung đã xuất bản. Câu hỏi tra cứu sẽ
                  lỗi cho tới khi kho có ít nhất một tài liệu được xuất bản và
                  lập chỉ mục.
                </span>
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="mt-2 h-7 gap-1.5 text-xs"
                >
                  <Link
                    to="/knowledge"
                    search={{
                      collectionId: assistant.collection_id ?? undefined,
                    }}
                  >
                    <Database className="size-3.5" />
                    <span>Mở kho tri thức</span>
                  </Link>
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}

          {!isInactive && !isCollectionEmpty && isIndexWarning ? (
            <Alert variant="info">
              <AlertTitle>Chỉ mục chưa sẵn sàng</AlertTitle>
              <AlertDescription>
                Kho có thể đang chờ nạp lại chỉ mục; câu trả lời có thể thiếu
                nguồn cho tới khi quá trình này hoàn tất.
              </AlertDescription>
            </Alert>
          ) : null}

          {conversationsQuery.isError && conversations.length === 0 ? (
            <Alert variant="destructive">
              <AlertTitle>Không tải được danh sách hội thoại</AlertTitle>
              <AlertDescription>
                <span>
                  {conversationsQuery.error instanceof Error
                    ? conversationsQuery.error.message
                    : "Lỗi không xác định."}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 h-7 text-xs"
                  onClick={() => void conversationsQuery.refetch()}
                >
                  Thử lại
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}

          {turnsQuery.isLoading && !isDraftMode ? (
            <div className="space-y-4 pt-2">
              <Skeleton className="ml-auto h-12 w-2/3" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : turnsQuery.isError ? (
            <Alert variant="destructive">
              <AlertTitle>Không tải được lượt hỏi</AlertTitle>
              <AlertDescription>
                <span>
                  {turnsQuery.error instanceof Error
                    ? turnsQuery.error.message
                    : "Lỗi không xác định."}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 h-7 text-xs"
                  onClick={() => void turnsQuery.refetch()}
                >
                  Thử lại
                </Button>
              </AlertDescription>
            </Alert>
          ) : turns.length === 0 && !pendingQuestion ? (
            <WelcomePanel
              assistant={assistant}
              isCollectionEmpty={Boolean(isCollectionEmpty)}
              isCollectionUnbound={isCollectionUnbound}
              onPick={(question) => void handleSend(question)}
            />
          ) : (
            <>
              {turns.map((turn) => (
                <TurnRow
                  key={turn.id}
                  turn={turn}
                  onCopy={(text) => void handleCopy(text)}
                />
              ))}
              {pendingQuestion ? (
                <PendingRow question={pendingQuestion} />
              ) : null}
            </>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t border-border/60 bg-card p-3">
        <div className="mx-auto w-full max-w-3xl space-y-1.5">
          <div className="flex items-end gap-2 rounded-xl border border-border/60 bg-muted/40 p-1.5 shadow-2xs transition-colors focus-within:border-primary/60 focus-within:bg-background">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void handleSend();
                }
              }}
              placeholder={
                isInactive
                  ? "Trợ lý đang tạm dừng nhận câu hỏi..."
                  : isCollectionUnbound
                    ? "Trợ lý chưa gắn kho tri thức..."
                    : "Nhập câu hỏi cho trợ lý..."
              }
              rows={1}
              maxLength={8000}
              disabled={isComposerDisabled}
              className="max-h-32 min-h-[38px] flex-1 resize-none border-0 bg-transparent px-3 py-2 text-xs leading-relaxed shadow-none placeholder:text-muted-foreground focus-visible:ring-0"
            />
            <Button
              size="sm"
              onClick={() => void handleSend()}
              disabled={isComposerDisabled || !input.trim()}
              className="h-8 shrink-0 gap-1.5 rounded-lg px-3 text-xs font-medium shadow-2xs"
            >
              {isSending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Send className="size-3.5" />
              )}
              <span className="hidden sm:inline">
                {isSending ? "Đang gửi" : "Gửi"}
              </span>
            </Button>
          </div>
          <p className="text-center text-[10px] text-muted-foreground/80">
            {isInactive
              ? "Bật lại trợ lý trong trang Trợ lý để tiếp tục hội thoại."
              : "Câu trả lời chỉ dùng nội dung đã xuất bản của kho tri thức gắn với trợ lý. Lượt hỏi thường mất 1–3 phút."}
          </p>
        </div>
      </div>
    </div>
  );
}
