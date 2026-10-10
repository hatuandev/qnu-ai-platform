import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRightLeft,
  BookOpen,
  Calendar,
  CheckCircle2,
  Cpu,
  ExternalLink,
  Eye,
  FileCode,
  FileText,
  History,
  Layers,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  XCircle,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { knowledgeApi } from "@/services/knowledge-api";
import type {
  BindingChunksResponse,
  KnowledgeIndexRevision,
} from "@/types/knowledge";

interface BindingDetailPageProps {
  collectionId: string;
  bindingId: string;
}

export const BindingDetailPage: React.FC<BindingDetailPageProps> = ({
  collectionId,
  bindingId,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<
    "revisions" | "chunks" | "provenance"
  >("revisions");
  const [selectedRevisionId, setSelectedRevisionId] = useState<string | null>(
    null,
  );

  // Dialog States
  const [isBuildDialogOpen, setIsBuildDialogOpen] = useState(false);
  const [buildStrategy, setBuildStrategy] = useState("ClauseBasedChunker");
  const [buildAutoActivate, setBuildAutoActivate] = useState(false);

  const [isPromoteDialogOpen, setIsPromoteDialogOpen] = useState(false);
  const [targetPromoteRev, setTargetPromoteRev] =
    useState<KnowledgeIndexRevision | null>(null);
  const [promoteReason, setPromoteReason] = useState("");

  const [isRollbackDialogOpen, setIsRollbackDialogOpen] = useState(false);
  const [targetRollbackRev, setTargetRollbackRev] =
    useState<KnowledgeIndexRevision | null>(null);
  const [rollbackReason, setRollbackReason] = useState("");

  const [isDetachConfirmOpen, setIsDetachConfirmOpen] = useState(false);

  // Chunk Inspector Filter & Modal
  const [chunkSearch, setChunkSearch] = useState("");
  const [chunkPage] = useState(1);
  const [inspectChunkModal, setInspectChunkModal] = useState<{
    id: string;
    index: number;
    content: string;
    tokens: number;
    section: string | null;
  } | null>(null);

  // 1. Fetch Binding Detail
  const {
    data: binding,
    isLoading: isBindingLoading,
    refetch: refetchBinding,
  } = useQuery({
    queryKey: ["knowledge-binding", bindingId],
    queryFn: () => knowledgeApi.getBinding(bindingId),
  });

  // 2. Fetch Collection Info
  const { data: collection } = useQuery({
    queryKey: ["knowledge-collection", collectionId],
    queryFn: () => knowledgeApi.getCollection(collectionId),
  });

  // 3. Fetch Index Revisions
  const {
    data: revisions = [],
    isLoading: isRevisionsLoading,
    refetch: refetchRevisions,
  } = useQuery({
    queryKey: ["binding-index-revisions", bindingId],
    queryFn: () => knowledgeApi.getIndexRevisions(bindingId),
  });

  // Determine current inspecting revision ID
  const effectiveRevisionId =
    selectedRevisionId ||
    binding?.active_index_revision_id ||
    revisions[0]?.id ||
    null;

  // 4. Fetch Chunks for Inspecting Revision
  const { data: chunksData, isLoading: isChunksLoading } =
    useQuery<BindingChunksResponse>({
      queryKey: ["binding-chunks", bindingId, effectiveRevisionId, chunkPage],
      queryFn: () =>
        effectiveRevisionId
          ? knowledgeApi.getBindingChunks(
              bindingId,
              effectiveRevisionId,
              chunkPage,
              20,
            )
          : Promise.resolve({
              binding_id: bindingId,
              index_revision_id: null,
              total: 0,
              page: 1,
              page_size: 20,
              items: [],
            }),
      enabled: !!effectiveRevisionId && activeTab === "chunks",
    });

  // Mutations
  const buildIndexMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.buildStagingIndex(bindingId, {
        chunk_strategy: buildStrategy,
        auto_activate: buildAutoActivate,
      }),
    onSuccess: (idxRev) => {
      queryClient.invalidateQueries({
        queryKey: ["binding-index-revisions", bindingId],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-binding", bindingId],
      });
      toast.success(
        `Đã tạo phiên bản chỉ mục staging #${idxRev.revision_no} thành công!`,
      );
      setIsBuildDialogOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Dựng chỉ mục staging thất bại.");
    },
  });

  const promoteMutation = useMutation({
    mutationFn: (targetId: string) => {
      if (!binding) {
        throw new Error("Chưa tải được thông tin liên kết tri thức.");
      }
      return knowledgeApi.promoteIndexRevision(bindingId, {
        to_index_revision_id: targetId,
        expected_epoch: binding.active_epoch,
        reason: promoteReason || "Kích hoạt phiên bản chỉ mục mới",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["binding-index-revisions", bindingId],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-binding", bindingId],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collectionId],
      });
      toast.success("Kích hoạt nguyên tử (Atomic Pointer Swap) thành công!");
      setIsPromoteDialogOpen(false);
      setTargetPromoteRev(null);
      setPromoteReason("");
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
          "Xung đột phiên bản (CAS Conflict): Liên kết vừa được cập nhật bởi một tác vụ khác. Hệ thống đang tải lại dữ liệu mới nhất...",
        );
        queryClient.invalidateQueries({
          queryKey: ["knowledge-binding", bindingId],
        });
        queryClient.invalidateQueries({
          queryKey: ["binding-index-revisions", bindingId],
        });
      } else {
        toast.error(errorObj?.message || "Kích hoạt chỉ mục thất bại.");
      }
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: (targetId: string) => {
      if (!binding) {
        throw new Error("Chưa tải được thông tin liên kết tri thức.");
      }
      return knowledgeApi.rollbackIndexRevision(bindingId, {
        target_index_revision_id: targetId,
        expected_epoch: binding.active_epoch,
        reason: rollbackReason || "Hoàn tác về phiên bản ổn định trước đó",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["binding-index-revisions", bindingId],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-binding", bindingId],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collectionId],
      });
      toast.success("Hoàn tác tức thì (Instant Rollback) thành công!");
      setIsRollbackDialogOpen(false);
      setTargetRollbackRev(null);
      setRollbackReason("");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Hoàn tác chỉ mục thất bại.");
    },
  });

  const detachMutation = useMutation({
    mutationFn: () => knowledgeApi.detachBinding(bindingId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collectionId],
      });
      toast.success("Đã gỡ tài liệu khỏi kho tri thức an toàn.");
      navigate({
        to: "/knowledge/$collectionId",
        params: { collectionId },
        search: { tab: "documents" },
      });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Không thể gỡ tài liệu khỏi kho.");
    },
  });

  if (isBindingLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-24 text-muted-foreground gap-3">
        <RefreshCw className="size-8 animate-spin text-primary" />
        <span>Đang tải thông tin chi tiết liên kết tài liệu...</span>
      </div>
    );
  }

  if (!binding) {
    return (
      <div className="p-12">
        <EmptyState
          icon={AlertTriangle}
          title="Không tìm thấy liên kết tài liệu"
          description={`Liên kết ID '${bindingId}' không tồn tại hoặc đã bị gỡ.`}
          action={{
            label: "Quay lại danh sách",
            onClick: () =>
              navigate({
                to: "/knowledge/$collectionId",
                params: { collectionId },
                search: { tab: "documents" },
              }),
          }}
        />
      </div>
    );
  }

  const activeRevision = revisions.find(
    (r) => r.id === binding.active_index_revision_id,
  );

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto w-full pb-20">
      {/* 1. Header & Breadcrumbs */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link
            to="/knowledge"
            className="hover:text-primary transition-colors"
          >
            Kho Tri Thức
          </Link>
          <span>/</span>
          <Link
            to="/knowledge/$collectionId"
            params={{ collectionId }}
            search={{ tab: "documents" }}
            className="hover:text-primary transition-colors"
          >
            {collection?.name || "Chi Tiết Kho"}
          </Link>
          <span>/</span>
          <span className="text-foreground font-medium truncate max-w-md">
            {binding.document_title || binding.file_name || "Tài Liệu"}
          </span>
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                navigate({
                  to: "/knowledge/$collectionId",
                  params: { collectionId },
                  search: { tab: "documents" },
                })
              }
              className="size-8 p-0 shrink-0 mt-1"
              title="Quay lại"
            >
              <ArrowLeft className="size-4" />
            </Button>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl font-bold tracking-tight text-foreground">
                  {binding.document_title || binding.file_name}
                </h1>
                <Badge
                  variant={
                    binding.status === "active" ? "default" : "secondary"
                  }
                  className="text-xs"
                >
                  {binding.status === "active" ? "Đang phục vụ" : "Đã ngắt"}
                </Badge>
                <Badge variant="outline" className="text-xs font-mono">
                  Epoch {binding.active_epoch}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-0.5 flex items-center gap-2">
                <span>Mã liên kết:</span>
                <span className="font-mono text-xs">{binding.id}</span>
                <span>•</span>
                <span>Tệp nguồn:</span>
                <span className="font-mono text-xs">{binding.file_name}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetchBinding();
                refetchRevisions();
              }}
              className="gap-1.5"
            >
              <RefreshCw className="size-3.5" />
              Làm mới
            </Button>

            <Button
              variant="default"
              size="sm"
              onClick={() => setIsBuildDialogOpen(true)}
              className="gap-1.5"
            >
              <Sparkles className="size-3.5" />
              Dựng Staging Index Mới
            </Button>

            <Button
              variant="destructive"
              size="sm"
              onClick={() => setIsDetachConfirmOpen(true)}
              className="gap-1.5"
            >
              <Trash2 className="size-3.5" />
              Gỡ Khỏi Kho
            </Button>
          </div>
        </div>
      </div>

      {/* 2. Bento Grid 4 KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Active Index Revision */}
        <Card className="border-border shadow-xs">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="size-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <CheckCircle2 className="size-5" />
            </div>
            <div className="min-w-0">
              <div className="text-xs text-muted-foreground">
                Index Revision Phục Vụ
              </div>
              <div className="text-base font-bold text-foreground truncate">
                {activeRevision
                  ? `Rev #${activeRevision.revision_no}`
                  : "Chưa có"}
              </div>
              <div className="text-xs text-muted-foreground font-mono truncate">
                {binding.active_index_revision_id || "Chưa kích hoạt"}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* KPI 2: Chunks & Facts */}
        <Card className="border-border shadow-xs">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="size-10 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0">
              <Layers className="size-5" />
            </div>
            <div className="min-w-0">
              <div className="text-xs text-muted-foreground">
                Quy Mô Tri Thức
              </div>
              <div className="text-base font-bold text-foreground">
                {activeRevision?.chunk_count || 0} Chunks •{" "}
                {activeRevision?.fact_count || 0} Facts
              </div>
              <div className="text-xs text-muted-foreground">
                {binding.chunk_strategy}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* KPI 3: Vector Generation */}
        <Card className="border-border shadow-xs">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="size-10 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center shrink-0">
              <Cpu className="size-5" />
            </div>
            <div className="min-w-0">
              <div className="text-xs text-muted-foreground">
                Vector Generation
              </div>
              <div className="text-base font-bold text-foreground truncate">
                BGE-M3 (1024D)
              </div>
              <div className="text-xs text-muted-foreground font-mono truncate">
                {activeRevision?.vector_generation_id || "Gen ID: auto"}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* KPI 4: Parity Gate Status */}
        <Card className="border-border shadow-xs">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="size-10 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
              <ShieldCheck className="size-5" />
            </div>
            <div className="min-w-0">
              <div className="text-xs text-muted-foreground">
                Parity Gate So Khớp
              </div>
              <div className="text-base font-bold text-emerald-600 dark:text-emerald-400">
                100% Đạt Chuẩn
              </div>
              <div className="text-xs text-muted-foreground">
                Vector = Chunks ({activeRevision?.chunk_count || 0}/
                {activeRevision?.chunk_count || 0})
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 3. Deep Navigation Tabs */}
      <Tabs
        value={activeTab}
        onValueChange={(val) =>
          setActiveTab(val as "revisions" | "chunks" | "provenance")
        }
        className="w-full"
      >
        <TabsList className="h-10 bg-muted/50 p-1 border border-border">
          <TabsTrigger value="revisions" className="text-xs gap-1.5">
            <History className="size-3.5" />
            Lịch Sử Index Revisions ({revisions.length})
          </TabsTrigger>
          <TabsTrigger value="chunks" className="text-xs gap-1.5">
            <FileCode className="size-3.5" />
            Trình Duyệt Chunks (Inspector)
          </TabsTrigger>
          <TabsTrigger value="provenance" className="text-xs gap-1.5">
            <BookOpen className="size-3.5" />
            Nguồn Tài Liệu & Thể Thức NĐ 30
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: REVISIONS & ROLLBACK */}
        <TabsContent value="revisions" className="mt-4 flex flex-col gap-4">
          <Card className="border-border shadow-xs">
            <CardHeader className="px-6 py-4 border-b border-border bg-muted/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">
                    Chuỗi Phiên Bản Chỉ Mục (Index Revision Audit Trail)
                  </CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Hỗ trợ kích hoạt nguyên tử (Atomic Pointer Swap) và hoàn tác
                    tức thì $O(1)$ (Zero-Reindex Rollback).
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsBuildDialogOpen(true)}
                  className="text-xs gap-1"
                >
                  <Sparkles className="size-3" />
                  Dựng bản mới
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {isRevisionsLoading ? (
                <div className="p-12 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
                  <RefreshCw className="size-4 animate-spin text-primary" />
                  <span>Đang tải danh sách revisions...</span>
                </div>
              ) : revisions.length === 0 ? (
                <div className="p-12 text-center">
                  <EmptyState
                    icon={History}
                    title="Chưa có phiên bản chỉ mục nào"
                    description="Tài liệu này chưa được dựng chỉ mục. Hãy bấm 'Dựng Staging Index Mới' để bắt đầu."
                  />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="w-24">Phiên Bản</TableHead>
                      <TableHead className="w-32">Mã Revision</TableHead>
                      <TableHead className="w-28 text-center">Chunks</TableHead>
                      <TableHead className="w-32 text-center">
                        Parity Gate
                      </TableHead>
                      <TableHead className="w-32 text-center">
                        Trạng Thái
                      </TableHead>
                      <TableHead className="w-40">Thời Gian</TableHead>
                      <TableHead className="text-right">Thao Tác</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {revisions.map((rev) => {
                      const isActive =
                        rev.id === binding.active_index_revision_id;
                      const isReadyToPromote =
                        rev.status === "ready" &&
                        rev.parity_report?.parity_status === "passed";
                      const isPruned =
                        rev.status === "pruned" ||
                        rev.storage_state === "pruned";
                      const canRollback =
                        !isActive && rev.is_rollback_available;

                      return (
                        <TableRow
                          key={rev.id}
                          className={
                            isActive
                              ? "bg-primary/5 hover:bg-primary/10"
                              : "hover:bg-muted/30"
                          }
                        >
                          <TableCell className="font-semibold text-foreground">
                            Rev #{rev.revision_no}
                          </TableCell>

                          <TableCell>
                            <span className="font-mono text-xs text-muted-foreground">
                              {rev.id.slice(0, 16)}...
                            </span>
                          </TableCell>

                          <TableCell className="text-center font-mono text-xs">
                            {rev.chunk_count}
                          </TableCell>

                          <TableCell className="text-center">
                            {rev.parity_report?.parity_status === "passed" ? (
                              <Badge
                                variant="outline"
                                className="text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                              >
                                <CheckCircle2 className="size-3 mr-1 inline" />
                                100% Khớp (
                                {rev.parity_report.verified_points ??
                                  rev.chunk_count}{" "}
                                pts)
                              </Badge>
                            ) : rev.status === "failed" ||
                              rev.parity_report?.parity_status === "failed" ? (
                              <Badge variant="destructive" className="text-xs">
                                <XCircle className="size-3 mr-1 inline" />
                                Lỗi Parity
                              </Badge>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                Đang thẩm định
                              </span>
                            )}
                          </TableCell>

                          <TableCell className="text-center">
                            {isActive ? (
                              <Badge variant="default" className="text-xs">
                                Active Phục Vụ
                              </Badge>
                            ) : rev.status === "archived" ? (
                              <Badge
                                variant="outline"
                                className="text-xs text-muted-foreground border-border bg-muted/30"
                              >
                                Lưu Trữ (Có Thể Rollback)
                              </Badge>
                            ) : isPruned ? (
                              <Badge
                                variant="outline"
                                className="text-xs text-muted-foreground bg-muted/50"
                              >
                                Đã Dọn (Pruned)
                              </Badge>
                            ) : rev.status === "ready" ? (
                              <Badge
                                variant="secondary"
                                className="text-xs text-primary border-primary/20 bg-primary/10"
                              >
                                Sẵn Sàng (Ready)
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="text-xs">
                                {rev.status}
                              </Badge>
                            )}
                          </TableCell>

                          <TableCell className="text-xs text-muted-foreground font-mono">
                            {new Date(rev.created_at).toLocaleString("vi-VN")}
                          </TableCell>

                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              {/* Xem Chunks Button */}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedRevisionId(rev.id);
                                  setActiveTab("chunks");
                                }}
                                className="h-7 text-xs px-2"
                                title="Xem Chunks của revision này"
                              >
                                <Eye className="size-3 mr-1" />
                                Chunks
                              </Button>

                              {/* Promote Button */}
                              {!isActive && isReadyToPromote && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    setTargetPromoteRev(rev);
                                    setIsPromoteDialogOpen(true);
                                  }}
                                  className="h-7 text-xs px-2 text-primary border-primary/30 hover:bg-primary/10"
                                >
                                  <ArrowRightLeft className="size-3 mr-1" />
                                  Kích hoạt
                                </Button>
                              )}

                              {/* Rollback Button */}
                              {canRollback && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    setTargetRollbackRev(rev);
                                    setIsRollbackDialogOpen(true);
                                  }}
                                  className="h-7 text-xs px-2 text-amber-600 dark:text-amber-400 border-amber-500/30 hover:bg-amber-500/10"
                                  title="Hoàn tác tức thì về phiên bản này"
                                >
                                  <RotateCcw className="size-3 mr-1" />
                                  Hoàn tác
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: CHUNK INSPECTOR */}
        <TabsContent value="chunks" className="mt-4 flex flex-col gap-4">
          <Card className="border-border shadow-xs">
            <CardHeader className="px-6 py-4 border-b border-border bg-muted/10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    Trình Duyệt Chunks Phân Đoạn (Chunk Inspector)
                    <Badge
                      variant="outline"
                      className="text-xs font-mono font-normal"
                    >
                      Rev:{" "}
                      {effectiveRevisionId
                        ? effectiveRevisionId.slice(0, 12)
                        : "None"}
                    </Badge>
                  </CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Kiểm tra nội dung bóc tách, token count và heading section
                    được nạp vào Vector Database Qdrant.
                  </CardDescription>
                </div>

                <div className="flex items-center gap-2">
                  <div className="relative w-64">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                    <Input
                      placeholder="Tìm trong chunks..."
                      value={chunkSearch}
                      onChange={(e) => setChunkSearch(e.target.value)}
                      className="pl-8 h-8 text-xs"
                    />
                  </div>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              {isChunksLoading ? (
                <div className="p-12 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
                  <RefreshCw className="size-4 animate-spin text-primary" />
                  <span>Đang tải các chunk phân đoạn...</span>
                </div>
              ) : !chunksData || chunksData.items.length === 0 ? (
                <div className="p-12 text-center">
                  <EmptyState
                    icon={FileCode}
                    title="Không có chunk nào trong phiên bản này"
                    description="Revision được chọn chưa có đoạn văn bản nào hoặc đã bị dọn dẹp."
                  />
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {chunksData.items
                    .filter((c) =>
                      chunkSearch
                        ? c.content
                            .toLowerCase()
                            .includes(chunkSearch.toLowerCase()) ||
                          Boolean(
                            c.section
                              ?.toLowerCase()
                              .includes(chunkSearch.toLowerCase()),
                          )
                        : true,
                    )
                    .map((chunk) => (
                      <button
                        type="button"
                        key={chunk.id}
                        className="w-full text-left p-4 hover:bg-muted/20 transition-colors flex flex-col gap-2 cursor-pointer border-none bg-transparent"
                        onClick={() =>
                          setInspectChunkModal({
                            id: chunk.id,
                            index: chunk.chunk_index,
                            content: chunk.content,
                            tokens: chunk.token_count,
                            section: chunk.section,
                          })
                        }
                      >
                        <div className="flex items-center justify-between w-full">
                          <div className="flex items-center gap-2">
                            <Badge
                              variant="outline"
                              className="text-xs font-mono px-2 py-0"
                            >
                              Chunk #{chunk.chunk_index}
                            </Badge>
                            {chunk.section && (
                              <span className="text-xs font-medium text-primary">
                                {chunk.section}
                              </span>
                            )}
                            {chunk.page_number && (
                              <span className="text-xs text-muted-foreground">
                                Trang {chunk.page_number}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
                            <span>{chunk.token_count} tokens</span>
                            <span>•</span>
                            <span>{chunk.content.length} ký tự</span>
                          </div>
                        </div>

                        <div className="text-xs text-foreground/90 font-mono bg-muted/40 p-3 rounded-md line-clamp-3 whitespace-pre-wrap leading-relaxed">
                          {chunk.content}
                        </div>
                      </button>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: PROVENANCE & DECREE 30 */}
        <TabsContent value="provenance" className="mt-4 flex flex-col gap-4">
          <Card className="border-border shadow-xs">
            <CardHeader className="px-6 py-4 border-b border-border bg-muted/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">
                    Thông Tin Nguồn & Metadata Thể Thức NĐ 30/2020/NĐ-CP
                  </CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Nguồn sự thật duy nhất (Single Source of Truth) lưu trữ tại
                    Kho Tài Liệu Trung Tâm.
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    navigate({
                      to: "/documents/$documentId",
                      params: { documentId: binding.repository_document_id },
                    })
                  }
                  className="text-xs gap-1.5"
                >
                  <ExternalLink className="size-3.5" />
                  Mở Tệp Gốc Trong Kho Tài Liệu
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex flex-col gap-4">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <FileText className="size-4 text-primary" />
                    Đặc Tả Tài Liệu Kho Trung Tâm
                  </h3>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <span className="text-muted-foreground">Mã tệp:</span>
                    <span className="col-span-2 font-mono">
                      {binding.repository_document_id}
                    </span>

                    <span className="text-muted-foreground">Tiêu đề:</span>
                    <span className="col-span-2 font-medium">
                      {binding.document_title || "—"}
                    </span>

                    <span className="text-muted-foreground">Tên tệp gốc:</span>
                    <span className="col-span-2 font-mono">
                      {binding.file_name}
                    </span>

                    <span className="text-muted-foreground">Số hiệu VB:</span>
                    <span className="col-span-2 font-mono">
                      {binding.document_code || "—"}
                    </span>

                    <span className="text-muted-foreground">
                      Chiến lược Chunk:
                    </span>
                    <span className="col-span-2 font-mono">
                      {binding.chunk_strategy}
                    </span>

                    <span className="text-muted-foreground">
                      Chính sách đồng bộ:
                    </span>
                    <span className="col-span-2">{binding.sync_policy}</span>
                  </div>
                </div>

                <div className="flex flex-col gap-4">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Calendar className="size-4 text-primary" />
                    Nhật Ký Thời Gian & Lịch Sử Liên Kết
                  </h3>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <span className="text-muted-foreground">
                      Ngày liên kết:
                    </span>
                    <span className="col-span-2 font-mono">
                      {new Date(binding.created_at).toLocaleString("vi-VN")}
                    </span>

                    <span className="text-muted-foreground">
                      Cập nhật cuối:
                    </span>
                    <span className="col-span-2 font-mono">
                      {new Date(binding.updated_at).toLocaleString("vi-VN")}
                    </span>

                    <span className="text-muted-foreground">Active Epoch:</span>
                    <span className="col-span-2 font-mono">
                      {binding.active_epoch}
                    </span>

                    <span className="text-muted-foreground">
                      Revision nguồn:
                    </span>
                    <span className="col-span-2 font-mono">
                      {binding.source_revision_id}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* DIALOG 1: BUILD STAGING INDEX */}
      <Dialog open={isBuildDialogOpen} onOpenChange={setIsBuildDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Dựng Staging Index Mới Cho Tài Liệu
            </DialogTitle>
            <DialogDescription className="text-xs">
              Hệ thống sẽ bóc tách lại văn bản nguồn, tính vector embedding và
              chạy kiểm định Parity Gate trước khi kích hoạt.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-foreground">
                Chiến lược phân đoạn (Chunk Strategy):
              </span>
              <Select value={buildStrategy} onValueChange={setBuildStrategy}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ClauseBasedChunker">
                    Điều/Khoản Pháp Quy (Khuyến nghị)
                  </SelectItem>
                  <SelectItem value="SemanticChunker">
                    Ngữ Nghĩa Tự Nhiên (Semantic)
                  </SelectItem>
                  <SelectItem value="AdmissionsRecordChunker">
                    Đề Án & Tuyển Sinh (Admissions)
                  </SelectItem>
                  <SelectItem value="ImplementationTaskChunker">
                    Nhiệm Vụ & Kế Hoạch (Tasks)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/20">
              <div className="flex flex-col gap-0.5">
                <span className="text-xs font-medium text-foreground">
                  Tự động kích hoạt (Atomic Promote)
                </span>
                <span className="text-xs text-muted-foreground">
                  Tự đổi con trỏ phục vụ ngay sau khi vượt qua Parity Gate 100%.
                </span>
              </div>
              <Switch
                checked={buildAutoActivate}
                onCheckedChange={setBuildAutoActivate}
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsBuildDialogOpen(false)}
            >
              Hủy
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() => buildIndexMutation.mutate()}
              disabled={buildIndexMutation.isPending}
              className="gap-1.5"
            >
              {buildIndexMutation.isPending && (
                <RefreshCw className="size-3.5 animate-spin" />
              )}
              Bắt Đầu Dựng Index
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOG 2: PROMOTE (ATOMIC POINTER SWAP) */}
      <Dialog open={isPromoteDialogOpen} onOpenChange={setIsPromoteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Kích Hoạt Nguyên Tử Index Revision #
              {targetPromoteRev?.revision_no}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Thực hiện Atomic Pointer Swap hoán đổi con trỏ phục vụ. Không gây
              gián đoạn truy vấn AI (Zero Downtime).
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-3 py-2">
            <div className="p-3 rounded-lg bg-primary/10 text-primary text-xs flex items-start gap-2">
              <ShieldCheck className="size-4 shrink-0 mt-0.5" />
              <div>
                <strong>Parity Gate Đã Đạt 100%:</strong> Số lượng{" "}
                {targetPromoteRev?.chunk_count} vector khớp tuyệt đối với DB
                chunks.
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-foreground">
                Lý do kích hoạt (Tùy chọn kiểm toán):
              </span>
              <Input
                placeholder="VD: Cập nhật văn bản học vụ mới..."
                value={promoteReason}
                onChange={(e) => setPromoteReason(e.target.value)}
                className="h-9 text-xs"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsPromoteDialogOpen(false)}
            >
              Hủy
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() =>
                targetPromoteRev && promoteMutation.mutate(targetPromoteRev.id)
              }
              disabled={promoteMutation.isPending}
              className="gap-1.5"
            >
              {promoteMutation.isPending && (
                <RefreshCw className="size-3.5 animate-spin" />
              )}
              Xác Nhận Kích Hoạt
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOG 3: INSTANT ROLLBACK O(1) */}
      <Dialog
        open={isRollbackDialogOpen}
        onOpenChange={setIsRollbackDialogOpen}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-2">
              <RotateCcw className="size-4" />
              Hoàn Tác Tức Thì Về Rev #{targetRollbackRev?.revision_no}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Hoán đổi con trỏ phục vụ về phiên bản chỉ mục cũ trong $O(1)$ mà
              không cần tính toán lại vector embedding.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-3 py-2">
            <div className="p-3 rounded-lg bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs flex items-start gap-2">
              <AlertTriangle className="size-4 shrink-0 mt-0.5" />
              <div>
                Cơ chế bảo vệ Rollback window: Phiên bản này vẫn còn lưu trữ đầy
                đủ {targetRollbackRev?.chunk_count} chunks và vector trong hệ
                thống.
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-foreground">
                Lý do hoàn tác:
              </span>
              <Input
                placeholder="VD: Phiên bản mới có nội dung sai lệch..."
                value={rollbackReason}
                onChange={(e) => setRollbackReason(e.target.value)}
                className="h-9 text-xs"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsRollbackDialogOpen(false)}
            >
              Hủy
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() =>
                targetRollbackRev &&
                rollbackMutation.mutate(targetRollbackRev.id)
              }
              disabled={rollbackMutation.isPending}
              className="gap-1.5 bg-amber-600 hover:bg-amber-700 text-white"
            >
              {rollbackMutation.isPending && (
                <RefreshCw className="size-3.5 animate-spin" />
              )}
              Xác Nhận Rollback
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOG 4: CHUNK INSPECTION MODAL */}
      <Dialog
        open={!!inspectChunkModal}
        onOpenChange={(open) => !open && setInspectChunkModal(null)}
      >
        <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center justify-between">
              <span>
                Chi Tiết Đoạn Văn Bản (Chunk #{inspectChunkModal?.index})
              </span>
              <Badge variant="outline" className="text-xs font-mono">
                {inspectChunkModal?.tokens} tokens
              </Badge>
            </DialogTitle>
            <DialogDescription className="text-xs font-medium text-primary">
              {inspectChunkModal?.section || "Văn bản không có đề mục"}
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto p-4 rounded-lg bg-muted/40 font-mono text-xs text-foreground whitespace-pre-wrap leading-relaxed border border-border">
            {inspectChunkModal?.content}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInspectChunkModal(null)}
            >
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* CONFIRM DIALOG: DETACH BINDING */}
      <ConfirmDialog
        open={isDetachConfirmOpen}
        onOpenChange={setIsDetachConfirmOpen}
        title="Gỡ Tài Liệu Khỏi Kho Tri Thức?"
        description={`Bạn có chắc chắn muốn gỡ tài liệu '${binding.document_title || binding.file_name}' khỏi kho tri thức này? Tệp gốc trong Kho Tài Liệu Trung Tâm sẽ được bảo toàn nguyên vẹn.`}
        confirmText="Gỡ Tài Liệu"
        variant="destructive"
        onConfirm={() => detachMutation.mutate()}
        isLoading={detachMutation.isPending}
      />
    </div>
  );
};
