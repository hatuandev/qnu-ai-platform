import {
  Check,
  ChevronDown,
  FileQuestion,
  FlaskConical,
  History,
  ListFilter,
  Loader2,
  RefreshCw,
  ScrollText,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import {
  type Conversation,
  type ConversationTurn,
  type TurnStatus,
  useAssistantConversationsQuery,
  useConversationTurnsQuery,
  usePromoteTurnToBenchmarkMutation,
} from "@/api/conversations";
import { EmptyState } from "@/components/admin/empty-state";
import { TurnFeedback } from "@/components/assistants/turn-feedback";
import { TurnResult } from "@/components/assistants/turn-result";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type TurnFilterType =
  | "all"
  | "insufficient_evidence"
  | "failed"
  | "dislike";

const FILTER_OPTIONS: {
  id: TurnFilterType;
  label: string;
  icon: typeof ListFilter;
}[] = [
  { id: "all", label: "Tất cả", icon: ListFilter },
  { id: "insufficient_evidence", label: "Thiếu dẫn chứng", icon: FileQuestion },
  { id: "failed", label: "Lỗi", icon: XCircle },
  { id: "dislike", label: "Bị Dislike", icon: ThumbsDown },
];

function matchesTurnFilter(
  turn: ConversationTurn,
  filter: TurnFilterType,
): boolean {
  if (filter === "all") return true;
  if (filter === "insufficient_evidence") {
    return (
      turn.result != null && turn.result.status === "insufficient_evidence"
    );
  }
  if (filter === "failed") {
    return turn.status === "failed";
  }
  if (filter === "dislike") {
    return turn.feedback?.rating === "dislike";
  }
  return true;
}

const TURN_STATUS_MAP: Record<
  TurnStatus,
  {
    label: string;
    variant: "success" | "warning" | "destructive" | "secondary" | "info";
  }
> = {
  running: { label: "Đang chạy", variant: "info" },
  completed: { label: "Hoàn tất", variant: "success" },
  failed: { label: "Lỗi", variant: "destructive" },
  uncertain: { label: "Chưa xác định", variant: "warning" },
  cancelled: { label: "Đã hủy", variant: "secondary" },
};

function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return date.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatDuration(turn: ConversationTurn): string | null {
  if (!turn.finished_at) return null;
  const started = new Date(turn.created_at).getTime();
  const finished = new Date(turn.finished_at).getTime();
  if (Number.isNaN(started) || Number.isNaN(finished)) return null;
  const totalSeconds = Math.max(1, Math.round((finished - started) / 1000));
  if (totalSeconds < 60) return `${totalSeconds} giây`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes} phút ${seconds} giây`;
}

function TurnMeta({ turn }: { turn: ConversationTurn }) {
  const result = turn.result;
  if (!result || result.status === "direct_reply") return null;
  const parts: string[] = [];
  if (result.trace.model_name) parts.push(result.trace.model_name);
  if (result.trace.total_tokens != null) {
    parts.push(`${result.trace.total_tokens.toLocaleString("vi-VN")} token`);
  }
  const duration = formatDuration(turn);
  if (duration) parts.push(duration);
  if (parts.length === 0) return null;
  return (
    <p className="text-[11px] text-muted-foreground">{parts.join(" · ")}</p>
  );
}

function PromoteToBenchmarkButton({
  workspaceId,
  conversationId,
  turn,
  isProblematic,
}: {
  workspaceId: string;
  conversationId: string;
  turn: ConversationTurn;
  isProblematic: boolean;
}) {
  const [promotedId, setPromotedId] = useState<string | null>(null);
  const promoteMutation = usePromoteTurnToBenchmarkMutation(workspaceId);

  const handlePromote = () => {
    if (promoteMutation.isPending || promotedId) return;
    promoteMutation.mutate(
      {
        conversationId,
        turnId: turn.id,
      },
      {
        onSuccess: (data) => {
          setPromotedId(data.question_id);
          if (data.already_exists) {
            toast.info(`Câu hỏi này đã có trong bộ đề (${data.question_id}).`);
          } else {
            toast.success(
              `Đã đưa câu hỏi vào bộ đề (${data.question_id}, tổng ${data.total_questions} câu) thành công!`,
            );
          }
        },
        onError: () => {
          toast.error("Không thể đưa câu hỏi vào bộ đề kiểm thử.");
        },
      },
    );
  };

  if (promotedId) {
    return (
      <Badge
        variant="outline"
        className="h-6 gap-1 px-2 text-[10px] font-normal text-primary border-primary/30 bg-primary/5"
        title="Đã lưu trong bộ đề kiểm thử"
      >
        <Check className="size-3 text-primary" />
        <span>Bộ đề ({promotedId})</span>
      </Badge>
    );
  }

  return (
    <Button
      type="button"
      variant={isProblematic ? "outline" : "ghost"}
      size="sm"
      className={cn(
        "h-6 gap-1 px-2 text-[10px] cursor-pointer",
        isProblematic
          ? "border-primary/30 text-primary hover:bg-primary/10 shadow-2xs font-medium"
          : "text-muted-foreground hover:text-foreground",
      )}
      onClick={handlePromote}
      disabled={promoteMutation.isPending}
      title={
        isProblematic
          ? "Đưa câu hỏi lỗi / cần cải thiện này vào bộ đề kiểm thử để đánh giá hồi quy"
          : "Đưa câu hỏi này vào bộ đề kiểm thử"
      }
    >
      {promoteMutation.isPending ? (
        <Loader2 className="size-3 animate-spin shrink-0" />
      ) : (
        <FlaskConical className="size-3 shrink-0" />
      )}
      <span>{isProblematic ? "+ Bộ đề kiểm thử" : "+ Bộ đề"}</span>
    </Button>
  );
}

function TurnLogEntry({
  turn,
  workspaceId,
  conversationId,
}: {
  turn: ConversationTurn;
  workspaceId: string;
  conversationId: string;
}) {
  const status = TURN_STATUS_MAP[turn.status] ?? {
    label: turn.status,
    variant: "secondary" as const,
  };
  const isProblematic =
    turn.status === "failed" ||
    (turn.result != null && turn.result.status === "insufficient_evidence") ||
    turn.feedback?.rating === "dislike";

  return (
    <div className="rounded-lg border border-border/60">
      <div className="flex items-start justify-between gap-3 border-b border-border/50 px-3 py-2">
        <div className="flex min-w-0 items-start gap-2">
          <span className="mt-0.5 shrink-0 font-mono text-[11px] text-muted-foreground">
            #{turn.turn_no}
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium leading-relaxed text-foreground">
              {turn.question}
            </p>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              {formatDateTime(turn.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {turn.feedback?.rating === "dislike" ? (
            <Badge
              variant="destructive"
              className="h-4 px-1.5 text-[10px] font-normal gap-1"
              title={turn.feedback.reason ?? "Cần cải thiện"}
            >
              <ThumbsDown className="size-2.5" />
              <span>Bị Dislike</span>
            </Badge>
          ) : turn.feedback?.rating === "like" ? (
            <Badge
              variant="success"
              className="h-4 px-1.5 text-[10px] font-normal gap-1"
            >
              <ThumbsUp className="size-2.5" />
              <span>Hữu ích</span>
            </Badge>
          ) : null}
          <Badge
            variant={status.variant}
            className="h-4 px-1.5 text-[10px] font-normal"
          >
            {status.label}
          </Badge>
        </div>
      </div>
      <div className="space-y-3 px-3 py-2.5">
        <TurnResult turn={turn} />
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/40 pt-1.5">
          <TurnMeta turn={turn} />
          <div className="flex items-center gap-1.5">
            <PromoteToBenchmarkButton
              workspaceId={workspaceId}
              conversationId={conversationId}
              turn={turn}
              isProblematic={isProblematic}
            />
            <TurnFeedback
              turnId={turn.id}
              workspaceId={workspaceId}
              conversationId={conversationId}
              initialFeedback={turn.feedback}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function ConversationTurns({
  workspaceId,
  conversationId,
  filter,
}: {
  workspaceId: string;
  conversationId: string;
  filter: TurnFilterType;
}) {
  const {
    data: turns,
    isError,
    refetch,
  } = useConversationTurnsQuery(workspaceId, conversationId);

  const filteredTurns = useMemo(() => {
    if (!turns) return [];
    if (filter === "all") return turns;
    return turns.filter((turn) => matchesTurnFilter(turn, filter));
  }, [turns, filter]);

  if (isError) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-md border border-dashed border-border/70 px-3 py-2">
        <p className="text-xs text-muted-foreground">
          Không tải được các lượt hỏi của hội thoại này.
        </p>
        <Button
          variant="outline"
          size="sm"
          className="h-7 shrink-0 gap-1.5 text-[11px]"
          onClick={() => void refetch()}
        >
          <RefreshCw className="size-3.5" />
          <span>Tải lại</span>
        </Button>
      </div>
    );
  }

  if (!turns) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-16 w-full rounded-lg" />
        <Skeleton className="h-16 w-full rounded-lg" />
      </div>
    );
  }

  if (turns.length === 0) {
    return (
      <p className="px-1 text-xs text-muted-foreground">
        Hội thoại chưa có lượt hỏi nào.
      </p>
    );
  }

  if (filteredTurns.length === 0) {
    return (
      <p className="px-1 py-1.5 text-xs text-muted-foreground italic">
        Không có lượt hỏi nào trong hội thoại này khớp với bộ lọc đã chọn.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {filteredTurns.map((turn) => (
        <TurnLogEntry
          key={turn.id}
          turn={turn}
          workspaceId={workspaceId}
          conversationId={conversationId}
        />
      ))}
    </div>
  );
}

function ConversationLogCard({
  workspaceId,
  conversation,
  filter,
}: {
  workspaceId: string;
  conversation: Conversation;
  filter: TurnFilterType;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const isArchived = conversation.status === "archived";

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className="rounded-lg border border-border/60"
    >
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          className="group h-auto w-full justify-between gap-3 rounded-lg px-3 py-2.5 text-left hover:bg-muted/40 cursor-pointer"
        >
          <span className="flex min-w-0 flex-1 items-center gap-2">
            <History className="size-4 shrink-0 text-muted-foreground" />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-foreground">
                {conversation.title}
              </span>
              <span className="block text-[11px] text-muted-foreground">
                {conversation.last_turn_no} lượt hỏi · Cập nhật{" "}
                {formatDateTime(conversation.updated_at)}
              </span>
            </span>
            <Badge
              variant={isArchived ? "secondary" : "outline"}
              className="h-4 shrink-0 px-1.5 text-[10px] font-normal text-muted-foreground"
            >
              {isArchived ? "Đã lưu trữ" : "Đang mở"}
            </Badge>
          </span>
          <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="border-t border-border/50 p-3">
          {isOpen ? (
            <ConversationTurns
              workspaceId={workspaceId}
              conversationId={conversation.id}
              filter={filter}
            />
          ) : null}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function AssistantLogs({
  workspaceId,
  assistantId,
}: {
  workspaceId: string;
  assistantId: string;
}) {
  const [activeFilter, setActiveFilter] = useState<TurnFilterType>("all");

  const {
    data: conversations,
    isError,
    isFetching,
    refetch,
  } = useAssistantConversationsQuery(workspaceId, assistantId);

  if (isError) {
    return (
      <EmptyState
        icon={ScrollText}
        title="Không tải được nhật ký hỏi đáp"
        description="Kết nối tới máy chủ không thành công hoặc phiên đăng nhập đã hết hạn."
        action={{ label: "Tải lại", onClick: () => void refetch() }}
      />
    );
  }

  if (!conversations) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-14 w-full rounded-lg" />
        <Skeleton className="h-14 w-full rounded-lg" />
        <Skeleton className="h-14 w-full rounded-lg" />
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <EmptyState
        icon={ScrollText}
        title="Chưa có nhật ký hỏi đáp"
        description="Nhật ký ghi lại các hội thoại của bạn với trợ lý. Khi bạn đặt câu hỏi qua giao diện trò chuyện, từng lượt hỏi và câu trả lời sẽ xuất hiện tại đây."
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-border/60 bg-muted/20 p-1">
          {FILTER_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const isActive = activeFilter === opt.id;
            return (
              <Button
                key={opt.id}
                type="button"
                variant={isActive ? "secondary" : "ghost"}
                size="sm"
                className={cn(
                  "h-7 gap-1.5 px-2.5 text-xs font-normal transition-colors cursor-pointer",
                  isActive &&
                    "bg-background font-medium text-foreground shadow-2xs border border-border/60",
                )}
                onClick={() => setActiveFilter(opt.id)}
              >
                <Icon
                  className={cn(
                    "size-3.5",
                    isActive ? "text-primary" : "text-muted-foreground",
                  )}
                />
                <span>{opt.label}</span>
              </Button>
            );
          })}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 self-start gap-1.5 px-2 text-[11px] text-muted-foreground"
          onClick={() => void refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={cn("size-3.5", isFetching && "animate-spin")} />
          <span>Tải lại</span>
        </Button>
      </div>
      {conversations.map((conversation) => (
        <ConversationLogCard
          key={conversation.id}
          workspaceId={workspaceId}
          conversation={conversation}
          filter={activeFilter}
        />
      ))}
    </div>
  );
}
