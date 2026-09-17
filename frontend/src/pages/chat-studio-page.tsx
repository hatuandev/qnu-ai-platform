import {
  BookOpen,
  FileText,
  GraduationCap,
  HelpCircle,
  Library,
  Paperclip,
  Send,
  SlidersHorizontal,
  Sparkles,
  Square,
  Trash2,
} from "lucide-react";
import type React from "react";
import { useRef, useState } from "react";
import { Attachment } from "../components/ai/attachment";
import { ChatMessage } from "../components/ai/chat-message";
import { CitationSheet } from "../components/ai/citation-sheet";
import { MessageScroller } from "../components/ai/message-scroller";
import { QuestionnaireCard } from "../components/ai/questionnaire-card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Separator } from "../components/ui/separator";
import { type ChatAttachment, useRAGStream } from "../hooks/use-rag-stream";

interface AssistantInfo {
  code: string;
  name: string;
  category: string;
  icon: React.ReactNode;
  description: string;
  quickPrompts: string[];
}

const ASSISTANTS: AssistantInfo[] = [
  {
    code: "admissions",
    name: "Trợ lý Tuyển sinh QNU",
    category: "Đào tạo & Tuyển sinh",
    icon: <GraduationCap className="h-4 w-4" />,
    description: "Giải đáp chỉ tiêu, điểm chuẩn, phương thức xét tuyển & học phí năm 2025.",
    quickPrompts: [
      "Điểm chuẩn ngành Công nghệ thông tin năm 2024 là bao nhiêu?",
      "Học phí ngành Sư phạm Toán và chính sách hỗ trợ NĐ 116?",
      "Chỉ tiêu và các tổ hợp xét tuyển ngành Kỹ thuật phần mềm?",
    ],
  },
  {
    code: "regulations",
    name: "Trợ lý Quy chế Học vụ",
    category: "Đào tạo & Khảo thí",
    icon: <BookOpen className="h-4 w-4" />,
    description: "Tra cứu quy chế tín chỉ, đăng ký học phần, cảnh báo học vụ và xét tốt nghiệp.",
    quickPrompts: [
      "Số tín chỉ tối thiểu sinh viên cần đăng ký trong một học kỳ chính?",
      "Điều kiện và tiêu chuẩn nhận học bổng khuyến khích loại Xuất sắc?",
      "Quy định về chuẩn đầu ra tiếng Anh B1 (VSTEP) tốt nghiệp?",
    ],
  },
  {
    code: "library",
    name: "Trợ lý Thư viện Số QNU",
    category: "Học liệu & Nghiên cứu",
    icon: <Library className="h-4 w-4" />,
    description: "Tra cứu giáo trình, bài báo khoa học Scopus, ScienceDirect & quy định mượn trả.",
    quickPrompts: [
      "Quy định về thời hạn mượn và số lượng sách tối đa cho sinh viên?",
      "Cách truy cập cơ sở dữ liệu ScienceDirect từ ngoài trường?",
      "Thời gian mở cửa khu tự học tầng 2 Thư viện?",
    ],
  },
  {
    code: "drafting",
    name: "Trợ lý Soạn thảo Văn bản",
    category: "Hành chính & Pháp chế",
    icon: <FileText className="h-4 w-4" />,
    description: "Hỗ trợ soạn thảo tờ trình, quyết định, công văn chuẩn Nghị định 30/2020/NĐ-CP.",
    quickPrompts: [
      "Quy cách căn lề và định dạng tiêu ngữ theo Nghị định 30/2020/NĐ-CP?",
      "Mẫu quyết định khen thưởng sinh viên đạt thành tích xuất sắc?",
      "Soạn thảo thông báo triệu tập cuộc họp giao ban đơn vị?",
    ],
  },
  {
    code: "question_bank",
    name: "Trợ lý Ngân hàng Đề thi",
    category: "Khảo thí & Đảm bảo chất lượng",
    icon: <HelpCircle className="h-4 w-4" />,
    description: "Biên soạn câu hỏi trắc nghiệm theo 4 mức Bloom, ma trận CLO và xuất Excel.",
    quickPrompts: [
      "Biên soạn 1 câu hỏi trắc nghiệm Bloom mức Vận dụng học phần CSDL?",
      "Tạo câu hỏi trắc nghiệm về kiến trúc Microservices và RESTful API?",
      "Giải thích ma trận tương quan giữa chuẩn đầu ra CLO và Bloom?",
    ],
  },
];

