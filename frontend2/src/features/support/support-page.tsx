import { useForm } from "@tanstack/react-form";
import { useNavigate } from "@tanstack/react-router";
import {
  CheckCircle2,
  CircleHelp,
  Clock,
  Eye,
  Inbox,
  LoaderCircle,
  MessageSquare,
  MoreHorizontal,
  Plus,
  RefreshCw,
  RotateCcw,
  UserRound,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
import { AccessDenied } from "@/components/admin/access-denied";
import { Combobox } from "@/components/admin/combobox";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { EmptyState } from "@/components/admin/empty-state";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
import { KpiMetric } from "@/components/admin/kpi-metric";
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
import { Card, CardContent } from "@/components/ui/card";
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
import { Textarea } from "@/components/ui/textarea";
import { useStudentsQuery } from "@/features/students/api";
import {
  useCreateSupportRequest,
  useSupportQuery,
} from "@/features/support/api";
import {
  type SupportRequestType,
  type SupportStatus,
  supportStatusLabels as statusLabels,
  supportStatusVariants as statusVariants,
  supportTypeLabels as typeLabels,
} from "@/features/support/types";
import { formatDateTime } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

export const supportStatuses = [
  "submitted",
  "processing",
  "resolved",
  "rejected",
  "cancelled",
] as const;
export const supportRequestTypes = [
  "change_room",
  "extend",
  "check_out",
  "other",
] as const;

export type SupportSearch = {
  q: string | number;
  status?: SupportStatus;
  type?: SupportRequestType;
  page: number;
  pageSize: number;
};

const statusDotColors: Record<SupportStatus, string> = {
  submitted: "bg-amber-500",
  processing: "bg-blue-500",
  resolved: "bg-emerald-500",
  rejected: "bg-red-500",
  cancelled: "bg-muted-foreground/60",
};

export function SupportPage({
  search,
  onSearchChange,
}: {
  search: SupportSearch;
  onSearchChange: (changes: Partial<SupportSearch>) => void;
}) {
  const navigate = useNavigate();
  const { can } = useRbac();
  const canView = can("ktx.support.view");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());

  const query = useSupportQuery(
    {
      search: String(search.q).trim() || undefined,
      status: search.status,
      requestType: search.type,
      page: search.page,
      pageSize: search.pageSize,
    },
    { enabled: canView },
  );

  const items = query.data?.items ?? [];

  // Summary Metrics
  const summary = useMemo(() => {
    const total = query.data?.total ?? items.length;
    const pending = items.filter(
      (r) => r.status === "submitted" || r.status === "processing",
    ).length;
    const resolved = items.filter((r) => r.status === "resolved").length;
    return { total, pending, resolved };
  }, [items, query.data?.total]);

  // Options for filters
  const statusOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả trạng thái" },
      ...supportStatuses.map((s) => ({ value: s, label: statusLabels[s] })),
    ],
    [],
  );

  const typeOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả loại yêu cầu" },
      ...supportRequestTypes.map((t) => ({ value: t, label: typeLabels[t] })),
    ],
    [],
  );

  const hasFilters = Boolean(
    String(search.q).trim() || search.status || search.type,
  );

  const resetFilters = () => {
    onSearchChange({
      q: "",
      status: undefined,
      type: undefined,
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

  if (!canView) return <AccessDenied />;

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="TIẾP NHẬN / SINH VIÊN"
        title="Yêu cầu hỗ trợ"
        description="Tiếp nhận, trao đổi và theo dõi tiến độ xử lý các yêu cầu từ sinh viên."
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
            {can("ktx.support.create") ? (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setCreateOpen(true)}
              >
                <Plus className="size-3.5" />
                <span>Tạo yêu cầu</span>
              </Button>
            ) : null}
          </div>
        }
      />

      {/* 2. KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Inbox}
            label="Tổng yêu cầu"
            value={summary.total.toLocaleString("vi-VN")}
            helper="Tổng số yêu cầu sinh viên đã gửi"
          />
          <KpiMetric
            icon={Clock}
            label="Đang xử lý / Chờ tiếp nhận"
            value={summary.pending.toLocaleString("vi-VN")}
            helper="Yêu cầu cần ban quản lý hỗ trợ xử lý"
          />
          <KpiMetric
            icon={CheckCircle2}
            label="Đã hoàn thành"
            value={summary.resolved.toLocaleString("vi-VN")}
            trend="positive"
            helper="Yêu cầu đã được giải quyết thỏa đáng"
          />
        </CardContent>
      </Card>

      {/* 3. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="w-full lg:w-80">
          <DebouncedSearchInput
            className="text-xs"
            value={String(search.q || "")}
            placeholder="Tìm theo tiêu đề, nội dung hoặc mã sinh viên..."
            aria-label="Tìm yêu cầu hỗ trợ"
            onChange={(val) => onSearchChange({ q: val, page: 1 })}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          {/* Trạng thái */}
          <Combobox
            className="w-full sm:w-48 text-xs"
            options={statusOptions}
            value={search.status ?? "all"}
            searchPlaceholder="Tìm trạng thái..."
            onValueChange={(value) =>
              onSearchChange({
                status: value === "all" ? undefined : (value as SupportStatus),
                page: 1,
              })
            }
          />

          {/* Loại yêu cầu */}
          <Combobox
            className="w-full sm:w-48 text-xs"
            options={typeOptions}
            value={search.type ?? "all"}
            searchPlaceholder="Tìm loại yêu cầu..."
            onValueChange={(value) =>
              onSearchChange({
                type:
                  value === "all" ? undefined : (value as SupportRequestType),
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
                    aria-label="Chọn tất cả yêu cầu"
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
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[280px]">
                Yêu cầu
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[180px]">
                Sinh viên
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[150px]">
                Loại yêu cầu
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[150px]">
                Trạng thái
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[160px]">
                Cập nhật
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[110px] text-center">
                Trao đổi
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
                    <LoaderCircle className="size-4 animate-spin" />
                    <span>Đang tải danh sách yêu cầu hỗ trợ...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : query.isError ? (
              <TableRow>
                <TableCell colSpan={8} className="p-8">
                  <EmptyState
                    icon={CircleHelp}
                    title="Không thể tải yêu cầu hỗ trợ"
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
                <TableCell colSpan={8} className="p-8">
                  <EmptyState
                    icon={CircleHelp}
                    title={
                      hasFilters
                        ? "Không có yêu cầu phù hợp"
                        : "Chưa có yêu cầu nào"
                    }
                    description={
                      hasFilters
                        ? "Không tìm thấy yêu cầu hỗ trợ nào phù hợp với bộ lọc hiện tại."
                        : "Các yêu cầu cần trợ giúp từ sinh viên ký túc xá sẽ xuất hiện tại đây."
                    }
                    action={
                      hasFilters
                        ? { label: "Xóa bộ lọc", onClick: resetFilters }
                        : can("ktx.support.create")
                          ? {
                              label: "Tạo yêu cầu đầu tiên",
                              onClick: () => setCreateOpen(true),
                            }
                          : undefined
                    }
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((request) => (
                <TableRow
                  key={request.id}
                  className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                  onClick={() =>
                    void navigate({
                      to: "/support/$supportRequestId",
                      params: { supportRequestId: request.id },
                    })
                  }
                >
                  <TableCell
                    className="pl-3"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <div className="flex items-center pl-1">
                      <Checkbox
                        aria-label={`Chọn yêu cầu ${request.title}`}
                        checked={selectedIds.has(request.id)}
                        onCheckedChange={(val) =>
                          toggleSelect(request.id, Boolean(val))
                        }
                      />
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-semibold text-foreground text-sm max-w-sm truncate">
                      {request.title}
                    </div>
                    <div className="type-supporting text-muted-foreground text-xs line-clamp-1 max-w-sm truncate">
                      {request.content}
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-medium text-foreground text-sm">
                      {request.studentName}
                    </div>
                    <div className="type-supporting text-muted-foreground font-mono text-xs">
                      {request.studentCode}
                    </div>
                  </TableCell>

                  <TableCell>
                    <Badge variant="secondary" className="text-xs font-normal">
                      {typeLabels[request.requestType]}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant={statusVariants[request.status]}
                      className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
                    >
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          statusDotColors[request.status],
                        )}
                      />
                      {statusLabels[request.status]}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    <span className="text-xs text-muted-foreground font-mono">
                      {formatDateTime(new Date(request.created))}
                    </span>
                  </TableCell>

                  <TableCell className="text-center">
                    <span className="inline-flex items-center gap-1 font-mono font-semibold tabular-nums text-xs bg-muted/60 px-2 py-0.5 rounded-md">
                      <MessageSquare className="size-3 text-muted-foreground" />
                      {request.commentCount}
                    </span>
                  </TableCell>

                  <TableCell onClick={(event) => event.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="size-8 text-muted-foreground hover:text-foreground"
                          aria-label={`Thao tác với yêu cầu ${request.title}`}
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
                              to: "/support/$supportRequestId",
                              params: { supportRequestId: request.id },
                            });
                          }}
                        >
                          <Eye className="size-4 mr-2 text-muted-foreground" />
                          Xem chi tiết
                        </DropdownMenuItem>
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
          page={query.data.page}
          pageSize={query.data.pageSize}
          pageCount={Math.max(query.data.totalPages, 1)}
          total={query.data.total}
          onPageChange={(page) => onSearchChange({ page })}
          onPageSizeChange={(pageSize) => onSearchChange({ pageSize, page: 1 })}
        />
      ) : null}

      {/* 6. Bulk Actions Floating Bar */}
      <DataTableBulkActions
        selectedCount={selectedIds.size}
        selectedLabel="yêu cầu"
        onClear={() => setSelectedIds(new Set())}
      />

      {/* 7. Create Support Dialog */}
      <CreateSupportDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}

