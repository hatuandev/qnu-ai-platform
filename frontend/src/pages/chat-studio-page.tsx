import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Bot,
  Download,
  FileText,
  GraduationCap,
  HelpCircle,
  Library,
  Loader2,
  Paperclip,
  Send,
  SlidersHorizontal,
  Sparkles,
  Square,
  Trash2,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "../components/admin/empty-state";
import { Attachment } from "../components/ai/attachment";
import { ChatMessage } from "../components/ai/chat-message";
import { CitationSheet } from "../components/ai/citation-sheet";
import { MessageScroller } from "../components/ai/message-scroller";
import { QuestionnaireCard } from "../components/ai/questionnaire-card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Separator } from "../components/ui/separator";
import { type ChatAttachment, useRAGStream } from "../hooks/use-rag-stream";
import { downloadMarkdownFile, formatConversationToMarkdown } from "../lib/export-markdown";
import { listAssistants } from "../services/assistants-api";
import { recordFeedbackVote } from "../services/conversations-api";

interface AssistantInfo {
  code: string;
  name: string;
  category: string;
  icon: React.ReactNode;
  description: string;
  quickPrompts: string[];
}

function getAssistantIcon(category: string, code: string): React.ReactNode {
  const normCategory = (category || "").toLowerCase();
  const normCode = (code || "").toLowerCase();
  if (
    normCode.includes("admission") ||
    normCategory.includes("tuyển sinh") ||
    normCategory === "admissions"
  ) {
    return <GraduationCap className="h-4 w-4" />;
  }
  if (
    normCode.includes("regulation") ||
    normCategory.includes("học vụ") ||
    normCategory === "academic"
  ) {
    return <BookOpen className="h-4 w-4" />;
  }
  if (
    normCode.includes("library") ||
    normCategory.includes("thư viện") ||
    normCategory === "resources"
  ) {
    return <Library className="h-4 w-4" />;
  }
  if (
    normCode.includes("draft") ||
    normCategory.includes("soạn thảo") ||
    normCategory === "administration"
  ) {
    return <FileText className="h-4 w-4" />;
  }
  if (
    normCode.includes("question") ||
    normCategory.includes("đề thi") ||
    normCategory === "examination"
  ) {
    return <HelpCircle className="h-4 w-4" />;
  }
  return <Bot className="h-4 w-4" />;
}

interface ChatStudioPageProps {
  initialAssistant?: string;
}

