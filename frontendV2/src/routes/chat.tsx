import { createFileRoute } from "@tanstack/react-router";
import {
  BookOpen,
  Bot,
  Check,
  ChevronRight,
  Copy,
  ExternalLink,
  Globe,
  GraduationCap,
  Loader2,
  MoreHorizontal,
  Plus,
  QrCode,
  RotateCw,
  Send,
  Share2,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  User,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

export const Route = createFileRoute("/chat")({
  component: ChatPage,
});

type Citation = {
  id: string;
  source: string;
  page: number;
  section?: string;
  excerpt: string;
  publishedAt: string;
  verified: boolean;
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
      "Chỉ tiêu tuyển sinh và phương thức xét tuyển ngành Công nghệ thông tin năm 2026 như thế nào?",
  },
  {
    icon: BookOpen,
    title: "Mức học phí các khối ngành",
    prompt:
      "Mức học phí năm học 2026 - 2027 của Trường Đại học Quy Nhơn được tính theo mức nào?",
  },
  {
    icon: ShieldCheck,
    title: "Xét tuyển thẳng & Ưu tiên",
    prompt:
      "Quy định xét tuyển thẳng đối với học sinh đạt giải học sinh giỏi và chứng chỉ ngoại ngữ quốc tế?",
  },
  {
    icon: Sparkles,
    title: "Chính sách học bổng",
    prompt:
      "Chính sách học bổng khuyến khích học tập và miễn giảm học phí cho tân sinh viên?",
  },
];

const INITIAL_MESSAGES: ChatMsg[] = [
  {
    id: "msg_1",
    role: "user",
    content:
      "Trường Đại học Quy Nhơn được thành lập vào năm nào và hiện đào tạo những khối ngành chính nào?",
    timestamp: "10:15",
  },
  {
    id: "msg_2",
    role: "assistant",
    content:
      "Trường Đại học Quy Nhơn được thành lập theo **Quyết định số 02/HĐBT** ngày **13/7/1981** của Hội đồng Bộ trưởng, trên cơ sở tiền thân là Cơ sở Đại học Sư phạm Quy Nhơn (thành lập ngày 21/12/1977 theo Quyết định số 1842/QĐ của Bộ Giáo dục).\n\nĐến ngày **30/10/2003**, Thủ tướng Chính phủ ban hành Quyết định số 221/2003/QĐ-TTg đổi tên trường thành **Trường Đại học Quy Nhơn**, đánh dấu bước chuyển mình thành trường đại học đa ngành, đa lĩnh vực.\n\nHiện nay, nhà trường đào tạo các khối ngành chính gồm:\n- **Khối Sư phạm & Giáo dục:** Đào tạo giáo viên các cấp từ Mầm non, Tiểu học đến THPT.\n- **Khối Khoa học Tự nhiên & Công nghệ:** Công nghệ thông tin, Kỹ thuật phần mềm, Trí tuệ nhân tạo, Hóa học, Sinh học ứng dụng.\n- **Khối Kinh tế & Quản lý:** Quản trị kinh doanh, Tài chính - Ngân hàng, Kế toán, Kinh tế số.\n- **Khối Khoa học Xã hội & Du lịch:** Ngôn ngữ Anh, Quản trị dịch vụ du lịch và lữ hành, Luật.",
    timestamp: "10:15",
    citations: [
      {
        id: "cite_1",
        source: "Du_lieu_RAG_Truong_Dai_hoc_Quy_Nhon_2026.docx",
        page: 1,
        section: "Lịch sử hình thành & Sứ mạng",
        excerpt:
          "Ngày 13/7/1981, Hội đồng Bộ trưởng ban hành Quyết định số 02/HĐBT thành lập Trường Đại học Sư phạm Quy Nhơn. Ngày 30/10/2003, Thủ tướng Chính phủ ban hành Quyết định 221/2003/QĐ-TTg đổi tên thành Trường Đại học Quy Nhơn phát triển theo định hướng đa ngành...",
        publishedAt: "10/11/2026",
        verified: true,
      },
      {
        id: "cite_2",
        source: "Thong_tin_TSDH_cap_nhat_2026.pdf",
        page: 3,
        section: "Khối ngành & Lĩnh vực đào tạo",
        excerpt:
          "Trường Đại học Quy Nhơn hiện đào tạo hơn 45 ngành đại học chính quy thuộc các khối ngành Sư phạm, Khoa học Tự nhiên, Kỹ thuật Công nghệ, Kinh tế và Khoa học Xã hội...",
        publishedAt: "11/11/2026",
        verified: true,
      },
    ],
    feedback: null,
  },
];

