import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckSquare, FileText, Plus, Search } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
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

interface SelectDocumentsForGroupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  groupId: string;
}

export function SelectDocumentsForGroupModal({
  open,
  onOpenChange,
  groupId,
}: SelectDocumentsForGroupModalProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Fetch documents from repository (server-side exclusion)
  const { data: documentsData, isLoading } = useQuery({
    queryKey: ["repository-documents-for-group-select", groupId, search],
    queryFn: () =>
      documentsApi.getDocuments({
        search: search.trim() || undefined,
        exclude_group_id: groupId,
        limit: 50,
      }),
    enabled: open,
  });

  const availableDocs = documentsData?.items ?? [];

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === availableDocs.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(availableDocs.map((d) => d.id));
    }
  };

  const addMutation = useMutation({
    mutationFn: () => {
      if (selectedIds.length === 0) {
        throw new Error("Vui lòng chọn ít nhất 1 tài liệu để thêm.");
      }
      return documentsApi.addDocumentsToGroup(groupId, {
        document_ids: selectedIds,
      });
    },
    onSuccess: (res) => {
      toast.success(
        `Đã thêm ${res.added_count} tài liệu vào nhóm (${res.skipped_existing_count} đã tồn tại).`,
      );
      queryClient.invalidateQueries({ queryKey: ["group-documents", groupId] });
      queryClient.invalidateQueries({ queryKey: ["document-group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      setSelectedIds([]);
      onOpenChange(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Thêm tài liệu vào nhóm thất bại.");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <CheckSquare className="size-5" />
            </div>
            <div>
              <DialogTitle>Thêm Tài Liệu Vào Nhóm</DialogTitle>
              <DialogDescription>
                Chọn các tài liệu từ Kho Tài Liệu để đưa vào nhóm quản lý này.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Search Toolbar */}
        <div className="relative py-2">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Tìm kiếm tài liệu theo tên, trích yếu, số hiệu..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-9 text-xs"
          />
        </div>

        {/* Table of available documents */}
        <div className="flex-1 overflow-y-auto rounded-md border border-border/70 min-h-[250px] max-h-[380px]">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              Đang tải danh sách tài liệu...
            </div>
          ) : availableDocs.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              {search
                ? "Không tìm thấy tài liệu phù hợp."
                : "Tất cả tài liệu trong kho đã có trong nhóm hoặc chưa có tài liệu nào."}
            </div>
          ) : (
            <Table>
              <TableHeader className="bg-muted/30 sticky top-0">
                <TableRow className="h-9">
                  <TableHead className="w-10">
                    <Checkbox
                      checked={
                        selectedIds.length > 0 &&
                        selectedIds.length === availableDocs.length
                      }
                      onCheckedChange={toggleSelectAll}
                      aria-label="Chọn tất cả"
                    />
                  </TableHead>
                  <TableHead className="text-xs">Tên Tài Liệu</TableHead>
                  <TableHead className="w-32 text-xs">Loại / Tệp</TableHead>
                  <TableHead className="w-28 text-xs">Trạng Thái MD</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {availableDocs.map((doc) => {
                  const isChecked = selectedIds.includes(doc.id);
                  return (
                    <TableRow
                      key={doc.id}
                      className="h-10 hover:bg-muted/40 cursor-pointer"
                      onClick={() => toggleSelect(doc.id)}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          checked={isChecked}
                          onCheckedChange={() => toggleSelect(doc.id)}
                          aria-label={`Chọn ${doc.title || doc.file_name}`}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <FileText className="size-4 shrink-0 text-muted-foreground" />
                          <div className="min-w-0">
                            <span className="font-medium text-xs text-foreground block truncate">
                              {doc.title || doc.file_name}
                            </span>
                            <span className="text-[11px] text-muted-foreground block truncate">
                              {doc.file_name}
                            </span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {doc.document_type_name || doc.file_type.toUpperCase()}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            doc.parse_status === "parsed"
                              ? "default"
                              : doc.parse_status === "failed"
                                ? "destructive"
                                : "outline"
                          }
                          className="text-[10px]"
                        >
                          {doc.parse_status === "parsed"
                            ? "Ready"
                            : doc.parse_status === "failed"
                              ? "Lỗi"
                              : "Đang xử lý"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>

        <DialogFooter className="flex items-center justify-between border-t border-border pt-3">
          <div className="text-xs text-muted-foreground">
            Đã chọn: <span className="font-semibold text-foreground">{selectedIds.length}</span> tài liệu
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={selectedIds.length === 0 || addMutation.isPending}
              onClick={() => addMutation.mutate()}
              className="gap-1.5"
            >
              <Plus className="size-4" />
              {addMutation.isPending ? "Đang thêm..." : `Thêm ${selectedIds.length} Tài Liệu`}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
