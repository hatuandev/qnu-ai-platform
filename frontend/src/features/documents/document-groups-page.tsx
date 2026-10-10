import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
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
import {
  Card,
  CardContent,
  CardFooter,
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
import { Textarea } from "@/components/ui/textarea";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import { documentsApi } from "@/services/documents-api";
import type { DocumentGroup, DocumentGroupListItem } from "@/types/documents";

export function DocumentGroupsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<DocumentGroup | null>(null);
  const [deletingGroup, setDeletingGroup] =
    useState<DocumentGroupListItem | null>(null);

  // Form states
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");

  // Fetch groups
  const {
    data: groupsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
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
      if (!name.trim()) throw new Error("Vui lòng nhập tên kho tài liệu.");
      return documentsApi.createGroup({
        name: name.trim(),
        description: desc.trim() || undefined,
      });
    },
    onSuccess: (newGrp) => {
      toast.success(`Đã tạo kho tài liệu "${newGrp.name}" thành công.`);
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      queryClient.invalidateQueries({ queryKey: ["repository-stats"] });
      setIsCreateOpen(false);
      setName("");
      setDesc("");
      // Không tự chuyển trang để tải lại data và hiển thị kho mới vừa tạo ra trên danh sách
    },
    onError: (err: Error) => {
      toast.error(err.message || "Tạo kho tài liệu thất bại.");
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: () => {
      if (!editingGroup) throw new Error("Không có kho tài liệu để cập nhật.");
      if (!name.trim())
        throw new Error("Tên kho tài liệu không được để trống.");
      return documentsApi.updateGroup(editingGroup.id, {
        name: name.trim(),
        description: desc.trim() || undefined,
        expected_lock_version: editingGroup.lock_version,
      });
    },
    onSuccess: (updated) => {
      toast.success(`Đã cập nhật kho tài liệu "${updated.name}".`);
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      setEditingGroup(null);
      setName("");
      setDesc("");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Cập nhật kho tài liệu thất bại.");
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.deleteGroup(id),
    onSuccess: () => {
      toast.success("Đã xóa kho tài liệu (các tài liệu gốc vẫn an toàn).");
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
      queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
      setDeletingGroup(null);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Xóa kho tài liệu thất bại.");
    },
  });

  const openEdit = (g: DocumentGroupListItem) => {
    setEditingGroup(g);
    setName(g.name);
    setDesc(g.description || "");
  };

  const isFiltered = Boolean(search.trim());
  const totalGroups = groupsData?.total ?? groups.length;
  const totalDocsInGroups = groups.reduce(
    (acc, g) => acc + g.total_documents,
    0,
  );
  const totalReadyDocsInGroups = groups.reduce(
    (acc, g) => acc + g.ready_documents,
    0,
  );
  const totalProcessingDocsInGroups = groups.reduce(
    (acc, g) => acc + g.processing_documents,
    0,
  );

  return (
    <div className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* 1. Header: Nút Thêm kho duy nhất */}
      <PageHeader
        title="Kho Tài Liệu"
        description="Quản lý và tổ chức các kho tài liệu số tập trung, lưu trữ trên MinIO S3, tiền xử lý Markdown sạch và gắn động vào các Kho Tri Thức."
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
            Thêm kho
          </Button>
        }
      />

      {/* 2. KPI Metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-4">
        <KpiMetric
          label={isFiltered ? "Kho Tìm Thấy" : "Tổng Kho Tài Liệu"}
          value={String(totalGroups)}
          icon={Folders}
        />
        <KpiMetric
          label={
            isFiltered ? "Tài Liệu (Trong kết quả)" : "Tổng Tài Liệu Trong Kho"
          }
          value={String(totalDocsInGroups)}
          icon={FileStack}
        />
        <KpiMetric
          label={
            isFiltered
              ? "Sẵn Sàng (Trong kết quả)"
              : "Sẵn Sàng Đưa Vào Kho Tri Thức"
          }
          value={String(totalReadyDocsInGroups)}
          icon={CheckCircle2}
        />
        <KpiMetric
          label={
            isFiltered ? "Đang Xử Lý (Trong kết quả)" : "Đang Xử Lý Bóc Tách"
          }
          value={String(totalProcessingDocsInGroups)}
          icon={Clock}
        />
      </div>

      {/* 3. Seamless Toolbar: Search + ViewModeToggle */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative min-w-[240px] flex-1 sm:max-w-md">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Tìm theo tên hoặc mô tả kho tài liệu..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-9"
          />
        </div>
        <div className="flex items-center gap-3 self-end sm:self-center">
          <span className="text-xs text-muted-foreground hidden sm:inline">
            Hiển thị {groups.length} kho tài liệu
          </span>
          <ViewModeToggle value={viewMode} onChange={setViewMode} />
        </div>
      </div>

      {/* 4. Content Area: Cards Grid or Table or Empty or Error */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {["sk-grp-1", "sk-grp-2", "sk-grp-3"].map((key) => (
            <div
              key={key}
              className="h-48 rounded-lg border border-border/50 bg-muted/20 animate-pulse"
            />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={AlertCircle}
          title={
            (error as { status?: number })?.status === 403
              ? "Không có quyền truy cập"
              : (error as { status?: number })?.status === 404
                ? "Không tìm thấy kho tài liệu"
                : "Không thể tải danh sách kho tài liệu"
          }
          description={
            (error as { status?: number })?.status === 403
              ? "Bạn không có quyền truy cập danh sách kho tài liệu. Vui lòng kiểm tra lại quyền của tài khoản."
              : (error as { status?: number })?.status === 404
                ? "Dữ liệu kho tài liệu không tồn tại hoặc đã bị gỡ bỏ."
                : (error as Error)?.message ||
                  "Đã xảy ra lỗi khi tải dữ liệu từ máy chủ. Vui lòng thử lại sau."
          }
          action={{
            label: "Thử lại",
            onClick: () => refetch(),
          }}
        />
      ) : groups.length === 0 ? (
        <EmptyState
          icon={Folders}
          title="Chưa có kho tài liệu nào"
          description={
            search
              ? "Không tìm thấy kho tài liệu nào khớp với từ khóa tìm kiếm. Hãy thử từ khóa khác."
              : "Kho tài liệu giúp tổ chức, phân loại các văn bản quy chế, thông báo hoặc biểu mẫu tập trung trước khi đưa vào Kho Tri Thức."
          }
          action={{
            label: "Thêm kho",
            onClick: () => {
              setName("");
              setDesc("");
              setIsCreateOpen(true);
            },
          }}
        />
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {groups.map((grp) => (
            <Card
              key={grp.id}
              className="flex flex-col justify-between hover:border-primary/50 hover:shadow-xs transition-all cursor-pointer group"
              onClick={() =>
                navigate({
                  to: "/documents/groups/$groupId",
                  params: { groupId: grp.id },
                })
              }
            >
              <CardHeader className="pb-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      <FolderOpen className="size-4" />
                    </div>
                    <CardTitle className="text-base font-semibold leading-tight text-foreground line-clamp-1 group-hover:text-primary transition-colors">
                      {grp.name}
                    </CardTitle>
                  </div>
                  <Badge
                    variant="outline"
                    className="text-[11px] shrink-0 font-normal"
                  >
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
                    {grp.ready_documents} sẵn sàng
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
                  Cập nhật:{" "}
                  {new Date(grp.updated_at).toLocaleDateString("vi-VN")}
                </div>
              </CardContent>

              <CardFooter className="flex items-center justify-between border-t border-border/60 pt-3">
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      openEdit(grp);
                    }}
                    title="Chỉnh sửa thông tin kho"
                    className="size-8 text-muted-foreground hover:text-foreground"
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeletingGroup(grp);
                    }}
                    title="Xóa kho tài liệu"
                    className="size-8 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>

                <Button
                  asChild
                  size="sm"
                  variant="outline"
                  className="h-8 gap-1 text-xs"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Link
                    to="/documents/groups/$groupId"
                    params={{ groupId: grp.id }}
                  >
                    <span>Mở Kho</span>
                    <ArrowUpRight className="size-3.5" />
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-border/80 bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[320px]">Tên Kho Tài Liệu</TableHead>
                <TableHead>Mô Tả</TableHead>
                <TableHead className="w-[120px] text-center">
                  Số Tài Liệu
                </TableHead>
                <TableHead className="w-[200px]">Trạng Thái</TableHead>
                <TableHead className="w-[130px]">Cập Nhật</TableHead>
                <TableHead className="w-[140px] text-right">Thao Tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {groups.map((grp) => (
                <TableRow
                  key={grp.id}
                  className="cursor-pointer hover:bg-muted/50 transition-colors group"
                  onClick={() =>
                    navigate({
                      to: "/documents/groups/$groupId",
                      params: { groupId: grp.id },
                    })
                  }
                >
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2.5">
                      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                        <FolderOpen className="size-4" />
                      </div>
                      <span className="group-hover:text-primary font-semibold transition-colors line-clamp-1">
                        {grp.name}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-xs truncate">
                    {grp.description || "—"}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className="text-xs font-normal">
                      {grp.total_documents}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-1">
                      <span className="inline-flex items-center gap-1 rounded bg-success/10 px-1.5 py-0.5 text-[11px] font-medium text-success">
                        <CheckCircle2 className="size-2.5" />
                        {grp.ready_documents}
                      </span>
                      {grp.processing_documents > 0 && (
                        <span className="inline-flex items-center gap-1 rounded bg-warning/10 px-1.5 py-0.5 text-[11px] font-medium text-warning">
                          <Clock className="size-2.5" />
                          {grp.processing_documents}
                        </span>
                      )}
                      {grp.error_documents > 0 && (
                        <span className="inline-flex items-center gap-1 rounded bg-destructive/10 px-1.5 py-0.5 text-[11px] font-medium text-destructive">
                          {grp.error_documents}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(grp.updated_at).toLocaleDateString("vi-VN")}
                  </TableCell>
                  <TableCell
                    className="text-right"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openEdit(grp)}
                        title="Chỉnh sửa thông tin kho"
                        className="size-8 text-muted-foreground hover:text-foreground"
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingGroup(grp)}
                        title="Xóa kho tài liệu"
                        className="size-8 text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                      <Button
                        asChild
                        size="sm"
                        variant="outline"
                        className="h-8 gap-1 text-xs ml-1"
                      >
                        <Link
                          to="/documents/groups/$groupId"
                          params={{ groupId: grp.id }}
                        >
                          <span>Mở</span>
                          <ArrowUpRight className="size-3" />
                        </Link>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
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
                <DialogTitle>Tạo Kho Tài Liệu Mới</DialogTitle>
                <DialogDescription>
                  Phân loại và quản lý các văn bản tập trung trước khi đưa vào
                  Kho Tri Thức.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <label
                htmlFor="create-group-name"
                className="text-xs font-medium text-foreground"
              >
                Tên kho tài liệu <span className="text-destructive">*</span>
              </label>
              <Input
                id="create-group-name"
                placeholder="Ví dụ: Tuyển sinh 2026, Quy chế đào tạo, Biểu mẫu nhân sự..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-9 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="create-group-desc"
                className="text-xs font-medium text-foreground"
              >
                Mô tả kho tài liệu
              </label>
              <Textarea
                id="create-group-desc"
                placeholder="Ghi chú mục đích hoặc phạm vi của kho tài liệu..."
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
              {createMutation.isPending ? "Đang thêm..." : "Thêm kho"}
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
            <DialogTitle>Chỉnh Sửa Kho Tài Liệu</DialogTitle>
            <DialogDescription>
              Cập nhật tên hoặc mô tả của kho tài liệu.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3.5 py-2">
            <div className="space-y-1.5">
              <label
                htmlFor="edit-group-name"
                className="text-xs font-medium text-foreground"
              >
                Tên kho tài liệu <span className="text-destructive">*</span>
              </label>
              <Input
                id="edit-group-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-9 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="edit-group-desc"
                className="text-xs font-medium text-foreground"
              >
                Mô tả kho tài liệu
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
        title="Xác nhận xóa kho tài liệu"
        description={
          deletingGroup
            ? `Bạn có chắc chắn muốn xóa kho "${deletingGroup.name}"? Thao tác này chỉ xóa phân loại kho; toàn bộ tài liệu gốc và các liên kết Kho Tri Thức đã tạo sẽ được bảo toàn nguyên vẹn.`
            : ""
        }
        confirmText="Xóa Kho Tài Liệu"
        confirmVariant="destructive"
        onConfirm={() =>
          deletingGroup && deleteMutation.mutate(deletingGroup.id)
        }
        isPending={deleteMutation.isPending}
      />
    </div>
  );
}
