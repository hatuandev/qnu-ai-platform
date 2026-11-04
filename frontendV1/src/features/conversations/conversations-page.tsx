import { useNavigate } from "@tanstack/react-router";
import {
  BookOpen,
  Bot,
  CheckCircle2,
  MessageSquarePlus,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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
      {/* Left Sidebar: mobile takes full width when no conversation is selected; desktop is always bounded */}
      <div
        className={cn(
          "h-full shrink-0 border-r border-border",
          conversationId
            ? "hidden sm:flex sm:w-80 md:w-96"
            : "flex w-full sm:w-80 md:w-96",
        )}
      >
        <ConversationsSidebar
          workspaceId={workspaceId}
          selectedConversationId={conversationId}
          onSelectConversation={handleSelectConversation}
          onDeleteSelectedConversation={handleBackToList}
          hasActiveConversation={Boolean(conversationId)}
        />
      </div>

      {/* Right Content Area: takes remaining space with min-w-0 */}
      <div
        className={cn(
          "flex-1 h-full min-w-0 bg-background",
          conversationId ? "flex flex-col" : "hidden sm:flex flex-col",
        )}
      >
        {conversationId ? (
          <ChatView
            key={conversationId}
            workspaceId={workspaceId}
            conversationId={conversationId}
            onBack={handleBackToList}
          />
        ) : (
          <div className="flex-1 overflow-y-auto flex flex-col items-center justify-center p-6 sm:p-10 text-center">
            <div className="max-w-xl mx-auto flex flex-col items-center space-y-6">
              {/* Central Welcome Badge */}
              <div className="relative flex items-center justify-center size-16 sm:size-20 rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-xs">
                <Bot className="size-8 sm:size-10" />
                <span className="absolute -top-1 -right-1 flex size-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex rounded-full size-3 bg-primary" />
                </span>
              </div>

              {/* Title & Tagline */}
              <div className="space-y-2">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20 mb-1">
                  <Sparkles className="size-3.5" />
                  <span>Trợ lý AI QNU</span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
                  Hội thoại Trợ lý AI QNU
                </h2>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed max-w-md mx-auto">
                  Hỏi đáp thông minh với các Trợ lý AI của đơn vị. Mọi câu trả
                  lời đều được tra cứu từ tri thức và dẫn nguồn văn bản minh
                  chứng có thể kiểm chứng.
                </p>
              </div>

              {/* Single Primary CTA */}
              <div>
                <Button
                  size="default"
                  className="gap-2 px-5 font-medium shadow-xs"
                  onClick={() => setCreateOpen(true)}
                >
                  <MessageSquarePlus className="size-4" />
                  <span>Tạo cuộc trò chuyện mới</span>
                </Button>
              </div>

              {/* Trust & Evidence Pillars */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full pt-4 text-left">
                <div className="p-3.5 rounded-xl border border-border/80 bg-card/60 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                    <BookOpen className="size-3.5 text-primary" />
                    <span>Tri thức chuẩn hóa</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Dẫn xuất từ các văn bản ký số, quyết định và tài liệu đã bóc
                    tách.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-border/80 bg-card/60 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                    <ShieldCheck className="size-3.5 text-primary" />
                    <span>Dẫn chứng rõ ràng</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Mỗi câu trả lời đều gắn mã bằng chứng để đối chiếu ngay trên
                    tài liệu gốc.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-border/80 bg-card/60 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                    <CheckCircle2 className="size-3.5 text-primary" />
                    <span>Kiểm chứng độc lập</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Tự động đánh giá tính xác thực và báo rõ khi chưa đủ căn cứ
                    chứng minh.
                  </p>
                </div>
              </div>
            </div>
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
