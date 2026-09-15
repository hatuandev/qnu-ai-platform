import {
  Bot,
  GraduationCap,
  Library,
  Search,
  Send,
  ShieldCheck,
  User,
  UserCheck,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

interface ConversationThread {
  id: string;
  user_name: string;
  user_email: string;
  assistant_code: string;
  assistant_name: string;
  last_message: string;
  updated_at: string;
  is_handed_off: boolean;
  messages: Array<{
    id: string;
    sender: "user" | "assistant" | "agent";
    text: string;
    time: string;
  }>;
}

const MOCK_THREADS: ConversationThread[] = [
  {
    id: "conv_01",
    user_name: "Thí sinh Nguyễn Văn An",
    user_email: "an.nguyen2007@gmail.com",
    assistant_code: "admissions",
    assistant_name: "Trợ lý Tuyển sinh QNU",
    last_message: "Em muốn hỏi về phương thức xét học bạ ngành Công nghệ thông tin?",
    updated_at: "19:45 hôm nay",
    is_handed_off: false,
    messages: [
      {
        id: "m1",
        sender: "user",
        text: "Xin chào, em muốn tìm hiểu thông tin tuyển sinh năm 2025 ạ.",
        time: "19:42",
      },
      {
        id: "m2",
        sender: "assistant",
        text: "Chào bạn! Mình là Trợ lý Tuyển sinh ĐH Quy Nhơn. Năm 2025 trường có 4 phương thức xét tuyển. Bạn đang quan tâm đến ngành nào?",
        time: "19:43",
      },
      {
        id: "m3",
        sender: "user",
        text: "Em muốn hỏi về phương thức xét học bạ ngành Công nghệ thông tin?",
        time: "19:45",
      },
    ],
  },
  {
    id: "conv_02",
    user_name: "Sinh viên Trần Thị Mai",
    user_email: "4551050123@qnu.edu.vn",
    assistant_code: "regulations",
    assistant_name: "Trợ lý Quy chế Học vụ",
    last_message: "Em xin bảo lưu học kỳ 1 năm học 2024-2025 thì nộp đơn ở đâu?",
    updated_at: "18:20 hôm nay",
    is_handed_off: true,
    messages: [
      {
        id: "m4",
        sender: "user",
        text: "Em xin bảo lưu học kỳ 1 năm học 2024-2025 thì nộp đơn ở đâu?",
        time: "18:18",
      },
      {
        id: "m5",
        sender: "assistant",
        text: "Theo Điều 12 Quy chế đào tạo, bạn cần làm đơn xin tạm hoãn học tập và nộp tại Bộ phận Một cửa - Phòng Đào tạo (Tầng 1 Nhà A1).",
        time: "18:19",
      },
      {
        id: "m6",
        sender: "agent",
        text: "[Cán bộ tư vấn Nguyễn Thị Lan đã tiếp quản phiên trao đổi]",
        time: "18:20",
      },
    ],
  },
  {
    id: "conv_03",
    user_name: "Học viên Lê Quốc Bảo",
    user_email: "baolq.msc@qnu.edu.vn",
    assistant_code: "library",
    assistant_name: "Trợ lý Thư viện Số",
    last_message: "Tài khoản ScienceDirect của em bị báo hết phiên đăng nhập từ xa.",
    updated_at: "Hôm qua 15:30",
    is_handed_off: false,
    messages: [
      {
        id: "m7",
        sender: "user",
        text: "Tài khoản ScienceDirect của em bị báo hết phiên đăng nhập từ xa.",
        time: "15:28",
      },
      {
        id: "m8",
        sender: "assistant",
        text: "Bạn vui lòng đăng nhập qua Cổng xác thực thư viện SSO tại lib.qnu.edu.vn bằng email @qnu.edu.vn để gia hạn token nhé.",
        time: "15:30",
      },
    ],
  },
];

export const ConversationsPage: React.FC = () => {
  const [threads, setThreads] = useState<ConversationThread[]>(MOCK_THREADS);
  const [selectedThreadId, setSelectedThreadId] = useState<string>("conv_01");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [replyText, setReplyText] = useState<string>("");

  const activeThread = threads.find((t) => t.id === selectedThreadId) || threads[0];

  const handleHandoffToggle = (id: string) => {
    setThreads((prev) =>
      prev.map((t) => {
        if (t.id === id) {
          const nextStatus = !t.is_handed_off;
          const newMsg = nextStatus
            ? {
                id: `h_${Date.now()}`,
                sender: "agent" as const,
                text: "[Cán bộ tư vấn đã tiếp nhận cuộc trò chuyện]",
                time: "Vừa xong",
              }
            : {
                id: `h_${Date.now()}`,
                sender: "assistant" as const,
                text: "[Đã chuyển lại quyền điều phối cho Trợ lý AI]",
                time: "Vừa xong",
              };
          return {
            ...t,
            is_handed_off: nextStatus,
            messages: [...t.messages, newMsg],
          };
        }
        return t;
      })
    );
  };

  const handleSendAgentReply = (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim()) return;

    setThreads((prev) =>
      prev.map((t) => {
        if (t.id === selectedThreadId) {
          return {
            ...t,
            messages: [
              ...t.messages,
              { id: `r_${Date.now()}`, sender: "agent", text: replyText, time: "Vừa xong" },
            ],
          };
        }
        return t;
      })
    );
    setReplyText("");
  };

  const filteredThreads = threads.filter(
    (t) =>
      t.user_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.user_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.last_message.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getAssistantIcon = (code: string) => {
    switch (code) {
      case "admissions":
        return <GraduationCap className="h-3.5 w-3.5" />;
      case "regulations":
        return <ShieldCheck className="h-3.5 w-3.5" />;
      case "library":
        return <Library className="h-3.5 w-3.5" />;
      default:
        return <Bot className="h-3.5 w-3.5" />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          Hội Thoại Đa Kênh & Bàn Giao Cán Bộ (Handoff)
          <Badge variant="outline" className="font-mono text-xs">
            Human-in-the-loop
          </Badge>
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Giám sát các phiên hỏi đáp trực tiếp của người dùng và bàn giao tức thì cho Cán bộ tư vấn
          khi gặp tình huống phức tạp.
        </p>
      </div>

      {/* Main split view */}
      <div className="flex h-[calc(100vh-var(--topbar-height)-8rem)] flex-col md:flex-row gap-4">
        {/* Left: Threads List */}
        <div className="w-full md:w-80 shrink-0 flex flex-col rounded-surface border border-border bg-card shadow-xs overflow-hidden">
          <div className="p-3 border-b border-border bg-muted/20">
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-muted-foreground absolute left-2.5 top-2.5" />
              <Input
                placeholder="Tìm phiên hội thoại..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 text-xs bg-background"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-border/60">
            {filteredThreads.map((thread) => {
              const isSelected = thread.id === selectedThreadId;
              return (
                <button
                  key={thread.id}
                  type="button"
                  onClick={() => setSelectedThreadId(thread.id)}
                  className={`w-full text-left p-3.5 transition-colors cursor-pointer space-y-1.5 ${
                    isSelected ? "bg-primary/10 border-l-3 border-l-primary" : "hover:bg-muted/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="font-semibold text-xs text-foreground truncate">
                        {thread.user_name}
                      </span>
                    </div>
                    <span className="text-[10px] text-muted-foreground shrink-0 font-mono">
                      {thread.updated_at}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 text-[11px] text-primary">
                    {getAssistantIcon(thread.assistant_code)}
                    <span className="truncate">{thread.assistant_name}</span>
                  </div>

                  <p className="text-[11px] text-muted-foreground line-clamp-1">
                    {thread.last_message}
                  </p>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {thread.user_email}
                    </span>
                    {thread.is_handed_off ? (
                      <Badge variant="warning" className="text-[10px]">
                        Cán bộ tiếp quản
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] text-muted-foreground">
                        AI Điều Phối
                      </Badge>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Conversation Transcript View */}
        <div className="flex-1 flex flex-col rounded-surface border border-border bg-card shadow-xs overflow-hidden">
          {/* Thread Header */}
          <div className="flex items-center justify-between p-3.5 border-b border-border bg-muted/20">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
                <User className="h-4 w-4" />
              </div>
              <div>
                <h3 className="font-bold text-xs text-foreground">{activeThread.user_name}</h3>
                <p className="text-[11px] text-muted-foreground font-mono">
                  {activeThread.user_email} • Đang kết nối {activeThread.assistant_name}
                </p>
              </div>
            </div>

            <Button
              size="sm"
              variant={activeThread.is_handed_off ? "default" : "outline"}
              onClick={() => handleHandoffToggle(activeThread.id)}
              className="text-xs h-8 gap-1.5"
            >
              <UserCheck className="h-3.5 w-3.5" />
              <span>
                {activeThread.is_handed_off
                  ? "Trả quyền cho Trợ lý AI"
                  : "Tiếp Quản Phiên Hội Thoại"}
              </span>
            </Button>
          </div>

          {/* Transcript Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-muted/10 text-xs">
            {activeThread.messages.map((m) => {
              if (m.sender === "agent") {
                return (
                  <div key={m.id} className="flex items-center justify-center my-2">
                    <span className="px-3 py-1 rounded-full bg-warning/10 border border-warning/30 text-warning text-[11px] font-medium">
                      {m.text} ({m.time})
                    </span>
                  </div>
                );
              }

              const isUser = m.sender === "user";
              return (
                <div
                  key={m.id}
                  className={`flex gap-2.5 max-w-xl ${isUser ? "ml-auto justify-end" : "mr-auto"}`}
                >
                  {!isUser && (
                    <div className="h-6 w-6 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
                      <Bot className="h-3.5 w-3.5" />
                    </div>
                  )}
                  <div
                    className={`p-3 rounded-surface text-xs leading-relaxed space-y-1 ${
                      isUser
                        ? "bg-primary text-primary-foreground rounded-br-micro"
                        : "bg-card border border-border text-foreground rounded-bl-micro shadow-2xs"
                    }`}
                  >
                    <p>{m.text}</p>
                    <span className="text-[10px] opacity-70 block text-right font-mono">
                      {m.time}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Reply box (for Human Counselor) */}
          <form
            onSubmit={handleSendAgentReply}
            className="p-3 border-t border-border bg-card flex items-center gap-2"
          >
            <Input
              placeholder={
                activeThread.is_handed_off
                  ? "Nhập tin nhắn với tư cách Cán bộ tư vấn QNU..."
                  : "Bấm 'Tiếp Quản Phiên Hội Thoại' ở trên để trực tiếp nhắn tin..."
              }
              disabled={!activeThread.is_handed_off}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              className="text-xs h-9"
            />
            <Button
              type="submit"
              size="sm"
              disabled={!activeThread.is_handed_off || !replyText.trim()}
              className="h-9 text-xs gap-1.5 shrink-0 font-semibold"
            >
              <Send className="h-3.5 w-3.5" />
              <span>Gửi</span>
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};
