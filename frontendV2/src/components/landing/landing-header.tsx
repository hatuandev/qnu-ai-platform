import { Bot, LogIn, Moon, Phone, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/lib/ui-store";

export function LandingHeader({
  onLogin,
  isSignedIn,
  onOpenAssistant,
}: {
  onLogin: () => void;
  isSignedIn: boolean;
  onOpenAssistant?: () => void;
}) {
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);
  const isDark = theme === "dark";

  return (
    <header className="sticky top-0 z-30 shrink-0 border-b border-border/60 bg-background/85 px-3 py-2.5 backdrop-blur-md sm:px-6 sm:py-3">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-2 sm:gap-4">
        <div className="flex min-w-0 items-center gap-2.5 sm:gap-3">
          <img
            src="/logo-qnu.png"
            alt="Logo Trường Đại học Quy Nhơn"
            className="h-9 w-9 shrink-0 object-contain sm:h-10 sm:w-10"
          />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="truncate text-sm font-semibold tracking-tight text-foreground sm:text-base">
                QNU AI Platform
              </span>
              <span className="inline-flex shrink-0 items-center rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                CỔNG TRỰC TUYẾN
              </span>
            </div>
            <p className="hidden truncate text-xs text-muted-foreground sm:block">
              Trợ lý Trí tuệ Nhân tạo Tư vấn Tuyển sinh Trường Đại học Quy Nhơn
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-2.5">
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={() => setTheme(isDark ? "light" : "dark")}
            title={
              isDark
                ? "Chuyển sang giao diện sáng"
                : "Chuyển sang giao diện tối"
            }
            aria-label={
              isDark
                ? "Chuyển sang giao diện sáng"
                : "Chuyển sang giao diện tối"
            }
          >
            {isDark ? (
              <Sun className="size-4 text-warning" />
            ) : (
              <Moon className="size-4" />
            )}
          </Button>

          <a
            href="tel:1800558849"
            className="hidden items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary/15 md:inline-flex"
            title="Tổng đài tư vấn tuyển sinh miễn cước: 1800 55 88 49"
          >
            <Phone className="size-3.5" />
            <span>1800 55 88 49</span>
          </a>

          {onOpenAssistant ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="hidden h-9 gap-1.5 px-3 sm:inline-flex"
              onClick={onOpenAssistant}
            >
              <Bot className="size-3.5" />
              <span>Trợ lý tư vấn</span>
            </Button>
          ) : null}

          <Button
            type="button"
            size="sm"
            className="h-9 gap-1.5 px-3 sm:px-4"
            onClick={onLogin}
          >
            <LogIn className="size-3.5" />
            <span>{isSignedIn ? "Vào nền tảng" : "Đăng nhập"}</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