type SupportFormValues = {
  studentId: string;
  requestType: SupportRequestType;
  title: string;
  content: string;
};

const supportFormSchema = z.object({
  studentId: z.string(),
  requestType: z.enum(supportRequestTypes),
  title: z
    .string()
    .trim()
    .min(1, "Tiêu đề là bắt buộc.")
    .max(255, "Tiêu đề tối đa 255 ký tự."),
  content: z
    .string()
    .trim()
    .min(1, "Nội dung là bắt buộc.")
    .max(4000, "Nội dung tối đa 4.000 ký tự."),
});

function firstError(errors: unknown[]) {
  const error = errors[0];
  return error ? String(error) : undefined;
}

function CreateSupportDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { can } = useRbac();
  const canManage = can("ktx.support.process");
  const create = useCreateSupportRequest();
  const [studentSearch, setStudentSearch] = useState("");
  const students = useStudentsQuery(
    { search: studentSearch.trim() || undefined, page: 1, pageSize: 20 },
    { enabled: open && canManage },
  );
  const form = useForm({
    defaultValues: {
      studentId: "",
      requestType: "other" as SupportRequestType,
      title: "",
      content: "",
    } satisfies SupportFormValues,
    validators: { onSubmit: supportFormSchema },
    onSubmit: async ({ value }) => {
      try {
        await create.mutateAsync({
          studentId: value.studentId || undefined,
          requestType: value.requestType,
          title: value.title.trim(),
          content: value.content.trim(),
        });
        form.reset();
        setStudentSearch("");
        onOpenChange(false);
        toast.success("Đã tạo yêu cầu hỗ trợ.");
      } catch (error) {
        toast.error(
          error instanceof ApiError ? error.message : "Không thể tạo yêu cầu.",
        );
      }
    },
  });

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(720px,calc(100dvh-1rem))] w-full max-w-xl flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>Tạo yêu cầu hỗ trợ</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Gửi yêu cầu để bộ phận KTX tiếp nhận và cập nhật tiến độ xử lý.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <form
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          <div className="grid gap-5 px-1 py-4 sm:px-2">
            {canManage ? (
              <form.Field name="studentId">
                {(field) => (
                  <Field>
                    <FieldLabel htmlFor="support-student-search">
                      Sinh viên cần hỗ trợ
                    </FieldLabel>
                    <Input
                      id="support-student-search"
                      value={studentSearch}
                      onChange={(event) => setStudentSearch(event.target.value)}
                      placeholder="Tìm theo mã hoặc tên sinh viên..."
                    />
                    <FieldDescription>
                      Chọn sinh viên khi tạo yêu cầu thay mặt; nếu không chọn,
                      hệ thống dùng hồ sơ của tài khoản hiện tại.
                    </FieldDescription>
                    <div className="max-h-40 overflow-y-auto rounded-md border">
                      {students.isLoading ? (
                        <div className="p-3 text-sm text-muted-foreground">
                          Đang tìm sinh viên...
                        </div>
                      ) : students.data?.items.length ? (
                        students.data.items.map((student) => (
                          <button
                            type="button"
                            key={student.id}
                            className={`flex w-full items-center gap-3 border-b px-3 py-2 text-left text-sm last:border-0 hover:bg-muted/40 ${field.state.value === student.id ? "bg-primary/[0.06]" : ""}`}
                            onClick={() => field.handleChange(student.id)}
                          >
                            <UserRound className="size-4 shrink-0 text-muted-foreground" />
                            <span className="min-w-0 flex-1">
                              <span className="block truncate font-medium">
                                {student.fullName}
                              </span>
                              <span className="block text-xs text-muted-foreground">
                                {student.studentCode}
                              </span>
                            </span>
                          </button>
                        ))
                      ) : (
                        <div className="p-3 text-sm text-muted-foreground">
                          Nhập từ khóa để tìm sinh viên.
                        </div>
                      )}
                    </div>
                  </Field>
                )}
              </form.Field>
            ) : null}
            <form.Field name="requestType">
              {(field) => (
                <Field>
                  <FieldLabel>Loại yêu cầu</FieldLabel>
                  <Select
                    value={field.state.value}
                    onValueChange={(value) =>
                      field.handleChange(value as SupportRequestType)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {supportRequestTypes.map((type) => (
                        <SelectItem key={type} value={type}>
                          {typeLabels[type]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </form.Field>
            <form.Field name="title">
              {(field) => {
                const error = firstError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="support-title">Tiêu đề</FieldLabel>
                    <Input
                      id="support-title"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                      placeholder="Ví dụ: Xin đổi phòng vì lý do sức khỏe"
                    />
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>
            <form.Field name="content">
              {(field) => {
                const error = firstError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="support-content">Nội dung</FieldLabel>
                    <Textarea
                      id="support-content"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                      placeholder="Mô tả rõ vấn đề hoặc nhu cầu của bạn..."
                      className="min-h-32"
                      maxLength={4000}
                    />
                    <FieldDescription>Tối đa 4.000 ký tự.</FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>
          </div>
          <ResponsiveDialogFooter className="border-t px-1 pt-4 sm:px-2">
            <Button
              type="button"
              variant="outline"
              disabled={create.isPending}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, isSubmitting]) => (
                <Button
                  type="submit"
                  disabled={!canSubmit || isSubmitting || create.isPending}
                >
                  {create.isPending ? "Đang gửi..." : "Gửi yêu cầu"}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
