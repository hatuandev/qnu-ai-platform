import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Info,
  Quote,
  ShieldQuestion,
} from "lucide-react";
import { useId, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { VerificationFinding, VerificationTrace } from "./types";
import { VERIFICATION_STATUS_LABEL } from "./types";

/**
 * Renders `trace.verification`.
 *
 * Rules encoded here:
 * - `off` / `not_run` render nothing; there is no "verified" claim without a run.
 * - `supported` is reported as an automatic check, never as a guarantee.
 * - `unsupported` / `uncertain` are warnings the reader can inspect: reason plus
 *   the quoted evidence the judge used.
 * - Missing judge usage stays unknown; it is never rendered as 0.
 */
export function VerificationPanel({
  trace,
  onOpenEvidence,
}: {
  trace: VerificationTrace | undefined;
  onOpenEvidence?: (evidenceId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const contentId = useId();

  if (!trace) return null;
  const mode = trace.mode ?? "off";
  const status = trace.status ?? "not_run";
  if (mode === "off" || status === "not_run") return null;

  const findings = trace.findings ?? [];
  const flagged = findings.filter((finding) => finding.status !== "supported");
  const isSupported = status === "supported";

  return (
    <div
      className={cn(
        "w-full rounded-xl border text-xs",
        isSupported
          ? "border-success/30 bg-success/5"
          : "border-warning/40 bg-warning/5",
      )}
    >
      <div className="flex flex-wrap items-start gap-2 p-3">
        <span
          className={cn(
            "mt-0.5 shrink-0",
            isSupported ? "text-success" : "text-warning",
          )}
        >
          {isSupported ? (
            <CheckCircle2 className="size-4" />
          ) : (
            <AlertTriangle className="size-4" />
          )}
        </span>

        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-semibold text-foreground">
              {isSupported
                ? "Đã kiểm chứng: mọi câu đều có trích đoạn nguồn hỗ trợ"
                : status === "unsupported"
                  ? "Cảnh báo: có câu chưa được nguồn hỗ trợ"
                  : "Cảnh báo: chưa xác định được căn cứ của câu trả lời"}
            </span>
            <Badge variant="outline" className="text-[10px] py-0 font-mono">
              {mode}
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] py-0",
                isSupported ? "text-success" : "text-warning",
              )}
            >
              {VERIFICATION_STATUS_LABEL[status]}
            </Badge>
          </div>

          <p className="text-[11px] leading-relaxed text-muted-foreground">
            {isSupported
              ? "Đây là kiểm tra tự động bằng mô hình trên đúng trích đoạn đã dẫn. Kết quả không phải bảo đảm tuyệt đối rằng câu trả lời đúng về mặt ngữ nghĩa; hãy đối chiếu nguồn khi cần độ chính xác cao."
              : mode === "observe"
                ? "Chế độ quan sát: câu trả lời vẫn được hiển thị nhưng có câu chưa được nguồn xác nhận. Đọc kỹ lý do và trích đoạn bên dưới trước khi sử dụng."
                : "Chế độ chặn: câu trả lời chưa đạt kiểm chứng nên không được phát hành. Đây là kết quả kiểm chứng, không phải lỗi kết nối."}
          </p>

          {!isSupported && flagged.length > 0 ? (
            <ul className="space-y-1.5 pt-1" role="alert">
              {flagged.map((finding) => (
                <VerificationFindingRow
                  key={`${finding.statement_index}-${finding.status}`}
                  finding={finding}
                  onOpenEvidence={onOpenEvidence}
                />
              ))}
            </ul>
          ) : null}
        </div>
      </div>

      <Collapsible open={open} onOpenChange={setOpen}>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-muted-foreground">
            <span>
              Kiểm chứng:{" "}
              {trace.model_name ?? trace.provider_id ?? "không rõ model"}
            </span>
            <span>
              Token kiểm chứng:{" "}
              {formatUsage(
                trace.total_tokens,
                trace.prompt_tokens,
                trace.completion_tokens,
              )}
            </span>
          </div>
          <CollapsibleTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-6 gap-1 px-2 text-[11px] text-primary"
              aria-controls={contentId}
            >
              <Info className="size-3" />
              <span>{open ? "Ẩn báo cáo" : "Xem báo cáo kiểm chứng"}</span>
              <ChevronDown
                className={cn(
                  "size-3 transition-transform",
                  open && "rotate-180",
                )}
              />
            </Button>
          </CollapsibleTrigger>
        </div>

        <CollapsibleContent id={contentId} className="border-t px-3 py-2">
          {findings.length === 0 ? (
            <p className="text-[11px] text-muted-foreground">
              Backend không kèm báo cáo chi tiết cho lượt này.
            </p>
          ) : (
            <ol className="space-y-2">
              {findings.map((finding) => (
                <li
                  key={`report-${finding.statement_index}`}
                  className="rounded-lg border bg-card/60 p-2.5"
                >
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-mono text-[10px] text-muted-foreground">
                      Câu #{finding.statement_index + 1}
                    </span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[10px] py-0",
                        finding.status === "supported"
                          ? "text-success"
                          : finding.status === "unsupported"
                            ? "text-destructive"
                            : "text-warning",
                      )}
                    >
                      {VERIFICATION_STATUS_LABEL[finding.status]}
                    </Badge>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-foreground">
                    {finding.reason}
                  </p>
                  {finding.quotes && finding.quotes.length > 0 ? (
                    <ul className="mt-1.5 space-y-1">
                      {finding.quotes.map((quote) => (
                        <li
                          key={`${quote.evidence_id}-${quote.quote.slice(0, 24)}`}
                          className="flex items-start gap-1.5 rounded bg-muted/40 px-2 py-1"
                        >
                          <Quote className="mt-0.5 size-3 shrink-0 text-muted-foreground" />
                          <span className="text-[11px] italic leading-relaxed text-muted-foreground">
                            “{quote.quote}”
                          </span>
                          {onOpenEvidence ? (
                            <button
                              type="button"
                              className="ml-auto shrink-0 font-mono text-[10px] text-primary underline-offset-2 hover:underline"
                              onClick={() => onOpenEvidence(quote.evidence_id)}
                            >
                              {quote.evidence_id}
                            </button>
                          ) : (
                            <span className="ml-auto shrink-0 font-mono text-[10px] text-muted-foreground">
                              {quote.evidence_id}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
          <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
            Điểm số truy xuất ở các thang khác nhau không cộng trực tiếp và
            không phải xác suất câu trả lời đúng.
          </p>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

function VerificationFindingRow({
  finding,
  onOpenEvidence,
}: {
  finding: VerificationFinding;
  onOpenEvidence?: (evidenceId: string) => void;
}) {
  return (
    <li className="rounded-lg border border-warning/30 bg-card/60 px-2.5 py-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <ShieldQuestion className="size-3 text-warning shrink-0" />
        <span className="font-mono text-[10px] text-muted-foreground">
          Câu #{finding.statement_index + 1}
        </span>
        <span className="text-[11px] text-foreground">{finding.reason}</span>
      </div>
      {finding.quotes && finding.quotes.length > 0 ? (
        <p className="mt-1 text-[11px] italic leading-relaxed text-muted-foreground">
          Trích đoạn đã đối chiếu: “{finding.quotes[0].quote}”
          {onOpenEvidence ? (
            <button
              type="button"
              className="ml-1 font-mono text-[10px] not-italic text-primary underline-offset-2 hover:underline"
              onClick={() =>
                onOpenEvidence(finding.quotes?.[0]?.evidence_id ?? "")
              }
            >
              [{finding.quotes[0].evidence_id}]
            </button>
          ) : null}
        </p>
      ) : (
        <p className="mt-1 text-[11px] text-muted-foreground">
          Mô hình không dẫn được trích đoạn nào cho câu này.
        </p>
      )}
    </li>
  );
}

/** Judge usage: unknown stays unknown; never rendered as a measured 0. */
export function formatUsage(
  total: number | null | undefined,
  prompt?: number | null,
  completion?: number | null,
): string {
  if (typeof total === "number") return String(total);
  if (typeof prompt === "number" && typeof completion === "number") {
    return `${prompt + completion} (tính từ prompt + completion)`;
  }
  return "không rõ";
}
