import { useNavigate } from "@tanstack/react-router";
import {
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  MessageSquarePlus,
  Search,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { ConversationCreateDialog } from "./conversation-create-dialog";
import { ConversationRenameDialog } from "./conversation-rename-dialog";
import { useConversationsQuery } from "./queries";
import type { Conversation, ConversationStatus } from "./types";

export function ConversationsSidebar({
  workspaceId,
  selectedConversationId,
  onSelectConversation,
  onDeleteSelectedConversation,
  hasActiveConversation = false,
}: {
  workspaceId: string;
  selectedConversationId?: string;
  onSelectConversation?: (conversationId: string) => void;
  onDeleteSelectedConversation?: () => void;
  hasActiveConversation?: boolean;
}) {
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const conversationsQuery = useConversationsQuery(workspaceId, {
    limit,
    offset,
  });

  const rawConversations = conversationsQuery.data ?? [];

  // Filter state
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | ConversationStatus>(
    "all",
  );

  // Dialog states
  const [createOpen, setCreateOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<Conversation | null>(null);

  // Client-side filtering of loaded conversations
  const filteredConversations = rawConversations.filter((c) => {
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    if (search.trim()) {
      return c.title.toLowerCase().includes(search.trim().toLowerCase());
    }
    return true;
  });

  const handleSelect = (id: string) => {
    if (onSelectConversation) {
      onSelectConversation(id);
    } else {
      void navigate({
        to: "/workspaces/$workspaceId/conversations/$conversationId",
        params: { workspaceId, conversationId: id },
      });
    }
  };

  return (
    <aside className="flex flex-col h-full bg-card shrink-0 w-full select-none">
      {/* Header & Create Button */}
      <div className="p-3.5 border-b space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <MessageSquare className="size-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">
              Cuộc trò chuyện
            </h2>
          </div>
          <Button
            size="sm"
            variant={hasActiveConversation ? "default" : "outline"}
            onClick={() => setCreateOpen(true)}
            className="h-8 gap-1.5 text-xs font-medium"
          >
            <MessageSquarePlus className="size-3.5" />
            <span>Mới</span>
          </Button>
        </div>

        {/* Search bar */}
        <div className="relative">
          <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo tiêu đề..."
            className="h-8 pl-8 text-xs bg-background"
          />
        </div>

        {/* Status Filter tabs */}
        <div className="flex items-center rounded-lg bg-muted/50 p-0.5 text-xs">
          <button
            type="button"
            onClick={() => setStatusFilter("all")}
            className={cn(
              "flex-1 py-1 rounded-md text-[11px] font-medium transition-colors text-center cursor-pointer",
              statusFilter === "all"
                ? "bg-background text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Tất cả
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter("active")}
            className={cn(
              "flex-1 py-1 rounded-md text-[11px] font-medium transition-colors text-center cursor-pointer",
              statusFilter === "active"
                ? "bg-background text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Đang mở
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter("archived")}
            className={cn(
              "flex-1 py-1 rounded-md text-[11px] font-medium transition-colors text-center cursor-pointer",
              statusFilter === "archived"
                ? "bg-background text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Lưu trữ
          </button>
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto min-h-0 divide-y">
        {conversationsQuery.isPending ? (
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="p-8 text-center space-y-2 text-muted-foreground">
            <MessageSquare className="size-8 mx-auto text-muted-foreground/40" />
            <p className="text-xs font-medium text-foreground">
              {search.trim()
                ? "Không tìm thấy hội thoại phù hợp"
                : statusFilter === "archived"
                  ? "Chưa có hội thoại nào được lưu trữ"
                  : "Chưa có cuộc trò chuyện nào"}
            </p>
            <p className="text-[11px]">
              {search.trim()
                ? "Thử tìm kiếm với từ khóa khác"
                : "Tạo cuộc trò chuyện mới để bắt đầu hỏi đáp"}
            </p>
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const isSelected = conv.id === selectedConversationId;
            return (
              <div
                key={conv.id}
                className={cn(
                  "p-3 text-left transition-colors group flex items-start justify-between gap-2",
                  isSelected
                    ? "bg-primary/10 text-primary border-l-3 border-l-primary"
                    : "hover:bg-muted/40 text-foreground",
                )}
              >
                <button
                  type="button"
                  onClick={() => handleSelect(conv.id)}
                  className="min-w-0 flex-1 space-y-1 text-left cursor-pointer focus-visible:outline-none"
                >
                  <div className="flex items-center gap-1.5">
                    <p
                      className={cn(
                        "text-xs font-medium truncate",
                        isSelected
                          ? "text-primary font-semibold"
                          : "text-foreground",
                      )}
                    >
                      {conv.title}
                    </p>
                    {conv.status === "archived" && (
                      <Badge
                        variant="secondary"
                        className="text-[9px] px-1 py-0 h-4 shrink-0"
                      >
                        Lưu trữ
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span>{formatDateTimeValue(conv.updated_at)}</span>
                    <span>•</span>
                    <span className="font-mono">{conv.last_turn_no} lượt</span>
                  </div>
                </button>

                <LifecycleActions
                  workspaceId={workspaceId}
                  kind="conversation"
                  resourceId={conv.id}
                  label={conv.title}
                  status={conv.status}
                  ownedConversation
                  compact
                  onRename={() => setRenameTarget(conv)}
                  onDeleted={
                    isSelected ? onDeleteSelectedConversation : undefined
                  }
                />
              </div>
            );
          })
        )}
      </div>

      {/* Pagination Footer (honest limit & offset) */}
      <div className="border-t bg-muted/20 px-3 py-2 flex items-center justify-between text-[11px] text-muted-foreground">
        <span>
          Đang xem {offset + 1}–{offset + rawConversations.length}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="size-6"
            disabled={offset === 0}
            onClick={() => setOffset((prev) => Math.max(0, prev - limit))}
          >
            <ChevronLeft className="size-3" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="size-6"
            disabled={rawConversations.length < limit}
            onClick={() => setOffset((prev) => prev + limit)}
          >
            <ChevronRight className="size-3" />
          </Button>
        </div>
      </div>

      {/* Dialogs */}
      <ConversationCreateDialog
        workspaceId={workspaceId}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      {renameTarget && (
        <ConversationRenameDialog
          workspaceId={workspaceId}
          conversation={renameTarget}
          open={Boolean(renameTarget)}
          onOpenChange={(open) => {
            if (!open) setRenameTarget(null);
          }}
        />
      )}
    </aside>
  );
}
