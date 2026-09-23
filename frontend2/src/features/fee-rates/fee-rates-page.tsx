import { format } from "date-fns";
import {
  Banknote,
  Loader2,
  MoreHorizontal,
  Pencil,
  Plus,
  Power,
  RotateCcw,
  Save,
  Search,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { AccessDenied } from "@/components/admin/access-denied";
import { Combobox } from "@/components/admin/combobox";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DatePicker } from "@/components/admin/date-pickers";
import { EmptyState } from "@/components/admin/empty-state";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { PageHeader } from "@/components/admin/page-header";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
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
import { useAcademicYearsQuery } from "@/features/academic-years/api";
import { useBuildingsQuery } from "@/features/buildings/api";
import {
  useCreateFeeRate,
  useDeactivateFeeRate,
  useDeleteFeeRate,
  useFeeRatesQuery,
  useUpdateFeeRate,
} from "@/features/fee-rates/api";
import type { FeeRate } from "@/features/fee-rates/types";
import { useFloorsQuery } from "@/features/floors/api";
import { useRoomTypesQuery } from "@/features/room-types/api";
import { useRoomsQuery } from "@/features/rooms/api";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

export type FeeRatesSearch = {
  q: string;
  academicYearId?: string;
  roomTypeId?: string;
  buildingId?: string;
  floorId?: string;
  roomId?: string;
  status?: "active" | "inactive";
  page: number;
  pageSize: number;
};

const currency = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

