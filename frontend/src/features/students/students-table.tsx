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
  RotateCcw,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DataTableViewOptions } from "@/components/admin/data-table/data-table-view-options";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import type { Student, StudentStatus } from "@/features/students/types";
import { exportToExcel } from "@/lib/excel-export";
import { cn } from "@/lib/utils";

const statusLabels: Record<StudentStatus, string> = {
  studying: "Đang học",
  paused: "Tạm dừng",
  graduated: "Đã tốt nghiệp",
  unknown: "Chưa xác định",
  inactive: "Ngừng hoạt động",
};

const genderLabels: Record<string, string> = {
  male: "Nam",
  female: "Nữ",
  other: "Khác",
  nam: "Nam",
  nu: "Nữ",
  nữ: "Nữ",
  "1": "Nam",
  "0": "Nữ",
};

const labels = {
  studentCode: "Mã sinh viên",
  fullName: "Họ tên",
  faculty: "Khoa",
  className: "Lớp",
  gender: "Giới tính",
  status: "Trạng thái",
};

function exportStudentsToExcel(students: Student[]) {
  exportToExcel({
    filename: `danh_sach_sinh_vien_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Sinh viên",
    data: students,
    columns: [
      { header: "Mã sinh viên", accessor: (s) => s.studentCode },
      { header: "Họ và tên", accessor: (s) => s.fullName },
      { header: "Khoa", accessor: (s) => s.faculty || "" },
      { header: "Lớp", accessor: (s) => s.className || "" },
      {
        header: "Giới tính",
        accessor: (s) => genderLabels[s.gender] || s.gender,
      },
      {
        header: "Email trường",
        accessor: (s) =>
          s.schoolEmail ||
          (s.studentCode
            ? `${s.studentCode.toLowerCase()}@st.qnu.edu.vn`
            : s.email || ""),
      },
      { header: "Số điện thoại", accessor: (s) => s.phoneNumber || "" },
      {
        header: "Trạng thái",
        accessor: (s) => statusLabels[s.status] || s.status,
      },
    ],
  });
}

export function StudentsTable({
  data,
  query,
  faculty,
  status,
  page,
  pageSize,
  total,
  totalPages,
  isLoading,
  isError,
  errorMessage,
  hasStudents,
  hasFilters,
  canUpdate,
  canDeactivate,
  onRetry,
  onQueryChange,
  onFacultyChange,
  onStatusChange,
  onReset,
  onPageChange,
  onPageSizeChange,
  onView,
  onEdit,
  onDeactivate,
}: {
  data: Student[];
  query: string;
  faculty: string;
  status?: StudentStatus;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  hasStudents: boolean;
  hasFilters: boolean;
  canUpdate: boolean;
  canDeactivate: boolean;
  onRetry: () => void;
  onQueryChange: (value: string) => void;
  onFacultyChange: (value: string) => void;
  onStatusChange: (value?: StudentStatus) => void;
  onReset: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  onView: (student: Student) => void;
  onEdit: (student: Student) => void;
  onDeactivate: (student: Student) => void;
}) {
  const [visibility, setVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  const columns = useMemo<ColumnDef<Student>[]>(
    () => [
      {
        id: "select",
        enableSorting: false,
        enableHiding: false,
        size: 40,
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
              aria-label="Chọn tất cả sinh viên trang này"
            />
          </div>
        ),
        cell: ({ row }) => (
          <div
            className="flex items-center pl-1"
            onClick={(e) => e.stopPropagation()}
          >
            <Checkbox
              checked={row.getIsSelected()}
              onCheckedChange={(value) => row.toggleSelected(Boolean(value))}
              aria-label={`Chọn ${row.original.fullName}`}
            />
          </div>
        ),
      },
      {
        accessorKey: "studentCode",
        header: labels.studentCode,
        cell: ({ row }) => (
          <span className="font-mono font-medium text-xs bg-muted/60 px-2 py-0.5 rounded text-foreground">
            {row.original.studentCode}
          </span>
        ),
      },
      {
        accessorKey: "fullName",
        header: labels.fullName,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="font-semibold text-foreground hover:text-primary transition-colors">
              {row.original.fullName}
            </span>
            {row.original.schoolEmail ||
            row.original.studentCode ||
            row.original.phoneNumber ? (
              <span className="text-[11px] text-muted-foreground">
                {row.original.schoolEmail ||
                  (row.original.studentCode
                    ? `${row.original.studentCode.toLowerCase()}@st.qnu.edu.vn`
                    : row.original.phoneNumber)}
              </span>
            ) : null}
          </div>
        ),
      },
      {
        accessorKey: "faculty",
        header: labels.faculty,
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.original.faculty || "—"}
          </span>
        ),
      },
      {
        accessorKey: "className",
        header: labels.className,
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.original.className || "—"}
          </span>
        ),
      },
      {
        accessorKey: "gender",
        header: labels.gender,
        cell: ({ row }) => {
          const raw = String(row.original.gender ?? "")
            .toLowerCase()
            .trim();
          const isMale = raw === "male" || raw === "nam" || raw === "1";
          const isFemale =
            raw === "female" || raw === "nu" || raw === "nữ" || raw === "0";
          const text = isMale
            ? "Nam"
            : isFemale
              ? "Nữ"
              : genderLabels[raw] || row.original.gender || "—";

          if (isMale) {
            return (
              <Badge
                variant="outline"
                className="bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-800 text-[11px] font-semibold px-2 py-0"
              >
                Nam
              </Badge>
            );
          }
          if (isFemale) {
            return (
              <Badge
                variant="outline"
                className="bg-pink-50 text-pink-700 border-pink-200 dark:bg-pink-950/40 dark:text-pink-300 dark:border-pink-800 text-[11px] font-semibold px-2 py-0"
              >
                Nữ
              </Badge>
            );
          }
          return <span className="text-muted-foreground">{text}</span>;
        },
      },
      {
        accessorKey: "status",
        header: labels.status,
        cell: ({ row }) => {
          const s = row.original.status;
          return (
            <Badge
              variant="outline"
              className={cn(
                "gap-1.5 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide shrink-0",
                s === "studying" &&
                  "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
                s === "graduated" &&
                  "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
                s === "paused" &&
                  "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
                s === "inactive" &&
                  "bg-destructive/15 text-destructive border-destructive/30",
                s === "unknown" && "bg-muted text-muted-foreground",
              )}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  s === "studying" && "bg-emerald-500",
                  s === "graduated" && "bg-blue-500",
                  s === "paused" && "bg-amber-500",
                  s === "inactive" && "bg-destructive",
                  s === "unknown" && "bg-muted-foreground/60",
                )}
              />
              {statusLabels[s] || s}
            </Badge>
          );
        },
      },
      {
        id: "actions",
        enableHiding: false,
        header: "",
        cell: ({ row }) => (
          <div
            className="flex justify-end"
            onClick={(e) => e.stopPropagation()}
          >
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Thao tác với ${row.original.fullName}`}
                >
                  <MoreHorizontal className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => onView(row.original)}>
                  <Eye className="size-4 mr-2" />
                  Xem chi tiết
                </DropdownMenuItem>
                {canUpdate ? (
                  <DropdownMenuItem onSelect={() => onEdit(row.original)}>
                    <Pencil className="size-4 mr-2" />
                    Chỉnh sửa
                  </DropdownMenuItem>
                ) : null}
                {canDeactivate && row.original.status !== "graduated" ? (
                  <DropdownMenuItem
                    onSelect={() => onDeactivate(row.original)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Power className="size-4 mr-2" />
                    Ngừng hồ sơ
                  </DropdownMenuItem>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [canDeactivate, canUpdate, onDeactivate, onEdit, onView],
  );

  const table = useReactTable({
    data,
    columns,
    state: {
      columnVisibility: visibility,
      rowSelection,
    },
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onColumnVisibilityChange: setVisibility,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,
  });

  const selectedStudents = useMemo(
    () => table.getSelectedRowModel().rows.map((row) => row.original),
    [table, rowSelection],
  );

  return (
    <div className="space-y-4">
      {/* 1. Responsive Filters Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-xs">
          <DebouncedSearchInput
            className="h-9 text-xs"
            value={query}
            placeholder="Tìm theo mã hoặc tên..."
            aria-label="Tìm kiếm sinh viên"
            onChange={onQueryChange}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="w-full sm:w-44">
            <DebouncedSearchInput
              className="h-9 text-xs"
              value={faculty}
              placeholder="Lọc theo khoa..."
              aria-label="Lọc theo khoa"
              showSearchIcon={false}
              onChange={onFacultyChange}
            />
          </div>
          <Select
            value={status ?? "all"}
            onValueChange={(value) =>
              onStatusChange(
                value === "all" ? undefined : (value as StudentStatus),
              )
            }
          >
            <SelectTrigger
              className="w-full sm:w-40 h-9 text-xs"
              aria-label="Lọc trạng thái"
            >
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              {Object.entries(statusLabels).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {hasFilters ? (
            <Button
              variant="outline"
              size="sm"
              className="h-9 px-2.5 text-xs text-muted-foreground hover:text-foreground"
              onClick={onReset}
            >
              <RotateCcw className="size-3.5 mr-1" />
              Đặt lại
            </Button>
          ) : null}

          <DataTableViewOptions table={table} labels={labels} />
        </div>
      </div>

      {/* 2. Main Table & Integrated Pagination */}
      {isLoading ? (
        <div className="rounded-xl border bg-card p-6 shadow-2xs">
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((row) => (
              <Skeleton key={row} className="h-9 w-full rounded" />
            ))}
          </div>
        </div>
      ) : isError ? (
        <div className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-card px-5 py-8 text-center shadow-2xs">
          <p className="font-semibold text-foreground">
            Không thể tải danh sách sinh viên
          </p>
          <p className="text-xs text-muted-foreground max-w-sm">
            {errorMessage ?? "Hãy kiểm tra kết nối mạng và thử lại."}
          </p>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Thử lại
          </Button>
        </div>
      ) : (
        <>
          <div className="rounded-xl border bg-card shadow-2xs overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-muted/40 hover:bg-muted/40">
                  {table.getHeaderGroups().map((group) => (
                    <TableRow key={group.id} className="hover:bg-transparent">
                      {group.headers.map((header) => (
                        <TableHead
                          key={header.id}
                          className="text-xs font-semibold text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap"
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
                        data-state={row.getIsSelected() && "selected"}
                        className="cursor-pointer hover:bg-muted/40 transition-colors"
                        onClick={() => onView(row.original)}
                      >
                        {row.getVisibleCells().map((cell) => (
                          <TableCell
                            key={cell.id}
                            className="text-xs sm:text-sm py-3.5"
                          >
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
                            hasFilters
                              ? "Không có sinh viên phù hợp với bộ lọc"
                              : hasStudents
                                ? "Không có sinh viên ở trang này"
                                : "Chưa có sinh viên nào"
                          }
                          description={
                            hasFilters
                              ? "Hãy mở rộng tìm kiếm hoặc xóa bộ lọc."
                              : "Tạo hồ sơ sinh viên đầu tiên để bắt đầu quản lý."
                          }
                          action={
                            hasFilters
                              ? { label: "Xóa bộ lọc", onClick: onReset }
                              : undefined
                          }
                        />
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* Clean borderless pagination directly below table */}
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

      {/* 3. Bulk Actions Floating Bar */}
      {selectedStudents.length > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedStudents.length}
          selectedLabel="sinh viên"
          onClear={() => setRowSelection({})}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => {
                  exportStudentsToExcel(selectedStudents);
                  toast.success(
                    `Đã xuất dữ liệu ${selectedStudents.length} sinh viên ra file Excel thành công.`,
                  );
                }}
                aria-label="Xuất Excel"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Xuất Excel ({selectedStudents.length} sinh viên)
            </TooltipContent>
          </Tooltip>
        </DataTableBulkActions>
      ) : null}
    </div>
  );
}
