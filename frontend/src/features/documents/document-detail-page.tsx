import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  Eye,
  FileCode,
  FileSpreadsheet,
  FileText,
  Folders,
  HardDrive,
  History,
  Info,
  Pencil,
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
import { documentsApi } from "@/services/documents-api";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(fileType: string) {
  switch (fileType.toLowerCase()) {
    case "pdf":
      return <FileText className="size-5 text-destructive" />;
    case "xlsx":
    case "xls":
      return <FileSpreadsheet className="size-5 text-success" />;
    case "md":
    case "txt":
      return <FileCode className="size-5 text-info" />;
    default:
      return <FileText className="size-5 text-primary" />;
  }
}

export function DocumentDetailPage() {
  const { documentId } = useParams({ from: "/documents/$documentId" });
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState("preview");
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  // 1. Fetch document details
  const {
    data: document,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["repository-document", documentId],
    queryFn: () => documentsApi.getDocument(documentId),
  });

  // 2. Fetch File Revisions (immutable storage revisions)
  const { data: fileRevisionsData, isLoading: isFileRevisionsLoading } =
    useQuery({
      queryKey: ["document-file-revisions", documentId],
      queryFn: () => documentsApi.getFileRevisions(documentId),
    });

  const fileRevisions = fileRevisionsData?.items ?? [];

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
        <div className="h-28 bg-muted rounded-lg" />
        <div className="h-96 bg-muted rounded-lg" />
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
                className="bg-primary/10 text-primary border-primary/20 text-xs"
              >
                {document.document_type_name}
              </Badge>
            )}
            <Badge
              variant="outline"
              className="gap-1 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 text-xs"
            >
              <CheckCircle2 className="size-3" />
              Đã Lưu Trữ
            </Badge>
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
            Sửa Thông Tin
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

      {/* 3. Storage Tabs Layout */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid grid-cols-3 w-full sm:w-[480px]">
          <TabsTrigger value="preview" className="gap-1.5 text-xs">
            <Eye className="size-3.5" />
            Xem Trước Tệp
          </TabsTrigger>
          <TabsTrigger value="info" className="gap-1.5 text-xs">
            <Info className="size-3.5" />
            Thông Tin Chi Tiết
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-1.5 text-xs">
            <History className="size-3.5" />
            Lịch Sử Phiên Bản ({fileRevisions.length || 1})
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Preview / Original File */}
        <TabsContent value="preview" className="space-y-4">
          <Card className="border-border/70">
            <CardHeader className="pb-3 border-b border-border/50">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Eye className="size-4 text-primary" />
                    Kết Xuất Xem Trước Tệp Gốc
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Hình ảnh render trực tiếp từ tệp lưu trữ trên MinIO S3
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" asChild className="gap-1.5 h-8 text-xs">
                  <a href={downloadUrl} download={document.file_name}>
                    <Download className="size-3.5" />
                    Tải Về Tệp Gốc
                  </a>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              {document.file_type === "pdf" ? (
                <div className="rounded-lg border border-border/60 bg-muted/10 p-4 flex flex-col items-center justify-center min-h-[450px]">
                  <img
                    src={previewPdfUrl}
                    alt="Xem trước trang 1"
                    className="max-h-[600px] rounded shadow-md object-contain border border-border bg-background"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = "none";
                    }}
                  />
                  <p className="text-xs text-muted-foreground mt-3">
                    Hình ảnh trang đầu tiên của tệp PDF lưu trên MinIO S3
                  </p>
                </div>
              ) : (
                <div className="rounded-lg border border-border/60 bg-muted/10 p-8 flex flex-col items-center justify-center text-center space-y-4">
                  <div className="flex size-14 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    {getFileIcon(document.file_type)}
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground">
                      {document.file_name}
                    </p>
                    <p className="text-xs text-muted-foreground max-w-md">
                      Tệp định dạng <span className="uppercase font-mono font-semibold">.{document.file_type}</span> ({formatFileSize(document.file_size_bytes)}) đã được lưu trữ an toàn trong kho.
                    </p>
                  </div>
                  <Button asChild size="sm" className="gap-1.5 shadow-xs">
                    <a href={downloadUrl} download={document.file_name}>
                      <Download className="size-4" />
                      Tải Về Tệp Gốc
                    </a>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Detailed Technical & Administrative Info */}
        <TabsContent value="info" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Box 1: Administrative Metadata (Nghị định 30) */}
            <Card className="border-border/70">
              <CardHeader className="pb-3 border-b border-border/50">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <ShieldCheck className="size-4 text-primary" />
                  Thông Tin Hành Chính (Nghị Định 30)
                </CardTitle>
                <CardDescription className="text-xs">
                  Metadata phân loại văn bản lưu trữ
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 pt-4 text-xs">
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Tiêu đề / Trích yếu:</span>
                  <span className="font-medium text-foreground text-right truncate max-w-[220px]">
                    {document.title || document.file_name}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Số hiệu VB:</span>
                  <span className="font-mono font-medium text-foreground">
                    {document.document_number || "Chưa cập nhật"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Cơ quan ban hành:</span>
                  <span className="font-medium text-foreground text-right truncate max-w-[200px]">
                    {document.issuing_authority || "ĐH Quy Nhơn"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Ngày ban hành:</span>
                  <span className="font-medium text-foreground">
                    {document.issued_date || "Chưa cập nhật"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Người ký:</span>
                  <span className="font-medium text-foreground">
                    {document.signer || "Chưa cập nhật"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5">
                  <span className="text-muted-foreground">Loại văn bản:</span>
                  <span className="font-medium text-primary">
                    {document.document_type_name || "Chưa phân loại"}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Box 2: Storage & Integrity Specs */}
            <Card className="border-border/70">
              <CardHeader className="pb-3 border-b border-border/50">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <HardDrive className="size-4 text-primary" />
                  Thông Số Lưu Trữ & Toàn Vẹn Tệp
                </CardTitle>
                <CardDescription className="text-xs">
                  Xác thực mã băm SHA-256 và vị trí MinIO S3
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 pt-4 text-xs">
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Tên tệp gốc:</span>
                  <span className="font-medium text-foreground truncate max-w-[200px]">
                    {document.file_name}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Định dạng tệp:</span>
                  <span className="font-mono uppercase font-medium text-foreground">
                    .{document.file_type}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Dung lượng:</span>
                  <span className="font-mono text-foreground">
                    {formatFileSize(document.file_size_bytes)}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Mã băm SHA-256:</span>
                  <span
                    className="font-mono text-[11px] text-muted-foreground truncate max-w-[180px]"
                    title={document.file_hash}
                  >
                    {document.file_hash}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                  <span className="text-muted-foreground">Đường dẫn MinIO:</span>
                  <span
                    className="font-mono text-[10px] text-muted-foreground truncate max-w-[180px]"
                    title={document.storage_path}
                  >
                    {document.storage_path}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5">
                  <span className="text-muted-foreground">Thời gian tải lên:</span>
                  <span className="text-foreground">
                    {new Date(document.created_at).toLocaleString("vi-VN")}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Box 3: Associated Document Groups */}
          <Card className="border-border/70">
            <CardHeader className="pb-3 border-b border-border/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Folders className="size-4 text-primary" />
                  Kho Tài Liệu Trực Thuộc
                </CardTitle>
                <Badge variant="secondary" className="text-xs">
                  {document.groups?.length ?? 0} kho
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              {document.groups && document.groups.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {document.groups.map((g) => (
                    <Link
                      key={g.id}
                      to="/documents/groups/$groupId"
                      params={{ groupId: g.id }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/70 bg-muted/20 hover:bg-muted/50 text-xs font-medium text-foreground transition-colors"
                    >
                      <Folders className="size-3.5 text-primary" />
                      {g.name}
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Tài liệu này chưa được gán vào kho tài liệu cụ thể nào. Bạn có thể gán tài liệu vào kho từ trang danh sách.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: File Revisions History */}
        <TabsContent value="history" className="space-y-4">
          <Card className="border-border/70">
            <CardHeader className="pb-3 border-b border-border/50">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <History className="size-4 text-primary" />
                    Lịch Sử Các Phiên Bản Tệp Gốc
                  </CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Theo dõi các phiên bản tệp gốc đã được tải lên và lưu trữ trên MinIO S3
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              {/* Microcopy Banner Tuân Thủ Kế Hoạch 12 */}
              <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3.5 text-xs leading-relaxed">
                <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
                  <ShieldCheck className="size-3.5" />
                </div>
                <div className="space-y-0.5">
                  <p className="font-semibold text-foreground">
                    Kho Lưu Trữ Tệp Bất Biến (Document Vault)
                  </p>
                  <p className="text-muted-foreground">
                    Tệp được lưu an toàn trong Kho tài liệu. Việc bóc tách văn bản, OCR và lập chỉ mục Vector được thực hiện độc lập khi bạn nạp tệp vào Kho Tri Thức.
                  </p>
                </div>
              </div>

              {isFileRevisionsLoading ? (
                <div className="p-6 text-center text-xs text-muted-foreground animate-pulse">
                  Đang tải lịch sử phiên bản tệp...
                </div>
              ) : fileRevisions.length > 0 ? (
                <div className="rounded-lg border border-border/70 overflow-hidden">
                  <Table>
                    <TableHeader className="bg-muted/30">
                      <TableRow>
                        <TableHead className="w-24 text-xs">Phiên bản</TableHead>
                        <TableHead className="text-xs">Tên tệp gốc</TableHead>
                        <TableHead className="w-24 text-xs">Định dạng</TableHead>
                        <TableHead className="w-28 text-xs text-right">Dung lượng</TableHead>
                        <TableHead className="w-40 text-xs">Mã băm SHA-256</TableHead>
                        <TableHead className="w-36 text-xs">Thời gian tải</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {fileRevisions.map((rev) => (
                        <TableRow key={rev.id}>
                          <TableCell className="font-mono font-medium text-xs">
                            v{rev.revision_no}
                          </TableCell>
                          <TableCell className="font-medium text-xs text-foreground truncate max-w-[200px]">
                            {rev.source_file_name}
                          </TableCell>
                          <TableCell className="font-mono text-xs uppercase text-muted-foreground">
                            .{rev.source_file_type}
                          </TableCell>
                          <TableCell className="text-right text-xs font-mono text-muted-foreground">
                            {formatFileSize(rev.source_size_bytes)}
                          </TableCell>
                          <TableCell className="font-mono text-[11px] text-muted-foreground truncate max-w-[150px]" title={rev.source_hash}>
                            {rev.source_hash.slice(0, 16)}...
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {new Date(rev.created_at).toLocaleString("vi-VN", {
                              dateStyle: "short",
                              timeStyle: "short",
                            })}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="rounded-lg border border-border/70 overflow-hidden">
                  <Table>
                    <TableHeader className="bg-muted/30">
                      <TableRow>
                        <TableHead className="w-24 text-xs">Phiên bản</TableHead>
                        <TableHead className="text-xs">Tên tệp gốc</TableHead>
                        <TableHead className="w-24 text-xs">Định dạng</TableHead>
                        <TableHead className="w-28 text-xs text-right">Dung lượng</TableHead>
                        <TableHead className="w-40 text-xs">Mã băm SHA-256</TableHead>
                        <TableHead className="w-36 text-xs">Thời gian tải</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell className="font-mono font-medium text-xs">v1</TableCell>
                        <TableCell className="font-medium text-xs text-foreground truncate max-w-[200px]">
                          {document.file_name}
                        </TableCell>
                        <TableCell className="font-mono text-xs uppercase text-muted-foreground">
                          .{document.file_type}
                        </TableCell>
                        <TableCell className="text-right text-xs font-mono text-muted-foreground">
                          {formatFileSize(document.file_size_bytes)}
                        </TableCell>
                        <TableCell className="font-mono text-[11px] text-muted-foreground truncate max-w-[150px]" title={document.file_hash}>
                          {document.file_hash.slice(0, 16)}...
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {new Date(document.created_at).toLocaleString("vi-VN", {
                            dateStyle: "short",
                            timeStyle: "short",
                          })}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

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
    </div>
  );
}
