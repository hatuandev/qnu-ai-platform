import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  type RowSelectionState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import {
  Download,
  Eye,
  MoreHorizontal,
  Pencil,
  Power,
  Search,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DataTableViewOptions } from "@/components/admin/data-table/data-table-view-options";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { AcademicYear } from "@/features/academic-years/types";
import { exportToExcel } from "@/lib/excel-export";

const labels: Record<string, string> = {
  code: "Mã",
  name: "Tên năm học",
  startDate: "Bắt đầu",
  endDate: "Kết thúc",
  isCurrent: "Trạng thái",
};

function displayDate(value: string) {
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

function exportAcademicYearsToExcel(years: AcademicYear[]) {
  exportToExcel({
    filename: `danh_sach_nam_hoc_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Năm học",
    data: years,
    columns: [
      { header: "Mã năm học", accessor: (y) => y.code },
      { header: "Tên năm học", accessor: (y) => y.name },
      { header: "Ngày bắt đầu", accessor: (y) => displayDate(y.startDate) },
      { header: "Ngày kết thúc", accessor: (y) => displayDate(y.endDate) },
      {
        header: "Trạng thái",
        accessor: (y) => (y.isCurrent ? "Đang hiện tại" : "Đã lưu trữ"),
      },
    ],
  });
}

export function AcademicYearsTable({
  data,
  total,
  totalPages,
  page,
  pageSize,
  isLoading,
  isError,
  errorMessage,
  hasAcademicYears,
  hasActiveFilters,
  query,
  isCurrent,
  canUpdate,
  canDeactivate,
  canDelete,
  onRetry,
  onQueryChange,
  onCurrentChange,
  onResetFilters,
  onPageChange,
  onPageSizeChange,
  onView,
  onEdit,
  onDeactivate,
  onDelete,
}: {
  data: AcademicYear[];
  total: number;
  totalPages: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  hasAcademicYears: boolean;
  hasActiveFilters: boolean;
  query: string;
  isCurrent?: boolean;
  canUpdate: boolean;
  canDeactivate: boolean;
  canDelete?: boolean;
  onRetry: () => void;
  onQueryChange: (value: string) => void;
  onCurrentChange: (value?: boolean) => void;
  onResetFilters: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onView: (year: AcademicYear) => void;
  onEdit: (year: AcademicYear) => void;
  onDeactivate: (year: AcademicYear) => void;
  onDelete?: (year: AcademicYear) => void;
}) {
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const canDeleteYear = canDelete ?? canDeactivate;
  const handleDelete = onDelete ?? onDeactivate;

  const columns = useMemo<ColumnDef<AcademicYear>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <div className="flex items-center pl-1">
            <Checkbox
              aria-label="Chọn tất cả năm học"
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
        accessorKey: "code",
        header: "Mã",
        cell: ({ row }) => (
          <span className="type-supporting font-mono font-semibold text-sm text-foreground">
            {row.original.code}
          </span>
        ),
      },
      {
        accessorKey: "name",
        header: "Tên năm học",
        cell: ({ row }) => (
          <span className="font-semibold text-foreground text-sm">
            {row.original.name}
          </span>
        ),
      },
      {
        accessorKey: "startDate",
        header: "Bắt đầu",
        cell: ({ row }) => (
          <span className="text-sm text-foreground">
            {displayDate(row.original.startDate)}
          </span>
        ),
      },
      {
        accessorKey: "endDate",
        header: "Kết thúc",
        cell: ({ row }) => (
          <span className="text-sm text-foreground">
            {displayDate(row.original.endDate)}
          </span>
        ),
      },
      {
        accessorKey: "isCurrent",
        header: "Trạng thái",
        cell: ({ row }) => (
          <Badge
            variant={row.original.isCurrent ? "success" : "secondary"}
            className="gap-1.5 font-medium px-2.5 py-0.5"
          >
            <span
              className={`size-1.5 rounded-full ${
                row.original.isCurrent
                  ? "bg-emerald-500"
                  : "bg-muted-foreground/60"
              }`}
            />
            {row.original.isCurrent ? "Hiện tại" : "Đã lưu trữ"}
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
                  onSelect={() => onView(row.original)}
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
                    onSelect={() => onEdit(row.original)}
                    onClick={(event) => {
                      event.stopPropagation();
                      onEdit(row.original);
                    }}
                  >
                    <Pencil className="size-4 mr-2 text-muted-foreground" />
                    Chỉnh sửa
                  </DropdownMenuItem>
                ) : null}
                {canDeactivate && row.original.isCurrent ? (
                  <DropdownMenuItem
                    onSelect={() => onDeactivate(row.original)}
                    onClick={(event) => {
                      event.stopPropagation();
                      onDeactivate(row.original);
                    }}
                  >
                    <Power className="size-4 mr-2 text-amber-500" />
                    Ngừng năm học
                  </DropdownMenuItem>
                ) : null}
                {canDeleteYear ? (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-destructive focus:bg-destructive/10 focus:text-destructive"
                      onSelect={() => handleDelete(row.original)}
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDelete(row.original);
                      }}
                    >
                      <Trash2 className="size-4 mr-2 text-destructive" />
                      Xóa năm học
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
      canDeleteYear,
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

  const selectedYears = table.getSelectedRowModel().rows.map((r) => r.original);

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-sm">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 w-full"
            value={query}
            placeholder="Tìm theo mã hoặc tên năm học..."
            aria-label="Tìm kiếm năm học"
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={
              isCurrent === undefined
                ? "all"
                : isCurrent
                  ? "current"
                  : "archived"
            }
            onValueChange={(value) =>
              onCurrentChange(value === "all" ? undefined : value === "current")
            }
          >
            <SelectTrigger className="w-full sm:w-44" aria-label="Lọc năm học">
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả năm học</SelectItem>
              <SelectItem value="current">Đang hiện tại</SelectItem>
              <SelectItem value="archived">Đã lưu trữ</SelectItem>
            </SelectContent>
          </Select>
          {hasActiveFilters ? (
            <Button variant="ghost" size="sm" onClick={onResetFilters}>
              Xóa bộ lọc
            </Button>
          ) : null}
          <DataTableViewOptions table={table} labels={labels} />
        </div>
      </div>
      {isLoading ? (
        <div className="overflow-x-auto rounded-lg border bg-card shadow-xs">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40">
                <TableHead className="w-10 pl-3" />
                {Object.values(labels).map((label) => (
                  <TableHead
                    key={label}
                    className="font-semibold whitespace-nowrap"
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
                    "start",
                    "end",
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
        <div className="flex min-h-52 flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-card px-5 text-center shadow-xs">
          <p className="font-medium">Không thể tải danh sách năm học</p>
          <p className="text-sm text-muted-foreground">
            {errorMessage ?? "Hãy kiểm tra kết nối và thử lại."}
          </p>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Thử lại
          </Button>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border bg-card shadow-xs">
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
                      className="p-0"
                    >
                      <DataTableEmpty
                        title={
                          hasActiveFilters
                            ? "Không có năm học phù hợp với bộ lọc"
                            : hasAcademicYears
                              ? "Không có năm học ở trang này"
                              : "Chưa có năm học nào"
                        }
                        description={
                          hasActiveFilters
                            ? "Hãy mở rộng tìm kiếm hoặc xóa bộ lọc."
                            : "Tạo năm học đầu tiên để bắt đầu cấu hình học vụ."
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
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
          />
          <p className="text-xs text-muted-foreground">
            Tổng cộng {total} năm học
          </p>
        </>
      )}

      {/* Thanh công cụ thao tác hàng loạt khi có năm học được chọn */}
      {selectedYears.length > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedYears.length}
          selectedLabel="năm học"
          onClear={() => setRowSelection({})}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => {
                  exportAcademicYearsToExcel(selectedYears);
                  toast.success(
                    `Đã xuất dữ liệu ${selectedYears.length} năm học ra file Excel thành công.`,
                  );
                }}
                aria-label="Xuất Excel"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Xuất Excel ({selectedYears.length} năm học)
            </TooltipContent>
          </Tooltip>

          {canDeleteYear ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="destructive"
                  size="icon"
                  className="size-8 rounded-xl shadow-2xs"
                  onClick={() => {
                    handleDelete(selectedYears[0]);
                  }}
                  aria-label="Xóa đã chọn"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                Xóa các năm học đã chọn
              </TooltipContent>
            </Tooltip>
          ) : null}
        </DataTableBulkActions>
      ) : null}
    </div>
  );
}