export const ChatStudioPage: React.FC = () => {
  const [selectedCode, setSelectedCode] = useState<string>(() => {
    const requestedCode = new URLSearchParams(window.location.search).get("assistant");
    return ASSISTANTS.some((assistant) => assistant.code === requestedCode)
      ? (requestedCode as string)
      : "admissions";
  });
  const [inputPrompt, setInputPrompt] = useState<string>("");
  const [pendingAttachments, setPendingAttachments] = useState<ChatAttachment[]>([]);
  const [showQuestionnaireDemo, setShowQuestionnaireDemo] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeAssistant = ASSISTANTS.find((a) => a.code === selectedCode) || ASSISTANTS[0];

  const {
    messages,
    isStreaming,
    activeCitation,
    setActiveCitation,
    sendMessage,
    stopStreaming,
    clearMessages,
  } = useRAGStream({
    assistantCode: selectedCode,
  });

  const handleSend = async () => {
    if (!inputPrompt.trim() && pendingAttachments.length === 0) return;
    const promptToSend = inputPrompt;
    const attachmentsToSend = [...pendingAttachments];

    setInputPrompt("");
    setPendingAttachments([]);

    await sendMessage(promptToSend, attachmentsToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const newAttachments: ChatAttachment[] = Array.from(files).map((file, idx) => ({
      id: `att_${Date.now()}_${idx}`,
      name: file.name,
      size: file.size,
      type: file.type || "application/octet-stream",
      ocrStatus: "completed",
    }));

    setPendingAttachments((prev) => [...prev, ...newAttachments]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleRemoveAttachment = (id: string) => {
    setPendingAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  return (
    <div className="flex h-[calc(100vh-var(--topbar-height)-2rem)] flex-col lg:flex-row gap-4">
      {/* Left Sidebar: Assistant Selector & Config */}
      <div className="w-full lg:w-72 shrink-0 flex flex-col gap-3 rounded-surface border border-border bg-card p-3.5 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-border/80">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h2 className="font-bold text-xs uppercase tracking-wider text-foreground">
              05 Trợ lý Chuyên trách
            </h2>
          </div>
          <Badge variant="outline" className="text-[10px] font-mono">
            v1alpha1
          </Badge>
        </div>

        <div className="flex flex-col gap-1.5 flex-1 overflow-y-auto pr-1">
          {ASSISTANTS.map((ast) => {
            const isSelected = ast.code === selectedCode;
            return (
              <button
                key={ast.code}
                type="button"
                onClick={() => {
                  setSelectedCode(ast.code);
                  clearMessages();
                }}
                className={`w-full text-left p-2.5 rounded-control border text-xs transition-all cursor-pointer flex items-start gap-2.5 ${
                  isSelected
                    ? "bg-primary/10 border-primary text-foreground font-semibold shadow-xs"
                    : "bg-muted/40 hover:bg-muted/80 border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <span
                  className={`p-1.5 rounded-micro shrink-0 mt-0.5 ${
                    isSelected
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {ast.icon}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold">{ast.name}</p>
                  <p className="text-[10px] text-muted-foreground line-clamp-1 mt-0.5">
                    {ast.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        <Separator />

        {/* Feature toggles */}
        <div className="space-y-2 pt-1 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground flex items-center gap-1 text-[11px]">
              <SlidersHorizontal className="h-3 w-3" />
              Thẻ trắc nghiệm Bloom
            </span>
            <Button
              variant={showQuestionnaireDemo ? "default" : "outline"}
              size="sm"
              onClick={() => setShowQuestionnaireDemo((prev) => !prev)}
              className="h-6 text-[10px] px-2"
            >
              {showQuestionnaireDemo ? "Đang bật" : "Bật thử nghiệm"}
            </Button>
          </div>
          <p className="text-[10px] text-muted-foreground leading-normal">
            Trợ lý kết nối trực tiếp bộ nhớ RAG Qdrant + Postgres FTS tiếng Việt với Reciprocal Rank
            Fusion.
          </p>
        </div>
      </div>

      {/* Main Chat Studio */}
      <div className="flex-1 flex flex-col min-w-0 rounded-surface border border-border bg-card shadow-xs overflow-hidden">
        {/* Chat Studio Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-control bg-primary text-primary-foreground font-semibold">
              {activeAssistant.icon}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-foreground">{activeAssistant.name}</h1>
                <Badge variant="success" className="text-[10px] h-4 px-1.5">
                  Đã kết nối
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">{activeAssistant.description}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              onClick={clearMessages}
              className="h-8 text-xs text-muted-foreground hover:text-foreground gap-1"
              title="Xóa phiên hội thoại"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Làm mới</span>
            </Button>
          </div>
        </div>

        {/* Messages Scroll Area */}
        <MessageScroller isStreaming={isStreaming} className="bg-background/40">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 max-w-xl mx-auto space-y-4">
              <div className="p-3 rounded-full bg-primary/10 text-primary">
                {activeAssistant.icon}
              </div>
              <div className="space-y-1">
                <h3 className="font-bold text-foreground text-sm">
                  Xin chào! Tôi là {activeAssistant.name}
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Tôi được huấn luyện dựa trên toàn bộ cơ sở dữ liệu tri thức chính thức của Trường
                  Đại học Quy Nhơn. Hãy đặt câu hỏi hoặc chọn các câu hỏi gợi ý bên dưới:
                </p>
              </div>

              {/* Quick Prompts */}
              <div className="grid grid-cols-1 gap-2 w-full pt-2">
                {activeAssistant.quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => sendMessage(prompt)}
                    className="p-2.5 rounded-control bg-card hover:bg-muted border border-border/80 text-left text-xs text-foreground/90 hover:text-primary transition-all shadow-2xs hover:shadow-xs flex items-center justify-between group cursor-pointer"
                  >
                    <span>💡 {prompt}</span>
                    <Send className="h-3 w-3 opacity-0 group-hover:opacity-100 text-primary transition-opacity shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4 max-w-4xl mx-auto w-full">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  assistantCode={selectedCode}
                  assistantName={activeAssistant.name}
                  onCitationClick={(cite) => setActiveCitation(cite)}
                  onRegenerate={() => {
                    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
                    if (lastUserMsg) {
                      sendMessage(lastUserMsg.content, lastUserMsg.attachments);
                    }
                  }}
                  onSuggestedClick={(q) => sendMessage(q)}
                />
              ))}

              {/* Bloom Questionnaire Demo Card */}
              {showQuestionnaireDemo && (
                <div className="max-w-2xl mx-auto pt-2">
                  <QuestionnaireCard
                    questionNumber={1}
                    bloomLevel="Vận dụng"
                    clo="CLO 3.2: Chuẩn hóa lược đồ quan hệ CSDL"
                    question="Cho lược đồ quan hệ R(A, B, C, D, E) với tập phụ thuộc hàm F = {A -> B, B -> C, C -> D, D -> E}. Khóa chính tối thiểu của lược đồ quan hệ R là gì?"
                    options={[
                      { key: "A", text: "Tập thuộc tính {A}" },
                      { key: "B", text: "Tập thuộc tính {A, B}" },
                      { key: "C", text: "Tập thuộc tính {B, C, D}" },
                      { key: "D", text: "Tập thuộc tính {A, E}" },
                    ]}
                    correctKey="A"
                    explanation="Vì bao đóng của A: A+ = {A, B, C, D, E} chứa toàn bộ tập thuộc tính của lược đồ R. Do đó A là siêu khóa duy nhất và tối thiểu."
                    citationTitle="Giáo trình Cơ sở Dữ liệu QNU (NXB ĐHQG)"
                  />
                </div>
              )}
            </div>
          )}
        </MessageScroller>

        {/* Input & Action Bar */}
        <div className="p-3 border-t border-border bg-card space-y-2">
          {/* Pending Attachments List */}
          {pendingAttachments.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pb-1">
              {pendingAttachments.map((att) => (
                <Attachment key={att.id} attachment={att} onRemove={handleRemoveAttachment} />
              ))}
            </div>
          )}

          <div className="flex items-end gap-2 bg-muted/40 rounded-control p-2 border border-border focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20 transition-all">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              multiple
              className="hidden"
              accept=".pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg"
            />

            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground shrink-0 rounded-micro"
              title="Đính kèm tài liệu (PDF, Word, Excel, Ảnh)"
            >
              <Paperclip className="h-4 w-4" />
            </Button>

            <textarea
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Nhắn tin với ${activeAssistant.name}... (Nhấn Enter để gửi, Shift+Enter xuống dòng)`}
              rows={1}
              className="flex-1 resize-none bg-transparent border-0 p-1 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none max-h-32 min-h-[32px] leading-relaxed"
            />

            {isStreaming ? (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={stopStreaming}
                className="h-8 px-3 text-xs gap-1.5 shrink-0 rounded-control"
              >
                <Square className="h-3 w-3 fill-current" />
                <span>Dừng</span>
              </Button>
            ) : (
              <Button
                type="button"
                variant="default"
                size="sm"
                onClick={handleSend}
                disabled={!inputPrompt.trim() && pendingAttachments.length === 0}
                className="h-8 px-3 text-xs gap-1.5 shrink-0 rounded-control"
              >
                <Send className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Gửi</span>
              </Button>
            )}
          </div>

          <div className="flex items-center justify-between text-[10px] text-muted-foreground px-1">
            <span>
              Mô hình chính: <strong className="text-foreground">GPT-4o Mini</strong> • Dự phòng:{" "}
              <strong className="text-foreground">Gemini 1.5 Flash</strong>
            </span>
            <span className="hidden sm:inline">
              Trích dẫn căn cứ xác thực 100% tài liệu ĐH Quy Nhơn
            </span>
          </div>
        </div>
      </div>

      {/* Grounding Citation Drawer */}
      <CitationSheet
        citation={activeCitation}
        isOpen={activeCitation !== null}
        onOpenChange={(open) => {
          if (!open) setActiveCitation(null);
        }}
      />
    </div>
  );
};
