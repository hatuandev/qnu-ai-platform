import { Quote, Tags } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RetrievalAnnotation } from "@/features/rag/types";
import {
  describeAnnotationTarget,
  describeMetadataValues,
} from "@/features/rag/types";

/**
 * Read-only view of a version's declared metadata.
 *
 * Every value is shown together with the quote that proves it, because the
 * approver has to confirm they reviewed *this* metadata before the backend
 * accepts `review_ack.retrieval_metadata_sha256`.
 */
export function RetrievalMetadataView({
  annotations,
  sha256,
  className,
}: {
  annotations: RetrievalAnnotation[] | null | undefined;
  sha256?: string | null;
  className?: string;
}) {
  const list = annotations ?? [];

  return (
    <Card className={`rounded-xl shadow-2xs ${className ?? ""}`}>
      <CardHeader className="p-3 sm:p-4 border-b bg-muted/10">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Tags className="size-4 text-primary" />
            <CardTitle className="text-xs font-semibold text-foreground">
              Metadata truy xuất ({list.length})
            </CardTitle>
          </div>
          {sha256 ? (
            <span
              className="text-[10px] font-mono text-muted-foreground truncate max-w-[240px]"
              title={`retrieval_metadata_sha256: ${sha256}`}
            >
              SHA-256: {sha256.slice(0, 16)}...
            </span>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="p-3 sm:p-4 space-y-3">
        {list.length === 0 ? (
          <p className="text-[11px] text-muted-foreground">
            Phiên bản này không khai báo metadata truy xuất. Tìm kiếm có lọc
            theo năm/ngành/đợt sẽ không trả về tài liệu này.
          </p>
        ) : (
          list.map((annotation) => (
            <div
              key={annotation.target}
              className="rounded-lg border bg-card p-3 space-y-2"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono max-w-full truncate"
                >
                  {annotation.target}
                </Badge>
                <span className="text-[11px] text-muted-foreground">
                  {describeAnnotationTarget(annotation.target)}
                </span>
              </div>

              <p className="text-xs text-foreground">
                {describeMetadataValues(annotation.values)}
              </p>

              <div className="space-y-1.5 border-t pt-2">
                <p className="text-[11px] font-medium text-muted-foreground flex items-center gap-1.5">
                  <Quote className="size-3" />
                  Căn cứ ({annotation.evidence.length})
                </p>
                {annotation.evidence.map((evidence) => (
                  <div
                    key={`${evidence.citation}:${evidence.quote}`}
                    className="rounded-md bg-muted/30 px-2 py-1.5 space-y-0.5"
                  >
                    <p className="text-[10px] font-mono text-primary truncate">
                      [{evidence.citation}]
                    </p>
                    <p className="text-[11px] text-foreground/90 whitespace-pre-wrap">
                      {evidence.quote}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
