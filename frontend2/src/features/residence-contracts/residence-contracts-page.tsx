import {
  CheckCircle2,
  Clock,
  Eye,
  FileClock,
  FilePenLine,
  FileText,
  MoreHorizontal,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Combobox } from "@/components/admin/combobox";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
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
  DropdownMenuSeparator,
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
import {
  contractStatusLabels,
  paymentPlanLabels,
  useActivateResidenceContract,
  useCancelResidenceContract,
  useCreateResidenceContract,
  useResidenceContractsQuery,
  useSubmitResidenceContract,
  useUpdateResidenceContract,
} from "@/features/residence-contracts/api";
import { ResidenceContractDialog } from "@/features/residence-contracts/residence-contract-dialog";
import type {
  ResidenceContract,
  ResidenceContractDetail,
  ResidenceContractStatus,
} from "@/features/residence-contracts/types";
import { useResidencesQuery } from "@/features/residences/api";
import { cn } from "@/lib/utils";

function formatDate(value?: string | null) {
  if (!value) return "—";
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

function formatAmount(value: number, currency: string) {
  return `${new Intl.NumberFormat("vi-VN").format(value)} ${currency}`;
}

const statusDotColors: Record<ResidenceContractStatus, string> = {
  active: "bg-emerald-500",
  pending_signature: "bg-amber-500",
  draft: "bg-muted-foreground/60",
  cancelled: "bg-red-500",
};

const statusBadgeVariants: Record<
  ResidenceContractStatus,
  "success" | "warning" | "secondary" | "destructive"
> = {
  active: "success",
  pending_signature: "warning",
  draft: "secondary",
  cancelled: "destructive",
};

const statusOptions: Array<{ value: string; label: string }> = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "active", label: "Đang hiệu lực" },
  { value: "pending_signature", label: "Chờ ký kết" },
  { value: "draft", label: "Bản nháp" },
  { value: "cancelled", label: "Đã hủy" },
];

type ActionState = {
  kind: "submit" | "activate" | "cancel";
  contract: ResidenceContract;
} | null;