export const ChatStudioPage: React.FC<ChatStudioPageProps> = ({ initialAssistant }) => {
  const assistantsQuery = useQuery({
    queryKey: ["assistants", "chat-studio"],
    queryFn: () => listAssistants({ includeInactive: false }),
  });

  const assistantsList: AssistantInfo[] = useMemo(() => {
    const data = assistantsQuery.data;
    if (!data || data.length === 0) return [];
    return data.map((ast) => {
      const sampleQ =
        Array.isArray(ast.sample_questions) && ast.sample_questions.length > 0
          ? ast.sample_questions
          : Array.isArray(ast.config?.sample_questions) && ast.config.sample_questions.length > 0
            ? ast.config.sample_questions
            : [];
      return {
        code: ast.code,
        name: ast.name,
        category: ast.category,
        icon: getAssistantIcon(ast.category, ast.code),
        description: ast.description,
        quickPrompts:
          sampleQ.length > 0
            ? sampleQ
            : [
                `Xin chào! Tôi có thể giúp gì về ${ast.name}?`,
                "Thông tin chính sách và quy định liên quan?",
              ],
      };
    });
  }, [assistantsQuery.data]);

  const [selectedCode, setSelectedCode] = useState<string>(() => {
    if (initialAssistant) return initialAssistant;
    const requestedCode = new URLSearchParams(window.location.search).get("assistant");
    return requestedCode || "";
  });

  useEffect(() => {
    const requestedCode = new URLSearchParams(window.location.search).get("assistant");
    if (requestedCode && assistantsList.some((a) => a.code === requestedCode)) {
      if (selectedCode !== requestedCode) {
        setSelectedCode(requestedCode);
      }
    } else if (assistantsList.length > 0 && !assistantsList.some((a) => a.code === selectedCode)) {
      setSelectedCode(assistantsList[0].code);
    }
  }, [assistantsList, selectedCode]);

  const [inputPrompt, setInputPrompt] = useState<string>("");
  const [pendingAttachments, setPendingAttachments] = useState<ChatAttachment[]>([]);
  const [isUploadingFile, setIsUploadingFile] = useState<boolean>(false);
  const [showQuestionnaireDemo, setShowQuestionnaireDemo] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeAssistant =
    assistantsList.find((a) => a.code === selectedCode) || assistantsList[0] || null;

  const {
    messages,
    isStreaming,
    activeCitation,
    setActiveCitation,
    conversationId,
    sendMessage,
    stopStreaming,
    clearMessages,
  } = useRAGStream({
    assistantCode: selectedCode,
  });

  const handleFeedback = (msgId: string, vote: "up" | "down") => {
    const msgIndex = messages.findIndex((m) => m.id === msgId);
    const answerMsg = msgIndex >= 0 ? messages[msgIndex] : undefined;
    if (!answerMsg) return;
    const questionMsg = [...messages.slice(0, msgIndex)].reverse().find((m) => m.role === "user");
    void recordFeedbackVote({
      thread_id: conversationId ?? null,
      assistant_code: selectedCode,
      vote,
      question: questionMsg?.content.slice(0, 2000),
      answer: answerMsg.content.slice(0, 8000),
    }).catch(() => {
      /* best-effort: vote failures must not break chat */
    });
  };

  const handleExportMarkdown = () => {
    if (messages.length === 0) {
      toast.info("Chưa có nội dung cuộc trò chuyện để tải về.");
      return;
    }
    const mdContent = formatConversationToMarkdown({
      assistantName: activeAssistant?.name || "Trợ lý AI QNU",
      assistantCode: activeAssistant?.code || selectedCode,
      assistantDescription: activeAssistant?.description,
      messages,
    });
    const dateStr = new Date().toISOString().slice(0, 10);
    const filename = `hoi_thoai_${activeAssistant?.code || "chat"}_${dateStr}.md`;
    downloadMarkdownFile(filename, mdContent);
    toast.success(`Đã tải tệp Markdown "${filename}" thành công!`);
  };

  const handleSelectAssistant = (code: string) => {
    setSelectedCode(code);
    clearMessages();
    const url = new URL(window.location.href);
    url.searchParams.set("assistant", code);
    window.history.replaceState({}, "", url.toString());
  };

  const handleSend = async () => {
    if ((!inputPrompt.trim() && pendingAttachments.length === 0) || isUploadingFile) return;
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const fileList = Array.from(files);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    for (let idx = 0; idx < fileList.length; idx++) {
      const file = fileList[idx];
      const attachmentId = `att_${Date.now()}_${idx}`;
      const initialAttachment: ChatAttachment = {
        id: attachmentId,
        name: file.name,
        size: file.size,
        type: file.type || "application/octet-stream",
        ocrStatus: "processing",
      };
      setPendingAttachments((prev) => [...prev, initialAttachment]);

      try {
        setIsUploadingFile(true);
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("/platform/v1alpha1/ocr/extract", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          throw new Error(`OCR thất bại (${res.status})`);
        }

        const data = await res.json();
        const extractedText = data.raw_text || "";

        setPendingAttachments((prev) =>
          prev.map((att) =>
            att.id === attachmentId
              ? {
                  ...att,
                  ocrStatus: "completed",
                  textContent: extractedText,
                }
              : att
          )
        );
        toast.success(`Đã trích xuất văn bản tệp "${file.name}" thành công!`);
      } catch (uploadErr) {
        console.error("Lỗi trích xuất OCR:", uploadErr);
        setPendingAttachments((prev) =>
          prev.map((att) =>
            att.id === attachmentId
              ? {
                  ...att,
                  ocrStatus: "failed",
                }
              : att
          )
        );
        toast.error(`Không thể trích xuất nội dung từ tệp "${file.name}".`);
      } finally {
        setIsUploadingFile(false);
      }
    }
  };

  const handleRemoveAttachment = (id: string) => {
    setPendingAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  if (assistantsQuery.isLoading) {
    return (
      <div className="flex h-[calc(100vh-var(--topbar-height)-2rem)] items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-xs text-muted-foreground">Đang tải cấu hình Trợ lý AI...</p>
        </div>
      </div>
    );
  }

  if (assistantsList.length === 0 || !activeAssistant) {
    return (
      <div className="flex h-[calc(100vh-var(--topbar-height)-2rem)] items-center justify-center p-6">
        <EmptyState
          icon={Bot}
          title="Chưa có Trợ lý AI nào được kích hoạt"
          description="Hệ thống chưa tìm thấy trợ lý nào khả dụng. Vui lòng tạo Trợ lý AI mới hoặc kích hoạt trợ lý trong trang Quản trị Trợ lý."
          action={
            <Button
              className="mt-2"
              onClick={() => {
                window.location.href = "/assistants";
              }}
            >
              Quản lý Trợ lý AI
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-var(--topbar-height)-2rem)] flex-col lg:flex-row gap-4">
      {/* Left Sidebar: Assistant Selector & Config */}
      <div className="w-full lg:w-72 shrink-0 flex flex-col gap-3 rounded-surface border border-border bg-card p-3.5 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-border/80">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h2 className="font-bold text-xs uppercase tracking-wider text-foreground">
              {assistantsList.length.toString().padStart(2, "0")} Trợ lý AI
            </h2>
          </div>
          <Badge variant="outline" className="text-[10px] font-mono">
            v1alpha1
          </Badge>
        </div>

        <div className="flex flex-col gap-1.5 flex-1 overflow-y-auto pr-1">
          {assistantsList.map((ast) => {
            const isSelected = ast.code === selectedCode;
            return (
              <button
                key={ast.code}
                type="button"
                onClick={() => handleSelectAssistant(ast.code)}
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
              onClick={handleExportMarkdown}
              disabled={messages.length === 0}
              className="h-8 text-xs text-muted-foreground hover:text-foreground gap-1.5 cursor-pointer disabled:cursor-not-allowed"
              title="Tải nội dung cuộc trò chuyện dạng Markdown (.md)"
            >
              <Download className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Tải về (.md)</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={clearMessages}
              className="h-8 text-xs text-muted-foreground hover:text-foreground gap-1.5 cursor-pointer"
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
                  onFeedback={(vote) => handleFeedback(msg.id, vote)}
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
              disabled={isUploadingFile}
              className="hidden"
              accept=".pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg"
            />

            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={isUploadingFile}
              onClick={() => fileInputRef.current?.click()}
              className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground shrink-0 rounded-micro"
              title={
                isUploadingFile
                  ? "Đang trích xuất OCR..."
                  : "Đính kèm tài liệu (PDF, Word, Excel, Ảnh)"
              }
            >
              {isUploadingFile ? (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              ) : (
                <Paperclip className="h-4 w-4" />
              )}
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
                disabled={
                  (!inputPrompt.trim() && pendingAttachments.length === 0) || isUploadingFile
                }
                className="h-8 px-3 text-xs gap-1.5 shrink-0 rounded-control"
              >
                <Send className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Gửi</span>
              </Button>
            )}
          </div>

          <div className="flex items-center justify-between text-[10px] text-muted-foreground px-1">
            <span>
              Trợ lý: <strong className="text-foreground">{activeAssistant.name}</strong> • Chuyên
              môn: <strong className="text-foreground">{activeAssistant.category}</strong>
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
