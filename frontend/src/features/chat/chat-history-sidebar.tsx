import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  Check,
  History,
  MessageSquare,
  PanelLeft,
  Pencil,
  PenLine,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ChatThread, GroupedChatThreads } from "@/hooks/use-chat-history";
import { cn } from "@/lib/utils";
import type { AssistantItem } from "@/types/assistants";

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = React.useState<boolean>(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth >= 1024;
    }
    return true;
  });

  React.useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const onChange = () => setIsDesktop(mql.matches);
    mql.addEventListener("change", onChange);
    setIsDesktop(mql.matches);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return isDesktop;
}

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
  onOpen?: () => void;
  className?: string;
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
  onOpen,
  className,
}: ChatHistorySidebarProps) {
  const isDesktop = useIsDesktop();
  const navigate = useNavigate();
  const [search, setSearch] = React.useState("");
  const [showSearch, setShowSearch] = React.useState(false);
  const searchInputRef = React.useRef<HTMLInputElement>(null);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editingTitle, setEditingTitle] = React.useState("");
  const [confirmClearOpen, setConfirmClearOpen] = React.useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<string | null>(
    null,
  );

  const handleToggleSearch = () => {
    setShowSearch((prev) => {
      const next = !prev;
      if (next) {
        setTimeout(() => searchInputRef.current?.focus(), 50);
      }
      return next;
    });
  };

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
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-background border border-primary/40 shadow-xs"
        >
          <Input
            value={editingTitle}
            onChange={(e) => setEditingTitle(e.target.value)}
            onKeyDown={(e) => handleKeyDownRename(e, thread.id)}
            onBlur={() => handleSaveRename(thread.id)}
            autoFocus
            className="h-7 text-xs py-0 px-2 border-0 bg-transparent focus-visible:ring-0"
          />
          <Button
            size="icon"
            variant="ghost"
            className="size-6 shrink-0 text-primary hover:bg-primary/10 rounded-micro"
            onClick={() => handleSaveRename(thread.id)}
          >
            <Check className="size-3.5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-6 shrink-0 text-muted-foreground hover:bg-muted rounded-micro"
            onClick={() => setEditingId(null)}
          >
            <X className="size-3.5" />
          </Button>
        </div>
      );
    }

    return (
      <motion.div
        key={thread.id}
        layout="position"
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.18 }}
        className={cn(
          "group relative flex items-center justify-between gap-1.5 px-2.5 py-1.5 rounded-md text-xs transition-colors select-none",
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

        {/* Action icons on hover or focus-within */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity shrink-0">
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
      </motion.div>
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
      {/* Mobile Backdrop Overlay with Motion Fade */}
      <AnimatePresence>
        {isOpen && !isDesktop && (
          <motion.button
            key="backdrop"
            type="button"
            aria-label="Đóng thanh lịch sử"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-background/80 backdrop-blur-xs z-30 lg:hidden border-0 p-0 cursor-default"
          />
        )}
      </AnimatePresence>

      {/* Unified Responsive Sidebar Container with Motion Apple/Gemini Deceleration Physics */}
      <motion.aside
        initial={false}
        animate={
          isDesktop
            ? { width: isOpen ? 256 : 64, x: 0 }
            : { width: 256, x: isOpen ? 0 : -256 }
        }
        transition={{
          duration: 0.35,
          ease: [0.16, 1, 0.3, 1], // Exponential deceleration curve
        }}
        className={cn(
          "bg-muted/40 dark:bg-muted/15 backdrop-blur-md border-r border-border/40 select-none shrink-0 overflow-hidden flex flex-col z-40",
          isDesktop ? "static h-full" : "fixed top-0 bottom-0 left-0",
          className,
        )}
      >
        <AnimatePresence mode="wait" initial={false}>
          {!isOpen && isDesktop ? (
            /* Mini-Rail on Desktop (w-16) with PanelLeft icon */
            <motion.div
              key="mini-rail"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="w-16 h-full flex flex-col items-center justify-between py-3.5 shrink-0"
            >
              {/* Top Actions: Expand Sidebar & New Chat */}
              <div className="flex flex-col items-center gap-2.5 w-full">
                {/* Expand Sidebar Button using PanelLeft */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <motion.div
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={onOpen}
                        className="size-9 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors"
                      >
                        <PanelLeft className="size-4" />
                      </Button>
                    </motion.div>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="text-xs font-medium">
                    Mở thanh bên
                  </TooltipContent>
                </Tooltip>

                {/* New Chat Button directly below */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <motion.div
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={onNewThread}
                        className="size-9 rounded-md bg-background hover:bg-background/90 dark:bg-card text-foreground border border-border/80 shadow-xs hover:shadow-sm transition-all"
                      >
                        <PenLine className="size-4 text-foreground/80" />
                      </Button>
                    </motion.div>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="text-xs font-medium">
                    Cuộc trò chuyện mới
                  </TooltipContent>
                </Tooltip>
              </div>

              {/* Bottom: Back to portal */}
              <div className="w-full flex justify-center">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <motion.div
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => void navigate({ to: "/" })}
                        className="size-9 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors"
                      >
                        <ArrowLeft className="size-4" />
                      </Button>
                    </motion.div>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="text-xs font-medium">
                    Cổng Trợ Lý
                  </TooltipContent>
                </Tooltip>
              </div>
            </motion.div>
          ) : (
            /* Expanded Sidebar Mode (w-64 / 256px per Rule 4.3) */
            <motion.div
              key="expanded"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="w-64 min-w-[256px] h-full flex flex-col shrink-0"
            >
              {/* Row 1: Logo on Left, Search + Close with Tooltips */}
              <div className="h-14 px-3 flex items-center justify-between shrink-0">
                {/* Brand Logo (Links to Portal) */}
                <Link
                  to="/"
                  className="flex items-center gap-2 group cursor-pointer select-none text-inherit no-underline"
                  title="Quay lại Cổng Trợ Lý QNU AI"
                >
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-white p-0.5 shadow-xs border border-border/60 group-hover:border-primary/50 transition-colors">
                    <img
                      src="/logo.png"
                      alt="Logo Trường Đại học Quy Nhơn"
                      className="size-6 object-contain"
                    />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-sm tracking-tight text-foreground group-hover:text-primary transition-colors">
                      QNU AI
                    </span>
                    <Sparkles className="size-3 text-primary/70" />
                  </div>
                </Link>

                {/* Right Actions: Search + Close with Tooltips */}
                <div className="flex items-center gap-0.5">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={handleToggleSearch}
                        className={cn(
                          "size-8 rounded-md text-muted-foreground hover:text-foreground transition-colors",
                          showSearch
                            ? "bg-muted text-foreground"
                            : "hover:bg-muted/70",
                        )}
                      >
                        <Search className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent
                      side="bottom"
                      className="text-xs font-medium"
                    >
                      Tìm kiếm đoạn chat
                    </TooltipContent>
                  </Tooltip>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="size-8 rounded-md text-muted-foreground hover:text-foreground shrink-0 hover:bg-muted/70 transition-colors"
                      >
                        <PanelLeft className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent
                      side="bottom"
                      className="text-xs font-medium"
                    >
                      Thu gọn thanh bên
                    </TooltipContent>
                  </Tooltip>
                </div>
              </div>

              {/* Row 2: "Cuộc trò chuyện mới" with White/Card background (User Request) */}
              <div className="px-3 pb-2 pt-0.5">
                <motion.div
                  whileHover={{ scale: 1.012 }}
                  whileTap={{ scale: 0.985 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25 }}
                >
                  <Button
                    onClick={onNewThread}
                    className="w-full justify-start gap-2.5 h-9 px-3 rounded-md bg-background hover:bg-background/90 dark:bg-card dark:hover:bg-card/80 text-foreground border border-border/80 hover:border-border shadow-xs hover:shadow-sm text-xs font-medium transition-all group cursor-pointer"
                  >
                    <PenLine className="size-4 text-foreground/80 shrink-0 transition-transform group-hover:scale-105" />
                    <span>Cuộc trò chuyện mới</span>
                  </Button>
                </motion.div>
              </div>

              {/* Row 3: Search Box (Revealed when search button clicked or query present) */}
              {(showSearch || Boolean(search.trim())) && (
                <div className="px-3 pt-1 pb-1">
                  <div className="relative">
                    <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/70" />
                    <Input
                      ref={searchInputRef}
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Tìm đoạn chat..."
                      className="h-8 pl-8 pr-7 text-xs rounded-md border-border/60 bg-background/60 focus-visible:ring-1 focus-visible:ring-primary/30"
                    />
                    {search && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => setSearch("")}
                        className="size-5 absolute right-1.5 top-1/2 -translate-y-1/2 rounded-micro text-muted-foreground hover:text-foreground hover:bg-transparent"
                      >
                        <X className="size-3" />
                      </Button>
                    )}
                  </div>
                </div>
              )}

              {/* 3. Conversations List */}
              <div className="flex-1 overflow-y-auto px-2 py-2 space-y-3">
                {threads.length === 0 ? (
                  <div className="py-12 px-4 text-center space-y-3">
                    <div className="size-10 rounded-lg bg-background border border-border/60 text-muted-foreground flex items-center justify-center mx-auto shadow-2xs">
                      <History className="size-5 text-muted-foreground/60" />
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-foreground">
                        Chưa có lịch sử chat
                      </p>
                      <p className="text-[11px] text-muted-foreground/80 leading-relaxed max-w-[200px] mx-auto">
                        Các cuộc trò chuyện của bạn sẽ tự động được lưu trữ và
                        phân nhóm tại đây.
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

              {/* 4. Footer Actions (Clean & Minimalist) */}
              <div className="p-3 border-t border-border/40 bg-background/50 backdrop-blur-xs flex items-center justify-between gap-1 text-xs">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1.5 text-muted-foreground hover:text-foreground text-[11px] px-2 flex-1 justify-start rounded-md hover:bg-background"
                  onClick={() => void navigate({ to: "/" })}
                  title="Quay lại Cổng Trợ Lý"
                >
                  <ArrowLeft className="size-3.5" />
                  <span>Cổng Trợ Lý</span>
                </Button>

                {threads.length > 0 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    onClick={() => setConfirmClearOpen(true)}
                    title="Xóa toàn bộ lịch sử"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.aside>

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
