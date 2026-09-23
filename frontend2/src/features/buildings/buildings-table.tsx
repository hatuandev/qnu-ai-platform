import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  type RowSelectionState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import {
  Building2,
  CheckCircle2,
  Download,
  Eye,
  Layers,
  MoreHorizontal,
  Pencil,
  Power,
  RotateCcw,
  Search,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Combobox } from "@/components/admin/combobox";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DataTableViewOptions } from "@/components/admin/data-table/data-table-view-options";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
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
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { Building, BuildingStatus } from "@/features/buildings/types";
import { exportToExcel } from "@/lib/excel-export";
import { cn } from "@/lib/utils";

const columnLabels: Record<string, string> = {
  code: "Mã",
  name: "Tên",
  address: "Địa chỉ",
  floorCount: "Số tầng",
  roomCount: "Số phòng",
  status: "Trạng thái",
};

const statusLabels: Record<BuildingStatus, string> = {
  active: "Đang hoạt động",
  inactive: "Ngừng sử dụng",
};

const statusOptions: Array<{ value: string; label: string }> = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "active", label: "Đang hoạt động" },
  { value: "inactive", label: "Ngừng sử dụng" },
];

function StatusBadge({ status }: { status: BuildingStatus }) {
  return (
    <Badge
      variant={status === "active" ? "success" : "secondary"}
      className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          status === "active" ? "bg-emerald-500" : "bg-muted-foreground/60",
        )}
      />
      {statusLabels[status]}
    </Badge>
  );
}

