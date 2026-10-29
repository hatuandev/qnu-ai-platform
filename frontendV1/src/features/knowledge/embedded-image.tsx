import { ImageIcon, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ocrPaths, v1Client } from "@/app/api/v1";

export function AuthenticatedEmbeddedImage({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  runId,
  assetNo,
  alt = "Ảnh trích xuất từ tài liệu",
  className = "max-w-full rounded border shadow-2xs",
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  runId: string;
  assetNo: number;
  alt?: string;
  className?: string;
}) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let currentUrl: string | null = null;
    setLoading(true);
    setError(null);

    async function loadImage() {
      try {
        const path = ocrPaths.image(
          workspaceId,
          collectionId,
          sourceId,
          revisionId,
          runId,
          assetNo,
        );
        const res = await v1Client.requestBlob(path, {
          headers: { Accept: "image/*" },
        });
        if (cancelled) return;
        currentUrl = URL.createObjectURL(res.blob);
        setBlobUrl(currentUrl);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Không tải được ảnh đính kèm",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadImage();

    return () => {
      cancelled = true;
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [workspaceId, collectionId, sourceId, revisionId, runId, assetNo]);

  if (loading) {
    return (
      <div className="flex h-36 w-full items-center justify-center rounded border bg-muted/20 text-muted-foreground text-xs gap-2">
        <Loader2 className="size-4 animate-spin text-primary" />
        <span>Đang tải ảnh #{assetNo}...</span>
      </div>
    );
  }

  if (error || !blobUrl) {
    return (
      <div className="flex h-24 w-full items-center justify-center rounded border border-dashed text-muted-foreground text-xs gap-2">
        <ImageIcon className="size-4 text-muted-foreground/60" />
        <span>Không tải được ảnh #{assetNo}</span>
      </div>
    );
  }

  return <img src={blobUrl} alt={alt} className={className} loading="lazy" />;
}
