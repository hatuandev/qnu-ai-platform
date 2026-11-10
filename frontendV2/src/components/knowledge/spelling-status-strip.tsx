import { Link } from "@tanstack/react-router";
import { AlertTriangle, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { useTextReviewChecksQuery } from "@/api/ocr/queries";
import { Button } from "@/components/ui/button";
import {
  preferredSpellingCheck,
  spellingCoverage,
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
    textVersion,
    { refetchInterval: 5000 },
  );
  const check = preferredSpellingCheck(data);
  const coverage = check ? spellingCoverage(check) : null;
  const count =
    (check?.suggestions.length ?? 0) +
    (check?.withheld_suggestions?.length ?? 0);
  const running = check?.status === "running";
  const complete = coverage?.complete === true;
  const label = isError
    ? "Không tải được kết quả soát chính tả"
    : isLoading
      ? "Đang tải kết quả soát chính tả…"
      : running
        ? "Đang soát chính tả…"
        : complete
          ? count
            ? `Có ${count} vị trí cần xem`
            : coverage?.total === 0
              ? "Không có đoạn văn để soát"
              : "Chưa phát hiện lỗi chính tả"
          : check
            ? "Chưa soát xong toàn bộ văn bản"
            : "Chưa có kết quả soát chính tả";
  const Icon =
    isLoading || running
      ? Loader2
      : complete && !count
        ? CheckCircle2
        : isError || (check && !complete)
          ? AlertTriangle
          : Sparkles;

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs">
      <div className="flex flex-1 flex-wrap items-center gap-2" role="status">
        <Icon
          className={isLoading || running ? "size-4 animate-spin" : "size-4"}
        />
        <span>{label}</span>
        {coverage && coverage.checked > 0 && !complete && (
          <span className="text-muted-foreground">
            {coverage.total === null
              ? `${coverage.checked} đoạn đã soát`
              : `${coverage.checked}/${coverage.total} đoạn đã soát`}
          </span>
        )}
      </div>
      {check && (count > 0 || !complete) && (
        <Button asChild variant="outline" size="sm" className="h-7 text-xs">
          <Link
            to="/knowledge/$sourceId/review"
            params={{ sourceId }}
            search={{ collectionId, revisionId, runId, textVersion }}
          >
            {count ? "Xem gợi ý" : "Xem chi tiết"}
          </Link>
        </Button>
      )}
    </div>
  );
}
