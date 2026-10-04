import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Bot,
  Building,
  CheckCircle2,
  ChevronDown,
  Coins,
  Download,
  FileText,
  GraduationCap,
  HelpCircle,
  Library,
  Moon,
  PanelLeft,
  RotateCcw,
  Sparkles,
  Square,
  SquarePen,
  Sun,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { useTheme } from "@/app/theme-provider";
import { ChatMessage } from "@/components/ai/chat-message";
import { CitationSheet } from "@/components/ai/citation-sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useChatHistory } from "@/hooks/use-chat-history";
import { type ChatCitation, useRAGStream } from "@/hooks/use-rag-stream";
import {
  downloadMarkdownFile,
  formatConversationToMarkdown,
} from "@/lib/export-markdown";
import { getAssistant, listAssistants } from "@/services/assistants-api";
import type { AssistantItem } from "@/types/assistants";
import { ChatHistorySidebar } from "./chat-history-sidebar";

interface PublicChatViewProps {
  assistantSlug: string;
  initialQuestion?: string;
}

interface PromptSuggestion {
  text: string;
  category: string;
  icon: React.ReactNode;
}

function getCategoryIcon(category?: string, code?: string) {
  const cat = (category || code || "").toLowerCase();
  if (cat.includes("admission") || cat.includes("tuyen_sinh")) {
    return <GraduationCap className="size-5" />;
  }
  if (
    cat.includes("regulation") ||
    cat.includes("quy_che") ||
    cat.includes("dao_tao")
  ) {
    return <BookOpen className="size-5" />;
  }
  if (cat.includes("library") || cat.includes("thu_vien")) {
    return <Library className="size-5" />;
  }
  if (
    cat.includes("exam") ||
    cat.includes("khao_thi") ||
    cat.includes("ngan_hang")
  ) {
    return <HelpCircle className="size-5" />;
  }
  return <Bot className="size-5" />;
}

function getCategorizedPrompts(
  assistantCode: string,
  sampleQuestions: string[],
): PromptSuggestion[] {
  const code = assistantCode.toLowerCase();
  if (code.includes("admission") || code.includes("tuyen_sinh")) {
    return [
      {
        text: "Điểm chuẩn các ngành Sư phạm Toán và CNTT năm gần nhất?",
        category: "Điểm chuẩn",
        icon: (
          <GraduationCap className="size-3.5 text-teal-600 dark:text-teal-400" />
        ),
      },
      {
        text: "Các phương thức xét tuyển thẳng và học bạ THPT năm 2026?",
        category: "Xét tuyển",
        icon: (
          <FileText className="size-3.5 text-blue-600 dark:text-blue-400" />
        ),
      },
      {
        text: "Chính sách hỗ trợ học phí & sinh hoạt phí SV Sư phạm theo Nghị định 116?",
        category: "Học bổng & Học phí",
        icon: <Coins className="size-3.5 text-amber-600 dark:text-amber-400" />,
      },
      {
        text: "Thủ tục và chi phí đăng ký ở Ký túc xá QNU cho tân sinh viên?",
        category: "Ký túc xá",
        icon: (
          <Building className="size-3.5 text-purple-600 dark:text-purple-400" />
        ),
      },
    ];
  }
  if (
    code.includes("regulation") ||
    code.includes("quy_che") ||
    code.includes("dao_tao")
  ) {
    return [
      {
        text: "Điều kiện và thủ tục để được xét tốt nghiệp sớm hoặc học vượt tiến độ?",
        category: "Tiến độ học",
        icon: (
          <BookOpen className="size-3.5 text-teal-600 dark:text-teal-400" />
        ),
      },
      {
        text: "Quy định về bảo lưu kết quả học tập và thời hạn tối đa là bao lâu?",
        category: "Học vụ",
        icon: (
          <FileText className="size-3.5 text-blue-600 dark:text-blue-400" />
        ),
      },
      {
        text: "Cách tính điểm rèn luyện và xét học bổng khuyến khích học tập?",
        category: "Học bổng",
        icon: <Coins className="size-3.5 text-amber-600 dark:text-amber-400" />,
      },
      {
        text: "Xử lý vắng thi kết thúc học phần có lý do chính đáng như thế nào?",
        category: "Khảo thí",
        icon: (
          <HelpCircle className="size-3.5 text-purple-600 dark:text-purple-400" />
        ),
      },
    ];
  }

  // Fallback cho các trợ lý khác
  const fallbackIcons = [
    <GraduationCap
      key="1"
      className="size-3.5 text-teal-600 dark:text-teal-400"
    />,
    <FileText key="2" className="size-3.5 text-blue-600 dark:text-blue-400" />,
    <Coins key="3" className="size-3.5 text-amber-600 dark:text-amber-400" />,
    <BookOpen
      key="4"
      className="size-3.5 text-purple-600 dark:text-purple-400"
    />,
  ];

  if (sampleQuestions.length > 0) {
    return sampleQuestions.slice(0, 4).map((q, idx) => ({
      text: q,
      category: "Gợi ý",
      icon: fallbackIcons[idx % fallbackIcons.length],
    }));
  }

  return [
    {
      text: "Trợ lý có thể hỗ trợ những thủ tục nghiệp vụ nào?",
      category: "Nghiệp vụ",
      icon: fallbackIcons[0],
    },
    {
      text: "Vui lòng tóm tắt các quy định và chính sách mới nhất.",
      category: "Quy chế",
      icon: fallbackIcons[1],
    },
    {
      text: "Thông tin liên hệ các phòng ban chuyên trách của Nhà trường?",
      category: "Liên hệ",
      icon: fallbackIcons[2],
    },
    {
      text: "Quy trình giải quyết các vướng mắc học vụ thông thường?",
      category: "Hướng dẫn",
      icon: fallbackIcons[3],
    },
  ];
}