function exportBuildingsToExcel(buildings: Building[]) {
  exportToExcel({
    filename: `danh_sach_toa_nha_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Tòa nhà",
    data: buildings,
    columns: [
      { header: "Mã tòa", accessor: (b) => b.code },
      { header: "Tên tòa nhà", accessor: (b) => b.name },
      { header: "Địa chỉ", accessor: (b) => b.address || "" },
      { header: "Số tầng", accessor: (b) => b.floorCount },
      { header: "Số phòng", accessor: (b) => b.roomCount },
      {
        header: "Trạng thái",
        accessor: (b) =>
          b.status === "active" ? "Đang hoạt động" : "Ngừng sử dụng",
      },
    ],
  });
}

export function BuildingsTable({
  data,
  page,
  pageSize,
  total,
  totalPages,
  isLoading,
  isError,
  errorMessage,
  hasBuildings,
  hasActiveFilters,
  query,
  status,
  canUpdate,
  canDeactivate,
  canDelete: canDeleteBuilding,
  onRetry,
  onQueryChange,
  onStatusChange,
  onResetFilters,
  onPageChange,
  onPageSizeChange,
  onView,
  onEdit,
  onDeactivate,
  onDelete: handleDelete,
}: {
  data: Building[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  hasBuildings: boolean;
  hasActiveFilters: boolean;
  query: string;
  status?: BuildingStatus;
  canUpdate?: boolean;
  canDeactivate?: boolean;
  canDelete?: boolean;
  onRetry: () => void;
  onQueryChange: (q: string) => void;
  onStatusChange: (status?: BuildingStatus) => void;
  onResetFilters: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onView: (building: Building) => void;
  onEdit: (building: Building) => void;
  onDeactivate: (building: Building) => void;
  onDelete: (building: Building) => void;
}) {
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  // Summary Metrics
  const summary = useMemo(() => {
    const totalCount = total;
    const activeCount = data.filter((b) => b.status === "active").length;
    const inactiveCount = data.filter((b) => b.status === "inactive").length;
    const totalRooms = data.reduce((sum, b) => sum + (b.roomCount || 0), 0);
    return { totalCount, activeCount, inactiveCount, totalRooms };
  }, [data, total]);

  const columns = useMemo<ColumnDef<Building>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <div className="flex items-center pl-1">
            <Checkbox
              checked={
                table.getIsAllPageRowsSelected() ||
                (table.getIsSomePageRowsSelected() && "indeterminate")
              }
              onCheckedChange={(value) =>
                table.toggleAllPageRowsSelected(Boolean(value))
              }
              aria-label="Chọn tất cả tòa nhà trên trang này"
            />
          </div>
        ),
        cell: ({ row }) => (
          <div className="flex items-center pl-1">
            <Checkbox
              checked={row.getIsSelected()}
              onClick={(event) => event.stopPropagation()}
              onCheckedChange={(value) => row.toggleSelected(Boolean(value))}
              aria-label={`Chọn tòa nhà ${row.original.name}`}
            />
          </div>
        ),
        enableSorting: false,
        enableHiding: false,
        size: 40,
      },
      {
        accessorKey: "code",
        header: "Mã",
        cell: ({ row }) => (
          <Badge variant="outline" className="font-mono text-xs">
            {row.original.code}
          </Badge>
        ),
      },
      {
        accessorKey: "name",
        header: "Tên tòa nhà",
        cell: ({ row }) => (
          <span className="font-semibold text-foreground text-sm">
            {row.original.name}
          </span>
        ),
      },
      {
        accessorKey: "address",
        header: "Địa chỉ",
        cell: ({ row }) => (
          <span className="text-muted-foreground text-xs">
            {row.original.address || "—"}
          </span>
        ),
      },
      {
        accessorKey: "floorCount",
        header: "Số tầng",
        cell: ({ row }) => (
          <span className="tabular-nums font-mono text-sm text-foreground">
            {row.original.floorCount} tầng
          </span>
        ),
      },
      {
        accessorKey: "roomCount",
        header: "Số phòng",
        cell: ({ row }) => (
          <span className="tabular-nums font-mono text-sm text-foreground">
            {row.original.roomCount} phòng
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Trạng thái",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: "actions",
        header: "",
        enableHiding: false,
        cell: ({ row }) => (
          <div
            className="flex justify-end"
            onClick={(event) => event.stopPropagation()}
          >
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="size-8 text-muted-foreground hover:text-foreground"
                  onClick={(event) => event.stopPropagation()}
                  aria-label={`Thao tác với ${row.original.name}`}
                >
                  <MoreHorizontal className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem
                  onClick={(event) => {
                    event.stopPropagation();
                    onView(row.original);
                  }}
                >
                  <Eye className="size-4 mr-2 text-muted-foreground" />
                  Xem chi tiết
                </DropdownMenuItem>
                {canUpdate ? (
                  <DropdownMenuItem
                    onClick={(event) => {
                      event.stopPropagation();
                      onEdit(row.original);
                    }}
                  >
                    <Pencil className="size-4 mr-2 text-muted-foreground" />
                    Chỉnh sửa
                  </DropdownMenuItem>
                ) : null}
                {canDeactivate && row.original.status === "active" ? (
                  <DropdownMenuItem
                    onClick={(event) => {
                      event.stopPropagation();
                      onDeactivate(row.original);
                    }}
                  >
                    <Power className="size-4 mr-2 text-amber-500" />
                    Ngừng sử dụng
                  </DropdownMenuItem>
                ) : null}
                {canDeleteBuilding ? (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-destructive focus:bg-destructive/10 focus:text-destructive"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDelete(row.original);
                      }}
                    >
                      <Trash2 className="size-4 mr-2 text-destructive" />
                      Xóa tòa nhà
                    </DropdownMenuItem>
                  </>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [
      canDeactivate,
      canDeleteBuilding,
      canUpdate,
      handleDelete,
      onDeactivate,
      onEdit,
      onView,
    ],
  );

  const table = useReactTable({
    data,
    columns,
    state: { columnVisibility, rowSelection },
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,
  });

  const selectedBuildings = table
    .getSelectedRowModel()
    .rows.map((r) => r.original);

  const viewOptions = (
    <DataTableViewOptions table={table} labels={columnLabels} />
  );

  return (
    <div className="space-y-6">
      {/* 1. Top KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Building2}
            label="Tổng số tòa nhà"
            value={summary.totalCount.toLocaleString("vi-VN")}
            helper="Tổng số tòa nhà trong danh mục KTX"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Đang hoạt động"
            value={summary.activeCount.toLocaleString("vi-VN")}
            trend="positive"
            helper="Tòa nhà đang mở tiếp nhận sinh viên"
          />
          <KpiMetric
            icon={Power}
            label="Ngừng sử dụng"
            value={summary.inactiveCount.toLocaleString("vi-VN")}
            trend={summary.inactiveCount > 0 ? "negative" : "neutral"}
            helper="Tòa nhà tạm ngưng hoặc bảo trì"
          />
          <KpiMetric
            icon={Layers}
            label="Tổng số phòng"
            value={summary.totalRooms.toLocaleString("vi-VN")}
            helper="Tổng phòng trực thuộc các tòa nhà"
          />
        </CardContent>
      </Card>

      {/* 2. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:w-80">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            className="pl-9 w-full text-xs"
            placeholder="Tìm theo mã hoặc tên tòa nhà..."
            onChange={(event) => onQueryChange(event.target.value)}
            aria-label="Tìm kiếm tòa nhà"
          />
        </div>
        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          {/* Trạng thái */}
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-52 text-xs"
            options={statusOptions}
            value={status ?? "all"}
            searchPlaceholder="Tìm trạng thái..."
            onValueChange={(value) =>
              onStatusChange(
                value === "all" ? undefined : (value as BuildingStatus),
              )
            }
          />
          {hasActiveFilters ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground col-span-2 sm:col-span-1"
              onClick={onResetFilters}
            >
              <RotateCcw className="size-3.5 mr-1" />
              <span>Đặt lại</span>
            </Button>
          ) : null}
          {viewOptions}
        </div>
      </div>

      {/* 3. Data Table */}
      {isLoading ? (
        <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40">
                <TableHead className="w-10 pl-3" />
                {Object.values(columnLabels).map((label) => (
                  <TableHead
                    key={label}
                    className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap"
                  >
                    {label}
                  </TableHead>
                ))}
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {["one", "two", "three", "four", "five", "six"].map((rowKey) => (
                <TableRow key={rowKey}>
                  {[
                    "select",
                    "code",
                    "name",
                    "address",
                    "floors",
                    "rooms",
                    "status",
                    "actions",
                  ].map((cellKey) => (
                    <TableCell key={`${rowKey}-${cellKey}`}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : isError ? (
        <div className="p-8">
          <EmptyState
            icon={Building2}
            title="Không thể tải danh sách tòa nhà"
            description={errorMessage ?? "Hãy kiểm tra kết nối và thử lại."}
            action={{
              label: "Thử lại",
              onClick: onRetry,
            }}
          />
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow
                    key={headerGroup.id}
                    className="bg-muted/40 hover:bg-muted/40"
                  >
                    {headerGroup.headers.map((header) => (
                      <TableHead
                        key={header.id}
                        className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap"
                      >
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
                {table.getRowModel().rows.length ? (
                  table.getRowModel().rows.map((row) => (
                    <TableRow
                      key={row.id}
                      className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                      onClick={(event) => {
                        if (event.defaultPrevented) return;
                        onView(row.original);
                      }}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id} className="py-3">
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={table.getVisibleLeafColumns().length}
                      className="p-8"
                    >
                      <EmptyState
                        icon={Building2}
                        title={
                          hasActiveFilters
                            ? "Không có tòa nhà phù hợp với bộ lọc"
                            : hasBuildings
                              ? "Không có tòa nhà ở trang này"
                              : "Chưa có tòa nhà nào"
                        }
                        description={
                          hasActiveFilters
                            ? "Hãy mở rộng tìm kiếm hoặc xóa bộ lọc."
                            : hasBuildings
                              ? "Hãy thử trang khác hoặc thay đổi số dòng mỗi trang."
                              : "Tạo tòa nhà đầu tiên để bắt đầu quản lý danh mục."
                        }
                        action={
                          hasActiveFilters
                            ? { label: "Xóa bộ lọc", onClick: onResetFilters }
                            : undefined
                        }
                      />
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          <DataTablePagination
            page={Math.min(page, Math.max(1, totalPages))}
            pageSize={pageSize}
            pageCount={Math.max(1, totalPages)}
            total={total}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
          />
        </>
      )}

      {/* 4. Bulk Actions Floating Bar */}
      {selectedBuildings.length > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedBuildings.length}
          selectedLabel="tòa nhà"
          onClear={() => setRowSelection({})}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => {
                  exportBuildingsToExcel(selectedBuildings);
                  toast.success(
                    `Đã xuất dữ liệu ${selectedBuildings.length} tòa nhà ra file Excel thành công.`,
                  );
                }}
                aria-label="Xuất Excel"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Xuất Excel ({selectedBuildings.length} tòa nhà)
            </TooltipContent>
          </Tooltip>

          {canDeleteBuilding ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="destructive"
                  size="icon"
                  className="size-8 rounded-xl shadow-2xs"
                  onClick={() => {
                    handleDelete(selectedBuildings[0]);
                  }}
                  aria-label="Xóa đã chọn"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                Xóa các tòa nhà đã chọn
              </TooltipContent>
            </Tooltip>
          ) : null}
        </DataTableBulkActions>
      ) : null}
    </div>
  );
}
