import { useNavigate } from "@tanstack/react-router";
import { Bot, MessageSquare } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ChatView } from "./chat-view";
import { ConversationCreateDialog } from "./conversation-create-dialog";
import { ConversationsSidebar } from "./conversations-sidebar";

export function ConversationsPage({
  workspaceId,
  conversationId,
}: {
  workspaceId: string;
  conversationId?: string;
}) {
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);

  const handleSelectConversation = (id: string) => {
    void navigate({
      to: "/workspaces/$workspaceId/conversations/$conversationId",
      params: { workspaceId, conversationId: id },
    });
  };

  const handleBackToList = () => {
    void navigate({
      to: "/workspaces/$workspaceId/conversations",
      params: { workspaceId },
    });
  };

  return (
    <div className="flex h-[calc(100vh-8.5rem)] sm:h-[calc(100vh-9.5rem)] rounded-xl border bg-card overflow-hidden shadow-2xs">
      {/* Left Sidebar: visible on desktop or when no conversation is selected on mobile */}
      <div
        className={`h-full ${
          conversationId ? "hidden sm:flex" : "flex w-full"
        }`}
      >
        <ConversationsSidebar
          workspaceId={workspaceId}
          selectedConversationId={conversationId}
          onSelectConversation={handleSelectConversation}
        />
      </div>

      {/* Right Content Area */}
      <div
        className={`flex-1 h-full min-w-0 ${
          conversationId ? "flex flex-col" : "hidden sm:flex flex-col"
        }`}
      >
        {conversationId ? (
          <ChatView
            key={conversationId}
            workspaceId={workspaceId}
            conversationId={conversationId}
            onBack={handleBackToList}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full p-8 text-center space-y-4">
            <div className="size-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
              <MessageSquare className="size-8" />
            </div>
            <div className="space-y-1.5 max-w-sm">
              <h3 className="text-base font-semibold text-foreground">
                Chọn cuộc trò chuyện
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Chọn một hội thoại từ danh sách bên trái hoặc tạo hội thoại mới
                để bắt đầu hỏi đáp với Trợ lý AI có dẫn nguồn.
              </p>
            </div>
            <Button
              size="sm"
              className="gap-2"
              onClick={() => setCreateOpen(true)}
            >
              <Bot className="size-4" />
              Tạo cuộc trò chuyện mới
            </Button>
          </div>
        )}
      </div>

      <ConversationCreateDialog
        workspaceId={workspaceId}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </div>
  );
}
