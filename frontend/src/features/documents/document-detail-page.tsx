import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Download,
  ExternalLink,
  Eye,
  FileCode,
  FileText,
  Pencil,
  RefreshCw,
  ShieldCheck,
  Trash2,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { documentsApi } from "@/services/documents-api";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentDetailPage() {
  const { documentId } = useParams({ from: "/documents/$documentId" });
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState("markdown");
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

  // Edit form state
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

  // Update mutation
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
              Tệp gốc: <strong className="text-foreground">{document.file_name}</strong>
            </span>
            <span>•</span>
            <span>Dung lượng: {formatFileSize(document.file_size_bytes)}</span>
            <span>•</span>
            <span>
              Định dạng: <span className="uppercase font-mono">{document.file_type}</span>
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
                <div className="flex items-center justify-between">
                  <TabsList className="grid grid-cols-2 w-72">
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
                    {document.doc_metadata?.table_count !== undefined && (
                      <span>
                        Bảng: {document.doc_metadata.table_count} | Trang:{" "}
                        {document.doc_metadata.page_count ?? 1}
                      </span>
                    )}
                  </div>
                </div>

                {/* Tab 1: Markdown Clean Content */}
                <TabsContent value="markdown" className="mt-4">
                  {document.parsed_markdown ? (
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-4 max-h-[650px] overflow-y-auto">
                      <pre className="text-xs font-mono whitespace-pre-wrap text-foreground leading-relaxed">
                        {document.parsed_markdown}
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

                {/* Tab 2: PDF Preview */}
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
              <span className="font-medium text-foreground">Tiêu đề / Trích yếu</span>
              <Input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <span className="font-medium text-foreground">Số hiệu văn bản</span>
              <Input
                value={editDocNumber}
                onChange={(e) => setEditDocNumber(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <span className="font-medium text-foreground">Cơ quan ban hành</span>
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
    </div>
  );
}
