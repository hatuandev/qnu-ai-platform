import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { downloadMarkdownFile } from "@/lib/export-markdown";
import { cn } from "@/lib/utils";
import { conversationsApi } from "@/services/conversations-api";
import type {
  ConversationStatus,
  ConversationThreadDetail,
  ConversationThreadItem,
} from "@/types/conversations";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock,
  CornerDownLeft,
  Download,
  GraduationCap,
  Headphones,
  Library,
  MessageSquare,
  RefreshCw,
  Send,
  ShieldCheck,
  User,
  UserCheck,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

const CANNED_REPLIES = [
  "Chào bạn! Cán bộ phụ trách đang kiểm tra hồ sơ và sẽ phản hồi trong giây lát.",
  "Bạn vui lòng cung cấp số CCCD hoặc mã hồ sơ để cán bộ tra cứu chi tiết nhé.",
  "Nội dung này thuộc thẩm quyền Phòng Đào tạo (Tầng 1 Nhà A1), hotline 0256.3846.156.",
  "Cảm ơn bạn đã liên hệ. Vấn đề của bạn đã được giải quyết xong!",
];

export const ConversationsPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [selectedThreadId, setSelectedThreadId] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [staffName, setStaffName] = useState<string>("Cán bộ QNU");
  const [replyText, setReplyText] = useState<string>("");

  // Fetch threads list with 8s polling
  const threadsQuery = useQuery({
    queryKey: ["conversations-list", statusFilter, searchQuery],
    queryFn: () =>
      conversationsApi.listConversations({
        status: statusFilter === "all" ? undefined : statusFilter,
        search: searchQuery || undefined,
      }),
    refetchInterval: 8_000,
  });

  const threads = threadsQuery.data || [];

  // Automatically select first thread if none selected
  useEffect(() => {
    if (!selectedThreadId && threads.length > 0) {
      setSelectedThreadId(threads[0].id);
    } else if (selectedThreadId && !threads.some((t) => t.id === selectedThreadId)) {
      if (threads.length > 0) {
        setSelectedThreadId(threads[0].id);
      }
    }
  }, [threads, selectedThreadId]);

  // Fetch selected thread detail
  const threadDetailQuery = useQuery({
    queryKey: ["conversation-detail", selectedThreadId],
    queryFn: () => conversationsApi.getConversationDetail(selectedThreadId),
    enabled: Boolean(selectedThreadId),
    refetchInterval: 5_000,
  });

  const activeThread: ConversationThreadDetail | undefined = threadDetailQuery.data;

  // Mutation: Reply
  const replyMutation = useMutation({
    mutationFn: (text: string) =>
      conversationsApi.replyConversation(selectedThreadId, {
        text,
        staff_name: staffName.trim() || "Cán bộ QNU",
      }),
    onSuccess: () => {
      setReplyText("");
      queryClient.invalidateQueries({ queryKey: ["conversation-detail", selectedThreadId] });
      queryClient.invalidateQueries({ queryKey: ["conversations-list"] });
      toast.success("Đã gửi phản hồi trực tiếp tới người học!");
    },
    onError: (err: Error) => toast.error(`Gửi phản hồi thất bại: ${err.message}`),
  });

  // Mutation: Status update (Claim / Handback / Resolve)
  const statusMutation = useMutation({
    mutationFn: ({ status, assigned_to }: { status: ConversationStatus; assigned_to?: string }) =>
      conversationsApi.updateConversationStatus(selectedThreadId, {
        status,
        assigned_to,
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["conversation-detail", selectedThreadId] });
      queryClient.invalidateQueries({ queryKey: ["conversations-list"] });
      const labels: Record<ConversationStatus, string> = {
        ai_active: "Đã chuyển lại quyền điều phối cho Trợ lý AI",
        staff_claimed: `Cán bộ ${updated.assigned_to || staffName} đã tiếp nhận phiên hỗ trợ`,
        handoff_requested: "Đã đánh dấu yêu cầu cán bộ tiếp quản",
        resolved: "Đã đánh dấu phiên trao đổi hoàn tất (Resolved)",
      };
      toast.success(labels[updated.status] || "Đã cập nhật trạng thái hội thoại.");
    },
    onError: (err: Error) => toast.error(`Cập nhật trạng thái thất bại: ${err.message}`),
  });

  const handleSendReply = (e?: React.SyntheticEvent) => {
    if (e) e.preventDefault();
    if (!replyText.trim() || replyMutation.isPending) return;
    replyMutation.mutate(replyText.trim());
  };

  const handleExportThreadMarkdown = () => {
    if (!activeThread || activeThread.messages.length === 0) {
      toast.info("Chưa có tin nhắn nào trong phiên hội thoại này.");
      return;
    }
    const lines: string[] = [];
    lines.push(`# Phiên Hội Thoại — ${activeThread.user_name}`);
    lines.push("");
    lines.push(
      `- **Người học**: ${activeThread.user_name}${
        activeThread.user_email ? ` <${activeThread.user_email}>` : ""
      }`
    );
    lines.push(
      `- **Trợ lý tiếp nhận**: ${activeThread.assistant_name} (\`${activeThread.assistant_code}\`)`
    );
    lines.push(`- **Trạng thái**: ${activeThread.status}`);
    if (activeThread.assigned_to) {
      lines.push(`- **Cán bộ phụ trách**: ${activeThread.assigned_to}`);
    }
    lines.push(`- **Thời gian xuất**: ${new Date().toLocaleString("vi-VN")}`);
    lines.push("");
    lines.push("---");
    lines.push("");

    activeThread.messages.forEach((msg, idx) => {
      const timeStr = msg.created_at ? new Date(msg.created_at).toLocaleTimeString("vi-VN") : "";
      const senderLabel =
        msg.sender === "user"
          ? `👤 Người dùng (${activeThread.user_name})`
          : msg.sender === "agent"
            ? `👨‍💼 Cán bộ hỗ trợ (${activeThread.assigned_to || "Cán bộ QNU"})`
            : `🎓 Trợ lý AI (${activeThread.assistant_name})`;

      lines.push(`### [Lượt ${idx + 1}] ${senderLabel} ${timeStr ? `(${timeStr})` : ""}`);
      lines.push("");
      lines.push(msg.text.trim());
      lines.push("");
      lines.push("---");
      lines.push("");
    });

    lines.push(
      "> *Tệp được xuất tự động từ Nền tảng AI Trường Đại học Quy Nhơn (QNU AI Platform).*"
    );
    lines.push("");

    const dateStr = new Date().toISOString().slice(0, 10);
    const filename = `hoi_thoai_${activeThread.id}_${dateStr}.md`;
    downloadMarkdownFile(filename, lines.join("\n"));
    toast.success(`Đã xuất tệp Markdown "${filename}" thành công!`);
  };

  const handoffCount = useMemo(() => {
    return threads.filter((t) => t.status === "handoff_requested").length;
  }, [threads]);

  const getAssistantIcon = (code: string) => {
    switch (code) {
      case "admissions":
        return <GraduationCap className="size-3.5 text-success" />;
      case "regulations":
        return <ShieldCheck className="size-3.5 text-info" />;
      case "library":
        return <Library className="size-3.5 text-warning" />;
      default:
        return <Bot className="size-3.5 text-primary" />;
    }
  };

  const getStatusBadge = (status: ConversationStatus) => {
    switch (status) {
      case "handoff_requested":
        return (
          <Badge variant="destructive" className="text-[10px] gap-1 animate-pulse">
            <AlertTriangle className="size-3" />
            Cần tiếp quản
          </Badge>
        );
      case "staff_claimed":
        return (
          <Badge
            variant="outline"
            className="text-[10px] gap-1 bg-info/10 text-info border-info/30"
          >
            <UserCheck className="size-3" />
            Cán bộ hỗ trợ
          </Badge>
        );
      case "resolved":
        return (
          <Badge
            variant="outline"
            className="text-[10px] gap-1 bg-success/10 text-success border-success/30"
          >
            <CheckCircle2 className="size-3" />
            Đã giải quyết
          </Badge>
        );
      default:
        return (
          <Badge
            variant="outline"
            className="text-[10px] gap-1 bg-primary/10 text-primary border-primary/30"
          >
            <Bot className="size-3" />
            AI đang xử lý
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        eyebrow="Hội Thoại / Giám Sát Nhân Sự"
        title={
          <span className="inline-flex items-center gap-2">
            Giám Sát Hội Thoại & Bàn Giao Nhân Sự (Staff Handoff)
            {handoffCount > 0 && (
              <Badge variant="destructive" className="animate-pulse">
                {handoffCount} yêu cầu cần hỗ trợ
              </Badge>
            )}
          </span>
        }
        description="Theo dõi các phiên trao đổi thời gian thực giữa người học và Trợ lý AI ĐH Quy Nhơn. Cán bộ có thể can thiệp 1-click khi câu hỏi vượt quá phạm vi tri thức."
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              threadsQuery.refetch();
              if (selectedThreadId) threadDetailQuery.refetch();
            }}
            disabled={threadsQuery.isFetching}
            className="gap-1.5"
          >
            <RefreshCw className={cn("size-3.5", threadsQuery.isFetching && "animate-spin")} />
            <span>Làm mới</span>
          </Button>
        }
      />

      {/* Main 2-Column Master-Detail Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[22rem_1fr] gap-4 min-h-[680px]">
        {/* Left Column: Threads Master List */}
        <Card className="flex flex-col border border-border overflow-hidden">
          {/* Search & Status Filter */}
          <div className="p-3 border-b border-border space-y-2 bg-muted/20">
            <DebouncedSearchInput
              placeholder="Tìm thí sinh, sinh viên, nội dung..."
              value={searchQuery}
              onChange={setSearchQuery}
              className="h-8 text-xs"
            />

            {/* Filter Tabs */}
            <div className="flex items-center gap-1 overflow-x-auto pb-1 text-[11px]">
              {[
                { id: "all", label: "Tất cả" },
                { id: "handoff_requested", label: `Cần tiếp quản (${handoffCount})` },
                { id: "staff_claimed", label: "Cán bộ" },
                { id: "ai_active", label: "AI xử lý" },
                { id: "resolved", label: "Đã xong" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setStatusFilter(tab.id)}
                  className={cn(
                    "px-2.5 py-1 rounded-md whitespace-nowrap transition-colors font-medium",
                    statusFilter === tab.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted/60 text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Threads List */}
          <div className="flex-1 overflow-y-auto divide-y divide-border/60">
            {threadsQuery.isLoading ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                <RefreshCw className="size-5 animate-spin mx-auto mb-2 text-primary" />
                <span>Đang đồng bộ danh sách hội thoại...</span>
              </div>
            ) : threads.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                <MessageSquare className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                <p className="font-medium text-foreground">Không có hội thoại nào</p>
                <p className="text-[11px] mt-1">
                  Không tìm thấy phiên trò chuyện phù hợp với bộ lọc hiện tại.
                </p>
              </div>
            ) : (
              threads.map((thread: ConversationThreadItem) => {
                const isSelected = thread.id === selectedThreadId;
                return (
                  <button
                    type="button"
                    key={thread.id}
                    onClick={() => setSelectedThreadId(thread.id)}
                    className={cn(
                      "w-full text-left p-3 transition-colors flex flex-col gap-1.5",
                      isSelected ? "bg-primary/10 border-l-2 border-primary" : "hover:bg-muted/40"
                    )}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-semibold text-xs text-foreground truncate">
                        {thread.user_name}
                      </span>
                      {getStatusBadge(thread.status)}
                    </div>

                    <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                      {getAssistantIcon(thread.assistant_code)}
                      <span className="truncate">{thread.assistant_name}</span>
                      <span className="ml-auto shrink-0 flex items-center gap-1 text-[10px]">
                        <Clock className="size-2.5" />
                        {thread.updated_at
                          ? new Date(thread.updated_at).toLocaleTimeString("vi-VN", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "Vừa xong"}
                      </span>
                    </div>

                    <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                      {thread.last_message}
                    </p>
                  </button>
                );
              })
            )}
          </div>
        </Card>

        {/* Right Column: Active Conversation Desk & Live Messages */}
        <Card className="flex flex-col border border-border overflow-hidden">
          {!activeThread ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-muted-foreground">
              <Headphones className="size-12 opacity-20 text-primary mb-3" />
              <p className="text-sm font-semibold text-foreground">
                Chọn một phiên hội thoại để kiểm tra
              </p>
              <p className="text-xs max-w-sm mt-1">
                Xem toàn bộ lịch sử trao đổi, thông tin người học và tiếp quản xử lý trực tiếp khi
                cần thiết.
              </p>
            </div>
          ) : (
            <>
              {/* Desk Topbar */}
              <div className="p-3.5 border-b border-border bg-card flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-sm text-foreground">
                      {activeThread.user_name}
                    </span>
                    {activeThread.user_email && (
                      <span className="text-xs text-muted-foreground font-mono">
                        &lt;{activeThread.user_email}&gt;
                      </span>
                    )}
                    {getStatusBadge(activeThread.status)}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      {getAssistantIcon(activeThread.assistant_code)}
                      <span>{activeThread.assistant_name}</span>
                    </span>
                    {activeThread.assigned_to && (
                      <span>
                        • Cán bộ phụ trách:{" "}
                        <strong className="text-foreground">{activeThread.assigned_to}</strong>
                      </span>
                    )}
                  </div>
                </div>

                {/* Status Action Buttons */}
                <div className="flex items-center gap-2 shrink-0 flex-wrap">
                  {activeThread.status === "handoff_requested" && (
                    <Button
                      size="sm"
                      onClick={() =>
                        statusMutation.mutate({
                          status: "staff_claimed",
                          assigned_to: staffName.trim() || "Cán bộ QNU",
                        })
                      }
                      disabled={statusMutation.isPending}
                      variant="destructive"
                      className="h-8 text-xs gap-1.5 font-medium shadow-sm"
                    >
                      <UserCheck className="size-3.5" />
                      <span>Tiếp nhận hỗ trợ</span>
                    </Button>
                  )}

                  {activeThread.status === "staff_claimed" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        statusMutation.mutate({
                          status: "ai_active",
                        })
                      }
                      disabled={statusMutation.isPending}
                      className="h-8 text-xs gap-1.5 text-primary hover:bg-primary/10"
                    >
                      <Bot className="size-3.5" />
                      <span>Chuyển lại cho AI</span>
                    </Button>
                  )}

                  {activeThread.status !== "resolved" ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        statusMutation.mutate({
                          status: "resolved",
                        })
                      }
                      disabled={statusMutation.isPending}
                      className="h-8 text-xs gap-1.5 text-success hover:bg-success/10 border-success/30"
                    >
                      <CheckCircle2 className="size-3.5" />
                      <span>Đã giải quyết</span>
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        statusMutation.mutate({
                          status: "ai_active",
                        })
                      }
                      disabled={statusMutation.isPending}
                      className="h-8 text-xs gap-1.5"
                    >
                      <RefreshCw className="size-3.5" />
                      <span>Mở lại phiên</span>
                    </Button>
                  )}

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExportThreadMarkdown}
                    className="h-8 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
                    title="Tải nội dung hội thoại dạng Markdown (.md)"
                  >
                    <Download className="size-3.5" />
                    <span className="hidden sm:inline">Xuất MD</span>
                  </Button>
                </div>
              </div>

              {/* Messages Area */}
              <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-muted/10">
                {activeThread.messages.map((msg) => {
                  const isUser = msg.sender === "user";
                  const isStaff = msg.sender === "agent";
                  const isAi = msg.sender === "assistant";

                  return (
                    <div
                      key={msg.id}
                      className={cn(
                        "flex gap-3 max-w-[85%]",
                        isUser ? "ml-auto flex-row-reverse" : "mr-auto"
                      )}
                    >
                      {/* Avatar */}
                      <div
                        className={cn(
                          "size-7 rounded-full flex items-center justify-center text-xs shrink-0 font-medium",
                          isUser && "bg-muted text-muted-foreground border border-border",
                          isStaff && "bg-sky-500/15 text-sky-600 border border-sky-500/30",
                          isAi && "bg-primary/15 text-primary border border-primary/30"
                        )}
                      >
                        {isUser && <User className="size-3.5" />}
                        {isStaff && <UserCheck className="size-3.5" />}
                        {isAi && <Bot className="size-3.5" />}
                      </div>

                      {/* Bubble */}
                      <div
                        className={cn(
                          "rounded-lg p-3 text-xs leading-relaxed border space-y-1 shadow-2xs",
                          isUser && "bg-primary text-primary-foreground border-primary",
                          isStaff &&
                            "bg-sky-50 dark:bg-sky-950/40 text-foreground border-sky-200 dark:border-sky-800/40",
                          isAi && "bg-card text-foreground border-border"
                        )}
                      >
                        <div className="flex items-center justify-between gap-3 text-[10px] opacity-75">
                          <span className="font-semibold">
                            {isUser && activeThread.user_name}
                            {isStaff && "Cán bộ tư vấn QNU"}
                            {isAi && activeThread.assistant_name}
                          </span>
                          <span>
                            {msg.created_at
                              ? new Date(msg.created_at).toLocaleTimeString("vi-VN", {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })
                              : "Vừa xong"}
                          </span>
                        </div>
                        <p className="whitespace-pre-wrap">{msg.text}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Staff Reply Box & Canned Quick Replies */}
              <div className="p-3 border-t border-border bg-card space-y-2.5">
                {/* Canned replies pills */}
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px]">
                  <span className="text-muted-foreground text-[10px] whitespace-nowrap shrink-0 flex items-center gap-1">
                    <CornerDownLeft className="size-3" /> Mẫu nhanh:
                  </span>
                  {CANNED_REPLIES.map((canned) => (
                    <button
                      type="button"
                      key={canned}
                      onClick={() => setReplyText(canned)}
                      className="px-2 py-0.5 rounded-md bg-muted/60 hover:bg-muted text-muted-foreground hover:text-foreground text-[10px] whitespace-nowrap border border-border transition-colors truncate max-w-[200px]"
                      title={canned}
                    >
                      {canned}
                    </button>
                  ))}
                </div>

                {/* Reply Form */}
                <form onSubmit={handleSendReply} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-muted-foreground shrink-0 font-medium">
                      Danh xưng cán bộ:
                    </span>
                    <Input
                      value={staffName}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        setStaffName(e.target.value)
                      }
                      placeholder="Cán bộ QNU..."
                      className="h-7 text-xs w-48 font-medium"
                    />
                  </div>

                  <div className="flex items-end gap-2">
                    <Textarea
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSendReply(e);
                        }
                      }}
                      placeholder="Nhập câu trả lời trực tiếp gửi đến thí sinh/sinh viên (Nhấn Enter để gửi)..."
                      rows={2}
                      className="text-xs resize-none"
                    />
                    <Button
                      type="submit"
                      size="sm"
                      disabled={!replyText.trim() || replyMutation.isPending}
                      className="h-14 px-4 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 shrink-0"
                    >
                      <Send className="size-3.5" />
                      <span>{replyMutation.isPending ? "Đang gửi..." : "Gửi phản hồi"}</span>
                    </Button>
                  </div>
                </form>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
};
