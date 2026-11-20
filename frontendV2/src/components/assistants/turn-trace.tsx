import { Activity, ChevronDown, Clock, Cpu } from "lucide-react";
import { useMemo, useState } from "react";
import type { AnswerTrace } from "@/api/answer-reviews";
import type { ConversationTurn } from "@/api/conversations";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    rewrite: "Viết lại",
    retrieval: "Truy xuất",
    rerank: "Xếp hạng",
    drafting: "Soạn thảo",
    verification: "Kiểm chứng",
  };
  return map[stage] ?? stage;
}

export function TurnTraceDetails({
  turn,
  trace,
}: {
  turn: ConversationTurn;
  trace: AnswerTrace;
}) {
  const [open, setOpen] = useState(false);

  const stageEntries = useMemo(() => {
    if (!trace.stage_ms) return [];
    return Object.entries(trace.stage_ms).filter(
      ([_, value]) => typeof value === "number",
    );
  }, [trace.stage_ms]);

  const totalMs = useMemo(() => {
    return stageEntries.reduce((sum, [_, ms]) => sum + ms, 0);
  }, [stageEntries]);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="space-y-1.5">
      <CollapsibleTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={cn(
            "h-6 px-1.5 text-[10px] gap-1 text-muted-foreground hover:text-foreground cursor-pointer font-mono",
            open && "text-foreground bg-muted",
          )}
          title="Xem thông số kỹ thuật (Trace)"
        >
          <Activity className="size-3 text-primary" />
          <span>Trace</span>
          {totalMs > 0 ? (
            <span className="text-muted-foreground/70">({totalMs}ms)</span>
          ) : null}
          <ChevronDown
            className={cn(
              "size-3 transition-transform duration-200",
              open && "rotate-180",
            )}
          />
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="rounded-lg border border-border/50 bg-muted/30 p-2.5 text-[11px] font-mono text-muted-foreground space-y-2 select-text animate-in fade-in-50 duration-200">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/30 pb-1.5">
            <div className="flex items-center gap-1.5">
              <Cpu className="size-3.5 text-primary" />
              <span className="font-semibold text-foreground">
                {trace.model_name ?? "Hệ thống mặc định"}
              </span>
              {trace.provider_id ? (
                <span className="text-[10px] text-muted-foreground/80">
                  ({trace.provider_id})
                </span>
              ) : null}
            </div>
            <div className="text-[10px] text-muted-foreground">
              {trace.prompt_version ? `Prompt v${trace.prompt_version}` : ""}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-1.5 text-center text-[10.5px]">
            <div className="rounded border border-border/40 bg-card/60 px-1.5 py-1">
              <div className="text-muted-foreground/70 text-[9px] uppercase">
                Prompt
              </div>
              <div className="font-semibold text-foreground">
                {trace.prompt_tokens ?? "-"}
              </div>
            </div>
            <div className="rounded border border-border/40 bg-card/60 px-1.5 py-1">
              <div className="text-muted-foreground/70 text-[9px] uppercase">
                Hoàn tất
              </div>
              <div className="font-semibold text-foreground">
                {trace.completion_tokens ?? "-"}
              </div>
            </div>
            <div className="rounded border border-border/40 bg-card/60 px-1.5 py-1">
              <div className="text-muted-foreground/70 text-[9px] uppercase">
                Tổng token
              </div>
              <div className="font-semibold text-primary">
                {trace.total_tokens ?? "-"}
              </div>
            </div>
          </div>

          {stageEntries.length > 0 ? (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-medium text-foreground/80">
                <span className="flex items-center gap-1">
                  <Clock className="size-3" /> Độ trễ từng chặng:
                </span>
                <span className="text-primary font-semibold">
                  Tổng: {totalMs}ms
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
                {stageEntries.map(([stage, ms]) => (
                  <span
                    key={stage}
                    className="inline-flex items-center gap-1 rounded bg-card px-1.5 py-0.5 text-[10px] text-muted-foreground border border-border/40"
                  >
                    <span>{stageLabel(stage)}:</span>
                    <span className="font-semibold text-foreground">
                      {ms}ms
                    </span>
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {trace.verification?.status ? (
            <div className="flex items-center justify-between text-[10px] border-t border-border/30 pt-1">
              <span className="text-muted-foreground">Kiểm chứng:</span>
              <span className="font-semibold text-foreground">
                {trace.verification.status}
                {trace.verification.mode ? ` (${trace.verification.mode})` : ""}
              </span>
            </div>
          ) : null}

          {turn.rewrite_trace && Object.keys(turn.rewrite_trace).length > 0 ? (
            <div className="border-t border-border/30 pt-1 text-[10px]">
              <span className="text-muted-foreground">Phân rã ngữ cảnh:</span>
              <div className="mt-0.5 text-foreground/80 truncate">
                {turn.resolved_question ?? "Đã xử lý ngữ cảnh"}
              </div>
            </div>
          ) : null}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