export function PublicChatView({
  assistantSlug,
  initialQuestion,
}: PublicChatViewProps) {
  const navigate = useNavigate();
  const { resolvedTheme, setTheme } = useTheme();
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const [input, setInput] = React.useState("");
  const [selectedCitation, setSelectedCitation] =
    React.useState<ChatCitation | null>(null);
  const [sidebarOpen, setSidebarOpen] = React.useState<boolean>(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth >= 1024;
    }
    return true;
  });

  // Load assistant details
  const { data: assistant, isLoading: isLoadingAssistant } =
    useQuery<AssistantItem>({
      queryKey: ["public-assistant", assistantSlug],
      queryFn: async () => {
        try {
          return await getAssistant(assistantSlug);
        } catch {
          const list = await listAssistants();
          const found = list.find(
            (a) =>
              a.code === assistantSlug ||
              a.id === assistantSlug ||
              a.code?.toLowerCase() === assistantSlug.toLowerCase(),
          );
          if (found) return found;
          throw new Error(`Không tìm thấy trợ lý với mã: ${assistantSlug}`);
        }
      },
    });

  // Load all assistants for switcher
  const { data: allAssistants = [] } = useQuery<AssistantItem[]>({
    queryKey: ["public-assistants-all"],
    queryFn: () => listAssistants(),
  });

  const assistantCode = assistant?.code || assistant?.id || assistantSlug;

  // Chat History Hook
  const {
    threads,
    currentThreadId,
    currentThread,
    groupedThreads,
    createNewThread,
    selectThread,
    saveThreadMessages,
    renameThread,
    deleteThread,
    clearAllThreads,
  } = useChatHistory(assistantCode);

  // RAG Stream Hook
  const {
    messages,
    setMessages,
    sendMessage,
    isStreaming,
    stopStreaming,
    clearMessages,
  } = useRAGStream({
    assistantCode,
    tenantId: "tenant_qnu",
  });

  // Load active thread messages into canvas when thread changes
  const prevThreadIdRef = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (currentThreadId !== prevThreadIdRef.current) {
      prevThreadIdRef.current = currentThreadId;
      if (currentThread && currentThread.messages.length > 0) {
        setMessages(currentThread.messages);
      } else {
        clearMessages();
      }
    }
  }, [currentThreadId, currentThread, setMessages, clearMessages]);

  // Persist messages to active thread when streaming completes or messages update
  const wasStreamingRef = React.useRef(false);
  React.useEffect(() => {
    if (wasStreamingRef.current && !isStreaming && messages.length > 0) {
      let targetId = currentThreadId;
      if (!targetId) {
        const newTh = createNewThread();
        targetId = newTh.id;
      }
      saveThreadMessages(targetId, messages);
    }
    wasStreamingRef.current = isStreaming;
  }, [
    isStreaming,
    messages,
    currentThreadId,
    createNewThread,
    saveThreadMessages,
  ]);

  // Handle auto-send initial question if provided via query param
  const initialSentRef = React.useRef(false);
  React.useEffect(() => {
    if (
      initialQuestion &&
      !initialSentRef.current &&
      assistant &&
      !isStreaming
    ) {
      initialSentRef.current = true;
      if (!currentThreadId) {
        createNewThread();
      }
      sendMessage(initialQuestion);
    }
  }, [
    initialQuestion,
    assistant,
    isStreaming,
    sendMessage,
    currentThreadId,
    createNewThread,
  ]);

  // Auto-scroll on new message
  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll triggered on message change
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  // Auto-adjust textarea height
  // biome-ignore lint/correctness/useExhaustiveDependencies: auto resize on input change
  React.useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(Math.max(scrollHeight, 44), 160)}px`;
    }
  }, [input]);

  const rawSampleQuestions = React.useMemo(() => {
    if (!assistant) return [];
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
    return [];
  }, [assistant]);

  const promptSuggestions = React.useMemo(() => {
    return getCategorizedPrompts(assistantCode, rawSampleQuestions);
  }, [assistantCode, rawSampleQuestions]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = (textToSend?: string) => {
    const text = (textToSend ?? input).trim();
    if (text && !isStreaming) {
      if (!currentThreadId) {
        createNewThread();
      }
      sendMessage(text);
      if (!textToSend) setInput("");
      textareaRef.current?.focus();
    }
  };

  const handleSelectThread = (threadId: string) => {
    if (isStreaming) {
      stopStreaming();
    }
    selectThread(threadId);
    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  };

  const handleNewThread = () => {
    if (isStreaming) {
      stopStreaming();
    }
    createNewThread();
    clearMessages();
    setInput("");
    toast.info("Đã tạo cuộc trò chuyện mới.");
    textareaRef.current?.focus();
    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  };

  const handleExportMarkdown = () => {
    if (messages.length === 0) {
      toast.info("Chưa có tin nhắn để xuất.");
      return;
    }
    const md = formatConversationToMarkdown({
      messages,
      assistantName: assistant?.name || "Trợ lý QNU",
      assistantCode,
      assistantDescription: assistant?.description,
    });
    downloadMarkdownFile(
      `hoi_thoai_${assistantCode}_${new Date().toISOString().slice(0, 10)}.md`,
      md,
    );
    toast.success("Đã tải tệp nội dung cuộc trò chuyện (.md) về máy!");
  };

  const handleSwitchAssistant = (slug: string) => {
    void navigate({ to: `/chat/${slug}` });
  };

  // Reusable Floating Input Dock Component
  const renderInputDock = () => (
    <div className="w-full space-y-2">
      {/* Gemini Rounded Floating Box */}
      <div className="relative rounded-3xl border border-border/80 bg-muted/40 dark:bg-muted/20 backdrop-blur-md shadow-md focus-within:bg-background focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 transition-all p-3 flex flex-col gap-1.5">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Hỏi bất kỳ điều gì về ${assistant?.name || "QNU AI"}...`}
          rows={1}
          className="min-h-[46px] max-h-36 resize-none border-0 shadow-none focus-visible:ring-0 text-xs sm:text-sm py-2 px-2 bg-transparent leading-relaxed text-foreground placeholder:text-muted-foreground/70"
        />

        {/* Action Strip Inside Input */}
        <div className="flex items-center justify-between px-1">
          {/* Secondary tools */}
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/75">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-7 rounded-full text-muted-foreground hover:text-foreground hover:bg-background"
              onClick={handleNewThread}
              title="Tạo đoạn chat mới"
            >
              <RotateCcw className="size-3.5" />
            </Button>
            <span className="hidden sm:inline font-mono text-[10px]">
              Shift + Enter để xuống dòng
            </span>
          </div>

          {/* Send / Stop Streaming Button (ArrowUp style) */}
          <div className="flex items-center gap-1">
            {isStreaming ? (
              <Button
                size="icon"
                variant="destructive"
                className="size-9 rounded-full shadow-xs"
                onClick={stopStreaming}
                title="Dừng sinh phản hồi"
              >
                <Square className="size-4 fill-current" />
              </Button>
            ) : (
              <Button
                size="icon"
                className="size-9 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                disabled={!input.trim()}
                onClick={() => handleSend()}
                title="Gửi câu hỏi"
              >
                <ArrowUp className="size-4.5 stroke-[2.5]" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Disclaimer Caption */}
      <div className="text-center text-[10px] text-muted-foreground/70 px-2 select-none">
        Trợ lý AI QNU đối soát từ nguồn văn bản và quy chế chính thức của Trường
        Đại học Quy Nhơn.
      </div>
    </div>
  );

  if (isLoadingAssistant) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-2xl space-y-4">
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-64 w-full rounded-lg" />
          <Skeleton className="h-14 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  if (!assistant) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 text-center space-y-4">
        <Bot className="size-12 text-muted-foreground mx-auto" />
        <h2 className="text-lg font-bold text-foreground">
          Không tìm thấy Trợ lý AI
        </h2>
        <p className="text-xs text-muted-foreground max-w-sm">
          Trợ lý với mã "{assistantSlug}" có thể đã bị thay đổi hoặc chưa kích
          hoạt.
        </p>
        <Button size="sm" onClick={() => void navigate({ to: "/chat" })}>
          Quay lại Cổng Trợ Lý
        </Button>
      </div>
    );
  }

  return (
    <div className="h-screen w-full flex bg-background text-foreground overflow-hidden">
      {/* 1. Collapsible Chat History Sidebar */}
      <ChatHistorySidebar
        assistant={assistant}
        assistantCode={assistantCode}
        threads={threads}
        groupedThreads={groupedThreads}
        currentThreadId={currentThreadId}
        onSelectThread={handleSelectThread}
        onNewThread={handleNewThread}
        onRenameThread={renameThread}
        onDeleteThread={deleteThread}
        onClearAll={clearAllThreads}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        allAssistants={allAssistants}
        onSwitchAssistant={handleSwitchAssistant}
      />

      {/* 2. Main Chat Canvas */}
      <div className="flex-1 flex flex-col h-full min-w-0 bg-background relative overflow-hidden">
        {/* Top Header Navbar - Seamless without border-b like Gemini & ChatGPT */}
        <header className="h-14 shrink-0 bg-background/80 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between z-20">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            {/* Toggle Sidebar Button (shown when sidebar is collapsed) */}
            {!sidebarOpen && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8 rounded-lg text-muted-foreground hover:text-foreground shrink-0"
                onClick={() => setSidebarOpen(true)}
                title="Mở thanh lịch sử chat"
              >
                <PanelLeft className="size-4" />
              </Button>
            )}

            {/* Back to Portal (Mobile only) */}
            <Button
              variant="ghost"
              size="icon"
              className="size-8 rounded-lg text-muted-foreground hover:text-foreground lg:hidden"
              onClick={() => void navigate({ to: "/chat" })}
              title="Quay lại Cổng Trợ Lý"
            >
              <ArrowLeft className="size-4" />
            </Button>

            {/* Assistant Identifier & Selector */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-muted/70 text-left transition-colors cursor-pointer group"
                >
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    {getCategoryIcon(assistant.category, assistant.code)}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-xs sm:text-sm text-foreground truncate max-w-[160px] sm:max-w-md group-hover:text-primary transition-colors">
                        {assistant.name}
                      </span>
                      <ChevronDown className="size-3 text-muted-foreground group-hover:text-foreground shrink-0 transition-transform" />
                    </div>
                  </div>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-64 text-xs">
                <div className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Chuyển sang Trợ lý khác
                </div>
                <DropdownMenuSeparator />
                {allAssistants.map((ast) => (
                  <DropdownMenuItem
                    key={ast.id || ast.code}
                    onClick={() => handleSwitchAssistant(ast.code || ast.id)}
                    className="gap-2 cursor-pointer"
                  >
                    <div className="size-5 rounded bg-primary/10 text-primary flex items-center justify-center shrink-0">
                      {getCategoryIcon(ast.category, ast.code)}
                    </div>
                    <span className="truncate flex-1">{ast.name}</span>
                    {(ast.code === assistantCode ||
                      ast.id === assistantCode) && (
                      <CheckCircle2 className="size-3 text-primary shrink-0" />
                    )}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <Badge
              variant="outline"
              className="text-[10px] hidden sm:inline-flex items-center gap-1 text-primary border-primary/20 bg-primary/5 h-5 px-1.5"
            >
              <CheckCircle2 className="size-3" />
              <span>Chính thức QNU</span>
            </Badge>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
            {/* New Chat Button */}
            <Button
              variant="ghost"
              size="icon"
              className="size-8 rounded-lg text-muted-foreground hover:text-foreground"
              onClick={handleNewThread}
              title="Đoạn chat mới"
            >
              <SquarePen className="size-4" />
            </Button>

            {/* Export Markdown */}
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8 rounded-lg text-muted-foreground hover:text-foreground"
                onClick={handleExportMarkdown}
                title="Tải đoạn chat (.md)"
              >
                <Download className="size-4" />
              </Button>
            )}

            {/* Theme Toggle */}
            <Button
              variant="ghost"
              size="icon"
              className="size-8 rounded-lg text-muted-foreground hover:text-foreground"
              onClick={() =>
                setTheme(resolvedTheme === "dark" ? "light" : "dark")
              }
              title="Đổi giao diện Sáng / Tối"
            >
              {resolvedTheme === "dark" ? (
                <Sun className="size-4 text-amber-400" />
              ) : (
                <Moon className="size-4 text-muted-foreground" />
              )}
            </Button>
          </div>
        </header>

        {/* 3. Conversation Area or Gemini Empty State */}
        {messages.length === 0 ? (
          /* Google Gemini Style Empty State Hero (Liền mạch, không khoảng trống) */
          <main className="flex-1 overflow-y-auto px-4 sm:px-8 flex flex-col justify-end pb-4 sm:pb-6">
            <div className="max-w-3xl mx-auto w-full space-y-7 animate-in fade-in slide-in-from-bottom-2 duration-300">
              {/* Gemini Hero Typography */}
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary border border-primary/20 text-xs font-semibold shadow-2xs">
                  <Sparkles className="size-3.5" />
                  <span>Trợ lý AI ĐH Quy Nhơn</span>
                </div>
                <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight">
                  <span className="text-muted-foreground/60 block text-xl sm:text-2xl font-medium mb-1">
                    Xin chào bạn,
                  </span>
                  <span className="bg-gradient-to-r from-primary via-teal-500 to-emerald-400 bg-clip-text text-transparent">
                    Hôm nay tôi có thể giúp gì cho bạn?
                  </span>
                </h1>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed max-w-xl">
                  {assistant.description ||
                    "Hỏi đáp chính xác mọi thông tin tuyển sinh, quy chế, thủ tục và học vụ từ nguồn văn bản chính thức của Nhà trường."}
                </p>
              </div>

              {/* 2x2 Prompt Suggestions Grid (Gemini Style) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {promptSuggestions.map((item) => (
                  <button
                    key={item.text}
                    type="button"
                    onClick={() => handleSend(item.text)}
                    className="group text-left p-4 rounded-2xl bg-muted/40 hover:bg-muted/70 dark:bg-muted/20 dark:hover:bg-muted/40 border border-border/70 hover:border-primary/40 transition-all shadow-2xs flex flex-col justify-between gap-3 min-h-[96px] cursor-pointer"
                  >
                    <span className="text-xs sm:text-sm font-medium text-foreground/90 leading-relaxed group-hover:text-primary transition-colors">
                      {item.text}
                    </span>
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-1.5">
                        {item.icon}
                        <span>{item.category}</span>
                      </span>
                      <div className="size-6 rounded-full bg-background border border-border/70 flex items-center justify-center opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all text-primary shadow-2xs">
                        <ArrowUpRight className="size-3.5" />
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {/* Input Dock ngay sát bên dưới (không có khoảng cách hố đen) */}
              <div className="pt-1">{renderInputDock()}</div>
            </div>
          </main>
        ) : (
          /* Active Chat Stream View */
          <>
            <main className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 scroll-smooth">
              <div className="max-w-3xl mx-auto space-y-6">
                {messages.map((message) => (
                  <ChatMessage
                    key={message.id}
                    message={message}
                    assistantCode={assistantCode}
                    assistantName={assistant.name}
                    variant="natural"
                    onCitationClick={(citation) =>
                      setSelectedCitation(citation)
                    }
                    onSuggestedClick={(q) => handleSend(q)}
                    onRegenerate={() => {
                      const lastUserMsg = [...messages]
                        .reverse()
                        .find((m) => m.role === "user");
                      if (lastUserMsg) {
                        sendMessage(lastUserMsg.content);
                      }
                    }}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            </main>

            {/* Floating Input Dock at Bottom in Active Chat */}
            <footer className="shrink-0 p-3 sm:p-5 bg-gradient-to-t from-background via-background/95 to-transparent z-10">
              <div className="max-w-3xl mx-auto">{renderInputDock()}</div>
            </footer>
          </>
        )}

        {/* Citation Inspector Sheet */}
        <CitationSheet
          citation={selectedCitation}
          isOpen={Boolean(selectedCitation)}
          onOpenChange={(open) => {
            if (!open) setSelectedCitation(null);
          }}
        />
      </div>
    </div>
  );
}