export function FeeRatesPage({
  search,
  onSearchChange,
}: {
  search: FeeRatesSearch;
  onSearchChange: (changes: Partial<FeeRatesSearch>) => void;
}) {
  const { can } = useRbac();
  const query = useFeeRatesQuery({
    search: search.q,
    academicYearId: search.academicYearId,
    roomTypeId: search.roomTypeId,
    buildingId: search.buildingId,
    floorId: search.floorId,
    roomId: search.roomId,
    isActive: search.status ? search.status === "active" : undefined,
    page: search.page,
    pageSize: search.pageSize,
  });

  const yearsQuery = useAcademicYearsQuery({ page: 1, pageSize: 100 });
  const roomTypesQuery = useRoomTypesQuery({
    page: 1,
    pageSize: 100,
    isActive: true,
  });
  const buildingsQuery = useBuildingsQuery({ page: 1, pageSize: 100 });
  const floorsQuery = useFloorsQuery(search.buildingId);

  const [editing, setEditing] = useState<FeeRate | null | undefined>(undefined);
  const [deactivating, setDeactivating] = useState<FeeRate | null>(null);
  const [deleting, setDeleting] = useState<FeeRate | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [pendingBulkDeactivate, setPendingBulkDeactivate] = useState(false);
  const [pendingBulkDelete, setPendingBulkDelete] = useState(false);
  const [isBulkOperating, setIsBulkOperating] = useState(false);

  const deactivate = useDeactivateFeeRate();
  const remove = useDeleteFeeRate();

  const buildingOptions = useMemo(() => {
    const items = buildingsQuery.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả tòa nhà" },
      ...items.map((b) => ({ value: b.id, label: `${b.code} · ${b.name}` })),
    ];
  }, [buildingsQuery.data]);

  const floorOptions = useMemo(() => {
    const items = floorsQuery.data ?? [];
    return [
      { value: "all", label: "Tất cả tầng" },
      ...items.map((f) => ({ value: f.id, label: `Tầng ${f.floorNumber}` })),
    ];
  }, [floorsQuery.data]);

  const academicYearOptions = useMemo(() => {
    const items = yearsQuery.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả năm học" },
      ...items.map((y) => ({ value: y.id, label: `Năm học ${y.code}` })),
    ];
  }, [yearsQuery.data]);

  const roomTypeOptions = useMemo(() => {
    const items = roomTypesQuery.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả loại phòng" },
      ...items.map((rt) => ({
        value: rt.id,
        label: `${rt.code} · ${rt.name}`,
      })),
    ];
  }, [roomTypesQuery.data]);

  if (!can("ktx.fee_rates.view")) return <AccessDenied />;

  const items = query.data?.items ?? [];
  const hasFilters = Boolean(
    search.q ||
      search.academicYearId ||
      search.roomTypeId ||
      search.buildingId ||
      search.floorId ||
      search.status,
  );

  const allSelected =
    items.length > 0 && items.every((item) => selectedIds.has(item.id));
  const someSelected =
    items.some((item) => selectedIds.has(item.id)) && !allSelected;

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(items.map((item) => item.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const toggleSelect = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const handleBulkDeactivate = async () => {
    setIsBulkOperating(true);
    try {
      const activeSelected = items.filter(
        (r) => selectedIds.has(r.id) && r.isActive,
      );
      await Promise.all(
        activeSelected.map((r) => deactivate.mutateAsync(r.id)),
      );
      toast.success(`Đã ngừng áp dụng ${activeSelected.length} mức phí.`);
      setSelectedIds(new Set());
      setPendingBulkDeactivate(false);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Không thể ngừng áp dụng các mức phí đã chọn.",
      );
    } finally {
      setIsBulkOperating(false);
    }
  };

  const handleBulkDelete = async () => {
    setIsBulkOperating(true);
    try {
      const selectedList = items.filter((r) => selectedIds.has(r.id));
      await Promise.all(selectedList.map((r) => remove.mutateAsync(r.id)));
      toast.success(`Đã xóa ${selectedList.length} mức phí.`);
      setSelectedIds(new Set());
      setPendingBulkDelete(false);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Không thể xóa các mức phí đã chọn.",
      );
    } finally {
      setIsBulkOperating(false);
    }
  };

  const resetFilters = () => {
    onSearchChange({
      q: "",
      academicYearId: undefined,
      roomTypeId: undefined,
      buildingId: undefined,
      floorId: undefined,
      status: undefined,
      page: 1,
    });
  };

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="TÀI CHÍNH / ĐỊNH MỨC"
        title="Mức phí"
        description="Thiết lập mức phí định mức theo loại phòng hoặc cấu hình mức phí ghi đè cho từng phòng cụ thể."
        actions={
          can("ktx.fee_rates.create") ? (
            <Button
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              onClick={() => setEditing(null)}
            >
              <Plus className="size-3.5" />
              <span>Thêm mức phí</span>
            </Button>
          ) : undefined
        }
      />

      {/* 2. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:w-72">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 text-xs"
            value={search.q}
            onChange={(event) =>
              onSearchChange({ q: event.target.value, page: 1 })
            }
            placeholder="Tìm loại phòng, mã phòng..."
          />
        </div>

        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          {/* Tòa nhà (Full width on mobile to avoid truncation) */}
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-52 text-xs"
            options={buildingOptions}
            value={search.buildingId ?? "all"}
            searchPlaceholder="Tìm tòa nhà..."
            onValueChange={(value) =>
              onSearchChange({
                buildingId: value === "all" ? undefined : value,
                floorId: undefined,
                page: 1,
              })
            }
          />

          {/* Tầng (50% on mobile) */}
          <Combobox
            className="w-full sm:w-32 text-xs"
            options={floorOptions}
            value={search.floorId ?? "all"}
            searchPlaceholder="Tìm tầng..."
            disabled={!search.buildingId}
            onValueChange={(value) =>
              onSearchChange({
                floorId: value === "all" ? undefined : value,
                page: 1,
              })
            }
          />

          {/* Năm học (50% on mobile) */}
          <Combobox
            className="w-full sm:w-44 text-xs"
            options={academicYearOptions}
            value={search.academicYearId ?? "all"}
            searchPlaceholder="Tìm năm học..."
            onValueChange={(value) =>
              onSearchChange({
                academicYearId: value === "all" ? undefined : value,
                page: 1,
              })
            }
          />

          {/* Loại phòng (Full width on mobile) */}
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-48 text-xs"
            options={roomTypeOptions}
            value={search.roomTypeId ?? "all"}
            searchPlaceholder="Tìm loại phòng..."
            onValueChange={(value) =>
              onSearchChange({
                roomTypeId: value === "all" ? undefined : value,
                page: 1,
              })
            }
          />

          {/* Trạng thái (Full width on mobile) */}
          <Select
            value={search.status ?? "all"}
            onValueChange={(value) =>
              onSearchChange({
                status:
                  value === "all"
                    ? undefined
                    : (value as "active" | "inactive"),
                page: 1,
              })
            }
          >
            <SelectTrigger className="w-full col-span-2 sm:col-span-1 sm:w-40 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              <SelectItem value="active">Đang áp dụng</SelectItem>
              <SelectItem value="inactive">Ngừng áp dụng</SelectItem>
            </SelectContent>
          </Select>

          {hasFilters && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground col-span-2 sm:col-span-1"
              onClick={resetFilters}
            >
              <RotateCcw className="size-3.5 mr-1" />
              <span>Đặt lại</span>
            </Button>
          )}
        </div>
      </div>

      {/* 3. Data Table */}
      <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40">
              <TableHead className="w-10 pl-3">
                <div className="flex items-center pl-1">
                  <Checkbox
                    aria-label="Chọn tất cả mức phí"
                    checked={
                      allSelected
                        ? true
                        : someSelected
                          ? "indeterminate"
                          : false
                    }
                    onCheckedChange={(val) => toggleSelectAll(Boolean(val))}
                  />
                </div>
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[220px]">
                Đối tượng áp dụng
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[120px]">
                Năm học
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[160px]">
                Mức phí / tháng
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[180px]">
                Thời hạn hiệu lực
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[130px]">
                Trạng thái
              </TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {query.isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="py-12 text-center text-xs text-muted-foreground"
                >
                  Đang tải danh sách mức phí...
                </TableCell>
              </TableRow>
            ) : query.isError ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="py-12 text-center text-xs text-destructive"
                >
                  {query.error instanceof Error
                    ? query.error.message
                    : "Không thể tải danh sách mức phí."}
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="p-8">
                  <EmptyState
                    icon={Banknote}
                    title="Không có mức phí nào"
                    description={
                      hasFilters
                        ? "Không tìm thấy mức phí nào phù hợp với bộ lọc hiện tại."
                        : "Chưa có mức phí nào được tạo trong hệ thống."
                    }
                    action={
                      hasFilters
                        ? {
                            label: "Xóa bộ lọc",
                            onClick: resetFilters,
                          }
                        : can("ktx.fee_rates.create")
                          ? {
                              label: "Thêm mức phí đầu tiên",
                              onClick: () => setEditing(null),
                            }
                          : undefined
                    }
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((rate) => (
                <TableRow
                  key={rate.id}
                  className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                  onClick={() => setEditing(rate)}
                >
                  <TableCell
                    className="pl-3"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <div className="flex items-center pl-1">
                      <Checkbox
                        aria-label={`Chọn mức phí ${rate.roomTypeName}`}
                        checked={selectedIds.has(rate.id)}
                        onCheckedChange={(val) =>
                          toggleSelect(rate.id, Boolean(val))
                        }
                      />
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-foreground text-sm">
                          {rate.roomId
                            ? `Phòng ${rate.roomCode}`
                            : rate.roomTypeName}
                        </span>
                        {rate.roomId ? (
                          <Badge
                            variant="outline"
                            className="text-[10px] px-1.5 py-0 font-normal"
                          >
                            Ghi đè phòng
                          </Badge>
                        ) : (
                          <Badge
                            variant="secondary"
                            className="text-[10px] px-1.5 py-0 font-normal"
                          >
                            Mặc định loại phòng
                          </Badge>
                        )}
                      </div>
                      <p className="type-supporting font-mono text-muted-foreground text-xs">
                        {rate.roomId
                          ? `${rate.buildingCode} · Tầng ${rate.floorNumber} · ${rate.roomTypeName}`
                          : rate.roomTypeCode}
                      </p>
                    </div>
                  </TableCell>

                  <TableCell>
                    <span className="font-mono font-medium text-foreground text-sm">
                      {rate.academicYearCode}
                    </span>
                  </TableCell>

                  <TableCell>
                    <div>
                      <span className="font-bold text-foreground tabular-nums text-sm">
                        {currency.format(rate.amount)}
                      </span>
                      <span className="text-[11px] text-muted-foreground block">
                        / người / tháng
                      </span>
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="text-xs space-y-0.5">
                      <span className="font-mono text-foreground">
                        {rate.effectiveFrom}
                      </span>
                      {rate.effectiveTo ? (
                        <span className="text-muted-foreground font-mono">
                          {" "}
                          → {rate.effectiveTo}
                        </span>
                      ) : (
                        <span className="text-muted-foreground block text-[11px]">
                          (Không thời hạn)
                        </span>
                      )}
                    </div>
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant={rate.isActive ? "success" : "secondary"}
                      className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
                    >
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          rate.isActive
                            ? "bg-emerald-500"
                            : "bg-muted-foreground/60",
                        )}
                      />
                      {rate.isActive ? "Đang áp dụng" : "Ngừng áp dụng"}
                    </Badge>
                  </TableCell>

                  <TableCell onClick={(event) => event.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="size-8 text-muted-foreground hover:text-foreground"
                          aria-label={`Thao tác với mức phí ${rate.roomTypeName}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        {can("ktx.fee_rates.update") && (
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditing(rate);
                            }}
                          >
                            <Pencil className="size-4 mr-2 text-muted-foreground" />
                            Chỉnh sửa
                          </DropdownMenuItem>
                        )}

                        {rate.isActive && can("ktx.fee_rates.deactivate") && (
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeactivating(rate);
                            }}
                          >
                            <Power className="size-4 mr-2 text-warning" />
                            Ngừng áp dụng
                          </DropdownMenuItem>
                        )}

                        {can("ktx.fee_rates.deactivate") && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleting(rate);
                              }}
                            >
                              <Trash2 className="size-4 mr-2 text-destructive" />
                              Xóa mức phí
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 4. Pagination */}
      {query.data ? (
        <DataTablePagination
          page={search.page}
          pageSize={search.pageSize}
          pageCount={query.data.totalPages}
          onPageChange={(page) => onSearchChange({ page })}
          onPageSizeChange={(pageSize) => onSearchChange({ pageSize, page: 1 })}
        />
      ) : null}

      {/* 5. Bulk Actions Bar */}
      <DataTableBulkActions
        selectedCount={selectedIds.size}
        selectedLabel="mức phí"
        onClear={() => setSelectedIds(new Set())}
      >
        {can("ktx.fee_rates.deactivate") && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => setPendingBulkDeactivate(true)}
                aria-label="Ngừng áp dụng"
              >
                <Power className="size-4 text-warning" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Ngừng áp dụng ({selectedIds.size} mức phí)
            </TooltipContent>
          </Tooltip>
        )}

        {can("ktx.fee_rates.deactivate") && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="destructive"
                size="icon"
                className="size-8 rounded-xl shadow-2xs"
                onClick={() => setPendingBulkDelete(true)}
                aria-label="Xóa đã chọn"
              >
                <Trash2 className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">Xóa các mức phí đã chọn</TooltipContent>
          </Tooltip>
        )}
      </DataTableBulkActions>

      {/* 6. Create / Edit Dialog */}
      <FeeRateDialog
        open={editing !== undefined}
        rate={editing ?? null}
        onOpenChange={(open) => {
          if (!open) setEditing(undefined);
        }}
      />

      {/* 7. Confirm Single Deactivate Dialog */}
      <ConfirmDialog
        open={Boolean(deactivating)}
        onOpenChange={(open) => {
          if (!open) setDeactivating(null);
        }}
        title="Ngừng áp dụng mức phí?"
        description={`Mức phí của "${deactivating?.roomTypeName}" (${deactivating?.academicYearCode}) sẽ không được sử dụng để sinh hóa đơn mới.`}
        confirmLabel="Ngừng áp dụng"
        isLoading={deactivate.isPending}
        onConfirm={() =>
          deactivating &&
          void deactivate.mutateAsync(deactivating.id).then(() => {
            setDeactivating(null);
            toast.success("Đã ngừng áp dụng mức phí.");
          })
        }
      />

      {/* 8. Confirm Single Delete Dialog */}
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title="Xóa mức phí?"
        description="Chỉ có thể xóa mức phí chưa được ghi nhận trong bất kỳ hóa đơn nào. Thao tác này không thể hoàn tác."
        confirmLabel="Xóa mức phí"
        confirmVariant="destructive"
        isLoading={remove.isPending}
        onConfirm={() =>
          deleting &&
          void remove.mutateAsync(deleting.id).then(() => {
            setDeleting(null);
            toast.success("Đã xóa mức phí.");
          })
        }
      />

      {/* 9. Confirm Bulk Deactivate Dialog */}
      <ConfirmDialog
        open={pendingBulkDeactivate}
        onOpenChange={setPendingBulkDeactivate}
        title="Ngừng áp dụng các mức phí đã chọn?"
        description={`Bạn có chắc muốn ngừng áp dụng ${selectedIds.size} mức phí đã chọn? Các mức phí này sẽ không thể dùng cho hóa đơn mới.`}
        confirmLabel="Ngừng áp dụng"
        isLoading={isBulkOperating}
        onConfirm={() => void handleBulkDeactivate()}
      />

      {/* 10. Confirm Bulk Delete Dialog */}
      <ConfirmDialog
        open={pendingBulkDelete}
        onOpenChange={setPendingBulkDelete}
        title="Xóa các mức phí đã chọn?"
        description={`Bạn có chắc muốn xóa vĩnh viễn ${selectedIds.size} mức phí đã chọn? Chỉ các mức phí chưa phát sinh hóa đơn mới có thể xóa thành công.`}
        confirmLabel="Xóa các mục đã chọn"
        confirmVariant="destructive"
        isLoading={isBulkOperating}
        onConfirm={() => void handleBulkDelete()}
      />
    </div>
  );
}

function FeeRateDialog({
  open,
  rate,
  onOpenChange,
}: {
  open: boolean;
  rate: FeeRate | null;
  onOpenChange: (open: boolean) => void;
}) {
  const years = useAcademicYearsQuery({ page: 1, pageSize: 100 });
  const roomTypes = useRoomTypesQuery({
    page: 1,
    pageSize: 100,
    isActive: true,
  });

  const [academicYearId, setAcademicYearId] = useState(
    rate?.academicYearId ?? "",
  );
  const [roomTypeId, setRoomTypeId] = useState(rate?.roomTypeId ?? "");
  const [roomId, setRoomId] = useState(rate?.roomId ?? "");
  const [amount, setAmount] = useState(rate?.amount ?? 0);
  const [effectiveFrom, setEffectiveFrom] = useState<Date | undefined>(
    rate?.effectiveFrom ? new Date(rate.effectiveFrom) : undefined,
  );
  const [effectiveTo, setEffectiveTo] = useState<Date | undefined>(
    rate?.effectiveTo ? new Date(rate.effectiveTo) : undefined,
  );

  const rooms = useRoomsQuery({
    roomTypeId: roomTypeId || undefined,
    page: 1,
    pageSize: 100,
  });

  const create = useCreateFeeRate();
  const update = useUpdateFeeRate();
  const pending = create.isPending || update.isPending;

  const availableRooms = useMemo(() => rooms.data?.items ?? [], [rooms.data]);

  const academicYearOptions = useMemo(
    () =>
      (years.data?.items ?? []).map((item) => ({
        value: item.id,
        label: `Năm học ${item.code}`,
      })),
    [years.data?.items],
  );

  const roomTypeOptions = useMemo(
    () =>
      (roomTypes.data?.items ?? []).map((item) => ({
        value: item.id,
        label: `${item.code} · ${item.name}`,
      })),
    [roomTypes.data?.items],
  );

  const roomScopeOptions = useMemo(
    () => [
      {
        value: "default",
        label: "Mặc định cho toàn bộ phòng thuộc loại này",
      },
      ...availableRooms.map((room) => ({
        value: room.id,
        label: `Phòng ${room.code} · ${room.buildingCode} · Tầng ${room.floorNumber}`,
      })),
    ],
    [availableRooms],
  );

  const submit = () => {
    if (
      !amount ||
      !effectiveFrom ||
      (!rate && (!academicYearId || !roomTypeId))
    ) {
      toast.error(
        "Vui lòng điền đầy đủ Năm học, Loại phòng, Mức phí và Ngày hiệu lực.",
      );
      return;
    }

    const input = {
      amount,
      currency: "VND",
      effectiveFrom: format(effectiveFrom, "yyyy-MM-dd"),
      effectiveTo: effectiveTo ? format(effectiveTo, "yyyy-MM-dd") : undefined,
      isActive: true,
    };

    const request = rate
      ? update.mutateAsync({ id: rate.id, input })
      : create.mutateAsync({
          ...input,
          academicYearId,
          roomTypeId,
          roomId: roomId || undefined,
        });

    void request
      .then(() => {
        toast.success(
          rate
            ? "Đã cập nhật mức phí thành công."
            : "Đã tạo mức phí mới thành công.",
        );
        onOpenChange(false);
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof Error ? error.message : "Không thể lưu mức phí.",
        ),
      );
  };

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-w-xl">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            {rate ? "Chỉnh sửa mức phí" : "Thêm mức phí mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {rate
              ? "Cập nhật đơn giá và thời hạn áp dụng cho mức phí đã chọn."
              : "Thiết lập đơn giá theo loại phòng hoặc chọn phòng cụ thể để ghi đè đơn giá."}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <div className="grid gap-4 py-4 sm:grid-cols-2">
          {/* Năm học */}
          <Field>
            <FieldLabel>
              Năm học <span className="text-destructive font-bold">*</span>
            </FieldLabel>
            <Combobox
              className="w-full text-xs"
              options={academicYearOptions}
              value={academicYearId}
              searchPlaceholder="Tìm năm học..."
              disabled={Boolean(rate) || pending}
              onValueChange={(val) => setAcademicYearId(val ?? "")}
            />
          </Field>

          {/* Loại phòng */}
          <Field>
            <FieldLabel>
              Loại phòng <span className="text-destructive font-bold">*</span>
            </FieldLabel>
            <Combobox
              className="w-full text-xs"
              options={roomTypeOptions}
              value={roomTypeId}
              searchPlaceholder="Tìm loại phòng..."
              disabled={Boolean(rate) || pending}
              onValueChange={(value) => {
                setRoomTypeId(value ?? "");
                setRoomId("");
              }}
            />
          </Field>

          {/* Phạm vi áp dụng */}
          {!rate && (
            <Field className="sm:col-span-2">
              <FieldLabel>Phạm vi áp dụng</FieldLabel>
              <Combobox
                className="w-full text-xs"
                options={roomScopeOptions}
                value={roomId || "default"}
                searchPlaceholder="Tìm phòng cụ thể..."
                disabled={!roomTypeId || pending}
                onValueChange={(value) =>
                  setRoomId(value === "default" || !value ? "" : value)
                }
              />
              <FieldDescription className="text-xs">
                {roomTypeId
                  ? "Chọn một phòng cụ thể nếu bạn muốn mức phí này ghi đè mức phí mặc định của loại phòng."
                  : "Vui lòng chọn Loại phòng trước để lọc danh sách phòng cụ thể (nếu cần)."}
              </FieldDescription>
            </Field>
          )}

          {/* Mức phí */}
          <Field className="sm:col-span-2">
            <FieldLabel>
              Mức phí / người / tháng (VND){" "}
              <span className="text-destructive font-bold">*</span>
            </FieldLabel>
            <Input
              type="number"
              min={0}
              step={10000}
              className="text-sm font-semibold font-mono"
              value={amount || ""}
              disabled={pending}
              onChange={(event) => setAmount(Number(event.target.value))}
              placeholder="Nhập mức phí, ví dụ: 500000"
            />
            {amount > 0 && (
              <FieldDescription className="text-primary font-medium text-xs">
                Định dạng: {currency.format(amount)} / sinh viên / tháng
              </FieldDescription>
            )}
          </Field>

          {/* Hiệu lực từ ngày */}
          <Field>
            <FieldLabel>
              Hiệu lực từ ngày{" "}
              <span className="text-destructive font-bold">*</span>
            </FieldLabel>
            <DatePicker
              value={effectiveFrom}
              onChange={setEffectiveFrom}
              disabled={pending}
            />
          </Field>

          {/* Hiệu lực đến ngày */}
          <Field>
            <FieldLabel>Hiệu lực đến ngày</FieldLabel>
            <DatePicker
              value={effectiveTo}
              onChange={setEffectiveTo}
              minDate={effectiveFrom}
              disabled={pending}
            />
            <FieldDescription className="text-xs">
              Để trống nếu áp dụng không thời hạn.
            </FieldDescription>
          </Field>
        </div>

        <ResponsiveDialogFooter>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="text-xs"
            disabled={pending}
            onClick={() => onOpenChange(false)}
          >
            Hủy
          </Button>
          <Button
            type="button"
            size="sm"
            className="gap-1.5 text-xs font-semibold"
            disabled={pending}
            onClick={submit}
          >
            {pending ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                <span>Đang lưu...</span>
              </>
            ) : rate ? (
              <>
                <Save className="size-3.5" />
                <span>Lưu mức phí</span>
              </>
            ) : (
              <>
                <Plus className="size-3.5" />
                <span>Lưu mức phí</span>
              </>
            )}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
