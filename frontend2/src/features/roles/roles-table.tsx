import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { Copy, Eye, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import {
  DataTableFacetedFilter,
  type DataTableFacetOption,
} from "@/components/admin/data-table/data-table-faceted-filter";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DataTableViewOptions } from "@/components/admin/data-table/data-table-view-options";
import { DataTableColumnHeader } from "@/components/admin/data-table-column-header";
import { StatusBadge } from "@/components/admin/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
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
import type { RoleRecord } from "@/rbac/demo";
import { roleTypeLabel } from "@/rbac/policy";

declare module "@tanstack/react-table" {
  interface ColumnMeta<TData, TValue> {
    className?: string;
  }
}

const columnLabels: Record<string, string> = {
  name: "Vai trò",
  description: "Mô tả",
  userCount: "Người dùng",
  permissions: "Quyền hạn",
  type: "Loại",
  status: "Trạng thái",
};
const loadingColumns = [
  "role",
  "description",
  "users",
  "permissions",
  "type",
  "status",
  "actions",
];

function toSorting(sort: string): SortingState {
  const [id, direction] = sort.split(".");
  return [{ id, desc: direction === "desc" }];
}

function toSort(sorting: SortingState) {
  const first = sorting[0];
  if (!first) return "name.asc";
  const id = ["name", "userCount", "permissions", "status"].includes(first.id)
    ? first.id
    : "name";
  return `${id}.${first.desc ? "desc" : "asc"}`;
}

