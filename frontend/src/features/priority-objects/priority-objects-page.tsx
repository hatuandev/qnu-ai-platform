import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  type RowSelectionState,
  useReactTable,
} from "@tanstack/react-table";
import {
  Download,
  ImageIcon,
  MapPin,
  MoreHorizontal,
  Pencil,
  Plus,
  Power,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  useCreatePriorityObject,
  useDeactivatePriorityObject,
  useDeletePriorityObject,
  useDeletePriorityObjectsBatch,
  usePriorityObjectsQuery,
  useUpdatePriorityObject,
} from "@/features/priority-objects/api";
import { EligibleAreasBody } from "@/features/priority-objects/eligible-areas-dialog";
import { PriorityObjectFormDialog } from "@/features/priority-objects/priority-object-form-dialog";
import {
  PRIORITY_OBJECT_VERIFICATION_TYPE,
  PRIORITY_OBJECT_VERIFICATION_TYPE_LABELS,
  type PriorityObject,
  type PriorityObjectVerificationType,
} from "@/features/priority-objects/types";
import { exportToExcel } from "@/lib/excel-export";
import { useRbac } from "@/rbac/context";

const VERIFICATION_FILTER_VALUES: PriorityObjectVerificationType[] = [
  PRIORITY_OBJECT_VERIFICATION_TYPE.None,
  PRIORITY_OBJECT_VERIFICATION_TYPE.ImageEvidence,
  PRIORITY_OBJECT_VERIFICATION_TYPE.ResidenceArea,
  PRIORITY_OBJECT_VERIFICATION_TYPE.ImageAndResidenceArea,
];

