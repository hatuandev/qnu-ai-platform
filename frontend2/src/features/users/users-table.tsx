import {
  flexRender,
  getCoreRowModel,
  type OnChangeFn,
  type RowSelectionState,
  type SortingState,
  type Updater,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import type { DataTableFacetOption } from "@/components/admin/data-table/data-table-faceted-filter";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DataTableViewOptions } from "@/components/admin/data-table/data-table-view-options";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { createUserColumns } from "@/features/users/columns";
import type { User, UserSort, UserStatus } from "@/features/users/types";
import { UsersBulkActions } from "@/features/users/users-bulk-actions";
import { UsersTableToolbar } from "@/features/users/users-table-toolbar";

const columnLabels: Record<string, string> = {
  name: "Người dùng",
  role: "Vai trò",
  status: "Trạng thái",
  createdAt: "Ngày tạo",
};
const loadingRows = ["one", "two", "three", "four", "five"];

function toSorting(sort: UserSort): SortingState {
  const [id, direction] = sort.split(".");
  return [{ id, desc: direction === "desc" }];
}

function toSort(sorting: SortingState): UserSort {
  const first = sorting[0];
  if (!first) return "createdAt.desc";
  const id =
    first.id === "name" ||
    first.id === "role" ||
    first.id === "status" ||
    first.id === "createdAt"
      ? first.id
      : "createdAt";
  return `${id}.${first.desc ? "desc" : "asc"}` as UserSort;
}

export function UsersTable({
  data,
  totalCount,
  page,
  pageSize,
  sort,
  isLoading,
  isError,
  errorMessage,
  hasUsers,
  hasActiveFilters,
  query,
  roleOptions,
  statusOptions,
  selectedRoles,
  selectedStatuses,
  canUpdate,
  canDelete,
  onRetry,
  onQueryChange,
  onRolesChange,
  onStatusesChange,
  onResetFilters,
  onPageChange,
  onPageSizeChange,
  onSortChange,
  onView,
  onEdit,
  onDelete,
  onStatusChange,
  onBulkUpdate,
  onBulkDelete,
}: {
  data: User[];
  totalCount: number;
  page: number;
  pageSize: number;
  sort: UserSort;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  hasUsers: boolean;
  hasActiveFilters: boolean;
  query: string;
  roleOptions: DataTableFacetOption[];
  statusOptions: DataTableFacetOption[];
  selectedRoles: string[];
  selectedStatuses: string[];
  canUpdate: boolean;
  canDelete: boolean;
  onRetry: () => void;
  onQueryChange: (value: string) => void;
  onRolesChange: (values: string[]) => void;
  onStatusesChange: (values: string[]) => void;
  onResetFilters: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onSortChange: (sort: UserSort) => void;
  onView: (user: User) => void;
  onEdit: (user: User) => void;
  onDelete: (user: User) => void;
  onStatusChange: (user: User, status: UserStatus) => void;
  onBulkUpdate: (users: User[], status: UserStatus) => void;
  onBulkDelete: (users: User[]) => void;
}) {
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const sorting = useMemo(() => toSorting(sort), [sort]);
  const columns = useMemo(
    () =>
      createUserColumns({
        canUpdate,
        canDelete,
        onView,
        onEdit,
        onDelete,
        onStatusChange,
      }),
    [canDelete, canUpdate, onDelete, onEdit, onStatusChange, onView],
  );

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      rowSelection,
      columnVisibility,
      pagination: { pageIndex: page - 1, pageSize },
    },
    getRowId: (row) => row.id,
    enableRowSelection: true,
    manualPagination: true,
    manualSorting: true,
    pageCount: Math.max(1, Math.ceil(totalCount / pageSize)),
    onRowSelectionChange: setRowSelection,
    onColumnVisibilityChange: setColumnVisibility,
    onSortingChange: ((updater: Updater<SortingState>) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      onSortChange(toSort(next));
    }) as OnChangeFn<SortingState>,
    onPaginationChange: (updater) => {
      const current = { pageIndex: page - 1, pageSize };
      const next = typeof updater === "function" ? updater(current) : updater;
      if (next.pageSize !== current.pageSize) onPageSizeChange(next.pageSize);
      if (next.pageIndex !== current.pageIndex) {
        onPageChange(next.pageIndex + 1);
      }
    },
    getCoreRowModel: getCoreRowModel(),
  });

  const selectedUsers = table
    .getSelectedRowModel()
    .rows.map((row) => row.original);
  const pageCount = Math.max(1, Math.ceil(totalCount / pageSize));
  const viewOptions = (
    <DataTableViewOptions table={table} labels={columnLabels} />
  );

  return (
    <div className="space-y-3">
      <UsersTableToolbar
        query={query}
        roleOptions={roleOptions}
        statusOptions={statusOptions}
        selectedRoles={selectedRoles}
        selectedStatuses={selectedStatuses}
        hasActiveFilters={hasActiveFilters}
        viewOptions={viewOptions}
        onQueryChange={onQueryChange}
        onRolesChange={onRolesChange}
        onStatusesChange={onStatusesChange}
        onReset={onResetFilters}
      />

      {isLoading ? (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader className="bg-muted/30">
              <TableRow>
                {[
                  ["selection", ""],
                  ["user", "User"],
                  ["role", "Vai trò"],
                  ["status", "Trạng thái"],
                  ["created", "Ngày tạo"],
                  ["actions", ""],
                ].map(([key, heading]) => (
                  <TableHead key={key}>{heading}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {loadingRows.map((row) => (
                <TableRow key={row}>
                  <TableCell>
                    <Skeleton className="size-4" />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2.5">
                      <Skeleton className="size-8 rounded-full" />
                      <div className="space-y-1.5">
                        <Skeleton className="h-3.5 w-28" />
                        <Skeleton className="h-3 w-40" />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-24" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="ml-auto size-8" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : isError ? (
        <div className="flex min-h-52 flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-card px-5 text-center">
          <p className="font-medium">Không thể tải danh sách người dùng</p>
          <p className="text-sm text-muted-foreground">
            {errorMessage ?? "Hãy kiểm tra kết nối và thử lại."}
          </p>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Thử lại
          </Button>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border bg-card">
            <Table>
              <TableHeader className="bg-muted/30">
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
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
                    <TableRow
                      key={row.id}
                      data-state={row.getIsSelected() ? "selected" : undefined}
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
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={table.getVisibleLeafColumns().length}
                      className="p-0"
                    >
                      <DataTableEmpty
                        title={
                          hasActiveFilters
                            ? "Không có người dùng phù hợp với bộ lọc"
                            : hasUsers
                              ? "Không có người dùng ở trang này"
                              : "Chưa có người dùng nào"
                        }
                        description={
                          hasActiveFilters
                            ? "Hãy mở rộng tìm kiếm hoặc đặt lại các bộ lọc đang dùng."
                            : hasUsers
                              ? "Hãy thử trang khác hoặc thay đổi số dòng mỗi trang."
                              : "Mời một người dùng để bắt đầu."
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

      <UsersBulkActions
        users={selectedUsers}
        canUpdate={canUpdate}
        canDelete={canDelete}
        onClear={() => setRowSelection({})}
        onStatusChange={(users, status) => {
          onBulkUpdate(users, status);
          setRowSelection({});
        }}
        onDelete={(users) => {
          onBulkDelete(users);
          setRowSelection({});
        }}
      />
    </div>
  );
}
