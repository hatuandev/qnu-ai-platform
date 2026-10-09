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
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import { documentsApi } from "@/services/documents-api";
import type { GroupDocumentItem } from "@/types/documents";
import { AttachGroupToKnowledgeDialog } from "./components/attach-group-to-knowledge-dialog";
import { SelectDocumentsForGroupModal } from "./components/select-documents-for-group-modal";

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

export function DocumentGroupDetailPage({ groupId }: DocumentGroupDetailPageProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState<"grid" | "table">("table");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isAttachDialogOpen, setIsAttachDialogOpen] = useState(false);
  const [removingDoc, setRemovingDoc] = useState<GroupDocumentItem | null>(null);

  // 1. Fetch Group Details
  const { data: group, isLoading: isLoadingGroup } = useQuery({
    queryKey: ["document-group", groupId],
    queryFn: () => documentsApi.getGroup(groupId),
  });

  // 2. Fetch Group Documents
  const { data: groupDocsData, isLoading: isLoadingDocs } = useQuery({
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
      toast.success("Đã xóa tài liệu khỏi nhóm (tài liệu gốc vẫn được bảo toàn).");
      queryClient.invalidateQueries({ queryKey: ["group-documents", groupId] });
      queryClient.invalidateQueries({ queryKey: ["document-group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      setRemovingDoc(null);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Xóa tài liệu khỏi nhóm thất bại.");
    },
  });

  if (isLoadingGroup) {
    return (
      <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="h-8 w-48 rounded bg-muted/30 animate-pulse" />
        <div className="h-28 rounded-lg bg-muted/20 animate-pulse" />
      </div>
    );
  }

  if (!group) {
    return (
      <div className="flex-1 p-8 max-w-7xl mx-auto">
        <EmptyState
          icon={AlertCircle}
          title="Không tìm thấy nhóm tài liệu"
          description={`Nhóm tài liệu ID '${groupId}' không tồn tại hoặc bạn không có quyền truy cập.`}
          action={{
            label: "Quay Lại Danh Sách Nhóm",
            onClick: () => navigate({ to: "/documents/groups" }),
          }}
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
          onClick={() => navigate({ to: "/documents/groups" })}
          className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Về Danh Sách Nhóm
        </Button>
        <span>/</span>
        <Link to="/documents" className="hover:text-foreground">
          Kho Tài Liệu
        </Link>
        <span>/</span>
        <Link to="/documents/groups" className="hover:text-foreground">
          Nhóm Tài Liệu
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
              Cập nhật lần cuối: {new Date(group.updated_at).toLocaleString("vi-VN")}
            </div>
          </div>
        </div>

        {/* Action Toolbar */}
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-center">
          <Button
            variant="outline"
            onClick={() => setIsAddModalOpen(true)}
            className="gap-1.5 h-9 text-xs"
          >
            <Plus className="size-4" />
            Thêm Tài Liệu
          </Button>
          <Button
            onClick={() => setIsAttachDialogOpen(true)}
            className="gap-1.5 h-9 text-xs shadow-sm"
          >
            <BookOpen className="size-4" />
            Đưa Vào Kho Tri Thức
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
              placeholder="Tìm kiếm tài liệu trong nhóm..."
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
              <SelectItem value="error">Lỗi bóc tách</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-2 self-end sm:self-center">
          <ViewModeToggle value={viewMode} onChange={setViewMode} />
        </div>
      </div>

      {/* 5. Document List: Grid or Table */}
      {isLoadingDocs ? (
        <div className="h-64 rounded-lg border border-border/50 bg-muted/20 animate-pulse" />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileStack}
          title="Nhóm tài liệu chưa có văn bản nào"
          description={
            search || statusFilter !== "all"
              ? "Không có tài liệu nào khớp với bộ lọc."
              : "Hãy thêm các tài liệu từ Kho Tài Liệu vào nhóm để chuẩn bị đưa vào Kho Tri Thức."
          }
          action={{
            label: "Thêm Tài Liệu Vào Nhóm",
            onClick: () => setIsAddModalOpen(true),
          }}
        />
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => (
            <Card key={doc.id} className="flex flex-col justify-between hover:border-primary/40 transition-all">
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
                  <Badge
                    variant={
                      doc.revision_status === "ready"
                        ? "default"
                        : doc.revision_status === "failed" || doc.revision_status === "rejected"
                          ? "destructive"
                          : "outline"
                    }
                    className="text-[10px] shrink-0"
                  >
                    {doc.revision_status === "ready"
                      ? "Ready"
                      : doc.revision_status === "failed" || doc.revision_status === "rejected"
                        ? "Lỗi"
                        : "Processing"}
                  </Badge>
                </div>
                <div className="text-[11px] text-muted-foreground truncate mt-1">
                  {doc.file_name}
                </div>
              </CardHeader>

              <CardContent className="space-y-1 text-[11px] text-muted-foreground py-1">
                <div>Dung lượng: {formatFileSize(doc.file_size_bytes)}</div>
                <div>Ngày thêm: {new Date(doc.added_at).toLocaleDateString("vi-VN")}</div>
              </CardContent>

              <CardFooter className="flex items-center justify-between border-t border-border/60 pt-2.5">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRemovingDoc(doc)}
                  className="h-7 text-xs text-muted-foreground hover:text-destructive gap-1 px-2"
                >
                  <X className="size-3.5" />
                  Gỡ khỏi nhóm
                </Button>

                <Button asChild size="sm" variant="ghost" className="h-7 text-xs gap-1 px-2">
                  <Link to="/documents/$documentId" params={{ documentId: doc.id }}>
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
                <TableHead className="w-32 text-xs">Trạng Thái Revision</TableHead>
                <TableHead className="w-28 text-right text-xs">Dung Lượng</TableHead>
                <TableHead className="w-32 text-xs">Ngày Thêm Vào Nhóm</TableHead>
                <TableHead className="w-24 text-right text-xs">Thao Tác</TableHead>
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
                    <Badge
                      variant={
                        doc.revision_status === "ready"
                          ? "default"
                          : doc.revision_status === "failed" || doc.revision_status === "rejected"
                            ? "destructive"
                            : "outline"
                      }
                      className="text-[10px]"
                    >
                      {doc.revision_status === "ready"
                        ? "Ready"
                        : doc.revision_status === "failed" || doc.revision_status === "rejected"
                          ? "Lỗi"
                          : "Processing"}
                    </Badge>
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
                      title="Gỡ khỏi nhóm (bảo toàn tài liệu gốc)"
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

      {/* 6. Select Documents Modal */}
      <SelectDocumentsForGroupModal
        open={isAddModalOpen}
        onOpenChange={setIsAddModalOpen}
        groupId={group.id}
      />

      {/* 7. Attach Group To Knowledge Dialog */}
      <AttachGroupToKnowledgeDialog
        open={isAttachDialogOpen}
        onOpenChange={setIsAttachDialogOpen}
        group={group}
      />

      {/* 8. Confirm Remove Document Dialog */}
      <ConfirmDialog
        open={Boolean(removingDoc)}
        onOpenChange={(open) => !open && setRemovingDoc(null)}
        title="Xác nhận gỡ tài liệu khỏi nhóm"
        description={
          removingDoc
            ? `Bạn có chắc chắn muốn gỡ tài liệu "${removingDoc.title || removingDoc.file_name}" khỏi nhóm này? Thao tác này KHÔNG xóa tài liệu gốc khỏi Kho Tài Liệu và không ảnh hưởng đến các liên kết tri thức đã tạo.`
            : ""
        }
        confirmText="Gỡ Khỏi Nhóm"
        confirmVariant="destructive"
        onConfirm={() => removingDoc && removeMutation.mutate(removingDoc.id)}
        isPending={removeMutation.isPending}
      />
    </div>
  );
}
