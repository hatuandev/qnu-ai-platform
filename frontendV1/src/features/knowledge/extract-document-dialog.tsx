import { useNavigate } from "@tanstack/react-router";
import { FileText, Loader2, Play, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRequestProcessingRunMutation } from "@/features/knowledge/ocr-queries";
import { useSourcesQuery } from "@/features/knowledge/queries";
import {
  formatBytes,
  formatProcessingStatus,
  isDocx,
  isPdf,
} from "@/features/knowledge/schemas";
import type { KBSource } from "@/features/knowledge/types";

export function ExtractDocumentDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
}) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [extractingSourceId, setExtractingSourceId] = useState<string | null>(
    null,
  );

  // Fetch sources for selection
  const sourcesQuery = useSourcesQuery(workspaceId, collectionId, {
    page: 1,
    pageSize: 100,
    allFolders: true,
  });

  const sources = sourcesQuery.data?.items ?? [];

  const filteredSources = useMemo(() => {
    if (!search.trim()) return sources;
    const q = search.toLowerCase().trim();
    return sources.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.file_name.toLowerCase().includes(q),
    );
  }, [sources, search]);

  const requestRunMutation = useRequestProcessingRunMutation(
    workspaceId,
    collectionId,
    extractingSourceId ?? "",
    "",
  );

  const handleStartExtraction = async (source: KBSource) => {
    setExtractingSourceId(source.id);
    try {
      // Find latest revision id from processing if available, or fetch
      const revisionId = source.processing?.revision_id;
      if (!revisionId) {
        // If no processing info yet, navigate to source detail where active revision is loaded
        onOpenChange(false);
        void navigate({
          to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
          params: { workspaceId, collectionId, sourceId: source.id },
        });
        return;
      }

      const result = await requestRunMutation.mutateAsync({
        strategy: "auto",
        force: false,
      });

      toast.success(
        result.created
          ? "Đã gửi yêu cầu bóc tách tài liệu."
          : "Mở lượt bóc tách hiện có.",
      );
      onOpenChange(false);
      void navigate({
        to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
        params: { workspaceId, collectionId, sourceId: source.id },
        search: { runId: result.run.id },
      });
    } catch {
      // Fallback navigate to source detail
      onOpenChange(false);
      void navigate({
        to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
        params: { workspaceId, collectionId, sourceId: source.id },
      });
    } finally {
      setExtractingSourceId(null);
    }
  };

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-h-[min(720px,calc(100vh-2rem))] max-w-xl p-0 gap-0 flex flex-col">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-3.5 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2 text-base font-semibold">
            <Play className="size-4 text-primary" />
            <span>Chọn tài liệu cần bóc tách</span>
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Bóc tách chủ động bằng phương pháp native-first. Chọn một tài liệu
            bên dưới để bắt đầu hoặc xem kết quả.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <div className="p-3 border-b bg-card">
          <div className="relative">
            <Search className="size-3.5 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm theo tên tài liệu hoặc tệp..."
              className="text-xs h-8 pl-8"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[420px]">
          {sourcesQuery.isLoading ? (
            <div className="py-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="size-4 animate-spin text-primary" />
              <span>Đang tải danh sách tài liệu...</span>
            </div>
          ) : filteredSources.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              {search
                ? "Không tìm thấy tài liệu phù hợp."
                : "Chưa có tài liệu nào trong kho. Hãy tải tài liệu lên trước."}
            </div>
          ) : (
            filteredSources.map((source) => {
              const statusInfo = formatProcessingStatus(source.processing);
              const pdf = isPdf(source.content_type, source.file_name);
              const docx = isDocx(source.content_type, source.file_name);
              const isExtracting = extractingSourceId === source.id;

              return (
                <div
                  key={source.id}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg border bg-card hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-start gap-2.5 min-w-0 flex-1">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded bg-muted text-muted-foreground">
                      <FileText className="size-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-foreground truncate">
                        {source.title}
                      </p>
                      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-0.5">
                        <span className="font-mono uppercase">
                          {pdf ? "PDF" : docx ? "DOCX" : "Tệp"}
                        </span>
                        <span>·</span>
                        <span>{formatBytes(source.size_bytes)}</span>
                        <span>·</span>
                        <Badge
                          variant={statusInfo.variant}
                          className="text-[10px] py-0 px-1 font-normal"
                        >
                          {statusInfo.label}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <Button
                    size="sm"
                    variant={
                      statusInfo.status === "completed" ? "outline" : "default"
                    }
                    className="h-7 text-xs px-2.5 shrink-0 gap-1"
                    disabled={isExtracting}
                    onClick={() => {
                      if (
                        statusInfo.status === "completed" ||
                        statusInfo.status === "running"
                      ) {
                        onOpenChange(false);
                        void navigate({
                          to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
                          params: {
                            workspaceId,
                            collectionId,
                            sourceId: source.id,
                          },
                          search: source.processing?.id
                            ? { runId: source.processing.id }
                            : undefined,
                        });
                      } else {
                        void handleStartExtraction(source);
                      }
                    }}
                  >
                    {isExtracting ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <Play className="size-3" />
                    )}
                    <span>
                      {statusInfo.status === "completed"
                        ? "Xem kết quả"
                        : statusInfo.status === "running"
                          ? "Theo dõi"
                          : "Bóc tách"}
                    </span>
                  </Button>
                </div>
              );
            })
          )}
        </div>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
