import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Mail, MapPin, Phone, ShieldCheck } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";
import { usePublicChatbotListQuery } from "@/api/publications";
import { getAccessToken } from "@/api/session-token";
import { beginSsoLogin, isSsoEnabled } from "@/api/sso";
import { scrollToPublicAssistants } from "@/components/landing/landing-assistants";
import { LandingHeader } from "@/components/landing/landing-header";
import { LandingHero } from "@/components/landing/landing-hero";
import { LandingShowcase } from "@/components/landing/landing-showcase";

export const Route = createFileRoute("/")({
  component: LandingPage,
});

function describeLoginError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Không thể bắt đầu đăng nhập QNU SSO.";
}

function readPublicChatbotSlug(): string {
  const env = (
    import.meta as unknown as { env?: Record<string, string | undefined> }
  ).env;
  return env?.VITE_PUBLIC_CHATBOT_SLUG?.trim() ?? "";
}

const PUBLIC_CHATBOT_SLUG = readPublicChatbotSlug();

function LandingPage() {
  const navigate = useNavigate();
  const [isSignedIn] = useState(() => getAccessToken() !== null);
  const publicChatbotsQuery = usePublicChatbotListQuery();
  const publicChatbots = publicChatbotsQuery.data?.chatbots ?? [];
  const availableBots = publicChatbots.filter((bot) => bot.available);
  // Honor the pinned env slug only when that bot is actually published and ready;
  // a stale or unavailable slug must not hijack the CTA into a dead chatbot page.
  const activeSlug =
    availableBots.find((bot) => bot.slug === PUBLIC_CHATBOT_SLUG)?.slug ??
    availableBots[0]?.slug;

  // Both handlers follow the same contract: SSO when configured, the dev
  // bridge otherwise, and the session gate resolves the workspace afterwards.
  const handleEnterApp = useCallback(() => {
    if (getAccessToken() !== null) {
      void navigate({ to: "/dashboard" });
      return;
    }
    if (isSsoEnabled()) {
      void beginSsoLogin("/dashboard").catch((error: unknown) => {
        toast.error(describeLoginError(error));
      });
      return;
    }
    void navigate({ to: "/dashboard" });
  }, [navigate]);

  const handleAsk = useCallback(
    (question?: string) => {
      const trimmed = question?.trim();
      if (activeSlug) {
        void navigate({
          to: "/chatbot/$slug",
          params: { slug: activeSlug },
          search: trimmed ? { q: trimmed } : {},
        });
        return;
      }
      if (getAccessToken() !== null) {
        if (trimmed) {
          void navigate({ to: "/chat", search: { q: trimmed } });
        } else {
          void navigate({ to: "/chat" });
        }
        return;
      }
      if (isSsoEnabled()) {
        const returnTo = trimmed
          ? `/chat?q=${encodeURIComponent(trimmed)}`
          : "/chat";
        void beginSsoLogin(returnTo).catch((error: unknown) => {
          toast.error(describeLoginError(error));
        });
        return;
      }
      if (trimmed) {
        void navigate({ to: "/chat", search: { q: trimmed } });
      } else {
        void navigate({ to: "/chat" });
      }
    },
    [navigate, activeSlug],
  );

  const handleOpenAssistant = useCallback(() => {
    scrollToPublicAssistants();
  }, []);

  const handleSelectPublicBot = useCallback(
    (slug: string) => {
      void navigate({
        to: "/chatbot/$slug",
        params: { slug },
        search: {},
      });
    },
    [navigate],
  );

  return (
    <div className="landing-grid landing-shell flex min-h-screen w-full flex-col font-sans text-foreground selection:bg-primary/20">
      <LandingHeader
        onLogin={handleEnterApp}
        isSignedIn={isSignedIn}
        onOpenAssistant={handleOpenAssistant}
      />

      <main className="flex flex-1 flex-col">
        <LandingHero
          chatbots={publicChatbots}
          isListPending={publicChatbotsQuery.isPending}
          isListError={publicChatbotsQuery.isError}
          onRetryList={() => void publicChatbotsQuery.refetch()}
          onOpen={handleSelectPublicBot}
          onFallback={() => handleAsk()}
        />
        <LandingShowcase onAsk={handleAsk} />

        <footer className="mt-auto border-t border-border/60 bg-card/70 px-3 py-6 backdrop-blur-xs sm:px-4 sm:py-8">
          <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 sm:flex-row sm:gap-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground sm:text-sm">
              <ShieldCheck className="size-4 shrink-0 text-primary" />
              <span>
                Trợ lý Trí tuệ Nhân tạo Tư vấn Tuyển sinh — Trường Đại học Quy
                Nhơn
              </span>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3 text-[11px] text-muted-foreground sm:gap-4 sm:text-xs">
              <span className="flex items-center gap-1">
                <MapPin className="size-3.5 shrink-0" />
                170 An Dương Vương, TP. Quy Nhơn
              </span>
              <span className="flex items-center gap-1">
                <Phone className="size-3.5 shrink-0" />
                0256.3846.156
              </span>
              <span className="flex items-center gap-1">
                <Mail className="size-3.5 shrink-0" />
                tuyensinh@qnu.edu.vn
              </span>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
