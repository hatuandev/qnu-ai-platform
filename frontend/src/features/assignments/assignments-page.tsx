import { useNavigate } from "@tanstack/react-router";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  Check,
  ClipboardCheck,
  Eye,
  FileSpreadsheet,
  MoreHorizontal,
  Power,
  RotateCcw,
  Search,
  UserPlus,
  UserX,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/app/api/client";
import { Combobox } from "@/components/admin/combobox";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  useAssignmentsQuery,
  useAssignmentWorkspaceQuery,
  useFinalizeRoomSelection,
} from "@/features/assignments/api";
import { AssignDialog } from "@/features/assignments/assign-dialog";
import {
  CancelDialog,
  RefundAndCancelDialog,
} from "@/features/assignments/assignment-dialogs";
import {
  AssignmentWorkflowSummary,
  formatAssignmentTime,
} from "@/features/assignments/assignment-workflow-summary";
import type {
  Assignment,
  AssignmentStatus,
  AssignmentsPage as AssignmentsPageData,
  EligibleApplication,
  EligibleApplicationsPage,
} from "@/features/assignments/types";
import { useBuildingsQuery } from "@/features/buildings/api";
import { useFloorsQuery } from "@/features/floors/api";
import { useRegistrationPeriodsQuery } from "@/features/registration-periods/api";
import { useRoomsQuery } from "@/features/rooms/api";
import { formatDateTimeValue } from "@/lib/date-utils";
import {
  type ExcelColumn,
  exportMultiSheetToExcel,
  exportToExcel,
} from "@/lib/excel-export";
import { cn } from "@/lib/utils";

