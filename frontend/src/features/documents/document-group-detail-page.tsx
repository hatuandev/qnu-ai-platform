import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  ArrowUpRight,
  Calendar,
  FileCode,
  FileSpreadsheet,
  FileStack,
  FileText,
  FolderOpen,
  Hash,
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
import { DocumentUploadModal } from "./components/document-upload-modal";

interface DocumentGroupDetailPageProps {
  groupId: string;
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
  const [fileTypeFilter, setFileTypeFilter] = useState<string>("all");
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
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
    queryKey: ["group-documents", groupId, search],
    queryFn: () =>
      documentsApi.getGroupDocuments(groupId, {
        search: search.trim() || undefined,
        page_size: 100,
      }),
  });

  const rawDocuments = groupDocsData?.items ?? [];
  const documents =
    fileTypeFilter === "all"
      ? rawDocuments
      : rawDocuments.filter((d) => d.file_type.toLowerCase() === fileTypeFilter);

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
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
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

        {/* Action Toolbar: Tải lên */}
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-center">
          <Button
            onClick={() => setIsUploadModalOpen(true)}
            className="gap-1.5 h-9 text-xs shadow-sm bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            <Upload className="size-4" />
            Tải Lên Tệp Mới
          </Button>
        </div>
      </div>

      {/* 3. KPI Bento Grid (Storage Domain) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 lg:gap-4">
        <KpiMetric
          label="Tổng Tài Liệu Trong Kho"
          value={String(group.total_documents)}
          icon={FileStack}
        />
        <KpiMetric
          label="Định Dạng Tệp"
          value={String(new Set(rawDocuments.map((d) => d.file_type)).size || "0")}
          icon={FileText}
        />
        <KpiMetric
          label="Cập Nhật Lần Cuối"
          value={new Date(group.updated_at).toLocaleDateString("vi-VN")}
          icon={Calendar}
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

          {/* File Type Filter */}
          <Select value={fileTypeFilter} onValueChange={setFileTypeFilter}>
            <SelectTrigger className="w-[140px] h-9 text-xs">
              <SelectValue placeholder="Định dạng tệp" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả định dạng</SelectItem>
              <SelectItem value="pdf">PDF (.pdf)</SelectItem>
              <SelectItem value="docx">Word (.docx)</SelectItem>
              <SelectItem value="xlsx">Excel (.xlsx)</SelectItem>
              <SelectItem value="txt">Văn bản (.txt)</SelectItem>
              <SelectItem value="md">Markdown (.md)</SelectItem>
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
            search || fileTypeFilter !== "all"
              ? "Không có tài liệu nào khớp với bộ lọc."
              : "Hãy bắt đầu bằng cách tải lên các tài liệu vào kho này."
          }
          action={{
            label: "Tải Lên Tệp Đầu Tiên",
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
                  <Badge variant="outline" className="text-[10px] uppercase font-mono">
                    .{doc.file_type}
                  </Badge>
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
                <TableHead className="w-40 text-xs">Số Hiệu & Phân Loại</TableHead>
                <TableHead className="w-24 text-center text-xs">Định Dạng</TableHead>
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

                  <TableCell className="text-xs">
                    {doc.document_number ? (
                      <div className="flex items-center gap-1 font-mono text-foreground">
                        <Hash className="size-3 text-muted-foreground" />
                        <span>{doc.document_number}</span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground italic">Chưa có số</span>
                    )}
                  </TableCell>

                  <TableCell className="text-center font-mono text-xs uppercase text-muted-foreground">
                    .{doc.file_type}
                  </TableCell>

                  <TableCell className="text-right text-xs font-mono text-muted-foreground">
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

      {/* 7. Confirm Remove Document Dialog */}
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
