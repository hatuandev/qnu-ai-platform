import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  CheckCircle2,
  FileStack,
  HardDrive,
  Search,
  Upload,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import {
  type DocumentTypeItem,
  documentTypesApi,
} from "@/services/document-types-api";
import { documentsApi } from "@/services/documents-api";
import type { RepositoryDocumentListItem } from "@/types/documents";
import { DocumentCard } from "./components/document-card";
import { DocumentUploadModal } from "./components/document-upload-modal";
import { DocumentsTable } from "./components/documents-table";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [search, setSearch] = useState("");
  const [docTypeCode, setDocTypeCode] = useState<string>("all");
  const [fileType, setFileType] = useState<string>("all");
  const [parseStatus, setParseStatus] = useState<string>("all");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [deletingDoc, setDeletingDoc] =
    useState<RepositoryDocumentListItem | null>(null);

  // 1. Fetch KPI Stats
  const { data: stats } = useQuery({
    queryKey: ["repository-stats"],
    queryFn: () => documentsApi.getStats(),
  });

  // 2. Fetch Document Types for filter
  const { data: documentTypes = [] } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentTypesApi.listDocumentTypes(),
  });

  // 3. Fetch Documents List
  const { data: documentsData, isLoading } = useQuery({
    queryKey: [
      "repository-documents",
      search,
      docTypeCode,
      fileType,
      parseStatus,
    ],
    queryFn: () =>
      documentsApi.getDocuments({
        search: search.trim() || undefined,
        document_type_code: docTypeCode !== "all" ? docTypeCode : undefined,
        file_type: fileType !== "all" ? fileType : undefined,
        parse_status: parseStatus !== "all" ? parseStatus : undefined,
        limit: 100,
      }),
  });

  const documents = useMemo(
    () => documentsData?.items ?? [],
    [documentsData?.items],
  );

  // Reparse mutation
  const reparseMutation = useMutation({
    mutationFn: (id: string) => documentsApi.reparseDocument(id),
    onSuccess: (data) => {
      toast.success(`Đã bóc tách lại thành công: ${data.file_name}`);
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Bóc tách lại tài liệu thất bại.");
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.deleteDocument(id),
    onSuccess: () => {
      toast.success("Đã xóa tài liệu khỏi kho tập trung.");
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
      queryClient.invalidateQueries({ queryKey: ["repository-stats"] });
      setDeletingDoc(null);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Xóa tài liệu thất bại.");
    },
  });

  // Selection handlers
  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
  };

  const handleToggleSelectAll = () => {
    if (selectedIds.length === documents.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(documents.map((d) => d.id));
    }
  };

  return (
    <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* 1. Page Header */}
      <PageHeader
        title="Kho Tài Liệu Tập Trung"
        description="Lưu trữ tài sản số trên MinIO S3, chống trùng lặp SHA-256, tiền xử lý Markdown sạch và gắn động vào các Kho Tri Thức."
        actions={
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setIsUploadOpen(true)}
              className="gap-1.5 shadow-sm"
            >
              <Upload className="size-4" />
              Tải Lên Tài Liệu
            </Button>
          </div>
        }
      />

      {/* 2. KPI Metrics Banner */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-4">
        <KpiMetric
          label="Tổng Tài Liệu"
          value={String(stats?.total_documents ?? 0)}
          icon={FileStack}
          helper="Tệp văn bản đã lưu trữ"
        />
        <KpiMetric
          label="Đã Bóc Tách MD"
          value={String(stats?.parsed_documents ?? 0)}
          icon={CheckCircle2}
          helper="Sẵn sàng nạp vào Vector DB"
        />
        <KpiMetric
          label="Dung Lượng MinIO"
          value={formatFileSize(stats?.total_size_bytes ?? 0)}
          icon={HardDrive}
          helper="Lưu trữ S3 phi cấu trúc"
        />
        <KpiMetric
          label="Liên Kết Kho Tri Thức"
          value={String(stats?.attached_usages_count ?? 0)}
          icon={BookOpen}
          helper="Tổng lượt gắn vào RAG Collections"
        />
      </div>

      {/* 3. Toolbar: Search + Filters + ViewModeToggle */}
      <div className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card p-3 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
            <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Tìm theo tên tệp, số hiệu, trích yếu..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-9"
            />
          </div>

          {/* Filter Document Type */}
          <Select value={docTypeCode} onValueChange={setDocTypeCode}>
            <SelectTrigger className="w-[160px] h-9 text-xs">
              <SelectValue placeholder="Loại văn bản" />
            </SelectTrigger>
            <SelectContent className="max-h-56">
              <SelectItem value="all">Tất cả loại VB</SelectItem>
              {documentTypes.map((dt: DocumentTypeItem) => (
                <SelectItem key={dt.code} value={dt.code}>
                  {dt.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Filter File Type */}
          <Select value={fileType} onValueChange={setFileType}>
            <SelectTrigger className="w-[120px] h-9 text-xs">
              <SelectValue placeholder="Định dạng" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả định dạng</SelectItem>
              <SelectItem value="pdf">PDF (.pdf)</SelectItem>
              <SelectItem value="docx">Word (.docx)</SelectItem>
              <SelectItem value="xlsx">Excel (.xlsx)</SelectItem>
              <SelectItem value="md">Markdown (.md)</SelectItem>
              <SelectItem value="txt">Văn bản (.txt)</SelectItem>
            </SelectContent>
          </Select>

          {/* Filter Parse Status */}
          <Select value={parseStatus} onValueChange={setParseStatus}>
            <SelectTrigger className="w-[140px] h-9 text-xs">
              <SelectValue placeholder="Trạng thái MD" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              <SelectItem value="parsed">Đã bóc tách MD</SelectItem>
              <SelectItem value="parsing">Đang bóc tách</SelectItem>
              <SelectItem value="failed">Lỗi bóc tách</SelectItem>
              <SelectItem value="pending">Chờ xử lý</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-2 self-end sm:self-center">
          <ViewModeToggle value={viewMode} onChange={setViewMode} />
        </div>
      </div>

      {/* 4. Content Area: Grid / Table / Empty */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            "doc-sk-1",
            "doc-sk-2",
            "doc-sk-3",
            "doc-sk-4",
            "doc-sk-5",
            "doc-sk-6",
          ].map((skKey) => (
            <div
              key={skKey}
              className="h-44 rounded-lg border border-border/50 bg-muted/20 animate-pulse"
            />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileStack}
          title="Không tìm thấy tài liệu nào trong kho"
          description={
            search ||
            docTypeCode !== "all" ||
            fileType !== "all" ||
            parseStatus !== "all"
              ? "Không có tài liệu nào khớp với các bộ lọc đã chọn. Hãy thử xóa bớt bộ lọc."
              : "Kho tài liệu tập trung đang trống. Hãy bắt đầu bằng cách tải lên các tài liệu quy chế, thông báo hoặc biểu mẫu."
          }
          action={{
            label: "Tải Lên Tài Liệu Đầu Tiên",
            onClick: () => setIsUploadOpen(true),
          }}
        />
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onReparse={(d) => reparseMutation.mutate(d.id)}
              onDelete={(d) => setDeletingDoc(d)}
            />
          ))}
        </div>
      ) : (
        <DocumentsTable
          documents={documents}
          selectedIds={selectedIds}
          onToggleSelect={handleToggleSelect}
          onToggleSelectAll={handleToggleSelectAll}
          onReparse={(d) => reparseMutation.mutate(d.id)}
          onDelete={(d) => setDeletingDoc(d)}
        />
      )}

      {/* 5. Modals & Dialogs */}
      <DocumentUploadModal open={isUploadOpen} onOpenChange={setIsUploadOpen} />

      <ConfirmDialog
        open={Boolean(deletingDoc)}
        onOpenChange={(open) => !open && setDeletingDoc(null)}
        title="Xác nhận xóa tài liệu khỏi kho tập trung"
        description={
          deletingDoc
            ? deletingDoc.attached_collections_count > 0
              ? `Tài liệu "${deletingDoc.title || deletingDoc.file_name}" đang được liên kết trong ${deletingDoc.attached_collections_count} Kho Tri Thức. Bạn có chắc chắn muốn xóa không?`
              : `Bạn có chắc chắn muốn xóa tài liệu "${deletingDoc.title || deletingDoc.file_name}" khỏi kho không?`
            : ""
        }
        confirmText="Xóa Tài Liệu"
        confirmVariant="destructive"
        onConfirm={() => deletingDoc && deleteMutation.mutate(deletingDoc.id)}
        isPending={deleteMutation.isPending}
      />
    </div>
  );
}
