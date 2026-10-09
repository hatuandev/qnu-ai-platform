import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRightLeft,
  CheckCircle2,
  ExternalLink,
  History,
  Layers,
  Link2,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { knowledgeApi } from "@/services/knowledge-api";
import type { KnowledgeBinding, KnowledgeCollection } from "@/types/knowledge";

interface CollectionBindingsTabProps {
  collection: KnowledgeCollection;
}

export const CollectionBindingsTab: React.FC<CollectionBindingsTabProps> = ({
  collection,
}) => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Selected binding for inspecting Index Revisions
  const [selectedBinding, setSelectedBinding] =
    useState<KnowledgeBinding | null>(null);
  const [isBindDialogOpen, setIsBindDialogOpen] = useState(false);
  const [detachTarget, setDetachTarget] = useState<KnowledgeBinding | null>(
    null,
  );

  // Promote Dialog State
  const [isPromoteDialogOpen, setIsPromoteDialogOpen] = useState(false);
  const [targetIndexRevId, setTargetIndexRevId] = useState<string | null>(null);
  const [promoteReason, setPromoteReason] = useState("");

  // 1. Fetch Bindings
  const {
    data: bindings = [],
    isLoading,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["knowledge-bindings", collection.id],
    queryFn: () => knowledgeApi.getBindings(collection.id),
  });

  // 2. Fetch Index Revisions for selected binding
  const { data: indexRevisions = [], isLoading: isRevisionsLoading } = useQuery(
    {
      queryKey: ["binding-index-revisions", selectedBinding?.id],
      queryFn: () =>
        selectedBinding
          ? knowledgeApi.getIndexRevisions(selectedBinding.id)
          : Promise.resolve([]),
      enabled: !!selectedBinding,
    },
  );

  // 3. Build Staging Index Mutation
  const buildIndexMutation = useMutation({
    mutationFn: (bindingId: string) =>
      knowledgeApi.buildStagingIndex(bindingId, {
        chunk_strategy: collection.chunking_strategy,
        auto_activate: false,
      }),
    onSuccess: (data) => {
      toast.success(
        `Đã tạo chỉ mục Staging v${data.revision_no} (Parity Gate: ${
          data.parity_report?.parity_status === "passed"
            ? "Đạt"
            : "Cần kiểm tra"
        }).`,
      );
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collection.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["binding-index-revisions", selectedBinding?.id],
      });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Dựng chỉ mục staging thất bại.");
    },
  });

  // 4. Promote Mutation (Atomic Pointer Swap)
  const promoteMutation = useMutation({
    mutationFn: () => {
      if (!selectedBinding || !targetIndexRevId)
        throw new Error("Chưa chọn phiên bản chỉ mục");
      return knowledgeApi.promoteIndexRevision(selectedBinding.id, {
        to_index_revision_id: targetIndexRevId,
        expected_epoch: selectedBinding.active_epoch,
        reason: promoteReason.trim() || undefined,
      });
    },
    onSuccess: (res) => {
      toast.success(
        `Đã kích hoạt nguyên tử chỉ mục thành công (Epoch ${res.epoch})!`,
      );
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collection.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["binding-index-revisions", selectedBinding?.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["collection", collection.id],
      });
      setIsPromoteDialogOpen(false);
      setTargetIndexRevId(null);
    },
    onError: (err: unknown) => {
      const errorObj = err as {
        status?: number;
        code?: string;
        message?: string;
      };
      if (
        errorObj?.status === 409 ||
        errorObj?.code === "CAS_EPOCH_CONFLICT" ||
        errorObj?.message?.includes("CAS")
      ) {
        toast.error(
          "Xung đột phiên bản (CAS Conflict): Liên kết vừa được cập nhật bởi một tác vụ khác. Đang tải lại dữ liệu...",
        );
        queryClient.invalidateQueries({
          queryKey: ["knowledge-bindings", collection.id],
        });
        queryClient.invalidateQueries({
          queryKey: ["binding-index-revisions", selectedBinding?.id],
        });
      } else {
        toast.error(errorObj?.message || "Kích hoạt chỉ mục thất bại.");
      }
    },
  });

  // 5. Detach Binding Mutation
  const detachMutation = useMutation({
    mutationFn: (bindingId: string) => knowledgeApi.detachBinding(bindingId),
    onSuccess: () => {
      toast.success("Đã hủy liên kết tài liệu khỏi kho tri thức.");
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collection.id],
      });
      if (selectedBinding?.id === detachTarget?.id) {
        setSelectedBinding(null);
      }
      setDetachTarget(null);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Hủy liên kết thất bại.");
    },
  });

  // 6. Artifact Garbage Collection (GC) Mutation
  const [isGcDialogOpen, setIsGcDialogOpen] = useState(false);
  const gcMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.runGarbageCollection(collection.id, {
        keep_revisions: 2,
        dry_run: false,
      }),
    onSuccess: (data) => {
      toast.success(data.message);
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collection.id],
      });
      if (selectedBinding) {
        queryClient.invalidateQueries({
          queryKey: ["binding-index-revisions", selectedBinding.id],
        });
      }
      setIsGcDialogOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Dọn dẹp chỉ mục thất bại.");
    },
  });

  const handleOpenPromote = (revId: string) => {
    setTargetIndexRevId(revId);
    setPromoteReason("");
    setIsPromoteDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-border/70 bg-card shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-foreground">
              Liên Kết Tri Thức & Xuất Bản Chỉ Mục V2 (ADR-011)
            </h2>
            <Badge
              variant="outline"
              className="text-[10px] bg-primary/10 text-primary border-primary/20"
            >
              Zero Downtime
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Mô hình "Tiếp nhận một lần — Xuất bản an toàn": Quản lý tài liệu
            liên kết từ Kho Trung Tâm, dựng chỉ mục Staging độc lập và chuyển
            con trỏ nguyên tử (Atomic Pointer Swap).
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="gap-1.5 text-xs"
          >
            <RefreshCw
              className={`size-3.5 ${isRefetching ? "animate-spin" : ""}`}
            />
            Làm Mới
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsGcDialogOpen(true)}
            className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            title="Dọn dẹp các phiên bản chỉ mục cũ không hoạt động (giữ lại 2 bản gần nhất cho rollback)"
          >
            <Trash2 className="size-3.5" />
            Dọn Chỉ Mục Cũ (GC)
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsBindDialogOpen(true)}
            className="gap-1.5 text-xs"
            title="Nạp nhanh qua modal popup"
          >
            Nạp Nhanh (Modal)
          </Button>
          <Button
            size="sm"
            onClick={() =>
              navigate({
                to: "/knowledge/$collectionId/add-documents",
                params: { collectionId: collection.id },
              })
            }
            className="gap-1.5 text-xs font-medium shadow-xs"
            title="Mở giao diện toàn màn hình để tìm kiếm và chọn nhiều tài liệu từ kho trung tâm"
          >
            <Plus className="size-3.5" />+ Thêm Tài Liệu Từ Kho
          </Button>
        </div>
      </div>

      {/* Main 2-Column or Table Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Table: Bindings List (2 Cols) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
              Danh Sách Tài Liệu Đã Liên Kết ({bindings.length})
            </span>
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground rounded-xl border border-border animate-pulse">
              Đang tải danh sách liên kết...
            </div>
          ) : bindings.length > 0 ? (
            <div className="rounded-xl border border-border/70 overflow-hidden bg-card">
              <Table>
                <TableHeader className="bg-muted/30">
                  <TableRow>
                    <TableHead className="text-xs">Tài liệu</TableHead>
                    <TableHead className="text-xs">Chiến lược</TableHead>
                    <TableHead className="text-xs">Trạng thái</TableHead>
                    <TableHead className="text-xs">Active Epoch</TableHead>
                    <TableHead className="text-right text-xs">
                      Thao tác
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bindings.map((b) => {
                    const isSelected = selectedBinding?.id === b.id;
                    return (
                      <TableRow
                        key={b.id}
                        className={`transition-colors cursor-pointer ${
                          isSelected
                            ? "bg-primary/5 border-l-2 border-l-primary"
                            : ""
                        }`}
                        onClick={() => setSelectedBinding(b)}
                      >
                        <TableCell>
                          <div className="space-y-0.5">
                            <span className="font-semibold text-xs text-foreground block truncate max-w-xs">
                              {b.document_title ||
                                b.file_name ||
                                "Tài liệu chưa đặt tên"}
                            </span>
                            <span className="text-[11px] font-mono text-muted-foreground block truncate max-w-xs">
                              {b.document_code
                                ? `Số: ${b.document_code} • `
                                : ""}
                              {b.file_name}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="secondary"
                            className="text-[10px] font-mono"
                          >
                            {b.chunk_strategy}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {b.status === "active" ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] gap-1 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                            >
                              <CheckCircle2 className="size-3" />
                              Đang Liên Kết
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-[10px]">
                              {b.status}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {b.active_epoch > 0 ? (
                            <span className="text-primary font-semibold">
                              Epoch #{b.active_epoch}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">
                              Chưa kích hoạt
                            </span>
                          )}
                        </TableCell>
                        <TableCell
                          className="text-right"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs gap-1"
                              title="Mở trang quản trị chi tiết liên kết này"
                              onClick={() =>
                                navigate({
                                  to: "/knowledge/$collectionId/documents/$bindingId",
                                  params: {
                                    collectionId: collection.id,
                                    bindingId: b.id,
                                  },
                                })
                              }
                            >
                              <ExternalLink className="size-3 text-primary" />
                              Chi Tiết
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs gap-1"
                              title="Dựng chỉ mục staging mới"
                              onClick={() => buildIndexMutation.mutate(b.id)}
                              disabled={buildIndexMutation.isPending}
                            >
                              <Layers className="size-3 text-primary" />
                              Dựng Index
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs text-destructive hover:bg-destructive/10"
                              title="Hủy liên kết tài liệu"
                              onClick={() => setDetachTarget(b)}
                            >
                              <Trash2 className="size-3" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <EmptyState
              icon={Link2}
              title="Chưa có tài liệu nào được liên kết"
              description="Hãy chọn tài liệu từ Kho Trung Tâm để liên kết vào Bộ Sưu Tập này theo kiến trúc V2."
              action={{
                label: "Liên Kết Tài Liệu Từ Kho",
                onClick: () => setIsBindDialogOpen(true),
              }}
            />
          )}
        </div>

        {/* Right Column: Selected Binding's Index Revisions & Parity Report */}
        <div className="space-y-4">
          <Card className="border-border/70">
            <CardHeader className="pb-3 border-b border-border/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <History className="size-4 text-primary" />
                  Chuỗi Chỉ Mục (Index Revisions)
                </CardTitle>
                {selectedBinding && (
                  <Badge variant="secondary" className="text-[10px]">
                    {indexRevisions.length} bản
                  </Badge>
                )}
              </div>
              <CardDescription className="text-xs">
                {selectedBinding ? (
                  <span>
                    Đang xem:{" "}
                    <strong>
                      {selectedBinding.document_title ||
                        selectedBinding.file_name}
                    </strong>
                  </span>
                ) : (
                  "Nhấp vào một tài liệu ở bảng bên trái để xem lịch sử chỉ mục."
                )}
              </CardDescription>
            </CardHeader>

            <CardContent className="pt-4 space-y-3">
              {selectedBinding ? (
                isRevisionsLoading ? (
                  <div className="p-4 text-center text-xs text-muted-foreground animate-pulse">
                    Đang tải danh sách chỉ mục...
                  </div>
                ) : indexRevisions.length > 0 ? (
                  <div className="space-y-3 max-h-[550px] overflow-y-auto pr-1">
                    {indexRevisions.map((rev) => {
                      const isActive =
                        rev.id === selectedBinding.active_index_revision_id;
                      const isStaging = rev.status === "ready";
                      const parity = rev.parity_report;

                      return (
                        <div
                          key={rev.id}
                          className={`p-3 rounded-lg border text-xs space-y-2 transition-all ${
                            isActive
                              ? "border-primary bg-primary/5"
                              : isStaging
                                ? "border-amber-500/40 bg-amber-500/5"
                                : "border-border/60 bg-muted/20"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-foreground">
                                Revision #{rev.revision_no}
                              </span>
                              {isActive && (
                                <Badge
                                  variant="outline"
                                  className="text-[9px] py-0 h-4 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                                >
                                  Đang Kích Hoạt
                                </Badge>
                              )}
                              {isStaging && (
                                <Badge
                                  variant="outline"
                                  className="text-[9px] py-0 h-4 border-amber-600/30 text-amber-600 dark:text-amber-400 bg-amber-500/10"
                                >
                                  Staging Sẵn Sàng
                                </Badge>
                              )}
                              {rev.status === "building" && (
                                <Badge
                                  variant="secondary"
                                  className="text-[9px] py-0 h-4 animate-pulse"
                                >
                                  Đang Dựng...
                                </Badge>
                              )}
                              {rev.status === "failed" && (
                                <Badge
                                  variant="outline"
                                  className="text-[9px] py-0 h-4 border-destructive/30 text-destructive bg-destructive/10"
                                >
                                  Thất Bại
                                </Badge>
                              )}
                            </div>
                            <span className="text-[10px] text-muted-foreground">
                              {new Date(rev.created_at).toLocaleTimeString(
                                "vi-VN",
                                {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                },
                              )}
                            </span>
                          </div>

                          {/* Stats row */}
                          <div className="grid grid-cols-2 gap-2 text-[11px] text-muted-foreground">
                            <span>
                              Chunks:{" "}
                              <strong className="text-foreground">
                                {rev.chunk_count}
                              </strong>
                            </span>
                            <span>
                              Facts số hóa:{" "}
                              <strong className="text-foreground">
                                {rev.fact_count}
                              </strong>
                            </span>
                          </div>

                          {/* Parity Report Box */}
                          {parity && Object.keys(parity).length > 0 && (
                            <div className="p-2 rounded bg-background/80 border border-border/50 text-[11px] space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-foreground flex items-center gap-1">
                                  <ShieldCheck className="size-3 text-primary" />
                                  Parity Gate:
                                </span>
                                {parity.parity_status === "passed" ? (
                                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-0.5">
                                    <CheckCircle2 className="size-3" /> Đạt
                                    Chuẩn
                                  </span>
                                ) : (
                                  <span className="text-rose-600 dark:text-rose-400 font-semibold flex items-center gap-0.5">
                                    <AlertTriangle className="size-3" /> Lệch
                                    Chỉ Mục
                                  </span>
                                )}
                              </div>
                              <div className="text-[10px] text-muted-foreground space-y-0.5 font-mono">
                                <div>
                                  Vector: {parity.indexed_points ?? 0} /
                                  Expected:{" "}
                                  {parity.expected_chunks ?? rev.chunk_count}
                                </div>
                                <div>
                                  Xác minh: {parity.verified_points ?? 0}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Action Button: Promote (Atomic Pointer Swap) */}
                          {isStaging && (
                            <Button
                              variant="default"
                              size="sm"
                              className="w-full h-7 text-xs gap-1.5 mt-1"
                              onClick={() => handleOpenPromote(rev.id)}
                            >
                              <ArrowRightLeft className="size-3" />
                              Kích Hoạt Nguyên Tử (Promote)
                            </Button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-4 text-center text-xs text-muted-foreground rounded-lg border border-dashed border-border">
                    Chưa có index revision nào. Nhấn "Dựng Index" để xây dựng
                    chỉ mục staging đầu tiên.
                  </div>
                )
              ) : (
                <div className="p-6 text-center text-xs text-muted-foreground">
                  Chọn một tài liệu để quản lý các phiên bản chỉ mục vector và
                  kích hoạt nguyên tử.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dialog 1: Bind Documents From Central Repository */}
      <BindDocumentsDialog
        collectionId={collection.id}
        chunkingStrategy={collection.chunking_strategy}
        open={isBindDialogOpen}
        onOpenChange={setIsBindDialogOpen}
        onSuccess={() => {
          queryClient.invalidateQueries({
            queryKey: ["knowledge-bindings", collection.id],
          });
          refetch();
        }}
      />

      {/* Dialog 2: Promote Index Revision (Atomic Swap) */}
      <Dialog open={isPromoteDialogOpen} onOpenChange={setIsPromoteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ArrowRightLeft className="size-4 text-primary" />
              Kích Hoạt Nguyên Tử (Atomic Pointer Swap)
            </DialogTitle>
            <DialogDescription className="text-xs">
              Thao tác này sẽ chuyển con trỏ truy vấn
              (`active_index_revision_id`) sang phiên bản staging đã được kiểm
              định Parity Gate thành công, tăng số Epoch lên 1 mà không gián
              đoạn truy vấn AI (Zero Downtime).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <span className="font-medium text-foreground">
                Lý do phát hành / kích hoạt
              </span>
              <Input
                value={promoteReason}
                onChange={(e) => setPromoteReason(e.target.value)}
                placeholder="Ví dụ: Cập nhật văn bản mới năm học 2026-2027, tái lập chỉ mục sau hiệu đính..."
                className="text-xs"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsPromoteDialogOpen(false)}
              className="text-xs"
            >
              Hủy
            </Button>
            <Button
              onClick={() => promoteMutation.mutate()}
              disabled={promoteMutation.isPending}
              className="text-xs"
            >
              Xác Nhận Kích Hoạt
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog 3: Detach Confirm */}
      <ConfirmDialog
        open={!!detachTarget}
        onOpenChange={(open) => !open && setDetachTarget(null)}
        title="Xác nhận hủy liên kết tài liệu"
        description={`Bạn có chắc chắn muốn hủy liên kết tài liệu "${detachTarget?.document_title || detachTarget?.file_name}" khỏi Bộ Sưu Tập này? Các vector trong Qdrant sẽ bị đánh dấu thu hồi an toàn.`}
        confirmText="Hủy Liên Kết"
        confirmVariant="destructive"
        onConfirm={() => detachTarget && detachMutation.mutate(detachTarget.id)}
        isPending={detachMutation.isPending}
      />

      {/* Dialog 4: Artifact Garbage Collection (GC) Confirm */}
      <ConfirmDialog
        open={isGcDialogOpen}
        onOpenChange={setIsGcDialogOpen}
        title="Dọn dẹp chỉ mục cũ (Artifact Garbage Collection)"
        description="Hệ thống sẽ rà soát và thu hồi các phiên bản chỉ mục cũ không hoạt động (superseded, failed) và xóa các vector tương ứng trong Qdrant. Để đảm bảo an toàn cho tính năng Rollback tức thì, 2 phiên bản lịch sử gần nhất cho mỗi tài liệu sẽ luôn được bảo lưu tuyệt đối."
        confirmText="Bắt Đầu Dọn Dẹp"
        confirmVariant="destructive"
        onConfirm={() => gcMutation.mutate()}
        isPending={gcMutation.isPending}
      />
    </div>
  );
};

// =============================================================================
// Sub-Dialog: Bind Documents From Repository
// =============================================================================
interface BindDocumentsDialogProps {
  collectionId: string;
  chunkingStrategy: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

function BindDocumentsDialog({
  collectionId,
  chunkingStrategy,
  open,
  onOpenChange,
  onSuccess,
}: BindDocumentsDialogProps) {
  const [search, setSearch] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  // Fetch available documents
  const { data, isLoading } = useQuery({
    queryKey: ["available-repository-documents", collectionId, search],
    queryFn: () =>
      knowledgeApi.getAvailableDocuments(collectionId, search || undefined),
    enabled: open,
  });

  const availableDocs = data?.items || [];

  const handleToggleSelect = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const bindMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.createBindings(collectionId, {
        items: selectedDocIds.map((docId) => ({
          repository_document_id: docId,
          chunk_strategy: chunkingStrategy,
          sync_policy: "manual",
          auto_activate: false,
        })),
      }),
    onSuccess: (res) => {
      toast.success(
        `Đã liên kết thành công ${res.created_count} tài liệu (Bỏ qua: ${res.skipped_count}).`,
      );
      setSelectedDocIds([]);
      onSuccess();
      onOpenChange(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Liên kết tài liệu thất bại.");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="size-4 text-primary" />
            Liên Kết Tài Liệu Từ Kho Trung Tâm
          </DialogTitle>
          <DialogDescription className="text-xs">
            Chọn các tài liệu đã được tiếp nhận và thẩm định trong Kho Tập Trung
            để đưa vào quy trình xuất bản tri thức của Bộ Sưu Tập này.
          </DialogDescription>
        </DialogHeader>

        {/* Search Bar */}
        <div className="pt-1 pb-2">
          <div className="relative">
            <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm kiếm tài liệu theo tên, số hiệu..."
              className="text-xs pl-8"
            />
          </div>
        </div>

        {/* List of Available Documents */}
        <div className="flex-1 overflow-y-auto space-y-2 max-h-[380px] pr-1">
          {isLoading ? (
            <div className="p-6 text-center text-xs text-muted-foreground animate-pulse">
              Đang tải danh sách tài liệu khả dụng...
            </div>
          ) : availableDocs.length > 0 ? (
            availableDocs.map((doc) => {
              const isChecked = selectedDocIds.includes(doc.id);
              return (
                <button
                  type="button"
                  key={doc.id}
                  disabled={doc.is_bound}
                  onClick={() => !doc.is_bound && handleToggleSelect(doc.id)}
                  className={`w-full text-left p-3 rounded-lg border text-xs flex items-center justify-between gap-3 transition-colors ${
                    doc.is_bound
                      ? "opacity-50 bg-muted/40 border-border/40 cursor-not-allowed"
                      : isChecked
                        ? "bg-primary/5 border-primary cursor-pointer"
                        : "hover:bg-muted/30 border-border/70 cursor-pointer"
                  }`}
                >
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground truncate max-w-md">
                        {doc.title || doc.file_name}
                      </span>
                      {doc.is_bound ? (
                        <Badge variant="secondary" className="text-[9px]">
                          Đã Liên Kết
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="text-[9px] border-emerald-600/30 text-emerald-600 bg-emerald-500/10"
                        >
                          Sẵn Sàng
                        </Badge>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {doc.document_code ? `Số: ${doc.document_code} • ` : ""}
                      {doc.file_name} (.{doc.file_type}) • {doc.revision_count}{" "}
                      phiên bản
                    </p>
                  </div>

                  {!doc.is_bound && (
                    <div className="shrink-0">
                      <div
                        className={`size-4 rounded border flex items-center justify-center transition-colors ${
                          isChecked
                            ? "bg-primary border-primary text-primary-foreground"
                            : "border-input"
                        }`}
                      >
                        {isChecked && <CheckCircle2 className="size-3.5" />}
                      </div>
                    </div>
                  )}
                </button>
              );
            })
          ) : (
            <div className="p-6 text-center text-xs text-muted-foreground rounded-lg border border-dashed border-border">
              Không có tài liệu nào khả dụng để liên kết.
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="flex-col sm:flex-row items-center justify-between gap-2 pt-2 border-t border-border/50">
          <span className="text-xs text-muted-foreground">
            Đã chọn:{" "}
            <strong className="text-foreground">{selectedDocIds.length}</strong>{" "}
            tài liệu
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs"
            >
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={() => bindMutation.mutate()}
              disabled={selectedDocIds.length === 0 || bindMutation.isPending}
              className="text-xs"
            >
              Liên Kết ({selectedDocIds.length})
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
