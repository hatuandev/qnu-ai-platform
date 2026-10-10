import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  Clock,
  FileCode,
  FileSpreadsheet,
  FileStack,
  FileText,
  FolderOpen,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import { documentsApi } from "@/services/documents-api";
import type { GroupDocumentItem } from "@/types/documents";
import { AttachGroupToKnowledgeDialog } from "./components/attach-group-to-knowledge-dialog";
import { DocumentUploadModal } from "./components/document-upload-modal";

interface DocumentGroupDetailPageProps {
  groupId: string;
}

function getRevisionStatusBadge(status?: string | null) {
  switch (status) {
    case "ready":
      return (
        <Badge variant="default" className="text-[10px]">
          Sẵn sàng
        </Badge>
      );
    case "queued":
      return (
        <Badge
          variant="outline"
          className="text-[10px] text-warning border-warning/30 bg-warning/10"
        >
          Chờ xử lý
        </Badge>
      );
    case "processing":
    case "validating":
      return (
        <Badge
          variant="outline"
          className="text-[10px] text-blue-600 border-blue-300 bg-blue-50 dark:bg-blue-950/20"
        >
          Đang xử lý
        </Badge>
      );
    case "review_required":
      return (
        <Badge
          variant="outline"
          className="text-[10px] text-purple-600 border-purple-300 bg-purple-50 dark:bg-purple-950/20"
        >
          Cần duyệt
        </Badge>
      );
    case "failed":
    case "cancelled":
      return (
        <Badge variant="destructive" className="text-[10px]">
          Lỗi
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-[10px]">
          Chờ xử lý
        </Badge>
      );
  }
}

