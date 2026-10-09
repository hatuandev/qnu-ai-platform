import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  FileStack,
  FolderOpen,
  FolderPlus,
  Folders,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { documentsApi } from "@/services/documents-api";
import type { DocumentGroup, DocumentGroupListItem } from "@/types/documents";

export function DocumentGroupsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<DocumentGroup | null>(null);
  const [deletingGroup, setDeletingGroup] = useState<DocumentGroupListItem | null>(null);

  // Form states
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");

  // Fetch groups
  const { data: groupsData, isLoading } = useQuery({
    queryKey: ["document-groups", search],
    queryFn: () =>
      documentsApi.getGroups({
        search: search.trim() || undefined,
        page_size: 100,
      }),
  });

  const groups = groupsData?.items ?? [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: () => {
      if (!name.trim()) throw new Error("Vui lòng nhập tên nhóm.");
      return documentsApi.createGroup({
        name: name.trim(),
        description: desc.trim() || undefined,
      });
    },
    onSuccess: (newGrp) => {
      toast.success(`Đã tạo nhóm tài liệu "${newGrp.name}" thành công.`);
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      setIsCreateOpen(false);
      setName("");
      setDesc("");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Tạo nhóm tài liệu thất bại.");
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: () => {
      if (!editingGroup) throw new Error("Không có nhóm để cập nhật.");
      if (!name.trim()) throw new Error("Tên nhóm không được để trống.");
      return documentsApi.updateGroup(editingGroup.id, {
        name: name.trim(),
        description: desc.trim() || undefined,
        expected_lock_version: editingGroup.lock_version,
      });
    },
    onSuccess: (updated) => {
      toast.success(`Đã cập nhật nhóm "${updated.name}".`);
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      setEditingGroup(null);
      setName("");
      setDesc("");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Cập nhật nhóm thất bại.");
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.deleteGroup(id),
    onSuccess: () => {
      toast.success("Đã xóa nhóm tài liệu (các tài liệu gốc vẫn an toàn).");
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
      setDeletingGroup(null);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Xóa nhóm tài liệu thất bại.");
    },
  });

  const openEdit = (g: DocumentGroupListItem) => {
    setEditingGroup(g);
    setName(g.name);
    setDesc(g.description || "");
  };

  const isFiltered = Boolean(search.trim());
  const totalGroups = groupsData?.total ?? groups.length;
  const totalDocsInGroups = groups.reduce((acc, g) => acc + g.total_documents, 0);
  const totalReadyDocsInGroups = groups.reduce((acc, g) => acc + g.ready_documents, 0);
  const totalProcessingDocsInGroups = groups.reduce((acc, g) => acc + g.processing_documents, 0);

  return (
    <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* 1. Header & Navigation */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate({ to: "/documents" })}
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            Về Kho Tài Liệu
          </Button>
        </div>

        <PageHeader
          title="Nhóm Tài Liệu"
          description="Gom nhóm logic nhiều tài liệu trong kho để quản trị nghiệp vụ tập trung và đưa nhanh toàn bộ nhóm vào Kho Tri Thức."
          actions={
            <Button
              onClick={() => {
                setName("");
                setDesc("");
                setIsCreateOpen(true);
              }}
              className="gap-1.5 shadow-sm"
            >
              <Plus className="size-4" />
              Tạo Nhóm Tài Liệu
            </Button>
          }
        />
      </div>

      {/* 2. KPI Metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-4">
        <KpiMetric
          label={isFiltered ? "Nhóm Tìm Thấy" : "Tổng Nhóm Tài Liệu"}
          value={String(totalGroups)}
          icon={Folders}
        />
        <KpiMetric
          label={isFiltered ? "Tài Liệu (Trong kết quả)" : "Tổng Tài Liệu Trong Nhóm"}
          value={String(totalDocsInGroups)}
          icon={FileStack}
        />
        <KpiMetric
          label={isFiltered ? "Sẵn Sàng (Trong kết quả)" : "Sẵn Sàng Đưa Vào Kho"}
          value={String(totalReadyDocsInGroups)}
          icon={CheckCircle2}
        />
        <KpiMetric
          label={isFiltered ? "Đang Xử Lý (Trong kết quả)" : "Đang Xử Lý Bóc Tách"}
          value={String(totalProcessingDocsInGroups)}
          icon={Clock}
        />
      </div>

      {/* 3. Seamless Search Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative min-w-[240px] flex-1 sm:max-w-md">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Tìm theo tên hoặc mô tả nhóm tài liệu..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-9"
          />
        </div>
        <div className="text-xs text-muted-foreground">
          Hiển thị {groups.length} nhóm
        </div>
      </div>

      {/* 4. Content Area: Cards Grid or Empty */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {["sk-grp-1", "sk-grp-2", "sk-grp-3"].map((key) => (
            <div
              key={key}
              className="h-48 rounded-lg border border-border/50 bg-muted/20 animate-pulse"
            />
          ))}
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          icon={Folders}
          title="Chưa có nhóm tài liệu nào"
          description={
            search
              ? "Không tìm thấy nhóm tài liệu nào khớp với từ khóa tìm kiếm."
              : "Bạn có thể gom nhiều tài liệu theo từng nghiệp vụ (ví dụ: Tuyển sinh 2026, Quy chế tài chính) để quản lý tập trung và đưa vào kho tri thức một lần."
          }
          action={{
            label: "Tạo Nhóm Đầu Tiên",
            onClick: () => {
              setName("");
              setDesc("");
              setIsCreateOpen(true);
            },
          }}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {groups.map((grp) => (
            <Card
              key={grp.id}
              className="flex flex-col justify-between hover:border-primary/40 hover:shadow-xs transition-all"
            >
              <CardHeader className="pb-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <FolderOpen className="size-4" />
                    </div>
                    <CardTitle className="text-base font-semibold leading-tight text-foreground line-clamp-1">
                      {grp.name}
                    </CardTitle>
                  </div>
                  <Badge variant="outline" className="text-[11px] shrink-0 font-normal">
                    {grp.total_documents} tài liệu
                  </Badge>
                </div>
                {grp.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                    {grp.description}
                  </p>
                )}
              </CardHeader>

              <CardContent className="space-y-3 py-2 text-xs">
                {/* Status Breakdown Chips */}
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded bg-success/10 px-2 py-0.5 text-[11px] font-medium text-success">
                    <CheckCircle2 className="size-3" />
                    {grp.ready_documents} ready
                  </span>
                  {grp.processing_documents > 0 && (
                  <span className="inline-flex items-center gap-1 rounded bg-warning/10 px-2 py-0.5 text-[11px] font-medium text-warning">
                      <Clock className="size-3" />
                      {grp.processing_documents} đang xử lý
                    </span>
                  )}
                  {grp.error_documents > 0 && (
                    <span className="inline-flex items-center gap-1 rounded bg-destructive/10 px-2 py-0.5 text-[11px] font-medium text-destructive">
                      {grp.error_documents} lỗi
                    </span>
                  )}
                </div>

                <div className="text-[11px] text-muted-foreground">
                  Cập nhật: {new Date(grp.updated_at).toLocaleDateString("vi-VN")}
                </div>
              </CardContent>

              <CardFooter className="flex items-center justify-between border-t border-border/60 pt-3">
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => openEdit(grp)}
                    title="Chỉnh sửa thông tin nhóm"
                    className="size-8 text-muted-foreground hover:text-foreground"
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setDeletingGroup(grp)}
                    title="Xóa nhóm"
                    className="size-8 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>

                <Button asChild size="sm" variant="outline" className="h-8 gap-1 text-xs">
                  <Link
                    to="/documents/groups/$groupId"
                    params={{ groupId: grp.id }}
                  >
                    <span>Mở Nhóm</span>
                    <ArrowUpRight className="size-3.5" />
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* 5. Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <FolderPlus className="size-5" />
              </div>
              <div>
                <DialogTitle>Tạo Nhóm Tài Liệu Mới</DialogTitle>
                <DialogDescription>
                  Gom nhóm logic phục vụ phân loại và đưa vào Kho Tri Thức.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <label htmlFor="create-group-name" className="text-xs font-medium text-foreground">
                Tên nhóm <span className="text-destructive">*</span>
              </label>
              <Input
                id="create-group-name"
                placeholder="Ví dụ: Đề án Tuyển sinh 2026, Quy chế thi đua..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-9 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="create-group-desc" className="text-xs font-medium text-foreground">
                Mô tả nhóm
              </label>
              <Textarea
                id="create-group-desc"
                placeholder="Ghi chú mục đích hoặc phạm vi của nhóm tài liệu..."
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                rows={3}
                className="text-sm resize-none"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsCreateOpen(false)}
              disabled={createMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="button"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !name.trim()}
              className="gap-1.5"
            >
              <Plus className="size-4" />
              {createMutation.isPending ? "Đang tạo..." : "Tạo Nhóm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 6. Edit Dialog */}
      <Dialog
        open={Boolean(editingGroup)}
        onOpenChange={(open) => !open && setEditingGroup(null)}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Chỉnh Sửa Nhóm Tài Liệu</DialogTitle>
            <DialogDescription>
              Cập nhật tên hoặc mô tả của nhóm tài liệu.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <label htmlFor="edit-group-name" className="text-xs font-medium text-foreground">
                Tên nhóm <span className="text-destructive">*</span>
              </label>
              <Input
                id="edit-group-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-9 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="edit-group-desc" className="text-xs font-medium text-foreground">
                Mô tả nhóm
              </label>
              <Textarea
                id="edit-group-desc"
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                rows={3}
                className="text-sm resize-none"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setEditingGroup(null)}
              disabled={updateMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="button"
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending || !name.trim()}
            >
              {updateMutation.isPending ? "Đang lưu..." : "Lưu Thay Đổi"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 7. Confirm Delete Dialog */}
      <ConfirmDialog
        open={Boolean(deletingGroup)}
        onOpenChange={(open) => !open && setDeletingGroup(null)}
        title="Xác nhận xóa nhóm tài liệu"
        description={
          deletingGroup
            ? `Bạn có chắc chắn muốn xóa nhóm "${deletingGroup.name}"? Thao tác này chỉ xóa phân loại nhóm; toàn bộ tài liệu gốc và các liên kết Kho Tri Thức đã tạo sẽ được bảo toàn nguyên vẹn.`
            : ""
        }
        confirmText="Xóa Nhóm"
        confirmVariant="destructive"
        onConfirm={() => deletingGroup && deleteMutation.mutate(deletingGroup.id)}
        isPending={deleteMutation.isPending}
      />
    </div>
  );
}
