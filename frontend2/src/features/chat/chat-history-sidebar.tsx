import {
  ArrowLeft,
  BookOpen,
  Bot,
  Check,
  ChevronDown,
  GraduationCap,
  HelpCircle,
  History,
  Library,
  MessageSquare,
  Moon,
  PanelLeftClose,
  Pencil,
  Plus,
  Search,
  Sun,
  Trash2,
  X,
} from "lucide-react";
import * as React from "react";
import { useTheme } from "@/app/theme-provider";
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
import type { ChatThread, GroupedChatThreads } from "@/hooks/use-chat-history";
import { cn } from "@/lib/utils";
import type { AssistantItem } from "@/types/assistants";

interface ChatHistorySidebarProps {
  assistant?: AssistantItem;
  assistantCode: string;
  threads: ChatThread[];
  groupedThreads: GroupedChatThreads;
  currentThreadId: string;
  onSelectThread: (id: string) => void;
  onNewThread: () => void;
  onRenameThread: (id: string, newTitle: string) => void;
  onDeleteThread: (id: string) => void;
  onClearAll: () => void;
  isOpen: boolean;
  onClose: () => void;
  allAssistants?: AssistantItem[];
  onSwitchAssistant?: (slug: string) => void;
  className?: string;
}

function getCategoryIcon(category?: string, code?: string) {
  const cat = (category || code || "").toLowerCase();
  if (cat.includes("admission") || cat.includes("tuyen_sinh")) {
    return <GraduationCap className="size-4 shrink-0" />;
  }
  if (
    cat.includes("regulation") ||
    cat.includes("quy_che") ||
    cat.includes("dao_tao")
  ) {
    return <BookOpen className="size-4 shrink-0" />;
  }
  if (cat.includes("library") || cat.includes("thu_vien")) {
    return <Library className="size-4 shrink-0" />;
  }
  if (
    cat.includes("exam") ||
    cat.includes("khao_thi") ||
    cat.includes("ngan_hang")
  ) {
    return <HelpCircle className="size-4 shrink-0" />;
  }
  return <Bot className="size-4 shrink-0" />;
}

