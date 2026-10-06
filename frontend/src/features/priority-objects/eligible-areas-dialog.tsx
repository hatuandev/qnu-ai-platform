import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  priorityObjectsQueryKeys,
  useAddEligibleAreaMutation,
  useAdministrativeAreasQuery,
  useEligibleAreasQuery,
  useRemoveEligibleAreaMutation,
} from "@/features/priority-objects/api";
import type { AdministrativeAreaSummary } from "@/features/priority-objects/types";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

type Filter = "all" | "active" | "inactive";

const FILTER_VALUES: Filter[] = ["active", "inactive", "all"];

function EligibleAreasBody({
  priorityObjectId,
  priorityObjectName,
  priorityObjectCode,
}: {
  priorityObjectId: string;
  priorityObjectName: string;
  priorityObjectCode: string;
}) {
  const client = useQueryClient();
  const { can } = useRbac();
  const canManage = can("ktx.priority_objects.areas.manage");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("active");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerSearch, setPickerSearch] = useState("");

  const areasQuery = useEligibleAreasQuery(priorityObjectId, {
    search,
    isActive: filter === "all" ? undefined : filter === "active",
    page,
    pageSize,
  });

  const adminAreasQuery = useAdministrativeAreasQuery({
    search: pickerSearch || undefined,
    page: 1,
    pageSize: 20,
  });

  const addMutation = useAddEligibleAreaMutation();
  const removeMutation = useRemoveEligibleAreaMutation();

  const totalPages = areasQuery.data?.totalPages ?? 1;
  const items = areasQuery.data?.items ?? [];
  const candidates = adminAreasQuery.data?.items ?? [];
  const totalCandidates = adminAreasQuery.data?.total ?? 0;

  const handleAdd = (area: AdministrativeAreaSummary) => {
    addMutation.mutate(
      { priorityObjectId, administrativeAreaId: area.id },
      {
        onSuccess: () => {
          toast.success(`Đã thêm địa bàn “${area.name}”.`);
          void client.invalidateQueries({
            queryKey: [
              ...priorityObjectsQueryKeys.all,
              "eligible-areas",
              priorityObjectId,
            ],
          });
        },
        onError: (error: unknown) =>
          toast.error(
            error instanceof Error ? error.message : "Không thể thêm địa bàn.",
          ),
      },
    );
  };

  const handleRemove = (
    area: { administrativeAreaId: string; name: string },
    hard: boolean,
  ) => {
    removeMutation.mutate(
      {
        priorityObjectId,
        administrativeAreaId: area.administrativeAreaId,
        hardDelete: hard,
      },
      {
        onSuccess: () => {
          toast.success(
            hard
              ? `Đã xóa cứng địa bàn “${area.name}”.`
              : `Đã ngừng áp dụng địa bàn “${area.name}”.`,
          );
        },
        onError: (error: unknown) =>
          toast.error(
            error instanceof Error
              ? error.message
              : "Không thể cập nhật địa bàn.",
          ),
      },
    );
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <DialogHeader>
        <DialogTitle>
          Địa bàn đủ điều kiện · {priorityObjectName}{" "}
          <span className="text-muted-foreground text-sm font-normal">
            ({priorityObjectCode})
          </span>
        </DialogTitle>
        <DialogDescription>
          Sinh viên phải có hộ khẩu/địa chỉ thường trú thuộc một trong các địa
          bàn dưới đây mới được áp dụng đối tượng.
        </DialogDescription>
      </DialogHeader>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-sm">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            placeholder="Tìm theo tên, mã hoặc tỉnh thành..."
            className="pl-9"
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-md border bg-muted/30 p-0.5 text-xs">
            {FILTER_VALUES.map((value) => (
              <button
                key={value}
                type="button"
                className={cn(
                  "rounded px-2.5 py-1 transition-colors",
                  filter === value
                    ? "bg-background shadow-xs"
                    : "text-muted-foreground hover:text-foreground",
                )}
                onClick={() => {
                  setFilter(value);
                  setPage(1);
                }}
              >
                {value === "active"
                  ? "Đang áp dụng"
                  : value === "inactive"
                    ? "Đã ngừng"
                    : "Tất cả"}
              </button>
            ))}
          </div>
          {canManage ? (
            <Button
              size="sm"
              onClick={() => setPickerOpen(true)}
              disabled={addMutation.isPending}
            >
              + Thêm địa bàn
            </Button>
          ) : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-x-auto rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40">
              <TableHead className="font-semibold text-xs uppercase tracking-wider">
                Mã
              </TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider">
                Tên địa bàn
              </TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider">
                Tỉnh/TP
              </TableHead>
              <TableHead className="font-semibold text-xs uppercase tracking-wider">
                Trạng thái
              </TableHead>
              <TableHead className="text-right font-semibold text-xs uppercase tracking-wider">
                Hành động
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {areasQuery.isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={`skeleton-row-${i}`}>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <TableCell key={`skeleton-cell-${i}-${j}`} className="py-3">
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center">
                  <p className="text-sm text-muted-foreground">
                    Chưa cấu hình địa bàn nào cho đối tượng này.
                  </p>
                </TableCell>
              </TableRow>
            ) : (
              items.map((row) => (
                <TableRow key={row.administrativeAreaId}>
                  <TableCell className="font-mono text-xs">
                    {row.externalCode}
                  </TableCell>
                  <TableCell>
                    <div className="font-medium">{row.name}</div>
                    {row.isWholeArea === false && row.specificVillages ? (
                      <div className="text-[11px] text-amber-600 dark:text-amber-400 font-normal">
                        Thôn/Ấp: {row.specificVillages}
                      </div>
                    ) : (
                      <div className="text-[11px] text-muted-foreground">
                        {row.divisionType} · Toàn xã
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    {row.provinceName ?? row.provinceCode ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={row.isActive ? "default" : "secondary"}>
                      {row.isActive ? "Đang áp dụng" : "Đã ngừng"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {canManage ? (
                      <TooltipProvider>
                        <div className="inline-flex items-center gap-1">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="size-8 text-amber-600 hover:bg-amber-50"
                                disabled={
                                  !row.isActive || removeMutation.isPending
                                }
                                onClick={() => handleRemove(row, false)}
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              Ngừng áp dụng địa bàn này (có thể kích hoạt lại)
                            </TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="size-8 text-destructive hover:bg-destructive/10"
                                disabled={removeMutation.isPending}
                                onClick={() => handleRemove(row, true)}
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              Xóa cứng khỏi đối tượng
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      </TooltipProvider>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <DialogFooter className="border-t pt-3">
        <div className="flex w-full items-center justify-between text-sm text-muted-foreground">
          <span>
            Trang {page}/{totalPages}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Trang trước
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Trang sau
            </Button>
          </div>
        </div>
      </DialogFooter>

      <Dialog
        open={pickerOpen}
        onOpenChange={(open) => {
          setPickerOpen(open);
          if (!open) setPickerSearch("");
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Thêm địa bàn</DialogTitle>
            <DialogDescription>
              Tìm theo tên, mã hoặc tỉnh/TP. Đã có sẵn {totalCandidates} đơn vị
              hành chính trong hệ thống.
            </DialogDescription>
          </DialogHeader>
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              autoFocus
              value={pickerSearch}
              onChange={(e) => setPickerSearch(e.target.value)}
              placeholder="Tìm theo tên xã/phường hoặc mã..."
              className="pl-9"
            />
          </div>
          <div className="max-h-80 overflow-y-auto rounded-md border">
            {adminAreasQuery.isLoading ? (
              <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Đang tải...
              </div>
            ) : candidates.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                Không tìm thấy địa bàn phù hợp.
              </p>
            ) : (
              <ul className="divide-y">
                {candidates.map((area) => (
                  <li
                    key={area.id}
                    className="flex items-center justify-between gap-2 px-3 py-2.5 hover:bg-muted/40"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {area.name}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {area.externalCode} ·{" "}
                        {area.provinceName ?? area.provinceCode ?? "—"}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={addMutation.isPending}
                      onClick={() => handleAdd(area)}
                    >
                      Thêm
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPickerOpen(false)}>
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export { EligibleAreasBody };

export function EligibleAreasDialog({
  priorityObjectId,
  priorityObjectName,
  priorityObjectCode,
  triggerLabel,
  triggerVariant,
  triggerSize,
  disabled,
}: {
  priorityObjectId: string;
  priorityObjectName: string;
  priorityObjectCode: string;
  triggerLabel: string;
  triggerVariant?: "outline" | "default" | "ghost" | "destructive";
  triggerSize?: "sm" | "default" | "lg" | "icon";
  disabled?: boolean;
}) {
  const [openDialog, setOpenDialog] = useState(false);
  return (
    <Dialog open={openDialog} onOpenChange={setOpenDialog}>
      <Button
        type="button"
        variant={triggerVariant ?? "outline"}
        size={triggerSize ?? "sm"}
        disabled={disabled}
        onClick={() => setOpenDialog(true)}
      >
        {triggerLabel}
      </Button>
      <DialogContent className="flex max-h-[min(720px,calc(100vh-2rem))] w-full max-w-3xl flex-col overflow-hidden">
        <EligibleAreasBody
          priorityObjectId={priorityObjectId}
          priorityObjectName={priorityObjectName}
          priorityObjectCode={priorityObjectCode}
        />
      </DialogContent>
    </Dialog>
  );
}
