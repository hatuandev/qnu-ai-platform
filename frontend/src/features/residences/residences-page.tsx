import { useNavigate } from "@tanstack/react-router";
import {
  Calendar,
  DoorOpen,
  Eye,
  FileSpreadsheet,
  FileText,
  Home,
  LogOut,
  MoreHorizontal,
  ReceiptText,
  RefreshCw,
  RotateCcw,
  Users,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/app/api/client";
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
import { useBuildingsQuery } from "@/features/buildings/api";
import { useFloorsQuery } from "@/features/floors/api";
import { useRegistrationPeriodsQuery } from "@/features/registration-periods/api";
import { useResidencesQuery } from "@/features/residences/api";
import type {
  Residence,
  ResidenceStatus,
  ResidencesPage as ResidencesPageData,
} from "@/features/residences/types";
import { useRoomsQuery } from "@/features/rooms/api";
import { formatDateValue } from "@/lib/date-utils";
import { type ExcelColumn, exportToExcel } from "@/lib/excel-export";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const statusLabels: Record<ResidenceStatus, string> = {
  active: "Đang cư trú",
  extended: "Đã gia hạn",
  checked_out: "Đã trả phòng",
  cancelled: "Đã thu hồi",
};

const statusDotColors: Record<ResidenceStatus, string> = {
  active: "bg-emerald-500",
  extended: "bg-blue-500",
  checked_out: "bg-muted-foreground/60",
  cancelled: "bg-red-500",
};

const statusVariants: Record<
  ResidenceStatus,
  "success" | "info" | "secondary" | "destructive"
> = {
  active: "success",
  extended: "info",
  checked_out: "secondary",
  cancelled: "destructive",
};

const statusOptions: Array<{ value: string; label: string }> = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "active", label: "Đang cư trú" },
  { value: "extended", label: "Đã gia hạn" },
  { value: "checked_out", label: "Đã trả phòng" },
  { value: "cancelled", label: "Đã thu hồi" },
];

const genderLabels: Record<string, string> = {
  male: "Nam",
  female: "Nữ",
  other: "Khác",
  nam: "Nam",
  nu: "Nữ",
  nữ: "Nữ",
};

const residenceExcelColumns: ExcelColumn<Residence>[] = [
  { header: "STT", accessor: (_item, index) => (index ?? 0) + 1, width: 6 },
  { header: "Mã sinh viên", accessor: (r) => r.studentCode, width: 14 },
  { header: "Họ và tên", accessor: (r) => r.studentName, width: 24 },
  {
    header: "Giới tính",
    accessor: (r) =>
      r.gender ? (genderLabels[r.gender.toLowerCase()] ?? r.gender) : "—",
    width: 10,
  },
  {
    header: "Số điện thoại",
    accessor: (r) => r.phoneNumber ?? "—",
    width: 16,
  },
  { header: "Khoa", accessor: (r) => r.faculty ?? "—", width: 20 },
  { header: "Lớp", accessor: (r) => r.className ?? "—", width: 14 },
  {
    header: "Tòa nhà",
    accessor: (r) => r.buildingName || r.buildingCode || "—",
    width: 16,
  },
  {
    header: "Số tầng",
    accessor: (r) =>
      r.floorNumber != null ? `Tầng ${r.floorNumber}` : (r.floorName ?? "—"),
    width: 12,
  },
  {
    header: "Số phòng",
    accessor: (r) => r.roomName || r.roomCode || "—",
    width: 14,
  },
  {
    header: "Đợt đăng ký",
    accessor: (r) => r.registrationPeriodName ?? "—",
    width: 20,
  },
  {
    header: "Năm học",
    accessor: (r) => r.academicYearName ?? "—",
    width: 16,
  },
  {
    header: "Ngày bắt đầu",
    accessor: (r) => (r.startDate ? formatDateValue(r.startDate) : "—"),
    width: 16,
  },
  {
    header: "Hạn dự kiến",
    accessor: (r) =>
      r.expectedEndDate ? formatDateValue(r.expectedEndDate) : "—",
    width: 16,
  },
  {
    header: "Ngày kết thúc",
    accessor: (r) => (r.actualEndDate ? formatDateValue(r.actualEndDate) : "—"),
    width: 16,
  },
  {
    header: "Ngày nhận phòng",
    accessor: (r) => (r.checkInAt ? formatDateValue(r.checkInAt) : "—"),
    width: 18,
  },
  {
    header: "Trạng thái",
    accessor: (r) => statusLabels[r.status] ?? r.status,
    width: 16,
  },
];

