import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  Layers,
  Loader2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { knowledgeApi } from "@/services/knowledge-api";
import type { DocumentGroup } from "@/types/documents";
import type { AttachDocumentGroupResponse } from "@/types/knowledge";

interface AttachGroupToKnowledgeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  group: DocumentGroup;
}

export function AttachGroupToKnowledgeDialog({
  open,
  onOpenChange,
  group,
}: AttachGroupToKnowledgeDialogProps) {
  const queryClient = useQueryClient();
  const [selectedCollectionId, setSelectedCollectionId] = useState<string>("");
  const [chunkStrategy, setChunkStrategy] = useState<string>("ClauseBasedChunker");
  const [result, setResult] = useState<AttachDocumentGroupResponse | null>(null);

  // Fetch available knowledge collections
  const { data: collections = [], isLoading: isLoadingCollections } = useQuery({
    queryKey: ["knowledge-collections"],
    queryFn: () => knowledgeApi.getCollections(),
    enabled: open,
  });

  // Server-side Preview Query (calculated across ALL group members)
  const {
    data: previewData,
    isLoading: isLoadingPreview,
    isError: isPreviewError,
    error: previewError,
  } = useQuery({
    queryKey: ["knowledge-preview-group", selectedCollectionId, group.id],
    queryFn: () => knowledgeApi.previewDocumentGroup(selectedCollectionId, group.id),
    enabled: open && Boolean(selectedCollectionId),
  });

  // Mutation to attach group to collection
  const attachMutation = useMutation({
    mutationFn: () => {
      if (!selectedCollectionId) {
        throw new Error("Vui lòng chọn Kho Tri Thức đích.");
      }
      return knowledgeApi.attachDocumentGroup(selectedCollectionId, {
        group_id: group.id,
        chunk_strategy: chunkStrategy,
        sync_policy: "manual",
        auto_activate: false,
      });
    },
    onSuccess: (data) => {
      setResult(data);
      toast.success(
        `Đã đưa nhóm vào kho thành công: ${data.created_count} mới, ${data.already_bound_count} đã có sẵn.`,
      );
      // Invalidate all related caches
      queryClient.invalidateQueries({
        queryKey: ["knowledge-collection", selectedCollectionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["collection-bindings", selectedCollectionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["document-group", group.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["document-groups"],
      });
      queryClient.invalidateQueries({
        queryKey: ["repository-documents"],
      });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Đưa nhóm vào Kho Tri Thức thất bại.");
    },
  });

  const handleClose = () => {
    onOpenChange(false);
    setTimeout(() => {
      setResult(null);
      setSelectedCollectionId("");
    }, 200);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <BookOpen className="size-5" />
            </div>
            <div>
              <DialogTitle>Đưa Nhóm Tài Liệu Vào Kho Tri Thức</DialogTitle>
              <DialogDescription>
                Tạo liên kết tri thức (Knowledge Binding) cho các tài liệu hợp lệ trong nhóm &ldquo;{group.name}&rdquo;.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {result ? (
          /* Success Result State */
          <div className="space-y-4 py-2">
            <div className="rounded-lg border border-success/30 bg-success/10 p-4">
              <div className="flex items-center gap-2 text-success font-semibold text-sm mb-1">
                <CheckCircle2 className="size-5" />
                Đưa Vào Kho Tri Thức Hoàn Tất!
              </div>
              <p className="text-xs text-muted-foreground">
                Đã xử lý toàn bộ tài liệu theo cơ chế Snapshot thủ công.
              </p>
            </div>

            {/* Results Breakdown Grid */}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 text-center">
              <div className="rounded-md border border-border/70 bg-card p-2.5">
                <div className="text-lg font-bold text-foreground">{result.total_documents}</div>
                <div className="text-[11px] text-muted-foreground">Tổng tài liệu</div>
              </div>
              <div className="rounded-md border border-success/30 bg-success/5 p-2.5">
                <div className="text-lg font-bold text-success">
                  {result.created_count}
                </div>
                <div className="text-[11px] text-success">Đã gắn mới</div>
              </div>
              <div className="rounded-md border border-info/30 bg-info/5 p-2.5">
                <div className="text-lg font-bold text-info">
                  {result.already_bound_count}
                </div>
                <div className="text-[11px] text-info">Đã tồn tại</div>
              </div>
              <div className="rounded-md border border-warning/30 bg-warning/5 p-2.5">
                <div className="text-lg font-bold text-warning">
                  {result.not_ready_count}
                </div>
                <div className="text-[11px] text-warning">Chưa sẵn sàng</div>
              </div>
            </div>

            {/* Detail items list */}
            <div className="space-y-1.5 max-h-48 overflow-y-auto rounded-md border border-border/60 p-2 text-xs">
              {result.items.map((item) => (
                <div
                  key={item.document_id}
                  className="flex items-center justify-between py-1 px-2 rounded hover:bg-muted/40"
                >
                  <span className="truncate max-w-[280px] font-medium text-foreground">
                    {item.document_title || item.document_id}
                  </span>
                  <Badge
                    variant={
                      item.status === "created"
                        ? "default"
                        : item.status === "already_bound"
                          ? "secondary"
                          : item.status === "not_ready"
                            ? "outline"
                            : "destructive"
                    }
                    className="text-[10px]"
                  >
                    {item.status === "created" && "Mới gắn"}
                    {item.status === "already_bound" && "Đã có sẵn"}
                    {item.status === "not_ready" && "Chưa ready"}
                    {item.status === "failed" && "Thất bại"}
                  </Badge>
                </div>
              ))}
            </div>

            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button type="button" variant="outline" onClick={handleClose}>
                Đóng
              </Button>
              <Button asChild className="gap-1.5">
                <Link
                  to="/knowledge/$collectionId"
                  params={{ collectionId: result.collection_id }}
                >
                  <span>Mở Trang Kho Tri Thức</span>
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            </DialogFooter>
          </div>
        ) : (
          /* Configuration & Preview Form State */
          <div className="space-y-4 py-2">
            {/* Step 1: Select Knowledge Collection */}
            <div className="space-y-1.5">
              <label htmlFor="collection-select" className="text-xs font-semibold text-foreground">
                1. Chọn Kho Tri Thức đích <span className="text-destructive">*</span>
              </label>
              {isLoadingCollections ? (
                <div className="h-9 w-full rounded-md bg-muted/40 animate-pulse" />
              ) : collections.length === 0 ? (
                <div className="rounded-md border border-dashed border-border p-3 text-center text-xs text-muted-foreground">
                  Chưa có Kho Tri Thức nào được tạo. Vui lòng tạo Kho Tri Thức trước.
                </div>
              ) : (
                <Select
                  value={selectedCollectionId}
                  onValueChange={setSelectedCollectionId}
                >
                  <SelectTrigger id="collection-select" className="w-full h-9">
                    <SelectValue placeholder="-- Chọn một Kho Tri Thức --" />
                  </SelectTrigger>
                  <SelectContent className="max-h-56">
                    {collections.map((col) => (
                      <SelectItem key={col.id} value={col.id}>
                        {col.name} ({col.document_count} tài liệu)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Step 2: Select Chunking Strategy */}
            <div className="space-y-1.5">
              <label htmlFor="chunk-strategy-select" className="text-xs font-semibold text-foreground">
                2. Chiến lược cắt đoạn (Chunking Strategy)
              </label>
              <Select value={chunkStrategy} onValueChange={setChunkStrategy}>
                <SelectTrigger id="chunk-strategy-select" className="w-full h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ClauseBasedChunker">
                    Clause-Based Chunker (Theo Điều/Khoản văn bản quy phạm)
                  </SelectItem>
                  <SelectItem value="SemanticChunker">
                    Semantic Chunker (Theo ngữ nghĩa đoạn văn)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Step 3: Server-side Snapshot Preview Banner */}
            <div className="space-y-2 rounded-lg border border-border/80 bg-muted/30 p-3.5">
              <div className="flex items-center justify-between text-xs font-semibold text-foreground">
                <div className="flex items-center gap-1.5">
                  <Layers className="size-4 text-primary" />
                  Xem trước phân tích từ Server
                </div>
                {isLoadingPreview && (
                  <div className="flex items-center gap-1 text-[11px] text-muted-foreground font-normal">
                    <Loader2 className="size-3 animate-spin text-primary" />
                    Đang phân tích...
                  </div>
                )}
              </div>

              {!selectedCollectionId ? (
                <div className="rounded border border-dashed border-border/70 p-3 text-center text-xs text-muted-foreground">
                  Vui lòng chọn Kho Tri Thức để hệ thống phân tích đối soát tự động.
                </div>
              ) : isPreviewError ? (
                <div className="rounded border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
                  <AlertCircle className="size-4 shrink-0" />
                  {(previewError as Error)?.message || "Không thể tải xem trước phân tích nhóm."}
                </div>
              ) : previewData ? (
                <>
                  <div className="grid grid-cols-4 gap-1.5 text-center text-xs">
                    <div className="rounded border border-border/70 bg-card p-2">
                      <div className="text-sm font-bold text-foreground">
                        {previewData.total_documents}
                      </div>
                      <div className="text-[10px] text-muted-foreground truncate">Tổng số</div>
                    </div>

                    <div className="rounded border border-success/30 bg-success/10 p-2">
                      <div className="flex items-center justify-center gap-0.5 text-success font-bold text-sm">
                        <CheckCircle2 className="size-3" />
                        {previewData.ready_count}
                      </div>
                      <div className="text-[10px] text-success truncate">Sẵn sàng</div>
                    </div>

                    <div className="rounded border border-info/30 bg-info/10 p-2">
                      <div className="text-sm font-bold text-info">
                        {previewData.already_bound_count}
                      </div>
                      <div className="text-[10px] text-info truncate">Đã có</div>
                    </div>

                    <div className="rounded border border-warning/30 bg-warning/10 p-2">
                      <div className="flex items-center justify-center gap-0.5 text-warning font-bold text-sm">
                        <Clock className="size-3" />
                        {previewData.not_ready_count + previewData.failed_count}
                      </div>
                      <div className="text-[10px] text-warning truncate">Chưa ready</div>
                    </div>
                  </div>

                  {previewData.ready_count === 0 && (
                    <div className="flex items-center gap-2 rounded bg-warning/10 p-2 text-[11px] text-warning-foreground">
                      <AlertCircle className="size-4 shrink-0 text-warning" />
                      {previewData.already_bound_count === previewData.total_documents && previewData.total_documents > 0
                        ? "Toàn bộ tài liệu trong nhóm đã được liên kết vào kho tri thức này."
                        : "Không có tài liệu nào ở trạng thái ready để gắn mới vào kho."}
                    </div>
                  )}
                </>
              ) : null}
            </div>

            {/* Step 4: Snapshot Policy Notice */}
            <div className="flex items-start gap-2.5 rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs text-warning-foreground">
              <AlertTriangle className="size-4 shrink-0 text-warning mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-semibold">Lưu ý quan trọng:</span>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Đây là thao tác snapshot thủ công tại thời điểm bấm. Những tài liệu được thêm vào nhóm sau này sẽ không tự động đồng bộ vào Kho Tri Thức production.
                </p>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button type="button" variant="ghost" onClick={handleClose} disabled={attachMutation.isPending}>
                Hủy
              </Button>
              <Button
                type="button"
                onClick={() => attachMutation.mutate()}
                disabled={
                  attachMutation.isPending ||
                  !selectedCollectionId ||
                  isLoadingPreview ||
                  !previewData ||
                  previewData.ready_count === 0
                }
                className="gap-1.5"
              >
                <BookOpen className="size-4" />
                {attachMutation.isPending ? "Đang liên kết..." : "Đưa Vào Kho Tri Thức"}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
