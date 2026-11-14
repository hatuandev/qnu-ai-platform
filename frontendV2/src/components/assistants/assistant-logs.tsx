import { ChevronDown, History, RefreshCw, ScrollText } from "lucide-react";
import { useState } from "react";
import {
  type Conversation,
  type ConversationTurn,
  type TurnStatus,
  useAssistantConversationsQuery,
  useConversationTurnsQuery,
} from "@/api/conversations";
import { EmptyState } from "@/components/admin/empty-state";
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

function TurnLogEntry({ turn }: { turn: ConversationTurn }) {
  const status = TURN_STATUS_MAP[turn.status] ?? {
    label: turn.status,
    variant: "secondary" as const,
  };
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
        <Badge
          variant={status.variant}
          className="h-4 shrink-0 px-1.5 text-[10px] font-normal"
        >
          {status.label}
        </Badge>
      </div>
      <div className="space-y-3 px-3 py-2.5">
        <TurnResult turn={turn} />
        <TurnMeta turn={turn} />
      </div>
    </div>
  );
}

function ConversationTurns({
  workspaceId,
  conversationId,
}: {
  workspaceId: string;
  conversationId: string;
}) {
  const {
    data: turns,
    isError,
    refetch,
  } = useConversationTurnsQuery(workspaceId, conversationId);

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

  return (
    <div className="space-y-2">
      {turns.map((turn) => (
        <TurnLogEntry key={turn.id} turn={turn} />
      ))}
    </div>
  );
}

function ConversationLogCard({
  workspaceId,
  conversation,
}: {
  workspaceId: string;
  conversation: Conversation;
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
          className="group h-auto w-full justify-between gap-3 rounded-lg px-3 py-2.5 text-left hover:bg-muted/40"
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
        <p className="text-xs text-muted-foreground">
          Hội thoại của bạn với trợ lý · 20 hội thoại gần nhất
        </p>
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
        />
      ))}
    </div>
  );
}
