import { Download } from "lucide-react";
import { useRef, useState, useSyncExternalStore } from "react";
import { getTokenState, subscribeToken, v1Client } from "@/app/api/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Button } from "@/components/ui/button";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { downloadBlob } from "@/lib/download-blob";
import {
  downloadCompilationReviewMarkdownBlob,
  getCompilationReviewRaw,
} from "./compilation-requests";
import type { ReviewStatus } from "./compilation-types";

type Props = {
  workspaceId: string;
  collectionId: string;
  runId: string;
  reviewId: string;
  status: ReviewStatus;
};
export function ReviewDownloads(props: Props) {
  const { sessionId } = useSyncExternalStore(
    subscribeToken,
    getTokenState,
    getTokenState,
  );
  return (
    <ReviewDownloadsSession
      key={`${sessionId}:${props.workspaceId}:${props.collectionId}:${props.runId}:${props.reviewId}`}
      {...props}
    />
  );
}
function ReviewDownloadsSession({
  workspaceId,
  collectionId,
  runId,
  reviewId,
  status,
}: Props) {
  const current = useActionScope();
  const active = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const terminal = ["completed", "failed", "uncertain"].includes(status);
  const handleDownload = async (raw: boolean) => {
    if (active.current || !terminal || (!raw && status !== "completed")) return;
    active.current = true;
    setBusy(true);
    setError(null);
    try {
      const load = raw
        ? getCompilationReviewRaw
        : downloadCompilationReviewMarkdownBlob;
      const result = await load(
        v1Client,
        workspaceId,
        collectionId,
        runId,
        reviewId,
      );
      if (current())
        downloadBlob(
          result.blob,
          result.fileName ?? `review-${reviewId}${raw ? "-raw.json" : ".md"}`,
        );
    } catch (cause) {
      if (current()) setError(cause);
    } finally {
      active.current = false;
      if (current()) setBusy(false);
    }
  };
  return (
    <section
      aria-label="Tải tệp review"
      className="space-y-2 rounded-lg border p-3"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">Tệp của lần rà soát</span>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy || !terminal}
          onClick={() => void handleDownload(true)}
        >
          <Download className="size-3.5" />
          Tải bản gốc
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy || status !== "completed"}
          aria-label="Tải Markdown báo cáo"
          onClick={() => void handleDownload(false)}
        >
          <Download className="size-3.5" />
          Tải Markdown
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Bản gốc là phản hồi model nguyên trạng, có thể chưa hợp lệ khi rà soát
        thất bại. Server sẽ báo nếu chưa có tệp.
      </p>
      {busy ? (
        <p role="status" className="text-sm">
          Đang tải tệp…
        </p>
      ) : null}
      {error ? <ErrorState error={error} /> : null}
    </section>
  );
}
