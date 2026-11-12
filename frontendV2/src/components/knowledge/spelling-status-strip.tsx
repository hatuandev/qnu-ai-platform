import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useTextReviewChecksQuery } from "@/api/ocr/queries";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  currentSpellingCheck,
  formatSpellingMoment,
  spellingCoverage,
  spellingIgnoredCount,
  spellingPendingCount,
  spellingPercent,
} from "@/lib/spelling-review";

interface SpellingStatusStripProps {
  workspaceId?: string | null;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  runId: string;
  textVersion: number;
}

export function SpellingStatusStrip({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  runId,
  textVersion,
}: SpellingStatusStripProps) {
  const { data, isLoading, isError } = useTextReviewChecksQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    runId,
    undefined,
    { refetchInterval: 5000 },
  );
  const check = currentSpellingCheck(data, textVersion);
  const coverage = check ? spellingCoverage(check) : null;
  const percent = coverage
    ? spellingPercent(coverage.checked, coverage.total)
    : null;
  const pending = check ? spellingPendingCount(check) : 0;
  const ignored = spellingIgnoredCount(check);
  const complete = coverage?.complete === true;
  const reviewed = check?.reviewed_at != null;
  const running = check?.status === "running";
  const failed = check?.status === "failed";
  const interrupted = check?.status === "uncertain";

  const label = isError
    ? "Không tải được kết quả soát chính tả"
    : isLoading
      ? "Đang tải kết quả soát chính tả…"
      : !check
        ? "Chưa có kết quả soát chính tả"
        : running
          ? "Đang soát chính tả…"
          : failed
            ? "Soát chính tả gặp lỗi"
            : interrupted
              ? "Soát chính tả bị gián đoạn"
              : reviewed
                ? `Đã duyệt chính tả${ignored > 0 ? ` · ${ignored} vị trí bỏ qua` : ""}`
                : !complete
                  ? "Chưa soát xong toàn bộ văn bản"
                  : pending > 0
                    ? `Có ${pending} vị trí cần xem${ignored > 0 ? ` · ${ignored} đã bỏ qua` : ""}`
                    : coverage?.total === 0
                      ? "Không có đoạn văn để soát"
                      : ignored > 0
                        ? `Đã bỏ qua ${ignored} vị trí · cần hoàn tất duyệt`
                        : "Chưa phát hiện lỗi chính tả";

  const Icon =
    isLoading || running
      ? Loader2
      : reviewed
        ? BadgeCheck
        : complete && pending === 0
          ? CheckCircle2
          : isError || (check && !complete)
            ? AlertTriangle
            : Sparkles;

  const action = reviewed
    ? "Xem kết quả"
    : pending > 0
      ? "Xem gợi ý"
      : !check
        ? "Mở rà soát"
        : complete
          ? "Duyệt chính tả"
          : "Xem chi tiết";

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs">
      <div className="flex flex-1 flex-wrap items-center gap-2" role="status">
        <Icon
          className={isLoading || running ? "size-4 animate-spin" : "size-4"}
        />
        <span>{label}</span>
        {coverage && !complete && percent !== null && (
          <span className="flex items-center gap-1.5">
            <Progress
              value={percent}
              className={
                failed || interrupted
                  ? "h-1.5 w-16 bg-destructive/15 sm:w-24 [&>[data-slot=progress-indicator]]:bg-destructive"
                  : "h-1.5 w-16 sm:w-24"
              }
              aria-label={`Tiến độ soát chính tả ${percent}%`}
            />
            <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
              {percent}%
            </span>
          </span>
        )}
        {coverage && !complete && (
          <span className="text-muted-foreground">
            {coverage.total === null
              ? `${coverage.checked} đoạn đã soát`
              : `${coverage.checked}/${coverage.total} đoạn đã soát`}
          </span>
        )}
        {reviewed && check?.reviewed_at && (
          <span className="text-muted-foreground">
            lúc {formatSpellingMoment(check.reviewed_at)}
          </span>
        )}
      </div>
      {isError ? null : (
        <Button asChild variant="outline" size="sm" className="h-7 text-xs">
          <Link
            to="/knowledge/$sourceId/review"
            params={{ sourceId }}
            search={{ collectionId, revisionId, runId }}
          >
            {action}
          </Link>
        </Button>
      )}
    </div>
  );
}
