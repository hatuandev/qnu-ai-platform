import {
  ExternalLink,
  FileText,
  Hash,
  Layers,
  MapPin,
  Tag,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { CitationDetail } from "./compilation-types";

export function CitationDrawer({
  citationId,
  detail,
  isOpen,
  onClose,
  onNavigateToOcr,
}: {
  citationId: string | null;
  detail: CitationDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onNavigateToOcr?: (args: {
    sourceId: string;
    revisionId: string;
    runId: string;
    page?: number;
  }) => void;
}) {
  if (!citationId || !detail) return null;

  const [ocrRunId, ...rest] = citationId.split(":");
  const evidenceRef = rest.join(":");

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="sm:max-w-md p-0 flex flex-col gap-0">
        <SheetHeader className="p-4 border-b bg-muted/20">
          <div className="flex items-center gap-2">
            <Tag className="size-4 text-primary" />
            <SheetTitle className="text-sm font-semibold truncate font-mono">
              [{citationId}]
            </SheetTitle>
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            Bằng chứng nguồn đối chiếu cho trích đoạn biên soạn.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          {/* Document Identity */}
          <Card className="rounded-lg shadow-2xs">
            <CardContent className="p-3.5 space-y-2">
              <div className="flex items-center gap-2 text-foreground font-semibold">
                <FileText className="size-3.5 text-primary" />
                <span className="truncate">
                  {detail.filename || "Tài liệu nguồn"}
                </span>
              </div>

              <div className="space-y-1 pt-1 border-t text-[11px] text-muted-foreground">
                <div className="flex justify-between">
                  <span>Source ID:</span>
                  <span className="font-mono text-foreground">
                    {detail.source_id}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Revision ID:</span>
                  <span className="font-mono text-foreground">
                    {detail.revision_id}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>OCR Run ID:</span>
                  <span className="font-mono text-foreground">{ocrRunId}</span>
                </div>
                <div className="flex justify-between">
                  <span>Evidence ID:</span>
                  <span className="font-mono text-foreground font-semibold">
                    {detail.evidence_id || evidenceRef}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Location & Artifacts */}
          <Card className="rounded-lg shadow-2xs">
            <CardContent className="p-3.5 space-y-2">
              <div className="flex items-center gap-2 text-foreground font-semibold">
                <MapPin className="size-3.5 text-primary" />
                <span>Vị trí trong tài liệu</span>
              </div>

              <div className="space-y-1.5 pt-1 border-t text-[11px]">
                {detail.page_number !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Trang:</span>
                    <Badge variant="outline" className="font-mono text-xs">
                      Trang {detail.page_number}
                    </Badge>
                  </div>
                )}

                {detail.path && (
                  <div className="space-y-0.5">
                    <span className="text-muted-foreground">
                      Đường dẫn khối:
                    </span>
                    <p className="font-mono text-[10px] bg-muted/30 p-1 rounded break-all">
                      {detail.path}
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Loại Artifact:</span>
                  <Badge variant="secondary" className="font-mono text-[10px]">
                    {detail.artifact || "ocr_document"}
                  </Badge>
                </div>

                {detail.text_version && (
                  <div className="pt-2 border-t space-y-1">
                    <div className="flex items-center gap-1 text-primary font-medium">
                      <Layers className="size-3" />
                      <span>
                        Hậu OCR: Bản rà soát #{detail.text_version.version}
                      </span>
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono truncate">
                      ID: {detail.text_version.id}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Hashes & Integrity */}
          <Card className="rounded-lg shadow-2xs">
            <CardContent className="p-3.5 space-y-2">
              <div className="flex items-center gap-2 text-foreground font-semibold">
                <Hash className="size-3.5 text-primary" />
                <span>Kiểm tra toàn vẹn (Hashes)</span>
              </div>

              <div className="space-y-1.5 pt-1 border-t text-[10px] font-mono">
                <div>
                  <span className="text-muted-foreground block">
                    Canonical SHA-256:
                  </span>
                  <span className="text-foreground break-all select-all">
                    {detail.canonical_sha256}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block">
                    Manifest SHA-256:
                  </span>
                  <span className="text-foreground break-all select-all">
                    {detail.manifest_sha256}
                  </span>
                </div>
                {detail.original_canonical_sha256 && (
                  <div>
                    <span className="text-muted-foreground block">
                      Gốc trước rà soát:
                    </span>
                    <span className="text-muted-foreground break-all select-all">
                      {detail.original_canonical_sha256}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {onNavigateToOcr && detail.source_id && detail.revision_id && (
          <div className="p-3 border-t bg-card">
            <Button
              size="sm"
              variant="outline"
              className="w-full text-xs gap-1.5 h-8"
              onClick={() =>
                onNavigateToOcr({
                  sourceId: detail.source_id,
                  revisionId: detail.revision_id,
                  runId: ocrRunId,
                  page: detail.page_number,
                })
              }
            >
              <ExternalLink className="size-3" />
              <span>Mở đối chiếu OCR & Văn bản</span>
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
