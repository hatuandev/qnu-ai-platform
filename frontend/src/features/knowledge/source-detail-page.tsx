import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  FileText,
  History,
  Layers,
  Pencil,
  RefreshCw,
  Save,
  Scan,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { DocumentStudioWorkspace } from "@/components/knowledge/ocr/document-studio-workspace";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type {
  KnowledgeChunkSetResponse,
  KnowledgeSourceDetailResponse,
} from "@/types/knowledge";
import { DeleteSourceButton } from "./components/delete-source-button";
import { SourceContextEditor } from "./components/source-context-editor";

interface SourceDetailPageProps {
  collectionId: string;
  sourceId: string;
  isStudioMode: boolean;
  onStudioModeChange: (isOpen: boolean) => void;
}

export const SourceDetailPage: React.FC<SourceDetailPageProps> = ({
  collectionId,
  sourceId,
  isStudioMode,
  onStudioModeChange,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedRevisionId, setSelectedRevisionId] = useState(
    () => new URLSearchParams(window.location.search).get("revision") || "",
  );

  const [activeTab, setActiveTab] = useState<
    "content" | "quality" | "chunks" | "revisions"
  >("content");

  // Editing state
  const [isEditingMarkdown, setIsEditingMarkdown] = useState(false);
  const [editedMarkdown, setEditedMarkdown] = useState("");

  // Review modal state
  const [isReviewDialogOpen, setIsReviewDialogOpen] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<"approved" | "rejected">(
    "approved",
  );
  const [reviewComment, setReviewComment] = useState("");

  // 1. Fetch Collection Info
  const { data: collection } = useQuery({
    queryKey: ["knowledge-collection", collectionId],
    queryFn: () => knowledgeApi.getCollection(collectionId),
  });

  // 2. Fetch Source Detail (V3)
  const {
    data: source,
    isLoading: isSourceLoading,
    isError: isSourceError,
    error: sourceError,
    refetch: refetchSource,
  } = useQuery<KnowledgeSourceDetailResponse>({
    queryKey: ["knowledge-source", collectionId, sourceId],
    queryFn: () => knowledgeApi.getKnowledgeSource(collectionId, sourceId),
    enabled: !!sourceId,
    refetchInterval: (query) =>
      query.state.data?.revisions?.some((r) =>
        ["queued", "extracting", "normalizing", "validating"].includes(
          r.status,
        ),
      )
        ? 1500
        : false,
  });

  // Active Revision
  const activeRev =
    source?.revisions.find((r) => r.id === selectedRevisionId) ||
    source?.revisions?.[0] ||
    source?.active_source_revision;

  // Sync markdown content when revision loads
  useEffect(() => {
    if (activeRev?.canonical_markdown) {
      setEditedMarkdown(activeRev.canonical_markdown);
    }
  }, [activeRev?.canonical_markdown]);

  // 3. Fetch Chunk Sets (V3)
  const {
    data: chunkSets = [],
    isLoading: isChunkSetsLoading,
    refetch: refetchChunkSets,
  } = useQuery<KnowledgeChunkSetResponse[]>({
    queryKey: ["knowledge-source-chunk-sets", collectionId, sourceId],
    queryFn: () => knowledgeApi.listSourceChunkSets(collectionId, sourceId),
    enabled: !!sourceId,
  });

  // 4. Mutation Update Markdown
  const updateContentMutation = useMutation({
    mutationFn: () => {
      if (!activeRev?.id) throw new Error("Chưa có bản sửa đổi để cập nhật.");
      return knowledgeApi.updateSourceRevisionContent(
        collectionId,
        sourceId,
        activeRev.id,
        editedMarkdown,
      );
    },
    onSuccess: (revision) => {
      toast.success("Đã lưu hiệu đính nội dung Markdown chuẩn thành công.");
      setSelectedRevisionId(revision.id);
      setIsEditingMarkdown(false);
      refetchSource();
      refetchChunkSets();
      queryClient.invalidateQueries({
        queryKey: ["knowledge-source", collectionId, sourceId],
      });
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Cập nhật nội dung thất bại."));
    },
  });

  // 5. Mutation Review Revision
  const reviewMutation = useMutation({
    mutationFn: () => {
      if (!activeRev?.id) throw new Error("Chưa có bản sửa đổi để duyệt.");
      return knowledgeApi.reviewSourceRevision(
        collectionId,
        sourceId,
        activeRev.id,
        reviewDecision,
        reviewComment.trim() || undefined,
      );
    },
    onSuccess: () => {
      toast.success(
        reviewDecision === "approved"
          ? "Đã phê duyệt bản sửa đổi thành công."
          : "Đã từ chối bản sửa đổi.",
      );
      setIsReviewDialogOpen(false);
      setReviewComment("");
      refetchSource();
      queryClient.invalidateQueries({
        queryKey: ["knowledge-source", collectionId, sourceId],
      });
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Phê duyệt thất bại."));
    },
  });

  // Studio & Reparse States
  const [isReparseDialogOpen, setIsReparseDialogOpen] = useState(false);
  const [reparseProfile, setReparseProfile] = useState<
    "vision_ocr" | "standard" | "layout_analysis"
  >("vision_ocr");
  const [reparseEngine, setReparseEngine] = useState<string>("auto");

  // 6. Mutation Reparse Source (chống chạy trùng qua Backend)
  const reparseMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.reparseSource(collectionId, sourceId, {
        parser_profile: reparseProfile,
        ocr_engine: reparseEngine === "auto" ? undefined : reparseEngine,
      }),
    onSuccess: (revision) => {
      toast.success("Đã xếp hàng bóc tách lại. Trạng thái sẽ tự cập nhật.");
      setSelectedRevisionId(revision.id);
      setIsReparseDialogOpen(false);
      refetchSource();
      refetchChunkSets();
      queryClient.invalidateQueries({
        queryKey: ["knowledge-source", collectionId, sourceId],
      });
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Bóc tách lại thất bại."));
    },
  });

  if (isSourceLoading) {
    return (
      <div className="py-24 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-2">
        <RefreshCw className="size-5 animate-spin text-primary" />
        <span>Đang tải thông tin nguồn tri thức...</span>
      </div>
    );
  }

  if (isSourceError || !source) {
    return (
      <div className="max-w-4xl mx-auto py-12">
        <EmptyState
          icon={AlertCircle}
          title="Không tìm thấy nguồn tri thức"
          description={extractErrorMessage(
            sourceError,
            "Nguồn tri thức không tồn tại hoặc đã bị gỡ bỏ.",
          )}
          action={{
            label: "Quay lại Kho tri thức",
            onClick: () =>
              navigate({
                to: "/knowledge/$collectionId",
                params: { collectionId },
              }),
          }}
        />
      </div>
    );
  }

  const qualityReport = activeRev?.quality_report || {};
  const violations = qualityReport.violations || [];
  const qualityScore = qualityReport.quality_score;

  if (isStudioMode && collection) {
    return (
      <>
        {activeRev && (
          <div className="mb-3 flex justify-end">
            <SourceContextEditor
              collectionId={collectionId}
              sourceId={sourceId}
              revisionId={activeRev.id}
              onSaved={setSelectedRevisionId}
            />
          </div>
        )}
        <DocumentStudioWorkspace
          collection={collection}
          documentId={sourceId}
          revisionId={activeRev?.id}
          onBack={() => onStudioModeChange(false)}
          onApproveSuccess={(savedRevisionId) => {
            if (savedRevisionId) setSelectedRevisionId(savedRevisionId);
            refetchSource();
            refetchChunkSets();
          }}
        />
      </>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      <div className="flex flex-wrap gap-3 items-center justify-between">
        {activeRev && (
          <SourceContextEditor
            collectionId={collectionId}
            sourceId={sourceId}
            revisionId={activeRev.id}
            onSaved={setSelectedRevisionId}
          />
        )}
        <Select
          value={activeRev?.id || ""}
          onValueChange={(id) => {
            setSelectedRevisionId(id);
            const url = new URL(window.location.href);
            url.searchParams.set("revision", id);
            window.history.replaceState(window.history.state, "", url);
          }}
        >
          <SelectTrigger className="w-full sm:w-72" aria-label="Bản bóc tách">
            <SelectValue placeholder="Chọn bản bóc tách" />
          </SelectTrigger>
          <SelectContent>
            {source.revisions.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                v{r.revision_no} · {r.status}
                {r.id === source.active_source_revision?.id
                  ? " · Đang áp dụng"
                  : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DeleteSourceButton
          sourceId={sourceId}
          status={source.status}
          title={sourceId}
          onDeleted={() =>
            navigate({
              to: "/knowledge/$collectionId",
              params: { collectionId },
            })
          }
        />
      </div>
      {/* 1. Header & Navigation Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link
              to="/knowledge"
              className="hover:text-foreground transition-colors"
            >
              Kho Tri Thức
            </Link>
            <span>/</span>
            <Link
              to="/knowledge/$collectionId"
              params={{ collectionId }}
              className="hover:text-foreground transition-colors"
            >
              {collection?.name || "Kho"}
            </Link>
            <span>/</span>
            <span className="text-foreground font-medium">Chi tiết nguồn</span>
          </div>

          <div className="flex items-center gap-2.5 pt-1">
            <h1 className="text-lg sm:text-xl font-bold text-foreground">
              Chi Tiết Nguồn Tri Thức
            </h1>
            <Badge
              variant="outline"
              className={`text-[11px] ${
                source.status === "ready"
                  ? "bg-success/10 text-success border-success/30"
                  : source.status === "review_required"
                    ? "bg-warning/10 text-warning border-warning/30"
                    : source.status === "failed"
                      ? "bg-destructive/10 text-destructive border-destructive/30"
                      : "bg-primary/10 text-primary border-primary/30"
              }`}
            >
              {source.status === "ready"
                ? "Sẵn sàng (Ready)"
                : source.status === "review_required"
                  ? "Cần duyệt (Review Required)"
                  : source.status === "failed"
                    ? "Lỗi (Failed)"
                    : source.status}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Mã nguồn:{" "}
            <span className="font-mono text-foreground">{source.id}</span>
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
          <Button
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() => onStudioModeChange(true)}
          >
            <Scan className="size-3.5" />
            <span>Bóc tách & Studio OCR</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() => setIsReparseDialogOpen(true)}
          >
            <RefreshCw className="size-3.5" />
            <span>Bóc tách lại</span>
          </Button>

          {source.repository_document_id && (
            <Button
              asChild
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5"
            >
              <Link
                to="/documents/$documentId"
                params={{ documentId: source.repository_document_id }}
              >
                <ExternalLink className="size-3.5" />
                <span>Xem tệp gốc trong Kho lưu trữ</span>
              </Link>
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() =>
              navigate({
                to: "/knowledge/$collectionId",
                params: { collectionId },
              })
            }
          >
            <ArrowLeft className="size-3.5" />
            <span>Quay lại</span>
          </Button>
        </div>
      </div>

      {/* 2. Snapshot Provenance Ribbon */}
      <Card className="border border-border/70 shadow-xs bg-muted/20">
        <CardContent className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <span className="text-muted-foreground text-[11px] block">
              Tài liệu gốc (Repository Doc)
            </span>
            <span className="font-mono font-medium text-foreground block truncate">
              {source.repository_document_id}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground text-[11px] block">
              Mã băm tệp gốc (SHA-256)
            </span>
            <span
              className="font-mono text-muted-foreground text-[11px] block truncate"
              title={activeRev?.origin_file_hash}
            >
              {activeRev?.origin_file_hash
                ? `${activeRev.origin_file_hash.slice(0, 16)}...`
                : "—"}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground text-[11px] block">
              Bản sửa đổi hiện hành (Revision)
            </span>
            <span className="font-semibold text-foreground">
              v{activeRev?.revision_no ?? 1} ({activeRev?.status ?? "—"})
            </span>
          </div>
          <div>
            <span className="text-muted-foreground text-[11px] block">
              Ngày nạp (Snapshot Date)
            </span>
            <span className="text-foreground">
              {new Date(source.created_at).toLocaleDateString("vi-VN")}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* 3. Review Required Alert Action Banner */}
      {activeRev?.status === "review_required" && (
        <Card className="border border-warning/40 bg-warning/5 shadow-xs">
          <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <ShieldAlert className="size-5 text-warning shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-foreground">
                  Tài liệu cần cán bộ kiểm duyệt trước khi lập chỉ mục (Quality
                  Gate)
                </h4>
                <p className="text-[11px] text-muted-foreground">
                  {activeRev.failure_detail ||
                    "Chất lượng bóc tách tài liệu chưa đạt ngưỡng tự động hoặc phát hiện bất thường cấu trúc."}
                </p>
              </div>
            </div>

            <Button
              size="sm"
              onClick={() => setIsReviewDialogOpen(true)}
              className="h-8 text-xs gap-1.5 shrink-0 self-start sm:self-auto"
            >
              <ShieldCheck className="size-3.5" />
              <span>Phê duyệt / Từ chối</span>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 4. Tab Navigation */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as typeof activeTab)}
        className="space-y-4"
      >
        <TabsList className="bg-muted/50 p-1">
          <TabsTrigger value="content" className="text-xs gap-1.5">
            <FileText className="size-3.5" />
            <span>Markdown Chuẩn</span>
          </TabsTrigger>
          <TabsTrigger value="quality" className="text-xs gap-1.5">
            <ShieldCheck className="size-3.5" />
            <span>
              Quality Gate{" "}
              {qualityScore !== undefined ? `(${qualityScore}đ)` : ""}
            </span>
          </TabsTrigger>
          <TabsTrigger value="chunks" className="text-xs gap-1.5">
            <Layers className="size-3.5" />
            <span>Tập Đoạn Cắt Chunks ({chunkSets.length})</span>
          </TabsTrigger>
          <TabsTrigger value="revisions" className="text-xs gap-1.5">
            <History className="size-3.5" />
            <span>Lịch Sử Bản Bóc Tách ({source.revisions.length})</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Canonical Markdown Content */}
        <TabsContent value="content" className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs text-muted-foreground">
              {isEditingMarkdown
                ? "Chế độ hiệu đính Markdown: Bạn có thể chỉnh sửa cấu trúc văn bản hoặc tiêu đề trước khi lập chỉ mục."
                : "Nội dung Markdown đã được chuẩn hóa qua tầng bóc tách và làm sạch Unicode NFC."}
            </div>

            <div className="flex items-center gap-2">
              {isEditingMarkdown ? (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => {
                      setIsEditingMarkdown(false);
                      setEditedMarkdown(activeRev?.canonical_markdown || "");
                    }}
                  >
                    Hủy
                  </Button>
                  <Button
                    size="sm"
                    className="h-8 text-xs gap-1.5"
                    disabled={updateContentMutation.isPending}
                    onClick={() => updateContentMutation.mutate()}
                  >
                    {updateContentMutation.isPending ? (
                      <RefreshCw className="size-3.5 animate-spin" />
                    ) : (
                      <Save className="size-3.5" />
                    )}
                    <span>Lưu Thay Đổi</span>
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs gap-1.5"
                  onClick={() => setIsEditingMarkdown(true)}
                >
                  <Pencil className="size-3.5" />
                  <span>Hiệu đính Markdown</span>
                </Button>
              )}
            </div>
          </div>

          <Card className="border border-border">
            <CardContent className="p-4">
              {isEditingMarkdown ? (
                <Textarea
                  value={editedMarkdown}
                  onChange={(e) => setEditedMarkdown(e.target.value)}
                  rows={20}
                  className="font-mono text-xs leading-relaxed resize-y bg-background"
                />
              ) : activeRev?.canonical_markdown ? (
                <pre className="font-mono text-xs leading-relaxed text-foreground whitespace-pre-wrap max-h-[600px] overflow-y-auto p-2">
                  {activeRev.canonical_markdown}
                </pre>
              ) : (
                <div className="py-12 text-center text-xs text-muted-foreground">
                  Chưa có nội dung Markdown cho bản sửa đổi này.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Quality Gate */}
        <TabsContent value="quality" className="space-y-4">
          <Card className="border border-border">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-semibold text-foreground">
                    Báo Cáo Đánh Giá Chất Lượng (Quality Gate Report)
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Tự động kiểm tra tính toàn vẹn văn bản, độ dài, mật độ ký tự
                    rác và cấu trúc bảng.
                  </CardDescription>
                </div>
                {qualityScore !== undefined && (
                  <div className="text-right">
                    <span className="text-[11px] text-muted-foreground block">
                      Điểm chất lượng
                    </span>
                    <span
                      className={`text-lg font-bold ${
                        qualityScore >= 80
                          ? "text-success"
                          : qualityScore >= 60
                            ? "text-warning"
                            : "text-destructive"
                      }`}
                    >
                      {qualityScore} / 100
                    </span>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              {violations.length === 0 ? (
                <div className="py-8 text-center text-xs text-success flex flex-col items-center justify-center gap-2">
                  <CheckCircle2 className="size-8" />
                  <span className="font-medium">
                    Tài liệu đạt 100% tiêu chuẩn chất lượng Quality Gate.
                  </span>
                </div>
              ) : (
                <div className="space-y-2">
                  <h5 className="text-xs font-semibold text-foreground">
                    Danh sách cảnh báo & vi phạm ({violations.length})
                  </h5>
                  <div className="space-y-2">
                    {violations.map((v) => (
                      <div
                        key={`${v.rule_name}:${v.description}:${v.snippet ?? ""}`}
                        className={`p-3 rounded-md border text-xs flex items-start gap-2.5 ${
                          v.level === "error"
                            ? "border-destructive/30 bg-destructive/5 text-destructive"
                            : "border-warning/30 bg-warning/5 text-warning"
                        }`}
                      >
                        {v.level === "error" ? (
                          <XCircle className="size-4 shrink-0 mt-0.5" />
                        ) : (
                          <AlertCircle className="size-4 shrink-0 mt-0.5" />
                        )}
                        <div className="space-y-0.5">
                          <span className="font-semibold block font-mono text-[11px]">
                            {v.rule_name}
                          </span>
                          <p className="text-foreground text-[11px]">
                            {v.description}
                          </p>
                          {v.snippet && (
                            <pre className="text-[10px] bg-muted/50 p-1.5 rounded font-mono mt-1 text-muted-foreground">
                              {v.snippet}
                            </pre>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Chunk Sets */}
        <TabsContent value="chunks" className="space-y-4">
          <Card className="border border-border">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <CardTitle className="text-sm font-semibold text-foreground">
                Tập Đoạn Cắt Chunks (Parse Once, Chunk Once, Embed Many)
              </CardTitle>
              <CardDescription className="text-xs">
                Các đoạn văn bản đã được phân tách và lưu cố định, tái sử dụng
                độc lập cho nhiều mô hình vector.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {isChunkSetsLoading ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  Đang tải danh sách chunk sets...
                </div>
              ) : chunkSets.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  Nguồn này chưa được phân đoạn chunks.
                </div>
              ) : (
                <Table>
                  <TableHeader className="bg-muted/30">
                    <TableRow className="text-xs h-9">
                      <TableHead>Chiến lược</TableHead>
                      <TableHead className="w-24 text-center">
                        Số Chunks
                      </TableHead>
                      <TableHead className="w-24 text-center">
                        Số Facts
                      </TableHead>
                      <TableHead className="w-32">Mã băm cấu hình</TableHead>
                      <TableHead className="w-24 text-center">
                        Trạng thái
                      </TableHead>
                      <TableHead className="w-32 text-right">
                        Ngày tạo
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {chunkSets.map((cs) => (
                      <TableRow key={cs.id} className="text-xs h-11">
                        <TableCell className="font-semibold text-foreground">
                          {cs.chunk_strategy}
                        </TableCell>
                        <TableCell className="text-center font-bold text-primary">
                          {cs.chunk_count}
                        </TableCell>
                        <TableCell className="text-center text-muted-foreground">
                          {cs.fact_count}
                        </TableCell>
                        <TableCell className="font-mono text-[11px] text-muted-foreground">
                          {cs.config_hash.slice(0, 10)}...
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant="outline"
                            className="bg-success/10 text-success border-success/30 text-[10px]"
                          >
                            {cs.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {new Date(cs.created_at).toLocaleDateString("vi-VN")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Revisions History */}
        <TabsContent value="revisions" className="space-y-4">
          <Card className="border border-border">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <CardTitle className="text-sm font-semibold text-foreground">
                Lịch Sử Các Bản Bóc Tách Nội Dung (Revisions)
              </CardTitle>
              <CardDescription className="text-xs">
                Lịch sử bóc tách, chuẩn hóa và hiệu đính thủ công của nguồn tri
                thức.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader className="bg-muted/30">
                  <TableRow className="text-xs h-9">
                    <TableHead className="w-24 text-center">Bản số</TableHead>
                    <TableHead>Mã sửa đổi</TableHead>
                    <TableHead className="w-32 text-center">
                      Trạng thái
                    </TableHead>
                    <TableHead className="w-36">Cập nhật lần cuối</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {source.revisions.map((rev) => (
                    <TableRow key={rev.id} className="text-xs h-11">
                      <TableCell className="text-center font-bold">
                        v{rev.revision_no}
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        {rev.id}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            rev.status === "ready"
                              ? "bg-success/10 text-success border-success/30"
                              : rev.status === "review_required"
                                ? "bg-warning/10 text-warning border-warning/30"
                                : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {rev.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(rev.updated_at).toLocaleDateString("vi-VN")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Review Dialog */}
      <Dialog open={isReviewDialogOpen} onOpenChange={setIsReviewDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-foreground">
              Kiểm Duyệt Nguồn Tri Thức
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Xác nhận phê duyệt tài liệu để tiến hành lập chỉ mục hoặc từ chối
              để yêu cầu quét lại.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <div className="space-y-1.5">
              <div className="font-medium text-foreground block">
                Quyết định phê duyệt
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant={
                    reviewDecision === "approved" ? "default" : "outline"
                  }
                  onClick={() => setReviewDecision("approved")}
                  className="h-9 text-xs gap-1.5"
                >
                  <CheckCircle2 className="size-3.5" />
                  <span>Chấp thuận (Approve)</span>
                </Button>
                <Button
                  type="button"
                  variant={
                    reviewDecision === "rejected" ? "destructive" : "outline"
                  }
                  onClick={() => setReviewDecision("rejected")}
                  className="h-9 text-xs gap-1.5"
                >
                  <XCircle className="size-3.5" />
                  <span>Từ chối (Reject)</span>
                </Button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="source-review-comment"
                className="font-medium text-foreground block"
              >
                Ghi chú phê duyệt (Tùy chọn)
              </label>
              <Textarea
                id="source-review-comment"
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                placeholder="Nhập lý do phê duyệt hoặc yêu cầu chỉnh sửa..."
                rows={3}
                className="text-xs resize-none"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsReviewDialogOpen(false)}
            >
              Hủy
            </Button>
            <Button
              type="button"
              disabled={reviewMutation.isPending}
              onClick={() => reviewMutation.mutate()}
            >
              {reviewMutation.isPending
                ? "Đang xử lý..."
                : "Xác Nhận Quyết Định"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Bóc Tách Lại */}
      <Dialog open={isReparseDialogOpen} onOpenChange={setIsReparseDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">
              Bóc Tách Lại Nguồn Tri Thức
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Thực hiện bóc tách lại từ tệp snapshot nhị phân độc lập. Không phụ
              thuộc vào việc tệp gốc còn trong Kho tài liệu hay không.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <div className="space-y-1.5">
              <label
                htmlFor="reparse-profile-select"
                className="text-xs font-semibold text-foreground block"
              >
                Cấu hình bộ bóc tách (Parser Profile)
              </label>
              <Select
                value={reparseProfile}
                onValueChange={(v) =>
                  setReparseProfile(
                    v as "vision_ocr" | "standard" | "layout_analysis",
                  )
                }
              >
                <SelectTrigger
                  id="reparse-profile-select"
                  className="h-8 text-xs"
                >
                  <SelectValue placeholder="Chọn profile" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="vision_ocr">
                    Vision OCR (PaddleOCR-VL Bóc Tách Khung & Bảng)
                  </SelectItem>
                  <SelectItem value="standard">
                    Standard (Native Document Parser)
                  </SelectItem>
                  <SelectItem value="layout_analysis">
                    Layout Analysis (Phân tích bố cục tài liệu)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="reparse-engine-select"
                className="text-xs font-semibold text-foreground block"
              >
                Động cơ OCR (OCR Engine)
              </label>
              <Select value={reparseEngine} onValueChange={setReparseEngine}>
                <SelectTrigger
                  id="reparse-engine-select"
                  className="h-8 text-xs"
                >
                  <SelectValue placeholder="Chọn động cơ" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">
                    Tự động phân giải (Auto Pipeline)
                  </SelectItem>
                  <SelectItem value="paddleocr">
                    PaddleOCR-VL (Layout & Table Detection)
                  </SelectItem>
                  <SelectItem value="gemini_vision">
                    Google Gemini Vision
                  </SelectItem>
                  <SelectItem value="mistral_ocr">Mistral OCR</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsReparseDialogOpen(false)}
              disabled={reparseMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="button"
              disabled={reparseMutation.isPending}
              onClick={() => reparseMutation.mutate()}
              className="gap-1.5"
            >
              {reparseMutation.isPending ? (
                <RefreshCw className="size-3.5 animate-spin" />
              ) : (
                <RefreshCw className="size-3.5" />
              )}
              <span>Bắt Đầu Bóc Tách Lại</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
