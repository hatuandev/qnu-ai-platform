import { useNavigate } from "@tanstack/react-router";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import {
  Check,
  CheckCheck,
  Eye,
  FileSpreadsheet,
  FileUp,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  RotateCcw,
  Trash2,
  X,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DataTableViewOptions } from "@/components/admin/data-table/data-table-view-options";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
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
import { Textarea } from "@/components/ui/textarea";
import {
  exportApplicationsToExcel,
  useApplicationsQuery,
  useBulkApprovePeriodApplications,
  useBulkReviewApplications,
  useDeleteApplication,
  useRejectApplication,
} from "@/features/applications/api";
import { EditApplicationDialog } from "@/features/applications/edit-application-dialog";
import { ImportApplicationsDialog } from "@/features/applications/import-applications-dialog";
import {
  type ApplicationStatus,
  applicationStatusLabels,
  type BulkReviewDecision,
  type DormitoryApplication,
} from "@/features/applications/types";
import { useRegistrationPeriodsQuery } from "@/features/registration-periods/api";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const labels = {
  applicationCode: "Mã hồ sơ",
  studentName: "Sinh viên",
  registrationPeriodName: "Đợt đăng ký",
  requestedRoomTypeName: "Loại phòng",
  status: "Trạng thái",
};

const statusDotColors: Record<ApplicationStatus, string> = {
  draft: "bg-muted-foreground/60",
  submitted: "bg-blue-500",
  need_supplement: "bg-amber-500",
  approved: "bg-emerald-500",
  rejected: "bg-destructive",
  cancelled: "bg-muted-foreground/60",
  assigned: "bg-purple-500",
};

const statusBadgeClasses: Record<ApplicationStatus, string> = {
  draft: "bg-muted text-muted-foreground border-border",
  submitted:
    "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
  need_supplement:
    "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
  approved:
    "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  rejected: "bg-destructive/15 text-destructive border-destructive/30",
  cancelled: "bg-muted text-muted-foreground border-border",
  assigned:
    "bg-purple-500/15 text-purple-700 dark:text-purple-400 border-purple-500/30",
};

