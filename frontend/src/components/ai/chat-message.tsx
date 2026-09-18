import {
  BookOpen,
  Bot,
  Check,
  Copy,
  Download,
  FileSpreadsheet,
  FileText,
  GraduationCap,
  HelpCircle,
  Library,
  RotateCcw,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  User,
  Zap,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import type { ChatCitation, ChatMessageItem } from "../../hooks/use-rag-stream";
import { cn } from "../../lib/utils";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Attachment } from "./attachment";
import { ChatBubble } from "./chat-bubble";

export interface ChatMessageProps {
  message: ChatMessageItem;
  assistantCode?: string;
  assistantName?: string;
  onCitationClick?: (citation: ChatCitation) => void;
  onRegenerate?: () => void;
  onSuggestedClick?: (question: string) => void;
  className?: string;
}

function getAssistantIcon(code?: string) {
  switch (code?.toLowerCase()) {
    case "admissions":
      return <GraduationCap className="h-4 w-4" />;
    case "regulations":
      return <BookOpen className="h-4 w-4" />;
    case "library":
      return <Library className="h-4 w-4" />;
    case "drafting":
      return <FileText className="h-4 w-4" />;
    case "question-bank":
      return <HelpCircle className="h-4 w-4" />;
    default:
      return <Bot className="h-4 w-4" />;
  }
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  assistantCode = "admissions",
  assistantName = "Trợ lý Tuyển sinh QNU",
  onCitationClick,
  onRegenerate,
  onSuggestedClick,
  className,
}) => {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  if (isUser) {
    return (
      <div className={cn("flex items-start justify-end gap-3 max-w-4xl ml-auto group", className)}>
        <div className="flex flex-col items-end gap-1.5 max-w-[85%] sm:max-w-2xl">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground pr-1">
            <span>Bạn</span>
            <span>•</span>
            <span>{message.timestamp}</span>
          </div>

          <ChatBubble content={message.content} senderRole="user" className="rounded-br-micro" />

          {message.attachments && message.attachments.length > 0 && (
            <div className="flex flex-wrap justify-end gap-1.5 mt-1">
              {message.attachments.map((att) => (
                <Attachment key={att.id} attachment={att} />
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-center h-8 w-8 rounded-full bg-muted border border-border text-foreground font-semibold text-xs shrink-0 mt-0.5">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className={cn("flex items-start gap-3 max-w-4xl group", className)}>
      <div className="flex items-center justify-center h-8 w-8 rounded-full bg-primary/10 border border-primary/30 text-primary font-semibold text-xs shrink-0 mt-0.5">
        {getAssistantIcon(assistantCode)}
      </div>

      <div className="flex flex-col gap-2 flex-1 min-w-0">
        {/* Assistant header */}
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground pl-1">
          <span className="font-semibold text-foreground text-xs">{assistantName}</span>
          <Badge
            variant="outline"
            className="text-[10px] h-4.5 px-1.5 bg-primary/5 text-primary border-primary/20"
          >
            QNU.AI
          </Badge>
          <span>•</span>
          <span>{message.timestamp}</span>

          {message.latencyMs !== undefined && message.latencyMs > 0 && (
            <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground ml-auto sm:ml-0">
              <Zap className="h-3 w-3 text-warning" />
              {message.latencyMs} ms
            </span>
          )}
        </div>

        {/* Message Bubble */}
        <ChatBubble
          content={message.content}
          senderRole="assistant"
          isStreaming={message.status === "streaming"}
        />

        {/* Exported Document Artifacts (.docx, .pdf) */}
        {message.artifacts && message.artifacts.length > 0 && (
          <div className="mt-2 p-3 rounded-surface border border-primary/20 bg-primary/5 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
              <Download className="h-4 w-4" />
              <span>
                {message.artifacts.some((a) => a.name.endsWith(".xlsx") || a.type.includes("sheet"))
                  ? `Ma trận đề thi kết xuất (${message.artifacts.length} tệp tải về):`
                  : `Tài liệu kết xuất (${message.artifacts.length} tệp tải về):`}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.artifacts.map((art) => (
                <a
                  key={art.id}
                  href={art.url || "#"}
                  download={art.name}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-control bg-card hover:bg-muted border border-border shadow-xs hover:border-primary/40 text-xs transition-all cursor-pointer group/art"
                >
                  {art.type.includes("pdf") || art.name.endsWith(".pdf") ? (
                    <FileText className="h-4 w-4 text-red-500 shrink-0" />
                  ) : art.type.includes("sheet") ||
                    art.type.includes("excel") ||
                    art.name.endsWith(".xlsx") ||
                    art.name.endsWith(".xls") ? (
                    <FileSpreadsheet className="h-4 w-4 text-emerald-600 shrink-0" />
                  ) : (
                    <FileText className="h-4 w-4 text-blue-600 shrink-0" />
                  )}
                  <div className="flex flex-col text-left">
                    <span className="font-semibold text-foreground group-hover/art:text-primary transition-colors">
                      {art.name}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {art.size > 0 ? `${(art.size / 1024).toFixed(1)} KB` : "Sẵn sàng"} • Nhấp để
                      tải về
                    </span>
                  </div>
                  <Download className="h-3.5 w-3.5 text-muted-foreground group-hover/art:text-primary ml-1 shrink-0" />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Citation Badges */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-1 space-y-1.5">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5 text-primary" />
              Căn cứ minh chứng ({message.citations.length} nguồn văn bản):
            </div>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((cite, index) => (
                <button
                  key={cite.id || `cite-${index}`}
                  type="button"
                  onClick={() => onCitationClick?.(cite)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-control bg-primary/5 hover:bg-primary/15 text-primary border border-primary/20 text-xs font-medium transition-colors cursor-pointer text-left"
                  title="Nhấp để xem chi tiết minh chứng đối chiếu văn bản gốc"
                >
                  <span className="font-bold text-[10px] bg-primary text-primary-foreground rounded-micro px-1 py-0.2">
                    [{index + 1}]
                  </span>
                  <span className="truncate max-w-[200px] sm:max-w-[260px]">{cite.title}</span>
                  {cite.article && (
                    <span className="text-[10px] text-primary/70">({cite.article})</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Suggested Follow-up Questions */}
        {message.suggestedQuestions &&
          message.suggestedQuestions.length > 0 &&
          message.status === "completed" && (
            <div className="mt-2 space-y-1.5">
              <span className="text-[11px] font-medium text-muted-foreground">
                Gợi ý câu hỏi liên quan tiếp theo:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {message.suggestedQuestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => onSuggestedClick?.(q)}
                    className="text-left text-xs px-2.5 py-1 rounded-control bg-muted/60 hover:bg-muted text-foreground/80 hover:text-primary border border-border/80 transition-colors cursor-pointer"
                  >
                    💡 {q}
                  </button>
                ))}
              </div>
            </div>
          )}

        {/* Actions Toolbar */}
        {message.status === "completed" && (
          <div className="flex items-center gap-1 pt-1 opacity-80 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
              title="Sao chép câu trả lời"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-success" />
                  <span className="text-[11px] text-success">Đã chép</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  <span className="text-[11px]">Sao chép</span>
                </>
              )}
            </Button>

            {onRegenerate && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRegenerate}
                className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
                title="Tạo lại câu trả lời"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span className="text-[11px]">Tạo lại</span>
              </Button>
            )}

            <div className="flex items-center gap-0.5 ml-auto">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFeedback(feedback === "up" ? null : "up")}
                className={cn(
                  "h-7 w-7 p-0 text-muted-foreground hover:text-foreground",
                  feedback === "up" && "text-primary bg-primary/10"
                )}
                title="Hữu ích"
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFeedback(feedback === "down" ? null : "down")}
                className={cn(
                  "h-7 w-7 p-0 text-muted-foreground hover:text-foreground",
                  feedback === "down" && "text-destructive bg-destructive/10"
                )}
                title="Chưa chính xác"
              >
                <ThumbsDown className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
