import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  CheckCircle2,
  FileCode,
  FileSpreadsheet,
  FileStack,
  FileText,
  Loader2,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import { documentsApi } from "@/services/documents-api";

interface AttachFromRepositoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collectionId: string;
  collectionName?: string;
  existingDocumentRepoIds?: string[];
  onSuccess?: () => void;
}

function getFileIcon(fileType: string) {
  switch (fileType.toLowerCase()) {
    case "pdf":
      return <FileText className="size-4 text-red-500" />;
    case "xlsx":
    case "xls":
      return <FileSpreadsheet className="size-4 text-emerald-600" />;
    case "md":
    case "txt":
      return <FileCode className="size-4 text-sky-500" />;
    default:
      return <FileText className="size-4 text-primary" />;
  }
}

export function AttachFromRepositoryDialog({
  open,
  onOpenChange,
  collectionId,
  collectionName,
  existingDocumentRepoIds = [],
  onSuccess,
}: AttachFromRepositoryDialogProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [autoApprove, setAutoApprove] = useState(true);

  // Fetch all documents from Central Repository
  const { data: repoDocsData, isLoading } = useQuery({
    queryKey: ["repository-documents-attach-modal", search],
    queryFn: () =>
      documentsApi.getDocuments({
        search: search.trim() || undefined,
        limit: 100,
      }),
    enabled: open,
  });

  const documents = useMemo(
    () => repoDocsData?.items ?? [],
    [repoDocsData?.items],
  );

  const attachMutation = useMutation({
    mutationFn: () =>
      documentsApi.attachToCollection(collectionId, {
        document_ids: selectedIds,
        auto_approve: autoApprove,
      }),
    onSuccess: (res) => {
      toast.success(
        res.message ||
          `Đã gắn thành công ${res.attached_count} tài liệu vào kho tri thức!`,
      );
      queryClient.invalidateQueries({
        queryKey: ["collection-documents", collectionId],
      });
      queryClient.invalidateQueries({ queryKey: ["collection", collectionId] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
      queryClient.invalidateQueries({ queryKey: ["repository-stats"] });
      setSelectedIds([]);
      onOpenChange(false);
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Gắn tài liệu từ kho thất bại.");
    },
  });

  const handleToggle = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
  };

  const handleSelectAll = () => {
    const selectable = documents.filter(
      (d) => !existingDocumentRepoIds.includes(d.id),
    );
    if (selectedIds.length === selectable.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(selectable.map((d) => d.id));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FileStack className="size-5" />
            </div>
            <div>
              <DialogTitle>Gắn Tài Liệu Từ Kho Tập Trung</DialogTitle>
              <DialogDescription>
                Chọn các tài liệu đã bóc tách sẵn để nạp vào Bộ Sưu Tập{" "}
                <strong className="text-foreground">
                  {collectionName || collectionId}
                </strong>{" "}
                mà không cần chạy lại OCR.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Toolbar: Search input */}
        <div className="relative my-2">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Tìm theo tên tệp, số hiệu, trích yếu văn bản..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-9 text-xs"
          />
        </div>

        {/* Table of selectable documents */}
        <div className="max-h-[360px] overflow-y-auto rounded-lg border border-border/70 bg-card">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-muted-foreground">
              <Loader2 className="size-5 animate-spin text-primary" />
              <span className="text-xs">Đang tải danh sách tài liệu...</span>
            </div>
          ) : documents.length === 0 ? (
            <div className="py-8">
              <EmptyState
                icon={FileStack}
                title="Không có tài liệu nào"
                description="Kho tài liệu tập trung chưa có tệp nào phù hợp."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent text-xs">
                  <TableHead className="w-10">
                    <Checkbox
                      checked={
                        selectedIds.length > 0 &&
                        selectedIds.length ===
                          documents.filter(
                            (d) => !existingDocumentRepoIds.includes(d.id),
                          ).length
                      }
                      onCheckedChange={handleSelectAll}
                    />
                  </TableHead>
                  <TableHead>Tài Liệu</TableHead>
                  <TableHead className="w-32">Số Hiệu / Loại</TableHead>
                  <TableHead className="w-28 text-center">
                    Trạng Thái MD
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => {
                  const isAlreadyAttached = existingDocumentRepoIds.includes(
                    doc.id,
                  );
                  const isChecked = selectedIds.includes(doc.id);

                  return (
                    <TableRow
                      key={doc.id}
                      className={`h-11 transition-colors ${
                        isAlreadyAttached
                          ? "opacity-50 bg-muted/20"
                          : "hover:bg-muted/40 cursor-pointer"
                      }`}
                      onClick={() => {
                        if (!isAlreadyAttached) handleToggle(doc.id);
                      }}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          checked={isChecked || isAlreadyAttached}
                          disabled={isAlreadyAttached}
                          onCheckedChange={() => handleToggle(doc.id)}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 min-w-0">
                          {getFileIcon(doc.file_type)}
                          <div className="min-w-0">
                            <span className="font-medium text-xs text-foreground truncate block">
                              {doc.title || doc.file_name}
                            </span>
                            <span className="text-[11px] text-muted-foreground truncate block">
                              {doc.file_name}
                            </span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs">
                        <span className="font-mono text-muted-foreground block truncate">
                          {doc.document_number || "—"}
                        </span>
                        {doc.document_type_name && (
                          <span className="text-[10px] text-primary truncate block font-medium">
                            {doc.document_type_name}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {isAlreadyAttached ? (
                          <Badge
                            variant="secondary"
                            className="text-[10px] py-0 h-4"
                          >
                            Đã Trong Kho
                          </Badge>
                        ) : doc.parse_status === "parsed" ? (
                          <Badge
                            variant="outline"
                            className="gap-1 text-[10px] py-0 h-4 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                          >
                            <CheckCircle2 className="size-2.5" />
                            Sẵn Sàng
                          </Badge>
                        ) : (
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 h-4"
                          >
                            {doc.parse_status}
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>

        {/* Auto approve check */}
        <div className="flex items-center space-x-2 rounded-md border border-border/60 bg-muted/20 p-2.5">
          <Checkbox
            id="auto-approve-attach"
            checked={autoApprove}
            onCheckedChange={(c) => setAutoApprove(Boolean(c))}
          />
          <label
            htmlFor="auto-approve-attach"
            className="text-xs text-foreground cursor-pointer select-none"
          >
            <span className="font-semibold text-primary">
              Tự động duyệt và lập chỉ mục Vector tức thì
            </span>
            <span className="text-muted-foreground block text-[11px]">
              Tự động cắt chunk và nạp vào Qdrant để trợ lý AI tra cứu ngay.
            </span>
          </label>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={attachMutation.isPending}
          >
            Hủy Bỏ
          </Button>
          <Button
            onClick={() => attachMutation.mutate()}
            disabled={attachMutation.isPending || selectedIds.length === 0}
            className="gap-1.5"
          >
            {attachMutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Đang Gắn Dữ Liệu...
              </>
            ) : (
              <>
                <Check className="size-4" />
                Gắn {selectedIds.length} Tài Liệu Vào Kho
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
