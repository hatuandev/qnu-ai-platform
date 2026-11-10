import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useMemo } from "react";
import { useTextReviewChecksQuery } from "@/api/ocr/queries";
import { Button } from "@/components/ui/button";

interface SpellingStatusStripProps {
  workspaceId?: string | null;
  collectionId?: string | null;
  sourceId: string;
  revisionId?: string | null;
  ocrRunId?: string | null;
  textVersion?: number;
}

export function SpellingStatusStrip({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  ocrRunId,
  textVersion,
}: SpellingStatusStripProps) {
  // Query spelling checks for the pinned OCR run & text version
  const { data: checks, isLoading } = useTextReviewChecksQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    ocrRunId,
    textVersion,
    {
      refetchInterval: 5000,
    },
  );

  const latestCheck = useMemo(() => {
    if (!checks || checks.length === 0) return null;
    return checks[0];
  }, [checks]);

  // If there's no OCR run or checks haven't been initiated yet, don't show anything intrusive
  if (!ocrRunId || (!isLoading && !latestCheck)) {
    return null;
  }

  if (isLoading && !latestCheck) {
    return (
      <div className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-muted/40 border border-border/60 text-xs text-muted-foreground animate-pulse">
        <Loader2 className="size-3.5 animate-spin text-primary shrink-0" />
        <span>Đang kiểm tra trạng thái soát chính tả...</span>
      </div>
    );
  }

  if (!latestCheck) return null;

  const status = latestCheck.status;
  const suggestionCount = latestCheck.suggestions?.length || 0;

  // 1. STATE: Check is running in background
  if (status === "running") {
    return (
      <div className="flex items-center justify-between gap-3 px-3.5 py-2 rounded-lg bg-primary/5 border border-primary/20 text-xs text-foreground">
        <div className="flex items-center gap-2 min-w-0">
          <Loader2 className="size-3.5 animate-spin text-primary shrink-0" />
          <span className="font-medium text-primary">Đang soát chính tả…</span>
          <span className="text-muted-foreground hidden sm:inline truncate">
            Hệ thống đang tự động rà soát văn bản trong nền mà không khóa tài
            liệu.
          </span>
        </div>
      </div>
    );
  }

  // 2. STATE: Check completed with suggestions
  if (status === "completed" && suggestionCount > 0) {
    return (
      <div className="flex items-center justify-between gap-3 px-3.5 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-foreground shadow-2xs">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="size-4 text-amber-600 dark:text-amber-400 shrink-0" />
          <span className="font-semibold text-foreground">
            Có {suggestionCount} vị trí nghi sai
          </span>
          <span className="text-muted-foreground hidden md:inline truncate">
            AI đã phát hiện các điểm nghi ngờ chính tả đối chiếu với văn bản
            gốc.
          </span>
        </div>

        <Button
          asChild
          variant="outline"
          size="sm"
          className="h-7 px-2.5 text-xs font-medium border-amber-500/40 hover:bg-amber-500/20 text-foreground gap-1.5 shrink-0"
        >
          <Link
            to="/knowledge/$sourceId/review"
            params={{ sourceId }}
            search={{ collectionId: collectionId || undefined }}
          >
            <span>Xem gợi ý</span>
            <ArrowRight className="size-3" />
          </Link>
        </Button>
      </div>
    );
  }

  // 3. STATE: Check completed cleanly (0 suggestions)
  if (status === "completed" && suggestionCount === 0) {
    return (
      <div className="flex items-center justify-between gap-3 px-3.5 py-2 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs text-foreground">
        <div className="flex items-center gap-2 min-w-0">
          <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span className="font-medium text-emerald-700 dark:text-emerald-400">
            Chưa phát hiện lỗi chính tả.
          </span>
          <span className="text-muted-foreground hidden sm:inline truncate">
            Đã rà soát toàn bộ các phân đoạn trong văn bản đối chiếu.
          </span>
        </div>

        <Button
          asChild
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground shrink-0"
        >
          <Link
            to="/knowledge/$sourceId/review"
            params={{ sourceId }}
            search={{ collectionId: collectionId || undefined }}
          >
            <span>Xem chi tiết</span>
          </Link>
        </Button>
      </div>
    );
  }

  // 4. STATE: Check interrupted, failed, or uncertain
  if (status === "failed" || status === "uncertain" || status === "cancelled") {
    return (
      <div className="flex items-center justify-between gap-3 px-3.5 py-2 rounded-lg bg-destructive/5 border border-destructive/20 text-xs text-foreground">
        <div className="flex items-center gap-2 min-w-0">
          <AlertTriangle className="size-3.5 text-destructive shrink-0" />
          <span className="font-medium text-destructive">
            Kiểm tra chưa hoàn tất
          </span>
          <span className="text-muted-foreground hidden sm:inline truncate">
            {latestCheck.error_code
              ? `(Mã lỗi: ${latestCheck.error_code})`
              : "Dịch vụ mô hình gián đoạn hoặc quá thời gian phản hồi."}
          </span>
        </div>

        <Button
          asChild
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground shrink-0"
        >
          <Link
            to="/knowledge/$sourceId/review"
            params={{ sourceId }}
            search={{ collectionId: collectionId || undefined }}
          >
            <span>Xem chi tiết</span>
          </Link>
        </Button>
      </div>
    );
  }

  return null;
}
