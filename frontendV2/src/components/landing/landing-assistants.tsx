import {
  ArrowRight,
  Bot,
  MessageSquare,
  RefreshCw,
  Search,
  SearchX,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { PublicChatbotSummary } from "@/api/publications";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export const PUBLIC_ASSISTANTS_SECTION_ID = "tro-ly-cong-khai";

const SKELETON_CARDS = ["assistant-skeleton-1", "assistant-skeleton-2"];

function foldText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

export function scrollToPublicAssistants(): void {
  document
    .getElementById(PUBLIC_ASSISTANTS_SECTION_ID)
    ?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function AssistantCard({
  bot,
  onOpen,
}: {
  bot: PublicChatbotSummary;
  onOpen: (slug: string) => void;
}) {
  return (
    <button
      type="button"
      disabled={!bot.available}
      onClick={() => onOpen(bot.slug)}
      title={
        bot.available
          ? `Trò chuyện với ${bot.display_name}`
          : (bot.unavailable_reason ?? "Trợ lý đang tạm ngưng phục vụ.")
      }
      className="group flex w-full items-center justify-between gap-3.5 rounded-xl border border-border/70 bg-card/90 p-3.5 text-left shadow-2xs transition-all duration-200 enabled:cursor-pointer enabled:hover:-translate-y-0.5 enabled:hover:border-primary/50 enabled:hover:bg-card enabled:hover:shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 sm:p-4"
    >
      <div className="flex min-w-0 items-center gap-3.5">
        <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary transition-all duration-200 group-hover:scale-105 group-hover:bg-primary group-hover:text-primary-foreground sm:size-12">
          <Bot className="size-5.5 sm:size-6" />
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-sm font-semibold tracking-tight text-foreground transition-colors group-hover:text-primary sm:text-base">
              {bot.display_name}
            </h3>
            {bot.available ? (
              <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-semibold text-success">
                <span className="size-1.5 rounded-full bg-success" />
                Sẵn sàng
              </span>
            ) : (
              <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-warning/10 px-2 py-0.5 text-[10px] font-semibold text-warning">
                <span className="size-1.5 rounded-full bg-warning" />
                Tạm ngưng
              </span>
            )}
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {bot.welcome_message ||
              "Trợ lý trí tuệ nhân tạo giải đáp thắc mắc trực tuyến."}
          </p>
        </div>
      </div>

      {bot.available && (
        <div className="flex shrink-0 items-center gap-1 text-xs font-medium text-muted-foreground transition-colors group-hover:text-primary">
          <span className="hidden sm:inline">Trò chuyện</span>
          <ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-1 text-primary" />
        </div>
      )}
    </button>
  );
}

export function AssistantDirectory({
  chatbots,
  isPending,
  isError,
  onRetry,
  onOpen,
  onFallback,
}: {
  chatbots: PublicChatbotSummary[];
  isPending: boolean;
  isError: boolean;
  onRetry: () => void;
  onOpen: (slug: string) => void;
  onFallback: () => void;
}) {
  const [search, setSearch] = useState("");

  const visibleBots = useMemo(() => {
    const raw = search.trim();
    if (!raw) return chatbots;
    const needle = foldText(raw);
    return chatbots.filter((bot) => {
      return (
        foldText(bot.display_name).includes(needle) ||
        bot.slug.toLowerCase().includes(raw.toLowerCase())
      );
    });
  }, [chatbots, search]);

  const showSearch = chatbots.length > 4;

  return (
    <div id={PUBLIC_ASSISTANTS_SECTION_ID} className="scroll-mt-24">
      {isPending ? (
        <div aria-hidden className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {SKELETON_CARDS.map((key) => (
            <div
              key={key}
              className="flex items-center gap-3.5 rounded-xl border border-border/70 bg-card/80 p-4"
            >
              <Skeleton className="size-11 rounded-xl" />
              <div className="min-w-0 flex-1 space-y-2">
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-3 w-3/4" />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {isError ? (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border/70 bg-card px-3.5 py-2.5">
          <p className="text-xs text-muted-foreground">
            Không tải được danh sách trợ lý công khai lúc này.
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 gap-1.5 text-xs"
            onClick={onRetry}
          >
            <RefreshCw className="size-3.5" />
            <span>Thử lại</span>
          </Button>
        </div>
      ) : null}

      {!isPending && !isError && chatbots.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-border/70 bg-card/80 px-4 py-10 text-center">
          <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Bot className="size-5" />
          </span>
          <p className="text-sm font-medium text-foreground">
            Chưa có trợ lý công khai nào được bật.
          </p>
          <p className="max-w-sm text-xs leading-relaxed text-muted-foreground">
            Trợ lý sẽ xuất hiện tại đây khi đơn vị xuất bản. Bạn vẫn có thể trò
            chuyện nội bộ sau khi đăng nhập.
          </p>
          <Button
            type="button"
            size="sm"
            className="mt-1 h-9 gap-1.5 text-xs"
            onClick={onFallback}
          >
            <MessageSquare className="size-3.5" />
            <span>Trò chuyện nội bộ</span>
          </Button>
        </div>
      ) : null}

      {chatbots.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="type-metadata font-semibold tracking-wide text-primary uppercase">
                Trợ lý xuất bản công khai
              </span>
              <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                {chatbots.length} trợ lý
              </span>
            </div>

            {showSearch && (
              <div className="relative w-full max-w-xs">
                <Search className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Tìm trợ lý..."
                  aria-label="Tìm trợ lý"
                  className="h-8 pl-8 text-xs"
                />
              </div>
            )}
          </div>

          {visibleBots.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {visibleBots.map((bot) => (
                <AssistantCard key={bot.slug} bot={bot} onOpen={onOpen} />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-border/70 bg-card/80 px-4 py-8 text-center">
              <SearchX className="size-5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Không tìm thấy trợ lý phù hợp.
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={() => setSearch("")}
              >
                Xóa tìm kiếm
              </Button>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
