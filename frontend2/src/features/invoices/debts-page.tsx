import { useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  FileSpreadsheet,
  MoreHorizontal,
  ReceiptText,
  RotateCcw,
  User,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Combobox } from "@/components/admin/combobox";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAcademicYearsQuery } from "@/features/academic-years/api";
import { exportDebtsToExcel, useDebtListQuery } from "@/features/invoices/api";
import { money } from "@/features/invoices/invoices-page";
import { useRbac } from "@/rbac/context";

export function DebtsPage({
  search,
  onSearch,
}: {
  search: { q: string; academicYearId?: string; roomId?: string };
  onSearch: (changes: Partial<typeof search>) => void;
}) {
  const navigate = useNavigate();
  const { can } = useRbac();
  const years = useAcademicYearsQuery({ page: 1, pageSize: 50 });
  const query = useDebtListQuery({
    search: search.q.trim() || undefined,
    academicYearId: search.academicYearId,
    roomId: search.roomId,
  });

  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isExporting, setIsExporting] = useState(false);

  const items = query.data ?? [];

  // Summary Metrics
  const summary = useMemo(() => {
    const totalStudents = items.length;
    const totalInvoices = items.reduce(
      (sum, item) => sum + item.invoiceCount,
      0,
    );
    const totalDebtAmount = items.reduce(
      (sum, item) => sum + item.totalDebt,
      0,
    );
    return { totalStudents, totalInvoices, totalDebtAmount };
  }, [items]);

  // Options for academic year
  const academicYearOptions = useMemo(() => {
    const list = years.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả năm học" },
      ...list.map((y) => ({ value: y.id, label: `Năm học ${y.code}` })),
    ];
  }, [years.data]);

  const roomOptions = useMemo(() => {
    const rooms = new Map<string, string>();
    for (const debt of items) {
      if (!debt.roomId) continue;
      const label = debt.roomCode
        ? `${debt.roomCode}${debt.roomName ? ` · ${debt.roomName}` : ""}`
        : (debt.roomName ?? debt.roomId);
      rooms.set(debt.roomId, label);
    }
    return [
      { value: "all", label: "Tất cả phòng" },
      ...Array.from(rooms, ([value, label]) => ({ value, label })).sort(
        (left, right) => left.label.localeCompare(right.label, "vi"),
      ),
    ];
  }, [items]);

  const hasFilters = Boolean(
    search.q || search.academicYearId || search.roomId,
  );

  const resetFilters = () => {
    onSearch({
      q: "",
      academicYearId: undefined,
      roomId: undefined,
    });
    setPage(1);
  };

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      await exportDebtsToExcel({
        academicYearId: search.academicYearId,
        roomId: search.roomId,
        search: search.q.trim() || undefined,
      });
      toast.success("Xuất file Excel công nợ thành công!");
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Không thể xuất file Excel. Vui lòng thử lại sau.",
      );
    } finally {
      setIsExporting(false);
    }
  };

  // Client-side pagination
  const paginatedItems = useMemo(() => {
    const start = (page - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, page, pageSize]);

  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));

  // Selection
  const allSelected =
    paginatedItems.length > 0 &&
    paginatedItems.every((item) => selectedIds.has(item.studentId));
  const someSelected =
    paginatedItems.some((item) => selectedIds.has(item.studentId)) &&
    !allSelected;

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        paginatedItems.forEach((item) => {
          next.add(item.studentId);
        });
        return next;
      });
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        paginatedItems.forEach((item) => {
          next.delete(item.studentId);
        });
        return next;
      });
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
        title="Công nợ"
        description="Tổng hợp các khoản nợ tiền phòng KTX chưa thanh toán theo từng sinh viên."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              disabled={isExporting || query.isLoading}
              onClick={() => void handleExportExcel()}
              aria-label="Xuất file Excel danh sách công nợ"
            >
              <FileSpreadsheet className="size-3.5" />
              <span>{isExporting ? "Đang xuất..." : "Xuất Excel"}</span>
            </Button>
            {can("ktx.invoices.view") ? (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() =>
                  void navigate({
                    to: "/invoices",
                    search: { q: "", page: 1, pageSize: 10 },
                  })
                }
              >
                <ReceiptText className="size-3.5" />
                <span>Quản lý hóa đơn</span>
              </Button>
            ) : null}
          </div>
        }
      />

      {/* 2. KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Users}
            label="Sinh viên còn nợ"
            value={summary.totalStudents.toLocaleString("vi-VN")}
            helper="Tổng số sinh viên có khoản nợ chưa thu"
          />
          <KpiMetric
            icon={ReceiptText}
            label="Hóa đơn chưa thanh toán"
            value={summary.totalInvoices.toLocaleString("vi-VN")}
            helper="Tổng số hóa đơn còn nợ đọng"
          />
          <KpiMetric
            icon={AlertCircle}
            label="Tổng tiền công nợ"
            value={money(summary.totalDebtAmount)}
            trend="negative"
            helper="Tổng số tiền KTX cần thu hồi"
          />
        </CardContent>
      </Card>

      {/* 3. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="w-full lg:w-80">
          <DebouncedSearchInput
            className="text-xs"
            value={search.q}
            placeholder="Tìm theo mã hoặc tên sinh viên..."
            aria-label="Tìm công nợ"
            onChange={(val) => {
              onSearch({ q: val });
              setPage(1);
            }}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          {/* Năm học */}
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-56 text-xs"
            options={academicYearOptions}
            value={search.academicYearId ?? "all"}
            searchPlaceholder="Tìm năm học..."
            onValueChange={(value) => {
              onSearch({
                academicYearId: value === "all" ? undefined : value,
              });
              setPage(1);
            }}
          />

          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-64 text-xs"
            options={roomOptions}
            value={search.roomId ?? "all"}
            searchPlaceholder="Tìm phòng..."
            onValueChange={(value) => {
              onSearch({ roomId: value === "all" ? undefined : value });
              setPage(1);
            }}
          />

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

      {/* 4. Data Table */}
      <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40">
              <TableHead className="w-10 pl-3">
                <div className="flex items-center pl-1">
                  <Checkbox
                    aria-label="Chọn tất cả sinh viên"
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
                Sinh viên
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[180px]">
                Khoa / Viện
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[180px]">
                Phòng đã chọn
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[140px] text-center">
                Số hóa đơn nợ
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[160px] text-right">
                Tổng công nợ
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
                  Đang tải danh sách công nợ...
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
                    : "Không thể tải danh sách công nợ."}
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="p-8">
                  <EmptyState
                    icon={ReceiptText}
                    title="Không có công nợ nào"
                    description={
                      hasFilters
                        ? "Không tìm thấy sinh viên có công nợ phù hợp với bộ lọc hiện tại."
                        : "Tuyệt vời! Hiện tại không có sinh viên nào có khoản nợ tiền phòng KTX chưa thanh toán."
                    }
                    action={
                      hasFilters
                        ? {
                            label: "Xóa bộ lọc",
                            onClick: resetFilters,
                          }
                        : undefined
                    }
                  />
                </TableCell>
              </TableRow>
            ) : (
              paginatedItems.map((debt) => (
                <TableRow
                  key={debt.studentId}
                  className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                  onClick={() =>
                    void navigate({
                      to: "/invoices",
                      search: { q: debt.studentCode, page: 1, pageSize: 10 },
                    })
                  }
                >
                  <TableCell
                    className="pl-3"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <div className="flex items-center pl-1">
                      <Checkbox
                        aria-label={`Chọn sinh viên ${debt.studentName}`}
                        checked={selectedIds.has(debt.studentId)}
                        onCheckedChange={(val) =>
                          toggleSelect(debt.studentId, Boolean(val))
                        }
                      />
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-semibold text-foreground text-sm">
                      {debt.studentName}
                    </div>
                    <div className="type-supporting text-muted-foreground font-mono text-xs">
                      {debt.studentCode}
                    </div>
                  </TableCell>

                  <TableCell>
                    <span className="text-foreground text-sm">
                      {debt.faculty || "—"}
                    </span>
                  </TableCell>

                  <TableCell>
                    {debt.roomCode ? (
                      <>
                        <div className="font-semibold text-foreground text-sm">
                          {debt.roomCode}
                        </div>
                        <div className="type-supporting text-muted-foreground text-xs">
                          {[debt.buildingCode, debt.roomName]
                            .filter(Boolean)
                            .join(" · ") || "—"}
                        </div>
                      </>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </TableCell>

                  <TableCell className="text-center">
                    <Badge
                      variant="outline"
                      className="font-semibold text-xs px-2 py-0.5"
                    >
                      {debt.invoiceCount} hóa đơn
                    </Badge>
                  </TableCell>

                  <TableCell className="text-right">
                    <span className="font-bold font-mono text-destructive tabular-nums text-sm">
                      {money(debt.totalDebt)}
                    </span>
                  </TableCell>

                  <TableCell onClick={(event) => event.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="size-8 text-muted-foreground hover:text-foreground"
                          aria-label={`Thao tác với sinh viên ${debt.studentName}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-52">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            void navigate({
                              to: "/invoices",
                              search: {
                                q: debt.studentCode,
                                page: 1,
                                pageSize: 10,
                              },
                            });
                          }}
                        >
                          <ReceiptText className="size-4 mr-2 text-muted-foreground" />
                          Xem hóa đơn nợ
                        </DropdownMenuItem>

                        {debt.studentId && (
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              void navigate({
                                to: "/students/$studentId",
                                params: { studentId: debt.studentId },
                              });
                            }}
                          >
                            <User className="size-4 mr-2 text-muted-foreground" />
                            Xem hồ sơ sinh viên
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

      {/* 5. Pagination */}
      {items.length > 0 && (
        <DataTablePagination
          page={page}
          pageSize={pageSize}
          pageCount={totalPages}
          total={items.length}
          onPageChange={setPage}
          onPageSizeChange={(newSize) => {
            setPageSize(newSize);
            setPage(1);
          }}
        />
      )}

      {/* 6. Bulk Actions Floating Bar */}
      <DataTableBulkActions
        selectedCount={selectedIds.size}
        selectedLabel="sinh viên"
        onClear={() => setSelectedIds(new Set())}
      />
    </div>
  );
}
