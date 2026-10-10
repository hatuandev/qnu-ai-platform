import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Clock,
  Download,
  Edit3,
  ExternalLink,
  Eye,
  FileCode,
  FileText,
  History,
  Pencil,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { documentsApi } from "@/services/documents-api";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getOcrEngine(
  provenance: Record<string, unknown> | null | undefined,
): string {
  const engine = provenance?.ocr_engine;
  return typeof engine === "string" && engine.trim() ? engine : "—";
}

export function DocumentDetailPage() {
  const { documentId } = useParams({ from: "/documents/$documentId" });
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState("revisions");
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  // Fetch document details
  const {
    data: document,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["repository-document", documentId],
    queryFn: () => documentsApi.getDocument(documentId),
  });

  // Revisions query
  const { data: revisions = [], isLoading: isRevisionsLoading } = useQuery({
    queryKey: ["document-revisions", documentId],
    queryFn: () => documentsApi.getRevisions(documentId),
  });

  // Selected revision state
  const [selectedRevisionId, setSelectedRevisionId] = useState<string | null>(
    null,
  );
  const effectiveRevisionId =
    selectedRevisionId ||
    document?.current_revision_id ||
    (revisions.length > 0 ? revisions[0].id : null);

  // Selected revision detail query
  const { data: selectedRevision } = useQuery({
    queryKey: ["document-revision", documentId, effectiveRevisionId],
    queryFn: () => {
      if (!effectiveRevisionId) throw new Error("Chưa chọn bản sửa đổi");
      return documentsApi.getRevision(documentId, effectiveRevisionId);
    },
    enabled: !!effectiveRevisionId,
  });

  // Revision Dialog States
  const [isEditMarkdownOpen, setIsEditMarkdownOpen] = useState(false);
  const [editMarkdownContent, setEditMarkdownContent] = useState("");
  const [editReason, setEditReason] = useState("");

  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<"approve" | "reject">(
    "approve",
  );
  const [reviewNotes, setReviewNotes] = useState("");

  const [isRetryOpen, setIsRetryOpen] = useState(false);
  const [retryOcrEngine, setRetryOcrEngine] = useState("PyMuPdfParser");

  // Edit form state (administrative metadata)
  const [editTitle, setEditTitle] = useState("");
  const [editDocNumber, setEditDocNumber] = useState("");
  const [editAuthority, setEditAuthority] = useState("");
  const [editIssuedDate, setEditIssuedDate] = useState("");

  const handleOpenEdit = () => {
    if (!document) return;
    setEditTitle(document.title || "");
    setEditDocNumber(document.document_number || "");
    setEditAuthority(document.issuing_authority || "");
    setEditIssuedDate(document.issued_date || "");
    setIsEditOpen(true);
  };

  const handleOpenEditMarkdown = () => {
    if (!selectedRevision) return;
    setEditMarkdownContent(selectedRevision.canonical_markdown || "");
    setEditReason("");
    setIsEditMarkdownOpen(true);
  };

  const handleOpenReview = (action: "approve" | "reject") => {
    setReviewAction(action);
    setReviewNotes("");
    setIsReviewOpen(true);
  };

  // Update administrative metadata mutation
  const updateMutation = useMutation({
    mutationFn: () =>
      documentsApi.updateDocument(documentId, {
        title: editTitle.trim() || undefined,
        document_number: editDocNumber.trim() || undefined,
        issuing_authority: editAuthority.trim() || undefined,
        issued_date: editIssuedDate || undefined,
      }),
    onSuccess: (data) => {
      toast.success("Đã cập nhật thông tin tài liệu.");
      queryClient.setQueryData(["repository-document", documentId], data);
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
      setIsEditOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Cập nhật tài liệu thất bại.");
    },
  });

  // Reparse mutation
  const reparseMutation = useMutation({
    mutationFn: () => documentsApi.reparseDocument(documentId),
    onSuccess: (data) => {
      toast.success("Đã bóc tách lại văn bản thành công.");
      queryClient.setQueryData(["repository-document", documentId], data);
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
      queryClient.invalidateQueries({
        queryKey: ["document-revisions", documentId],
      });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Bóc tách lại thất bại.");
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => documentsApi.deleteDocument(documentId),
    onSuccess: () => {
      toast.success("Đã xóa tài liệu khỏi kho tập trung.");
      navigate({ to: "/documents" });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Xóa tài liệu thất bại.");
    },
  });

  // Update Revision Content Mutation
  const updateContentMutation = useMutation({
    mutationFn: () => {
      if (!effectiveRevisionId) throw new Error("Chưa chọn bản sửa đổi");
      if (!selectedRevision) throw new Error("Chưa tải trạng thái bản sửa đổi");
      return documentsApi.updateRevisionContent(
        documentId,
        effectiveRevisionId,
        editMarkdownContent,
        selectedRevision.lock_version,
        editReason.trim() || undefined,
      );
    },
    onSuccess: (data) => {
      toast.success("Đã lưu nội dung hiệu đính Markdown.");
      queryClient.setQueryData(
        ["document-revision", documentId, effectiveRevisionId],
        data,
      );
      queryClient.invalidateQueries({
        queryKey: ["document-revisions", documentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["repository-document", documentId],
      });
      setIsEditMarkdownOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Lưu nội dung hiệu đính thất bại.");
    },
  });

  // Review Revision Mutation (Approve / Reject)
  const reviewMutation = useMutation({
    mutationFn: () => {
      if (!effectiveRevisionId) throw new Error("Chưa chọn bản sửa đổi");
      if (!selectedRevision) throw new Error("Chưa tải trạng thái bản sửa đổi");
      return documentsApi.reviewRevision(
        documentId,
        effectiveRevisionId,
        reviewAction,
        selectedRevision.lock_version,
        reviewNotes.trim() || undefined,
      );
    },
    onSuccess: (data) => {
      const msg =
        reviewAction === "approve"
          ? "Đã phê duyệt bản sửa đổi (Trạng thái Ready)."
          : "Đã từ chối bản sửa đổi.";
      toast.success(msg);
      queryClient.setQueryData(
        ["document-revision", documentId, effectiveRevisionId],
        data,
      );
      queryClient.invalidateQueries({
        queryKey: ["document-revisions", documentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["repository-document", documentId],
      });
      setIsReviewOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Thao tác thẩm định thất bại.");
    },
  });

  // Retry Revision Mutation
  const retryMutation = useMutation({
    mutationFn: () => {
      if (!effectiveRevisionId) throw new Error("Chưa chọn bản sửa đổi");
      return documentsApi.retryRevision(
        documentId,
        effectiveRevisionId,
        retryOcrEngine,
      );
    },
    onSuccess: (data) => {
      toast.success("Đã hoàn tất thử lại bóc tách và thẩm định chất lượng.");
      queryClient.setQueryData(
        ["document-revision", documentId, effectiveRevisionId],
        data,
      );
      queryClient.invalidateQueries({
        queryKey: ["document-revisions", documentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["repository-document", documentId],
      });
      setIsRetryOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Thử lại bóc tách thất bại.");
    },
  });

  if (isLoading) {
    return (
      <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto animate-pulse">
        <div className="h-8 w-48 bg-muted rounded-md" />
        <div className="h-32 bg-muted rounded-lg" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-96 bg-muted rounded-lg" />
          <div className="h-96 bg-muted rounded-lg" />
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex-1 p-8 max-w-3xl mx-auto">
        <EmptyState
          icon={XCircle}
          title="Không tìm thấy tài liệu"
          description="Tài liệu bạn tìm kiếm không tồn tại trong kho hoặc đã bị xóa."
          action={{
            label: "Quay Lại Kho Tài Liệu",
            onClick: () => navigate({ to: "/documents" }),
          }}
        />
      </div>
    );
  }

  const downloadUrl = documentsApi.getDownloadUrl(document.id);
  const previewPdfUrl = documentsApi.getPreviewPdfUrl(document.id, 1);

  return (
    <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* 1. Breadcrumb & Back Navigation */}
      <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground">
        <Link
          to="/documents"
          className="flex items-center gap-1.5 hover:text-primary transition-colors font-medium"
        >
          <ArrowLeft className="size-4" />
          Kho Tài Liệu
        </Link>
        <span>/</span>
        <span className="text-foreground font-semibold truncate max-w-md">
          {document.title || document.file_name}
        </span>
      </div>

      {/* 2. Detail Header & Action Toolbar */}
      <div className="flex flex-col gap-4 rounded-xl border border-border/70 bg-card p-5 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg sm:text-xl font-bold text-foreground truncate">
              {document.title || document.file_name}
            </h1>
            {document.document_type_name && (
              <Badge
                variant="secondary"
                className="bg-primary/10 text-primary border-primary/20"
              >
                {document.document_type_name}
              </Badge>
            )}
            {document.parse_status === "parsed" && (
              <Badge
                variant="outline"
                className="gap-1 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
              >
                <CheckCircle2 className="size-3" />
                Markdown Sạch
              </Badge>
            )}
            {document.parse_status === "failed" && (
              <Badge
                variant="outline"
                className="gap-1 border-destructive/30 text-destructive bg-destructive/10"
              >
                <XCircle className="size-3" />
                Lỗi Bóc Tách
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground flex flex-wrap items-center gap-3">
            <span>
              Tệp gốc:{" "}
              <strong className="text-foreground">{document.file_name}</strong>
            </span>
            <span>•</span>
            <span>Dung lượng: {formatFileSize(document.file_size_bytes)}</span>
            <span>•</span>
            <span>
              Định dạng:{" "}
              <span className="uppercase font-mono">{document.file_type}</span>
            </span>
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={handleOpenEdit}
            className="gap-1.5"
          >
            <Pencil className="size-3.5" />
            Sửa Metadata
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => reparseMutation.mutate()}
            disabled={reparseMutation.isPending}
            className="gap-1.5"
          >
            <RefreshCw
              className={`size-3.5 ${reparseMutation.isPending ? "animate-spin" : ""}`}
            />
            Bóc Tách Lại
          </Button>
          <Button variant="outline" size="sm" asChild className="gap-1.5">
            <a href={downloadUrl} download={document.file_name}>
              <Download className="size-3.5" />
              Tải Tệp Gốc
            </a>
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setIsDeleteOpen(true)}
            className="gap-1.5"
          >
            <Trash2 className="size-3.5" />
            Xóa
          </Button>
        </div>
      </div>

      {/* 3. Deep 2-Column Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2/3): Content Tabs */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="border-border/70">
            <CardHeader className="pb-3 border-b border-border/50">
              <Tabs
                value={activeTab}
                onValueChange={setActiveTab}
                className="w-full"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <TabsList className="grid grid-cols-3 w-full sm:w-[450px]">
                    <TabsTrigger value="revisions" className="gap-1.5 text-xs">
                      <History className="size-3.5" />
                      Phiên Bản ({revisions.length})
                    </TabsTrigger>
                    <TabsTrigger value="markdown" className="gap-1.5 text-xs">
                      <FileCode className="size-3.5" />
                      Markdown Sạch
                    </TabsTrigger>
                    <TabsTrigger value="preview" className="gap-1.5 text-xs">
                      <Eye className="size-3.5" />
                      Xem Trước PDF
                    </TabsTrigger>
                  </TabsList>

                  <div className="text-xs text-muted-foreground font-mono">
                    {selectedRevision ? (
                      <span>
                        Phiên bản:{" "}
                        <strong>v{selectedRevision.revision_no}</strong> (
                        {getOcrEngine(selectedRevision.parse_provenance)})
                      </span>
                    ) : document.doc_metadata?.table_count !== undefined ? (
                      <span>
                        Bảng: {document.doc_metadata.table_count} | Trang:{" "}
                        {document.doc_metadata.page_count ?? 1}
                      </span>
                    ) : null}
                  </div>
                </div>

                {/* Tab 1: Revisions & Quality Gate */}
                <TabsContent value="revisions" className="mt-4 space-y-4">
                  {/* Danh sách các bản sửa đổi */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
                        Lịch Sử Chuỗi Phiên Bản Bất Biến (Audit Trail)
                      </h3>
                      {selectedRevision && (
                        <div className="flex items-center gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1"
                            onClick={handleOpenEditMarkdown}
                          >
                            <Edit3 className="size-3" />
                            Hiệu Đính Markdown
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1 text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                            onClick={() => handleOpenReview("approve")}
                          >
                            <CheckCircle2 className="size-3" />
                            Duyệt (Ready)
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1 text-rose-600 dark:text-rose-400 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                            onClick={() => handleOpenReview("reject")}
                          >
                            <XCircle className="size-3" />
                            Từ Chối
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1"
                            onClick={() => setIsRetryOpen(true)}
                          >
                            <RotateCcw className="size-3" />
                            Thử Lại
                          </Button>
                        </div>
                      )}
                    </div>

                    {isRevisionsLoading ? (
                      <div className="p-4 text-center text-xs text-muted-foreground animate-pulse">
                        Đang tải chuỗi phiên bản...
                      </div>
                    ) : revisions.length > 0 ? (
                      <div className="rounded-lg border border-border/70 overflow-hidden">
                        <Table>
                          <TableHeader className="bg-muted/30">
                            <TableRow>
                              <TableHead className="w-20 text-xs">
                                Phiên bản
                              </TableHead>
                              <TableHead className="text-xs">
                                Trạng thái
                              </TableHead>
                              <TableHead className="text-xs">
                                OCR Engine
                              </TableHead>
                              <TableHead className="text-xs">
                                Quality Gate
                              </TableHead>
                              <TableHead className="text-xs">
                                Thời gian
                              </TableHead>
                              <TableHead className="text-right text-xs">
                                Thao tác
                              </TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {revisions.map((rev) => {
                              const isSelected = rev.id === effectiveRevisionId;
                              return (
                                <TableRow
                                  key={rev.id}
                                  className={isSelected ? "bg-primary/5" : ""}
                                >
                                  <TableCell className="font-mono font-medium text-xs">
                                    v{rev.revision_no}
                                    {rev.id ===
                                      document.current_revision_id && (
                                      <Badge
                                        variant="secondary"
                                        className="ml-1 text-[9px] h-3.5 px-1 bg-primary/10 text-primary border-primary/20"
                                      >
                                        Hiện Tại
                                      </Badge>
                                    )}
                                  </TableCell>
                                  <TableCell>
                                    {rev.status === "ready" && (
                                      <Badge
                                        variant="outline"
                                        className="text-[10px] gap-1 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                                      >
                                        <CheckCircle2 className="size-3" />
                                        Sẵn Sàng
                                      </Badge>
                                    )}
                                    {rev.status === "review_required" && (
                                      <Badge
                                        variant="outline"
                                        className="text-[10px] gap-1 border-warning/30 text-warning bg-warning/10"
                                      >
                                        <Clock className="size-3" />
                                        Chờ Thẩm Định
                                      </Badge>
                                    )}
                                    {(rev.status === "queued" ||
                                      rev.status === "processing" ||
                                      rev.status === "validating") && (
                                      <Badge
                                        variant="secondary"
                                        className="text-[10px]"
                                      >
                                        Đang Xử Lý
                                      </Badge>
                                    )}
                                    {rev.status === "failed" && (
                                      <Badge
                                        variant="outline"
                                        className="text-[10px] gap-1 border-destructive/30 text-destructive bg-destructive/10"
                                      >
                                        <XCircle className="size-3" />
                                        Lỗi
                                      </Badge>
                                    )}
                                  </TableCell>
                                  <TableCell className="text-xs font-mono text-muted-foreground">
                                    {rev.source_file_type.toUpperCase()}
                                  </TableCell>
                                  <TableCell>
                                    {rev.quality_report?.overall_status ===
                                    "passed" ? (
                                      <Badge
                                        variant="outline"
                                        className="text-[10px] gap-1 border-emerald-600/30 text-emerald-600 dark:text-emerald-400"
                                      >
                                        <ShieldCheck className="size-3" />
                                        Đạt Chuẩn
                                      </Badge>
                                    ) : rev.quality_report?.overall_status ===
                                      "failed" ? (
                                      <Badge
                                        variant="outline"
                                        className="text-[10px] gap-1 border-rose-600/30 text-rose-600 dark:text-rose-400"
                                      >
                                        <ShieldAlert className="size-3" />
                                        Chưa Đạt
                                      </Badge>
                                    ) : (
                                      <span className="text-xs text-muted-foreground">
                                        —
                                      </span>
                                    )}
                                  </TableCell>
                                  <TableCell className="text-xs text-muted-foreground">
                                    {new Date(rev.created_at).toLocaleString(
                                      "vi-VN",
                                      {
                                        dateStyle: "short",
                                        timeStyle: "short",
                                      },
                                    )}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    <Button
                                      variant={
                                        isSelected ? "default" : "outline"
                                      }
                                      size="sm"
                                      className="h-6 text-[11px] px-2"
                                      onClick={() =>
                                        setSelectedRevisionId(rev.id)
                                      }
                                    >
                                      {isSelected ? "Đang Chọn" : "Xem"}
                                    </Button>
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </div>
                    ) : (
                      <div className="p-4 text-center text-xs text-muted-foreground rounded-lg border border-dashed border-border">
                        Chưa có phiên bản nào được tạo. Nhấn "Bóc Tách Lại" để
                        khởi tạo phiên bản đầu tiên.
                      </div>
                    )}
                  </div>

                  {/* Chi tiết Quality Gate Report của Revision đang chọn */}
                  {selectedRevision?.quality_report && (
                    <Card className="border-border/60 bg-muted/10">
                      <CardHeader className="pb-2.5 pt-3 px-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Sparkles className="size-4 text-primary" />
                            <CardTitle className="text-xs font-semibold">
                              Báo Cáo Thẩm Định Chất Lượng (Quality Gate Report
                              — v{selectedRevision.revision_no})
                            </CardTitle>
                          </div>
                          <Badge
                            variant={
                              selectedRevision.quality_report.overall_status ===
                              "passed"
                                ? "outline"
                                : "destructive"
                            }
                            className={
                              selectedRevision.quality_report.overall_status ===
                              "passed"
                                ? "border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 text-xs"
                                : "text-xs"
                            }
                          >
                            {selectedRevision.quality_report.overall_status ===
                            "passed"
                              ? "Đạt Tiêu Chuẩn Xuất Bản"
                              : "Cần Hiệu Đính / Xử Lý Lại"}
                          </Badge>
                        </div>
                        <CardDescription className="text-[11px]">
                          Điểm đánh giá tự động:{" "}
                          <strong>
                            {typeof selectedRevision.quality_report
                              .overall_score === "number"
                              ? `${(selectedRevision.quality_report.overall_score * 100).toFixed(0)}%`
                              : "100%"}
                          </strong>{" "}
                          • Thuật toán kiểm tra bất biến hình thái học & mã hóa
                          Unicode UTF-8 sạch.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="px-4 pb-3.5 pt-0">
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
                          {Object.entries(
                            selectedRevision.quality_report.checks || {},
                          ).map(([checkName, check]) => (
                            <div
                              key={checkName}
                              className="p-2.5 rounded-lg border border-border/50 bg-background/60 space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-[11px] font-medium text-foreground">
                                  {checkName === "mojibake_clean"
                                    ? "Sạch Font UTF-8"
                                    : checkName === "text_density"
                                      ? "Mật Độ Ký Tự"
                                      : checkName === "table_count"
                                        ? "Bảng Biểu"
                                        : checkName === "min_length"
                                          ? "Độ Dài Tối Thiểu"
                                          : checkName}
                                </span>
                                {check.passed ? (
                                  <CheckCircle2 className="size-3 text-emerald-600" />
                                ) : (
                                  <AlertTriangle className="size-3 text-warning" />
                                )}
                              </div>
                              <p className="text-[10px] text-muted-foreground truncate">
                                {check.detail ||
                                  (check.passed ? "Đạt chuẩn" : "Cảnh báo")}
                              </p>
                            </div>
                          ))}
                        </div>

                        {selectedRevision.review_notes && (
                          <div className="mt-3 p-2.5 rounded-lg bg-muted/40 border border-border/50 text-xs">
                            <span className="font-semibold text-foreground">
                              Ghi chú thẩm định:{" "}
                            </span>
                            <span className="text-muted-foreground">
                              {selectedRevision.review_notes}
                            </span>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>

                {/* Tab 2: Markdown Clean Content */}
                <TabsContent value="markdown" className="mt-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      Nguồn:{" "}
                      <strong>
                        {selectedRevision
                          ? `Phiên bản v${selectedRevision.revision_no}`
                          : "Tài liệu gốc"}
                      </strong>
                    </span>
                    {selectedRevision && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-6 text-xs gap-1"
                        onClick={handleOpenEditMarkdown}
                      >
                        <Edit3 className="size-3" />
                        Hiệu Đính Nội Dung Này
                      </Button>
                    )}
                  </div>
                  {selectedRevision?.canonical_markdown ||
                  document.parsed_markdown ? (
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-4 max-h-[650px] overflow-y-auto">
                      <pre className="text-xs font-mono whitespace-pre-wrap text-foreground leading-relaxed">
                        {selectedRevision?.canonical_markdown ||
                          document.parsed_markdown}
                      </pre>
                    </div>
                  ) : (
                    <EmptyState
                      icon={FileCode}
                      title="Chưa có dữ liệu Markdown"
                      description="Tài liệu chưa được bóc tách hoặc đang trong quá trình xử lý."
                      action={{
                        label: "Tiến Hành Bóc Tách",
                        onClick: () => reparseMutation.mutate(),
                      }}
                    />
                  )}
                </TabsContent>

                {/* Tab 3: PDF Preview */}
                <TabsContent value="preview" className="mt-4">
                  {document.file_type === "pdf" ? (
                    <div className="rounded-lg border border-border/60 bg-muted/10 p-2 flex flex-col items-center justify-center min-h-[450px]">
                      <img
                        src={previewPdfUrl}
                        alt="Xem trước trang 1"
                        className="max-h-[600px] rounded shadow-md object-contain border border-border"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                      <p className="text-xs text-muted-foreground mt-3">
                        Hình ảnh render trang đầu tiên từ MinIO S3
                      </p>
                    </div>
                  ) : (
                    <EmptyState
                      icon={FileText}
                      title="Không hỗ trợ xem trước hình ảnh"
                      description={`Định dạng .${document.file_type} không hỗ trợ kết xuất hình ảnh trực tiếp. Vui lòng tải về tệp gốc để xem.`}
                      action={{
                        label: "Tải Tệp Về",
                        onClick: () => window.open(downloadUrl, "_blank"),
                      }}
                    />
                  )}
                </TabsContent>
              </Tabs>
            </CardHeader>
          </Card>
        </div>

        {/* Right Column (1/3): Metadata & Attached Collections */}
        <div className="space-y-6">
          {/* Box 1: Administrative Metadata (Nghị định 30) */}
          <Card className="border-border/70">
            <CardHeader className="pb-3 border-b border-border/50">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" />
                Thông Tin Hành Chính (NĐ 30)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-4 text-xs">
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Số hiệu VB:</span>
                <span className="font-mono font-medium text-foreground">
                  {document.document_number || "Chưa cập nhật"}
                </span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Cơ quan ban hành:</span>
                <span className="font-medium text-foreground text-right truncate max-w-[180px]">
                  {document.issuing_authority || "ĐH Quy Nhơn"}
                </span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Ngày ban hành:</span>
                <span className="font-medium text-foreground">
                  {document.issued_date || "Chưa cập nhật"}
                </span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Người ký:</span>
                <span className="font-medium text-foreground">
                  {document.signer || "Chưa cập nhật"}
                </span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Loại văn bản:</span>
                <span className="font-medium text-primary">
                  {document.document_type_name || "Chưa phân loại"}
                </span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Mã băm SHA-256:</span>
                <span
                  className="font-mono text-[11px] text-muted-foreground truncate max-w-[150px]"
                  title={document.file_hash}
                >
                  {document.file_hash.slice(0, 16)}...
                </span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-muted-foreground">MinIO S3 Key:</span>
                <span
                  className="font-mono text-[10px] text-muted-foreground truncate max-w-[150px]"
                  title={document.storage_path}
                >
                  {document.storage_path}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Box 2: Attached Knowledge Collections */}
          <Card className="border-border/70">
            <CardHeader className="pb-3 border-b border-border/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <BookOpen className="size-4 text-primary" />
                  Kho Tri Thức Đang Gắn
                </CardTitle>
                <Badge variant="secondary" className="text-xs">
                  {document.attached_collections_count}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              {document.attached_collections.length > 0 ? (
                <div className="space-y-2">
                  {document.attached_collections.map((ac) => (
                    <div
                      key={ac.document_id}
                      className="flex items-center justify-between p-2.5 rounded-lg border border-border/60 bg-muted/20 hover:bg-muted/40 transition-colors"
                    >
                      <div className="min-w-0">
                        <Link
                          to="/knowledge/$collectionId"
                          params={{ collectionId: ac.collection_id }}
                          className="text-xs font-semibold text-foreground hover:text-primary transition-colors flex items-center gap-1 truncate"
                        >
                          {ac.collection_name}
                          <ExternalLink className="size-3 text-muted-foreground" />
                        </Link>
                        <span className="text-[11px] text-muted-foreground block">
                          Trạng thái: {ac.index_status}
                        </span>
                      </div>
                      <Badge
                        variant="outline"
                        className="text-[10px] py-0 h-4 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                      >
                        Đã Gắn
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center">
                  <p className="text-xs text-muted-foreground">
                    Tài liệu này chưa được gắn vào Kho Tri Thức nào.
                  </p>
                  <p className="text-[11px] text-muted-foreground/80 mt-1">
                    Bạn có thể vào phân hệ Kho Tri Thức và chọn "Gắn Từ Kho Tài
                    Liệu".
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Metadata Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Chỉnh Sửa Thông Tin Hành Chính</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <span className="font-medium text-foreground">
                Tiêu đề / Trích yếu
              </span>
              <Input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <span className="font-medium text-foreground">
                Số hiệu văn bản
              </span>
              <Input
                value={editDocNumber}
                onChange={(e) => setEditDocNumber(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <span className="font-medium text-foreground">
                Cơ quan ban hành
              </span>
              <Input
                value={editAuthority}
                onChange={(e) => setEditAuthority(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <span className="font-medium text-foreground">Ngày ban hành</span>
              <Input
                type="date"
                value={editIssuedDate}
                onChange={(e) => setEditIssuedDate(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>
              Hủy
            </Button>
            <Button
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending}
            >
              Lưu Thay Đổi
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        open={isDeleteOpen}
        onOpenChange={setIsDeleteOpen}
        title="Xác nhận xóa tài liệu khỏi kho"
        description={`Bạn có chắc chắn muốn xóa tài liệu "${document.title || document.file_name}" không? Hành động này sẽ xóa tệp gốc trên MinIO S3.`}
        confirmText="Xóa Tài Liệu"
        confirmVariant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        isPending={deleteMutation.isPending}
      />

      {/* Revision Edit Markdown Dialog */}
      <Dialog open={isEditMarkdownOpen} onOpenChange={setIsEditMarkdownOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit3 className="size-4 text-primary" />
              Hiệu Đính Nội Dung Markdown (Phiên Bản v
              {selectedRevision?.revision_no})
            </DialogTitle>
            <DialogDescription className="text-xs">
              Chỉnh sửa trực tiếp nội dung văn bản Markdown trước khi phê duyệt
              sẵn sàng xuất bản. Hành động này ghi nhận nhật ký kiểm toán.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2 flex-1 overflow-y-auto">
            <div className="space-y-1">
              <span className="text-xs font-medium text-foreground">
                Nội dung Markdown
              </span>
              <Textarea
                value={editMarkdownContent}
                onChange={(e) => setEditMarkdownContent(e.target.value)}
                className="font-mono text-xs min-h-[350px] max-h-[450px]"
                placeholder="# Nhập nội dung Markdown..."
              />
            </div>
            <div className="space-y-1">
              <span className="text-xs font-medium text-foreground">
                Lý do hiệu đính (Bắt buộc kiểm toán ISO)
              </span>
              <Input
                value={editReason}
                onChange={(e) => setEditReason(e.target.value)}
                placeholder="Ví dụ: Chuẩn hóa lại bảng biểu học phí, sửa lỗi chính tả tiêu đề Điều 4..."
                className="text-xs"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsEditMarkdownOpen(false)}
              className="text-xs"
            >
              Hủy
            </Button>
            <Button
              onClick={() => updateContentMutation.mutate()}
              disabled={updateContentMutation.isPending}
              className="text-xs"
            >
              Lưu Nội Dung Hiệu Đính
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revision Review Dialog (Approve / Reject) */}
      <Dialog open={isReviewOpen} onOpenChange={setIsReviewOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {reviewAction === "approve" ? (
                <>
                  <CheckCircle2 className="size-4 text-emerald-600" />
                  Phê Duyệt Bản Sửa Đổi (Chuyển Sang Ready)
                </>
              ) : (
                <>
                  <XCircle className="size-4 text-rose-600" />
                  Từ Chối Bản Sửa Đổi
                </>
              )}
            </DialogTitle>
            <DialogDescription className="text-xs">
              {reviewAction === "approve"
                ? `Xác nhận bản sửa đổi v${selectedRevision?.revision_no} đạt chuẩn chất lượng và sẵn sàng để các Kho Tri Thức liên kết, lập chỉ mục vector.`
                : `Từ chối bản sửa đổi v${selectedRevision?.revision_no}. Cán bộ phụ trách sẽ cần hiệu đính hoặc bóc tách lại.`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <span className="font-medium text-foreground">
                Ghi chú thẩm định
              </span>
              <Textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Nhập nhận xét hoặc chỉ dẫn cho cán bộ biên tập..."
                className="text-xs min-h-20"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsReviewOpen(false)}
              className="text-xs"
            >
              Hủy
            </Button>
            <Button
              variant={reviewAction === "approve" ? "default" : "destructive"}
              onClick={() => reviewMutation.mutate()}
              disabled={reviewMutation.isPending}
              className="text-xs"
            >
              {reviewAction === "approve"
                ? "Xác Nhận Phê Duyệt"
                : "Xác Nhận Từ Chối"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revision Retry Dialog */}
      <Dialog open={isRetryOpen} onOpenChange={setIsRetryOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RotateCcw className="size-4 text-primary" />
              Thử Lại Bóc Tách & Thẩm Định Chất Lượng
            </DialogTitle>
            <DialogDescription className="text-xs">
              Khởi chạy lại chuỗi bóc tách OCR và kiểm định Quality Gate cho bản
              sửa đổi v{selectedRevision?.revision_no}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <span className="font-medium text-foreground">
                Công cụ trích xuất (OCR Engine)
              </span>
              <div className="grid grid-cols-2 gap-2 pt-1">
                <Button
                  type="button"
                  variant={
                    retryOcrEngine === "PyMuPdfParser" ? "default" : "outline"
                  }
                  size="sm"
                  className="text-xs"
                  onClick={() => setRetryOcrEngine("PyMuPdfParser")}
                >
                  PyMuPDF Parser (Mặc định)
                </Button>
                <Button
                  type="button"
                  variant={
                    retryOcrEngine === "DoclingParser" ? "default" : "outline"
                  }
                  size="sm"
                  className="text-xs"
                  onClick={() => setRetryOcrEngine("DoclingParser")}
                >
                  Docling Parser (Chuyên sâu)
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsRetryOpen(false)}
              className="text-xs"
            >
              Hủy
            </Button>
            <Button
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              className="text-xs"
            >
              Bắt Đầu Bóc Tách Lại
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