export const priorityObjectsSearchSchema = z.object({
  q: z.string().catch(""),
  status: z.enum(["active", "inactive"]).optional().catch(undefined),
  verificationType: z
    .enum([
      PRIORITY_OBJECT_VERIFICATION_TYPE.None,
      PRIORITY_OBJECT_VERIFICATION_TYPE.ImageEvidence,
      PRIORITY_OBJECT_VERIFICATION_TYPE.ResidenceArea,
      PRIORITY_OBJECT_VERIFICATION_TYPE.ImageAndResidenceArea,
    ])
    .optional()
    .catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

type SearchState = z.infer<typeof priorityObjectsSearchSchema>;

function exportPriorityObjectsToExcel(objects: PriorityObject[]) {
  exportToExcel({
    filename: `danh_sach_doi_tuong_uu_tien_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Đối tượng ưu tiên",
    data: objects,
    columns: [
      { header: "Mã đối tượng", accessor: (obj) => obj.code },
      { header: "Tên đối tượng", accessor: (obj) => obj.name },
      { header: "Mô tả", accessor: (obj) => obj.description || "" },
      { header: "Điểm ưu tiên", accessor: (obj) => `+${obj.score}` },
      {
        header: "Trạng thái",
        accessor: (obj) => (obj.isActive ? "Đang áp dụng" : "Đã ngừng"),
      },
    ],
  });
}

function VerificationBadge({ type }: { type: PriorityObjectVerificationType }) {
  switch (type) {
    case PRIORITY_OBJECT_VERIFICATION_TYPE.ImageEvidence:
      return (
        <Badge variant="info" className="gap-1.5 px-2.5 py-0.5 font-medium">
          <ImageIcon className="size-3" />
          Ảnh minh chứng
        </Badge>
      );
    case PRIORITY_OBJECT_VERIFICATION_TYPE.ResidenceArea:
      return (
        <Badge variant="warning" className="gap-1.5 px-2.5 py-0.5 font-medium">
          <MapPin className="size-3" />
          Theo địa bàn
        </Badge>
      );
    case PRIORITY_OBJECT_VERIFICATION_TYPE.ImageAndResidenceArea:
      return (
        <Badge variant="warning" className="gap-1.5 px-2.5 py-0.5 font-medium">
          <ShieldCheck className="size-3" />
          Ảnh + địa bàn
        </Badge>
      );
    default:
      return (
        <Badge variant="secondary" className="px-2.5 py-0.5 font-medium">
          Không yêu cầu
        </Badge>
      );
  }
}

function requiresResidenceArea(type: PriorityObjectVerificationType): boolean {
  return (
    type === PRIORITY_OBJECT_VERIFICATION_TYPE.ResidenceArea ||
    type === PRIORITY_OBJECT_VERIFICATION_TYPE.ImageAndResidenceArea
  );
}

function VerificationCell({ object }: { object: PriorityObject }) {
  return (
    <div className="flex flex-col gap-1">
      <VerificationBadge type={object.verificationType} />
      {requiresResidenceArea(object.verificationType) ? (
        <button
          type="button"
          className="text-muted-foreground text-xs underline-offset-2 hover:underline"
          onClick={(event) => event.stopPropagation()}
        >
          {object.eligibleAreaCount > 0
            ? `${object.eligibleAreaCount} địa bàn đã cấu hình`
            : "Chưa cấu hình địa bàn"}
        </button>
      ) : null}
    </div>
  );
}

export function PriorityObjectsPage({
  search,
  updateSearch,
}: {
  search: SearchState;
  updateSearch: (changes: Partial<SearchState>) => void;
}) {
  const { can } = useRbac();
  const [formState, setFormState] = useState<
    PriorityObject | null | "create"
  >();
  const [pendingDeactivate, setPendingDeactivate] =
    useState<PriorityObject | null>(null);
  const [pendingDeleteObjects, setPendingDeleteObjects] = useState<
    PriorityObject[] | null
  >(null);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [managingAreasFor, setManagingAreasFor] =
    useState<PriorityObject | null>(null);

  const query = usePriorityObjectsQuery({
    searchCodeOrName: search.q.trim() || undefined,
    verificationType: search.verificationType,
    isActive:
      search.status === undefined ? undefined : search.status === "active",
    page: search.page,
    pageSize: search.pageSize,
  });
  const create = useCreatePriorityObject();
  const update = useUpdatePriorityObject();
  const deactivate = useDeactivatePriorityObject();
  const deletePriorityObject = useDeletePriorityObject();
  const deletePriorityObjectsBatch = useDeletePriorityObjectsBatch();
  const items = query.data?.items ?? [];
  const hasFilters = Boolean(
    search.q || search.status || search.verificationType,
  );

  const columns = useMemo<ColumnDef<PriorityObject>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <div className="flex items-center pl-1">
            <Checkbox
              aria-label="Chọn tất cả đối tượng"
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
        header: "Tên đối tượng",
        cell: ({ row }) => (
          <div>
            <div className="font-semibold text-foreground text-sm">
              {row.original.name}
            </div>
            {row.original.description ? (
              <div className="text-xs text-muted-foreground mt-0.5">
                {row.original.description}
              </div>
            ) : null}
          </div>
        ),
      },
      {
        accessorKey: "score",
        header: "Điểm",
        cell: ({ row }) => (
          <span className="tabular-nums font-semibold text-emerald-600 dark:text-emerald-400 text-sm">
            +{row.original.score}
          </span>
        ),
      },
      {
        id: "verification",
        header: "Minh chứng",
        cell: ({ row }) => <VerificationCell object={row.original} />,
      },
      {
        accessorKey: "isActive",
        header: "Trạng thái",
        cell: ({ row }) => (
          <Badge
            variant={row.original.isActive ? "success" : "secondary"}
            className="gap-1.5 font-medium px-2.5 py-0.5"
          >
            <span
              className={`size-1.5 rounded-full ${
                row.original.isActive
                  ? "bg-emerald-500"
                  : "bg-muted-foreground/60"
              }`}
            />
            {row.original.isActive ? "Đang áp dụng" : "Đã ngừng"}
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
                {can("ktx.priority_objects.update") ? (
                  <DropdownMenuItem
                    onSelect={() => setFormState(row.original)}
                    onClick={(e) => {
                      e.stopPropagation();
                      setFormState(row.original);
                    }}
                  >
                    <Pencil className="size-4 mr-2 text-muted-foreground" />
                    Chỉnh sửa
                  </DropdownMenuItem>
                ) : null}
                {can("ktx.priority_objects.areas.manage") &&
                requiresResidenceArea(row.original.verificationType) ? (
                  <DropdownMenuItem
                    onSelect={() => setManagingAreasFor(row.original)}
                    onClick={(e) => {
                      e.stopPropagation();
                      setManagingAreasFor(row.original);
                    }}
                  >
                    <MapPin className="size-4 mr-2 text-muted-foreground" />
                    Quản lý địa bàn
                  </DropdownMenuItem>
                ) : null}
                {can("ktx.priority_objects.deactivate") &&
                row.original.isActive ? (
                  <DropdownMenuItem
                    onSelect={() => setPendingDeactivate(row.original)}
                    onClick={(e) => {
                      e.stopPropagation();
                      setPendingDeactivate(row.original);
                    }}
                  >
                    <Power className="size-4 mr-2 text-amber-500" />
                    Ngừng áp dụng
                  </DropdownMenuItem>
                ) : null}
                {can("ktx.priority_objects.deactivate") ? (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-destructive focus:bg-destructive/10 focus:text-destructive"
                      onSelect={() => setPendingDeleteObjects([row.original])}
                      onClick={(e) => {
                        e.stopPropagation();
                        setPendingDeleteObjects([row.original]);
                      }}
                    >
                      <Trash2 className="size-4 mr-2 text-destructive" />
                      Xóa đối tượng
                    </DropdownMenuItem>
                  </>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [can],
  );

  const table = useReactTable({
    data: items,
    columns,
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,
  });

  const selectedObjects = table
    .getSelectedRowModel()
    .rows.map((r) => r.original);

  if (!can("ktx.priority_objects.view")) return <AccessDenied />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Học vụ / Cấu hình xét duyệt"
        title="Đối tượng ưu tiên"
        description="Quản lý nhóm đối tượng và điểm cộng được dùng khi xét duyệt hồ sơ KTX."
        actions={
          can("ktx.priority_objects.create") ? (
            <Button className="gap-2" onClick={() => setFormState("create")}>
              <Plus className="size-4" />
              Thêm đối tượng
            </Button>
          ) : null
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-sm">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search.q}
            placeholder="Tìm theo mã hoặc tên đối tượng..."
            className="pl-9"
            onChange={(e) => updateSearch({ q: e.target.value, page: 1 })}
          />
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={search.verificationType ?? "all"}
            onValueChange={(val) =>
              updateSearch({
                verificationType:
                  val === "all"
                    ? undefined
                    : (val as PriorityObjectVerificationType),
                page: 1,
              })
            }
          >
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Hình thức xác minh" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả hình thức</SelectItem>
              {VERIFICATION_FILTER_VALUES.map((value) => (
                <SelectItem key={value} value={value}>
                  {PRIORITY_OBJECT_VERIFICATION_TYPE_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={search.status ?? "all"}
            onValueChange={(val) =>
              updateSearch({
                status:
                  val === "all" ? undefined : (val as "active" | "inactive"),
                page: 1,
              })
            }
          >
            <SelectTrigger className="w-full sm:w-40">
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả</SelectItem>
              <SelectItem value="active">Đang áp dụng</SelectItem>
              <SelectItem value="inactive">Đã ngừng</SelectItem>
            </SelectContent>
          </Select>
          {hasFilters ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                updateSearch({
                  q: "",
                  status: undefined,
                  verificationType: undefined,
                  page: 1,
                })
              }
            >
              Xóa bộ lọc
            </Button>
          ) : null}
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-card shadow-xs">
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
            {query.isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((_, j) => (
                    <TableCell key={j} className="py-3">
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-32 text-center"
                >
                  <DataTableEmpty
                    title="Chưa có đối tượng ưu tiên"
                    description="Thêm nhóm đối tượng ưu tiên đầu tiên để phân loại hồ sơ đăng ký."
                  />
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                  onClick={() => setFormState(row.original)}
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
            )}
          </TableBody>
        </Table>
      </div>

      <DataTablePagination
        page={search.page}
        pageSize={search.pageSize}
        pageCount={query.data?.totalPages ?? 1}
        onPageChange={(page) => updateSearch({ page })}
        onPageSizeChange={(pageSize) =>
          updateSearch({ pageSize: pageSize as 10 | 20 | 50, page: 1 })
        }
      />

      {/* Thanh tác vụ nổi khi có đối tượng được chọn */}
      {selectedObjects.length > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedObjects.length}
          selectedLabel="đối tượng"
          onClear={() => setRowSelection({})}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => {
                  exportPriorityObjectsToExcel(selectedObjects);
                  toast.success(
                    `Đã xuất dữ liệu ${selectedObjects.length} đối tượng ưu tiên ra file Excel thành công.`,
                  );
                }}
                aria-label="Xuất Excel"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Xuất Excel ({selectedObjects.length} đối tượng)
            </TooltipContent>
          </Tooltip>

          {can("ktx.priority_objects.deactivate") ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="destructive"
                  size="icon"
                  className="size-8 rounded-xl shadow-2xs"
                  onClick={() => {
                    setPendingDeleteObjects(selectedObjects);
                  }}
                  aria-label="Xóa đã chọn"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                Xóa {selectedObjects.length} đối tượng đã chọn
              </TooltipContent>
            </Tooltip>
          ) : null}
        </DataTableBulkActions>
      ) : null}

      <PriorityObjectFormDialog
        key={formState === "create" ? "create" : (formState?.id ?? "closed")}
        open={Boolean(formState)}
        priorityObject={formState === "create" ? null : (formState ?? null)}
        isSubmitting={create.isPending || update.isPending}
        onOpenChange={(open) => {
          if (!open) setFormState(undefined);
        }}
        onCreate={async (input) => {
          await create.mutateAsync(input);
          toast.success("Đã tạo đối tượng ưu tiên.");
          setFormState(undefined);
        }}
        onUpdate={async (id, input) => {
          await update.mutateAsync({ id, input });
          toast.success("Đã cập nhật đối tượng ưu tiên.");
          setFormState(undefined);
        }}
      />

      {/* Dialog xác nhận Ngừng áp dụng */}
      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        onOpenChange={(open) => {
          if (!open && !deactivate.isPending) setPendingDeactivate(null);
        }}
        title="Ngừng áp dụng đối tượng ưu tiên?"
        description={
          pendingDeactivate
            ? `Ngừng áp dụng “${pendingDeactivate.name}” (${pendingDeactivate.code}) cho các đợt đăng ký hồ sơ mới?`
            : ""
        }
        confirmLabel="Ngừng áp dụng"
        isLoading={deactivate.isPending}
        onConfirm={() => {
          if (!pendingDeactivate) return;
          void deactivate
            .mutateAsync(pendingDeactivate.id)
            .then(() => {
              setPendingDeactivate(null);
              toast.success("Đã ngừng áp dụng đối tượng ưu tiên.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể ngừng đối tượng ưu tiên.",
              ),
            );
        }}
      />

      {/* Dialog xác nhận Xóa đối tượng */}
      <ConfirmDialog
        open={Boolean(pendingDeleteObjects && pendingDeleteObjects.length > 0)}
        onOpenChange={(open) => {
          if (
            !open &&
            !deletePriorityObject.isPending &&
            !deletePriorityObjectsBatch.isPending
          ) {
            setPendingDeleteObjects(null);
          }
        }}
        title={
          pendingDeleteObjects && pendingDeleteObjects.length > 1
            ? `Xác nhận xóa ${pendingDeleteObjects.length} đối tượng ưu tiên đã chọn?`
            : "Xác nhận xóa đối tượng ưu tiên?"
        }
        description={
          pendingDeleteObjects && pendingDeleteObjects.length > 0
            ? pendingDeleteObjects.length === 1
              ? `Bạn có chắc chắn muốn xóa đối tượng “${pendingDeleteObjects[0].name}” (${pendingDeleteObjects[0].code}) không? Hành động này sẽ xóa hoàn toàn bản ghi khỏi hệ thống.`
              : `Bạn có chắc chắn muốn xóa ${pendingDeleteObjects.length} đối tượng ưu tiên đã chọn không? Hệ thống sẽ từ chối nếu có đối tượng đang được tham chiếu bởi hồ sơ sinh viên.`
            : ""
        }
        confirmLabel={
          pendingDeleteObjects && pendingDeleteObjects.length > 1
            ? `Xác nhận xóa ${pendingDeleteObjects.length} đối tượng`
            : "Xóa đối tượng"
        }
        confirmVariant="destructive"
        isLoading={
          deletePriorityObject.isPending || deletePriorityObjectsBatch.isPending
        }
        onConfirm={() => {
          if (!pendingDeleteObjects || pendingDeleteObjects.length === 0)
            return;
          const count = pendingDeleteObjects.length;
          const promise =
            count === 1
              ? deletePriorityObject.mutateAsync(pendingDeleteObjects[0].id)
              : deletePriorityObjectsBatch.mutateAsync(
                  pendingDeleteObjects.map((o) => o.id),
                );

          void promise
            .then(() => {
              setPendingDeleteObjects(null);
              setRowSelection({});
              toast.success(
                count === 1
                  ? "Đã xóa đối tượng ưu tiên thành công."
                  : `Đã xóa ${count} đối tượng ưu tiên thành công.`,
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể xóa đối tượng ưu tiên.",
              ),
            );
        }}
      />

      {/* Dialog quản lý địa bàn */}
      {managingAreasFor ? (
        <Dialog
          open={Boolean(managingAreasFor)}
          onOpenChange={(open) => {
            if (!open) setManagingAreasFor(null);
          }}
        >
          <DialogContent className="flex max-h-[min(720px,calc(100vh-2rem))] w-full max-w-3xl flex-col overflow-hidden">
            <DialogHeader>
              <DialogTitle>
                Quản lý địa bàn · {managingAreasFor.name}
              </DialogTitle>
              <DialogDescription>
                Thêm hoặc ngừng áp dụng các địa bàn hành chính cho đối tượng ưu
                tiên.
              </DialogDescription>
            </DialogHeader>
            <EligibleAreasBody
              priorityObjectId={managingAreasFor.id}
              priorityObjectName={managingAreasFor.name}
              priorityObjectCode={managingAreasFor.code}
            />
          </DialogContent>
        </Dialog>
      ) : null}
    </div>
  );
}