export function ApplicationsPage({
  search,
  onSearch,
  canReview,
}: {
  search: {
    q: string;
    status?: ApplicationStatus;
    registrationPeriodId?: string;
    page: number;
    pageSize: number;
  };
  onSearch: (changes: Partial<typeof search>) => void;
  canReview: boolean;
}) {
  const navigate = useNavigate();
  const { can } = useRbac();
  const query = useApplicationsQuery({
    registrationPeriodId: search.registrationPeriodId,
    search: search.q.trim() || undefined,
    status: search.status,
    page: search.page,
    pageSize: search.pageSize,
  });
  const periodsQuery = useRegistrationPeriodsQuery({ page: 1, pageSize: 100 });
  const bulkReview = useBulkReviewApplications();
  const bulkApprovePeriod = useBulkApprovePeriodApplications();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkAction, setBulkAction] = useState<BulkReviewDecision | null>(null);
  const [bulkNote, setBulkNote] = useState("");
  const [bulkApprovePeriodOpen, setBulkApprovePeriodOpen] = useState(false);
  const [bulkApprovePeriodNote, setBulkApprovePeriodNote] = useState("");
  const [visibility, setVisibility] = useState<VisibilityState>({});
  const [isExporting, setIsExporting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [editingApplication, setEditingApplication] =
    useState<DormitoryApplication | null>(null);
  const [deletingApplication, setDeletingApplication] =
    useState<DormitoryApplication | null>(null);
  const [rejectingApplication, setRejectingApplication] =
    useState<DormitoryApplication | null>(null);
  const [rejectNote, setRejectNote] = useState("");

  const deleteApplication = useDeleteApplication();
  const rejectApplication = useRejectApplication();

  const handleExportExcel = async () => {
    if (!search.registrationPeriodId || search.registrationPeriodId === "all") {
      toast.warning("Vui lòng chọn một đợt đăng ký để xuất file Excel.");
      return;
    }

    try {
      setIsExporting(true);
      await exportApplicationsToExcel({
        registrationPeriodId: search.registrationPeriodId,
        status: search.status,
        search: search.q,
      });
      toast.success("Xuất file Excel hồ sơ đăng ký thành công!");
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

  const handleBulkApprovePeriod = async () => {
    if (!search.registrationPeriodId || search.registrationPeriodId === "all")
      return;
    try {
      const result = await bulkApprovePeriod.mutateAsync({
        registrationPeriodId: search.registrationPeriodId,
        reviewNote: bulkApprovePeriodNote.trim() || undefined,
      });
      if (result.approvedCount > 0) {
        toast.success(
          `Đã duyệt thành công ${result.approvedCount} hồ sơ trong đợt "${result.periodName}".`,
        );
      } else {
        toast.info("Không có hồ sơ nào đang chờ duyệt trong đợt này.");
      }
      setBulkApprovePeriodOpen(false);
      setBulkApprovePeriodNote("");
      setSelectedIds(new Set());
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Không thể duyệt hồ sơ theo đợt.",
      );
    }
  };

  const items = query.data?.items ?? [];
  const reviewableItems = canReview
    ? items.filter(
        (item) =>
          item.status === "submitted" || item.status === "need_supplement",
      )
    : [];
  const allReviewableSelected =
    reviewableItems.length > 0 &&
    reviewableItems.every((item) => selectedIds.has(item.id));
  const someReviewableSelected = reviewableItems.some((item) =>
    selectedIds.has(item.id),
  );
  const selectionResetKey = [
    search.q,
    search.status,
    search.registrationPeriodId,
    search.page,
  ].join("|");

  // Selection belongs to the current filtered page and must reset when that page changes.
  // biome-ignore lint/correctness/useExhaustiveDependencies: selectionResetKey intentionally controls the reset boundary.
  useEffect(() => {
    setSelectedIds(new Set());
  }, [selectionResetKey]);

  const togglePageSelection = (checked: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      for (const item of reviewableItems) {
        if (checked) next.add(item.id);
        else next.delete(item.id);
      }
      return next;
    });
  };

  const toggleSelection = (id: string, checked: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const bulkActionLabel =
    bulkAction === "approve"
      ? "Duyệt hồ sơ"
      : bulkAction === "reject"
        ? "Từ chối hồ sơ"
        : "Yêu cầu bổ sung hồ sơ";

  const handleBulkReview = async () => {
    if (!bulkAction || selectedIds.size === 0) return;
    try {
      const result = await bulkReview.mutateAsync({
        applicationIds: [...selectedIds],
        decision: bulkAction,
        reviewNote: bulkNote.trim() || undefined,
      });
      if (result.skippedCount > 0) {
        toast.warning(
          `Đã xử lý ${result.processedCount} hồ sơ; ${result.skippedCount} hồ sơ không thể xử lý.`,
        );
      } else {
        toast.success(`Đã xử lý ${result.processedCount} hồ sơ.`);
      }
      setSelectedIds(new Set());
      setBulkAction(null);
      setBulkNote("");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Không thể xử lý hồ sơ.",
      );
    }
  };

  const columns = useMemo<ColumnDef<DormitoryApplication>[]>(
    () => [
      {
        id: "select",
        size: 40,
        enableSorting: false,
        enableHiding: false,
        header: () => (
          <div className="flex items-center pl-1">
            <Checkbox
              aria-label="Chọn tất cả hồ sơ có thể xử lý trên trang"
              checked={
                allReviewableSelected
                  ? true
                  : someReviewableSelected
                    ? "indeterminate"
                    : false
              }
              disabled={reviewableItems.length === 0}
              onCheckedChange={(checked) =>
                togglePageSelection(checked === true)
              }
            />
          </div>
        ),
        cell: ({ row }) => {
          const reviewable =
            row.original.status === "submitted" ||
            row.original.status === "need_supplement";
          return (
            <div
              className="flex items-center pl-1"
              onClick={(event) => event.stopPropagation()}
            >
              <Checkbox
                aria-label={`Chọn hồ sơ ${row.original.applicationCode}`}
                checked={selectedIds.has(row.original.id)}
                disabled={!reviewable}
                onCheckedChange={(checked) =>
                  toggleSelection(row.original.id, checked === true)
                }
              />
            </div>
          );
        },
      },
      {
        accessorKey: "applicationCode",
        header: labels.applicationCode,
        cell: ({ row }) => (
          <span className="font-mono font-medium text-xs bg-muted/60 px-2 py-0.5 rounded text-foreground">
            {row.original.applicationCode}
          </span>
        ),
      },
      {
        accessorKey: "studentName",
        header: labels.studentName,
        cell: ({ row }) => (
          <div>
            <p className="font-semibold text-foreground hover:text-primary transition-colors">
              {row.original.studentName}
            </p>
            <p className="text-[11px] text-muted-foreground font-mono">
              {row.original.studentCode}
            </p>
          </div>
        ),
      },
      {
        accessorKey: "registrationPeriodName",
        header: labels.registrationPeriodName,
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.original.registrationPeriodName || "—"}
          </span>
        ),
      },
      {
        accessorKey: "requestedRoomTypeName",
        header: labels.requestedRoomTypeName,
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.original.requestedRoomTypeName || "—"}
          </span>
        ),
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
                statusBadgeClasses[s] || "bg-muted text-muted-foreground",
              )}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  statusDotColors[s] || "bg-muted-foreground/60",
                )}
              />
              {applicationStatusLabels[s] || s}
            </Badge>
          );
        },
      },
      {
        id: "actions",
        header: "",
        enableHiding: false,
        cell: ({ row }) => {
          const hasEditPermission =
            can("ktx.applications.update") ||
            can("ktx.applications.create") ||
            can("ktx.applications.review");

          const canEdit =
            hasEditPermission &&
            (row.original.status === "draft" ||
              row.original.status === "submitted" ||
              row.original.status === "need_supplement" ||
              row.original.status === "approved");

          const canRejectItem =
            can("ktx.applications.review") &&
            (row.original.status === "submitted" ||
              row.original.status === "need_supplement" ||
              row.original.status === "approved");

          const canDeleteItem =
            (can("ktx.applications.delete") ||
              can("ktx.applications.review")) &&
            row.original.status !== "assigned";

          return (
            <div
              className="flex justify-end"
              onClick={(event) => event.stopPropagation()}
            >
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Thao tác với hồ sơ ${row.original.applicationCode}`}
                  >
                    <MoreHorizontal className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onSelect={() =>
                      void navigate({
                        to: "/applications/$applicationId",
                        params: { applicationId: row.original.id },
                      })
                    }
                  >
                    <Eye className="size-4 mr-2" />
                    Xem chi tiết
                  </DropdownMenuItem>
                  {canEdit && (
                    <DropdownMenuItem
                      onSelect={() => setEditingApplication(row.original)}
                    >
                      <Pencil className="size-4 mr-2" />
                      Chỉnh sửa hồ sơ
                    </DropdownMenuItem>
                  )}
                  {canRejectItem && (
                    <DropdownMenuItem
                      className="text-destructive focus:text-destructive"
                      onSelect={() => {
                        setRejectingApplication(row.original);
                        setRejectNote("");
                      }}
                    >
                      <XCircle className="size-4 mr-2" />
                      Từ chối hồ sơ
                    </DropdownMenuItem>
                  )}
                  {canDeleteItem && (
                    <DropdownMenuItem
                      className="text-destructive focus:text-destructive"
                      onSelect={() => setDeletingApplication(row.original)}
                    >
                      <Trash2 className="size-4 mr-2" />
                      Xóa hồ sơ
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          );
        },
      },
    ],
    // biome-ignore lint/correctness/useExhaustiveDependencies: navigate and reviewable state intentionally bound
    [
      allReviewableSelected,
      someReviewableSelected,
      reviewableItems.length,
      selectedIds,
      navigate,
    ],
  );

  const table = useReactTable({
    data: items,
    columns,
    state: { columnVisibility: visibility },
    onColumnVisibilityChange: setVisibility,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,
  });

  const hasFilters = Boolean(
    search.q || search.status || search.registrationPeriodId,
  );

  return (
    <div className="space-y-4">
      {/* 1. Responsive Filters Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-xs">
          <DebouncedSearchInput
            className="h-9 text-xs"
            value={search.q}
            placeholder="Tìm theo mã hoặc tên sinh viên..."
            aria-label="Tìm hồ sơ đăng ký"
            onChange={(val) => onSearch({ q: val, page: 1 })}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={search.registrationPeriodId ?? "all"}
            onValueChange={(value) =>
              onSearch({
                registrationPeriodId: value === "all" ? undefined : value,
                page: 1,
              })
            }
          >
            <SelectTrigger
              className="w-full sm:w-52 h-9 text-xs"
              aria-label="Lọc đợt đăng ký"
            >
              <SelectValue placeholder="Đợt đăng ký" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả đợt đăng ký</SelectItem>
              {periodsQuery.data?.items.map((period) => (
                <SelectItem key={period.id} value={period.id}>
                  {period.code} · {period.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={search.status ?? "all"}
            onValueChange={(value) =>
              onSearch({
                status:
                  value === "all" ? undefined : (value as ApplicationStatus),
                page: 1,
              })
            }
          >
            <SelectTrigger
              className="w-full sm:w-44 h-9 text-xs"
              aria-label="Lọc trạng thái"
            >
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              {Object.entries(applicationStatusLabels).map(([value, label]) => (
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
              onClick={() =>
                onSearch({
                  q: "",
                  status: undefined,
                  registrationPeriodId: undefined,
                  page: 1,
                })
              }
            >
              <RotateCcw className="size-3.5 mr-1" />
              Đặt lại
            </Button>
          ) : null}

          {canReview &&
          search.registrationPeriodId &&
          search.registrationPeriodId !== "all" ? (
            <Button
              variant="outline"
              size="sm"
              className="h-9 px-3 text-xs gap-1.5 border-emerald-500/50 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 font-medium shadow-2xs"
              onClick={() => setBulkApprovePeriodOpen(true)}
              disabled={bulkApprovePeriod.isPending}
              aria-label="Duyệt tất cả hồ sơ chờ duyệt trong đợt này"
            >
              <CheckCheck className="size-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Duyệt toàn bộ đợt này</span>
            </Button>
          ) : null}

          <Button
            variant="outline"
            size="sm"
            className="h-9 px-3 text-xs gap-1.5 border-border/80 shadow-2xs hover:bg-muted text-foreground"
            onClick={() => void handleExportExcel()}
            disabled={isExporting}
            aria-label="Xuất file Excel danh sách hồ sơ"
          >
            <FileSpreadsheet className="size-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>{isExporting ? "Đang xuất..." : "Xuất Excel"}</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-9 px-3 text-xs gap-1.5 border-border/80 shadow-2xs hover:bg-muted text-foreground"
            onClick={() => setImportOpen(true)}
            aria-label="Nhập file Excel danh sách hồ sơ"
          >
            <FileUp className="size-3.5 text-blue-600 dark:text-blue-400" />
            <span>Nhập Excel</span>
          </Button>

          <DataTableViewOptions table={table} labels={labels} />
        </div>
      </div>

      {/* 2. Main Table & Integrated Pagination */}
      {query.isLoading ? (
        <div className="rounded-xl border bg-card p-6 shadow-2xs">
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((item) => (
              <Skeleton key={item} className="h-9 w-full rounded" />
            ))}
          </div>
        </div>
      ) : query.isError ? (
        <div className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-card px-5 py-8 text-center shadow-2xs">
          <p className="font-semibold text-foreground">
            Không thể tải hồ sơ đăng ký
          </p>
          <p className="text-xs text-muted-foreground max-w-sm">
            {query.error instanceof Error
              ? query.error.message
              : "Hãy kiểm tra kết nối mạng và thử lại."}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void query.refetch()}
          >
            Thử lại
          </Button>
        </div>
      ) : (
        <>
          {canReview &&
          allReviewableSelected &&
          (query.data?.total ?? 0) > reviewableItems.length ? (
            <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20 px-4 py-2 text-xs text-foreground animate-in fade-in duration-200">
              <span className="text-muted-foreground">
                Đang chọn <strong>{reviewableItems.length}</strong> hồ sơ chờ
                duyệt trên trang này.
              </span>
              {search.registrationPeriodId &&
              search.registrationPeriodId !== "all" ? (
                <Button
                  variant="link"
                  size="sm"
                  className="h-auto p-0 text-xs font-semibold text-emerald-700 dark:text-emerald-400 hover:underline"
                  onClick={() => setBulkApprovePeriodOpen(true)}
                >
                  Duyệt toàn bộ {query.data?.total} hồ sơ trong đợt này &rarr;
                </Button>
              ) : null}
            </div>
          ) : null}

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
                        data-state={
                          selectedIds.has(row.original.id) && "selected"
                        }
                        className="cursor-pointer hover:bg-muted/40 transition-colors"
                        onClick={() =>
                          void navigate({
                            to: "/applications/$applicationId",
                            params: { applicationId: row.original.id },
                          })
                        }
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
                              ? "Không có hồ sơ phù hợp với bộ lọc"
                              : "Chưa có hồ sơ đăng ký nào"
                          }
                          description={
                            hasFilters
                              ? "Hãy mở rộng tìm kiếm hoặc xóa bộ lọc."
                              : "Hồ sơ sẽ xuất hiện khi sinh viên gửi đăng ký nội trú."
                          }
                          action={
                            hasFilters
                              ? {
                                  label: "Xóa bộ lọc",
                                  onClick: () =>
                                    onSearch({
                                      q: "",
                                      status: undefined,
                                      registrationPeriodId: undefined,
                                      page: 1,
                                    }),
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
          </div>

          {/* Clean borderless pagination directly below table */}
          <DataTablePagination
            page={search.page}
            pageSize={search.pageSize}
            pageCount={Math.max(1, query.data?.totalPages ?? 1)}
            total={query.data?.total ?? 0}
            onPageChange={(page) => onSearch({ page })}
            onPageSizeChange={(pageSize) => onSearch({ pageSize, page: 1 })}
          />
        </>
      )}

      {/* 3. Bulk Actions Floating Bar */}
      {canReview && selectedIds.size > 0 ? (
        <DataTableBulkActions
          selectedCount={selectedIds.size}
          selectedLabel="hồ sơ"
          onClear={() => setSelectedIds(new Set())}
        >
          <Button
            size="sm"
            className="h-8 px-3 text-xs font-medium gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs"
            onClick={() => setBulkAction("approve")}
            disabled={bulkReview.isPending}
            aria-label="Duyệt các hồ sơ đã chọn"
          >
            <Check className="size-3.5" />
            <span>Duyệt ({selectedIds.size})</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-8 px-3 text-xs font-medium gap-1.5 border-amber-500/40 text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30"
            onClick={() => setBulkAction("request-supplement")}
            disabled={bulkReview.isPending}
            aria-label="Yêu cầu bổ sung thông tin"
          >
            <MessageSquare className="size-3.5" />
            <span>Yêu cầu bổ sung</span>
          </Button>

          <Button
            variant="destructive"
            size="sm"
            className="h-8 px-3 text-xs font-medium gap-1.5 shadow-xs"
            onClick={() => setBulkAction("reject")}
            disabled={bulkReview.isPending}
            aria-label="Từ chối các hồ sơ đã chọn"
          >
            <X className="size-3.5" />
            <span>Từ chối</span>
          </Button>
        </DataTableBulkActions>
      ) : null}

      {/* 4. Responsive Bulk Action Dialog */}
      <ResponsiveDialog
        open={bulkAction !== null}
        onOpenChange={(open) => {
          if (!open && !bulkReview.isPending) {
            setBulkAction(null);
            setBulkNote("");
          }
        }}
      >
        <ResponsiveDialogContent>
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle>{bulkActionLabel}</ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              Bạn đang xử lý {selectedIds.size} hồ sơ đã chọn. Những hồ sơ không
              còn ở trạng thái chờ xử lý hoặc vượt chỉ tiêu sẽ được bỏ qua và
              báo lại sau khi hoàn tất.
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="space-y-2 py-2">
            <label
              className="text-xs font-semibold text-foreground"
              htmlFor="bulk-review-note"
            >
              {bulkAction === "approve"
                ? "Ghi chú (không bắt buộc)"
                : "Nội dung xử lý"}
            </label>
            <Textarea
              id="bulk-review-note"
              value={bulkNote}
              onChange={(event) => setBulkNote(event.target.value)}
              placeholder={
                bulkAction === "approve"
                  ? "Ví dụ: Đã kiểm tra hồ sơ theo danh sách ưu tiên."
                  : "Nhập nội dung gửi cho sinh viên..."
              }
              disabled={bulkReview.isPending}
            />
          </div>
          <ResponsiveDialogFooter>
            <Button
              variant="outline"
              onClick={() => setBulkAction(null)}
              disabled={bulkReview.isPending}
            >
              Hủy
            </Button>
            <Button
              variant={bulkAction === "reject" ? "destructive" : "default"}
              className={
                bulkAction === "approve"
                  ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                  : undefined
              }
              onClick={() => void handleBulkReview()}
              disabled={
                bulkReview.isPending ||
                (bulkAction !== "approve" && !bulkNote.trim())
              }
            >
              {bulkReview.isPending ? "Đang xử lý..." : "Xác nhận"}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* 5. Bulk Approve Period Dialog */}
      <ResponsiveDialog
        open={bulkApprovePeriodOpen}
        onOpenChange={(open) => {
          if (!open && !bulkApprovePeriod.isPending) {
            setBulkApprovePeriodOpen(false);
            setBulkApprovePeriodNote("");
          }
        }}
      >
        <ResponsiveDialogContent>
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle>
              Duyệt toàn bộ hồ sơ trong đợt
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              Hệ thống sẽ tự động duyệt toàn bộ các hồ sơ đang ở trạng thái{" "}
              <strong>Chờ duyệt</strong> và <strong>Yêu cầu bổ sung</strong>{" "}
              thuộc đợt đăng ký:{" "}
              <strong>
                {periodsQuery.data?.items.find(
                  (p) => p.id === search.registrationPeriodId,
                )?.name || "đang chọn"}
              </strong>
              .
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="space-y-2 py-2">
            <label
              className="text-xs font-semibold text-foreground"
              htmlFor="bulk-approve-period-note"
            >
              Ghi chú phê duyệt (không bắt buộc)
            </label>
            <Textarea
              id="bulk-approve-period-note"
              value={bulkApprovePeriodNote}
              onChange={(event) => setBulkApprovePeriodNote(event.target.value)}
              placeholder="Ví dụ: Duyệt hàng loạt theo danh sách phê duyệt của Nhà trường."
              disabled={bulkApprovePeriod.isPending}
            />
          </div>
          <ResponsiveDialogFooter>
            <Button
              variant="outline"
              onClick={() => setBulkApprovePeriodOpen(false)}
              disabled={bulkApprovePeriod.isPending}
            >
              Hủy
            </Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => void handleBulkApprovePeriod()}
              disabled={bulkApprovePeriod.isPending}
            >
              {bulkApprovePeriod.isPending
                ? "Đang xử lý..."
                : "Xác nhận duyệt tất cả"}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* 6. Import Applications Dialog */}
      <ImportApplicationsDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        defaultPeriodId={search.registrationPeriodId}
      />

      {/* 7. Edit Application Dialog */}
      <EditApplicationDialog
        open={Boolean(editingApplication)}
        onOpenChange={(open) => {
          if (!open) setEditingApplication(null);
        }}
        application={editingApplication}
      />

      {/* 8. Reject Application Dialog */}
      <ResponsiveDialog
        open={Boolean(rejectingApplication)}
        onOpenChange={(open) => {
          if (!open) setRejectingApplication(null);
        }}
      >
        <ResponsiveDialogContent className="max-w-md">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle className="flex items-center gap-2 text-destructive">
              <XCircle className="size-5" />
              <span>Từ chối hồ sơ đăng ký</span>
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              Từ chối hồ sơ{" "}
              <strong className="font-mono text-foreground">
                {rejectingApplication?.applicationCode}
              </strong>{" "}
              của sinh viên <strong>{rejectingApplication?.studentName}</strong>
              .
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="space-y-2 py-2">
            <label
              className="text-xs font-semibold text-foreground"
              htmlFor="reject-application-note"
            >
              Lý do từ chối <span className="text-destructive">*</span>
            </label>
            <Textarea
              id="reject-application-note"
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              placeholder="Nhập lý do từ chối hồ sơ..."
              disabled={rejectApplication.isPending}
            />
          </div>
          <ResponsiveDialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setRejectingApplication(null)}
              disabled={rejectApplication.isPending}
            >
              Hủy
            </Button>
            <Button
              variant="destructive"
              disabled={rejectApplication.isPending || !rejectNote.trim()}
              onClick={() => {
                if (!rejectingApplication || !rejectNote.trim()) return;
                rejectApplication.mutate(
                  {
                    id: rejectingApplication.id,
                    reviewNote: rejectNote.trim(),
                  },
                  {
                    onSuccess: () => {
                      toast.success("Đã từ chối hồ sơ đăng ký.");
                      setRejectingApplication(null);
                    },
                    onError: (err) => {
                      toast.error(
                        err instanceof Error
                          ? err.message
                          : "Từ chối hồ sơ thất bại.",
                      );
                    },
                  },
                );
              }}
            >
              {rejectApplication.isPending
                ? "Đang xử lý..."
                : "Xác nhận từ chối"}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* 9. Delete Application Dialog */}
      <ResponsiveDialog
        open={Boolean(deletingApplication)}
        onOpenChange={(open) => {
          if (!open) setDeletingApplication(null);
        }}
      >
        <ResponsiveDialogContent className="max-w-md">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="size-5" />
              <span>Xác nhận xóa hồ sơ đăng ký</span>
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription>
              Bạn có chắc chắn muốn xóa vĩnh viễn hồ sơ đăng ký{" "}
              <strong className="font-mono text-foreground">
                {deletingApplication?.applicationCode}
              </strong>{" "}
              của sinh viên <strong>{deletingApplication?.studentName}</strong>{" "}
              không?
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <div className="my-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-xs text-muted-foreground space-y-1">
            <p className="font-semibold text-destructive">Cảnh báo:</p>
            <p>
              Thao tác này sẽ xóa sạch hồ sơ đăng ký, các file minh chứng và
              lịch sử trạng thái kèm theo. Dữ liệu sau khi xóa sẽ không thể phục
              hồi.
            </p>
          </div>
          <ResponsiveDialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setDeletingApplication(null)}
              disabled={deleteApplication.isPending}
            >
              Hủy bỏ
            </Button>
            <Button
              variant="destructive"
              disabled={deleteApplication.isPending}
              onClick={() => {
                if (!deletingApplication) return;
                deleteApplication.mutate(deletingApplication.id, {
                  onSuccess: () => {
                    toast.success("Đã xóa hồ sơ đăng ký thành công.");
                    setDeletingApplication(null);
                  },
                  onError: (err) => {
                    toast.error(
                      err instanceof Error
                        ? err.message
                        : "Xóa hồ sơ thất bại.",
                    );
                  },
                });
              }}
            >
              {deleteApplication.isPending ? "Đang xóa..." : "Xác nhận xóa"}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>
    </div>
  );
}
