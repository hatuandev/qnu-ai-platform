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
  Clock,
  DoorClosed,
  Download,
  Eye,
  MoreHorizontal,
  Pencil,
  Power,
  RotateCcw,
  Trash2,
  Wrench,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Combobox } from "@/components/admin/combobox";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DataTableViewOptions } from "@/components/admin/data-table/data-table-view-options";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
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
import { useBuildingsQuery } from "@/features/buildings/api";
import { useFloorsQuery } from "@/features/floors/api";
import { useRoomTypesQuery } from "@/features/room-types/api";
import { roomStatusLabels } from "@/features/rooms/api";
import type { Room, RoomStatus } from "@/features/rooms/types";
import { exportToExcel } from "@/lib/excel-export";
import { cn } from "@/lib/utils";

const columnLabels: Record<string, string> = {
  code: "Mã phòng",
  name: "Tên phòng",
  buildingName: "Tòa nhà",
  floorNumber: "Tầng",
  roomTypeName: "Loại phòng",
  capacity: "Sức chứa",
  places: "Chỗ còn trống",
  status: "Trạng thái",
};

const statusDotColors: Record<RoomStatus, string> = {
  available: "bg-emerald-500",
  full: "bg-amber-500",
  maintenance: "bg-destructive",
  inactive: "bg-muted-foreground/60",
};

const roomStatusVariants: Record<
  RoomStatus,
  "success" | "warning" | "destructive" | "secondary"
> = {
  available: "success",
  full: "warning",
  maintenance: "destructive",
  inactive: "secondary",
};

const statusOptions: Array<{ value: string; label: string }> = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "available", label: "Còn trống" },
  { value: "full", label: "Đã đủ chỗ" },
  { value: "maintenance", label: "Bảo trì" },
  { value: "inactive", label: "Ngừng sử dụng" },
];

function StatusBadge({ status }: { status: RoomStatus }) {
  return (
    <Badge
      variant={roomStatusVariants[status]}
      className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
    >
      <span className={cn("size-1.5 rounded-full", statusDotColors[status])} />
      {roomStatusLabels[status]}
    </Badge>
  );
}