export function ResidenceContractsPage({
  search,
  onSearch,
  onView,
  canCreate,
  canUpdate,
}: {
  search: {
    q: string;
    status?: ResidenceContractStatus;
    page: number;
    pageSize: number;
  };
  onSearch: (changes: Partial<typeof search>) => void;
  onView: (contract: ResidenceContract) => void;
  canCreate: boolean;
  canUpdate: boolean;
}) {
  const [dialog, setDialog] = useState<
    "create" | ResidenceContract | ResidenceContractDetail | null
  >(null);
  const [action, setAction] = useState<ActionState>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());

  const query = useResidenceContractsQuery({
    search: search.q.trim() || undefined,
    status: search.status,
    page: search.page,
    pageSize: search.pageSize,
  });

  const residences = useResidencesQuery({
    page: 1,
    pageSize: 100,
    status: "active",
    enabled: canCreate,
  });

  const create = useCreateResidenceContract();
  const update = useUpdateResidenceContract();
  const submit = useSubmitResidenceContract();
  const activate = useActivateResidenceContract();
  const cancel = useCancelResidenceContract();

  const contracts = query.data?.items ?? [];

  // Summary Metrics
  const summary = useMemo(() => {
    const total = query.data?.total ?? contracts.length;
    const active = contracts.filter((c) => c.status === "active").length;
    const pending = contracts.filter(
      (c) => c.status === "pending_signature",
    ).length;
    const draft = contracts.filter((c) => c.status === "draft").length;
    return { total, active, pending, draft };
  }, [contracts, query.data?.total]);

  const hasFilters = Boolean(search.q || search.status);

  const resetFilters = () => {
    onSearch({
      q: "",
      status: undefined,
      page: 1,
    });
  };

  const allSelected =
    contracts.length > 0 && contracts.every((item) => selectedIds.has(item.id));
  const someSelected =
    contracts.some((item) => selectedIds.has(item.id)) && !allSelected;

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(contracts.map((item) => item.id)));
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

  const actionTitle =
    action?.kind === "submit"
      ? "Gửi hợp đồng chờ ký?"
      : action?.kind === "activate"
        ? "Kích hoạt hợp đồng?"
        : "Hủy bản nháp hợp đồng?";
  const actionDescription =
    action?.kind === "submit"
      ? "Hợp đồng sẽ chuyển sang trạng thái chờ ký và không còn chỉnh sửa được."
      : action?.kind === "activate"
        ? "Xác nhận hợp đồng đã ký để bắt đầu hiệu lực nội trú."
        : "Hợp đồng sẽ được đánh dấu đã hủy. Bạn chỉ nên thực hiện khi hồ sơ không còn sử dụng.";

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / CƯ TRÚ"
        title="Hợp đồng nội trú"
        description="Theo dõi thời hạn, giá trị và trạng thái ký kết của từng lượt cư trú."
        actions={
          <div className="flex items-center gap-2">
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
            {canCreate && (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setDialog("create")}
              >
                <Plus className="size-3.5" />
                <span>Tạo hợp đồng</span>
              </Button>
            )}
          </div>
        }
      />

      {/* 2. KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={FileText}
            label="Tổng hợp đồng"
            value={summary.total.toLocaleString("vi-VN")}
            helper="Tổng số hợp đồng nội trú đã lưu trữ"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Đang hiệu lực"
            value={summary.active.toLocaleString("vi-VN")}
            trend="positive"
            helper="Hợp đồng đã ký kết và có hiệu lực"
          />
          <KpiMetric
            icon={Clock}
            label="Chờ ký kết"
            value={summary.pending.toLocaleString("vi-VN")}
            helper="Hợp đồng đã gửi cho sinh viên ký"
          />
          <KpiMetric
            icon={FileClock}
            label="Bản nháp"
            value={summary.draft.toLocaleString("vi-VN")}
            helper="Hợp đồng đang soạn thảo chưa phát hành"
          />
        </CardContent>
      </Card>

      {/* 3. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="w-full lg:w-80">
          <DebouncedSearchInput
            className="text-xs"
            value={search.q}
            placeholder="Tìm mã hợp đồng, mã hoặc tên sinh viên..."
            aria-label="Tìm hợp đồng"
            onChange={(val) => onSearch({ q: val, page: 1 })}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          {/* Trạng thái */}
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-52 text-xs"
            options={statusOptions}
            value={search.status ?? "all"}
            searchPlaceholder="Tìm trạng thái..."
            onValueChange={(value) =>
              onSearch({
                status:
                  value === "all"
                    ? undefined
                    : (value as ResidenceContractStatus),
                page: 1,
              })
            }
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
                    aria-label="Chọn tất cả hợp đồng"
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
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[200px]">
                Hợp đồng
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[220px]">
                Sinh viên
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[180px]">
                Chỗ ở
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[180px]">
                Thời hạn
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[160px]">
                Giá trị
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[150px]">
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
                  <div className="flex items-center justify-center gap-2">
                    <RefreshCw className="size-4 animate-spin" />
                    <span>Đang tải danh sách hợp đồng...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : query.isError ? (
              <TableRow>
                <TableCell colSpan={8} className="p-8">
                  <EmptyState
                    icon={FileText}
                    title="Không thể tải danh sách hợp đồng"
                    description="Kiểm tra kết nối mạng hoặc thử tải lại sau ít phút."
                    action={{
                      label: "Thử lại",
                      onClick: () => void query.refetch(),
                    }}
                  />
                </TableCell>
              </TableRow>
            ) : contracts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="p-8">
                  <EmptyState
                    icon={FileText}
                    title={
                      hasFilters
                        ? "Không có hợp đồng phù hợp"
                        : "Chưa có hợp đồng nội trú"
                    }
                    description={
                      hasFilters
                        ? "Thử thay đổi từ khóa tìm kiếm hoặc trạng thái lọc."
                        : "Hợp đồng sẽ xuất hiện sau khi sinh viên hoàn tất đăng ký cư trú."
                    }
                    action={
                      hasFilters
                        ? { label: "Xóa bộ lọc", onClick: resetFilters }
                        : canCreate
                          ? {
                              label: "Tạo hợp đồng đầu tiên",
                              onClick: () => setDialog("create"),
                            }
                          : undefined
                    }
                  />
                </TableCell>
              </TableRow>
            ) : (
              contracts.map((contract) => (
                <TableRow
                  key={contract.id}
                  className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                  onClick={() => onView(contract)}
                >
                  <TableCell
                    className="pl-3"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <div className="flex items-center pl-1">
                      <Checkbox
                        aria-label={`Chọn hợp đồng ${contract.contractNumber}`}
                        checked={selectedIds.has(contract.id)}
                        onCheckedChange={(val) =>
                          toggleSelect(contract.id, Boolean(val))
                        }
                      />
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-semibold text-foreground text-sm font-mono">
                      {contract.contractNumber}
                    </div>
                    <div className="type-supporting text-muted-foreground text-xs">
                      {formatDate(contract.signedAt)}
                      {contract.signedAt ? " · Đã ký" : " · Chưa ký"}
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-semibold text-foreground text-sm">
                      {contract.studentName}
                    </div>
                    <div className="type-supporting text-muted-foreground font-mono text-xs">
                      {contract.studentCode}
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono text-xs">
                        {contract.roomCode}
                      </Badge>
                      <span className="text-foreground text-sm">
                        {contract.buildingName}
                      </span>
                    </div>
                  </TableCell>

                  <TableCell>
                    <span className="text-xs text-muted-foreground font-mono">
                      {formatDate(contract.effectiveFrom)} –{" "}
                      {formatDate(contract.effectiveTo)}
                    </span>
                  </TableCell>

                  <TableCell>
                    <div className="font-semibold font-mono tabular-nums text-foreground text-sm">
                      {formatAmount(contract.totalAmount, contract.currency)}
                    </div>
                    <div className="type-supporting text-muted-foreground text-xs">
                      {paymentPlanLabels[contract.paymentPlan] ??
                        contract.paymentPlan}
                    </div>
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant={statusBadgeVariants[contract.status]}
                      className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
                    >
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          statusDotColors[contract.status],
                        )}
                      />
                      {contractStatusLabels[contract.status]}
                    </Badge>
                  </TableCell>

                  <TableCell onClick={(event) => event.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          className="size-8 text-muted-foreground hover:text-foreground"
                          aria-label={`Thao tác với hợp đồng ${contract.contractNumber}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-52">
                        <DropdownMenuItem onClick={() => onView(contract)}>
                          <Eye className="size-4 mr-2 text-muted-foreground" />
                          Xem chi tiết
                        </DropdownMenuItem>

                        {canUpdate && contract.status === "draft" && (
                          <DropdownMenuItem onClick={() => setDialog(contract)}>
                            <FilePenLine className="size-4 mr-2 text-muted-foreground" />
                            Chỉnh sửa
                          </DropdownMenuItem>
                        )}

                        {canUpdate && contract.status === "draft" && (
                          <DropdownMenuItem
                            onClick={() =>
                              setAction({ kind: "submit", contract })
                            }
                          >
                            <Send className="size-4 mr-2 text-muted-foreground" />
                            Gửi chờ ký
                          </DropdownMenuItem>
                        )}

                        {canUpdate &&
                          contract.status === "pending_signature" && (
                            <DropdownMenuItem
                              onClick={() =>
                                setAction({ kind: "activate", contract })
                              }
                            >
                              <ShieldCheck className="size-4 mr-2 text-emerald-600 dark:text-emerald-400" />
                              Kích hoạt hợp đồng
                            </DropdownMenuItem>
                          )}

                        {canUpdate &&
                          (contract.status === "draft" ||
                            contract.status === "pending_signature") && (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={() =>
                                  setAction({ kind: "cancel", contract })
                                }
                              >
                                <Trash2 className="size-4 mr-2" />
                                Hủy hợp đồng
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
        selectedLabel="hợp đồng"
        onClear={() => setSelectedIds(new Set())}
      />

      {/* 7. Dialogs */}
      <ResidenceContractDialog
        key={dialog === "create" ? "create" : (dialog?.id ?? "closed")}
        open={dialog !== null}
        contract={dialog === "create" ? null : dialog}
        residences={residences.data?.items ?? []}
        onOpenChange={(open) => {
          if (!open) setDialog(null);
        }}
        onCreate={async (input) => {
          await create.mutateAsync(input);
          toast.success("Tạo hợp đồng thành công");
          setDialog(null);
        }}
        onUpdate={async (id, input) => {
          await update.mutateAsync({ id, input });
          toast.success("Cập nhật hợp đồng thành công");
          setDialog(null);
        }}
        isSubmitting={create.isPending || update.isPending}
      />

      <ConfirmDialog
        open={action !== null}
        title={actionTitle}
        description={actionDescription}
        confirmLabel={
          action?.kind === "submit"
            ? "Gửi chờ ký"
            : action?.kind === "activate"
              ? "Kích hoạt"
              : "Hủy hợp đồng"
        }
        confirmVariant={action?.kind === "cancel" ? "destructive" : "default"}
        isLoading={submit.isPending || activate.isPending || cancel.isPending}
        onOpenChange={(open) => {
          if (!open) setAction(null);
        }}
        onConfirm={() => {
          if (!action) return;
          if (action.kind === "submit") {
            submit.mutate(action.contract.id, {
              onSuccess: () => {
                toast.success("Đã gửi hợp đồng chờ ký");
                setAction(null);
              },
            });
            return;
          }
          if (action.kind === "activate") {
            activate.mutate(action.contract.id, {
              onSuccess: () => {
                toast.success("Kích hoạt hợp đồng thành công");
                setAction(null);
              },
            });
            return;
          }
          cancel.mutate(action.contract.id, {
            onSuccess: () => {
              toast.success("Đã hủy hợp đồng");
              setAction(null);
            },
          });
        }}
      />
    </div>
  );
}
