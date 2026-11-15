import { GraduationCap, ShieldCheck } from "lucide-react";
import type { PublicChatbotSummary } from "@/api/publications";
import { AssistantDirectory } from "@/components/landing/landing-assistants";

export function LandingHero({
  chatbots,
  isListPending,
  isListError,
  onRetryList,
  onOpen,
  onFallback,
}: {
  chatbots: PublicChatbotSummary[];
  isListPending: boolean;
  isListError: boolean;
  onRetryList: () => void;
  onOpen: (slug: string) => void;
  onFallback: () => void;
}) {
  return (
    <section className="relative overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="landing-aurora absolute -top-28 left-[calc(50%-21rem)] h-72 w-[42rem] rounded-full bg-primary/10 blur-3xl dark:bg-primary/15" />
        <div className="absolute top-44 -left-28 h-64 w-64 rounded-full bg-info/10 blur-3xl" />
        <div className="absolute top-20 -right-28 h-64 w-64 rounded-full bg-warning/10 blur-3xl" />
      </div>

      <div className="relative mx-auto w-full max-w-5xl px-4 pt-8 pb-6 sm:px-6 sm:pt-12 sm:pb-8">
        <div className="landing-rise max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            <GraduationCap className="size-3.5" />
            <span>Cổng Tư Vấn Tuyển Sinh Thông Minh 2026 · ĐH Quy Nhơn</span>
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl md:text-5xl">
            Một Điểm Chạm.{" "}
            <span className="text-primary block sm:inline">
              Mọi Thông Tin ĐH Quy Nhơn.
            </span>
          </h1>

          <p className="max-w-2xl text-xs sm:text-sm leading-relaxed text-muted-foreground">
            Trợ lý AI giải đáp tức thì 24/7 về 05 phương thức tuyển sinh, điểm
            chuẩn, học phí tín chỉ, đời sống ký túc xá và thủ tục nhập học — bảo
            chứng 100% bám sát văn bản pháp lý chính thức.
          </p>
        </div>

        <div className="landing-rise landing-delay-1 mt-6">
          <AssistantDirectory
            chatbots={chatbots}
            isPending={isListPending}
            isError={isListError}
            onRetry={onRetryList}
            onOpen={onOpen}
            onFallback={onFallback}
          />
        </div>

        <div className="landing-rise landing-delay-2 mt-3 flex items-center gap-2 text-[11px] text-muted-foreground">
          <ShieldCheck className="size-3.5 text-primary" />
          <span>Khi thiếu căn cứ, trợ lý nói rõ thay vì suy đoán.</span>
        </div>
      </div>
    </section>
  );
}
