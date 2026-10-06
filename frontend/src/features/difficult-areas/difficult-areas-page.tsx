import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  type RowSelectionState,
  useReactTable,
} from "@tanstack/react-table";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Download,
  Globe2,
  Landmark,
  MoreHorizontal,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import {
  useBatchDeleteDifficultAreas,
  useDeleteDifficultArea,
  useDifficultAreaProvincesQuery,
  useDifficultAreaStatsQuery,
  useDifficultAreasQuery,
} from "@/features/difficult-areas/api";
import { DifficultAreaFormDialog } from "@/features/difficult-areas/difficult-area-form-dialog";
import type { DifficultAreaItem } from "@/features/difficult-areas/types";
import { exportToExcel } from "@/lib/excel-export";
import { useRbac } from "@/rbac/context";

export const difficultAreasSearchSchema = z.object({
  q: z.string().catch(""),
  province: z.string().catch("all"),
  scope: z.enum(["all", "whole", "partial"]).catch("all"),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(20),
});

export type DifficultAreasSearch = z.infer<typeof difficultAreasSearchSchema>;

function exportDifficultAreasToExcel(areas: DifficultAreaItem[]) {
  exportToExcel({
    filename: `danh_sach_dia_ban_kho_khan_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Địa bàn khó khăn",
    data: areas,
    columns: [
      { header: "Mã địa bàn", accessor: (a) => a.externalCode },
      { header: "Tên đơn vị", accessor: (a) => a.name },
      { header: "Loại đơn vị", accessor: (a) => a.divisionType },
      { header: "Tỉnh/Thành phố", accessor: (a) => a.provinceName || "" },
      {
        header: "Phạm vi",
        accessor: (a) => (a.isWholeArea ? "Toàn bộ xã" : "Theo thôn/ấp"),
      },
      {
        header: "Danh sách thôn/ấp áp dụng",
        accessor: (a) => a.specificVillages || "",
      },
    ],
  });
}

export function DifficultAreasPage({
  search,
  updateSearch,
}: {
  search: DifficultAreasSearch;
  updateSearch: (changes: Partial<DifficultAreasSearch>) => void;
}) {
  const { can } = useRbac();
  const canManage =
    can("ktx.difficult_areas.create") ||
    can("ktx.difficult_areas.update") ||
    can("ktx.difficult_areas.delete") ||
    can("ktx.priority_objects.create") ||
    can("ktx.priority_objects.update") ||
    can("ktx.access.manage") ||
    can("ktx.access.admin");

  const [localSearch, setLocalSearch] = useState(search.q || "");
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [areaToEdit, setAreaToEdit] = useState<DifficultAreaItem | null>(null);
  const [areaToDelete, setAreaToDelete] = useState<DifficultAreaItem | null>(
    null,
  );
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  const provincesQuery = useDifficultAreaProvincesQuery();
  const provinces = provincesQuery.data ?? [];

  const statsQuery = useDifficultAreaStatsQuery();
  const stats = statsQuery.data;

  const isWholeAreaFilter =
    search.scope === "whole"
      ? true
      : search.scope === "partial"
        ? false
        : undefined;

  const areasQuery = useDifficultAreasQuery({
    search: search.q || undefined,
    provinceName: search.province === "all" ? undefined : search.province,
    isWholeArea: isWholeAreaFilter,
    page: search.page,
    pageSize: search.pageSize,
  });

  const deleteMutation = useDeleteDifficultArea();
  const batchDeleteMutation = useBatchDeleteDifficultAreas();

  const items = areasQuery.data?.items ?? [];
  const total = areasQuery.data?.total ?? 0;
  const totalPages = areasQuery.data?.totalPages ?? 1;

  const columns = useMemo<ColumnDef<DifficultAreaItem>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <Checkbox
            checked={
              table.getIsAllPageRowsSelected() ||
              (table.getIsSomePageRowsSelected() && "indeterminate")
            }
            onCheckedChange={(value) =>
              table.toggleAllPageRowsSelected(Boolean(value))
            }
            aria-label="Chọn tất cả"
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(Boolean(value))}
            aria-label="Chọn dòng"
          />
        ),
        enableSorting: false,
        enableHiding: false,
      },
      {
        id: "stt",
        header: () => <span className="w-10 text-center">STT</span>,
        cell: ({ row }) => {
          const index = row.index + 1 + (search.page - 1) * search.pageSize;
          return (
            <span className="text-xs text-muted-foreground font-mono">
              {index}
            </span>
          );
        },
      },
      {
        accessorKey: "externalCode",
        header: "Mã ĐB",
        cell: ({ row }) => (
          <span className="font-mono text-xs font-semibold text-foreground">
            {row.original.externalCode}
          </span>
        ),
      },
      {
        accessorKey: "name",
        header: "Xã / Phường / Thị trấn",
        cell: ({ row }) => (
          <div className="flex items-center gap-2.5">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
              <Building2 className="size-3.5" />
            </div>
            <div>
              <div className="font-medium text-foreground text-xs sm:text-sm">
                {row.original.name}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {row.original.divisionType}
              </div>
            </div>
          </div>
        ),
      },
      {
        accessorKey: "provinceName",
        header: "Tỉnh / Thành phố",
        cell: ({ row }) => (
          <Badge
            variant="outline"
            className="font-normal text-xs bg-muted/40 text-foreground px-2 py-0.5 border-border/60"
          >
            {row.original.provinceName ?? "—"}
          </Badge>
        ),
      },
      {
        accessorKey: "isWholeArea",
        header: "Phạm vi áp dụng",
        cell: ({ row }) => {
          const isWhole = row.original.isWholeArea;
          if (isWhole) {
            return (
              <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>Toàn bộ xã</span>
              </div>
            );
          }
          return (
            <div className="space-y-1 py-1">
              <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300">
                <AlertCircle className="size-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                <span>Theo thôn / ấp</span>
              </div>
              {row.original.specificVillages ? (
                <div className="text-xs text-foreground bg-muted/40 p-1.5 rounded-md border border-border/50 max-w-md font-normal leading-relaxed">
                  {row.original.specificVillages}
                </div>
              ) : null}
            </div>
          );
        },
      },
      {
        id: "actions",
        header: () => <span className="sr-only">Thao tác</span>,
        cell: ({ row }) => {
          const area = row.original;
          return (
            <div className="text-right">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-muted-foreground hover:text-foreground"
                  >
                    <MoreHorizontal className="size-4" />
                    <span className="sr-only">Mở menu</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="text-xs">
                  <DropdownMenuItem
                    onClick={() => {
                      setAreaToEdit(area);
                      setFormDialogOpen(true);
                    }}
                  >
                    <Pencil className="mr-2 size-3.5" />
                    Chỉnh sửa
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => setAreaToDelete(area)}
                  >
                    <Trash2 className="mr-2 size-3.5" />
                    Xóa địa bàn
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          );
        },
      },
    ],
    [search.page, search.pageSize, canManage],
  );

  const table = useReactTable({
    data: items,
    columns,
    state: {
      rowSelection,
    },
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: totalPages,
    getRowId: (row) => row.id,
  });

  const selectedCount = Object.keys(rowSelection).length;
  const selectedIds = useMemo(
    () => Object.keys(rowSelection).filter((id) => rowSelection[id]),
    [rowSelection],
  );

  function handleSearchSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateSearch({ q: localSearch.trim(), page: 1 });
  }

  function handleReset() {
    setLocalSearch("");
    updateSearch({ q: "", province: "all", scope: "all", page: 1 });
  }

  async function handleConfirmDelete() {
    if (!areaToDelete) return;
    try {
      await deleteMutation.mutateAsync(areaToDelete.id);
      toast.success(`Đã xóa địa bàn "${areaToDelete.name}".`);
      setAreaToDelete(null);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Có lỗi khi xóa địa bàn.",
      );
    }
  }

  async function handleConfirmBulkDelete() {
    if (selectedIds.length === 0) return;
    try {
      await batchDeleteMutation.mutateAsync(selectedIds);
      toast.success(`Đã xóa ${selectedIds.length} địa bàn đã chọn.`);
      setRowSelection({});
      setIsBulkDeleting(false);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Có lỗi khi xóa hàng loạt.",
      );
    }
  }

  const hasActiveFilters =
    Boolean(search.q) || search.province !== "all" || search.scope !== "all";

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Địa bàn ưu tiên"
        description="Danh mục xã, phường, thôn/ấp thuộc diện đặc biệt khó khăn theo Quyết định 60/QĐ-BDTTG (áp dụng đối soát đối tượng Vùng cao, vùng có điều kiện KT-XH đặc biệt khó khăn)."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs font-medium"
              disabled={items.length === 0 || areasQuery.isLoading}
              onClick={() => {
                exportDifficultAreasToExcel(items);
                toast.success(
                  `Đã xuất dữ liệu ${items.length} địa bàn khó khăn ra file Excel thành công.`,
                );
              }}
              aria-label="Xuất Excel"
            >
              <Download className="mr-1.5 size-3.5" />
              Xuất Excel
            </Button>
            {canManage && (
              <Button
                size="sm"
                className="text-xs font-medium"
                onClick={() => {
                  setAreaToEdit(null);
                  setFormDialogOpen(true);
                }}
              >
                <Plus className="mr-1.5 size-3.5" />
                Thêm địa bàn
              </Button>
            )}
          </div>
        }
      />

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        <Card className="border-border/60 bg-card/60 shadow-xs">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground sm:text-sm">
                Tổng số địa bàn
              </span>
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Landmark className="size-4" />
              </div>
            </div>
            <div className="mt-2 text-xl font-bold tracking-tight sm:text-2xl">
              {statsQuery.isLoading ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                (stats?.total ?? total).toLocaleString("vi-VN")
              )}
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Địa bàn cấp xã được công nhận
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60 shadow-xs">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground sm:text-sm">
                Số Tỉnh / TP
              </span>
              <div className="flex size-8 items-center justify-center rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400">
                <Globe2 className="size-4" />
              </div>
            </div>
            <div className="mt-2 text-xl font-bold tracking-tight sm:text-2xl">
              {statsQuery.isLoading ? (
                <Skeleton className="h-7 w-12" />
              ) : (
                (stats?.totalProvinces ?? provinces.length)
              )}
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Tỉnh/TP có xã khó khăn
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60 shadow-xs">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground sm:text-sm">
                Khó khăn toàn xã
              </span>
              <div className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-4" />
              </div>
            </div>
            <div className="mt-2 text-xl font-bold tracking-tight sm:text-2xl text-emerald-600 dark:text-emerald-400">
              {statsQuery.isLoading ? (
                <Skeleton className="h-7 w-14" />
              ) : (
                (stats?.wholeAreaCount ?? 0).toLocaleString("vi-VN")
              )}
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Áp dụng toàn bộ địa bàn xã
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60 shadow-xs">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground sm:text-sm">
                Theo thôn / ấp
              </span>
              <div className="flex size-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <AlertCircle className="size-4" />
              </div>
            </div>
            <div className="mt-2 text-xl font-bold tracking-tight sm:text-2xl text-amber-600 dark:text-amber-400">
              {statsQuery.isLoading ? (
                <Skeleton className="h-7 w-14" />
              ) : (
                (stats?.partialAreaCount ?? 0).toLocaleString("vi-VN")
              )}
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Áp dụng cho thôn/xóm cụ thể
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <form
          onSubmit={handleSearchSubmit}
          className="flex flex-1 items-center gap-2"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={localSearch}
              placeholder="Tìm theo tên xã/phường, mã hoặc thôn/ấp..."
              className="pl-9 text-xs sm:text-sm"
              onChange={(e) => setLocalSearch(e.target.value)}
            />
          </div>
          <Button
            type="submit"
            size="sm"
            className="h-9 px-3 text-xs sm:text-sm"
          >
            Tìm kiếm
          </Button>
        </form>

        <div className="flex flex-wrap items-center gap-2">
          {/* Lọc theo Tỉnh / TP */}
          <Select
            value={search.province}
            onValueChange={(val) => updateSearch({ province: val, page: 1 })}
          >
            <SelectTrigger className="w-[180px] text-xs">
              <SelectValue placeholder="Tất cả Tỉnh/TP" />
            </SelectTrigger>
            <SelectContent className="max-h-64 text-xs">
              <SelectItem value="all">
                Tất cả Tỉnh/TP ({provinces.length})
              </SelectItem>
              {provinces.map((prov) => (
                <SelectItem key={prov} value={prov}>
                  {prov}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Lọc theo Phạm vi */}
          <Select
            value={search.scope}
            onValueChange={(val) =>
              updateSearch({
                scope: val as DifficultAreasSearch["scope"],
                page: 1,
              })
            }
          >
            <SelectTrigger className="w-[160px] text-xs">
              <SelectValue placeholder="Tất cả phạm vi" />
            </SelectTrigger>
            <SelectContent className="text-xs">
              <SelectItem value="all">Tất cả phạm vi</SelectItem>
              <SelectItem value="whole">Toàn xã khó khăn</SelectItem>
              <SelectItem value="partial">Theo thôn / ấp</SelectItem>
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 text-xs"
              onClick={handleReset}
            >
              <RotateCcw className="mr-1 size-3.5" />
              Đặt lại
            </Button>
          )}
        </div>
      </div>

      {/* Main DataTable */}
      <div className="rounded-lg border bg-card shadow-xs">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-muted/40">
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id} className="text-xs">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {areasQuery.isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={`skeleton-row-${i}`}>
                    <TableCell>
                      <Skeleton className="h-4 w-4 mx-auto" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-6 mx-auto" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-12" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-32" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-24" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-40" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-28" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-6 ml-auto" />
                    </TableCell>
                  </TableRow>
                ))
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-44 text-center"
                  >
                    <DataTableEmpty
                      title="Không tìm thấy địa bàn nào"
                      description={
                        hasActiveFilters
                          ? "Thử thay đổi từ khóa tìm kiếm hoặc bỏ bớt các bộ lọc đang chọn."
                          : "Chưa có dữ liệu địa bàn khó khăn."
                      }
                      action={
                        hasActiveFilters
                          ? { label: "Đặt lại bộ lọc", onClick: handleReset }
                          : undefined
                      }
                    />
                  </TableCell>
                </TableRow>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    data-state={row.getIsSelected() && "selected"}
                    className="hover:bg-muted/30"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Standard DataTable Pagination */}
        <div className="border-t p-3">
          <DataTablePagination
            page={search.page}
            pageSize={search.pageSize}
            pageCount={totalPages}
            total={total}
            onPageChange={(page) => updateSearch({ page })}
            onPageSizeChange={(pageSize) => updateSearch({ pageSize, page: 1 })}
          />
        </div>
      </div>

      {/* Floating Bulk Actions Bar */}
      <DataTableBulkActions
        selectedCount={selectedCount}
        selectedLabel="địa bàn"
        onClear={() => setRowSelection({})}
      >
        <Button
          variant="destructive"
          size="sm"
          className="h-7 text-xs px-2.5"
          onClick={() => setIsBulkDeleting(true)}
        >
          <Trash2 className="mr-1.5 size-3.5" />
          Xóa đã chọn ({selectedCount})
        </Button>
      </DataTableBulkActions>

      {/* Form Dialog for Add/Edit */}
      <DifficultAreaFormDialog
        open={formDialogOpen}
        onOpenChange={setFormDialogOpen}
        areaToEdit={areaToEdit}
      />

      {/* Confirm Dialog for Single Delete */}
      <ConfirmDialog
        open={Boolean(areaToDelete)}
        onOpenChange={(open) => !open && setAreaToDelete(null)}
        title="Xác nhận xóa địa bàn ưu tiên"
        description={`Bạn có chắc chắn muốn xóa địa bàn "${areaToDelete?.name}" (${areaToDelete?.provinceName}) khỏi danh mục khó khăn? Hành động này sẽ hủy liên kết đối soát của địa bàn này.`}
        confirmLabel="Xóa địa bàn"
        confirmVariant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={handleConfirmDelete}
      />

      {/* Confirm Dialog for Bulk Delete */}
      <ConfirmDialog
        open={isBulkDeleting}
        onOpenChange={setIsBulkDeleting}
        title="Xác nhận xóa nhiều địa bàn"
        description={`Bạn có chắc chắn muốn xóa ${selectedCount} địa bàn đã chọn? Thao tác này không thể hoàn tác.`}
        confirmLabel={`Xóa ${selectedCount} địa bàn`}
        confirmVariant="destructive"
        isLoading={batchDeleteMutation.isPending}
        onConfirm={handleConfirmBulkDelete}
      />
    </div>
  );
}