export function ResidencesPage({
  search,
  onSearch,
}: {
  search: {
    q: string;
    status?: ResidenceStatus;
    buildingId?: string;
    floorId?: string;
    roomId?: string;
    registrationPeriodId?: string;
    academicYearId?: string;
    page: number;
    pageSize: number;
  };
  onSearch: (changes: Partial<typeof search>) => void;
}) {
  const navigate = useNavigate();
  const { can } = useRbac();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [isExporting, setIsExporting] = useState(false);

  // Load danh sách Tòa nhà cho dropdown lọc
  const buildingsQuery = useBuildingsQuery({
    page: 1,
    pageSize: 100,
    status: "active",
  });

  // Load danh sách Tầng & Phòng cho dropdown lọc
  const floorsQuery = useFloorsQuery(search.buildingId);
  const roomsQuery = useRoomsQuery({
    buildingId: search.buildingId,
    floorId: search.floorId,
    page: 1,
    pageSize: 200,
  });

  // Load danh sách Đợt đăng ký cho dropdown lọc
  const periodsQuery = useRegistrationPeriodsQuery({
    page: 1,
    pageSize: 50,
  });

  const query = useResidencesQuery({
    search: search.q.trim() || undefined,
    status: search.status,
    buildingId: search.buildingId,
    floorId: search.floorId,
    roomId: search.roomId,
    registrationPeriodId: search.registrationPeriodId,
    academicYearId: search.academicYearId,
    page: search.page,
    pageSize: search.pageSize,
  });

  const items = query.data?.items ?? [];

  // Summary Metrics
  const summary = useMemo(() => {
    const total = query.data?.total ?? items.length;
    const active = items.filter(
      (i) => i.status === "active" || i.status === "extended",
    ).length;
    const checkedOut = items.filter((i) => i.status === "checked_out").length;
    const cancelled = items.filter((i) => i.status === "cancelled").length;
    return { total, active, checkedOut, cancelled };
  }, [items, query.data?.total]);

  const buildingOptions = useMemo(() => {
    const list = buildingsQuery.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả tòa nhà" },
      ...list.map((b) => ({ value: b.id, label: `${b.code} · ${b.name}` })),
    ];
  }, [buildingsQuery.data?.items]);

  const floorOptions = useMemo(() => {
    const list = floorsQuery.data ?? [];
    return [
      { value: "all", label: "Tất cả tầng" },
      ...list.map((f) => ({
        value: f.id,
        label: `Tầng ${f.floorNumber} · ${f.name}`,
      })),
    ];
  }, [floorsQuery.data]);

  const roomOptions = useMemo(() => {
    const list = roomsQuery.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả phòng" },
      ...list.map((r) => ({
        value: r.id,
        label: `${r.code} · ${r.name}`,
      })),
    ];
  }, [roomsQuery.data?.items]);

  const periodOptions = useMemo(() => {
    const list = periodsQuery.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả đợt đăng ký" },
      ...list.map((p) => ({ value: p.id, label: p.name })),
    ];
  }, [periodsQuery.data?.items]);

  const handleExportExcel = async () => {
    try {
      setIsExporting(true);
      const res = await apiClient.get<ResidencesPageData>("/Residences", {
        searchParams: {
          BuildingId: search.buildingId,
          FloorId: search.floorId,
          RoomId: search.roomId,
          RegistrationPeriodId: search.registrationPeriodId,
          AcademicYearId: search.academicYearId,
          Status: search.status,
          SearchStudentCodeOrName: search.q.trim() || undefined,
          PageIndex: 1,
          PageSize: 5000,
        },
      });
      const data = res?.items ?? [];
      const dateSlug = new Date().toISOString().slice(0, 10);
      await exportToExcel({
        filename: `danh_sach_cu_tru_${dateSlug}.xlsx`,
        sheetName: "Cư trú KTX",
        data,
        columns: residenceExcelColumns,
      });
      toast.success(`Đã xuất Excel thành công (${data.length} hồ sơ cư trú).`);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Có lỗi khi xuất file Excel.",
      );
    } finally {
      setIsExporting(false);
    }
  };

  const hasFilters = Boolean(
    search.q ||
      search.status ||
      search.buildingId ||
      search.floorId ||
      search.roomId ||
      search.registrationPeriodId ||
      search.academicYearId,
  );

  const resetFilters = () => {
    onSearch({
      q: "",
      status: undefined,
      buildingId: undefined,
      floorId: undefined,
      roomId: undefined,
      registrationPeriodId: undefined,
      academicYearId: undefined,
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
        eyebrow="KÝ TÚC XÁ / VẬN HÀNH"
        title="Quản lý cư trú"
        description="Theo dõi sinh viên đang ở thực tế, hiện trạng phòng, đợt đăng ký, chuyển phòng và trả phòng."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              disabled={isExporting}
              onClick={() => void handleExportExcel()}
            >
              <FileSpreadsheet
                className={cn(
                  "size-3.5 text-emerald-600",
                  isExporting && "animate-spin",
                )}
              />
              <span>
                {isExporting ? "Đang xuất Excel..." : "Xuất file Excel"}
              </span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw
                className={cn("size-3.5", query.isFetching && "animate-spin")}
              />
              <span>Làm mới</span>
            </Button>
            {can("ktx.residence_contracts.view") && (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() =>
                  void navigate({
                    to: "/residence-contracts",
                    search: { q: "", page: 1, pageSize: 10 },
                  })
                }
              >
                <FileText className="size-3.5" />
                <span>Hợp đồng cư trú</span>
              </Button>
            )}
          </div>
        }
      />

      {/* 2. KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Home}
            label="Đang cư trú"
            value={summary.active.toLocaleString("vi-VN")}
            trend="positive"
            helper="Sinh viên đang ở thực tế"
          />
          <KpiMetric
            icon={Users}
            label="Tổng lượt cư trú"
            value={summary.total.toLocaleString("vi-VN")}
            helper="Tổng hồ sơ cư trú đã lưu trữ"
          />
          <KpiMetric
            icon={LogOut}
            label="Đã trả phòng"
            value={summary.checkedOut.toLocaleString("vi-VN")}
            helper="Lượt sinh viên đã làm thủ tục trả phòng"
          />
          <KpiMetric
            icon={XCircle}
            label="Đã thu hồi / Hủy"
            value={summary.cancelled.toLocaleString("vi-VN")}
            trend={summary.cancelled > 0 ? "negative" : "neutral"}
            helper="Chỗ ở bị chấm dứt hoặc thu hồi"
          />
        </CardContent>
      </Card>

      {/* 3. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="w-full lg:w-80">
          <DebouncedSearchInput
            className="text-xs"
            value={search.q}
            placeholder="Tìm theo tên SV, MSSV, phòng, tòa..."
            aria-label="Tìm cư trú"
            onChange={(val) => onSearch({ q: val, page: 1 })}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:flex lg:flex-wrap lg:items-center gap-2 w-full lg:w-auto">
          {/* Lọc Tòa nhà */}
          <Combobox
            className="w-full sm:w-44 text-xs"
            options={buildingOptions}
            value={search.buildingId ?? "all"}
            searchPlaceholder="Tìm tòa nhà..."
            onValueChange={(value) =>
              onSearch({
                buildingId: value === "all" ? undefined : value,
                floorId: undefined,
                roomId: undefined,
                page: 1,
              })
            }
          />

          {/* Lọc Tầng */}
          <Combobox
            className="w-full sm:w-36 text-xs"
            options={floorOptions}
            value={search.floorId ?? "all"}
            searchPlaceholder="Tìm tầng..."
            disabled={!search.buildingId}
            onValueChange={(value) =>
              onSearch({
                floorId: value === "all" ? undefined : value,
                roomId: undefined,
                page: 1,
              })
            }
          />

          {/* Lọc Phòng */}
          <Combobox
            className="w-full sm:w-36 text-xs"
            options={roomOptions}
            value={search.roomId ?? "all"}
            searchPlaceholder="Tìm phòng..."
            disabled={!search.buildingId}
            onValueChange={(value) =>
              onSearch({
                roomId: value === "all" ? undefined : value,
                page: 1,
              })
            }
          />

          {/* Lọc Đợt đăng ký */}
          <Combobox
            className="w-full sm:w-56 text-xs"
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

          {/* Lọc Trạng thái */}
          <Combobox
            className="w-full sm:w-40 text-xs"
            options={statusOptions}
            value={search.status ?? "all"}
            searchPlaceholder="Tìm trạng thái..."
            onValueChange={(value) =>
              onSearch({
                status:
                  value === "all" ? undefined : (value as ResidenceStatus),
                page: 1,
              })
            }
          />

          {hasFilters && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground col-span-full sm:col-span-1"
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
                    aria-label="Chọn tất cả cư trú"
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
                Sinh viên & MSSV
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[200px]">
                Tòa / Tầng / Phòng
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[170px]">
                Hiện trạng phòng (Sĩ số)
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[200px]">
                Đợt đăng ký & Thời hạn
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[140px]">
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
                  <div className="flex items-center justify-center gap-2">
                    <RefreshCw className="size-4 animate-spin" />
                    <span>Đang tải danh sách cư trú...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : query.isError ? (
              <TableRow>
                <TableCell colSpan={7} className="p-8">
                  <EmptyState
                    icon={Home}
                    title="Không thể tải danh sách cư trú"
                    description="Kiểm tra kết nối mạng hoặc thử tải lại sau ít phút."
                    action={{
                      label: "Thử lại",
                      onClick: () => void query.refetch(),
                    }}
                  />
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="p-8">
                  <EmptyState
                    icon={Home}
                    title={
                      hasFilters
                        ? "Không có cư trú phù hợp"
                        : "Chưa có lượt cư trú nào"
                    }
                    description={
                      hasFilters
                        ? "Không tìm thấy hồ sơ cư trú nào phù hợp với bộ lọc hiện tại."
                        : "Danh sách cư trú sẽ xuất hiện sau khi sinh viên hoàn tất thủ tục nhận phòng (Check-in)."
                    }
                    action={
                      hasFilters
                        ? { label: "Xóa bộ lọc", onClick: resetFilters }
                        : undefined
                    }
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((residence) => {
                const capacity =
                  residence.roomOperationalCapacity ||
                  residence.roomCapacity ||
                  8;
                const occupants = residence.roomOccupantsCount || 1;
                const available = Math.max(0, capacity - occupants);
                const isFull = occupants >= capacity;

                return (
                  <TableRow
                    key={residence.id}
                    className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                    onClick={() =>
                      void navigate({
                        to: "/residences/$residenceId",
                        params: { residenceId: residence.id },
                      })
                    }
                  >
                    <TableCell
                      className="pl-3"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className="flex items-center pl-1">
                        <Checkbox
                          aria-label={`Chọn cư trú của sinh viên ${residence.studentName}`}
                          checked={selectedIds.has(residence.id)}
                          onCheckedChange={(val) =>
                            toggleSelect(residence.id, Boolean(val))
                          }
                        />
                      </div>
                    </TableCell>

                    {/* Cột Sinh viên & MSSV */}
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-xs">
                          {residence.studentName.charAt(0)}
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-foreground text-sm flex items-center gap-1.5">
                            {residence.studentName}
                          </div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <Badge
                              variant="outline"
                              className="font-mono text-[11px] px-1.5 py-0 bg-muted/40 font-semibold"
                            >
                              {residence.studentCode}
                            </Badge>
                            {residence.phoneNumber && (
                              <span className="text-[11px] text-muted-foreground font-mono">
                                • {residence.phoneNumber}
                              </span>
                            )}
                            {residence.faculty && (
                              <span
                                className="text-[11px] text-muted-foreground truncate max-w-[130px]"
                                title={residence.faculty}
                              >
                                • {residence.faculty}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </TableCell>

                    {/* Cột Tòa / Tầng / Phòng */}
                    <TableCell>
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5">
                          <Badge
                            variant="secondary"
                            className="font-mono font-bold text-xs px-2 py-0.5 bg-primary/10 text-primary border-primary/20"
                          >
                            <DoorOpen className="size-3 mr-1" />
                            Phòng {residence.roomCode}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <span className="font-medium text-foreground">
                            {residence.buildingName}
                          </span>
                          {residence.floorNumber != null && (
                            <span className="text-[11px] bg-muted px-1.5 py-0.2 rounded">
                              Tầng {residence.floorNumber}
                            </span>
                          )}
                        </div>
                      </div>
                    </TableCell>

                    {/* Cột Hiện trạng phòng (Sĩ số) */}
                    <TableCell>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-xs text-foreground">
                            {occupants}/{capacity} chỗ
                          </span>
                          {isFull ? (
                            <Badge
                              variant="secondary"
                              className="text-[10px] px-1.5 py-0 bg-muted text-muted-foreground"
                            >
                              Đã đầy
                            </Badge>
                          ) : (
                            <Badge
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 text-emerald-600 border-emerald-300 bg-emerald-50"
                            >
                              Còn {available} chỗ
                            </Badge>
                          )}
                        </div>
                        {/* Mini progress bar */}
                        <div className="h-1.5 w-28 bg-muted rounded-full overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full transition-all",
                              isFull
                                ? "bg-amber-500"
                                : occupants / capacity > 0.7
                                  ? "bg-blue-500"
                                  : "bg-emerald-500",
                            )}
                            style={{
                              width: `${Math.min(100, (occupants / capacity) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    </TableCell>

                    {/* Cột Đợt đăng ký & Thời hạn */}
                    <TableCell>
                      <div className="space-y-0.5">
                        <div
                          className="text-xs font-medium text-foreground truncate max-w-[200px]"
                          title={
                            residence.registrationPeriodName ??
                            residence.academicYearName ??
                            "—"
                          }
                        >
                          {residence.registrationPeriodName ??
                            residence.academicYearName ??
                            "Nội trú theo kỳ"}
                        </div>
                        <div className="flex items-center gap-1 text-[11px] text-muted-foreground font-mono">
                          <Calendar className="size-3" />
                          <span>{formatDateValue(residence.startDate)}</span>
                          <span>➔</span>
                          <span>
                            {formatDateValue(residence.expectedEndDate) || "—"}
                          </span>
                        </div>
                      </div>
                    </TableCell>

                    {/* Cột Trạng thái */}
                    <TableCell>
                      <Badge
                        variant={statusVariants[residence.status]}
                        className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
                      >
                        <span
                          className={cn(
                            "size-1.5 rounded-full",
                            statusDotColors[residence.status],
                          )}
                        />
                        {statusLabels[residence.status]}
                      </Badge>
                    </TableCell>

                    {/* Cột Thao tác */}
                    <TableCell onClick={(event) => event.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="size-8 text-muted-foreground hover:text-foreground"
                            aria-label={`Thao tác với cư trú của ${residence.studentName}`}
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
                                to: "/residences/$residenceId",
                                params: { residenceId: residence.id },
                              });
                            }}
                          >
                            <Eye className="size-4 mr-2 text-muted-foreground" />
                            Xem chi tiết cư trú
                          </DropdownMenuItem>

                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              void navigate({
                                to: "/invoices",
                                search: {
                                  q: residence.studentCode,
                                  page: 1,
                                  pageSize: 10,
                                },
                              });
                            }}
                          >
                            <ReceiptText className="size-4 mr-2 text-muted-foreground" />
                            Xem hóa đơn sinh viên
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 5. Pagination */}
      {query.data ? (
        <DataTablePagination
          page={search.page}
          pageSize={search.pageSize}
          pageCount={Math.max(1, query.data?.totalPages ?? 1)}
          total={query.data.total}
          onPageChange={(page) => onSearch({ page })}
          onPageSizeChange={(pageSize) => onSearch({ pageSize, page: 1 })}
        />
      ) : null}

      {/* 6. Bulk Actions Floating Bar */}
      <DataTableBulkActions
        selectedCount={selectedIds.size}
        selectedLabel="lượt cư trú"
        onClear={() => setSelectedIds(new Set())}
      />
    </div>
  );
}
