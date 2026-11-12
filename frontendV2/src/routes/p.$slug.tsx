import { createFileRoute } from "@tanstack/react-router";
import {
  BookOpen,
  Bot,
  Check,
  ChevronRight,
  Copy,
  ExternalLink,
  GraduationCap,
  Loader2,
  Moon,
  RotateCcw,
  Send,
  Share2,
  ShieldCheck,
  Sparkles,
  Sun,
  ThumbsDown,
  ThumbsUp,
  User,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { useUiStore } from "@/lib/ui-store";

export const Route = createFileRoute("/p/$slug")({
  component: PublicChatPage,
});

type Citation = {
  id: string;
  source: string;
  page: number;
  section?: string;
  excerpt: string;
  publishedAt: string;
};

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: Citation[];
  feedback?: "up" | "down" | null;
};

const STARTER_PROMPTS = [
  {
    icon: GraduationCap,
    title: "Chỉ tiêu tuyển sinh 2026",
    prompt:
      "Chỉ tiêu tuyển sinh và các phương thức xét tuyển vào Trường Đại học Quy Nhơn năm 2026?",
  },
  {
    icon: BookOpen,
    title: "Mức học phí các khối ngành",
    prompt:
      "Mức học phí năm học 2026 - 2027 của khối ngành Công nghệ thông tin và Sư phạm là bao nhiêu?",
  },
  {
    icon: ShieldCheck,
    title: "Xét tuyển thẳng & Ưu tiên",
    prompt:
      "Quy định xét tuyển thẳng và cộng điểm ưu tiên đối với chứng chỉ tiếng Anh IELTS hoặc VSTEP?",
  },
  {
    icon: Sparkles,
    title: "Chính sách học bổng",
    prompt:
      "Chính sách học bổng tuyển sinh và chế độ miễn giảm học phí cho tân sinh viên?",
  },
];

const INITIAL_PUBLIC_MESSAGES: ChatMsg[] = [
  {
    id: "pub_msg_1",
    role: "user",
    content:
      "Trường Đại học Quy Nhơn có những phương thức xét tuyển nào trong năm 2026 và ngành Công nghệ thông tin lấy bao nhiêu chỉ tiêu?",
    timestamp: "10:20",
  },
  {
    id: "pub_msg_2",
    role: "assistant",
    content:
      "Chào bạn! Căn cứ theo **Đề án tuyển sinh trình độ đại học năm 2026** của Trường Đại học Quy Nhơn, nhà trường áp dụng 4 phương thức tuyển sinh chính thức:\n\n1. **Phương thức 1:** Xét tuyển dựa trên kết quả kỳ thi tốt nghiệp THPT năm 2026.\n2. **Phương thức 2:** Xét tuyển dựa vào kết quả học tập THPT (học bạ) với tổng điểm trung bình 3 môn theo tổ hợp từ 18.0 điểm trở lên.\n3. **Phương thức 3:** Xét tuyển thẳng và ưu tiên xét tuyển theo Quy chế tuyển sinh hiện hành của Bộ GD&ĐT.\n4. **Phương thức 4:** Xét tuyển dựa trên kết quả kỳ thi Đánh giá năng lực của Đại học Quốc gia TP.HCM.\n\nĐối với **ngành Công nghệ thông tin (mã ngành: 7480201)**:\n- Dự kiến tổng chỉ tiêu tuyển sinh: **180 chỉ tiêu**.\n- Các tổ hợp môn xét tuyển: A00 (Toán, Lý, Hóa), A01 (Toán, Lý, Tiếng Anh), C01 (Toán, Văn, Lý), D01 (Toán, Văn, Tiếng Anh).",
    timestamp: "10:20",
    citations: [
      {
        id: "pub_cite_1",
        source: "De_an_tuyen_sinh_2026.pdf",
        page: 4,
        section: "Chương II. Chỉ tiêu và Phương thức xét tuyển",
        excerpt:
          "Năm 2026, Trường Đại học Quy Nhơn áp dụng 4 phương thức tuyển sinh chính quy. Ngành Công nghệ thông tin phân bổ 180 chỉ tiêu cho các tổ hợp A00, A01, C01, D01...",
        publishedAt: "10/11/2026",
      },
      {
        id: "pub_cite_2",
        source: "Thong_tin_TSDH_cap_nhat_2026.pdf",
        page: 2,
        section: "Ngưỡng đảm bảo chất lượng đầu vào",
        excerpt:
          "Đối với phương thức xét học bạ, thí sinh cần có tổng điểm 3 môn trong tổ hợp xét tuyển từ 18.00 điểm trở lên (không tính điểm ưu tiên)...",
        publishedAt: "11/11/2026",
      },
    ],
    feedback: null,
  },
];

