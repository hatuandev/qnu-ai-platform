import { useForm } from "@tanstack/react-form";
import { useNavigate } from "@tanstack/react-router";
import {
  Archive,
  Bell,
  Calendar,
  CalendarDays,
  CheckCheck,
  CheckCircle2,
  CreditCard,
  DoorOpen,
  Download,
  Eye,
  GraduationCap,
  Lock,
  MoreHorizontal,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  StickyNote,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DatePicker } from "@/components/admin/date-pickers";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { Field, FieldError, FieldLabel } from "@/components/admin/field";
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
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAcademicYearsQuery } from "@/features/academic-years/api";
import { useFinalizeRoomSelection } from "@/features/assignments/api";
import { usePaymentConfigurationsQuery } from "@/features/payment-configurations/api";
import type { PaymentConfiguration } from "@/features/payment-configurations/types";
import {
  useCreateRegistrationPeriod,
  useDeleteRegistrationPeriodsBatch,
  useRegistrationPeriodsQuery,
  useRegistrationPeriodTransition,
  useUpdateRegistrationPeriod,
} from "@/features/registration-periods/api";
import type { RegistrationPeriod } from "@/features/registration-periods/types";
import { formatDateValue } from "@/lib/date-utils";
import { exportToExcel } from "@/lib/excel-export";
import { getFormErrorMessage } from "@/lib/form-errors";
import { useRbac } from "@/rbac/context";

function firstError(errors: unknown[]): string | undefined {
  return getFormErrorMessage(errors[0]);
}

function parseIsoToDate(value: string | null | undefined): Date | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

function startOfDay(date: Date): Date {
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  return next;
}

function endOfDay(date: Date): Date {
  const next = new Date(date);
  next.setHours(23, 59, 59, 999);
  return next;
}

export type RegistrationPeriodsSearch = {
  q: string;
  status?: "draft" | "open" | "closed" | "archived";
  page: number;
  pageSize: number;
};

const statusLabels = {
  draft: "Nháp",
  open: "Đang mở",
  closed: "Đã đóng",
  archived: "Đã kết thúc",
};
const optionalDate = z.union([z.date(), z.undefined()]);

function isPeriodEditable(period: RegistrationPeriod): boolean {
  if (period.status === "archived") return false;
  if (period.status === "closed" && period.roomSelectionFinalizedAt)
    return false;
  return (
    period.status === "draft" ||
    period.status === "open" ||
    period.status === "closed"
  );
}

