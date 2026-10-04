import {
  ArrowRight,
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
  Lightbulb,
  RotateCcw,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  User,
  Zap,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import type { ChatCitation, ChatMessageItem } from "../../hooks/use-rag-stream";
import { cn } from "../../lib/utils";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";
import { Attachment } from "./attachment";
import { ChatBubble } from "./chat-bubble";

export interface ChatMessageProps {
  message: ChatMessageItem;
  assistantCode?: string;
  assistantName?: string;
  variant?: "card" | "natural";
  onCitationClick?: (citation: ChatCitation) => void;
  onRegenerate?: () => void;
  onSuggestedClick?: (question: string) => void;
  onFeedback?: (vote: "up" | "down") => void;
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
  variant = "natural",
  onCitationClick,
  onRegenerate,
  onSuggestedClick,
  onFeedback,
  className,
}) => {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const uniqueCitations = useMemo(() => {
    if (!message.citations) return [];
    const seen = new Set<string>();
    return message.citations.filter((cite) => {
      const key = `${cite.title}__${cite.document_name || ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [message.citations]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const handleDownloadArtifact = async (
    e: React.MouseEvent,
    art: { name: string; url?: string },
  ) => {
    e.preventDefault();
    e.stopPropagation();
    if (!art.url) return;

    try {
      const res = await fetch(art.url);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = art.name;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(blobUrl);
      }, 1000);
    } catch (err) {
      console.warn(
        "Direct blob download failed, falling back to direct navigation:",
        err,
      );
      const fallbackLink = document.createElement("a");
      fallbackLink.href = art.url;
      fallbackLink.download = art.name;
      document.body.appendChild(fallbackLink);
      fallbackLink.click();
      document.body.removeChild(fallbackLink);
    }
  };

  if (isUser) {
    return (
      <div
        className={cn(
          "flex items-start justify-end gap-3 max-w-4xl ml-auto group",
          className,
        )}
      >
        <div className="flex flex-col items-end gap-1.5 max-w-[85%] sm:max-w-2xl">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground pr-1">
            <span>Bạn</span>
            <span>•</span>
            <span>{message.timestamp}</span>
          </div>

          <ChatBubble
            content={message.content}
            senderRole="user"
            variant={variant}
            className={variant === "card" ? "rounded-br-micro" : undefined}
          />

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
          <span className="font-semibold text-foreground text-xs">
            {assistantName}
          </span>
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
          variant={variant}
          isStreaming={message.status === "streaming"}
        />

        {/* Exported Document Artifacts (.docx, .pdf) */}
        {message.artifacts && message.artifacts.length > 0 && (
          <div className="mt-2 p-3 rounded-surface border border-primary/20 bg-primary/5 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
              <Download className="h-4 w-4" />
              <span>
                Tài liệu kết xuất ({message.artifacts.length} tệp tải về):
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.artifacts.map((art) => (
                <Button
                  key={art.id}
                  variant="outline"
                  size="sm"
                  onClick={(e) => handleDownloadArtifact(e, art)}
                  title={`Tải về ${art.name}`}
                  className="h-auto py-1.5 px-3 rounded-md bg-card hover:bg-muted border border-border shadow-xs hover:border-primary/40 text-xs transition-all cursor-pointer group/art gap-2 text-left font-normal"
                >
                  {art.type.includes("pdf") || art.name.endsWith(".pdf") ? (
                    <FileText className="size-4 text-destructive shrink-0" />
                  ) : art.type.includes("sheet") ||
                    art.type.includes("excel") ||
                    art.name.endsWith(".xlsx") ||
                    art.name.endsWith(".xls") ? (
                    <FileSpreadsheet className="size-4 text-emerald-600 shrink-0" />
                  ) : (
                    <FileText className="size-4 text-blue-600 shrink-0" />
                  )}
                  <div className="flex flex-col text-left">
                    <span className="font-semibold text-foreground group-hover/art:text-primary transition-colors">
                      {art.name}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {art.size > 0
                        ? `${(art.size / 1024).toFixed(1)} KB`
                        : "Sẵn sàng"}{" "}
                      • Nhấp để tải về
                    </span>
                  </div>
                  <Download className="size-3.5 text-muted-foreground group-hover/art:text-primary ml-1 shrink-0" />
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* HITL Approval Pending Banner */}
        {message.status === "paused_for_approval" && (
          <div className="mt-2 p-3 rounded-surface border border-amber-500/30 bg-amber-500/10 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-amber-600 dark:text-amber-400">
                <ShieldCheck className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <span>
                  Tác vụ đang chờ cán bộ phê duyệt (Human-in-the-loop)
                </span>
              </div>
              <Badge
                variant="outline"
                className="text-[10px] font-mono border-amber-500/40 text-amber-600 dark:text-amber-400"
              >
                Pending Approval
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Yêu cầu đã được ghi nhận vào hàng đợi kiểm duyệt an toàn. Cán bộ
              quản trị có thể xem xét và phê duyệt tại Hộp thư Phê duyệt.
            </p>
            {message.approvalId && (
              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] font-mono text-muted-foreground">
                  Mã phê duyệt:{" "}
                  <strong className="text-foreground">
                    {message.approvalId}
                  </strong>
                </span>
                <a
                  href="/runs"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
                >
                  Mở Hộp thư Phê duyệt &rarr;
                </a>
              </div>
            )}
          </div>
        )}

        {/* Citation Badges (Deduplicated, Clean Academic Style, Zero Raw IDs) */}
        {uniqueCitations.length > 0 && (
          <div className="mt-1 space-y-1.5">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground">
              <ShieldCheck className="size-3.5 text-primary" />
              Căn cứ minh chứng ({uniqueCitations.length} nguồn văn bản):
            </div>
            <div className="flex flex-wrap gap-1.5">
              {uniqueCitations.map((cite, index) => {
                const isRawId =
                  cite.article &&
                  (/^doc_[a-f0-9]+/i.test(cite.article) ||
                    /^[a-f0-9]{8,}/i.test(cite.article));
                const displayArticle =
                  cite.article && !isRawId ? cite.article : null;
                return (
                  <Button
                    key={cite.id || `cite-${index}`}
                    variant="outline"
                    size="sm"
                    onClick={() => onCitationClick?.(cite)}
                    className="h-7 px-2.5 rounded-md border-border/80 bg-background hover:bg-muted/80 text-xs text-foreground/85 font-normal gap-1.5 shadow-2xs cursor-pointer text-left transition-colors"
                    title="Nhấp để xem chi tiết minh chứng đối chiếu văn bản gốc"
                  >
                    <span className="font-bold text-[10px] text-primary">
                      [{index + 1}]
                    </span>
                    <span className="truncate max-w-[200px] sm:max-w-[260px]">
                      {cite.title}
                    </span>
                    {displayArticle && (
                      <span className="text-[10px] text-muted-foreground">
                        ({displayArticle})
                      </span>
                    )}
                  </Button>
                );
              })}
            </div>
          </div>
        )}

        {/* Suggested Follow-up Questions (Interactive 1-Click Chips) */}
        {message.suggestedQuestions &&
          message.suggestedQuestions.length > 0 &&
          message.status === "completed" && (
            <div className="mt-2.5 space-y-1.5">
              <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                <Lightbulb className="size-3 text-primary shrink-0" />
                Gợi ý câu hỏi liên quan tiếp theo:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {message.suggestedQuestions.map((q) => (
                  <Button
                    key={q}
                    variant="outline"
                    size="sm"
                    onClick={() => onSuggestedClick?.(q)}
                    title="Nhấp để hỏi ngay câu này"
                    className="h-8 px-3 rounded-md text-left text-xs bg-background hover:bg-muted/70 text-foreground/90 hover:text-foreground border-border/80 shadow-2xs transition-colors cursor-pointer group/chip font-normal"
                  >
                    <ArrowRight className="size-3 text-primary shrink-0 group-hover/chip:translate-x-0.5 transition-transform" />
                    <span className="truncate max-w-[320px] sm:max-w-[420px]">
                      {q}
                    </span>
                  </Button>
                ))}
              </div>
            </div>
          )}

        {/* Actions Toolbar (Symmetrical Icon-Only with Radix Tooltips) */}
        {message.status === "completed" && (
          <div className="flex items-center gap-1 pt-1 opacity-80 group-hover:opacity-100 transition-opacity">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCopy}
                  className="size-7 rounded-md text-muted-foreground hover:text-foreground"
                  aria-label="Sao chép câu trả lời"
                >
                  {copied ? (
                    <Check className="size-3.5 text-success" />
                  ) : (
                    <Copy className="size-3.5" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">
                {copied ? "Đã sao chép!" : "Sao chép câu trả lời"}
              </TooltipContent>
            </Tooltip>

            {onRegenerate && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onRegenerate}
                    className="size-7 rounded-md text-muted-foreground hover:text-foreground"
                    aria-label="Tạo lại câu trả lời"
                  >
                    <RotateCcw className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs">
                  Tạo lại câu trả lời
                </TooltipContent>
              </Tooltip>
            )}

            <div className="flex items-center gap-0.5 ml-auto">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      const next = feedback === "up" ? null : "up";
                      setFeedback(next);
                      if (next) onFeedback?.(next);
                    }}
                    className={cn(
                      "size-7 rounded-md text-muted-foreground hover:text-foreground",
                      feedback === "up" && "text-primary bg-primary/10",
                    )}
                    aria-label="Hữu ích"
                  >
                    <ThumbsUp className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs">
                  Hữu ích
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      const next = feedback === "down" ? null : "down";
                      setFeedback(next);
                      if (next) onFeedback?.(next);
                    }}
                    className={cn(
                      "size-7 rounded-md text-muted-foreground hover:text-foreground",
                      feedback === "down" &&
                        "text-destructive bg-destructive/10",
                    )}
                    aria-label="Chưa chính xác"
                  >
                    <ThumbsDown className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs">
                  Chưa chính xác
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
