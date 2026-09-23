import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  type RowSelectionState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import {
  BedDouble,
  CheckCircle2,
  DoorClosed,
  Download,
  Eye,
  MoreHorizontal,
  Pencil,
  Power,
  RotateCcw,
  Search,
  Trash2,
  Users,
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
import type { RoomType } from "@/features/room-types/types";
import { exportToExcel } from "@/lib/excel-export";
import { cn } from "@/lib/utils";

const columnLabels: Record<string, string> = {
  code: "Mã",
  name: "Tên loại phòng",
  capacity: "Sức chứa",
  roomCount: "Số phòng",
  isActive: "Trạng thái",
};

const statusLabels: Record<string, string> = {
  active: "Đang sử dụng",
  inactive: "Ngừng sử dụng",
};

const statusOptions: Array<{ value: string; label: string }> = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "active", label: "Đang sử dụng" },
  { value: "inactive", label: "Ngừng sử dụng" },
];

function exportRoomTypesToExcel(roomTypes: RoomType[]) {
  exportToExcel({
    filename: `danh_sach_loai_phong_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Loại phòng",
    data: roomTypes,
    columns: [
      { header: "Mã loại phòng", accessor: (rt) => rt.code },
      { header: "Tên loại phòng", accessor: (rt) => rt.name },
      { header: "Sức chứa", accessor: (rt) => rt.capacity },
      { header: "Số phòng", accessor: (rt) => rt.roomCount },
      {
        header: "Trạng thái",
        accessor: (rt) => (rt.isActive ? "Đang sử dụng" : "Ngừng sử dụng"),
      },
    ],
  });
}

export function RoomTypesTable({
  data,
  total,
  totalPages,
  page,
  pageSize,
  isLoading,
  isError,
  errorMessage,
  hasRoomTypes,
  hasActiveFilters,
  query,
  isActive,
  canUpdate,
  canDeactivate,
  canDelete,
  onRetry,
  onQueryChange,
  onActiveChange,
  onResetFilters,
  onPageChange,
  onPageSizeChange,
  onView,
  onEdit,
  onDeactivate,
  onDelete,
}: {
  data: RoomType[];
  total: number;
  totalPages: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  hasRoomTypes: boolean;
  hasActiveFilters: boolean;
  query: string;
  isActive?: boolean;
  canUpdate: boolean;
  canDeactivate: boolean;
  canDelete?: boolean;
  onRetry: () => void;
  onQueryChange: (value: string) => void;
  onActiveChange: (value?: boolean) => void;
  onResetFilters: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onView: (roomType: RoomType) => void;
  onEdit: (roomType: RoomType) => void;
  onDeactivate: (roomType: RoomType) => void;
  onDelete?: (roomType: RoomType) => void;
}) {
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const canDeleteRoomType = canDelete ?? canDeactivate;
  const handleDelete = onDelete ?? onDeactivate;

  // Summary Metrics
  const summary = useMemo(() => {
    const totalRoomTypes = total;
    const activeCount = data.filter((rt) => rt.isActive).length;
    const inactiveCount = data.filter((rt) => !rt.isActive).length;
    const totalRooms = data.reduce((sum, rt) => sum + (rt.roomCount || 0), 0);
    return { totalRoomTypes, activeCount, inactiveCount, totalRooms };
  }, [data, total]);

  const columns = useMemo<ColumnDef<RoomType>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <div className="flex items-center pl-1">
            <Checkbox
              aria-label="Chọn tất cả loại phòng trên trang này"
              checked={
                table.getIsAllPageRowsSelected() ||
                (table.getIsSomePageRowsSelected() && "indeterminate")
              }
              onCheckedChange={(value) =>
                table.toggleAllPageRowsSelected(Boolean(value))
              }
            />
          </div>
        ),
        cell: ({ row }) => (
          <div
            className="flex items-center pl-1"
            onClick={(event) => event.stopPropagation()}
          >
            <Checkbox
              aria-label={`Chọn loại phòng ${row.original.name}`}
              checked={row.getIsSelected()}
              onCheckedChange={(value) => row.toggleSelected(Boolean(value))}
            />
          </div>
        ),
        enableSorting: false,
        enableHiding: false,
        size: 36,
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
        header: "Tên loại phòng",
        cell: ({ row }) => (
          <span className="font-semibold text-foreground text-sm">
            {row.original.name}
          </span>
        ),
      },
      {
        accessorKey: "capacity",
        header: "Sức chứa",
        cell: ({ row }) => (
          <div className="inline-flex items-center gap-1.5 text-sm text-foreground">
            <Users className="size-3.5 text-muted-foreground" />
            <span className="tabular-nums font-mono font-semibold">
              {row.original.capacity}
            </span>
            <span className="text-muted-foreground text-xs">người / phòng</span>
          </div>
        ),
      },
      {
        accessorKey: "roomCount",
        header: "Số phòng",
        cell: ({ row }) => (
          <div className="inline-flex items-center gap-1.5 text-sm text-foreground">
            <DoorClosed className="size-3.5 text-muted-foreground" />
            <span className="tabular-nums font-mono font-semibold">
              {row.original.roomCount}
            </span>
            <span className="text-muted-foreground text-xs">phòng</span>
          </div>
        ),
      },
      {
        accessorKey: "isActive",
        header: "Trạng thái",
        cell: ({ row }) => (
          <Badge
            variant={row.original.isActive ? "success" : "secondary"}
            className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
          >
            <span
              className={cn(
                "size-1.5 rounded-full",
                row.original.isActive
                  ? "bg-emerald-500"
                  : "bg-muted-foreground/60",
              )}
            />
            {row.original.isActive
              ? statusLabels.active
              : statusLabels.inactive}
          </Badge>
        ),
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
                  aria-label={`Thao tác với ${row.original.name}`}
                  onClick={(event) => event.stopPropagation()}
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
                {canDeactivate && row.original.isActive ? (
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
                {canDeleteRoomType ? (
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
                      Xóa loại phòng
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
      canDeleteRoomType,
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

  const selectedRoomTypes = table
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
            icon={BedDouble}
            label="Tổng loại phòng"
            value={summary.totalRoomTypes.toLocaleString("vi-VN")}
            helper="Tổng số loại phòng trong danh mục"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Đang sử dụng"
            value={summary.activeCount.toLocaleString("vi-VN")}
            trend="positive"
            helper="Loại phòng đang mở áp dụng"
          />
          <KpiMetric
            icon={Power}
            label="Ngừng sử dụng"
            value={summary.inactiveCount.toLocaleString("vi-VN")}
            trend={summary.inactiveCount > 0 ? "negative" : "neutral"}
            helper="Loại phòng tạm ngưng hoặc không dùng"
          />
          <KpiMetric
            icon={DoorClosed}
            label="Tổng số phòng"
            value={summary.totalRooms.toLocaleString("vi-VN")}
            helper="Tổng phòng quy đổi từ các loại phòng"
          />
        </CardContent>
      </Card>

      {/* 2. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:w-80">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 w-full text-xs"
            value={query}
            placeholder="Tìm theo mã hoặc tên loại phòng..."
            aria-label="Tìm kiếm loại phòng"
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          {/* Trạng thái */}
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-52 text-xs"
            options={statusOptions}
            value={
              isActive === undefined ? "all" : isActive ? "active" : "inactive"
            }
            searchPlaceholder="Tìm trạng thái..."
            onValueChange={(value) =>
              onActiveChange(value === "all" ? undefined : value === "active")
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
              {["one", "two", "three", "four", "five"].map((key) => (
                <TableRow key={key}>
                  {[
                    "select",
                    "code",
                    "name",
                    "capacity",
                    "rooms",
                    "status",
                    "actions",
                  ].map((cellKey) => (
                    <TableCell key={`${key}-${cellKey}`}>
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
            icon={BedDouble}
            title="Không thể tải danh sách loại phòng"
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
                {table.getHeaderGroups().map((group) => (
                  <TableRow
                    key={group.id}
                    className="bg-muted/40 hover:bg-muted/40"
                  >
                    {group.headers.map((header) => (
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
                        icon={BedDouble}
                        title={
                          hasActiveFilters
                            ? "Không có loại phòng phù hợp với bộ lọc"
                            : hasRoomTypes
                              ? "Không có loại phòng ở trang này"
                              : "Chưa có loại phòng nào"
                        }
                        description={
                          hasActiveFilters
                            ? "Hãy mở rộng tìm kiếm hoặc xóa bộ lọc."
                            : hasRoomTypes
                              ? "Hãy thử trang khác hoặc thay đổi số dòng mỗi trang."
                              : "Tạo loại phòng đầu tiên để bắt đầu cấu hình phòng ở."
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
      {selectedRoomTypes.length > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedRoomTypes.length}
          selectedLabel="loại phòng"
          onClear={() => setRowSelection({})}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => {
                  exportRoomTypesToExcel(selectedRoomTypes);
                  toast.success(
                    `Đã xuất dữ liệu ${selectedRoomTypes.length} loại phòng ra file Excel thành công.`,
                  );
                }}
                aria-label="Xuất Excel"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Xuất Excel ({selectedRoomTypes.length} loại phòng)
            </TooltipContent>
          </Tooltip>

          {canDeleteRoomType ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="destructive"
                  size="icon"
                  className="size-8 rounded-xl shadow-2xs"
                  onClick={() => {
                    handleDelete(selectedRoomTypes[0]);
                  }}
                  aria-label="Xóa đã chọn"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                Xóa các loại phòng đã chọn
              </TooltipContent>
            </Tooltip>
          ) : null}
        </DataTableBulkActions>
      ) : null}
    </div>
  );
}