function exportRegistrationPeriodsToExcel(periods: RegistrationPeriod[]) {
  exportToExcel({
    filename: `danh_sach_dot_dang_ky_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Đợt đăng ký",
    data: periods,
    columns: [
      { header: "Mã đợt", accessor: (p) => p.code },
      { header: "Tên đợt", accessor: (p) => p.name },
      { header: "Ngày bắt đầu", accessor: (p) => formatDateValue(p.startAt) },
      { header: "Ngày kết thúc", accessor: (p) => formatDateValue(p.endAt) },
      {
        header: "Thời gian chọn phòng",
        accessor: (p) =>
          p.roomSelectionStartAt && p.roomSelectionEndAt
            ? `${formatDateValue(p.roomSelectionStartAt)} - ${formatDateValue(p.roomSelectionEndAt)}`
            : "Chưa cấu hình",
      },
      {
        header: "Trạng thái",
        accessor: (p) => statusLabels[p.status] || p.status,
      },
    ],
  });
}

export function RegistrationPeriodsPage({
  search,
  onSearchChange,
}: {
  search: RegistrationPeriodsSearch;
  onSearchChange: (changes: Partial<RegistrationPeriodsSearch>) => void;
}) {
  const navigate = useNavigate();
  const { can } = useRbac();
  const [createOpen, setCreateOpen] = useState(false);
  const [editPeriod, setEditPeriod] = useState<RegistrationPeriod | null>(null);
  const [detailPeriod, setDetailPeriod] = useState<RegistrationPeriod | null>(
    null,
  );
  const [pendingOpenPeriod, setPendingOpenPeriod] =
    useState<RegistrationPeriod | null>(null);
  const [pendingClosePeriod, setPendingClosePeriod] =
    useState<RegistrationPeriod | null>(null);
  const [pendingFinalizePeriod, setPendingFinalizePeriod] =
    useState<RegistrationPeriod | null>(null);
  const [pendingArchive, setPendingArchive] =
    useState<RegistrationPeriod | null>(null);
  const [pendingRestore, setPendingRestore] =
    useState<RegistrationPeriod | null>(null);
  const [pendingDeletePeriods, setPendingDeletePeriods] = useState<
    RegistrationPeriod[] | null
  >(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const params = useMemo(
    () => ({
      search: search.q || undefined,
      status: search.status,
      page: search.page,
      pageSize: search.pageSize,
    }),
    [search.page, search.pageSize, search.q, search.status],
  );
  const query = useRegistrationPeriodsQuery(params);
  const years = useAcademicYearsQuery({ page: 1, pageSize: 100 });
  const paymentConfigurations = usePaymentConfigurationsQuery();
  const transition = useRegistrationPeriodTransition();
  const deletePeriodsBatch = useDeleteRegistrationPeriodsBatch();
  const finalizeSelection = useFinalizeRoomSelection();
  const updateSearch = (changes: Partial<RegistrationPeriodsSearch>) =>
    onSearchChange(changes);

  const items = query.data?.items ?? [];
  const selectedPeriods = useMemo(
    () => items.filter((p) => selectedIds.has(p.id)),
    [items, selectedIds],
  );

  const allSelected =
    items.length > 0 && items.every((p) => selectedIds.has(p.id));
  const someSelected = items.some((p) => selectedIds.has(p.id)) && !allSelected;

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(items.map((p) => p.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const toggleSelectPeriod = (id: string, checked: boolean) => {
    const next = new Set(selectedIds);
    if (checked) {
      next.add(id);
    } else {
      next.delete(id);
    }
    setSelectedIds(next);
  };

  if (!can("ktx.registration_periods.view")) return <AccessDenied />;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Học vụ / Cấu hình"
        title="Đợt đăng ký KTX"
        description="Cấu hình thời gian tiếp nhận hồ sơ và cách sinh viên nhận chỗ."
        actions={
          can("ktx.registration_periods.create") ? (
            <Button onClick={() => setCreateOpen(true)}>
              <Plus /> Tạo đợt đăng ký
            </Button>
          ) : null
        }
      />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-sm">
          <DebouncedSearchInput
            placeholder="Tìm theo mã hoặc tên đợt đăng ký..."
            value={search.q}
            onChange={(val) => updateSearch({ q: val, page: 1 })}
          />
        </div>
        <Select
          value={search.status ?? "all"}
          onValueChange={(value) =>
            updateSearch({
              status:
                value === "all" ? undefined : (value as typeof search.status),
              page: 1,
            })
          }
        >
          <SelectTrigger className="w-full sm:w-44">
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
      </div>
      <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40">
              <TableHead className="w-10 pl-3">
                <div className="flex items-center pl-1">
                  <Checkbox
                    aria-label="Chọn tất cả đợt đăng ký"
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
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                Mã / Tên đợt
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                Thời gian
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                Thời gian chọn phòng
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap">
                Trạng thái
              </TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {query.isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-12 text-center text-muted-foreground"
                >
                  Đang tải dữ liệu...
                </TableCell>
              </TableRow>
            ) : null}
            {query.isError ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-12 text-center text-destructive"
                >
                  {query.error instanceof Error
                    ? query.error.message
                    : "Không thể tải dữ liệu."}
                </TableCell>
              </TableRow>
            ) : null}
            {!query.isLoading && !query.isError && items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-12 text-center text-muted-foreground"
                >
                  Chưa có đợt đăng ký phù hợp.
                </TableCell>
              </TableRow>
            ) : null}
            {items.map((period) => (
              <TableRow
                key={period.id}
                className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                onClick={() => setDetailPeriod(period)}
              >
                <TableCell
                  className="pl-3"
                  onClick={(event) => event.stopPropagation()}
                >
                  <div className="flex items-center pl-1">
                    <Checkbox
                      aria-label={`Chọn ${period.name}`}
                      checked={selectedIds.has(period.id)}
                      onCheckedChange={(val) =>
                        toggleSelectPeriod(period.id, Boolean(val))
                      }
                    />
                  </div>
                </TableCell>
                <TableCell>
                  <div className="font-semibold text-foreground text-sm">
                    {period.name}
                  </div>
                  <div className="type-supporting font-mono font-semibold text-xs text-muted-foreground">
                    {period.code}
                  </div>
                </TableCell>
                <TableCell className="text-sm text-foreground">
                  {formatDateValue(period.startAt)} –{" "}
                  {formatDateValue(period.endAt)}
                </TableCell>
                <TableCell className="text-sm">
                  {period.roomSelectionStartAt && period.roomSelectionEndAt ? (
                    <div className="space-y-1">
                      <div className="text-foreground">
                        {formatDateValue(period.roomSelectionStartAt)} –{" "}
                        {formatDateValue(period.roomSelectionEndAt)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {period.roomSelectionFinalizedAt
                          ? "Đã chốt phân phòng"
                          : period.roomSelectionNotificationSentAt
                            ? "Đã thông báo sinh viên"
                            : new Date(period.roomSelectionStartAt) > new Date()
                              ? "Chờ mở chọn phòng"
                              : new Date(period.roomSelectionEndAt) < new Date()
                                ? "Đã hết thời gian chọn"
                                : "Đang cho chọn phòng"}
                      </div>
                    </div>
                  ) : (
                    <span className="text-muted-foreground">Chưa cấu hình</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={period.status === "open" ? "success" : "secondary"}
                    className="gap-1.5 font-medium px-2.5 py-0.5"
                  >
                    <span
                      className={`size-1.5 rounded-full ${
                        period.status === "open"
                          ? "bg-emerald-500"
                          : "bg-muted-foreground/60"
                      }`}
                    />
                    {statusLabels[period.status]}
                  </Badge>
                </TableCell>
                <TableCell onClick={(event) => event.stopPropagation()}>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="size-8 text-muted-foreground hover:text-foreground"
                        aria-label={`Thao tác với ${period.name}`}
                        onClick={(event) => event.stopPropagation()}
                      >
                        <MoreHorizontal className="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-52">
                      {can("ktx.registration_periods.view") ? (
                        <DropdownMenuItem
                          onSelect={() => setDetailPeriod(period)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setDetailPeriod(period);
                          }}
                        >
                          <Eye className="size-4 mr-2 text-muted-foreground" />
                          Xem chi tiết
                        </DropdownMenuItem>
                      ) : null}

                      {(period.status === "closed" ||
                        period.status === "archived") &&
                      can("ktx.registration_periods.view") ? (
                        <DropdownMenuItem
                          onSelect={() => {
                            void navigate({
                              to: "/registration-periods/$periodId/room-rules",
                              params: { periodId: period.id },
                            });
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            void navigate({
                              to: "/registration-periods/$periodId/room-rules",
                              params: { periodId: period.id },
                            });
                          }}
                        >
                          <Settings2 className="size-4 mr-2 text-muted-foreground" />
                          {period.roomSelectionNotificationSentAt
                            ? "Xem phân bổ & thông báo"
                            : "Phân bổ phòng"}
                        </DropdownMenuItem>
                      ) : null}

                      {isPeriodEditable(period) &&
                      can("ktx.registration_periods.update") ? (
                        <DropdownMenuItem
                          onSelect={() => setEditPeriod(period)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditPeriod(period);
                          }}
                        >
                          <Pencil className="size-4 mr-2 text-muted-foreground" />
                          Chỉnh sửa
                        </DropdownMenuItem>
                      ) : null}

                      {can("ktx.registration_periods.update") ? (
                        <DropdownMenuItem
                          onSelect={() =>
                            void navigate({ to: "/payment-configurations" })
                          }
                          onClick={(e) => {
                            e.stopPropagation();
                            void navigate({ to: "/payment-configurations" });
                          }}
                        >
                          <Settings2 className="mr-2 size-4 text-muted-foreground" />
                          Cấu hình thanh toán
                        </DropdownMenuItem>
                      ) : null}

                      {period.status === "draft" &&
                      can("ktx.registration_periods.open") ? (
                        <DropdownMenuItem
                          onSelect={() => setPendingOpenPeriod(period)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingOpenPeriod(period);
                          }}
                        >
                          <Play className="size-4 mr-2 text-emerald-600" />
                          Mở đợt
                        </DropdownMenuItem>
                      ) : null}

                      {period.status === "open" &&
                      can("ktx.registration_periods.close") ? (
                        <DropdownMenuItem
                          onSelect={() => setPendingClosePeriod(period)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingClosePeriod(period);
                          }}
                        >
                          <Lock className="size-4 mr-2 text-amber-600" />
                          Đóng đợt
                        </DropdownMenuItem>
                      ) : null}

                      {period.status === "closed" &&
                      can("ktx.registration_periods.archive") ? (
                        <DropdownMenuItem
                          onSelect={() => setPendingArchive(period)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingArchive(period);
                          }}
                        >
                          <Archive className="size-4 mr-2 text-muted-foreground" />
                          Kết thúc đợt
                        </DropdownMenuItem>
                      ) : null}

                      {period.status === "archived" &&
                      can("ktx.registration_periods.archive") ? (
                        <DropdownMenuItem
                          onSelect={() => setPendingRestore(period)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingRestore(period);
                          }}
                        >
                          <RotateCcw className="size-4 mr-2 text-blue-600" />
                          Mở lại đợt
                        </DropdownMenuItem>
                      ) : null}

                      {period.roomSelectionEndAt &&
                      !period.roomSelectionFinalizedAt &&
                      new Date(period.roomSelectionEndAt) < new Date() &&
                      can("ktx.assignments.create") ? (
                        <DropdownMenuItem
                          onSelect={() => setPendingFinalizePeriod(period)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingFinalizePeriod(period);
                          }}
                        >
                          <CheckCheck className="size-4 mr-2 text-emerald-600" />
                          Chốt chọn phòng
                        </DropdownMenuItem>
                      ) : null}

                      {can("ktx.registration_periods.archive") ? (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:bg-destructive/10 focus:text-destructive"
                            onSelect={() => setPendingDeletePeriods([period])}
                            onClick={(e) => {
                              e.stopPropagation();
                              setPendingDeletePeriods([period]);
                            }}
                          >
                            <Trash2 className="size-4 mr-2 text-destructive" />
                            Xóa đợt đăng ký
                          </DropdownMenuItem>
                        </>
                      ) : null}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Modern Seamless Pagination */}
      <DataTablePagination
        page={search.page}
        pageSize={search.pageSize}
        pageCount={query.data?.totalPages ?? 1}
        total={query.data?.total ?? 0}
        onPageChange={(page) => updateSearch({ page })}
        onPageSizeChange={(pageSize) => updateSearch({ pageSize, page: 1 })}
      />

      {/* Floating bulk actions bar */}
      {selectedPeriods.length > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedPeriods.length}
          selectedLabel="đợt đăng ký"
          onClear={() => setSelectedIds(new Set())}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
                onClick={() => {
                  exportRegistrationPeriodsToExcel(selectedPeriods);
                  toast.success(
                    `Đã xuất dữ liệu ${selectedPeriods.length} đợt đăng ký ra file Excel thành công.`,
                  );
                }}
                aria-label="Xuất Excel"
              >
                <Download className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              Xuất Excel ({selectedPeriods.length} đợt đăng ký)
            </TooltipContent>
          </Tooltip>

          {can("ktx.registration_periods.archive") ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="destructive"
                  size="icon"
                  className="size-8 rounded-xl shadow-2xs"
                  onClick={() => {
                    setPendingDeletePeriods(selectedPeriods);
                  }}
                  aria-label="Xóa đã chọn"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                Xóa {selectedPeriods.length} đợt đăng ký đã chọn
              </TooltipContent>
            </Tooltip>
          ) : null}
        </DataTableBulkActions>
      ) : null}
      <CreateRegistrationPeriodDialog
        key={editPeriod?.id ?? (createOpen ? "create" : "closed")}
        open={createOpen}
        onOpenChange={setCreateOpen}
        academicYears={years.data?.items ?? []}
        paymentConfigurations={paymentConfigurations.data ?? []}
        period={null}
      />
      <CreateRegistrationPeriodDialog
        key={editPeriod?.id ?? "edit-closed"}
        open={Boolean(editPeriod)}
        onOpenChange={(open) => {
          if (!open) setEditPeriod(null);
        }}
        academicYears={years.data?.items ?? []}
        paymentConfigurations={paymentConfigurations.data ?? []}
        period={editPeriod}
      />
      <RegistrationPeriodDetailDialog
        open={Boolean(detailPeriod)}
        onOpenChange={(open) => {
          if (!open) setDetailPeriod(null);
        }}
        period={detailPeriod}
        canEdit={Boolean(
          detailPeriod &&
            isPeriodEditable(detailPeriod) &&
            can("ktx.registration_periods.update"),
        )}
        canManageRooms={Boolean(
          detailPeriod &&
            (detailPeriod.status === "closed" ||
              detailPeriod.status === "archived") &&
            can("ktx.registration_periods.view"),
        )}
        onEdit={(period) => {
          setDetailPeriod(null);
          setEditPeriod(period);
        }}
        onManageRooms={(period) => {
          setDetailPeriod(null);
          void navigate({
            to: "/registration-periods/$periodId/room-rules",
            params: { periodId: period.id },
          });
        }}
        onConfigurePayment={() => {
          setDetailPeriod(null);
          void navigate({ to: "/payment-configurations" });
        }}
      />
      <ConfirmDialog
        open={Boolean(pendingOpenPeriod)}
        onOpenChange={(open) => {
          if (!open && !transition.isPending) setPendingOpenPeriod(null);
        }}
        title="Mở đợt đăng ký nội trú?"
        description={
          pendingOpenPeriod ? (
            <div className="space-y-2 text-xs">
              <p>
                Bạn có chắc chắn muốn mở đợt đăng ký{" "}
                <strong className="text-foreground">
                  “{pendingOpenPeriod.name}”
                </strong>{" "}
                ({pendingOpenPeriod.code}) không?
              </p>
              <div className="rounded-lg border bg-muted/40 p-3 space-y-1 text-muted-foreground font-normal">
                <div>
                  <span>Thời gian tiếp nhận: </span>
                  <strong className="text-foreground">
                    {formatDateValue(pendingOpenPeriod.startAt)} –{" "}
                    {formatDateValue(pendingOpenPeriod.endAt)}
                  </strong>
                </div>
              </div>
              <p className="text-muted-foreground text-[11px]">
                Lưu ý: Sau khi mở đợt, sinh viên đủ điều kiện sẽ có thể bắt đầu
                nộp hồ sơ đăng ký nội trú KTX trực tuyến qua cổng thông tin.
              </p>
            </div>
          ) : (
            ""
          )
        }
        confirmLabel="Mở đợt đăng ký"
        confirmVariant="default"
        isLoading={transition.isPending}
        onConfirm={() => {
          if (!pendingOpenPeriod) return;
          void transition
            .mutateAsync({ id: pendingOpenPeriod.id, action: "open" })
            .then(() => {
              setPendingOpenPeriod(null);
              toast.success("Đã mở đợt đăng ký tiếp nhận hồ sơ.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể mở đợt đăng ký.",
              ),
            );
        }}
      />
      <ConfirmDialog
        open={Boolean(pendingClosePeriod)}
        onOpenChange={(open) => {
          if (!open && !transition.isPending) setPendingClosePeriod(null);
        }}
        title="Đóng đợt đăng ký nội trú?"
        description={
          pendingClosePeriod ? (
            <div className="space-y-2 text-xs">
              <p>
                Bạn có chắc chắn muốn đóng tiếp nhận hồ sơ cho đợt{" "}
                <strong className="text-foreground">
                  “{pendingClosePeriod.name}”
                </strong>{" "}
                ({pendingClosePeriod.code}) không?
              </p>
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-amber-700 dark:text-amber-300 text-[11px] font-medium">
                ⚠️ Sau khi đóng đợt, hệ thống sẽ ngừng tiếp nhận toàn bộ hồ sơ
                đăng ký mới từ sinh viên. Cán bộ có thể tiến hành phân bổ phòng
                và gửi thông báo chọn phòng.
              </div>
            </div>
          ) : (
            ""
          )
        }
        confirmLabel="Đóng đợt đăng ký"
        confirmVariant="destructive"
        isLoading={transition.isPending}
        onConfirm={() => {
          if (!pendingClosePeriod) return;
          void transition
            .mutateAsync({ id: pendingClosePeriod.id, action: "close" })
            .then(() => {
              setPendingClosePeriod(null);
              toast.success("Đã đóng đợt đăng ký tiếp nhận hồ sơ.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể đóng đợt đăng ký.",
              ),
            );
        }}
      />
      <ConfirmDialog
        open={Boolean(pendingFinalizePeriod)}
        onOpenChange={(open) => {
          if (!open && !finalizeSelection.isPending) {
            setPendingFinalizePeriod(null);
          }
        }}
        title="Chốt lựa chọn phòng?"
        description={
          pendingFinalizePeriod ? (
            <div className="space-y-2 text-xs">
              <p>
                Bạn có chắc chắn muốn chốt phân phòng cho toàn bộ sinh viên đã
                chọn phòng trong đợt{" "}
                <strong className="text-foreground">
                  “{pendingFinalizePeriod.name}”
                </strong>{" "}
                ({pendingFinalizePeriod.code}) không?
              </p>
              <div className="rounded-lg border bg-muted/40 p-3 space-y-1 text-muted-foreground font-normal">
                <div>
                  <span>Thời gian chọn phòng đã kết thúc: </span>
                  <strong className="text-foreground">
                    {formatDateValue(pendingFinalizePeriod.roomSelectionEndAt)}
                  </strong>
                </div>
              </div>
              <p className="text-muted-foreground text-[11px]">
                Hệ thống sẽ kiểm tra lại các hồ sơ đang giữ chỗ: hồ sơ hợp lệ sẽ
                chuyển thành <strong>Đã xếp phòng chính thức</strong> và tự động
                phát thông báo chúc mừng đến sinh viên.
              </p>
            </div>
          ) : (
            ""
          )
        }
        confirmLabel="Chốt phân phòng"
        confirmVariant="default"
        isLoading={finalizeSelection.isPending}
        onConfirm={() => {
          if (!pendingFinalizePeriod) return;
          void finalizeSelection
            .mutateAsync(pendingFinalizePeriod.id)
            .then((result) => {
              setPendingFinalizePeriod(null);
              toast.success(
                `Đã chốt ${result.finalizedCount} lựa chọn${result.skippedCount ? `, bỏ qua ${result.skippedCount}` : ""}.`,
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể chốt lựa chọn phòng.",
              ),
            );
        }}
      />
      <ConfirmDialog
        open={Boolean(pendingArchive)}
        onOpenChange={(open) => {
          if (!open && !transition.isPending) setPendingArchive(null);
        }}
        title="Kết thúc đợt đăng ký?"
        description={
          pendingArchive
            ? `“${pendingArchive.name}” sẽ chuyển sang trạng thái Đã kết thúc. Toàn bộ dữ liệu hồ sơ và phân phòng của đợt sẽ được khóa cố định để lưu trữ lịch sử, không thể chỉnh sửa thêm.`
            : ""
        }
        confirmLabel="Kết thúc đợt"
        isLoading={transition.isPending}
        onConfirm={() => {
          if (!pendingArchive) return;
          void transition
            .mutateAsync({ id: pendingArchive.id, action: "archive" })
            .then(() => {
              setPendingArchive(null);
              toast.success("Đã kết thúc đợt đăng ký thành công.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể kết thúc đợt đăng ký.",
              ),
            );
        }}
      />
      <ConfirmDialog
        open={Boolean(pendingRestore)}
        onOpenChange={(open) => {
          if (!open && !transition.isPending) setPendingRestore(null);
        }}
        title="Mở lại đợt đăng ký?"
        description={
          pendingRestore
            ? `“${pendingRestore.name}” sẽ được đưa về trạng thái Đã đóng để tiếp tục xem và xử lý. Việc mở lại không tự động kích hoạt nộp hồ sơ hoặc thời gian chọn phòng.`
            : ""
        }
        confirmLabel="Mở lại đợt"
        confirmVariant="default"
        isLoading={transition.isPending}
        onConfirm={() => {
          if (!pendingRestore) return;
          void transition
            .mutateAsync({ id: pendingRestore.id, action: "restore" })
            .then(() => {
              setPendingRestore(null);
              toast.success("Đã mở lại đợt đăng ký thành công.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể mở lại đợt đăng ký.",
              ),
            );
        }}
      />
      <ConfirmDialog
        open={Boolean(pendingDeletePeriods && pendingDeletePeriods.length > 0)}
        onOpenChange={(open) => {
          if (!open && !transition.isPending && !deletePeriodsBatch.isPending) {
            setPendingDeletePeriods(null);
          }
        }}
        title={
          pendingDeletePeriods && pendingDeletePeriods.length > 1
            ? `Xác nhận xóa ${pendingDeletePeriods.length} đợt đăng ký đã chọn?`
            : "Xác nhận xóa đợt đăng ký?"
        }
        description={
          pendingDeletePeriods && pendingDeletePeriods.length > 0
            ? pendingDeletePeriods.length === 1
              ? `Bạn có chắc chắn muốn xóa đợt đăng ký “${pendingDeletePeriods[0].name}” (${pendingDeletePeriods[0].code}) không? Hệ thống sẽ từ chối nếu đợt đã có sinh viên nộp hồ sơ hoặc đang mở tiếp nhận.`
              : `Bạn có chắc chắn muốn xóa ${pendingDeletePeriods.length} đợt đăng ký đã chọn không? Hệ thống sẽ từ chối nếu có đợt đã có sinh viên đăng ký hồ sơ hoặc đang mở tiếp nhận.`
            : ""
        }
        confirmLabel={
          pendingDeletePeriods && pendingDeletePeriods.length > 1
            ? `Xác nhận xóa ${pendingDeletePeriods.length} đợt`
            : "Xóa đợt đăng ký"
        }
        confirmVariant="destructive"
        isLoading={transition.isPending || deletePeriodsBatch.isPending}
        onConfirm={() => {
          if (!pendingDeletePeriods || pendingDeletePeriods.length === 0)
            return;
          const count = pendingDeletePeriods.length;
          const promise =
            count === 1
              ? transition.mutateAsync({
                  id: pendingDeletePeriods[0].id,
                  action: "deactivate",
                })
              : deletePeriodsBatch.mutateAsync(
                  pendingDeletePeriods.map((p) => p.id),
                );

          void promise
            .then(() => {
              setPendingDeletePeriods(null);
              setSelectedIds(new Set());
              toast.success(
                count === 1
                  ? "Đã xóa đợt đăng ký thành công."
                  : `Đã xóa ${count} đợt đăng ký thành công.`,
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể xóa đợt đăng ký.",
              ),
            );
        }}
      />
    </div>
  );
}

function RegistrationPeriodDetailDialog({
  open,
  onOpenChange,
  period,
  canEdit,
  canManageRooms,
  onEdit,
  onManageRooms,
  onConfigurePayment,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  period: RegistrationPeriod | null;
  canEdit: boolean;
  canManageRooms: boolean;
  onEdit: (period: RegistrationPeriod) => void;
  onManageRooms: (period: RegistrationPeriod) => void;
  onConfigurePayment: (period: RegistrationPeriod) => void;
}) {
  if (!period) return null;

  const roomSelectionConfigured = Boolean(
    period.roomSelectionStartAt && period.roomSelectionEndAt,
  );
  const roomSelectionState = period.roomSelectionFinalizedAt
    ? "Đã chốt phân phòng"
    : period.roomSelectionNotificationSentAt
      ? "Đã thông báo sinh viên"
      : roomSelectionConfigured
        ? new Date(period.roomSelectionStartAt as string) > new Date()
          ? "Chờ mở chọn phòng"
          : new Date(period.roomSelectionEndAt as string) < new Date()
            ? "Đã hết thời gian chọn"
            : "Đang cho chọn phòng"
        : "Chưa cấu hình";

  const formatDate = (value: string | null | undefined) =>
    formatDateValue(value) || "Chưa cấu hình";

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-w-2xl p-0 gap-0 overflow-hidden shadow-xl">
        {/* Header */}
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-6 py-4 pr-12">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base sm:text-lg font-bold">
            <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground shrink-0">
              <CalendarDays className="size-4" />
            </div>
            <span>Chi tiết đợt đăng ký</span>
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs text-muted-foreground mt-0.5">
            Cấu hình thời gian nhận hồ sơ, chọn phòng và trạng thái hoạt động
            của đợt.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <div className="space-y-4 px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)]">
          {/* Hero Banner */}
          <div className="rounded-xl border bg-muted/20 p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <h3 className="font-bold text-foreground text-base leading-tight">
                {period.name}
              </h3>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Mã đợt:</span>
                <Badge
                  variant="outline"
                  className="font-mono text-xs font-semibold px-2 py-0"
                >
                  {period.code}
                </Badge>
              </div>
            </div>
            <Badge
              variant={period.status === "open" ? "success" : "secondary"}
              className="gap-1.5 font-medium px-3 py-1 text-xs self-start sm:self-auto shrink-0"
            >
              <span
                className={`size-2 rounded-full ${
                  period.status === "open"
                    ? "bg-emerald-500"
                    : period.status === "draft"
                      ? "bg-amber-500"
                      : "bg-muted-foreground/60"
                }`}
              />
              {statusLabels[period.status]}
            </Badge>
          </div>

          {/* Unified 2-Column Info Grid */}
          <div className="grid gap-3.5 sm:grid-cols-2 text-xs">
            <div className="flex items-start gap-3 rounded-lg border bg-card p-3.5 shadow-2xs">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <GraduationCap className="size-4" />
              </div>
              <div className="min-w-0 space-y-0.5">
                <p className="text-xs text-muted-foreground">Năm học</p>
                <p className="text-sm font-semibold text-foreground break-words">
                  {period.academicYearCode || "Chưa xác định"}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-lg border bg-card p-3.5 shadow-2xs">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <Calendar className="size-4" />
              </div>
              <div className="min-w-0 space-y-0.5">
                <p className="text-xs text-muted-foreground">
                  Thời gian nhận hồ sơ
                </p>
                <p className="text-sm font-semibold text-foreground break-words">
                  {formatDate(period.startAt)} – {formatDate(period.endAt)}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-lg border bg-card p-3.5 shadow-2xs">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <DoorOpen className="size-4" />
              </div>
              <div className="min-w-0 space-y-0.5">
                <p className="text-xs text-muted-foreground">
                  Thời gian chọn phòng
                </p>
                <p className="text-sm font-semibold text-foreground break-words">
                  {roomSelectionConfigured
                    ? `${formatDate(period.roomSelectionStartAt)} – ${formatDate(period.roomSelectionEndAt)}`
                    : "Chưa cấu hình"}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-lg border bg-card p-3.5 shadow-2xs">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <ShieldCheck className="size-4" />
              </div>
              <div className="min-w-0 space-y-0.5">
                <p className="text-xs text-muted-foreground">
                  Trạng thái chọn phòng
                </p>
                <p className="text-sm font-semibold text-foreground break-words">
                  {roomSelectionState}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-lg border bg-card p-3.5 shadow-2xs">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <Bell className="size-4" />
              </div>
              <div className="min-w-0 space-y-0.5">
                <p className="text-xs text-muted-foreground">
                  Thông báo sinh viên
                </p>
                <p className="text-sm font-semibold text-foreground break-words">
                  {period.roomSelectionNotificationSentAt
                    ? `Đã gửi ${formatDate(period.roomSelectionNotificationSentAt)}`
                    : "Chưa gửi"}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-lg border bg-card p-3.5 shadow-2xs">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <CheckCircle2 className="size-4" />
              </div>
              <div className="min-w-0 space-y-0.5">
                <p className="text-xs text-muted-foreground">Chốt phân phòng</p>
                <p className="text-sm font-semibold text-foreground break-words">
                  {period.roomSelectionFinalizedAt
                    ? `Đã chốt ${formatDate(period.roomSelectionFinalizedAt)}`
                    : "Chưa chốt"}
                </p>
              </div>
            </div>
          </div>

          {/* Note Callout */}
          {period.note ? (
            <div className="flex items-start gap-2.5 rounded-lg border bg-muted/20 p-3.5 text-xs text-muted-foreground">
              <StickyNote className="size-4 shrink-0 text-muted-foreground mt-0.5" />
              <div>
                <span className="font-semibold text-foreground">Ghi chú: </span>
                <span className="whitespace-pre-wrap">{period.note}</span>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer Actions */}
        <ResponsiveDialogFooter className="border-t bg-muted/20 px-4 py-3 sm:px-6 sm:py-3.5">
          <div className="flex flex-col-reverse gap-2 w-full sm:flex-row sm:items-center sm:justify-between">
            <Button
              variant="outline"
              size="sm"
              className="w-full sm:w-auto h-9 text-xs"
              onClick={() => onOpenChange(false)}
            >
              Đóng
            </Button>
            <div className="flex flex-col gap-2 w-full sm:flex-row sm:w-auto sm:items-center sm:justify-end sm:gap-2">
              <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-2">
                {canManageRooms ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full sm:w-auto h-9 gap-1.5 text-xs"
                    onClick={() => onManageRooms(period)}
                  >
                    <SlidersHorizontal className="size-3.5" />
                    <span>Phân bổ phòng</span>
                  </Button>
                ) : null}
                {canEdit ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full sm:w-auto h-9 gap-1.5 text-xs"
                    onClick={() => onConfigurePayment(period)}
                  >
                    <CreditCard className="size-3.5" />
                    <span>Thanh toán</span>
                  </Button>
                ) : null}
              </div>
              {canEdit ? (
                <Button
                  size="sm"
                  className="w-full sm:w-auto h-9 gap-1.5 text-xs font-semibold"
                  onClick={() => onEdit(period)}
                >
                  <Pencil className="size-3.5" />
                  <span>Chỉnh sửa</span>
                </Button>
              ) : null}
            </div>
          </div>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

function CreateRegistrationPeriodDialog({
  open,
  onOpenChange,
  academicYears,
  paymentConfigurations,
  period,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  academicYears: { id: string; name: string }[];
  paymentConfigurations: PaymentConfiguration[];
  period: RegistrationPeriod | null;
}) {
  const mutation = useCreateRegistrationPeriod();
  const updateMutation = useUpdateRegistrationPeriod();
  const isEdit = Boolean(period);
  const applicationWindowLocked = period?.status === "closed";
  const form = useForm({
    defaultValues: {
      code: period?.code ?? "",
      name: period?.name ?? "",
      academicYearId: period?.academicYearId ?? academicYears[0]?.id ?? "",
      paymentConfigurationId:
        period?.paymentConfigurationId ??
        paymentConfigurations.find((item) => item.isEnabled)?.id ??
        paymentConfigurations[0]?.id ??
        "",
      startAt: parseIsoToDate(period?.startAt),
      endAt: parseIsoToDate(period?.endAt),
      roomSelectionStartAt: parseIsoToDate(period?.roomSelectionStartAt),
      roomSelectionEndAt: parseIsoToDate(period?.roomSelectionEndAt),
      note: period?.note ?? "",
    },
    validators: {
      onSubmit: z
        .object({
          code: z.string().trim().min(1, "Mã đợt là bắt buộc"),
          name: z.string().trim().min(1, "Tên đợt là bắt buộc"),
          academicYearId: z.string().min(1, "Năm học là bắt buộc"),
          paymentConfigurationId: z
            .string()
            .trim()
            .min(1, "Cấu hình thanh toán là bắt buộc.")
            .refine(
              (val) => val !== "none",
              "Vui lòng chọn cấu hình thanh toán cho đợt đăng ký.",
            ),
          startAt: optionalDate,
          endAt: optionalDate,
          roomSelectionStartAt: optionalDate,
          roomSelectionEndAt: optionalDate,
          note: z.string(),
        })
        .superRefine((value, context) => {
          const day = (date: Date) =>
            new Date(
              date.getFullYear(),
              date.getMonth(),
              date.getDate(),
            ).getTime();

          if (!value.startAt) {
            context.addIssue({
              code: "custom",
              path: ["startAt"],
              message: "Thời gian bắt đầu nhận hồ sơ là bắt buộc.",
            });
          }

          if (!value.endAt) {
            context.addIssue({
              code: "custom",
              path: ["endAt"],
              message: "Thời gian kết thúc nhận hồ sơ là bắt buộc.",
            });
          }

          if (
            value.startAt &&
            value.endAt &&
            day(value.endAt) < day(value.startAt)
          ) {
            context.addIssue({
              code: "custom",
              path: ["endAt"],
              message:
                "Thời gian kết thúc nhận hồ sơ phải sau hoặc cùng ngày bắt đầu.",
            });
          }

          if (
            value.endAt &&
            value.roomSelectionStartAt &&
            day(value.roomSelectionStartAt) <= day(value.endAt)
          ) {
            context.addIssue({
              code: "custom",
              path: ["roomSelectionStartAt"],
              message:
                "Thời gian chọn phòng phải bắt đầu sau khi kết thúc nhận hồ sơ.",
            });
          }

          if (value.roomSelectionStartAt && !value.roomSelectionEndAt) {
            context.addIssue({
              code: "custom",
              path: ["roomSelectionEndAt"],
              message: "Vui lòng chọn thời gian kết thúc chọn phòng.",
            });
          }

          if (!value.roomSelectionStartAt && value.roomSelectionEndAt) {
            context.addIssue({
              code: "custom",
              path: ["roomSelectionStartAt"],
              message: "Vui lòng chọn thời gian bắt đầu chọn phòng.",
            });
          }

          if (
            value.roomSelectionStartAt &&
            value.roomSelectionEndAt &&
            day(value.roomSelectionEndAt) < day(value.roomSelectionStartAt)
          ) {
            context.addIssue({
              code: "custom",
              path: ["roomSelectionEndAt"],
              message:
                "Thời gian kết thúc chọn phòng phải sau hoặc cùng ngày thời gian bắt đầu.",
            });
          }
        }),
    },
    onSubmit: async ({ value }) => {
      if (!value.startAt || !value.endAt) {
        toast.error("Vui lòng chọn thời gian bắt đầu và kết thúc.");
        return;
      }
      const input = {
        code: value.code,
        name: value.name,
        academicYearId: value.academicYearId,
        paymentConfigurationId:
          value.paymentConfigurationId === "none" ||
          !value.paymentConfigurationId
            ? undefined
            : value.paymentConfigurationId,
        startAt: startOfDay(value.startAt).toISOString(),
        endAt: endOfDay(value.endAt).toISOString(),
        roomSelectionStartAt: value.roomSelectionStartAt
          ? startOfDay(value.roomSelectionStartAt).toISOString()
          : undefined,
        roomSelectionEndAt: value.roomSelectionEndAt
          ? endOfDay(value.roomSelectionEndAt).toISOString()
          : undefined,
        note: value.note.trim() || undefined,
      };
      try {
        if (period) await updateMutation.mutateAsync({ id: period.id, input });
        else await mutation.mutateAsync(input);
        onOpenChange(false);
        toast.success(
          isEdit ? "Đã cập nhật đợt đăng ký." : "Đã tạo đợt đăng ký.",
        );
      } catch (error: unknown) {
        toast.error(
          error instanceof Error ? error.message : "Không thể lưu đợt đăng ký.",
        );
      }
    },
  });
  const pending = mutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] w-full max-w-2xl flex-col overflow-hidden p-0 gap-0 shadow-xl">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-6 py-4 pr-12">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base sm:text-lg font-bold">
            <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground shrink-0">
              {isEdit ? (
                <Pencil className="size-4" />
              ) : (
                <Plus className="size-4" />
              )}
            </div>
            <span>{isEdit ? "Chỉnh sửa đợt đăng ký" : "Tạo đợt đăng ký"}</span>
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs text-muted-foreground mt-0.5">
            {isEdit
              ? "Cập nhật thời gian tiếp nhận hồ sơ, chọn phòng và cấu hình thanh toán của đợt."
              : "Cấu hình thông tin đợt đăng ký nội trú mới trong hệ thống."}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit();
          }}
        >
          <div className="space-y-4 px-6 py-5">
            {/* Row 1: Mã đợt & Tên đợt */}
            <div className="grid gap-4 sm:grid-cols-2 text-xs">
              <form.Field name="code">
                {(field) => (
                  <Field>
                    <FieldLabel
                      htmlFor="period-code"
                      className="flex items-center gap-1.5 text-xs font-medium"
                    >
                      <span>Mã đợt</span>
                      {isEdit ? (
                        <Lock className="size-3 text-muted-foreground ml-auto" />
                      ) : (
                        <span className="text-destructive">*</span>
                      )}
                    </FieldLabel>
                    <Input
                      id="period-code"
                      placeholder="VD: KTX-D1"
                      value={field.state.value}
                      disabled={isEdit || pending}
                      className={
                        isEdit
                          ? "bg-muted/40 font-mono font-medium"
                          : "font-mono"
                      }
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>

              <form.Field name="name">
                {(field) => (
                  <Field>
                    <FieldLabel
                      htmlFor="period-name"
                      className="flex items-center gap-1.5 text-xs font-medium"
                    >
                      <span>Tên đợt</span>
                      <span className="text-destructive">*</span>
                    </FieldLabel>
                    <Input
                      id="period-name"
                      placeholder="VD: Đăng ký KTX đợt 1 năm 2026"
                      value={field.state.value}
                      disabled={pending}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
            </div>

            {/* Row 2: Năm học & Cấu hình thanh toán */}
            <div className="grid gap-4 sm:grid-cols-2 text-xs">
              <form.Field name="academicYearId">
                {(field) => (
                  <Field>
                    <FieldLabel
                      htmlFor="period-academic-year"
                      className="text-xs font-medium"
                    >
                      <span>Năm học</span>
                      <span className="text-destructive">*</span>
                    </FieldLabel>
                    <Select
                      value={field.state.value}
                      disabled={pending}
                      onValueChange={(value) => field.handleChange(value)}
                    >
                      <SelectTrigger
                        id="period-academic-year"
                        className="text-xs"
                      >
                        <SelectValue placeholder="Chọn năm học" />
                      </SelectTrigger>
                      <SelectContent>
                        {academicYears.map((year) => (
                          <SelectItem key={year.id} value={year.id}>
                            {year.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>

              <form.Field name="paymentConfigurationId">
                {(field) => (
                  <Field>
                    <FieldLabel
                      htmlFor="period-payment-configuration"
                      className="flex items-center gap-1 text-xs font-medium"
                    >
                      <span>Cấu hình thanh toán</span>
                      <span className="text-destructive">*</span>
                    </FieldLabel>
                    <Select
                      value={field.state.value}
                      disabled={pending}
                      onValueChange={(value) => field.handleChange(value)}
                    >
                      <SelectTrigger
                        id="period-payment-configuration"
                        className="text-xs"
                      >
                        <SelectValue placeholder="Chọn cấu hình thanh toán..." />
                      </SelectTrigger>
                      <SelectContent>
                        {paymentConfigurations
                          .filter(
                            (item) =>
                              item.isEnabled ||
                              item.id === period?.paymentConfigurationId,
                          )
                          .map((item) => (
                            <SelectItem key={item.id} value={item.id}>
                              {item.name}
                              {item.qrMode === "uploaded"
                                ? " · QR tải lên"
                                : " · QR động"}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
            </div>

            {/* Locked Notice if closed */}
            {applicationWindowLocked ? (
              <div className="flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-300">
                <Lock className="size-3.5 shrink-0" />
                <span>
                  Đợt đã đóng nên thời gian tiếp nhận hồ sơ được giữ nguyên.
                </span>
              </div>
            ) : null}

            {/* Row 3: Thời gian nhận hồ sơ */}
            <div className="grid gap-4 sm:grid-cols-2 text-xs">
              <form.Field name="startAt">
                {(field) => (
                  <Field>
                    <FieldLabel
                      htmlFor="period-start-at"
                      className="text-xs font-medium"
                    >
                      <span>Thời gian bắt đầu nhận hồ sơ</span>
                      <span className="text-destructive">*</span>
                    </FieldLabel>
                    <DatePicker
                      id="period-start-at"
                      value={field.state.value}
                      disabled={applicationWindowLocked || pending}
                      onBlur={field.handleBlur}
                      onChange={(value) => field.handleChange(value)}
                      onValidationChange={(message) => {
                        field.setMeta((meta) => ({
                          ...meta,
                          errors: message ? [message] : [],
                        }));
                      }}
                      aria-invalid={Boolean(
                        firstError(field.state.meta.errors),
                      )}
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>

              <form.Field name="endAt">
                {(field) => (
                  <Field>
                    <FieldLabel
                      htmlFor="period-end-at"
                      className="text-xs font-medium"
                    >
                      <span>Thời gian kết thúc nhận hồ sơ</span>
                      <span className="text-destructive">*</span>
                    </FieldLabel>
                    <DatePicker
                      id="period-end-at"
                      value={field.state.value}
                      disabled={applicationWindowLocked || pending}
                      minDate={form.getFieldValue("startAt")}
                      onBlur={field.handleBlur}
                      onChange={(value) => field.handleChange(value)}
                      onValidationChange={(message) => {
                        field.setMeta((meta) => ({
                          ...meta,
                          errors: message ? [message] : [],
                        }));
                      }}
                      aria-invalid={Boolean(
                        firstError(field.state.meta.errors),
                      )}
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
            </div>

            {/* Divider Subtitle: Thời gian chọn phòng */}
            <div className="pt-1">
              <div className="pb-1 border-b text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
                <span>Thời gian sinh viên chọn phòng</span>
                <span className="text-[11px] font-normal normal-case text-muted-foreground">
                  Tùy chọn
                </span>
              </div>
            </div>

            {/* Row 4: Thời gian chọn phòng */}
            <div className="grid gap-4 sm:grid-cols-2 text-xs">
              <form.Field name="roomSelectionStartAt">
                {(field) => (
                  <Field>
                    <FieldLabel
                      htmlFor="period-room-start"
                      className="text-xs font-medium"
                    >
                      Bắt đầu chọn phòng
                    </FieldLabel>
                    <DatePicker
                      id="period-room-start"
                      value={field.state.value}
                      disabled={pending}
                      minDate={
                        form.getFieldValue("endAt")
                          ? new Date(
                              form.getFieldValue("endAt")!.getTime() +
                                24 * 60 * 60 * 1000,
                            )
                          : undefined
                      }
                      onBlur={field.handleBlur}
                      onChange={(value) => field.handleChange(value)}
                      onValidationChange={(message) => {
                        field.setMeta((meta) => ({
                          ...meta,
                          errors: message ? [message] : [],
                        }));
                      }}
                      aria-invalid={Boolean(
                        firstError(field.state.meta.errors),
                      )}
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>

              <form.Field name="roomSelectionEndAt">
                {(field) => (
                  <Field>
                    <FieldLabel
                      htmlFor="period-room-end"
                      className="text-xs font-medium"
                    >
                      Kết thúc chọn phòng
                    </FieldLabel>
                    <DatePicker
                      id="period-room-end"
                      value={field.state.value}
                      disabled={pending}
                      minDate={form.getFieldValue("roomSelectionStartAt")}
                      onBlur={field.handleBlur}
                      onChange={(value) => field.handleChange(value)}
                      onValidationChange={(message) => {
                        field.setMeta((meta) => ({
                          ...meta,
                          errors: message ? [message] : [],
                        }));
                      }}
                      aria-invalid={Boolean(
                        firstError(field.state.meta.errors),
                      )}
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
            </div>

            {/* Row 5: Ghi chú */}
            <form.Field name="note">
              {(field) => (
                <Field>
                  <FieldLabel
                    htmlFor="period-note"
                    className="text-xs font-medium"
                  >
                    Ghi chú
                  </FieldLabel>
                  <Textarea
                    id="period-note"
                    placeholder="Thông tin hướng dẫn hoặc lưu ý cho cán bộ xử lý"
                    rows={2}
                    className="text-xs"
                    value={field.state.value}
                    disabled={pending}
                    onBlur={field.handleBlur}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                  {firstError(field.state.meta.errors) ? (
                    <FieldError>
                      {firstError(field.state.meta.errors)}
                    </FieldError>
                  ) : null}
                </Field>
              )}
            </form.Field>
          </div>

          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6 sm:py-3.5">
            <div className="grid grid-cols-2 gap-3 w-full sm:flex sm:w-auto sm:items-center sm:justify-end sm:gap-2.5">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full sm:w-auto h-9 text-xs"
                disabled={pending}
                onClick={() => onOpenChange(false)}
              >
                Hủy
              </Button>
              <Button
                type="submit"
                size="sm"
                className="w-full sm:w-auto h-9 text-xs font-semibold"
                disabled={pending}
              >
                {pending ? "Đang lưu..." : isEdit ? "Lưu thay đổi" : "Tạo đợt"}
              </Button>
            </div>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