function getFileIcon(fileType: string) {
  switch (fileType.toLowerCase()) {
    case "pdf":
      return <FileText className="size-4 text-destructive" />;
    case "xlsx":
    case "xls":
      return <FileSpreadsheet className="size-4 text-success" />;
    case "md":
    case "txt":
      return <FileCode className="size-4 text-info" />;
    default:
      return <FileText className="size-4 text-primary" />;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentGroupDetailPage({
  groupId,
}: DocumentGroupDetailPageProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState<"grid" | "table">("table");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isAttachModalOpen, setIsAttachModalOpen] = useState(false);
  const [removingDoc, setRemovingDoc] = useState<GroupDocumentItem | null>(
    null,
  );

  // 1. Fetch Group Details
  const {
    data: group,
    isLoading: isLoadingGroup,
    isError: isErrorGroup,
    error: groupError,
    refetch: refetchGroup,
  } = useQuery({
    queryKey: ["document-group", groupId],
    queryFn: () => documentsApi.getGroup(groupId),
  });

  // 2. Fetch Group Documents
  const {
    data: groupDocsData,
    isLoading: isLoadingDocs,
    isError: isErrorDocs,
    error: docsError,
    refetch: refetchDocs,
  } = useQuery({
    queryKey: ["group-documents", groupId, search, statusFilter],
    queryFn: () =>
      documentsApi.getGroupDocuments(groupId, {
        search: search.trim() || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        page_size: 100,
      }),
  });

  const documents = groupDocsData?.items ?? [];

  // Remove document from group mutation
  const removeMutation = useMutation({
    mutationFn: (docId: string) =>
      documentsApi.removeDocumentFromGroup(groupId, docId),
    onSuccess: () => {
      toast.success(
        "Đã gỡ tài liệu khỏi kho (tài liệu gốc vẫn được bảo toàn nguyên vẹn).",
      );
      queryClient.invalidateQueries({ queryKey: ["group-documents", groupId] });
      queryClient.invalidateQueries({ queryKey: ["document-group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      setRemovingDoc(null);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Gỡ tài liệu khỏi kho thất bại.");
    },
  });

  if (isLoadingGroup) {
    return (
      <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-32" />
        </div>
        <div className="rounded-xl border border-border/80 bg-card p-6 space-y-3">
          <Skeleton className="h-6 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
        <Skeleton className="h-64 rounded-lg" />
      </div>
    );
  }

  if (isErrorGroup || !group) {
    const status = (groupError as { status?: number })?.status;
    return (
      <div className="flex-1 p-8 max-w-7xl mx-auto">
        <EmptyState
          icon={AlertCircle}
          title={
            status === 403
              ? "Không có quyền truy cập kho tài liệu"
              : status === 404
                ? "Không tìm thấy kho tài liệu"
                : "Không thể tải thông tin kho tài liệu"
          }
          description={
            status === 403
              ? `Bạn không có quyền truy cập kho tài liệu '${groupId}'. Vui lòng liên hệ quản trị viên.`
              : status === 404
                ? `Kho tài liệu ID '${groupId}' không tồn tại hoặc đã bị gỡ bỏ.`
                : (groupError as Error)?.message ||
                  "Đã xảy ra lỗi khi tải dữ liệu từ máy chủ. Vui lòng thử lại sau."
          }
          action={
            status === 404
              ? {
                  label: "Quay Lại Kho Tài Liệu",
                  onClick: () => navigate({ to: "/documents" }),
                }
              : {
                  label: "Thử lại",
                  onClick: () => refetchGroup(),
                }
          }
        />
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* 1. Breadcrumb & Back button */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate({ to: "/documents" })}
          className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Về Kho Tài Liệu
        </Button>
        <span>/</span>
        <Link to="/documents" className="hover:text-foreground">
          Kho Tài Liệu
        </Link>
        <span>/</span>
        <span className="text-foreground font-medium">{group.name}</span>
      </div>

      {/* 2. Group Hero Banner */}
      <div className="flex flex-col gap-4 rounded-xl border border-border/80 bg-card p-4 sm:p-6 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3.5">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <FolderOpen className="size-6" />
          </div>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold text-foreground tracking-tight">
                {group.name}
              </h1>
              <Badge variant="outline" className="text-xs">
                {group.total_documents} tài liệu
              </Badge>
            </div>
            {group.description && (
              <p className="text-xs sm:text-sm text-muted-foreground max-w-2xl leading-relaxed">
                {group.description}
              </p>
            )}
            <div className="text-[11px] text-muted-foreground pt-0.5">
              Cập nhật lần cuối:{" "}
              {new Date(group.updated_at).toLocaleString("vi-VN")}
            </div>
          </div>
        </div>

        {/* Action Toolbar: Tải lên & Đưa vào kho tri thức */}
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-center">
          <Button
            onClick={() => setIsUploadModalOpen(true)}
            className="gap-1.5 h-9 text-xs shadow-sm bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            <Upload className="size-4" />
            Tải lên
          </Button>
          <Button
            onClick={() => setIsAttachModalOpen(true)}
            variant="outline"
            className="gap-1.5 h-9 text-xs shadow-sm border-primary/30 text-primary hover:bg-primary/10"
          >
            <BookOpen className="size-4" />
            Đưa vào kho tri thức
          </Button>
        </div>
      </div>

      {/* 3. KPI Bento Grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-4">
        <KpiMetric
          label="Tổng Tài Liệu"
          value={String(group.total_documents)}
          icon={FileStack}
        />
        <KpiMetric
          label="Sẵn Sàng Đưa Vào Kho"
          value={String(group.ready_documents)}
          icon={CheckCircle2}
        />
        <KpiMetric
          label="Đang Xử Lý Bóc Tách"
          value={String(group.processing_documents)}
          icon={Clock}
        />
        <KpiMetric
          label="Lỗi Cần Kiểm Tra"
          value={String(group.error_documents)}
          icon={AlertCircle}
        />
      </div>

      {/* 4. Seamless Search & Filter Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          {/* Search */}
          <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
            <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Tìm kiếm tài liệu trong kho..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-9 text-xs"
            />
          </div>

          {/* Status Filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px] h-9 text-xs">
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              <SelectItem value="ready">Sẵn sàng (Ready)</SelectItem>
              <SelectItem value="processing">Đang xử lý</SelectItem>
              <SelectItem value="queued">Chờ xử lý</SelectItem>
              <SelectItem value="review_required">Cần duyệt</SelectItem>
              <SelectItem value="error">Lỗi bóc tách</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-2 self-end sm:self-center">
          <ViewModeToggle value={viewMode} onChange={setViewMode} />
        </div>
      </div>

      {/* 5. Document List: Grid or Table or Error */}
      {isLoadingDocs ? (
        <div className="h-64 rounded-lg border border-border/50 bg-muted/20 animate-pulse" />
      ) : isErrorDocs ? (
        <EmptyState
          icon={AlertCircle}
          title={
            (docsError as { status?: number })?.status === 403
              ? "Không có quyền xem tài liệu"
              : "Không thể tải danh sách tài liệu"
          }
          description={
            (docsError as { status?: number })?.status === 403
              ? "Bạn không có quyền truy cập danh sách tài liệu trong kho này."
              : (docsError as Error)?.message ||
                "Đã xảy ra lỗi khi tải danh sách tài liệu. Vui lòng thử lại."
          }
          action={{
            label: "Thử lại",
            onClick: () => refetchDocs(),
          }}
        />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileStack}
          title="Kho tài liệu chưa có văn bản nào"
          description={
            search || statusFilter !== "all"
              ? "Không có tài liệu nào khớp với bộ lọc."
              : "Hãy bắt đầu bằng cách tải lên các tài liệu vào kho này."
          }
          action={{
            label: "Tải lên",
            onClick: () => setIsUploadModalOpen(true),
          }}
        />
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => (
            <Card
              key={doc.id}
              className="flex flex-col justify-between hover:border-primary/40 transition-all"
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="flex size-7 shrink-0 items-center justify-center rounded bg-muted/60">
                      {getFileIcon(doc.file_type)}
                    </div>
                    <CardTitle className="text-xs sm:text-sm font-semibold line-clamp-1">
                      {doc.title || doc.file_name}
                    </CardTitle>
                  </div>
                  {getRevisionStatusBadge(doc.revision_status)}
                </div>
                <div className="text-[11px] text-muted-foreground truncate mt-1">
                  {doc.file_name}
                </div>
              </CardHeader>

              <CardContent className="space-y-1 text-[11px] text-muted-foreground py-1">
                <div>Dung lượng: {formatFileSize(doc.file_size_bytes)}</div>
                <div>
                  Ngày thêm:{" "}
                  {new Date(doc.added_at).toLocaleDateString("vi-VN")}
                </div>
              </CardContent>

              <CardFooter className="flex items-center justify-between border-t border-border/60 pt-2.5">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRemovingDoc(doc)}
                  className="h-7 text-xs text-muted-foreground hover:text-destructive gap-1 px-2"
                >
                  <X className="size-3.5" />
                  Gỡ khỏi kho
                </Button>

                <Button
                  asChild
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs gap-1 px-2"
                >
                  <Link
                    to="/documents/$documentId"
                    params={{ documentId: doc.id }}
                  >
                    <span>Chi tiết</span>
                    <ArrowUpRight className="size-3" />
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-border/70 bg-card overflow-hidden">
          <Table>
            <TableHeader className="bg-muted/20">
              <TableRow className="h-9 hover:bg-transparent">
                <TableHead className="text-xs">Tên Tài Liệu & Tệp</TableHead>
                <TableHead className="w-36 text-xs">Loại Văn Bản</TableHead>
                <TableHead className="w-32 text-xs">Trạng Thái</TableHead>
                <TableHead className="w-28 text-right text-xs">
                  Dung Lượng
                </TableHead>
                <TableHead className="w-32 text-xs">Ngày Thêm</TableHead>
                <TableHead className="w-24 text-right text-xs">
                  Thao Tác
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.map((doc) => (
                <TableRow key={doc.id} className="h-11 hover:bg-muted/40">
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="flex size-7 shrink-0 items-center justify-center rounded bg-muted/60">
                        {getFileIcon(doc.file_type)}
                      </div>
                      <div className="min-w-0">
                        <Link
                          to="/documents/$documentId"
                          params={{ documentId: doc.id }}
                          className="font-medium text-xs sm:text-sm text-foreground hover:text-primary transition-colors truncate block max-w-md"
                        >
                          {doc.title || doc.file_name}
                        </Link>
                        <span className="text-[11px] text-muted-foreground truncate block">
                          {doc.file_name}
                        </span>
                      </div>
                    </div>
                  </TableCell>

                  <TableCell className="text-xs text-muted-foreground">
                    {doc.document_type_code || doc.file_type.toUpperCase()}
                  </TableCell>

                  <TableCell>
                    {getRevisionStatusBadge(doc.revision_status)}
                  </TableCell>

                  <TableCell className="text-right text-xs text-muted-foreground">
                    {formatFileSize(doc.file_size_bytes)}
                  </TableCell>

                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(doc.added_at).toLocaleDateString("vi-VN")}
                  </TableCell>

                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setRemovingDoc(doc)}
                      title="Gỡ khỏi kho (bảo toàn tài liệu gốc)"
                      className="size-8 text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* 6. Upload Documents Directly Into Group Modal */}
      <DocumentUploadModal
        open={isUploadModalOpen}
        onOpenChange={setIsUploadModalOpen}
        groupId={group.id}
        groupName={group.name}
        onSuccess={() => {
          queryClient.invalidateQueries({
            queryKey: ["group-documents", groupId],
          });
          queryClient.invalidateQueries({
            queryKey: ["document-group", groupId],
          });
          queryClient.invalidateQueries({ queryKey: ["document-groups"] });
        }}
      />

      {/* 7. Attach Group To Knowledge Dialog */}
      <AttachGroupToKnowledgeDialog
        open={isAttachModalOpen}
        onOpenChange={setIsAttachModalOpen}
        group={group}
      />

      {/* 8. Confirm Remove Document Dialog */}
      <ConfirmDialog
        open={Boolean(removingDoc)}
        onOpenChange={(open) => !open && setRemovingDoc(null)}
        title="Xác nhận gỡ tài liệu khỏi kho"
        description={
          removingDoc
            ? `Bạn có chắc chắn muốn gỡ tài liệu "${removingDoc.title || removingDoc.file_name}" khỏi kho này? Thao tác này chỉ xóa liên kết thành viên trong kho; tài liệu gốc vẫn được bảo toàn nguyên vẹn trong hệ thống và không ảnh hưởng đến bất kỳ snapshot Kho tri thức nào đã xuất bản trước đó.`
            : ""
        }
        confirmText="Gỡ khỏi kho"
        confirmVariant="destructive"
        onConfirm={() => removingDoc && removeMutation.mutate(removingDoc.id)}
        isPending={removeMutation.isPending}
      />
    </div>
  );
}
