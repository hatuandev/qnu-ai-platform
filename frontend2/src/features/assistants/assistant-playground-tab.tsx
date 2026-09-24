import {
  ArrowRight,
  BookOpen,
  Bot,
  CheckCircle2,
  Clock,
  Layers,
  Lightbulb,
  Loader2,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import * as React from "react";
import { ChatMessage } from "@/components/ai/chat-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { type ChatCitation, useRAGStream } from "@/hooks/use-rag-stream";
import type { AssistantItem } from "@/types/assistants";

interface AssistantPlaygroundTabProps {
  assistant: AssistantItem;
  className?: string;
}

export function AssistantPlaygroundTab({
  assistant,
  className,
}: AssistantPlaygroundTabProps) {
  const assistantCode = assistant.code || assistant.id;
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const [selectedCitation, setSelectedCitation] =
    React.useState<ChatCitation | null>(null);
  const [input, setInput] = React.useState("");

  const { messages, sendMessage, isStreaming, clearMessages } = useRAGStream({
    assistantCode,
    tenantId: "tenant_qnu",
  });

  const sampleQuestions = React.useMemo(() => {
    if (
      Array.isArray(assistant.sample_questions) &&
      assistant.sample_questions.length > 0
    ) {
      return assistant.sample_questions;
    }
    if (
      Array.isArray(assistant.config?.sample_questions) &&
      assistant.config.sample_questions.length > 0
    ) {
      return assistant.config.sample_questions;
    }
    return [
      `Trợ lý ${assistant.name} có thể hỗ trợ những nghiệp vụ gì?`,
      "Vui lòng tóm tắt các quy định hoặc thông tin mới nhất.",
    ];
  }, [assistant]);

  // Auto scroll to bottom on new message
  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll triggered on message change
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  // Latest assistant message for inspector
  const latestAssistantMessage = React.useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i];
    }
    return null;
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isStreaming) {
        sendMessage(input.trim());
        setInput("");
      }
    }
  };

  const handleSend = () => {
    if (input.trim() && !isStreaming) {
      sendMessage(input.trim());
      setInput("");
    }
  };

  const handleSuggestedClick = (question: string) => {
    if (!isStreaming) {
      sendMessage(question);
    }
  };

  return (
    <div className={`grid grid-cols-1 lg:grid-cols-3 gap-4 ${className || ""}`}>
      {/* 1. Main Chat Area (2 Columns) */}
      <Card className="lg:col-span-2 flex flex-col h-[650px] border-border/80 shadow-xs overflow-hidden">
        {/* Chat Header Bar */}
        <CardHeader className="py-2.5 px-4 border-b border-border flex flex-row items-center justify-between shrink-0 bg-muted/20">
          <div className="flex items-center gap-2.5">
            <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
              <Bot className="size-4" />
            </div>
            <div>
              <CardTitle className="text-xs font-bold text-foreground">
                Thử Nghiệm Sandbox / {assistant.name}
              </CardTitle>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="font-mono text-[10px] text-muted-foreground">
                  {assistant.config?.model_policy?.primary_model || "Mặc định"}
                </span>
                <span className="size-1 rounded-full bg-emerald-500" />
                <span className="text-[10px] text-muted-foreground">
                  Kho: {assistant.collection_id || "Chưa gán"}
                </span>
              </div>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
            onClick={clearMessages}
            title="Xóa lịch sử cuộc trò chuyện"
          >
            <RotateCcw className="size-3" />
            <span>Làm mới</span>
          </Button>
        </CardHeader>

        {/* Message Scroller */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto space-y-4 py-8">
              <div className="size-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <Sparkles className="size-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-foreground">
                  Khung Thử Nghiệm Trợ Lý AI
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Trò chuyện trực tiếp với Trợ lý để kiểm thử độ chính xác,
                  trích dẫn minh chứng văn bản và tính năng rào chắn an toàn
                  TM-08.
                </p>
              </div>

              {/* Sample Question Chips */}
              <div className="w-full pt-2 space-y-2 text-left">
                <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1.5">
                  <Lightbulb className="size-3 text-amber-500" />
                  Câu hỏi gợi ý mẫu:
                </span>
                <div className="flex flex-col gap-1.5">
                  {sampleQuestions.map((q) => (
                    <button
                      type="button"
                      key={q}
                      onClick={() => handleSuggestedClick(q)}
                      className="text-left text-xs p-2.5 rounded-lg border border-border bg-card hover:border-primary/40 hover:bg-primary/5 transition-all flex items-center justify-between group cursor-pointer"
                    >
                      <span className="line-clamp-1 text-foreground/90 group-hover:text-primary">
                        {q}
                      </span>
                      <ArrowRight className="size-3.5 text-muted-foreground group-hover:text-primary shrink-0 ml-2" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  assistantCode={assistant.category}
                  assistantName={assistant.name}
                  onCitationClick={(cit) => setSelectedCitation(cit)}
                  onSuggestedClick={handleSuggestedClick}
                />
              ))}

              {isStreaming && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground py-2 pl-3">
                  <Loader2 className="size-3.5 animate-spin text-primary" />
                  <span>Đang suy luận và truy xuất RAG...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-border bg-background">
          <div className="flex items-end gap-2 bg-muted/40 p-2 rounded-lg border border-border focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Nhập câu hỏi thử nghiệm với ${assistant.name} (Enter để gửi)...`}
              rows={2}
              className="min-h-[44px] max-h-32 border-0 bg-transparent p-0 text-xs focus-visible:ring-0 shadow-none resize-none"
            />
            <Button
              type="button"
              size="sm"
              className="h-8 px-3 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 shrink-0"
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
            >
              {isStreaming ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Send className="size-3.5" />
              )}
              <span>Gửi</span>
            </Button>
          </div>
        </div>
      </Card>

      {/* 2. Side Inspector Card (1 Column) */}
      <Card className="flex flex-col h-[650px] border-border/80 shadow-xs overflow-hidden">
        <CardHeader className="py-2.5 px-4 border-b border-border bg-muted/20">
          <CardTitle className="text-xs font-bold text-foreground flex items-center gap-1.5">
            <ShieldCheck className="size-4 text-primary" />
            <span>Đối Soát RAG & Groundedness</span>
          </CardTitle>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          {/* Grounding Telemetry */}
          <div className="rounded-lg border border-border p-3 space-y-2 bg-card">
            <span className="text-[11px] font-semibold text-muted-foreground block">
              Trạng thái kiểm định câu trả lời:
            </span>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Chuẩn TM-08:</span>
              <Badge
                variant="outline"
                className="text-success border-success/30 font-medium"
              >
                <CheckCircle2 className="size-3 mr-1" />
                Faithfulness ≥ 0.90
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Thời gian phản hồi:</span>
              <span className="font-mono text-foreground font-medium flex items-center gap-1">
                <Clock className="size-3 text-muted-foreground" />
                {latestAssistantMessage?.latencyMs
                  ? `${latestAssistantMessage.latencyMs} ms`
                  : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Kho dữ liệu:</span>
              <span className="font-mono text-muted-foreground truncate max-w-[140px]">
                {assistant.collection_id || "Chưa gắn"}
              </span>
            </div>
          </div>

          {/* Citations Inspector */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-foreground flex items-center gap-1">
                <BookOpen className="size-3.5 text-primary" />
                Trích dẫn văn bản gốc (
                {latestAssistantMessage?.citations?.length || 0})
              </span>
            </div>

            {latestAssistantMessage?.citations &&
            latestAssistantMessage.citations.length > 0 ? (
              <div className="space-y-2">
                {latestAssistantMessage.citations.map((cit) => (
                  <button
                    type="button"
                    key={cit.id}
                    onClick={() => setSelectedCitation(cit)}
                    className={`w-full p-2.5 rounded-lg border text-left cursor-pointer transition-all ${
                      selectedCitation?.id === cit.id
                        ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                        : "border-border hover:border-primary/40 bg-card"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <span className="font-semibold text-foreground text-[11px] truncate">
                        {cit.document_name || cit.title}
                      </span>
                      {cit.page && (
                        <Badge
                          variant="secondary"
                          className="text-[9px] px-1 h-4"
                        >
                          Trang {cit.page}
                        </Badge>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground line-clamp-3 leading-relaxed">
                      "{cit.excerpt}"
                    </p>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg p-3">
                <Layers className="size-5 mx-auto mb-1 opacity-50" />
                <p className="text-[11px]">
                  Chưa có trích dẫn nào được sinh cho lượt hỏi này.
                </p>
              </div>
            )}
          </div>

          {/* Citation Detail Modal / Box if selected */}
          {selectedCitation && (
            <div className="rounded-lg border border-primary/30 bg-primary/5 p-3 space-y-1.5 animate-in fade-in">
              <span className="text-[10px] font-bold text-primary uppercase tracking-wider block">
                Chi tiết trích dẫn đã chọn:
              </span>
              <p className="font-semibold text-foreground text-xs">
                {selectedCitation.document_name}
              </p>
              <p className="text-[11px] text-foreground/80 leading-relaxed italic bg-background p-2 rounded border">
                "{selectedCitation.excerpt}"
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
