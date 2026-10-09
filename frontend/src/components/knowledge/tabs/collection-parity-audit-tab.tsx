import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Database,
  FolderSync,
  History,
  Info,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  Sliders,
  Sparkles,
  Trash2,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
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
import { Progress } from "@/components/ui/progress";
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
  BackfillReport,
  GarbageCollectionReport,
  KnowledgeCollection,
  LegacyAuditItem,
  ShadowRetrievalReport,
} from "@/types/knowledge";

interface CollectionParityAuditTabProps {
  collection: KnowledgeCollection;
  onNavigateToBinding?: (bindingId: string) => void;
}

export function CollectionParityAuditTab({
  collection,
  onNavigateToBinding,
}: CollectionParityAuditTabProps) {
  const queryClient = useQueryClient();

  // State
  const [subTab, setSubTab] = useState<"audit" | "shadow" | "canary">("audit");
  const [auditFilter, setAuditFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isBackfillDialogOpen, setIsBackfillDialogOpen] =
    useState<boolean>(false);
  const [backfillForceRebuild, setBackfillForceRebuild] =
    useState<boolean>(false);
  const [backfillStrategy, setBackfillStrategy] =
    useState<string>("ClauseBasedChunker");
  const [backfillResult, setBackfillResult] = useState<BackfillReport | null>(
    null,
  );

  // Canary Policy State
  const [selectedReadMode, setSelectedReadMode] = useState<
    "system" | "revisioned" | "shadow" | "legacy"
  >("system");
  const [retentionRevisions, setRetentionRevisions] = useState<number>(2);

  // GC State
  const [isGcDialogOpen, setIsGcDialogOpen] = useState<boolean>(false);
  const [gcDryRun, setGcDryRun] = useState<boolean>(true);
  const [gcKeepRevisions, setGcKeepRevisions] = useState<number>(2);
  const [gcResult, setGcResult] = useState<GarbageCollectionReport | null>(
    null,
  );

  // Shadow Test State
  const [shadowQuery, setShadowQuery] = useState<string>(
    "Quy định xét tuyển đại học chính quy",
  );
  const [shadowTopK, setShadowTopK] = useState<number>(5);
  const [shadowReport, setShadowReport] =
    useState<ShadowRetrievalReport | null>(null);

  // 1. Query Audit Report
  const {
    data: auditReport,
    isLoading: isLoadingAudit,
    isFetching: isFetchingAudit,
    refetch: refetchAudit,
  } = useQuery({
    queryKey: ["canary-audit", collection.id],
    queryFn: () => knowledgeApi.auditCollectionCanary(collection.id),
    staleTime: 60 * 1000,
  });

  // 2. Mutation Backfill
  const backfillMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.backfillCollectionCanary(collection.id, {
        force_rebuild: backfillForceRebuild,
        default_chunk_strategy: backfillStrategy,
      }),
    onSuccess: (data) => {
      toast.success(
        `Đã hoàn tất di trú ${data.documents_processed} tài liệu (${data.bindings_created} bindings mới).`,
      );
      setBackfillResult(data);
      queryClient.invalidateQueries({
        queryKey: ["canary-audit", collection.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-bindings", collection.id],
      });
    },
    onError: (err: Error) => {
      toast.error(`Di trú thất bại: ${err.message}`);
    },
  });

  // 3. Mutation Shadow Retrieval Test
  const shadowMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.runShadowRetrievalTest(collection.id, {
        query: shadowQuery.trim(),
        top_k: shadowTopK,
      }),
    onSuccess: (data) => {
      setShadowReport(data);
      if (data.leak_detected || data.retrieval_revision_leak_total > 0) {
        toast.error("Phát hiện rò rỉ revision trong kết quả truy xuất!");
      } else {
        toast.success(
          `Shadow Test hoàn tất trong ${data.latency_v2_ms.toFixed(1)}ms. Zero Revision Leak!`,
        );
      }
    },
    onError: (err: Error) => {
      toast.error(`Kiểm thử thất bại: ${err.message}`);
    },
  });

  // 4. Query Canary Policy & Retention Window
  const { data: canaryPolicy, isLoading: isLoadingPolicy } = useQuery({
    queryKey: ["canary-policy", collection.id],
    queryFn: () => knowledgeApi.getCanaryPolicy(collection.id),
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (canaryPolicy) {
      setSelectedReadMode(canaryPolicy.read_mode);
      setRetentionRevisions(canaryPolicy.retention_revisions);
      setGcKeepRevisions(canaryPolicy.retention_revisions);
    }
  }, [canaryPolicy]);

  // 5. Mutation Update Canary Policy
  const updatePolicyMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.updateCanaryPolicy(collection.id, {
        read_mode: selectedReadMode,
        retention_revisions: retentionRevisions,
      }),
    onSuccess: (data) => {
      toast.success(
        `Đã lưu chính sách: Phục vụ '${data.effective_read_mode}', lưu trữ ${data.retention_revisions} bản superseded.`,
      );
      queryClient.invalidateQueries({
        queryKey: ["canary-policy", collection.id],
      });
    },
    onError: (err: Error) => {
      toast.error(`Cập nhật chính sách thất bại: ${err.message}`);
    },
  });

  // 6. Mutation Artifact Garbage Collection
  const gcMutation = useMutation({
    mutationFn: (dryRun: boolean) =>
      knowledgeApi.runGarbageCollection(collection.id, {
        keep_revisions: gcKeepRevisions,
        dry_run: dryRun,
      }),
    onSuccess: (report) => {
      setGcResult(report);
      if (report.dry_run) {
        toast.info(
          `Mô phỏng GC: Sẽ dọn dẹp ${report.pruned_revisions_count} revisions cũ, giải phóng ${report.pruned_chunks_count} chunks.`,
        );
      } else {
        toast.success(
          `Đã dọn dẹp ${report.pruned_revisions_count} revisions cũ (${report.pruned_points_count} points Qdrant, ${report.pruned_chunks_count} chunks DB).`,
        );
        queryClient.invalidateQueries({
          queryKey: ["canary-policy", collection.id],
        });
        queryClient.invalidateQueries({
          queryKey: ["canary-audit", collection.id],
        });
      }
    },
    onError: (err: Error) => {
      toast.error(`Thực thi dọn dẹp thất bại: ${err.message}`);
    },
  });

  // Lọc tài liệu trong bảng audit
  const filteredItems = (auditReport?.items || []).filter(
    (item: LegacyAuditItem) => {
      const matchFilter =
        auditFilter === "all" || item.classification === auditFilter;
      const matchSearch =
        !searchQuery.trim() ||
        item.document_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.document_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        Boolean(
          item.binding_id?.toLowerCase().includes(searchQuery.toLowerCase()),
        );
      return matchFilter && matchSearch;
    },
  );

  const parityPct = auditReport ? auditReport.parity_ratio * 100 : 0;

  return (
    <div className="space-y-6">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl border border-border bg-card/60 backdrop-blur-xs">
        <div>
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <ShieldCheck className="size-4 text-primary" />
            Kiểm Định Parity Gate & Shadow Retrieval V2 (ADR-011)
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Đối soát tính toàn vẹn 100% giữa PostgreSQL Chunks và Qdrant Vector
            Points; kiểm định Zero Revision Leak.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchAudit()}
            disabled={isFetchingAudit}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw
              className={`size-3.5 ${isFetchingAudit ? "animate-spin text-primary" : ""}`}
            />
            {isFetchingAudit ? "Đang quét..." : "Kiểm Kê Lại"}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setBackfillResult(null);
              setIsBackfillDialogOpen(true);
            }}
            className="h-8 text-xs gap-1.5"
          >
            <FolderSync className="size-3.5" />
            Di Trú Backfill
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setSubTab("shadow")}
            className="h-8 text-xs gap-1.5"
          >
            <Zap className="size-3.5" />
            Chạy Shadow Test
          </Button>

          <Button
            variant={subTab === "canary" ? "default" : "outline"}
            size="sm"
            onClick={() => setSubTab("canary")}
            className="h-8 text-xs gap-1.5"
          >
            <Sliders className="size-3.5" />
            Chính Sách Canary & GC
          </Button>
        </div>
      </div>

      {/* 2. Bento Grid 4 KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* KPI 1: Parity Ratio */}
        <Card className="border-border shadow-2xs">
          <CardHeader className="pb-2 pt-3.5 px-4 flex flex-row items-center justify-between space-y-0">
            <span className="text-xs font-medium text-muted-foreground">
              Tỷ Lệ Parity Toàn Kho
            </span>
            <div
              className={`size-7 rounded-md flex items-center justify-center ${
                parityPct === 100
                  ? "bg-primary/10 text-primary"
                  : "bg-amber-500/10 text-amber-600"
              }`}
            >
              <ShieldCheck className="size-4" />
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-3.5">
            <div className="text-xl font-bold tracking-tight text-foreground">
              {isLoadingAudit ? "..." : `${parityPct.toFixed(1)}%`}
            </div>
            <div className="mt-2 space-y-1">
              <Progress value={parityPct} className="h-1.5 bg-muted" />
              <span className="text-[11px] text-muted-foreground block">
                {parityPct === 100
                  ? "Khớp tuyệt đối 100% DB vs Qdrant"
                  : "Có tài liệu bị lệch điểm vector"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 2: Active Parity OK */}
        <Card className="border-border shadow-2xs">
          <CardHeader className="pb-2 pt-3.5 px-4 flex flex-row items-center justify-between space-y-0">
            <span className="text-xs font-medium text-muted-foreground">
              Khớp Tuyệt Đối (OK)
            </span>
            <div className="size-7 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="size-4" />
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-3.5">
            <div className="text-xl font-bold tracking-tight text-foreground">
              {isLoadingAudit
                ? "..."
                : auditReport?.active_parity_ok_count || 0}
              <span className="text-xs font-normal text-muted-foreground ml-1">
                / {auditReport?.total_documents || 0} tài liệu
              </span>
            </div>
            <span className="text-[11px] text-muted-foreground block mt-1">
              Sẵn sàng phục vụ AI không có rủi ro
            </span>
          </CardContent>
        </Card>

        {/* KPI 3: Needs Rebuild */}
        <Card className="border-border shadow-2xs">
          <CardHeader className="pb-2 pt-3.5 px-4 flex flex-row items-center justify-between space-y-0">
            <span className="text-xs font-medium text-muted-foreground">
              Cần Tái Dựng (Mismatch)
            </span>
            <div
              className={`size-7 rounded-md flex items-center justify-center ${
                (auditReport?.needs_rebuild_count || 0) > 0
                  ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              <AlertTriangle className="size-4" />
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-3.5">
            <div className="text-xl font-bold tracking-tight text-foreground">
              {isLoadingAudit ? "..." : auditReport?.needs_rebuild_count || 0}
            </div>
            <span className="text-[11px] text-muted-foreground block mt-1">
              Số chunks DB lệch với vector Qdrant
            </span>
          </CardContent>
        </Card>

        {/* KPI 4: Pending Intake */}
        <Card className="border-border shadow-2xs">
          <CardHeader className="pb-2 pt-3.5 px-4 flex flex-row items-center justify-between space-y-0">
            <span className="text-xs font-medium text-muted-foreground">
              Chờ Intake / Rỗng
            </span>
            <div className="size-7 rounded-md bg-muted text-muted-foreground flex items-center justify-center">
              <Clock className="size-4" />
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-3.5">
            <div className="text-xl font-bold tracking-tight text-foreground">
              {isLoadingAudit ? "..." : auditReport?.pending_intake_count || 0}
            </div>
            <span className="text-[11px] text-muted-foreground block mt-1">
              Chưa liên kết Kho Tập Trung hoặc 0 chunks
            </span>
          </CardContent>
        </Card>
      </div>

      {/* 3. Sub Tabs Navigation */}
      <Tabs
        value={subTab}
        onValueChange={(val) => setSubTab(val as "audit" | "shadow" | "canary")}
        className="w-full space-y-4"
      >
        <div className="flex items-center justify-between border-b border-border pb-2">
          <TabsList className="h-8 p-1 bg-muted/60">
            <TabsTrigger
              value="audit"
              className="text-xs h-6 px-3 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary"
            >
              <Database className="size-3.5" />
              <span>Kiểm Kê Danh Mục Parity</span>
            </TabsTrigger>

            <TabsTrigger
              value="shadow"
              className="text-xs h-6 px-3 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary"
            >
              <Zap className="size-3.5" />
              <span>Trình Thử Nghiệm Shadow Test</span>
            </TabsTrigger>

            <TabsTrigger
              value="canary"
              className="text-xs h-6 px-3 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary"
            >
              <Sliders className="size-3.5" />
              <span>Chính Sách Canary & Lưu Trữ</span>
            </TabsTrigger>
          </TabsList>

          <span className="text-xs text-muted-foreground hidden sm:inline">
            Cập nhật lúc:{" "}
            {auditReport?.audited_at
              ? new Date(auditReport.audited_at).toLocaleTimeString("vi-VN")
              : "--:--"}
          </span>
        </div>

        {/* ================================================================= */}
        {/* SUB-TAB 1: KIỂM KÊ PARITY DANH MỤC TÀI LIỆU */}
        {/* ================================================================= */}
        <TabsContent
          value="audit"
          className="mt-0 space-y-4 focus-visible:ring-0"
        >
          {/* Controls */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
              <Input
                placeholder="Tìm tiêu đề, mã doc, binding..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 text-xs"
              />
            </div>

            <div className="flex items-center gap-2">
              <Select value={auditFilter} onValueChange={setAuditFilter}>
                <SelectTrigger className="h-8 text-xs w-[170px]">
                  <SelectValue placeholder="Lọc trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    Tất cả ({auditReport?.items.length || 0})
                  </SelectItem>
                  <SelectItem value="active-parity-ok">
                    Khớp chuẩn ({auditReport?.active_parity_ok_count || 0})
                  </SelectItem>
                  <SelectItem value="needs-rebuild">
                    Lệch vector ({auditReport?.needs_rebuild_count || 0})
                  </SelectItem>
                  <SelectItem value="pending-intake">
                    Chờ intake ({auditReport?.pending_intake_count || 0})
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-lg border border-border bg-card overflow-hidden">
            <Table>
              <TableHeader className="bg-muted/40">
                <TableRow className="h-9 hover:bg-transparent">
                  <TableHead className="text-xs font-semibold">
                    Tài Liệu
                  </TableHead>
                  <TableHead className="text-xs font-semibold w-24 text-right">
                    DB Chunks
                  </TableHead>
                  <TableHead className="text-xs font-semibold w-24 text-right">
                    Qdrant Points
                  </TableHead>
                  <TableHead className="text-xs font-semibold w-36 text-center">
                    Phân Loại Parity
                  </TableHead>
                  <TableHead className="text-xs font-semibold">
                    Chi Tiết / Lý Do
                  </TableHead>
                  <TableHead className="text-xs font-semibold w-24 text-right">
                    Thao Tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoadingAudit ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="h-32 text-center text-xs text-muted-foreground"
                    >
                      <RefreshCw className="size-4 animate-spin mx-auto mb-2 text-primary" />
                      Đang kiểm kê số liệu Parity Gate...
                    </TableCell>
                  </TableRow>
                ) : filteredItems.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="h-32 text-center text-xs text-muted-foreground"
                    >
                      Không có tài liệu nào phù hợp với bộ lọc.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredItems.map((item) => (
                    <TableRow key={item.document_id} className="h-11">
                      <TableCell className="text-xs py-2">
                        <div className="font-medium text-foreground truncate max-w-[280px]">
                          {item.document_title}
                        </div>
                        <div className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-mono">
                          <span>{item.document_id}</span>
                          {item.binding_id && (
                            <>
                              <span>•</span>
                              <span className="text-primary">
                                {item.binding_id}
                              </span>
                            </>
                          )}
                        </div>
                      </TableCell>

                      <TableCell className="text-xs font-mono text-right py-2">
                        {item.db_chunks_count}
                      </TableCell>

                      <TableCell className="text-xs font-mono text-right py-2">
                        <span
                          className={
                            item.db_chunks_count !== item.qdrant_points_count
                              ? "text-amber-600 dark:text-amber-400 font-semibold"
                              : "text-foreground"
                          }
                        >
                          {item.qdrant_points_count}
                        </span>
                      </TableCell>

                      <TableCell className="text-xs text-center py-2">
                        {item.classification === "active-parity-ok" && (
                          <Badge
                            variant="outline"
                            className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 text-[11px] font-normal"
                          >
                            Parity OK 100%
                          </Badge>
                        )}
                        {item.classification === "needs-rebuild" && (
                          <Badge
                            variant="outline"
                            className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20 text-[11px] font-normal"
                          >
                            Needs Rebuild
                          </Badge>
                        )}
                        {item.classification === "pending-intake" && (
                          <Badge
                            variant="outline"
                            className="bg-muted text-muted-foreground border-border text-[11px] font-normal"
                          >
                            Pending Intake
                          </Badge>
                        )}
                      </TableCell>

                      <TableCell className="text-xs text-muted-foreground py-2 truncate max-w-[220px]">
                        {item.discrepancy_reason ||
                          "Khớp tuyệt đối dữ liệu serving"}
                      </TableCell>

                      <TableCell className="text-xs text-right py-2">
                        {item.binding_id ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs gap-1 text-primary hover:text-primary"
                            onClick={() =>
                              item.binding_id &&
                              onNavigateToBinding?.(item.binding_id)
                            }
                          >
                            <span>Chi tiết</span>
                            <ArrowUpRight className="size-3" />
                          </Button>
                        ) : (
                          <span className="text-[11px] text-muted-foreground">
                            --
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* ================================================================= */}
        {/* SUB-TAB 2: TRÌNH THỬ NGHIỆM SHADOW RETRIEVAL TESTER */}
        {/* ================================================================= */}
        <TabsContent
          value="shadow"
          className="mt-0 space-y-5 focus-visible:ring-0"
        >
          {/* Query Input Card */}
          <Card className="border-border shadow-2xs">
            <CardHeader className="pb-3 pt-4 px-4">
              <CardTitle className="text-xs font-semibold text-foreground flex items-center gap-2">
                <Sparkles className="size-3.5 text-primary" />
                Kiểm Thử Song Song V1 Legacy vs V2 Snapshot Isolation
              </CardTitle>
              <CardDescription className="text-xs">
                Chạy truy vấn đồng thời qua cả hai động cơ để kiểm tra độ trễ
                (latency delta) và bảo đảm tuyệt đối không có rò rỉ phiên bản.
              </CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-3">
              <div className="flex flex-col sm:flex-row gap-2">
                <Input
                  placeholder="Nhập câu hỏi thử nghiệm (VD: Quy chế tuyển sinh, học phí...)"
                  value={shadowQuery}
                  onChange={(e) => setShadowQuery(e.target.value)}
                  className="h-9 text-xs flex-1"
                />

                <Select
                  value={String(shadowTopK)}
                  onValueChange={(val) => setShadowTopK(Number(val))}
                >
                  <SelectTrigger className="h-9 text-xs w-[110px]">
                    <SelectValue placeholder="Top K" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="3">Top 3 chunks</SelectItem>
                    <SelectItem value="5">Top 5 chunks</SelectItem>
                    <SelectItem value="10">Top 10 chunks</SelectItem>
                  </SelectContent>
                </Select>

                <Button
                  variant="default"
                  size="sm"
                  onClick={() => shadowMutation.mutate()}
                  disabled={shadowMutation.isPending || !shadowQuery.trim()}
                  className="h-9 text-xs gap-1.5 px-4 font-medium"
                >
                  {shadowMutation.isPending ? (
                    <RefreshCw className="size-3.5 animate-spin" />
                  ) : (
                    <Play className="size-3.5" />
                  )}
                  Chạy Shadow Test
                </Button>
              </div>

              {/* Sample Queries Chips */}
              <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground pt-1">
                <span className="text-[11px] font-medium">Gợi ý mẫu:</span>
                {[
                  "Quy định xét tuyển thẳng và ưu tiên xét tuyển",
                  "Mức học phí theo tín chỉ năm học 2025-2026",
                  "Điều kiện tốt nghiệp và xét chứng chỉ ngoại ngữ",
                ].map((sample) => (
                  <button
                    type="button"
                    key={sample}
                    className="text-[11px] px-2 py-0.5 rounded-md bg-muted/60 hover:bg-muted text-foreground transition-colors cursor-pointer border border-border"
                    onClick={() => setShadowQuery(sample)}
                  >
                    {sample}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Shadow Test Results */}
          {shadowReport && (
            <div className="space-y-4">
              {/* Security Banner: Zero Leak Assertion */}
              <div
                className={`p-4 rounded-xl border flex items-start gap-3 ${
                  !shadowReport.leak_detected &&
                  shadowReport.retrieval_revision_leak_total === 0
                    ? "bg-primary/10 border-primary/20 text-primary"
                    : "bg-destructive/10 border-destructive/20 text-destructive"
                }`}
              >
                {!shadowReport.leak_detected &&
                shadowReport.retrieval_revision_leak_total === 0 ? (
                  <ShieldCheck className="size-5 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="size-5 shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="text-sm font-semibold">
                    {!shadowReport.leak_detected &&
                    shadowReport.retrieval_revision_leak_total === 0
                      ? "XÁC NHẬN AN TOÀN TUYỆT ĐỐI — ZERO REVISION LEAK"
                      : "CẢNH BÁO: PHÁT HIỆN RÒ RỈ PHIÊN BẢN TRUY XUẤT!"}
                  </div>
                  <div className="text-xs mt-1 text-foreground/80 leading-relaxed">
                    {!shadowReport.leak_detected &&
                    shadowReport.retrieval_revision_leak_total === 0
                      ? "Bộ lọc Snapshot Isolation đã chặn đứng 100% các đoạn staging/superseded, toàn bộ tài liệu trả về đều thuộc phiên bản đang phục vụ chính thức."
                      : `Phát hiện ${shadowReport.retrieval_revision_leak_total} đoạn rò rỉ phiên bản. Cần rà soát lại cấu hình Snapshot Isolation.`}
                  </div>
                </div>
              </div>

              {/* Performance Metrics Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Card className="border-border">
                  <CardHeader className="pb-1 pt-3 px-3">
                    <span className="text-[11px] text-muted-foreground">
                      Thời Gian Đáp Ứng V1 vs V2
                    </span>
                  </CardHeader>
                  <CardContent className="px-3 pb-3">
                    <div className="text-lg font-bold text-foreground">
                      {shadowReport.latency_v2_ms.toFixed(1)} ms
                      <span className="text-xs font-normal text-muted-foreground ml-1.5">
                        (V1: {shadowReport.latency_v1_ms.toFixed(1)} ms)
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      Chênh lệch:{" "}
                      <span
                        className={
                          shadowReport.latency_delta_pct <= 0
                            ? "text-emerald-600 dark:text-emerald-400 font-medium"
                            : "text-amber-600 dark:text-amber-400 font-medium"
                        }
                      >
                        {shadowReport.latency_delta_pct > 0 ? "+" : ""}
                        {shadowReport.latency_delta_pct.toFixed(1)}%
                      </span>
                    </span>
                  </CardContent>
                </Card>

                <Card className="border-border">
                  <CardHeader className="pb-1 pt-3 px-3">
                    <span className="text-[11px] text-muted-foreground">
                      Độ Tương Đồng Kết Quả (Jaccard)
                    </span>
                  </CardHeader>
                  <CardContent className="px-3 pb-3">
                    <div className="text-lg font-bold text-foreground">
                      {(shadowReport.jaccard_similarity * 100).toFixed(1)}%
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      Trùng khớp: {shadowReport.overlap_count} chunks
                    </span>
                  </CardContent>
                </Card>

                <Card className="border-border">
                  <CardHeader className="pb-1 pt-3 px-3">
                    <span className="text-[11px] text-muted-foreground">
                      Số Lượng Trả Về (Top K)
                    </span>
                  </CardHeader>
                  <CardContent className="px-3 pb-3">
                    <div className="text-lg font-bold text-foreground">
                      {shadowReport.v2_result_count} chunks
                      <span className="text-xs font-normal text-muted-foreground ml-1.5">
                        (V1: {shadowReport.v1_result_count})
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      {shadowReport.leak_detected
                        ? "Có lỗi rò rỉ"
                        : "Chỉ mục nhất quán"}
                    </span>
                  </CardContent>
                </Card>
              </div>

              {/* Two Column Chunk Comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* V1 Legacy Results */}
                <div className="rounded-lg border border-border bg-card p-3 space-y-2">
                  <div className="text-xs font-semibold text-muted-foreground flex items-center justify-between pb-1 border-b border-border">
                    <span>V1 Legacy Engine</span>
                    <Badge
                      variant="outline"
                      className="text-[10px] font-normal"
                    >
                      {shadowReport.v1_result_count} items
                    </Badge>
                  </div>
                  <div className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
                    {shadowReport.v1_chunk_ids.length === 0 ? (
                      <span className="text-xs text-muted-foreground block py-2 text-center">
                        Không tìm thấy chunks nào
                      </span>
                    ) : (
                      shadowReport.v1_chunk_ids.map((id, idx) => (
                        <div
                          key={`v1-${id}`}
                          className="p-2 rounded bg-muted/40 text-xs font-mono text-muted-foreground flex items-center justify-between"
                        >
                          <span className="truncate max-w-[200px]">
                            #{idx + 1}: {id}
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            Legacy
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* V2 Snapshot Isolation Results */}
                <div className="rounded-lg border border-border bg-card p-3 space-y-2">
                  <div className="text-xs font-semibold text-primary flex items-center justify-between pb-1 border-b border-border">
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck className="size-3.5" />
                      V2 Snapshot Isolation
                    </span>
                    <Badge
                      variant="default"
                      className="text-[10px] font-normal"
                    >
                      {shadowReport.v2_result_count} items
                    </Badge>
                  </div>
                  <div className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
                    {shadowReport.v2_chunk_ids.length === 0 ? (
                      <span className="text-xs text-muted-foreground block py-2 text-center">
                        Không tìm thấy chunks nào
                      </span>
                    ) : (
                      shadowReport.v2_chunk_ids.map((id, idx) => (
                        <div
                          key={`v2-${id}`}
                          className="p-2 rounded bg-primary/5 border border-primary/10 text-xs font-mono text-foreground flex items-center justify-between"
                        >
                          <span className="truncate max-w-[200px]">
                            #{idx + 1}: {id}
                          </span>
                          <span className="text-[10px] text-primary font-medium">
                            Snapshot Pin
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </TabsContent>

        {/* ================================================================= */}
        {/* SUB-TAB 3: CHÍNH SÁCH CANARY PHỤC VỤ RAG & LƯU TRỮ CHỈ MỤC */}
        {/* ================================================================= */}
        <TabsContent
          value="canary"
          className="mt-0 space-y-6 focus-visible:ring-0"
        >
          {/* Bento Grid 2 Cột */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Cột 1: Cấu hình Phục Vụ RAG & Canary Rollout */}
            <Card className="border-border shadow-2xs">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                      <Sliders className="size-4" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold text-foreground">
                        Chế Độ Phục Vụ RAG (Canary Serving Mode)
                      </CardTitle>
                      <CardDescription className="text-xs text-muted-foreground mt-0.5">
                        Kiểm soát thuật toán và phạm vi dữ liệu phục vụ Trợ lý
                        AI
                      </CardDescription>
                    </div>
                  </div>
                  {canaryPolicy && (
                    <Badge
                      variant="outline"
                      className={`text-[11px] font-medium ${
                        canaryPolicy.effective_read_mode === "revisioned"
                          ? "bg-primary/10 text-primary border-primary/20"
                          : canaryPolicy.effective_read_mode === "shadow"
                            ? "bg-purple-500/10 text-purple-600 border-purple-500/20"
                            : "bg-amber-500/10 text-amber-600 border-amber-500/20"
                      }`}
                    >
                      Đang chạy:{" "}
                      {canaryPolicy.effective_read_mode.toUpperCase()}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-1">
                <div className="space-y-2">
                  <label
                    htmlFor="read-mode-select"
                    className="text-xs font-medium text-foreground block"
                  >
                    Chính sách đọc (Read Serving Mode):
                  </label>
                  <Select
                    value={selectedReadMode}
                    onValueChange={(val) =>
                      setSelectedReadMode(
                        val as "system" | "revisioned" | "shadow" | "legacy",
                      )
                    }
                  >
                    <SelectTrigger
                      id="read-mode-select"
                      className="h-9 text-xs"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="system">
                        system — Mặc định toàn hệ thống (
                        {canaryPolicy?.system_read_mode || "revisioned"})
                      </SelectItem>
                      <SelectItem value="revisioned">
                        revisioned — Strict Cutover V2 (Chỉ đọc từ active index
                        revisions)
                      </SelectItem>
                      <SelectItem value="shadow">
                        shadow — Shadow Testing (Phục vụ song song, kiểm chứng
                        ngầm)
                      </SelectItem>
                      <SelectItem value="legacy">
                        legacy — Tương thích ngược V1 (Bao gồm chunks unindexed
                        cũ)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="p-3 rounded-lg border border-border bg-muted/30 text-xs space-y-1.5">
                  <div className="font-medium text-foreground flex items-center gap-1.5">
                    <Info className="size-3.5 text-primary" />Ý nghĩa chế độ
                    phục vụ:
                  </div>
                  <p className="text-muted-foreground text-[11px] leading-relaxed">
                    {selectedReadMode === "system" &&
                      `Kho tri thức sẽ tự động kế thừa cấu hình chung của nền tảng (hiện là ${canaryPolicy?.system_read_mode || "revisioned"}). Thích hợp cho môi trường vận hành ổn định.`}
                    {selectedReadMode === "revisioned" &&
                      "Cách ly tuyệt đối 100%. Các tài liệu đang soạn thảo (Staging) hoặc đã bị thay thế (Superseded) sẽ không bao giờ xuất hiện trong câu trả lời của Trợ lý AI."}
                    {selectedReadMode === "shadow" &&
                      "Cho phép thử nghiệm so sánh chất lượng giữa dữ liệu cũ và dữ liệu mới mà không làm gián đoạn câu trả lời của Trợ lý AI."}
                    {selectedReadMode === "legacy" &&
                      "Chế độ dự phòng khẩn cấp: Cho phép truy xuất toàn bộ chunks cũ chưa qua chuẩn hóa binding V2."}
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-border">
                  <div className="flex items-center justify-between">
                    <div>
                      <label
                        htmlFor="retention-input"
                        className="text-xs font-medium text-foreground block"
                      >
                        Số bản superseded lưu lại cho Rollback:
                      </label>
                      <span className="text-[11px] text-muted-foreground">
                        Lưu trữ tối thiểu N phiên bản cũ để phục hồi tức thì
                        trong O(1)
                      </span>
                    </div>
                    <div className="w-20">
                      <Input
                        id="retention-input"
                        type="number"
                        min={1}
                        max={10}
                        value={retentionRevisions}
                        onChange={(e) =>
                          setRetentionRevisions(
                            Math.max(
                              1,
                              Math.min(
                                10,
                                Number.parseInt(e.target.value, 10) || 2,
                              ),
                            ),
                          )
                        }
                        className="h-8 text-xs text-center"
                      />
                    </div>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <Button
                    size="sm"
                    onClick={() => updatePolicyMutation.mutate()}
                    disabled={updatePolicyMutation.isPending || isLoadingPolicy}
                    className="h-8 text-xs gap-1.5"
                  >
                    {updatePolicyMutation.isPending ? (
                      <RefreshCw className="size-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="size-3.5" />
                    )}
                    Lưu Thiết Lập Chính Sách
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Cột 2: Thu Dọn Chỉ Mục Cũ (Artifact Garbage Collection) */}
            <Card className="border-border shadow-2xs flex flex-col justify-between">
              <div>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <div className="size-8 rounded-lg bg-destructive/10 text-destructive flex items-center justify-center">
                      <Trash2 className="size-4" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold text-foreground">
                        Dọn Dẹp Chỉ Mục Cũ (Artifact Garbage Collection)
                      </CardTitle>
                      <CardDescription className="text-xs text-muted-foreground mt-0.5">
                        Thu dọn các index revision đã cũ quá hạn, giải phóng
                        Qdrant & DB
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-1">
                  <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5 text-xs text-amber-800 dark:text-amber-300 space-y-1">
                    <div className="font-semibold flex items-center gap-1.5">
                      <ShieldCheck className="size-4 text-amber-600" />
                      Cơ Chế Bảo Vệ Rollback Tuyệt Đối (Rollback Protection)
                    </div>
                    <p className="text-[11px] leading-relaxed text-muted-foreground">
                      Hệ thống tự động bảo vệ phiên bản đang Active và đúng{" "}
                      {retentionRevisions} phiên bản Superseded gần nhất. Chỉ
                      các bản cũ hơn mới bị thu hồi chunks và điểm vector
                      Qdrant.
                    </p>
                  </div>

                  {/* Lịch sử dọn dẹp gần nhất */}
                  <div className="rounded-lg border border-border p-3 space-y-2 bg-card/60">
                    <div className="text-xs font-medium text-foreground flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <History className="size-3.5 text-muted-foreground" />
                        Báo cáo dọn dẹp gần nhất
                      </span>
                      {canaryPolicy?.last_gc_report ? (
                        <Badge variant="outline" className="text-[10px]">
                          {canaryPolicy.last_gc_report.dry_run
                            ? "Mô phỏng"
                            : "Thực thi"}
                        </Badge>
                      ) : (
                        <span className="text-[11px] text-muted-foreground">
                          Chưa chạy
                        </span>
                      )}
                    </div>

                    {canaryPolicy?.last_gc_report ? (
                      <div className="text-xs space-y-1 text-muted-foreground pt-1 border-t border-border/60">
                        <div className="text-foreground font-medium text-[11px]">
                          {canaryPolicy.last_gc_report.message}
                        </div>
                        <div className="grid grid-cols-3 gap-2 pt-1 text-[11px]">
                          <div className="bg-muted/40 p-1.5 rounded text-center">
                            <span className="text-muted-foreground block text-[10px]">
                              Revisions Pruned
                            </span>
                            <span className="font-semibold text-foreground">
                              {
                                canaryPolicy.last_gc_report
                                  .pruned_revisions_count
                              }
                            </span>
                          </div>
                          <div className="bg-muted/40 p-1.5 rounded text-center">
                            <span className="text-muted-foreground block text-[10px]">
                              Chunks Xóa
                            </span>
                            <span className="font-semibold text-foreground">
                              {canaryPolicy.last_gc_report.pruned_chunks_count}
                            </span>
                          </div>
                          <div className="bg-muted/40 p-1.5 rounded text-center">
                            <span className="text-muted-foreground block text-[10px]">
                              Vector Points
                            </span>
                            <span className="font-semibold text-foreground">
                              {canaryPolicy.last_gc_report.pruned_points_count}
                            </span>
                          </div>
                        </div>
                        <div className="text-[10px] text-muted-foreground pt-1 flex justify-between">
                          <span>
                            Thời điểm:{" "}
                            {new Date(
                              canaryPolicy.last_gc_report.executed_at,
                            ).toLocaleString("vi-VN")}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="text-[11px] text-muted-foreground py-2 text-center">
                        Kho tri thức này chưa từng chạy Artifact Garbage
                        Collection.
                      </div>
                    )}
                  </div>
                </CardContent>
              </div>

              <div className="p-4 pt-0 flex items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setGcDryRun(true);
                    setGcResult(null);
                    setIsGcDialogOpen(true);
                  }}
                  className="h-8 text-xs gap-1.5"
                >
                  <Play className="size-3.5" />
                  Mô Phỏng Dry-Run
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    setGcDryRun(false);
                    setGcResult(null);
                    setIsGcDialogOpen(true);
                  }}
                  className="h-8 text-xs gap-1.5"
                >
                  <Trash2 className="size-3.5" />
                  Dọn Dẹp Chỉ Mục Cũ
                </Button>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* ================================================================= */}
      {/* DIALOG BACKFILL MIGRATION */}
      {/* ================================================================= */}
      <Dialog
        open={isBackfillDialogOpen}
        onOpenChange={setIsBackfillDialogOpen}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold text-foreground flex items-center gap-2">
              <FolderSync className="size-4 text-primary" />
              Di Trú Dữ Liệu An Toàn (Backfill to V2)
            </DialogTitle>
            <DialogDescription className="text-xs">
              Chuyển đổi toàn bộ tài liệu legacy sang kiến trúc bất biến
              Document Revision v1 và Knowledge Binding độc lập.
            </DialogDescription>
          </DialogHeader>

          {!backfillResult ? (
            <div className="flex flex-col gap-3 py-2">
              <div className="p-3 rounded-lg bg-primary/10 text-primary text-xs flex items-start gap-2">
                <Info className="size-4 shrink-0 mt-0.5" />
                <div>
                  <strong>Idempotent & Safe:</strong> Quá trình di trú hoàn toàn
                  không xóa dữ liệu đang phục vụ. Nếu tài liệu đã có binding, hệ
                  thống sẽ bỏ qua an toàn.
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-medium text-foreground">
                  Chiến lược phân đoạn mặc định (Chunking Strategy):
                </span>
                <Select
                  value={backfillStrategy}
                  onValueChange={setBackfillStrategy}
                >
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ClauseBasedChunker">
                      ClauseBasedChunker (Nghị định 30 & Quy chế ĐH Quy Nhơn)
                    </SelectItem>
                    <SelectItem value="SemanticChunker">
                      SemanticChunker (Phân đoạn ngữ nghĩa)
                    </SelectItem>
                    <SelectItem value="RecursiveCharacterChunker">
                      RecursiveCharacterChunker (Ký tự đệ quy)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg border border-border">
                <div>
                  <span className="text-xs font-medium text-foreground block">
                    Buộc tái dựng (Force Rebuild)
                  </span>
                  <span className="text-[11px] text-muted-foreground block">
                    Tái lập chỉ mục ngay cả khi tài liệu đã có binding cũ
                  </span>
                </div>
                <Switch
                  checked={backfillForceRebuild}
                  onCheckedChange={setBackfillForceRebuild}
                />
              </div>
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 text-xs space-y-1.5 my-2">
              <div className="font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="size-4 text-emerald-600" />
                Di Trú Thành Công (Epoch #{backfillResult.collection_epoch})
              </div>
              <div>• Tài liệu xử lý: {backfillResult.documents_processed}</div>
              <div>• Bindings tạo mới: {backfillResult.bindings_created}</div>
              <div>
                • Index Revisions v1: {backfillResult.index_revisions_created}
              </div>
              <div>• Chunks được gắn tag: {backfillResult.chunks_tagged}</div>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsBackfillDialogOpen(false)}
            >
              {backfillResult ? "Đóng" : "Hủy"}
            </Button>
            {!backfillResult && (
              <Button
                variant="default"
                size="sm"
                onClick={() => backfillMutation.mutate()}
                disabled={backfillMutation.isPending}
                className="gap-1.5"
              >
                {backfillMutation.isPending && (
                  <RefreshCw className="size-3.5 animate-spin" />
                )}
                Bắt Đầu Di Trú
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ================================================================= */}
      {/* DIALOG ARTIFACT GARBAGE COLLECTION */}
      {/* ================================================================= */}
      <Dialog open={isGcDialogOpen} onOpenChange={setIsGcDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold text-foreground flex items-center gap-2">
              <Trash2 className="size-4 text-destructive" />
              {gcDryRun
                ? "Mô Phỏng Dọn Dẹp Chỉ Mục"
                : "Thực Thi Dọn Dẹp Chỉ Mục Cũ"}
            </DialogTitle>
            <DialogDescription className="text-xs">
              {gcDryRun
                ? "Tính toán và rà soát số lượng revision, chunks và vector points có thể giải phóng mà không làm thay đổi dữ liệu."
                : "Thu dọn các index revision đã lỗi thời và giải phóng dung lượng bộ nhớ. Active revisions luôn được bảo vệ."}
            </DialogDescription>
          </DialogHeader>

          {!gcResult ? (
            <div className="flex flex-col gap-3 py-2">
              <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
                <ShieldCheck className="size-4 shrink-0 mt-0.5 text-amber-600" />
                <div>
                  <strong>Bảo vệ Rollback:</strong> Hệ thống luôn giữ lại bản
                  Active và {gcKeepRevisions} bản Superseded gần nhất. Các bản
                  này sẽ không bao giờ bị xóa.
                </div>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg border border-border">
                <div>
                  <span className="text-xs font-medium text-foreground block">
                    Chế độ mô phỏng (Dry-run)
                  </span>
                  <span className="text-[11px] text-muted-foreground block">
                    Chỉ tính toán và báo cáo, không xóa dữ liệu thật
                  </span>
                </div>
                <Switch checked={gcDryRun} onCheckedChange={setGcDryRun} />
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg border border-border">
                <div>
                  <label
                    htmlFor="gc-keep-revs"
                    className="text-xs font-medium text-foreground block"
                  >
                    Số bản Superseded bảo lưu
                  </label>
                  <span className="text-[11px] text-muted-foreground block">
                    Giữ lại để đảm bảo Rollback tức thì O(1)
                  </span>
                </div>
                <div className="w-20">
                  <Input
                    id="gc-keep-revs"
                    type="number"
                    min={1}
                    max={10}
                    value={gcKeepRevisions}
                    onChange={(e) =>
                      setGcKeepRevisions(
                        Math.max(
                          1,
                          Math.min(
                            10,
                            Number.parseInt(e.target.value, 10) || 2,
                          ),
                        ),
                      )
                    }
                    className="h-8 text-xs text-center"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div
              className={`p-3 rounded-lg text-xs space-y-2 my-2 ${
                gcResult.dry_run
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-500/20"
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="size-4" />
                {gcResult.message}
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 text-[11px]">
                <div className="bg-background/80 p-2 rounded">
                  <span className="text-muted-foreground block text-[10px]">
                    Revisions Đã Prune
                  </span>
                  <span className="font-bold text-foreground text-sm">
                    {gcResult.pruned_revisions_count}
                  </span>
                </div>
                <div className="bg-background/80 p-2 rounded">
                  <span className="text-muted-foreground block text-[10px]">
                    Bindings Quét
                  </span>
                  <span className="font-bold text-foreground text-sm">
                    {gcResult.total_bindings_scanned}
                  </span>
                </div>
                <div className="bg-background/80 p-2 rounded">
                  <span className="text-muted-foreground block text-[10px]">
                    Chunks Giải Phóng
                  </span>
                  <span className="font-bold text-foreground text-sm">
                    {gcResult.pruned_chunks_count}
                  </span>
                </div>
                <div className="bg-background/80 p-2 rounded">
                  <span className="text-muted-foreground block text-[10px]">
                    Vector Points Qdrant
                  </span>
                  <span className="font-bold text-foreground text-sm">
                    {gcResult.pruned_points_count}
                  </span>
                </div>
              </div>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsGcDialogOpen(false)}
            >
              {gcResult ? "Đóng" : "Hủy"}
            </Button>
            {!gcResult && (
              <Button
                variant={gcDryRun ? "default" : "destructive"}
                size="sm"
                onClick={() => gcMutation.mutate(gcDryRun)}
                disabled={gcMutation.isPending}
                className="gap-1.5"
              >
                {gcMutation.isPending && (
                  <RefreshCw className="size-3.5 animate-spin" />
                )}
                {gcDryRun ? "Bắt Đầu Mô Phỏng" : "Xác Nhận Dọn Dẹp"}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
