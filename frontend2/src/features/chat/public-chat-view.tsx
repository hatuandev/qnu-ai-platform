import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
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
  PenLine,
  Sparkles,
  Square,
  Sun,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { useTheme } from "@/app/theme-provider";
import { ChatMessage } from "@/components/ai/chat-message";
import { CitationSheet } from "@/components/ai/citation-sheet";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { useChatHistory } from "@/hooks/use-chat-history";
import {
  type ChatCitation,
  type ChatMessageItem,
  useRAGStream,
} from "@/hooks/use-rag-stream";
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

function formatAssistantDisplayName(name: string, code?: string): string {
  const c = (code || "").toLowerCase();
  const n = (name || "").toLowerCase();
  if (
    c.includes("admission") ||
    c.includes("tuyen_sinh") ||
    n.includes("tuyển sinh")
  ) {
    return "Trợ lý Tư vấn Tuyển sinh 2026";
  }
  if (
    c.includes("regulation") ||
    c.includes("quy_che") ||
    c.includes("academic") ||
    n.includes("quy chế") ||
    n.includes("học vụ")
  ) {
    return "Trợ lý Quy chế & Học vụ";
  }
  if (
    c.includes("library") ||
    c.includes("thu_vien") ||
    c.includes("resources") ||
    n.includes("thư viện") ||
    n.includes("học liệu")
  ) {
    return "Trợ lý Thư viện & Học liệu Số";
  }
  if (
    c.includes("draft") ||
    c.includes("soan_thao") ||
    c.includes("administration") ||
    n.includes("soạn thảo")
  ) {
    return "Trợ lý Soạn thảo Văn bản";
  }
  if (
    c.includes("exam") ||
    c.includes("khao_thi") ||
    c.includes("ngan_hang") ||
    c.includes("question") ||
    c.includes("cau_hoi") ||
    c.includes("de_thi") ||
    n.includes("câu hỏi") ||
    n.includes("ngân hàng") ||
    n.includes("khảo thí") ||
    n.includes("đề thi")
  ) {
    return "Trợ lý Ngân hàng Đề & Khảo thí";
  }
  return name.replace(
    /^Mô-đun trợ lý ảo\s*(tư vấn\s*|hỗ trợ\s*|tra cứu,\s*tư vấn\s*)?/i,
    "Trợ lý ",
  );
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

  // Load active thread messages into canvas on mount and when thread selection changes
  const prevThreadIdRef = React.useRef<string | null>(null);
  const isInitialMountRef = React.useRef(true);

  React.useEffect(() => {
    // Initial mount: load current thread's messages if present
    if (isInitialMountRef.current) {
      isInitialMountRef.current = false;
      prevThreadIdRef.current = currentThreadId;
      if (currentThread && currentThread.messages.length > 0) {
        setMessages(currentThread.messages);
      }
      return;
    }

    // Only switch messages if currentThreadId changed to another thread,
    // and never wipe in-flight streaming
    if (currentThreadId !== prevThreadIdRef.current) {
      prevThreadIdRef.current = currentThreadId;
      if (isStreaming) {
        return; // Protect active stream from cancellation
      }
      if (currentThread && currentThread.messages.length > 0) {
        setMessages(currentThread.messages);
      } else if (!currentThreadId) {
        clearMessages();
      }
    }
  }, [currentThreadId, currentThread, isStreaming, setMessages, clearMessages]);

  // Persist messages to active thread when streaming completes
  const wasStreamingRef = React.useRef(false);
  React.useEffect(() => {
    if (wasStreamingRef.current && !isStreaming && messages.length > 0) {
      const targetId = currentThreadId || prevThreadIdRef.current;
      if (targetId) {
        saveThreadMessages(targetId, messages);
      }
    }
    wasStreamingRef.current = isStreaming;
  }, [isStreaming, messages, currentThreadId, saveThreadMessages]);

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
      let targetId = currentThreadId;
      if (!targetId) {
        const newTh = createNewThread(initialQuestion);
        targetId = newTh.id;
        prevThreadIdRef.current = targetId;
      }
      const userMsgItem: ChatMessageItem = {
        id: `user-${Date.now()}`,
        role: "user",
        content: initialQuestion,
        timestamp: new Date().toLocaleTimeString("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      saveThreadMessages(targetId, [userMsgItem]);
      sendMessage(initialQuestion);
    }
  }, [
    initialQuestion,
    assistant,
    isStreaming,
    sendMessage,
    currentThreadId,
    createNewThread,
    saveThreadMessages,
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
      // Prevent premature submit during Vietnamese IME tone composition
      if (e.nativeEvent.isComposing) return;
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = (textToSend?: string) => {
    const text = (textToSend ?? input).trim();
    if (text && !isStreaming) {
      let targetId = currentThreadId;
      if (!targetId) {
        const newTh = createNewThread(text);
        targetId = newTh.id;
        prevThreadIdRef.current = targetId;
      }

      // Immediately save user message to thread to prevent data loss on unexpected close
      const userMsgItem: ChatMessageItem = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date().toLocaleTimeString("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      const existingMsgs = currentThread?.messages || [];
      saveThreadMessages(targetId, [...existingMsgs, userMsgItem]);

      sendMessage(text);
      if (!textToSend) setInput("");
      textareaRef.current?.focus();
    }
  };

  const handleSelectThread = (threadId: string) => {
    if (isStreaming) {
      stopStreaming();
    }
    const targetThread = threads.find((t) => t.id === threadId);
    selectThread(threadId);
    prevThreadIdRef.current = threadId;

    if (targetThread && targetThread.messages.length > 0) {
      setMessages(targetThread.messages);
    } else {
      clearMessages();
    }

    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  };

  const handleNewThread = () => {
    if (isStreaming) {
      stopStreaming();
    }
    const newTh = createNewThread();
    prevThreadIdRef.current = newTh.id;
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
          placeholder={`Hỏi bất kỳ điều gì về ${formatAssistantDisplayName(assistant?.name || "", assistant?.code) || "QNU AI"}...`}
          rows={1}
          className="min-h-[46px] max-h-36 resize-none border-0 shadow-none focus-visible:ring-0 text-xs sm:text-sm py-2 px-2 bg-transparent leading-relaxed text-foreground placeholder:text-muted-foreground/70"
        />

        {/* Action Strip Inside Input */}
        <div className="flex items-center justify-between px-1">
          {/* Keyboard hint */}
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/70 px-1 select-none">
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

  function PublicChatSkeleton() {
    return (
      <div className="h-screen w-full flex bg-background text-foreground overflow-hidden">
        {/* 1. Desktop Sidebar Skeleton (matches ChatHistorySidebar w-64) */}
        <aside className="w-64 min-w-[256px] h-full flex flex-col shrink-0 border-r border-border/70 bg-card/40 hidden lg:flex">
          {/* Header: Official Logo + Brand Title */}
          <div className="h-14 px-3 flex items-center justify-between shrink-0">
            <Link
              to="/chat"
              className="flex items-center gap-2 group cursor-pointer select-none text-inherit no-underline"
              title="Quay lại Cổng Trợ Lý QNU AI"
            >
              <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-white p-0.5 shadow-xs border border-border/60">
                <img
                  src="/logo.png"
                  alt="Logo Trường Đại học Quy Nhơn"
                  className="size-6 object-contain"
                />
              </div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm tracking-tight text-foreground">
                  QNU AI
                </span>
                <Sparkles className="size-3 text-primary/70 animate-pulse" />
              </div>
            </Link>
            <div className="size-8 rounded-md bg-muted/40 animate-pulse" />
          </div>

          {/* New Chat Button Skeleton */}
          <div className="px-3 pb-2 pt-1">
            <div className="h-9 w-full rounded-full bg-background border border-border/80 flex items-center px-4 gap-2 text-xs text-muted-foreground shadow-xs">
              <PenLine className="size-4 text-muted-foreground/60" />
              <span className="font-medium">Cuộc trò chuyện mới</span>
            </div>
          </div>

          {/* Thread List Skeletons */}
          <div className="flex-1 p-3 space-y-3 overflow-hidden">
            <div className="h-3 w-16 rounded bg-muted/40 animate-pulse" />
            <div className="space-y-1.5">
              <div className="h-8 w-full rounded-md bg-muted/40 animate-pulse" />
              <div className="h-8 w-5/6 rounded-md bg-muted/30 animate-pulse" />
              <div className="h-8 w-4/5 rounded-md bg-muted/30 animate-pulse" />
              <div className="h-8 w-full rounded-md bg-muted/20 animate-pulse" />
            </div>
          </div>

          {/* Footer Back link */}
          <div className="p-3 border-t border-border/50">
            <Link
              to="/chat"
              className="h-8 w-full rounded-md flex items-center px-2 gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="size-3.5" />
              <span>Cổng Trợ Lý QNU</span>
            </Link>
          </div>
        </aside>

        {/* 2. Main Chat Canvas Skeleton (matches Canvas layout exactly) */}
        <div className="flex-1 flex flex-col h-full min-w-0 bg-background relative overflow-hidden">
          {/* Top Header Navbar */}
          <header className="h-14 shrink-0 bg-background/80 backdrop-blur-md px-3 sm:px-4 flex items-center justify-between z-20">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 h-9 px-2.5 rounded-md bg-muted/30 border border-border/50">
                <div className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Sparkles className="size-3.5 text-primary animate-pulse" />
                </div>
                <div className="h-4 w-36 sm:w-48 rounded bg-muted/50 animate-pulse" />
                <ChevronDown className="size-3 text-muted-foreground/50 ml-1" />
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="size-8 rounded-md bg-muted/30 animate-pulse" />
              <div className="size-8 rounded-md bg-muted/30 animate-pulse" />
            </div>
          </header>

          {/* Empty State Hero Skeleton (Bottom-aligned Gemini style) */}
          <main className="flex-1 overflow-y-auto px-4 sm:px-8 flex flex-col justify-end pb-4 sm:pb-6">
            <div className="max-w-3xl mx-auto w-full space-y-7 animate-in fade-in duration-300">
              {/* Typography skeleton */}
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary border border-primary/20 text-xs font-semibold shadow-2xs">
                  <Sparkles className="size-3.5 text-primary animate-spin" />
                  <span>Đang kết nối Trợ lý AI QNU...</span>
                </div>
                <div className="space-y-2">
                  <div className="h-8 sm:h-10 w-2/3 rounded-lg bg-muted/50 animate-pulse" />
                  <div className="h-8 sm:h-10 w-4/5 rounded-lg bg-gradient-to-r from-muted/50 to-muted/20 animate-pulse" />
                </div>
                <div className="h-4 w-1/2 rounded bg-muted/30 animate-pulse pt-1" />
              </div>

              {/* 4 Prompt Cards Skeleton */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="p-4 rounded-lg bg-card/60 border border-border/80 flex flex-col justify-between gap-3 min-h-[96px] shadow-2xs"
                  >
                    <div className="space-y-1.5">
                      <div className="h-3.5 w-4/5 rounded bg-muted/40 animate-pulse" />
                      <div className="h-3.5 w-3/5 rounded bg-muted/30 animate-pulse" />
                    </div>
                    <div className="h-3 w-20 rounded bg-muted/30 animate-pulse" />
                  </div>
                ))}
              </div>

              {/* Floating Input Dock Skeleton */}
              <div className="w-full space-y-2">
                <div className="relative rounded-3xl border border-border/80 bg-muted/40 dark:bg-muted/20 backdrop-blur-md shadow-md p-3 flex flex-col gap-1.5 min-h-[82px] justify-between">
                  <div className="h-4 w-52 rounded bg-muted/40 animate-pulse mt-1 ml-1" />
                  <div className="flex items-center justify-between px-1">
                    <div className="h-3 w-32 rounded bg-muted/30 hidden sm:block" />
                    <div className="size-9 rounded-full bg-primary/20 flex items-center justify-center text-primary/40 ml-auto">
                      <ArrowUp className="size-4.5 opacity-40" />
                    </div>
                  </div>
                </div>
                <div className="text-center text-[10px] text-muted-foreground/60 px-2 select-none">
                  Trợ lý AI QNU đối soát từ nguồn văn bản và quy chế chính thức
                  của Trường Đại học Quy Nhơn.
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (isLoadingAssistant) {
    return <PublicChatSkeleton />;
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
        onOpen={() => setSidebarOpen(true)}
      />

      {/* 2. Main Chat Canvas */}
      <div className="flex-1 flex flex-col h-full min-w-0 bg-background relative overflow-hidden">
        {/* Top Header Navbar - Seamless without border-b like Gemini & ChatGPT */}
        <header className="h-14 shrink-0 bg-background/80 backdrop-blur-md px-3 sm:px-4 flex items-center justify-between z-20">
          <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
            {/* Mobile-only Toggle Sidebar Button (Desktop uses Mini-Rail) */}
            {!sidebarOpen && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8 rounded-md text-muted-foreground hover:text-foreground shrink-0 hover:bg-muted/70 transition-colors lg:hidden"
                onClick={() => setSidebarOpen(true)}
                title="Mở rộng thanh lịch sử"
              >
                <PanelLeft className="size-4" />
              </Button>
            )}

            {/* Mobile-only New Chat Button (Desktop uses Mini-Rail) */}
            {!sidebarOpen && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8 rounded-md text-muted-foreground hover:text-foreground shrink-0 hover:bg-muted/70 transition-colors lg:hidden"
                onClick={handleNewThread}
                title="Đoạn chat mới"
              >
                <PenLine className="size-4" />
              </Button>
            )}

            {/* Back to Portal (Mobile only) */}
            <Button
              variant="ghost"
              size="icon"
              className="size-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/70 transition-colors shrink-0 lg:hidden"
              onClick={() => void navigate({ to: "/chat" })}
              title="Quay lại Cổng Trợ Lý"
            >
              <ArrowLeft className="size-4" />
            </Button>

            {/* Assistant Identifier & Selector */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="h-9 px-2 gap-2 rounded-md hover:bg-muted/70 text-left font-normal group text-foreground cursor-pointer"
                >
                  <div className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                    {getCategoryIcon(assistant.category, assistant.code)}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-xs sm:text-sm text-foreground truncate max-w-[160px] sm:max-w-md group-hover:text-primary transition-colors">
                        {formatAssistantDisplayName(
                          assistant.name,
                          assistant.code,
                        )}
                      </span>
                      <ChevronDown className="size-3 text-muted-foreground group-hover:text-foreground shrink-0 transition-transform" />
                    </div>
                  </div>
                </Button>
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
                    <span className="truncate flex-1">
                      {formatAssistantDisplayName(ast.name, ast.code)}
                    </span>
                    {(ast.code === assistantCode ||
                      ast.id === assistantCode) && (
                      <CheckCircle2 className="size-3 text-primary shrink-0" />
                    )}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
            {/* Export Markdown */}
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8 rounded-md text-muted-foreground hover:text-foreground"
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
              className="size-8 rounded-md text-muted-foreground hover:text-foreground"
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

              {/* 2x2 Prompt Suggestions Grid (Gemini Style, Surface rounded-lg per Rule 4.3) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {promptSuggestions.map((item) => (
                  <button
                    key={item.text}
                    type="button"
                    onClick={() => handleSend(item.text)}
                    className="group text-left p-4 rounded-lg bg-card/60 hover:bg-card border border-border/80 hover:border-primary/40 transition-all shadow-2xs hover:shadow-xs flex flex-col justify-between gap-3 min-h-[96px] cursor-pointer"
                  >
                    <span className="text-xs sm:text-sm font-medium text-foreground/90 leading-relaxed group-hover:text-primary transition-colors">
                      {item.text}
                    </span>
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-1.5">
                        {item.icon}
                        <span>{item.category}</span>
                      </span>
                      <div className="size-6 rounded-md bg-muted/80 border border-border/70 flex items-center justify-center opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all text-primary shadow-2xs">
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