export function RolesTable({
  data,
  totalCount,
  page,
  pageSize,
  sort,
  query,
  type,
  status,
  typeOptions,
  statusOptions,
  isLoading,
  isError,
  hasRoles,
  hasActiveFilters,
  onQueryChange,
  onTypeChange,
  onStatusChange,
  onResetFilters,
  onPageChange,
  onPageSizeChange,
  onSortChange,
  canUpdate,
  canCreate,
  canDelete,
  onView,
  onEdit,
  onDuplicate,
  onDelete,
}: {
  data: RoleRecord[];
  totalCount: number;
  page: number;
  pageSize: number;
  sort: string;
  query: string;
  type: string;
  status: string;
  typeOptions: DataTableFacetOption[];
  statusOptions: DataTableFacetOption[];
  isLoading: boolean;
  isError: boolean;
  hasRoles: boolean;
  hasActiveFilters: boolean;
  onQueryChange: (value: string) => void;
  onTypeChange: (values: string[]) => void;
  onStatusChange: (values: string[]) => void;
  onResetFilters: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onSortChange: (sort: string) => void;
  canUpdate: boolean;
  canCreate: boolean;
  canDelete: boolean;
  onView: (role: RoleRecord) => void;
  onEdit: (role: RoleRecord) => void;
  onDuplicate: (role: RoleRecord) => void;
  onDelete: (role: RoleRecord) => void;
}) {
  const [columnVisibility, setColumnVisibility] = useState<
    Record<string, boolean>
  >({});
  const sorting = useMemo(() => toSorting(sort), [sort]);
  const columns = useMemo<ColumnDef<RoleRecord>[]>(
    () => [
      {
        accessorKey: "name",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Vai trò" />
        ),
        cell: ({ row }) => (
          <div className="min-w-36">
            <div className="text-sm font-semibold">{row.original.name}</div>
            <div className="type-metadata font-mono text-muted-foreground">
              {row.original.key}
            </div>
          </div>
        ),
      },
      {
        accessorKey: "description",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Mô tả" />
        ),
        meta: { className: "hidden md:table-cell" },
        cell: ({ row }) => (
          <span className="type-supporting block max-w-64 truncate text-muted-foreground">
            {row.original.description}
          </span>
        ),
      },
      {
        accessorKey: "userCount",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Người dùng" />
        ),
        meta: { className: "hidden sm:table-cell" },
      },
      {
        id: "permissions",
        accessorFn: (role) => role.permissions.length,
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Quyền hạn" />
        ),
        meta: { className: "hidden lg:table-cell" },
        cell: ({ row }) => `${row.original.permissions.length} quyền`,
      },
      {
        id: "type",
        accessorFn: (role) => (role.isSystem ? "system" : "custom"),
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Loại" />
        ),
        meta: { className: "hidden sm:table-cell" },
        cell: ({ row }) => (
          <Badge variant={row.original.isSystem ? "secondary" : "outline"}>
            {roleTypeLabel(row.original)}
          </Badge>
        ),
      },
      {
        accessorKey: "status",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Trạng thái" />
        ),
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: "actions",
        enableHiding: false,
        enableSorting: false,
        cell: ({ row }) => {
          const role = row.original;
          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Thao tác với ${role.name}`}
                >
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Thao tác</DropdownMenuLabel>
                <DropdownMenuItem onSelect={() => onView(role)}>
                  <Eye />
                  Xem chi tiết
                </DropdownMenuItem>
                {canUpdate ? (
                  <DropdownMenuItem onSelect={() => onEdit(role)}>
                    <Pencil />
                    Chỉnh sửa
                  </DropdownMenuItem>
                ) : null}
                {canCreate ? (
                  <DropdownMenuItem onSelect={() => onDuplicate(role)}>
                    <Copy />
                    Nhân bản
                  </DropdownMenuItem>
                ) : null}
                {canDelete && !role.isSystem ? (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      variant="destructive"
                      onSelect={() => onDelete(role)}
                    >
                      <Trash2 />
                      Xóa
                    </DropdownMenuItem>
                  </>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          );
        },
      },
    ],
    [canCreate, canDelete, canUpdate, onDelete, onDuplicate, onEdit, onView],
  );
  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnVisibility },
    manualSorting: true,
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      onSortChange(toSort(next));
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  });
  const pageCount = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Tìm kiếm vai trò..."
          aria-label="Tìm kiếm vai trò"
          className="sm:max-w-sm"
        />
        <DataTableFacetedFilter
          title="Loại"
          options={typeOptions}
          selectedValues={type ? [type] : []}
          onChange={(values) => onTypeChange(values.slice(-1))}
        />
        <DataTableFacetedFilter
          title="Trạng thái"
          options={statusOptions}
          selectedValues={status ? [status] : []}
          onChange={(values) => onStatusChange(values.slice(-1))}
        />
        <div className="sm:ml-auto">
          <DataTableViewOptions table={table} labels={columnLabels} />
        </div>
      </div>
      {isLoading ? (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableBody>
              {["one", "two", "three", "four"].map((row) => (
                <TableRow key={row}>
                  {loadingColumns.map((column) => (
                    <TableCell key={`${row}-${column}`}>
                      <Skeleton className="h-4 w-24" />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : isError ? (
        <div className="flex min-h-48 flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-card px-5 text-center">
          <p className="font-medium">Không thể tải danh sách vai trò</p>
          <p className="text-sm text-muted-foreground">
            Hãy thử tải lại trang.
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border bg-card">
            <Table>
              <TableHeader className="bg-muted/30">
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead
                        key={header.id}
                        className={header.column.columnDef.meta?.className}
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
                {data.length ? (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id}>
                      {row.getVisibleCells().map((cell) => (
                        <TableCell
                          key={cell.id}
                          className={cell.column.columnDef.meta?.className}
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
                          hasActiveFilters
                            ? "Không có vai trò phù hợp với bộ lọc"
                            : hasRoles
                              ? "Không có vai trò ở trang này"
                              : "Chưa có vai trò nào"
                        }
                        description={
                          hasActiveFilters
                            ? "Hãy mở rộng tìm kiếm hoặc đặt lại bộ lọc."
                            : "Tạo vai trò tùy chỉnh để bắt đầu."
                        }
                        action={
                          hasActiveFilters
                            ? {
                                label: "Đặt lại bộ lọc",
                                onClick: onResetFilters,
                              }
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
            page={Math.min(page, pageCount)}
            pageSize={pageSize}
            pageCount={pageCount}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
          />
        </>
      )}
    </div>
  );
}
