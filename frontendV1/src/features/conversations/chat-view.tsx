import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  ChevronUp,
  Loader2,
  Lock,
  MoreVertical,
  Pencil,
  SendHorizontal,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError, v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useAssistantQuery } from "@/features/assistants/queries";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import {
  draftToFilter,
  EMPTY_METADATA_FILTER_DRAFT,
  isMetadataFilterDraftEmpty,
  type MetadataFilterDraft,
  MetadataFilterFields,
  validateMetadataFilterDraft,
} from "@/features/rag/metadata-filter-fields";
import {
  describeMetadataFilter,
  type MetadataFilter,
} from "@/features/rag/types";
import { ChatMessageItem } from "./chat-message-item";
import { CitationSheet } from "./citation-sheet";
import { ConversationRenameDialog } from "./conversation-rename-dialog";
import {
  conversationsQueryKeys,
  useConversationHistoryQuery,
  useConversationQuery,
  useSendTurn,
} from "./queries";
import { getTurn } from "./requests";
import { formatConversationError, generateIdempotencyKey } from "./schemas";
import type { EvidenceSource, Statement, TurnResponse } from "./types";

type ChatViewProps = {
  workspaceId: string;
  conversationId: string;
  onBack?: () => void;
};
export function ChatView(props: ChatViewProps) {
  const { sessionId } = useV1Auth();
  return (
    <ChatSession
      key={`${sessionId}:${props.workspaceId}:${props.conversationId}`}
      {...props}
    />
  );
}
function ChatSession({ workspaceId, conversationId, onBack }: ChatViewProps) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  const conversationQuery = useConversationQuery(workspaceId, conversationId);
  const conversation = conversationQuery.data;

  // Assistant query for info and status
  const assistantQuery = useAssistantQuery(
    workspaceId,
    conversation?.assistant_id ?? "",
  );
  const assistant = assistantQuery.data;

  const turnsQuery = useConversationHistoryQuery(
    workspaceId,
    conversationId,
    conversation?.last_turn_no,
  );
  const turns = turnsQuery.data?.turns ?? [];

  // Update conversation mutation (rename / archive / unarchive)
  const sendTurnMutation = useSendTurn(workspaceId, conversationId);

  // UI state
  const [renameOpen, setRenameOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [citationOpen, setCitationOpen] = useState(false);
  const [activeStatement, setActiveStatement] = useState<Statement | null>(
    null,
  );
  const [activeSources, setActiveSources] = useState<EvidenceSource[]>([]);
  const [activeTurnNo, setActiveTurnNo] = useState<number | undefined>();

  // Explicit metadata scope for the next turn. Empty means "inherit the
  // assistant policy and the last completed turn", which is the backend rule.
  const [scopeOpen, setScopeOpen] = useState(false);
  const [filterDraft, setFilterDraft] = useState<MetadataFilterDraft>(
    EMPTY_METADATA_FILTER_DRAFT,
  );
  const filterErrors = validateMetadataFilterDraft(filterDraft);
  const hasFilterErrors = Object.keys(filterErrors).length > 0;
  const explicitFilter = hasFilterErrors ? {} : draftToFilter(filterDraft);
  const hasExplicitFilter = Object.keys(explicitFilter).length > 0;
  const fixedFilter = assistant?.rag_policy?.metadata_filter ?? {};

  // Changing a key the assistant policy pinned is rejected by the backend with
  // `conversation_scope_conflict`. Surface it here instead of failing the turn.
  const scopeConflicts = Object.keys(explicitFilter).filter((key) => {
    const pinned = fixedFilter[key as keyof MetadataFilter];
    if (pinned === undefined || pinned === null) return false;
    return (
      String(pinned) !== String(explicitFilter[key as keyof MetadataFilter])
    );
  });

  // Attempt tracking for idempotency & retry
  const [lastAttempt, setLastAttempt] = useState<{
    key: string;
    question: string;
    expected_turn_no: number;
    metadata_filter: MetadataFilter | null;
  } | null>(null);

  // Polling for running turn
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const [pollingTurnId, setPollingTurnId] = useState<string | null>(null);

  // Scroll container ref
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);

  // Handle scroll to detect if user is near bottom
  const handleScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const threshold = 150;
    const isNearBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight <= threshold;
    isNearBottomRef.current = isNearBottom;
  };

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior,
      });
    }
  }, []);

  // Scroll to bottom on initial load
  useEffect(() => {
    if (turns.length > 0 && isNearBottomRef.current) {
      scrollToBottom("auto");
    }
  }, [turns.length, scrollToBottom]);

  // Clean polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, []);

  // Poll running turn if any
  useEffect(() => {
    const runningTurn = turns.find((t) => t.status === "running");
    if (runningTurn && runningTurn.id !== pollingTurnId) {
      setPollingTurnId(runningTurn.id);

      if (pollingRef.current) clearInterval(pollingRef.current);

      let attempts = 0;
      const maxAttempts = 15; // 30 seconds max polling

      pollingRef.current = setInterval(async () => {
        attempts += 1;
        try {
          const fresh = await getTurn(
            v1Client,
            workspaceId,
            conversationId,
            runningTurn.id,
          );
          if (fresh.status !== "running" || attempts >= maxAttempts) {
            if (pollingRef.current) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
            }
            setPollingTurnId(null);
            void queryClient.invalidateQueries({
              queryKey: conversationsQueryKeys.detail(
                sessionId,
                workspaceId,
                conversationId,
              ),
            });
          }
        } catch {
          if (attempts >= maxAttempts && pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
            setPollingTurnId(null);
          }
        }
      }, 2000);
    }
  }, [
    turns,
    conversationId,
    workspaceId,
    sessionId,
    queryClient,
    pollingTurnId,
  ]);

  // Handle send turn
  const handleSend = async (overrideAttempt?: {
    key: string;
    question: string;
    expected_turn_no: number;
    metadata_filter: MetadataFilter | null;
  }) => {
    if (!conversation) return;
    if (!overrideAttempt && hasFilterErrors) {
      setScopeOpen(true);
      toast.error("Hãy sửa năm trong phạm vi metadata trước khi gửi câu hỏi.");
      return;
    }
    if (conversation.status === "archived") {
      toast.error("Hội thoại đã lưu trữ. Hãy mở lại để tiếp tục trò chuyện.");
      return;
    }
    if (assistant && !assistant.is_active) {
      toast.error("Trợ lý AI đã tạm dừng hoạt động.");
      return;
    }

    const questionText = overrideAttempt
      ? overrideAttempt.question
      : question.trim();
    if (!questionText) return;
    if (questionText.length > 8000) {
      toast.error("Câu hỏi tối đa 8000 ký tự.");
      return;
    }

    // Sequence strictly from conversation.last_turn_no
    const expectedTurnNo = overrideAttempt
      ? overrideAttempt.expected_turn_no
      : conversation.last_turn_no;

    // Keep same key if retry, or generate new key for new intent
    const idempotencyKey = overrideAttempt
      ? overrideAttempt.key
      : generateIdempotencyKey();

    // A retry keeps the scope it was sent with; a new question uses the scope
    // currently shown in the composer. Never derived from an earlier answer.
    const attemptFilter = overrideAttempt
      ? overrideAttempt.metadata_filter
      : Object.keys(explicitFilter).length > 0
        ? explicitFilter
        : null;

    const attempt = {
      key: idempotencyKey,
      question: questionText,
      expected_turn_no: expectedTurnNo,
      metadata_filter: attemptFilter,
    };
    setLastAttempt(attempt);

    if (!overrideAttempt) {
      setQuestion(""); // clear input box
    }

    try {
      isNearBottomRef.current = true;
      const newTurn = await sendTurnMutation.mutateAsync({
        input: {
          question: questionText,
          expected_turn_no: expectedTurnNo,
          metadata_filter: attemptFilter,
        },
        idempotencyKey,
      });

      // Check if immediate running turn
      if (newTurn.status === "running") {
        setPollingTurnId(newTurn.id);
      }
      scrollToBottom();
    } catch (err) {
      if (err instanceof ApiProblemError) {
        toast.error(formatConversationError(err.code, err.message));
        if (err.code === "conversation_sequence_conflict") {
          // Re-fetch conversation to sync last_turn_no
          void queryClient.invalidateQueries({
            queryKey: conversationsQueryKeys.detail(
              sessionId,
              workspaceId,
              conversationId,
            ),
          });
        }
        if (err.code === "conversation_scope_conflict") {
          // The pinned scope rejected this filter: open the panel so the user can
          // see and correct it rather than retrying blindly.
          setScopeOpen(true);
        }
      } else {
        toast.error(
          "Không nhận được phản hồi từ máy chủ. Bạn có thể bấm Thử lại lượt hỏi này.",
        );
      }
    }
  };

  const handleOpenCitation = (statement: Statement, turn: TurnResponse) => {
    setActiveStatement(statement);
    setActiveSources(turn.result?.sources ?? []);
    setActiveTurnNo(turn.turn_no);
    setCitationOpen(true);
  };

  const handleRetryLast = (turn: TurnResponse) => {
    if (!conversation) return;
    if (lastAttempt && lastAttempt.question === turn.question) {
      void handleSend(lastAttempt);
    } else {
      // Re-send with turn's data. The scope comes from the turn itself when the
      // backend recorded one; otherwise it inherits, exactly like the first send.
      void handleSend({
        key: generateIdempotencyKey(),
        question: turn.question,
        expected_turn_no: conversation.last_turn_no,
        metadata_filter: turn.metadata_filter ?? null,
      });
    }
  };

  if (conversationQuery.isPending) {
    return (
      <div className="flex flex-col h-full p-6 space-y-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="flex-1 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (conversationQuery.isError || !conversation) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 space-y-4 text-center">
        <Alert variant="destructive" className="max-w-md">
          <AlertDescription>
            Không tìm thấy cuộc trò chuyện này hoặc bạn không có quyền truy cập.
          </AlertDescription>
        </Alert>
        {onBack && (
          <Button variant="outline" size="sm" onClick={onBack}>
            <ArrowLeft className="size-4 mr-2" /> Quay lại danh sách
          </Button>
        )}
      </div>
    );
  }

  const isArchived = conversation.status === "archived";
  const isAssistantInactive = assistant && !assistant.is_active;

  return (
    <div className="flex flex-col h-full bg-background min-h-0 relative">
      {/* 1. Chat Header */}
      <div className="border-b bg-card px-4 py-3 flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          {onBack && (
            <Button
              variant="ghost"
              size="icon"
              className="size-8 sm:hidden shrink-0"
              onClick={onBack}
              aria-label="Quay lại danh sách"
            >
              <ArrowLeft className="size-4" />
            </Button>
          )}

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-sm text-foreground truncate max-w-xs sm:max-w-md">
                {conversation.title}
              </h2>
              <Badge
                variant={isArchived ? "secondary" : "default"}
                className="text-[10px] shrink-0"
              >
                {isArchived ? "Đã lưu trữ" : "Đang hoạt động"}
              </Badge>
            </div>

            <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-0.5">
              <Link
                to="/workspaces/$workspaceId/assistants/$assistantId"
                params={{
                  workspaceId,
                  assistantId: conversation.assistant_id,
                }}
                className="hover:text-primary transition-colors flex items-center gap-1 truncate"
              >
                <Bot className="size-3 text-primary shrink-0" />
                <span>
                  {assistant?.name ||
                    `Trợ lý (${conversation.assistant_id.slice(0, 8)})`}
                </span>
                <span>(v{conversation.assistant_revision})</span>
              </Link>
              <span>•</span>
              <span className="font-mono">
                #{conversation.last_turn_no} lượt
              </span>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-1.5 shrink-0">
          <LifecycleActions
            workspaceId={workspaceId}
            kind="conversation"
            resourceId={conversationId}
            label={conversation.title}
            status={conversation.status}
            ownedConversation
          />
          {turns
            .filter((turn) => turn.status === "running")
            .map((turn) => (
              <LifecycleActions
                key={turn.id}
                workspaceId={workspaceId}
                kind="job"
                jobKind="turn"
                resourceId={turn.id}
                label={`Lượt hỏi #${turn.turn_no}`}
                ownedConversation
              />
            ))}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="size-8">
                <MoreVertical className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="text-xs">
              <DropdownMenuItem onClick={() => setRenameOpen(true)}>
                <Pencil className="size-3.5 mr-2" />
                Đổi tên cuộc trò chuyện
              </DropdownMenuItem>
              <DropdownMenuSeparator />
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* 2. Chat Notice Banner if Archived or Assistant Inactive */}
      {isArchived && (
        <div className="bg-muted/40 border-b px-4 py-2 flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Lock className="size-3.5" />
            <span>Hội thoại đã lưu trữ (chế độ chỉ đọc).</span>
          </div>
          <LifecycleActions
            workspaceId={workspaceId}
            kind="conversation"
            resourceId={conversationId}
            label={conversation.title}
            status="archived"
            ownedConversation
          />
        </div>
      )}

      {isAssistantInactive && !isArchived && (
        <div className="bg-warning/10 border-b border-warning/30 px-4 py-2 text-xs text-warning flex items-center gap-2">
          <Lock className="size-3.5" />
          <span>
            Trợ lý AI này đã tạm dừng hoạt động. Không thể gửi thêm câu hỏi mới.
          </span>
        </div>
      )}

      {/* 3. Messages Container */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto min-h-0 p-4 sm:p-6 space-y-2"
      >
        {/* Load earlier turns button if needed */}
        {turnsQuery.hasNextPage && (
          <div className="flex justify-center pb-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs h-7 gap-1"
              disabled={turnsQuery.isFetchingNextPage}
              onClick={() => void turnsQuery.fetchNextPage()}
            >
              <ChevronUp className="size-3" />
              Tải các lượt trước đó
            </Button>
          </div>
        )}

        {turnsQuery.isError ? (
          <Alert variant="destructive">
            <AlertDescription>
              Không tải được lịch sử hội thoại.
            </AlertDescription>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void turnsQuery.refetch()}
            >
              Tải lại
            </Button>
          </Alert>
        ) : turnsQuery.isPending ? (
          <Skeleton className="h-24 w-full" />
        ) : turns.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center p-6 space-y-3">
            <div className="size-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <Bot className="size-6" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                Bắt đầu cuộc trò chuyện
              </p>
              <p className="text-xs text-muted-foreground max-w-sm">
                Đặt câu hỏi liên quan đến tài liệu trong bộ sưu tập gắn với Trợ
                lý {assistant?.name || "AI"}.
              </p>
            </div>
          </div>
        ) : (
          turns.map((turn) => (
            <ChatMessageItem
              key={turn.id}
              turn={turn}
              onOpenCitation={handleOpenCitation}
              onRetry={handleRetryLast}
            />
          ))
        )}
      </div>

      {/* 4. Bottom Input Bar */}
      <div className="border-t bg-card p-3 sm:p-4 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleSend();
          }}
          className="flex flex-col gap-2"
        >
          {/*
            Explicit metadata scope for the next turn only. Left empty it inherits
            the assistant policy, which is the backend rule; the panel never
            pre-fills from an earlier answer.
          */}
          <Collapsible open={scopeOpen} onOpenChange={setScopeOpen}>
            <div className="flex items-center justify-between gap-2">
              <CollapsibleTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1.5 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
                  aria-expanded={scopeOpen}
                >
                  <SlidersHorizontal className="size-3.5" />
                  <span>Phạm vi metadata</span>
                  {hasFilterErrors ? (
                    <Badge variant="destructive" className="text-[10px]">
                      Cần sửa năm
                    </Badge>
                  ) : hasExplicitFilter ? (
                    <Badge variant="secondary" className="text-[10px]">
                      Đã đặt
                    </Badge>
                  ) : (
                    <span className="text-[10px] text-muted-foreground/80">
                      Theo trợ lý
                    </span>
                  )}
                </Button>
              </CollapsibleTrigger>

              {!isMetadataFilterDraftEmpty(filterDraft) ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
                  onClick={() => {
                    setFilterDraft(EMPTY_METADATA_FILTER_DRAFT);
                    setScopeOpen(false);
                  }}
                >
                  <X className="size-3" />
                  Bỏ phạm vi
                </Button>
              ) : null}
            </div>

            <CollapsibleContent>
              <div className="space-y-2.5 rounded-lg border bg-muted/20 px-3 py-3 mt-1.5">
                <p className="text-[11px] text-muted-foreground">
                  Chỉ áp dụng cho lượt hỏi tiếp theo. Để trống để dùng đúng phạm
                  vi đã cấu hình ở trợ lý.
                </p>

                <MetadataFilterFields
                  value={filterDraft}
                  onChange={setFilterDraft}
                  disabled={
                    isArchived ||
                    Boolean(isAssistantInactive) ||
                    sendTurnMutation.isPending
                  }
                  showHint={false}
                />

                {Object.keys(fixedFilter).length > 0 ? (
                  <p className="text-[11px] text-muted-foreground">
                    Phạm vi cố định từ trợ lý:{" "}
                    <span className="text-foreground">
                      {describeMetadataFilter(fixedFilter)}
                    </span>
                  </p>
                ) : null}

                {scopeConflicts.length > 0 ? (
                  <Alert variant="destructive" className="py-2">
                    <AlertTriangle className="size-4" />
                    <AlertDescription className="text-[11px]">
                      Trợ lý đã cố định {scopeConflicts.join(", ")}. Máy chủ sẽ
                      từ chối lượt hỏi nếu bạn đặt giá trị khác — hãy xoá các ô
                      này, hoặc đổi cấu hình trợ lý rồi mở hội thoại mới.
                    </AlertDescription>
                  </Alert>
                ) : null}
              </div>
            </CollapsibleContent>
          </Collapsible>

          <div className="relative flex items-end rounded-xl border bg-background shadow-xs focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-1">
            <Textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.nativeEvent.isComposing) return;
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
              disabled={
                isArchived ||
                Boolean(isAssistantInactive) ||
                sendTurnMutation.isPending
              }
              placeholder={
                isArchived
                  ? "Hội thoại đã lưu trữ. Mở lại để tiếp tục trò chuyện..."
                  : isAssistantInactive
                    ? "Trợ lý AI đã tạm dừng hoạt động..."
                    : "Nhập câu hỏi (Enter để gửi, Shift+Enter để xuống dòng)..."
              }
              rows={1}
              className="min-h-[48px] max-h-36 resize-none border-0 shadow-none focus-visible:ring-0 text-xs sm:text-sm py-3 px-3.5 pr-12 flex-1"
            />

            <Button
              type="submit"
              size="icon"
              disabled={
                !question.trim() ||
                hasFilterErrors ||
                isArchived ||
                Boolean(isAssistantInactive) ||
                sendTurnMutation.isPending
              }
              className="absolute right-2 bottom-2 size-8 rounded-lg"
              aria-label="Gửi câu hỏi"
            >
              {sendTurnMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <SendHorizontal className="size-4" />
              )}
            </Button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground px-1">
            <span className="truncate">
              Lượt #{conversation.last_turn_no + 1} • Nhấn Enter để gửi
              {hasExplicitFilter
                ? ` • ${describeMetadataFilter(explicitFilter)}`
                : ""}
            </span>
            <span className="shrink-0">{question.length}/8000 ký tự</span>
          </div>
        </form>
      </div>

      {/* Dialogs & Sheets */}
      <ConversationRenameDialog
        workspaceId={workspaceId}
        conversation={conversation}
        open={renameOpen}
        onOpenChange={setRenameOpen}
      />

      <CitationSheet
        open={citationOpen}
        onOpenChange={setCitationOpen}
        statement={activeStatement}
        sources={activeSources}
        turnNo={activeTurnNo}
        workspaceId={workspaceId}
        collectionId={assistant?.collection_id}
      />
    </div>
  );
}