function exportRoomsToExcel(rooms: Room[]) {
  exportToExcel({
    filename: `danh_sach_phong_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Phòng",
    data: rooms,
    columns: [
      { header: "Mã phòng", accessor: (r) => r.code },
      { header: "Tên phòng", accessor: (r) => r.name },
      {
        header: "Tòa nhà",
        accessor: (r) => `${r.buildingName ?? ""} (${r.buildingCode})`,
      },
      { header: "Tầng", accessor: (r) => `Tầng ${r.floorNumber}` },
      { header: "Loại phòng", accessor: (r) => r.roomTypeName },
      { header: "Sức chứa", accessor: (r) => r.capacity },
      {
        header: "Chỗ còn trống",
        accessor: (r) => `${r.availablePlaces}/${r.operationalCapacity}`,
      },
      {
        header: "Trạng thái",
        accessor: (r) => roomStatusLabels[r.status] || r.status,
      },
    ],
  });
}

export function RoomsTable({
  data,
  total,
  totalPages,
  page,
  pageSize,
  isLoading,
  isError,
  errorMessage,
  hasRooms,
  hasActiveFilters,
  query,
  buildingId,
  floorId,
  roomTypeId,
  status,
  onRetry,
  onQueryChange,
  onBuildingChange,
  onFloorChange,
  onRoomTypeChange,
  onStatusChange,
  onResetFilters,
  onPageChange,
  onPageSizeChange,
  onView,
  onEdit,
  onDeactivate,
  onDelete,
  onDeleteBatch,
  canUpdate,
  canDeactivate,
  canDelete,
}: {
  data: Room[];
  total: number;
  totalPages: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  hasRooms: boolean;
  hasActiveFilters: boolean;
  query: string;
  buildingId?: string;
  floorId?: string;
  roomTypeId?: string;
  status?: RoomStatus;
  onRetry: () => void;
  onQueryChange: (value: string) => void;
  onBuildingChange: (value?: string) => void;
  onFloorChange: (value?: string) => void;
  onRoomTypeChange: (value?: string) => void;
  onStatusChange: (value?: RoomStatus) => void;
  onResetFilters: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onView: (room: Room) => void;
  onEdit: (room: Room) => void;
  onDeactivate: (room: Room) => void;
  onDelete?: (room: Room) => void;
  onDeleteBatch?: (rooms: Room[]) => void;
  canUpdate: boolean;
  canDeactivate: boolean;
  canDelete?: boolean;
}) {
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  const canDeleteRoom = canDelete ?? canDeactivate;
  const handleDelete = onDelete ?? onDeactivate;

  const buildingsQuery = useBuildingsQuery({
    page: 1,
    pageSize: 100,
    status: "active",
  });
  const floorsQuery = useFloorsQuery(buildingId);
  const roomTypesQuery = useRoomTypesQuery({
    page: 1,
    pageSize: 100,
    isActive: true,
  });

  const buildings = buildingsQuery.data?.items ?? [];
  const floors = floorsQuery.data ?? [];
  const roomTypes = roomTypesQuery.data?.items ?? [];

  const buildingOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả tòa nhà" },
      ...buildings.map((b) => ({
        value: b.id,
        label: `${b.code} · ${b.name}`,
      })),
    ],
    [buildings],
  );

  const floorOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả tầng" },
      ...floors.map((f) => ({
        value: f.id,
        label: `Tầng ${f.floorNumber} · ${f.name}`,
      })),
    ],
    [floors],
  );

  const roomTypeOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả loại phòng" },
      ...roomTypes.map((rt) => ({
        value: rt.id,
        label: `${rt.code} · ${rt.name}`,
      })),
    ],
    [roomTypes],
  );

  // Summary Metrics
  const summary = useMemo(() => {
    const totalCount = total;
    const availableCount = data.filter((r) => r.status === "available").length;
    const fullCount = data.filter((r) => r.status === "full").length;
    const maintenanceCount = data.filter(
      (r) => r.status === "maintenance" || r.status === "inactive",
    ).length;
    return { totalCount, availableCount, fullCount, maintenanceCount };
  }, [data, total]);

  const columns = useMemo<ColumnDef<Room>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <div className="flex items-center pl-1">
            <Checkbox
              aria-label="Chọn tất cả phòng trên trang này"
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
              aria-label={`Chọn phòng ${row.original.name}`}
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
        header: "Mã phòng",
        cell: ({ row }) => (
          <Badge variant="outline" className="font-mono text-xs">
            {row.original.code}
          </Badge>
        ),
      },
      {
        accessorKey: "name",
        header: "Tên phòng",
        cell: ({ row }) => (
          <span className="font-semibold text-foreground text-sm">
            {row.original.name}
          </span>
        ),
      },
      {
        accessorKey: "buildingName",
        header: "Tòa nhà",
        cell: ({ row }) => (
          <span className="text-sm text-foreground">
            {row.original.buildingName}
            <span className="type-supporting ml-1 text-muted-foreground text-xs font-mono">
              ({row.original.buildingCode})
            </span>
          </span>
        ),
      },
      {
        accessorKey: "floorNumber",
        header: "Tầng",
        cell: ({ row }) => (
          <span className="tabular-nums font-mono text-sm text-foreground">
            Tầng {row.original.floorNumber}
          </span>
        ),
      },
      {
        accessorKey: "roomTypeName",
        header: "Loại phòng",
        cell: ({ row }) => (
          <span className="text-sm text-foreground">
            {row.original.roomTypeName}
          </span>
        ),
      },
      {
        accessorKey: "capacity",
        header: "Sức chứa",
        cell: ({ row }) => (
          <span className="tabular-nums font-mono text-sm text-foreground">
            {row.original.capacity} chỗ
          </span>
        ),
      },
      {
        id: "places",
        header: "Chỗ còn trống",
        cell: ({ row }) => (
          <span className="tabular-nums font-mono font-semibold text-sm text-foreground">
            {row.original.availablePlaces}/{row.original.operationalCapacity}{" "}
            chỗ
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
                {canDeactivate && row.original.status !== "inactive" ? (
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
                {canDeleteRoom ? (
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
                      Xóa phòng
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
      canDeleteRoom,
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

  const selectedRooms = table.getSelectedRowModel().rows.map((r) => r.original);

  const viewOptions = (
    <DataTableViewOptions table={table} labels={columnLabels} />
  );

  return (
    <div className="space-y-6">
      {/* 1. Top KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={DoorClosed}
            label="Tổng số phòng"
            value={summary.totalCount.toLocaleString("vi-VN")}
            helper="Tổng số phòng trong danh mục"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Còn chỗ trống"
            value={summary.availableCount.toLocaleString("vi-VN")}
            trend="positive"
            helper="Phòng sẵn sàng tiếp nhận sinh viên"
          />
          <KpiMetric
            icon={Clock}
            label="Đã đủ chỗ"
            value={summary.fullCount.toLocaleString("vi-VN")}
            helper="Phòng đã đạt tối đa sức chứa"
          />
          <KpiMetric
            icon={Wrench}
            label="Bảo trì / Ngừng dùng"
            value={summary.maintenanceCount.toLocaleString("vi-VN")}
            trend={summary.maintenanceCount > 0 ? "negative" : "neutral"}
            helper="Phòng tạm ngưng phục vụ"
          />
        </CardContent>
      </Card>

      {/* 2. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {/* Ô tìm kiếm */}
          <div className="sm:col-span-2 lg:col-span-1">
            <DebouncedSearchInput
              className="w-full text-xs"
              value={query}
              placeholder="Tìm mã hoặc tên phòng..."
              aria-label="Tìm kiếm phòng"
              onChange={onQueryChange}
            />
          </div>

          {/* Tòa nhà */}
          <Combobox
            className="w-full text-xs"
            options={buildingOptions}
            value={buildingId ?? "all"}
            searchPlaceholder="Tìm tòa nhà..."
            onValueChange={(value) =>
              onBuildingChange(value === "all" ? undefined : value)
            }
          />

          {/* Tầng */}
          <Combobox
            className="w-full text-xs"
            options={floorOptions}
            value={floorId ?? "all"}
            searchPlaceholder="Tìm tầng..."
            disabled={!buildingId}
            onValueChange={(value) =>
              onFloorChange(value === "all" ? undefined : value)
            }
          />

          {/* Loại phòng */}
          <Combobox
            className="w-full text-xs"
            options={roomTypeOptions}
            value={roomTypeId ?? "all"}
            searchPlaceholder="Tìm loại phòng..."
            onValueChange={(value) =>
              onRoomTypeChange(value === "all" ? undefined : value)
            }
          />

          {/* Trạng thái */}
          <Combobox
            className="w-full text-xs"
            options={statusOptions}
            value={status ?? "all"}
            searchPlaceholder="Tìm trạng thái..."
            onValueChange={(value) =>
              onStatusChange(
                value === "all" ? undefined : (value as RoomStatus),
              )
            }
          />
        </div>

        <div className="flex items-center justify-between gap-2">
          <div>
            {hasActiveFilters && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                onClick={onResetFilters}
              >
                <RotateCcw className="size-3.5 mr-1" />
                <span>Đặt lại bộ lọc</span>
              </Button>
            )}
          </div>
          <div>{viewOptions}</div>
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
              {["one", "two", "three", "four", "five", "six"].map((key) => (
                <TableRow key={key}>
                  {[
                    "select",
                    "code",
                    "name",
                    "building",
                    "floor",
                    "type",
                    "capacity",
                    "places",
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
            icon={DoorClosed}
            title="Không thể tải danh sách phòng"
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
                        icon={DoorClosed}
                        title={
                          hasActiveFilters
                            ? "Không có phòng phù hợp với bộ lọc"
                            : hasRooms
                              ? "Không có phòng ở trang này"
                              : "Chưa có phòng nào"
                        }
                        description={
                          hasActiveFilters
                            ? "Hãy mở rộng tìm kiếm hoặc xóa bớt các bộ lọc."
                            : hasRooms
                              ? "Hãy thử trang khác hoặc thay đổi số dòng mỗi trang."
                              : "Tạo phòng đầu tiên để bắt đầu quản lý chỗ ở ký túc xá."
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
      {selectedRooms.length > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedRooms.length}
          selectedLabel="phòng"
          onClear={() => setRowSelection({})}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => {
                  exportRoomsToExcel(selectedRooms);
                  toast.success(
                    `Đã xuất dữ liệu ${selectedRooms.length} phòng ra file Excel thành công.`,
                  );
                }}
                aria-label="Xuất Excel"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Xuất Excel ({selectedRooms.length} phòng)
            </TooltipContent>
          </Tooltip>

          {canDeleteRoom ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="destructive"
                  size="icon"
                  className="size-8 rounded-xl shadow-2xs"
                  onClick={() => {
                    if (onDeleteBatch) {
                      onDeleteBatch(selectedRooms);
                    } else {
                      handleDelete(selectedRooms[0]);
                    }
                  }}
                  aria-label="Xóa đã chọn"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">Xóa các phòng đã chọn</TooltipContent>
            </Tooltip>
          ) : null}
        </DataTableBulkActions>
      ) : null}
    </div>
  );
}
