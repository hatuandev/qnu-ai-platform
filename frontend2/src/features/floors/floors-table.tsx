import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  type RowSelectionState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import {
  CheckCircle2,
  DoorClosed,
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
import type { Floor, FloorStatus } from "@/features/floors/types";
import { exportToExcel } from "@/lib/excel-export";
import { cn } from "@/lib/utils";

const columnLabels: Record<string, string> = {
  floorNumber: "Số tầng",
  name: "Tên tầng",
  roomCount: "Số phòng",
  status: "Trạng thái",
};

const statusLabels: Record<FloorStatus, string> = {
  active: "Đang hoạt động",
  inactive: "Ngừng sử dụng",
};

const statusOptions: Array<{ value: string; label: string }> = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "active", label: "Đang hoạt động" },
  { value: "inactive", label: "Ngừng sử dụng" },
];

function exportFloorsToExcel(floors: Floor[]) {
  exportToExcel({
    filename: `danh_sach_tang_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Tầng",
    data: floors,
    columns: [
      { header: "Số tầng", accessor: (f) => `Tầng ${f.floorNumber}` },
      { header: "Tên tầng", accessor: (f) => f.name },
      { header: "Số phòng", accessor: (f) => f.roomCount },
      {
        header: "Trạng thái",
        accessor: (f) =>
          f.status === "active" ? "Đang hoạt động" : "Ngừng sử dụng",
      },
    ],
  });
}

export function FloorsTable({
  data,
  allFloors,
  isLoading,
  isError,
  errorMessage,
  query,
  status,
  hasActiveFilters,
  canUpdate,
  canDeactivate,
  canDelete,
  onRetry,
  onQueryChange,
  onStatusChange,
  onResetFilters,
  onView,
  onEdit,
  onDeactivate,
  onDelete,
}: {
  data: Floor[];
  allFloors: Floor[];
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  query: string;
  status?: FloorStatus;
  hasActiveFilters: boolean;
  canUpdate: boolean;
  canDeactivate: boolean;
  canDelete?: boolean;
  onRetry: () => void;
  onQueryChange: (value: string) => void;
  onStatusChange: (value?: FloorStatus) => void;
  onResetFilters: () => void;
  onView: (floor: Floor) => void;
  onEdit: (floor: Floor) => void;
  onDeactivate: (floor: Floor) => void;
  onDelete?: (floor: Floor) => void;
}) {
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  const canDeleteFloor = canDelete ?? canDeactivate;
  const handleDelete = onDelete ?? onDeactivate;

  // Summary Metrics
  const summary = useMemo(() => {
    const totalFloors = allFloors.length;
    const activeFloors = allFloors.filter((f) => f.status === "active").length;
    const inactiveFloors = allFloors.filter(
      (f) => f.status === "inactive",
    ).length;
    const totalRooms = allFloors.reduce(
      (sum, f) => sum + (f.roomCount || 0),
      0,
    );
    return { totalFloors, activeFloors, inactiveFloors, totalRooms };
  }, [allFloors]);

  const columns = useMemo<ColumnDef<Floor>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <div className="flex items-center pl-1">
            <Checkbox
              aria-label="Chọn tất cả tầng"
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
              aria-label={`Chọn ${row.original.name}`}
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
        accessorKey: "floorNumber",
        header: "Số tầng",
        cell: ({ row }) => (
          <div className="flex items-center gap-2.5">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
              <Layers className="size-3.5" />
            </div>
            <span className="tabular-nums font-semibold font-mono text-foreground text-sm">
              Tầng {row.original.floorNumber}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "name",
        header: "Tên tầng",
        cell: ({ row }) => (
          <span className="font-semibold text-foreground text-sm">
            {row.original.name}
          </span>
        ),
      },
      {
        accessorKey: "roomCount",
        header: "Số phòng",
        cell: ({ row }) => (
          <div className="inline-flex items-center gap-2 text-sm text-foreground">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
              <DoorClosed className="size-3.5" />
            </div>
            <span className="tabular-nums font-semibold font-mono">
              {row.original.roomCount}
            </span>
            <span className="text-muted-foreground text-xs">phòng</span>
          </div>
        ),
      },
      {
        accessorKey: "status",
        header: "Trạng thái",
        cell: ({ row }) => (
          <Badge
            variant={row.original.status === "active" ? "success" : "secondary"}
            className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
          >
            <span
              className={cn(
                "size-1.5 rounded-full",
                row.original.status === "active"
                  ? "bg-emerald-500"
                  : "bg-muted-foreground/60",
              )}
            />
            {statusLabels[row.original.status]}
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
              <DropdownMenuContent align="end" className="w-44">
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
                {canDeleteFloor ? (
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
                      Xóa tầng
                    </DropdownMenuItem>
                  </>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [canDeleteFloor, canUpdate, handleDelete, onEdit, onView],
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

  const selectedFloors = table
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
            icon={Layers}
            label="Tổng số tầng"
            value={summary.totalFloors.toLocaleString("vi-VN")}
            helper="Tổng số tầng thuộc tòa nhà"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Đang hoạt động"
            value={summary.activeFloors.toLocaleString("vi-VN")}
            trend="positive"
            helper="Tầng đang mở tiếp nhận sinh viên"
          />
          <KpiMetric
            icon={Power}
            label="Ngừng sử dụng"
            value={summary.inactiveFloors.toLocaleString("vi-VN")}
            trend={summary.inactiveFloors > 0 ? "negative" : "neutral"}
            helper="Tầng tạm ngưng sử dụng hoặc bảo trì"
          />
          <KpiMetric
            icon={DoorClosed}
            label="Tổng số phòng"
            value={summary.totalRooms.toLocaleString("vi-VN")}
            helper="Tổng phòng trên tất cả các tầng"
          />
        </CardContent>
      </Card>

      {/* 2. Toolbar: Tìm kiếm & Lọc trạng thái */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:w-80">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 text-xs w-full"
            value={query}
            placeholder="Tìm theo tên hoặc số tầng..."
            aria-label="Tìm kiếm tầng"
            onChange={(event) => onQueryChange(event.target.value)}
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
                value === "all" ? undefined : (value as FloorStatus),
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
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                  Số tầng
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                  Tên tầng
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                  Số phòng
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                  Trạng thái
                </TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {["one", "two", "three", "four"].map((key) => (
                <TableRow key={key}>
                  {[
                    "select",
                    "floor",
                    "name",
                    "rooms",
                    "status",
                    "actions",
                  ].map((cellKey) => (
                    <TableCell key={`${key}-${cellKey}`}>
                      <Skeleton className="h-5 w-full rounded" />
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
            icon={Layers}
            title="Không thể tải danh sách tầng"
            description={
              errorMessage ?? "Hãy kiểm tra kết nối mạng và thử lại."
            }
            action={{
              label: "Thử lại",
              onClick: onRetry,
            }}
          />
        </div>
      ) : (
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
                  <TableCell colSpan={6} className="p-8">
                    <EmptyState
                      icon={Layers}
                      title={
                        hasActiveFilters
                          ? "Không có tầng phù hợp với bộ lọc"
                          : allFloors.length
                            ? "Không có tầng ở trang này"
                            : "Chưa có tầng nào thuộc tòa nhà này"
                      }
                      description={
                        hasActiveFilters
                          ? "Hãy thử tìm kiếm với từ khóa khác hoặc xóa bộ lọc."
                          : "Tạo tầng đầu tiên để bắt đầu quản lý phòng ở."
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
      )}

      {/* 4. Thanh công cụ thao tác hàng loạt khi có dòng được chọn */}
      {selectedFloors.length > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedFloors.length}
          selectedLabel="tầng"
          onClear={() => setRowSelection({})}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => {
                  exportFloorsToExcel(selectedFloors);
                  toast.success(
                    `Đã xuất dữ liệu ${selectedFloors.length} tầng ra file Excel thành công.`,
                  );
                }}
                aria-label="Xuất Excel"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Xuất Excel ({selectedFloors.length} tầng)
            </TooltipContent>
          </Tooltip>

          {canDeleteFloor ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="destructive"
                  size="icon"
                  className="size-8 rounded-xl shadow-2xs"
                  onClick={() => {
                    handleDelete(selectedFloors[0]);
                  }}
                  aria-label="Xóa đã chọn"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">Xóa các tầng đã chọn</TooltipContent>
            </Tooltip>
          ) : null}
        </DataTableBulkActions>
      ) : null}
    </div>
  );
}