const statusLabels: Record<AssignmentStatus, string> = {
  selected: "Đang giữ chỗ",
  assigned: "Đã xếp",
  checked_in: "Đã nhận phòng",
  cancelled: "Đã hủy",
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

const genderPolicyLabels: Record<string, string> = {
  male: "Phòng Nam",
  female: "Phòng Nữ",
  mixed: "Phòng Hỗn hợp",
  unspecified: "Chưa phân loại",
};

export function AssignmentsPage({
  search,
  onSearch,
  canCreate,
  canFinalize,
  canCancel,
}: {
  search: {
    q: string;
    registrationPeriodId?: string;
    buildingId?: string;
    floorId?: string;
    roomId?: string;
    status?: AssignmentStatus;
    page: number;
    pageSize: number;
  };
  onSearch: (changes: Partial<typeof search>) => void;
  canCreate: boolean;
  canFinalize: boolean;
  canCancel: boolean;
}) {
  const navigate = useNavigate();
  const periods = useRegistrationPeriodsQuery({ page: 1, pageSize: 100 });
  const periodOptions =
    periods.data?.items.filter((period) => period.status !== "archived") ?? [];
  const now = Date.now();
  const defaultPeriod =
    periodOptions.find(
      (period) =>
        period.roomSelectionNotificationSentAt &&
        !period.roomSelectionFinalizedAt &&
        period.roomSelectionStartAt &&
        period.roomSelectionEndAt &&
        new Date(period.roomSelectionStartAt).getTime() <= now &&
        now <= new Date(period.roomSelectionEndAt).getTime(),
    ) ??
    periodOptions.find((period) => period.status === "closed") ??
    periodOptions.find((period) => period.status === "open") ??
    periodOptions[0];
  const selectedPeriodId = search.registrationPeriodId ?? defaultPeriod?.id;
  const workspace = useAssignmentWorkspaceQuery(selectedPeriodId);

  // Load danh sách Tòa nhà, Tầng, Phòng cho bộ lọc
  const buildingsQuery = useBuildingsQuery({
    page: 1,
    pageSize: 100,
    status: "active",
  });
  const floorsQuery = useFloorsQuery(search.buildingId);
  const roomsQuery = useRoomsQuery({
    buildingId: search.buildingId,
    floorId: search.floorId,
    page: 1,
    pageSize: 200,
  });

  const buildingOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả tòa nhà" },
      ...(buildingsQuery.data?.items ?? []).map((b) => ({
        value: b.id,
        label: `${b.code} · ${b.name}`,
      })),
    ],
    [buildingsQuery.data?.items],
  );

  const floorOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả tầng" },
      ...(floorsQuery.data ?? []).map((f) => ({
        value: f.id,
        label: `Tầng ${f.floorNumber} · ${f.name}`,
      })),
    ],
    [floorsQuery.data],
  );

  const roomOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả phòng" },
      ...(roomsQuery.data?.items ?? []).map((r) => ({
        value: r.id,
        label: `${r.code} · ${r.name}`,
      })),
    ],
    [roomsQuery.data?.items],
  );

  const query = useAssignmentsQuery({
    search: search.q.trim() || undefined,
    status: search.status,
    registrationPeriodId: selectedPeriodId,
    buildingId: search.buildingId,
    floorId: search.floorId,
    roomId: search.roomId,
    page: search.page,
    pageSize: search.pageSize,
  });

  const [createOpen, setCreateOpen] = useState(false);
  const [pending, setPending] = useState<Assignment | null>(null);
  const [refundPending, setRefundPending] = useState<Assignment | null>(null);
  const [finalizeOpen, setFinalizeOpen] = useState(false);
  const finalizeSelection = useFinalizeRoomSelection();
  const manualAssignmentAvailable =
    canCreate &&
    (!workspace.data?.roomSelectionNotificationSentAt ||
      workspace.data.selectionWindowEnded ||
      Boolean(workspace.data.roomSelectionFinalizedAt));

  useEffect(() => {
    if (!search.registrationPeriodId && defaultPeriod?.id) {
      onSearch({ registrationPeriodId: defaultPeriod.id, page: 1 });
    }
  }, [defaultPeriod?.id, onSearch, search.registrationPeriodId]);

  const columns = useMemo<ColumnDef<Assignment>[]>(
    () => [
      {
        accessorKey: "applicationCode",
        header: "Mã hồ sơ",
        cell: ({ row }) => (
          <span className="type-supporting font-mono">
            {row.original.applicationCode}
          </span>
        ),
      },
      {
        accessorKey: "studentName",
        header: "Sinh viên",
        cell: ({ row }) => (
          <div>
            <p className="font-medium">{row.original.studentName}</p>
            <p className="text-xs text-muted-foreground">
              {row.original.studentCode}
              {row.original.studentPhone
                ? ` • ${row.original.studentPhone}`
                : ""}
            </p>
          </div>
        ),
      },
      {
        accessorKey: "roomCode",
        header: "Phòng",
        cell: ({ row }) => row.original.roomCode,
      },
      {
        accessorKey: "studentGender",
        header: "Giới tính",
        cell: ({ row }) => (
          <span>{genderLabels[row.original.studentGender ?? ""] ?? "—"}</span>
        ),
      },
      {
        id: "roomLocation",
        header: "Vị trí",
        cell: ({ row }) => (
          <div className="text-sm">
            <p>{row.original.buildingCode ?? "—"}</p>
            <p className="text-xs text-muted-foreground">
              Tầng {row.original.floorNumber ?? "—"}
            </p>
          </div>
        ),
      },
      {
        accessorKey: "assignedAt",
        header: "Thời điểm chọn",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {formatAssignmentTime(row.original.assignedAt)}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Trạng thái",
        cell: ({ row }) => (
          <Badge
            variant={
              row.original.status === "cancelled"
                ? "secondary"
                : row.original.status === "checked_in"
                  ? "success"
                  : "default"
            }
          >
            {statusLabels[row.original.status]}
          </Badge>
        ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                aria-label={`Thao tác ${row.original.studentName}`}
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() =>
                  void navigate({
                    to: "/assignments/$assignmentId",
                    params: { assignmentId: row.original.id },
                  })
                }
              >
                <Eye className="size-3.5" />
                Chi tiết phân phòng
              </DropdownMenuItem>
              {canCancel &&
              (row.original.status === "selected" ||
                row.original.status === "assigned") ? (
                <DropdownMenuItem onSelect={() => setPending(row.original)}>
                  <Power className="size-3.5" />
                  Hủy xếp phòng
                </DropdownMenuItem>
              ) : null}
              {canCancel &&
              (row.original.status === "assigned" ||
                row.original.status === "checked_in") ? (
                <DropdownMenuItem
                  onSelect={() => setRefundPending(row.original)}
                >
                  <RotateCcw className="size-3.5" />
                  Hủy phòng & Hoàn tiền
                </DropdownMenuItem>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        ),
      },
    ],
    [canCancel, navigate],
  );

  const table = useReactTable({
    data: query.data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,
  });

  const [isExporting, setIsExporting] = useState(false);
  const selectedPeriod = periodOptions.find((p) => p.id === selectedPeriodId);
  const periodSlug = (selectedPeriod?.code ?? "dot_dang_ky").toLowerCase();
  const dateSlug = new Date().toISOString().slice(0, 10);

  const assignedColumns = useMemo<ExcelColumn<Assignment>[]>(
    () => [
      { header: "STT", accessor: (_item, index) => (index ?? 0) + 1, width: 6 },
      // 1. Nhóm thông tin sinh viên
      {
        header: "Mã sinh viên",
        accessor: (item) => item.studentCode,
        width: 14,
      },
      { header: "Họ và tên", accessor: (item) => item.studentName, width: 24 },
      {
        header: "Giới tính",
        accessor: (item) => genderLabels[item.studentGender ?? ""] ?? "—",
        width: 10,
      },
      {
        header: "Số điện thoại",
        accessor: (item) => item.studentPhone ?? "—",
        width: 16,
      },
      // 2. Nhóm thông tin phòng chọn
      {
        header: "Tòa nhà",
        accessor: (item) => item.buildingName ?? item.buildingCode ?? "—",
        width: 16,
      },
      {
        header: "Số tầng",
        accessor: (item) =>
          item.floorNumber != null ? `Tầng ${item.floorNumber}` : "—",
        width: 12,
      },
      {
        header: "Số phòng",
        accessor: (item) => item.roomName ?? item.roomCode ?? "—",
        width: 14,
      },
      {
        header: "Loại phòng",
        accessor: (item) => item.roomTypeName ?? "—",
        width: 18,
      },
      {
        header: "Dành cho",
        accessor: (item) =>
          genderPolicyLabels[item.roomGenderPolicy ?? ""] ?? "—",
        width: 14,
      },
      // 3. Nhóm thời gian & trạng thái
      {
        header: "Thời điểm chọn",
        accessor: (item) =>
          item.assignedAt ? formatDateTimeValue(item.assignedAt) : "—",
        width: 20,
      },
      {
        header: "Trạng thái",
        accessor: (item) => statusLabels[item.status] ?? item.status,
        width: 16,
      },
    ],
    [],
  );

  const unassignedColumns = useMemo<ExcelColumn<EligibleApplication>[]>(
    () => [
      { header: "STT", accessor: (_item, index) => (index ?? 0) + 1, width: 6 },
      // 1. Nhóm thông tin sinh viên
      {
        header: "Mã sinh viên",
        accessor: (item) => item.studentCode,
        width: 14,
      },
      { header: "Họ và tên", accessor: (item) => item.studentName, width: 24 },
      {
        header: "Giới tính",
        accessor: (item) => genderLabels[item.gender ?? ""] ?? "—",
        width: 10,
      },
      {
        header: "Số điện thoại",
        accessor: (item) => item.studentPhone ?? "—",
        width: 16,
      },
      { header: "Lớp", accessor: (item) => item.className ?? "—", width: 14 },
      { header: "Khoa", accessor: (item) => item.faculty ?? "—", width: 20 },
      // 2. Nhóm nhu cầu & ưu tiên
      {
        header: "Loại phòng mong muốn",
        accessor: (item) => item.requestedRoomTypeName ?? "—",
        width: 22,
      },
      {
        header: "Đối tượng ưu tiên",
        accessor: (item) => item.priorityObjectName ?? "—",
        width: 22,
      },
      {
        header: "Điểm ưu tiên",
        accessor: (item) => item.priorityScore ?? 0,
        width: 12,
      },
      // 3. Nhóm thời gian & trạng thái
      {
        header: "Thời điểm nộp",
        accessor: (item) =>
          item.submittedAt ? formatDateTimeValue(item.submittedAt) : "—",
        width: 20,
      },
      {
        header: "Trạng thái",
        accessor: () => "Đã duyệt - Chưa chọn phòng",
        width: 24,
      },
    ],
    [],
  );

  const fetchAllAssigned = async () => {
    const res = await apiClient.get<AssignmentsPageData>("/RoomAssignments", {
      searchParams: {
        RegistrationPeriodId: selectedPeriodId,
        BuildingId: search.buildingId,
        FloorId: search.floorId,
        RoomId: search.roomId,
        Status: search.status,
        SearchStudentCodeOrName: search.q.trim() || undefined,
        PageIndex: 1,
        PageSize: 5000,
      },
    });
    return res?.items ?? [];
  };

  const fetchAllUnassigned = async () => {
    const res = await apiClient.get<EligibleApplicationsPage>(
      "/RoomAssignments/eligible",
      {
        searchParams: {
          RegistrationPeriodId: selectedPeriodId,
          PageIndex: 1,
          PageSize: 5000,
        },
      },
    );
    return res?.items ?? [];
  };

  const handleExportAll = async () => {
    if (!selectedPeriodId) {
      toast.error("Vui lòng chọn đợt đăng ký cần xuất dữ liệu.");
      return;
    }
    try {
      setIsExporting(true);
      const [assigned, unassigned] = await Promise.all([
        fetchAllAssigned(),
        fetchAllUnassigned(),
      ]);

      await exportMultiSheetToExcel({
        filename: `danh_sach_chon_phong_${periodSlug}_${dateSlug}.xlsx`,
        sheets: [
          {
            sheetName: "SV Đã Chọn Phòng",
            data: assigned,
            columns: assignedColumns,
          },
          {
            sheetName: "SV Chưa Chọn Phòng",
            data: unassigned,
            columns: unassignedColumns,
          },
        ],
      });
      toast.success(
        `Đã xuất Excel thành công (${assigned.length} đã chọn, ${unassigned.length} chưa chọn).`,
      );
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Có lỗi khi xuất file Excel.",
      );
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportAssigned = async () => {
    if (!selectedPeriodId) {
      toast.error("Vui lòng chọn đợt đăng ký cần xuất dữ liệu.");
      return;
    }
    try {
      setIsExporting(true);
      const assigned = await fetchAllAssigned();
      await exportToExcel({
        filename: `sv_da_chon_phong_${periodSlug}_${dateSlug}.xlsx`,
        sheetName: "SV Đã Chọn Phòng",
        data: assigned,
        columns: assignedColumns,
      });
      toast.success(`Đã xuất ${assigned.length} sinh viên đã chọn phòng.`);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Có lỗi khi xuất file Excel.",
      );
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportUnassigned = async () => {
    if (!selectedPeriodId) {
      toast.error("Vui lòng chọn đợt đăng ký cần xuất dữ liệu.");
      return;
    }
    try {
      setIsExporting(true);
      const unassigned = await fetchAllUnassigned();
      await exportToExcel({
        filename: `sv_chua_chon_phong_${periodSlug}_${dateSlug}.xlsx`,
        sheetName: "SV Chưa Chọn Phòng",
        data: unassigned,
        columns: unassignedColumns,
      });
      toast.success(`Đã xuất ${unassigned.length} sinh viên chưa chọn phòng.`);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Có lỗi khi xuất file Excel.",
      );
    } finally {
      setIsExporting(false);
    }
  };

  const finalize = () => {
    if (!selectedPeriodId) return;
    finalizeSelection
      .mutateAsync(selectedPeriodId)
      .then((result) => {
        setFinalizeOpen(false);
        toast.success(
          `Đã chốt ${result.finalizedCount} hồ sơ${result.skippedCount ? `, loại ${result.skippedCount} hồ sơ không hợp lệ` : ""}.`,
        );
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Không thể chốt lựa chọn phòng.",
        ),
      );
  };

  const hasFilters = Boolean(
    search.q ||
      search.status ||
      search.buildingId ||
      search.floorId ||
      search.roomId,
  );

  const resetFilters = () => {
    onSearch({
      q: "",
      status: undefined,
      buildingId: undefined,
      floorId: undefined,
      roomId: undefined,
      page: 1,
    });
  };

  return (
    <div className="space-y-4">
      {/* 1. Filter Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 text-xs"
            value={search.q}
            placeholder="Tìm theo mã hồ sơ hoặc sinh viên..."
            aria-label="Tìm phân phòng"
            onChange={(event) => onSearch({ q: event.target.value, page: 1 })}
          />
        </div>
        <div className="flex flex-col gap-2 w-full sm:flex-row sm:flex-wrap sm:w-auto sm:items-center">
          <Select
            value={selectedPeriodId ?? "none"}
            onValueChange={(value) => {
              if (value !== "none") {
                onSearch({ registrationPeriodId: value, page: 1 });
              }
            }}
          >
            <SelectTrigger
              className="w-full sm:w-56 text-xs"
              aria-label="Lọc đợt đăng ký"
            >
              <SelectValue
                placeholder={
                  periods.isLoading ? "Đang tải đợt..." : "Chọn đợt đăng ký"
                }
              />
            </SelectTrigger>
            <SelectContent>
              {periodOptions.length ? (
                periodOptions.map((period) => (
                  <SelectItem key={period.id} value={period.id}>
                    {period.code} · {period.name}
                  </SelectItem>
                ))
              ) : (
                <SelectItem value="none" disabled>
                  Chưa có đợt đăng ký
                </SelectItem>
              )}
            </SelectContent>
          </Select>

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

          <Select
            value={search.status ?? "all"}
            onValueChange={(value) =>
              onSearch({
                status:
                  value === "all" ? undefined : (value as AssignmentStatus),
                page: 1,
              })
            }
          >
            <SelectTrigger
              className="w-full sm:w-36 text-xs"
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

          {hasFilters && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-9 px-2.5 text-xs text-muted-foreground hover:text-foreground"
              onClick={resetFilters}
            >
              <RotateCcw className="size-3.5 mr-1" />
              <span>Đặt lại</span>
            </Button>
          )}

          {/* Export Excel Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="w-full sm:w-auto gap-1.5 text-xs font-semibold"
                disabled={isExporting || !selectedPeriodId}
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
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem onClick={() => void handleExportAll()}>
                <FileSpreadsheet className="size-4 mr-2 text-emerald-600" />
                <span>Xuất tất cả (2 Sheet)</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => void handleExportAssigned()}>
                <Check className="size-4 mr-2 text-blue-600" />
                <span>Chỉ xuất SV đã chọn phòng</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => void handleExportUnassigned()}>
                <UserX className="size-4 mr-2 text-amber-600" />
                <span>Chỉ xuất SV chưa chọn phòng</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {manualAssignmentAvailable ? (
            <Button
              variant="outline"
              size="sm"
              className="w-full sm:w-auto gap-1.5 text-xs font-medium"
              onClick={() => setCreateOpen(true)}
            >
              <UserPlus className="size-3.5" />
              <span>Xếp thủ công</span>
            </Button>
          ) : null}

          {canFinalize && workspace.data?.canFinalizeSelection ? (
            <Button
              size="sm"
              className="w-full sm:w-auto gap-1.5 text-xs font-semibold"
              disabled={workspace.data.selectedCount === 0}
              onClick={() => setFinalizeOpen(true)}
            >
              <ClipboardCheck className="size-3.5" />
              <span>Chốt chỗ ở</span>
            </Button>
          ) : null}
        </div>
      </div>

      <AssignmentWorkflowSummary
        workspace={workspace.data}
        isLoading={workspace.isLoading}
        error={workspace.error}
        onRetry={() => void workspace.refetch()}
        onOpenRoomScope={
          selectedPeriodId
            ? () =>
                void navigate({
                  to: "/registration-periods/$periodId/room-rules",
                  params: { periodId: selectedPeriodId },
                })
            : undefined
        }
      />

      {query.isLoading ? (
        <div className="rounded-lg border bg-card p-5">
          <div className="grid gap-4">
            {[1, 2, 3, 4].map((item) => (
              <Skeleton key={item} className="h-8 w-full" />
            ))}
          </div>
        </div>
      ) : query.isError ? (
        <div className="rounded-lg border border-dashed p-10 text-center">
          <p>Không thể tải danh sách xếp phòng.</p>
          <Button
            className="mt-3"
            variant="outline"
            size="sm"
            onClick={() => void query.refetch()}
          >
            Thử lại
          </Button>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border bg-card shadow-2xs">
            <Table>
              <TableHeader className="bg-muted/30">
                {table.getHeaderGroups().map((group) => (
                  <TableRow key={group.id} className="hover:bg-transparent">
                    {group.headers.map((header) => (
                      <TableHead
                        key={header.id}
                        className="text-xs font-semibold text-muted-foreground whitespace-nowrap"
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
                      className="hover:bg-muted/40 transition-colors"
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
                      colSpan={columns.length}
                      className="h-32 text-center"
                    >
                      <DataTableEmpty
                        title="Không tìm thấy bản ghi phân phòng"
                        description="Thử thay đổi bộ lọc hoặc thêm phân phòng mới."
                      />
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          <DataTablePagination
            page={search.page}
            pageSize={search.pageSize}
            pageCount={query.data?.totalPages ?? 1}
            total={query.data?.total ?? 0}
            onPageChange={(page) => onSearch({ page })}
            onPageSizeChange={(pageSize) => onSearch({ pageSize, page: 1 })}
          />
        </>
      )}

      <AssignDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        registrationPeriodId={selectedPeriodId}
      />

      <CancelDialog assignment={pending} onClose={() => setPending(null)} />

      <RefundAndCancelDialog
        assignment={refundPending}
        onClose={() => setRefundPending(null)}
      />

      <ConfirmDialog
        open={finalizeOpen}
        onOpenChange={(open) => {
          if (!open && !finalizeSelection.isPending) setFinalizeOpen(false);
        }}
        title="Chốt lựa chọn phòng?"
        description={`Bạn có chắc chắn muốn chốt toàn bộ ${workspace.data?.selectedCount ?? 0} chỗ ở đang giữ chỗ của đợt này?`}
        confirmLabel="Chốt chỗ ở"
        isLoading={finalizeSelection.isPending}
        onConfirm={finalize}
      />
    </div>
  );
}