function ChatPage() {
  const [messages, setMessages] = useState<ChatMsg[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(
    null,
  );
  const [isPublishDialogOpen, setIsPublishDialogOpen] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedEmbed, setCopiedEmbed] = useState(false);

  const handleSend = (textToSend?: string) => {
    const content = (textToSend || input).trim();
    if (!content || isTyping) return;

    const userMsg: ChatMsg = {
      id: `msg_u_${Date.now()}`,
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

    // Mock response simulating RAG retrieval & synthesis
    setTimeout(() => {
      const assistantMsg: ChatMsg = {
        id: `msg_a_${Date.now()}`,
        role: "assistant",
        content: `Dựa trên cơ sở dữ liệu tri thức chính thức của Trường Đại học Quy Nhơn:\n\nVề câu hỏi **"${content}"**:\n\nNhà trường đã công bố chỉ tiêu, phương thức tuyển sinh và học phí chính thức cho năm học 2026 - 2027. Mọi thông tin đều được thẩm định và đối chiếu theo Quyết định số 1842 và Đề án tuyển sinh ban hành ngày 10/11/2026. Thí sinh được đăng ký không giới hạn nguyện vọng xét tuyển và ưu tiên xét tuyển thẳng cho học sinh có chứng chỉ ngoại ngữ quốc tế (IELTS từ 5.5 hoặc VSTEP bậc 3 trở lên).`,
        timestamp: new Date().toLocaleTimeString("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        citations: [
          {
            id: `cite_${Date.now()}_1`,
            source: "De_an_tuyen_sinh_2026.pdf",
            page: 4,
            section: "Chỉ tiêu & Phương thức xét tuyển 2026",
            excerpt:
              "Năm 2026, Trường Đại học Quy Nhơn áp dụng 4 phương thức tuyển sinh chính quy: Xét điểm thi tốt nghiệp THPT 2026, xét học bạ THPT, xét tuyển thẳng theo quy chế của Bộ GD&ĐT và xét điểm thi đánh giá năng lực của ĐHQG TP.HCM...",
            publishedAt: "10/11/2026",
            verified: true,
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
        ? "Cảm ơn bạn đã xác nhận câu trả lời chính xác!"
        : "Đã ghi nhận phản hồi để đội ngũ biên soạn rà soát nguồn tri thức.",
    );
  };

  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content);
    toast.success("Đã sao chép nội dung câu trả lời.");
  };

  const handleCopyPublicLink = () => {
    navigator.clipboard.writeText("https://ai.qnu.edu.vn/p/tuyen-sinh-2026");
    setCopiedLink(true);
    toast.success("Đã sao chép liên kết công khai vào clipboard!");
    setTimeout(() => setCopiedLink(false), 2000);
  };

  const handleCopyEmbedCode = () => {
    const code = `<script src="https://ai.qnu.edu.vn/widget.js" data-bot-id="tuyen-sinh-2026" async></script>`;
    navigator.clipboard.writeText(code);
    setCopiedEmbed(true);
    toast.success("Đã sao chép mã nhúng widget vào clipboard!");
    setTimeout(() => setCopiedEmbed(false), 2000);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col bg-background">
      {/* 1. Header Chat chuẩn mực: Branding ĐH Quy Nhơn, Metadata Trợ lý, Nút Xuất bản & Menu */}
      <header className="flex h-14 items-center justify-between border-b border-border/60 bg-card px-4 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20">
            <Bot className="size-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold text-foreground truncate">
                Trợ lý Tuyển sinh 2026
              </h1>
              <Badge
                variant="secondary"
                className="text-[10px] h-4.5 px-1.5 font-normal bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20"
              >
                Đã xuất bản
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground truncate">
              Trung Tâm Số & Học Liệu · Kho tri thức: Dữ liệu tuyển sinh QNU
              2026
            </p>
          </div>
        </div>

        {/* Cụm hành động Header: 1 Primary CTA Xuất bản + Hội thoại mới + Menu ⋯ duy nhất */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="default"
            size="sm"
            onClick={() => setIsPublishDialogOpen(true)}
            className="h-8 gap-1.5 text-xs shadow-2xs font-medium"
          >
            <Share2 className="size-3.5" />
            <span className="hidden sm:inline">Xuất bản & Chia sẻ</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setMessages([])}
            className="h-8 gap-1.5 text-xs"
            title="Bắt đầu hội thoại mới"
          >
            <Plus className="size-3.5" />
            <span className="hidden sm:inline">Hội thoại mới</span>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="size-8 p-0 text-muted-foreground hover:text-foreground"
              >
                <MoreHorizontal className="size-4" />
                <span className="sr-only">Thao tác khác</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <DropdownMenuItem
                onClick={() => {
                  setMessages(INITIAL_MESSAGES);
                  toast.info("Đã nạp lại hội thoại mẫu.");
                }}
                className="text-xs gap-2"
              >
                <RotateCw className="size-3.5" />
                <span>Nạp hội thoại mẫu</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  toast.info(
                    "Đang chuyển hướng tới Kho tri thức: Dữ liệu tuyển sinh QNU 2026",
                  );
                }}
                className="text-xs gap-2"
              >
                <BookOpen className="size-3.5" />
                <span>Xem kho tri thức</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => setMessages([])}
                className="text-xs gap-2 text-destructive focus:text-destructive"
              >
                <Plus className="size-3.5" />
                <span>Xóa toàn bộ tin nhắn</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* 2. Vùng hiển thị tin nhắn (Message Thread) hoặc Trạng thái ban đầu (Starter Prompts) */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl w-full mx-auto space-y-6">
          {messages.length === 0 ? (
            /* Trạng thái chào đón & Starter Prompts */
            <div className="py-8 space-y-6 animate-in fade-in-50 duration-300">
              <div className="text-center space-y-2">
                <div className="size-12 rounded-2xl bg-primary/10 text-primary mx-auto flex items-center justify-center border border-primary/20 shadow-2xs">
                  <GraduationCap className="size-6" />
                </div>
                <h2 className="text-base font-semibold text-foreground">
                  Trợ lý Tư vấn Tuyển sinh & Đào tạo QNU
                </h2>
                <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                  Hệ thống trả lời thông minh dựa trên Đề án tuyển sinh, biểu
                  phí và quy chế đào tạo chính thức đã xuất bản của Trường Đại
                  học Quy Nhơn.
                </p>
              </div>

              {/* Lưới câu hỏi gợi ý */}
              <div className="space-y-2.5">
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground px-1">
                  Câu hỏi thường gặp:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {STARTER_PROMPTS.map((item) => (
                    <button
                      type="button"
                      key={item.title}
                      onClick={() => handleSend(item.prompt)}
                      className="group flex flex-col items-start p-3 rounded-xl border border-border/60 bg-card hover:bg-muted/40 hover:border-primary/40 transition-all text-left shadow-2xs cursor-pointer"
                    >
                      <div className="flex items-center gap-1.5 text-xs font-medium text-foreground group-hover:text-primary transition-colors">
                        <item.icon className="size-3.5 text-primary" />
                        <span>{item.title}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                        {item.prompt}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Danh sách tin nhắn */
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5 border border-primary/20">
                    <Bot className="size-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] sm:max-w-[80%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                    msg.role === "user"
                      ? "rounded-tr-xs bg-primary text-primary-foreground font-normal shadow-2xs"
                      : "rounded-tl-xs bg-card border border-border/60 text-foreground space-y-3 shadow-2xs"
                  }`}
                >
                  <div className="whitespace-pre-line leading-relaxed">
                    {msg.content}
                  </div>

                  {/* Khối trích dẫn chứng cứ (Evidence Citations) */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2.5 border-t border-border/40 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground font-medium">
                        <span className="flex items-center gap-1.5">
                          <BookOpen className="size-3.5 text-primary" />
                          <span>Căn cứ trích dẫn ({msg.citations.length})</span>
                        </span>
                        <span className="text-[10px] text-muted-foreground/80">
                          Bấm để xem văn bản nguồn
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-1.5">
                        {msg.citations.map((cite, index) => (
                          <button
                            type="button"
                            key={cite.id}
                            onClick={() => setSelectedCitation(cite)}
                            className="inline-flex items-center gap-1.5 rounded-md border border-border/70 bg-muted/50 hover:bg-muted hover:border-primary/50 px-2 py-1 text-[11px] text-foreground transition-all cursor-pointer group"
                          >
                            <span className="size-4 rounded bg-primary/10 text-primary text-[10px] font-semibold flex items-center justify-center shrink-0">
                              {index + 1}
                            </span>
                            <span className="truncate max-w-[180px] sm:max-w-[240px]">
                              {cite.source}
                            </span>
                            <span className="text-muted-foreground text-[10px]">
                              · Tr. {cite.page}
                            </span>
                            <ChevronRight className="size-3 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Thanh công cụ đánh giá & sao chép cho tin nhắn của Bot */}
                  {msg.role === "assistant" && (
                    <div className="flex items-center justify-between pt-1 border-t border-border/30 text-[11px] text-muted-foreground">
                      <span className="text-[10px] text-muted-foreground/70">
                        {msg.timestamp} · Đối chiếu dữ liệu chính thức
                      </span>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopyContent(msg.content)}
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
                          title="Câu trả lời hữu ích & chính xác"
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
                          title="Câu trả lời thiếu hoặc chưa chính xác"
                        >
                          <ThumbsDown className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="size-8 rounded-lg bg-muted text-muted-foreground flex items-center justify-center shrink-0 mt-0.5 border border-border/50">
                    <User className="size-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Chỉ báo trạng thái suy nghĩ & tìm kiếm */}
          {isTyping && (
            <div className="flex gap-3 justify-start items-center text-xs text-muted-foreground animate-in fade-in-50 duration-200">
              <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20">
                <Bot className="size-4" />
              </div>
              <div className="flex items-center gap-2 bg-card border border-border/60 rounded-xl px-3.5 py-2.5 shadow-2xs">
                <Loader2 className="size-3.5 animate-spin text-primary shrink-0" />
                <span className="text-[11px] font-medium text-foreground">
                  Đang tra cứu kho tri thức tuyển sinh & đối chiếu căn cứ...
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. Khung nhập liệu tinh gọn, phẳng (Flat Chat Input) */}
      <div className="border-t border-border/60 bg-card p-3 shrink-0">
        <div className="max-w-3xl mx-auto space-y-1.5">
          <div className="flex items-end gap-2 bg-muted/40 border border-border/60 rounded-xl p-1.5 focus-within:border-primary/60 focus-within:bg-background transition-colors shadow-2xs">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Nhập câu hỏi về chỉ tiêu, điểm sàn, phương thức xét tuyển, học phí..."
              rows={1}
              className="flex-1 min-h-[38px] max-h-32 resize-none border-0 bg-transparent px-3 py-2 text-xs placeholder:text-muted-foreground focus-visible:ring-0 shadow-none leading-relaxed"
            />
            <Button
              size="sm"
              onClick={() => handleSend()}
              disabled={!input.trim() || isTyping}
              className="h-8 px-3 gap-1.5 text-xs font-medium shrink-0 rounded-lg shadow-2xs"
            >
              <Send className="size-3.5" />
              <span className="hidden sm:inline">Gửi</span>
            </Button>
          </div>
          <p className="text-[10px] text-center text-muted-foreground/80">
            Nội dung do Trợ lý AI tổng hợp và trích dẫn trực tiếp từ các văn bản
            đã được phê duyệt của Trường Đại học Quy Nhơn.
          </p>
        </div>
      </div>

      {/* 4. Slide-over Sheet xem chi tiết bằng chứng trích dẫn (Evidence Viewer Drawer) */}
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
                Xuất bản: {selectedCitation?.publishedAt}
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
                <span>Trích đoạn nguyên văn:</span>
              </span>
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-3.5 text-xs leading-relaxed text-foreground italic border-l-3 border-l-primary shadow-2xs">
                "{selectedCitation?.excerpt}"
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-border/40 text-xs">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Thông tin truy vết nguồn:
              </span>
              <div className="rounded-lg border border-border/50 bg-card p-3 space-y-2 text-[11px]">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">
                    Cơ quan ban hành:
                  </span>
                  <span className="font-medium text-foreground">
                    Trường Đại học Quy Nhơn
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">
                    Trạng thái bóc tách:
                  </span>
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">
                    Hoàn tất · Đã xuất bản
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">
                    Vị trí tài liệu:
                  </span>
                  <span className="font-medium text-foreground">
                    Trang {selectedCitation?.page}
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
                  `Mở tệp ${selectedCitation?.source} trong Kho tri thức`,
                );
              }}
              className="text-xs h-8 gap-1.5"
            >
              <ExternalLink className="size-3.5" />
              <span>Xem tệp trong Kho tri thức</span>
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* 5. Dialog Xuất bản & Chia sẻ Trợ lý AI (Publish & Share Dialog) */}
      <Dialog open={isPublishDialogOpen} onOpenChange={setIsPublishDialogOpen}>
        <DialogContent className="sm:max-w-lg p-0 overflow-hidden">
          <DialogHeader className="p-5 pb-3 border-b border-border/60 bg-muted/20">
            <div className="flex items-center gap-2">
              <div className="size-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                <Globe className="size-4" />
              </div>
              <DialogTitle className="text-base font-semibold">
                Xuất bản & Chia sẻ Trợ lý AI
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted-foreground mt-1">
              Phát hành Trợ lý Tuyển sinh 2026 cho thí sinh, sinh viên và cổng
              thông tin trường.
            </DialogDescription>
          </DialogHeader>

          <div className="p-5 space-y-4">
            <Tabs defaultValue="link" className="w-full">
              <TabsList className="grid grid-cols-2 w-full h-8 mb-4">
                <TabsTrigger value="link" className="text-xs">
                  Liên kết công khai
                </TabsTrigger>
                <TabsTrigger value="widget" className="text-xs">
                  Mã nhúng Web
                </TabsTrigger>
              </TabsList>

              {/* Tab 1: Liên kết trực tiếp */}
              <TabsContent value="link" className="space-y-4 mt-0">
                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-foreground block">
                    Đường dẫn truy cập trực tiếp:
                  </span>
                  <div className="flex items-center gap-2">
                    <Input
                      readOnly
                      value="https://ai.qnu.edu.vn/p/tuyen-sinh-2026"
                      className="text-xs h-8 bg-muted/40 font-mono text-muted-foreground"
                    />
                    <Button
                      size="sm"
                      onClick={handleCopyPublicLink}
                      className="h-8 text-xs gap-1.5 shrink-0 px-3"
                    >
                      {copiedLink ? (
                        <Check className="size-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="size-3.5" />
                      )}
                      <span>{copiedLink ? "Đã chép" : "Sao chép"}</span>
                    </Button>
                  </div>
                </div>

                <div className="rounded-xl border border-border/60 bg-muted/30 p-3.5 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
                      <QrCode className="size-4 text-primary" />
                      <span>Mã QR Tra cứu tại sảnh</span>
                    </span>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      Quét trực tiếp trên điện thoại để mở cổng chat tuyển sinh.
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toast.success("Đã tải tệp mã QR (SVG)!")}
                    className="h-7 text-xs gap-1 shrink-0"
                  >
                    Tải mã QR
                  </Button>
                </div>
              </TabsContent>

              {/* Tab 2: Mã nhúng Widget */}
              <TabsContent value="widget" className="space-y-3 mt-0">
                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-foreground block">
                    Đoạn mã chèn vào website (HTML/JS):
                  </span>
                  <div className="relative">
                    <pre className="rounded-lg border border-border/60 bg-muted/60 p-3 text-[11px] font-mono text-foreground overflow-x-auto whitespace-pre-wrap leading-relaxed">
                      {`<script src="https://ai.qnu.edu.vn/widget.js" data-bot-id="tuyen-sinh-2026" async></script>`}
                    </pre>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Dán đoạn mã trên vào trước thẻ &lt;/body&gt; của trang tuyển
                    sinh (tuyensinh.qnu.edu.vn) để hiển thị bong bóng chat.
                  </p>
                </div>

                <Button
                  size="sm"
                  onClick={handleCopyEmbedCode}
                  className="w-full h-8 text-xs gap-1.5"
                >
                  {copiedEmbed ? (
                    <Check className="size-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="size-3.5" />
                  )}
                  <span>
                    {copiedEmbed
                      ? "Đã sao chép mã nhúng"
                      : "Sao chép mã nhúng widget"}
                  </span>
                </Button>
              </TabsContent>
            </Tabs>
          </div>

          <DialogFooter className="p-4 border-t border-border/60 bg-muted/20 sm:justify-between">
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <ShieldCheck className="size-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Chỉ trích xuất dữ liệu đã xuất bản</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsPublishDialogOpen(false)}
              className="text-xs h-8"
            >
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