export function ChatHistorySidebar({
  assistant,
  assistantCode,
  threads,
  groupedThreads,
  currentThreadId,
  onSelectThread,
  onNewThread,
  onRenameThread,
  onDeleteThread,
  onClearAll,
  isOpen,
  onClose,
  allAssistants = [],
  onSwitchAssistant,
  className,
}: ChatHistorySidebarProps) {
  const { resolvedTheme, setTheme } = useTheme();
  const [search, setSearch] = React.useState("");
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editingTitle, setEditingTitle] = React.useState("");
  const [confirmClearOpen, setConfirmClearOpen] = React.useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<string | null>(
    null,
  );

  // Filter threads by search query
  const filteredThreads = React.useMemo(() => {
    if (!search.trim()) return null;
    const query = search.toLowerCase().trim();
    return threads.filter((t) => t.title.toLowerCase().includes(query));
  }, [threads, search]);

  const handleStartRename = (e: React.MouseEvent, thread: ChatThread) => {
    e.stopPropagation();
    setEditingId(thread.id);
    setEditingTitle(thread.title);
  };

  const handleSaveRename = (threadId: string) => {
    if (editingTitle.trim()) {
      onRenameThread(threadId, editingTitle.trim());
    }
    setEditingId(null);
  };

  const handleKeyDownRename = (
    e: React.KeyboardEvent<HTMLInputElement>,
    threadId: string,
  ) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSaveRename(threadId);
    } else if (e.key === "Escape") {
      setEditingId(null);
    }
  };

  const renderThreadItem = (thread: ChatThread) => {
    const isActive = thread.id === currentThreadId;
    const isEditing = thread.id === editingId;

    if (isEditing) {
      return (
        <div
          key={thread.id}
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-background border border-primary/40 shadow-xs"
        >
          <Input
            value={editingTitle}
            onChange={(e) => setEditingTitle(e.target.value)}
            onKeyDown={(e) => handleKeyDownRename(e, thread.id)}
            autoFocus
            className="h-7 text-xs py-0 px-2 border-0 bg-transparent focus-visible:ring-0"
          />
          <Button
            size="icon"
            variant="ghost"
            className="size-6 shrink-0 text-primary hover:bg-primary/10"
            onClick={() => handleSaveRename(thread.id)}
          >
            <Check className="size-3.5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-6 shrink-0 text-muted-foreground hover:bg-muted"
            onClick={() => setEditingId(null)}
          >
            <X className="size-3.5" />
          </Button>
        </div>
      );
    }

    return (
      <div
        key={thread.id}
        className={cn(
          "group relative flex items-center justify-between gap-1.5 px-2.5 py-1.5 rounded-xl text-xs transition-all select-none",
          isActive
            ? "bg-background text-foreground font-semibold shadow-xs border border-border/80"
            : "text-foreground/75 hover:bg-background/60 hover:text-foreground",
        )}
      >
        <button
          type="button"
          onClick={() => onSelectThread(thread.id)}
          className="flex items-center gap-2.5 min-w-0 flex-1 text-left bg-transparent border-0 p-1 cursor-pointer text-inherit font-inherit rounded-md"
        >
          <MessageSquare
            className={cn(
              "size-3.5 shrink-0 transition-colors",
              isActive
                ? "text-primary"
                : "text-muted-foreground/70 group-hover:text-foreground",
            )}
          />
          <span className="truncate leading-relaxed" title={thread.title}>
            {thread.title}
          </span>
        </button>

        {/* Action icons on hover */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="size-6 p-0 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted"
            onClick={(e) => handleStartRename(e, thread)}
            title="Đổi tên đoạn chat"
          >
            <Pencil className="size-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-6 p-0 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            onClick={(e) => {
              e.stopPropagation();
              setConfirmDeleteId(thread.id);
            }}
            title="Xóa đoạn chat"
          >
            <Trash2 className="size-3" />
          </Button>
        </div>
      </div>
    );
  };

  const renderGroup = (label: string, items: ChatThread[]) => {
    if (items.length === 0) return null;
    return (
      <div className="space-y-1">
        <div className="px-3 pt-2.5 pb-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
          {label}
        </div>
        <div className="space-y-0.5">{items.map(renderThreadItem)}</div>
      </div>
    );
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <button
          type="button"
          aria-label="Đóng thanh lịch sử"
          onClick={onClose}
          className="fixed inset-0 bg-background/80 backdrop-blur-xs z-30 lg:hidden transition-opacity border-0 p-0 cursor-default"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          "fixed top-0 bottom-0 left-0 z-40 w-72 bg-muted/40 dark:bg-muted/15 backdrop-blur-md border-r border-border/40 flex flex-col transition-all duration-300 ease-in-out lg:static select-none",
          isOpen ? "translate-x-0" : "-translate-x-full lg:hidden",
          className,
        )}
      >
        {/* 1. Header Toolbar - Seamless without border-b like Gemini & ChatGPT */}
        <div className="h-14 px-3 flex items-center justify-between gap-2 shrink-0">
          {/* New Chat Button (Google Gemini Pill Capsule style) */}
          <Button
            onClick={onNewThread}
            variant="outline"
            className="flex-1 justify-start gap-2 h-9 px-3 rounded-full bg-background hover:bg-background/90 border-border/70 hover:border-primary/40 text-foreground hover:text-primary shadow-2xs text-xs font-semibold transition-all group"
          >
            <Plus className="size-3.5 text-primary group-hover:rotate-90 transition-transform duration-200" />
            <span>Đoạn chat mới</span>
          </Button>

          {/* Close Sidebar Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="size-8 rounded-lg text-muted-foreground hover:text-foreground shrink-0 hover:bg-background/80"
            title="Đóng thanh lịch sử"
          >
            <PanelLeftClose className="size-4" />
          </Button>
        </div>

        {/* 2. Search Box */}
        {threads.length > 2 && (
          <div className="px-3 pt-2 pb-1">
            <div className="relative">
              <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/70" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm đoạn chat..."
                className="h-8 pl-8 pr-2 text-xs rounded-lg border-border/60 bg-background/60 focus-visible:ring-1 focus-visible:ring-primary/30"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="size-3" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* 3. Conversations List */}
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-3">
          {threads.length === 0 ? (
            <div className="py-12 px-4 text-center space-y-3">
              <div className="size-10 rounded-2xl bg-background border border-border/60 text-muted-foreground flex items-center justify-center mx-auto shadow-2xs">
                <History className="size-5 text-muted-foreground/60" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-foreground">
                  Chưa có lịch sử chat
                </p>
                <p className="text-[11px] text-muted-foreground/80 leading-relaxed max-w-[200px] mx-auto">
                  Các cuộc trò chuyện của bạn sẽ tự động được lưu trữ và phân
                  nhóm tại đây.
                </p>
              </div>
            </div>
          ) : filteredThreads !== null ? (
            /* Search Results */
            <div className="space-y-1">
              <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
                Kết quả tìm kiếm ({filteredThreads.length})
              </div>
              {filteredThreads.length === 0 ? (
                <p className="text-xs text-muted-foreground px-3 py-3">
                  Không tìm thấy đoạn chat phù hợp.
                </p>
              ) : (
                filteredThreads.map(renderThreadItem)
              )}
            </div>
          ) : (
            /* Grouped by Date */
            <>
              {renderGroup("Hôm nay", groupedThreads.today)}
              {renderGroup("Hôm qua", groupedThreads.yesterday)}
              {renderGroup("7 ngày trước", groupedThreads.last7Days)}
              {renderGroup("Trước đó", groupedThreads.older)}
            </>
          )}
        </div>

        {/* 4. Footer Settings & Assistant Switcher */}
        <div className="p-3 border-t border-border/60 bg-background/50 backdrop-blur-xs space-y-2">
          {/* Assistant Quick Switcher Card */}
          {allAssistants.length > 1 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="w-full flex items-center justify-between gap-2.5 p-2 rounded-xl border border-border/70 bg-background hover:bg-background/90 text-left text-xs transition-all shadow-2xs cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="size-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                      {getCategoryIcon(assistant?.category, assistantCode)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-foreground truncate text-xs group-hover:text-primary transition-colors">
                        {assistant?.name || assistantCode}
                      </div>
                      <div className="text-[10px] text-muted-foreground truncate">
                        Đổi Trợ lý AI QNU
                      </div>
                    </div>
                  </div>
                  <ChevronDown className="size-3.5 text-muted-foreground shrink-0 group-hover:text-foreground transition-transform" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-64 text-xs">
                <div className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Trợ lý AI Đại Học Quy Nhơn
                </div>
                <DropdownMenuSeparator />
                {allAssistants.map((ast) => {
                  const isCurrent =
                    ast.code === assistantCode || ast.id === assistantCode;
                  return (
                    <DropdownMenuItem
                      key={ast.id || ast.code}
                      onClick={() => onSwitchAssistant?.(ast.code || ast.id)}
                      className={cn(
                        "flex items-center gap-2 cursor-pointer py-1.5",
                        isCurrent && "bg-primary/10 text-primary font-semibold",
                      )}
                    >
                      <div className="size-5 rounded bg-primary/10 text-primary flex items-center justify-center shrink-0">
                        {getCategoryIcon(ast.category, ast.code)}
                      </div>
                      <span className="truncate flex-1">{ast.name}</span>
                      {isCurrent && (
                        <Check className="size-3 text-primary shrink-0" />
                      )}
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {/* Quick Action Links */}
          <div className="flex items-center justify-between gap-1 pt-0.5 text-xs">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 text-muted-foreground hover:text-foreground text-[11px] px-2 flex-1 justify-start rounded-lg hover:bg-background"
              onClick={() => {
                window.location.href = "/chat";
              }}
              title="Quay lại Cổng Trợ Lý"
            >
              <ArrowLeft className="size-3.5" />
              <span>Cổng Trợ Lý</span>
            </Button>

            {threads.length > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                onClick={() => setConfirmClearOpen(true)}
                title="Xóa toàn bộ lịch sử"
              >
                <Trash2 className="size-3.5" />
              </Button>
            )}

            <Button
              variant="ghost"
              size="icon"
              className="size-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-background"
              onClick={() =>
                setTheme(resolvedTheme === "dark" ? "light" : "dark")
              }
              title="Đổi giao diện Sáng / Tối"
            >
              {resolvedTheme === "dark" ? (
                <Sun className="size-3.5 text-amber-400" />
              ) : (
                <Moon className="size-3.5" />
              )}
            </Button>
          </div>
        </div>
      </aside>

      {/* Delete Single Thread Confirm Dialog */}
      <Dialog
        open={Boolean(confirmDeleteId)}
        onOpenChange={(open) => !open && setConfirmDeleteId(null)}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold">
              Xóa đoạn chat?
            </DialogTitle>
            <DialogDescription className="text-xs">
              Đoạn chat này sẽ bị xóa vĩnh viễn khỏi lịch sử trình duyệt của
              bạn. Bạn có chắc chắn muốn xóa không?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmDeleteId(null)}
            >
              Hủy
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                if (confirmDeleteId) {
                  onDeleteThread(confirmDeleteId);
                  setConfirmDeleteId(null);
                }
              }}
            >
              Xác nhận xóa
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Clear All Threads Confirm Dialog */}
      <Dialog open={confirmClearOpen} onOpenChange={setConfirmClearOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold">
              Xóa toàn bộ lịch sử trò chuyện?
            </DialogTitle>
            <DialogDescription className="text-xs">
              Toàn bộ các cuộc trò chuyện của trợ lý "
              {assistant?.name || assistantCode}" trên máy này sẽ bị xóa sạch và
              không thể khôi phục.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmClearOpen(false)}
            >
              Hủy
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                onClearAll();
                setConfirmClearOpen(false);
              }}
            >
              Xóa sạch lịch sử
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