function PublicChatPage() {
  const { slug } = Route.useParams();
  const { theme, setTheme } = useUiStore();
  const [messages, setMessages] = useState<ChatMsg[]>(INITIAL_PUBLIC_MESSAGES);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(
    null,
  );
  const [copiedLink, setCopiedLink] = useState(false);

  const botTitle =
    slug === "tuyen-sinh-2026"
      ? "Trợ lý Tuyển sinh 2026"
      : `Trợ lý AI · ${slug}`;

  const handleSend = (textToSend?: string) => {
    const content = (textToSend || input).trim();
    if (!content || isTyping) return;

    const userMsg: ChatMsg = {
      id: `u_${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const assistantMsg: ChatMsg = {
        id: `a_${Date.now()}`,
        role: "assistant",
        content: `Thông tin về câu hỏi **"${content}"**:\n\nCăn cứ theo văn bản hướng dẫn và đề án tuyển sinh chính thức năm học 2026 - 2027 của Trường Đại học Quy Nhơn, quy trình đăng ký xét tuyển được thực hiện hoàn toàn trực tuyến trên Cổng thông tin của Bộ GD&ĐT hoặc Cổng tuyển sinh nhà trường. Thí sinh được hưởng đầy đủ các chính sách ưu tiên đối tượng và khu vực theo quy định hiện hành.`,
        timestamp: new Date().toLocaleTimeString("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        citations: [
          {
            id: `c_${Date.now()}`,
            source: "De_an_tuyen_sinh_2026.pdf",
            page: 5,
            section: "Thời gian và quy trình xét tuyển",
            excerpt:
              "Thí sinh đăng ký nguyện vọng xét tuyển theo hình thức trực tuyến. Mọi thông tin hướng dẫn và biểu mẫu chi tiết được cập nhật tại website tuyensinh.qnu.edu.vn...",
            publishedAt: "10/11/2026",
          },
        ],
        feedback: null,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsTyping(false);
    }, 700);
  };

  const handleFeedback = (msgId: string, type: "up" | "down") => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === msgId
          ? { ...m, feedback: m.feedback === type ? null : type }
          : m,
      ),
    );
    toast.success(
      type === "up"
        ? "Cảm ơn bạn đã xác nhận câu trả lời hữu ích!"
        : "Đã ghi nhận góp ý của bạn để nhà trường rà soát và bổ sung thông tin.",
    );
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    toast.success("Đã sao chép nội dung câu trả lời.");
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    toast.success("Đã sao chép liên kết cổng tra cứu!");
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className="flex h-screen w-full max-w-full flex-col bg-background text-foreground antialiased overflow-hidden">
      {/* 1. Header Công cộng (Public Branding) - Không có Sidebar Admin */}
      <header className="flex h-14 sm:h-16 items-center justify-between border-b border-border/60 bg-card px-3 sm:px-6 shrink-0 z-10 shadow-2xs">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 mr-2">
          <div className="size-8 sm:size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20 shadow-2xs">
            <GraduationCap className="size-4.5 sm:size-5.5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-bold tracking-wider uppercase text-primary truncate">
                Trường ĐH Quy Nhơn
              </span>
              <Badge
                variant="secondary"
                className="text-[10px] h-4 px-1.5 font-normal bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 hidden sm:inline-flex"
              >
                Cơ sở dữ liệu chính thức 2026
              </Badge>
            </div>
            <h1 className="text-xs sm:text-base font-semibold text-foreground truncate">
              {botTitle}
            </h1>
          </div>
        </div>

        {/* Nút thao tác dành cho người dùng công chúng */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleShare}
            className="size-8 p-0 sm:w-auto sm:px-3 sm:h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            title="Chia sẻ liên kết này"
          >
            {copiedLink ? (
              <Check className="size-3.5 text-emerald-500" />
            ) : (
              <Share2 className="size-3.5" />
            )}
            <span className="hidden md:inline">
              {copiedLink ? "Đã chép link" : "Chia sẻ"}
            </span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setMessages([]);
              toast.info("Đã đặt lại cuộc hội thoại.");
            }}
            className="size-8 p-0 sm:w-auto sm:px-3 sm:h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            title="Xóa và bắt đầu lại cuộc trò chuyện"
          >
            <RotateCcw className="size-3.5" />
            <span className="hidden md:inline">Hội thoại mới</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="size-8 p-0 text-muted-foreground hover:text-foreground"
            title="Đổi chế độ sáng / tối"
          >
            {theme === "dark" ? (
              <Sun className="size-4" />
            ) : (
              <Moon className="size-4" />
            )}
          </Button>
        </div>
      </header>

      {/* 2. Khung Hội thoại (Conversation Canvas) */}
      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="max-w-3xl w-full mx-auto space-y-6">
          {messages.length === 0 ? (
            /* Trạng thái chào đón thí sinh & Starter Questions */
            <div className="py-12 space-y-8 animate-in fade-in-50 duration-300">
              <div className="text-center space-y-3">
                <div className="size-16 rounded-2xl bg-primary/10 text-primary mx-auto flex items-center justify-center border border-primary/20 shadow-xs">
                  <GraduationCap className="size-8" />
                </div>
                <div className="space-y-1">
                  <h2 className="text-lg sm:text-xl font-bold text-foreground">
                    Cổng Tra cứu Tuyển sinh & Học vụ QNU
                  </h2>
                  <p className="text-xs sm:text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
                    Hệ thống hỏi đáp thông minh hỗ trợ 24/7 của Trường Đại học
                    Quy Nhơn. Thông tin được trích xuất trực tiếp từ các văn bản
                    phê duyệt chính thức.
                  </p>
                </div>
              </div>

              {/* Lưới các câu hỏi mẫu gợi ý */}
              <div className="space-y-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground px-1">
                  Gợi ý câu hỏi tra cứu phổ biến:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {STARTER_PROMPTS.map((item) => (
                    <button
                      type="button"
                      key={item.title}
                      onClick={() => handleSend(item.prompt)}
                      className="group flex flex-col items-start p-3.5 rounded-xl border border-border/70 bg-card hover:bg-muted/40 hover:border-primary/50 transition-all text-left shadow-2xs cursor-pointer"
                    >
                      <div className="flex items-center gap-2 text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                        <item.icon className="size-4 text-primary shrink-0" />
                        <span>{item.title}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-1.5 line-clamp-2 leading-relaxed">
                        {item.prompt}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Luồng tin nhắn hỏi đáp */
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2 sm:gap-3 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="size-7 sm:size-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5 border border-primary/20 shadow-2xs">
                    <Bot className="size-3.5 sm:size-4.5" />
                  </div>
                )}

                <div
                  className={`max-w-[calc(100%-2.5rem)] sm:max-w-[80%] rounded-2xl px-3.5 py-3 sm:px-4 sm:py-3.5 text-xs sm:text-[13px] leading-relaxed ${
                    msg.role === "user"
                      ? "rounded-tr-xs bg-primary text-primary-foreground font-normal shadow-2xs"
                      : "rounded-tl-xs bg-card border border-border/60 text-foreground space-y-3 shadow-2xs"
                  }`}
                >
                  <div className="whitespace-pre-line leading-relaxed">
                    {msg.content}
                  </div>

                  {/* Bằng chứng trích dẫn nguồn văn bản (Interactive Citations) */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2.5 border-t border-border/40 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground font-medium">
                        <span className="flex items-center gap-1.5">
                          <BookOpen className="size-3.5 text-primary" />
                          <span>
                            Căn cứ văn bản trích dẫn ({msg.citations.length})
                          </span>
                        </span>
                        <span className="text-[10px] text-muted-foreground/80 hidden sm:inline">
                          Bấm để xem đối chiếu
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-1.5">
                        {msg.citations.map((cite, idx) => (
                          <button
                            type="button"
                            key={cite.id}
                            onClick={() => setSelectedCitation(cite)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-border/70 bg-muted/40 hover:bg-muted hover:border-primary/50 px-2.5 py-1 text-[11px] text-foreground transition-all cursor-pointer group shadow-2xs"
                          >
                            <span className="size-4 rounded bg-primary/15 text-primary text-[10px] font-bold flex items-center justify-center shrink-0">
                              {idx + 1}
                            </span>
                            <span className="truncate max-w-[190px] sm:max-w-[260px] font-medium">
                              {cite.source}
                            </span>
                            <span className="text-muted-foreground text-[10px]">
                              · Trang {cite.page}
                            </span>
                            <ChevronRight className="size-3 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Thanh công cụ đánh giá & sao chép dưới câu trả lời */}
                  {msg.role === "assistant" && (
                    <div className="flex items-center justify-between pt-1 border-t border-border/30 text-[11px] text-muted-foreground">
                      <span className="text-[10px] text-muted-foreground/70">
                        {msg.timestamp} · Đối chiếu dữ liệu chính thức
                      </span>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(msg.content)}
                          className="size-7 p-0 text-muted-foreground hover:text-foreground"
                          title="Sao chép nội dung"
                        >
                          <Copy className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleFeedback(msg.id, "up")}
                          className={`size-7 p-0 ${
                            msg.feedback === "up"
                              ? "text-primary bg-primary/10"
                              : "text-muted-foreground hover:text-foreground"
                          }`}
                          title="Hữu ích và chính xác"
                        >
                          <ThumbsUp className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleFeedback(msg.id, "down")}
                          className={`size-7 p-0 ${
                            msg.feedback === "down"
                              ? "text-destructive bg-destructive/10"
                              : "text-muted-foreground hover:text-foreground"
                          }`}
                          title="Chưa chính xác hoặc thiếu thông tin"
                        >
                          <ThumbsDown className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="size-8 sm:size-9 rounded-xl bg-muted text-muted-foreground flex items-center justify-center shrink-0 mt-0.5 border border-border/50">
                    <User className="size-4.5" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Hiệu ứng đang tìm kiếm và suy nghĩ */}
          {isTyping && (
            <div className="flex gap-3 justify-start items-center text-xs text-muted-foreground animate-in fade-in-50 duration-200">
              <div className="size-8 sm:size-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20">
                <Bot className="size-4.5" />
              </div>
              <div className="flex items-center gap-2 bg-card border border-border/60 rounded-xl px-4 py-3 shadow-2xs">
                <Loader2 className="size-3.5 animate-spin text-primary shrink-0" />
                <span className="text-xs font-medium text-foreground">
                  Đang tra cứu cơ sở dữ liệu đề án & quy chế tuyển sinh...
                </span>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* 3. Khung Nhập liệu (Bottom Chat Input Bar) */}
      <footer className="border-t border-border/60 bg-card p-2.5 sm:p-4 shrink-0 shadow-lg">
        <div className="max-w-3xl w-full mx-auto space-y-1.5 sm:space-y-2">
          <div className="flex items-end gap-1.5 sm:gap-2 bg-muted/40 border border-border/60 rounded-2xl p-1.5 sm:p-2 focus-within:border-primary/60 focus-within:bg-background transition-colors shadow-2xs">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Nhập câu hỏi cần hỗ trợ..."
              rows={1}
              className="flex-1 min-h-[38px] sm:min-h-[40px] max-h-36 resize-none border-0 bg-transparent px-2.5 sm:px-3 py-2 text-xs sm:text-sm placeholder:text-muted-foreground focus-visible:ring-0 shadow-none leading-relaxed"
            />
            <Button
              size="sm"
              onClick={() => handleSend()}
              disabled={!input.trim() || isTyping}
              className="h-8 sm:h-9 px-3 sm:px-3.5 gap-1.5 text-xs font-semibold shrink-0 rounded-xl shadow-2xs"
            >
              <Send className="size-3.5" />
              <span className="hidden sm:inline">Gửi câu hỏi</span>
            </Button>
          </div>
          <p className="text-[10px] text-center text-muted-foreground/80 leading-tight">
            Thông tin hỗ trợ tra cứu 24/7 của Trường Đại học Quy Nhơn. Dữ liệu
            được đối chiếu trực tiếp từ các quyết định và đề án đã ban hành.
          </p>
        </div>
      </footer>

      {/* 4. Slide-over Sheet xem chi tiết văn bản gốc (Evidence Drawer) */}
      <Sheet
        open={Boolean(selectedCitation)}
        onOpenChange={(open) => !open && setSelectedCitation(null)}
      >
        <SheetContent side="right" className="sm:max-w-md p-0 flex flex-col">
          <SheetHeader className="p-4 border-b border-border/60 bg-muted/30">
            <div className="flex items-center gap-2">
              <Badge
                variant="secondary"
                className="text-[10px] h-4.5 px-1.5 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 font-normal"
              >
                Căn cứ đã xác thực
              </Badge>
              <span className="text-[11px] text-muted-foreground">
                Ban hành: {selectedCitation?.publishedAt}
              </span>
            </div>
            <SheetTitle className="text-sm font-semibold text-foreground mt-1">
              {selectedCitation?.source}
            </SheetTitle>
            <SheetDescription className="text-xs text-muted-foreground">
              {selectedCitation?.section || "Văn bản chính thức"} · Trang{" "}
              {selectedCitation?.page}
            </SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div className="space-y-1.5">
              <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen className="size-3.5 text-primary" />
                <span>Trích đoạn nguyên văn trong tài liệu:</span>
              </span>
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-xs leading-relaxed text-foreground italic border-l-3 border-l-primary shadow-2xs">
                "{selectedCitation?.excerpt}"
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-border/40 text-xs">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Độ tin cậy & Nguồn trích xuất:
              </span>
              <div className="rounded-lg border border-border/50 bg-card p-3 space-y-2 text-[11px]">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">
                    Đơn vị ban hành:
                  </span>
                  <span className="font-medium text-foreground">
                    Trường Đại học Quy Nhơn
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">
                    Vị trí đối chiếu:
                  </span>
                  <span className="font-medium text-foreground">
                    Trang {selectedCitation?.page}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Xác thực:</span>
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">
                    Bản bóc tách & xuất bản chính thức
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="p-4 border-t border-border/60 bg-card flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                toast.info(
                  `Văn bản nguồn: ${selectedCitation?.source} (Lưu trữ điện tử)`,
                );
              }}
              className="text-xs h-8 gap-1.5"
            >
              <ExternalLink className="size-3.5" />
              <span>Xem tài liệu lưu trữ</span>
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
