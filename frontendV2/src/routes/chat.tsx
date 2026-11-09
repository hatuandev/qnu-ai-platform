import { createFileRoute } from "@tanstack/react-router";
import { BookOpen, Bot, Plus, Send, Sparkles, User } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/chat")({
  component: ChatPage,
});

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: { source: string; page: number; excerpt: string }[];
};

function ChatPage() {
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      id: "msg_1",
      role: "user",
      content:
        "Trường Đại học Quy Nhơn được thành lập vào năm nào theo quyết định của Hội đồng Bộ trưởng?",
    },
    {
      id: "msg_2",
      role: "assistant",
      content:
        "Trường Đại học Quy Nhơn được thành lập theo **Quyết định số 02/HĐBT** ngày **13/7/1981** của Hội đồng Bộ trưởng (tiền thân từ Cơ sở Đại học Sư phạm Quy Nhơn thành lập ngày 21/12/1977 theo Quyết định 1842/QĐ của Bộ Giáo dục).\n\nĐến ngày 30/10/2003, Thủ tướng Chính phủ ban hành Quyết định số 221/2003/QĐ-TTg đổi tên trường thành Trường Đại học Quy Nhơn để phát triển đa ngành.",
      citations: [
        {
          source: "Du_lieu_RAG_Truong_Dai_hoc_Quy_Nhon_2026.docx",
          page: 1,
          excerpt:
            "Ngày 13/7/1981, Hội đồng Bộ trưởng ban hành Quyết định số 02/HĐBT thành lập Trường Đại học Sư phạm Quy Nhơn...",
        },
      ],
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    const currentInput = input;
    const userMsg: ChatMsg = {
      id: `msg_${Date.now()}`,
      role: "user",
      content: currentInput,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    // Simulate AI response with realistic citation after 600ms
    setTimeout(() => {
      const assistantMsg: ChatMsg = {
        id: `msg_ai_${Date.now()}`,
        role: "assistant",
        content: `Dựa trên dữ liệu văn bản chính thức của Trường Đại học Quy Nhơn:\n\nThông tin về "${currentInput}" đã được đối chiếu trong cơ sở dữ liệu tri thức năm học 2026 - 2027. Hệ thống xác nhận nội dung tuân thủ đúng các quy định tuyển sinh và quy chế đào tạo hiện hành.`,
        citations: [
          {
            source: "De_an_tuyen_sinh_2026.pdf",
            page: 2,
            excerpt:
              "Cơ chế tuyển sinh và các phương thức xét tuyển thẳng, điểm thi tốt nghiệp THPT năm 2026 theo quy chế Đào tạo...",
          },
        ],
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsTyping(false);
    }, 600);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col bg-background">
      {/* Top chat header */}
      <div className="flex h-12 items-center justify-between border-b border-border/60 bg-card px-4">
        <div className="flex items-center gap-2">
          <div className="size-6 rounded-md bg-primary/10 text-primary flex items-center justify-center">
            <Bot className="size-3.5" />
          </div>
          <span className="text-xs font-semibold text-foreground">
            Trợ lý Tuyển sinh 2026
          </span>
          <Badge
            variant="outline"
            className="text-[10px] h-4 px-1 text-muted-foreground"
          >
            Qwen 2.5 Coder
          </Badge>
          <Badge
            variant="secondary"
            className="text-[10px] h-4 px-1.5 bg-emerald-500/10 text-emerald-600 font-normal"
          >
            Chế độ Demo giao diện
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setMessages([])}
          className="h-7 text-xs gap-1 text-muted-foreground"
        >
          <Plus className="size-3" />
          <span>Hội thoại mới</span>
        </Button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-w-3xl w-full mx-auto">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.role === "assistant" && (
              <div className="size-7 rounded-full bg-primary/15 text-primary flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="size-3.5" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-lg px-4 py-3 text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground font-normal"
                  : "bg-card border border-border/60 text-foreground space-y-2 shadow-2xs"
              }`}
            >
              <div className="whitespace-pre-line">{msg.content}</div>

              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-border/40 space-y-1.5">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                    <BookOpen className="size-3" />
                    <span>Nguồn trích dẫn</span>
                  </span>
                  {msg.citations.map((cite) => (
                    <div
                      key={`${cite.source}-${cite.page}`}
                      className="rounded bg-muted/50 p-2 text-[11px] text-muted-foreground border border-border/30"
                    >
                      <div className="font-medium text-foreground flex items-center justify-between">
                        <span>
                          {cite.source} · Trang {cite.page}
                        </span>
                      </div>
                      <p className="mt-1 italic line-clamp-2">
                        "{cite.excerpt}"
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="size-7 rounded-full bg-muted text-muted-foreground flex items-center justify-center shrink-0 mt-0.5">
                <User className="size-3.5" />
              </div>
            )}
          </div>
        ))}

        {isTyping && (
          <div className="flex gap-3 justify-start items-center text-xs text-muted-foreground">
            <div className="size-7 rounded-full bg-primary/15 text-primary flex items-center justify-center shrink-0">
              <Bot className="size-3.5" />
            </div>
            <div className="flex items-center gap-1.5 bg-card border border-border/60 rounded-lg px-3 py-2 shadow-2xs">
              <Sparkles className="size-3 animate-spin text-primary" />
              <span>Trợ lý đang suy nghĩ & tra cứu trích dẫn...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-border/60 bg-card p-3">
        <div className="max-w-3xl mx-auto flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Đặt câu hỏi về thông tin tuyển sinh, quy chế đào tạo..."
            className="flex-1 h-9 rounded-md border border-border/60 bg-muted/30 px-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:bg-background transition-colors"
          />
          <Button
            size="sm"
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="h-9 px-3 gap-1.5 text-xs"
          >
            <Send className="size-3.5" />
            <span>Gửi</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
