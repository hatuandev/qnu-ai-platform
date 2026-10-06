import { useForm } from "@tanstack/react-form";
import { useNavigate } from "@tanstack/react-router";
import {
  Eye,
  FileSpreadsheet,
  MoreHorizontal,
  Plus,
  ReceiptText,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Combobox } from "@/components/admin/combobox";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DatePicker } from "@/components/admin/date-pickers";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { EmptyState } from "@/components/admin/empty-state";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
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
import { useAcademicYearsQuery } from "@/features/academic-years/api";
import {
  exportInvoicesToExcel,
  useDeleteInvoice,
  useGenerateInvoicesBatch,
  useInvoicesQuery,
} from "@/features/invoices/api";
import {
  type GenerateBatchInput,
  type InvoiceStatus,
  invoiceStatusLabels,
  invoiceStatusVariants,
} from "@/features/invoices/types";
import { useRegistrationPeriodsQuery } from "@/features/registration-periods/api";
import { formatDateOnly, formatDateValue } from "@/lib/date-utils";
import { getFormErrorMessage } from "@/lib/form-errors";
import { cn } from "@/lib/utils";

const money = (value: number) =>
  new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(
    value,
  );

function BatchDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const years = useAcademicYearsQuery({ page: 1, pageSize: 50 });
  const [selectedAcademicYearId, setSelectedAcademicYearId] = useState("");
  const periods = useRegistrationPeriodsQuery({
    page: 1,
    pageSize: 100,
    academicYearId: selectedAcademicYearId || undefined,
  });
  const mutation = useGenerateInvoicesBatch();
  const form = useForm({
    defaultValues: {
      academicYearId: "",
      registrationPeriodId: "",
      dueDate: undefined as Date | undefined,
      note: "",
    },
    validators: {
      onSubmit: z.object({
        academicYearId: z.string().min(1, "Năm học là bắt buộc."),
        registrationPeriodId: z.string().min(1, "Đợt đăng ký là bắt buộc."),
        dueDate: z.union([z.date(), z.undefined()]),
        note: z.string().max(2000, "Ghi chú tối đa 2.000 ký tự."),
      }),
    },
    onSubmit: async ({ value }) => {
      const input: GenerateBatchInput = {
        academicYearId: value.academicYearId,
        registrationPeriodId: value.registrationPeriodId,
        dueDate: formatDateOnly(value.dueDate) || undefined,
        note: value.note.trim() || undefined,
      };
      await mutation
        .mutateAsync(input)
        .then((res) => {
          toast.success(
            `Đã tạo thành công ${res.generated} hóa đơn${res.skipped ? `, bỏ qua ${res.skipped}` : ""}.`,
          );
          onOpenChange(false);
        })
        .catch((err: unknown) => {
          toast.error(
            err instanceof Error
              ? err.message
              : "Không thể tạo hóa đơn theo đợt.",
          );
        });
    },
  });

  const firstError = (errors: unknown[]) =>
    errors.length ? getFormErrorMessage(errors[0]) : undefined;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-w-lg">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>Tạo hóa đơn theo đợt</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Tạo hóa đơn tự động cho tất cả sinh viên đã chốt phòng hoặc đang cư
            trú trong đợt đã chọn.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          className="space-y-4 py-3"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          {/* Năm học */}
          <form.Field name="academicYearId">
            {(field) => (
              <Field>
                <FieldLabel>
                  Năm học <span className="text-destructive">*</span>
                </FieldLabel>
                <Select
                  value={field.state.value}
                  disabled={mutation.isPending}
                  onValueChange={(value) => {
                    setSelectedAcademicYearId(value);
                    field.handleChange(value);
                    form.setFieldValue("registrationPeriodId", "");
                  }}
                >
                  <SelectTrigger className="w-full text-xs">
                    <SelectValue placeholder="Chọn năm học..." />
                  </SelectTrigger>
                  <SelectContent>
                    {(years.data?.items ?? []).map((year) => (
                      <SelectItem key={year.id} value={year.id}>
                        Năm học {year.code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {firstError(field.state.meta.errors) ? (
                  <FieldError>{firstError(field.state.meta.errors)}</FieldError>
                ) : null}
              </Field>
            )}
          </form.Field>

          {/* Đợt đăng ký */}
          <form.Field name="registrationPeriodId">
            {(field) => (
              <Field>
                <FieldLabel>
                  Đợt đăng ký <span className="text-destructive">*</span>
                </FieldLabel>
                <Select
                  value={field.state.value}
                  disabled={mutation.isPending || !selectedAcademicYearId}
                  onValueChange={field.handleChange}
                >
                  <SelectTrigger className="w-full text-xs">
                    <SelectValue
                      placeholder={
                        selectedAcademicYearId
                          ? "Chọn đợt đăng ký..."
                          : "Vui lòng chọn năm học trước"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {(periods.data?.items ?? []).map((period) => (
                      <SelectItem key={period.id} value={period.id}>
                        {period.code} · {period.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {firstError(field.state.meta.errors) ? (
                  <FieldError>{firstError(field.state.meta.errors)}</FieldError>
                ) : null}
              </Field>
            )}
          </form.Field>

          {/* Hạn thanh toán */}
          <form.Field name="dueDate">
            {(field) => (
              <Field>
                <FieldLabel>Hạn thanh toán</FieldLabel>
                <DatePicker
                  value={field.state.value}
                  disabled={mutation.isPending}
                  onChange={field.handleChange}
                />
                <FieldDescription>
                  Hạn chót sinh viên phải hoàn thành thanh toán.
                </FieldDescription>
              </Field>
            )}
          </form.Field>

          {/* Ghi chú */}
          <form.Field name="note">
            {(field) => (
              <Field>
                <FieldLabel>Ghi chú</FieldLabel>
                <Input
                  placeholder="Ghi chú đợt hóa đơn (không bắt buộc)"
                  className="text-xs"
                  value={field.state.value}
                  disabled={mutation.isPending}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
                {firstError(field.state.meta.errors) ? (
                  <FieldError>{firstError(field.state.meta.errors)}</FieldError>
                ) : null}
              </Field>
            )}
          </form.Field>

          <ResponsiveDialogFooter className="pt-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, formSubmitting]) => (
                <Button
                  type="submit"
                  size="sm"
                  disabled={!canSubmit || formSubmitting || mutation.isPending}
                >
                  {mutation.isPending ? "Đang tạo..." : "Tạo hóa đơn"}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

export function InvoicesPage({
  search,
  onSearch,
  canGenerate,
}: {
  search: {
    q: string;
    status?: InvoiceStatus;
    academicYearId?: string;
    registrationPeriodId?: string;
    page: number;
    pageSize: number;
  };
  onSearch: (changes: Partial<typeof search>) => void;
  canGenerate: boolean;
}) {
  const navigate = useNavigate();
  const query = useInvoicesQuery({
    search: search.q.trim() || undefined,
    status: search.status,
    academicYearId: search.academicYearId,
    registrationPeriodId: search.registrationPeriodId,
    page: search.page,
    pageSize: search.pageSize,
  });

  const years = useAcademicYearsQuery({ page: 1, pageSize: 50 });
  const periods = useRegistrationPeriodsQuery({
    page: 1,
    pageSize: 100,
    academicYearId: search.academicYearId,
  });

  const [batchOpen, setBatchOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [isExporting, setIsExporting] = useState(false);

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      await exportInvoicesToExcel({
        studentId: undefined,
        academicYearId: search.academicYearId,
        registrationPeriodId: search.registrationPeriodId,
        status: search.status,
        search: search.q.trim() || undefined,
      });
      toast.success("Xuất file Excel hóa đơn thành công!");
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Không thể xuất file Excel. Vui lòng thử lại sau.",
      );
    } finally {
      setIsExporting(false);
    }
  };

  const deleteMutation = useDeleteInvoice();
  const items = query.data?.items ?? [];
  const [deletingInvoice, setDeletingInvoice] = useState<
    (typeof items)[number] | null
  >(null);

  const academicYearOptions = useMemo(() => {
    const list = years.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả năm học" },
      ...list.map((y) => ({ value: y.id, label: `Năm học ${y.code}` })),
    ];
  }, [years.data]);

  const periodOptions = useMemo(() => {
    const list = periods.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả đợt đăng ký" },
      ...list.map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` })),
    ];
  }, [periods.data]);

  const hasFilters = Boolean(
    search.q ||
      search.academicYearId ||
      search.registrationPeriodId ||
      search.status,
  );

  const resetFilters = () => {
    onSearch({
      q: "",
      academicYearId: undefined,
      registrationPeriodId: undefined,
      status: undefined,
      page: 1,
    });
  };

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

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / TÀI CHÍNH"
        title="Hóa đơn"
        description="Theo dõi hóa đơn, hạn thanh toán và số tiền còn phải thu."
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 text-xs font-semibold"
              disabled={isExporting}
              onClick={() => void handleExportExcel()}
              aria-label="Xuất file Excel danh sách hóa đơn"
            >
              <FileSpreadsheet className="size-3.5" />
              <span>{isExporting ? "Đang xuất..." : "Xuất Excel"}</span>
            </Button>
            {canGenerate && (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setBatchOpen(true)}
              >
                <Plus className="size-3.5" />
                <span>Tạo theo đợt</span>
              </Button>
            )}
          </div>
        }
      />

      {/* 2. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="w-full lg:w-80">
          <DebouncedSearchInput
            className="text-xs"
            value={search.q}
            placeholder="Tìm theo mã hoặc tên sinh viên..."
            aria-label="Tìm hóa đơn"
            onChange={(val) => onSearch({ q: val, page: 1 })}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          {/* Năm học (50% on mobile) */}
          <Combobox
            className="w-full sm:w-44 text-xs"
            options={academicYearOptions}
            value={search.academicYearId ?? "all"}
            searchPlaceholder="Tìm năm học..."
            onValueChange={(value) =>
              onSearch({
                academicYearId: value === "all" ? undefined : value,
                registrationPeriodId: undefined,
                page: 1,
              })
            }
          />

          {/* Đợt đăng ký (Full width on mobile to avoid truncation) */}
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-56 text-xs"
            options={periodOptions}
            value={search.registrationPeriodId ?? "all"}
            searchPlaceholder="Tìm đợt đăng ký..."
            onValueChange={(value) =>
              onSearch({
                registrationPeriodId: value === "all" ? undefined : value,
                page: 1,
              })
            }
          />

          {/* Trạng thái (50% on mobile / inline on desktop) */}
          <Select
            value={search.status ?? "all"}
            onValueChange={(value) =>
              onSearch({
                status: value === "all" ? undefined : (value as InvoiceStatus),
                page: 1,
              })
            }
          >
            <SelectTrigger className="w-full col-span-2 sm:col-span-1 sm:w-44 text-xs">
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              {Object.entries(invoiceStatusLabels).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
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
                    aria-label="Chọn tất cả hóa đơn"
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
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[130px]">
                Mã hóa đơn
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[200px]">
                Sinh viên
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[180px]">
                Đợt đăng ký
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[130px] text-right">
                Tổng tiền
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[130px] text-right">
                Còn nợ
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[160px]">
                Trạng thái
              </TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {query.isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="py-12 text-center text-xs text-muted-foreground"
                >
                  Đang tải danh sách hóa đơn...
                </TableCell>
              </TableRow>
            ) : query.isError ? (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="py-12 text-center text-xs text-destructive"
                >
                  {query.error instanceof Error
                    ? query.error.message
                    : "Không thể tải danh sách hóa đơn."}
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="p-8">
                  <EmptyState
                    icon={ReceiptText}
                    title="Không có hóa đơn nào"
                    description={
                      hasFilters
                        ? "Không tìm thấy hóa đơn nào phù hợp với bộ lọc hiện tại."
                        : "Chưa có hóa đơn nào trong hệ thống. Hóa đơn sẽ xuất hiện sau khi phát sinh lượt cư trú hoặc tạo theo đợt."
                    }
                    action={
                      hasFilters
                        ? {
                            label: "Xóa bộ lọc",
                            onClick: resetFilters,
                          }
                        : canGenerate
                          ? {
                              label: "Tạo hóa đơn theo đợt",
                              onClick: () => setBatchOpen(true),
                            }
                          : undefined
                    }
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((invoice) => (
                <TableRow
                  key={invoice.id}
                  className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                  onClick={() =>
                    void navigate({
                      to: "/invoices/$invoiceId",
                      params: { invoiceId: invoice.id },
                    })
                  }
                >
                  <TableCell
                    className="pl-3"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <div className="flex items-center pl-1">
                      <Checkbox
                        aria-label={`Chọn hóa đơn ${invoice.invoiceCode}`}
                        checked={selectedIds.has(invoice.id)}
                        onCheckedChange={(val) =>
                          toggleSelect(invoice.id, Boolean(val))
                        }
                      />
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-mono font-semibold text-foreground text-sm">
                      {invoice.invoiceCode}
                    </div>
                    <div className="type-supporting text-[11px] text-muted-foreground">
                      {formatDateValue(invoice.issuedAt) || "—"}
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-semibold text-foreground text-sm">
                      {invoice.studentName}
                    </div>
                    <div className="type-supporting text-muted-foreground font-mono text-xs">
                      {invoice.studentCode}
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-medium text-foreground text-sm">
                      {invoice.registrationPeriodName ?? "—"}
                    </div>
                    <div className="type-supporting text-muted-foreground font-mono text-xs">
                      {invoice.registrationPeriodCode ?? "Chưa gắn đợt"}
                    </div>
                  </TableCell>

                  <TableCell className="text-right">
                    <span className="font-bold font-mono tabular-nums text-foreground text-sm">
                      {money(invoice.totalAmount)}
                    </span>
                  </TableCell>

                  <TableCell className="text-right">
                    <span
                      className={cn(
                        "font-bold font-mono tabular-nums text-sm",
                        invoice.remainingAmount > 0
                          ? "text-destructive"
                          : "text-muted-foreground",
                      )}
                    >
                      {money(invoice.remainingAmount)}
                    </span>
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant={invoiceStatusVariants[invoice.status]}
                      className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
                    >
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          invoice.status === "paid" && "bg-emerald-500",
                          invoice.status === "partial" && "bg-amber-500",
                          invoice.status === "unpaid" && "bg-red-500",
                          invoice.status === "cancelled" &&
                            "bg-muted-foreground/60",
                        )}
                      />
                      {invoiceStatusLabels[invoice.status]}
                    </Badge>
                  </TableCell>

                  <TableCell onClick={(event) => event.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="size-8 text-muted-foreground hover:text-foreground"
                          aria-label={`Thao tác với hóa đơn ${invoice.invoiceCode}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            void navigate({
                              to: "/invoices/$invoiceId",
                              params: { invoiceId: invoice.id },
                            });
                          }}
                        >
                          <Eye className="size-4 mr-2 text-muted-foreground" />
                          Xem chi tiết
                        </DropdownMenuItem>
                        {(invoice.status === "unpaid" ||
                          invoice.status === "cancelled") && (
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeletingInvoice(invoice);
                            }}
                          >
                            <Trash2 className="size-4 mr-2" />
                            Xóa hóa đơn
                          </DropdownMenuItem>
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
      <DataTablePagination
        page={search.page}
        pageSize={search.pageSize}
        pageCount={Math.max(1, query.data?.totalPages ?? 1)}
        total={query.data?.total ?? 0}
        onPageChange={(page) => onSearch({ page })}
        onPageSizeChange={(pageSize) => onSearch({ pageSize, page: 1 })}
      />

      {/* 5. Bulk Actions Floating Bar */}
      <DataTableBulkActions
        selectedCount={selectedIds.size}
        selectedLabel="hóa đơn"
        onClear={() => setSelectedIds(new Set())}
      />

      {/* 6. Batch Dialog */}
      {canGenerate ? (
        <BatchDialog open={batchOpen} onOpenChange={setBatchOpen} />
      ) : null}

      <ConfirmDialog
        open={Boolean(deletingInvoice)}
        onOpenChange={(open) => {
          if (!open && !deleteMutation.isPending) setDeletingInvoice(null);
        }}
        title="Xóa hóa đơn?"
        description={
          deletingInvoice
            ? `Bạn có chắc chắn muốn xóa hóa đơn ${deletingInvoice.invoiceCode} của sinh viên ${deletingInvoice.studentName}? Toàn bộ các dòng chi tiết sẽ bị xóa.`
            : ""
        }
        confirmLabel="Xóa hóa đơn"
        isLoading={deleteMutation.isPending}
        onConfirm={() => {
          if (!deletingInvoice) return;
          deleteMutation
            .mutateAsync({ id: deletingInvoice.id })
            .then(() => {
              toast.success("Đã xóa hóa đơn thành công.");
              setDeletingInvoice(null);
            })
            .catch((err: unknown) => {
              toast.error(
                err instanceof Error ? err.message : "Không thể xóa hóa đơn.",
              );
            });
        }}
      />
    </div>
  );
}

export { money };
