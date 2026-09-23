import { useForm } from "@tanstack/react-form";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  CheckCircle2,
  Clock3,
  Download,
  Eye,
  FileCheck2,
  FileSpreadsheet,
  Info,
  ReceiptText,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { runtimeConfig } from "@/app/config/runtime";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
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
  exportPaymentSubmissionsToExcel,
  usePaymentSubmissionQuery,
  usePaymentSubmissionsQuery,
  usePaymentSubmissionsStatsQuery,
  useRejectPaymentSubmission,
  useVerifyPaymentSubmission,
} from "@/features/payments/api";
import {
  type PaymentSubmission,
  type PaymentSubmissionStatus,
  paymentSubmissionStatusLabels,
  paymentSubmissionStatusVariants,
} from "@/features/payments/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { getFormErrorMessage } from "@/lib/form-errors";
import { cn } from "@/lib/utils";

const money = (value: number) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);

const dateTime = (value?: string | null) =>
  value ? formatDateTimeValue(value) : "—";

const formatBytes = (value?: number | null) => {
  if (!value) return "Không rõ dung lượng";
  if (value < 1024 * 1024) return String(Math.ceil(value / 1024)) + " KB";
  return (value / (1024 * 1024)).toFixed(1) + " MB";
};

function StatusBadge({ status }: { status: PaymentSubmissionStatus }) {
  const Icon =
    status === "verified"
      ? CheckCircle2
      : status === "rejected"
        ? XCircle
        : status === "submitted"
          ? Clock3
          : FileCheck2;

  return (
    <Badge
      variant={paymentSubmissionStatusVariants[status]}
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold shrink-0"
    >
      <Icon className="size-3.5 shrink-0" />
      {paymentSubmissionStatusLabels[status]}
    </Badge>
  );
}

function ReviewDialog({
  submissionId,
  open,
  onOpenChange,
  canReview,
}: {
  submissionId?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  canReview: boolean;
}) {
  const detail = usePaymentSubmissionQuery(submissionId, open);
  const verify = useVerifyPaymentSubmission();
  const reject = useRejectPaymentSubmission();
  const [reviewMode, setReviewMode] = useState<"verify" | "reject">();
  const [reviewError, setReviewError] = useState<string>();
  const form = useForm({
    defaultValues: { reviewNote: "" },
    validators: {
      onSubmit: z.object({
        reviewNote: z.string().max(2000, "Ghi chú tối đa 2.000 ký tự."),
      }),
    },
    onSubmit: async ({ value }) => {
      if (!submissionId || !reviewMode) return;
      if (reviewMode === "reject" && !value.reviewNote.trim()) {
        setReviewError("Vui lòng nhập lý do từ chối.");
        return;
      }
      setReviewError(undefined);
      if (reviewMode === "reject") {
        await reject.mutateAsync({
          id: submissionId,
          reviewNote: value.reviewNote,
        });
        toast.success("Đã từ chối hồ sơ nộp thanh toán.");
      } else {
        await verify.mutateAsync({
          id: submissionId,
          reviewNote: value.reviewNote,
        });
        toast.success("Đã xác nhận thanh toán.");
      }
      form.reset();
      setReviewMode(undefined);
    },
  });

  useEffect(() => {
    form.reset();
    setReviewMode(undefined);
    setReviewError(undefined);
  }, [form, submissionId]);

  const submission = detail.data;
  const receiptUrl = submissionId
    ? runtimeConfig.apiBaseUrl +
      "/PaymentSubmissions/" +
      submissionId +
      "/receipt"
    : "";
  const isImage = submission?.receiptContentType?.startsWith("image/") ?? false;
  const isPdf = submission?.receiptContentType === "application/pdf";
  const mutationError = verify.error ?? reject.error;

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && !verify.isPending && !reject.isPending) {
          setReviewMode(undefined);
          form.reset();
        }
        onOpenChange(nextOpen);
      }}
    >
      <ResponsiveDialogContent className="max-w-4xl">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>Hồ sơ nộp thanh toán</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Kiểm tra thông tin chuyển khoản và biên lai trước khi xác nhận.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        {detail.isLoading ? (
          <div className="grid gap-3">
            <Skeleton className="h-20" />
            <Skeleton className="h-52" />
            <Skeleton className="h-28" />
          </div>
        ) : detail.isError || !submission ? (
          <Alert variant="destructive">
            <Info />
            <div>
              <AlertTitle>Không thể tải hồ sơ</AlertTitle>
              <AlertDescription>
                {detail.error instanceof Error
                  ? detail.error.message
                  : "Vui lòng đóng cửa sổ và thử lại."}
              </AlertDescription>
            </div>
          </Alert>
        ) : (
          <div className="grid max-h-[calc(100dvh-12rem)] gap-5 overflow-y-auto pr-1">
            <div className="grid gap-4 rounded-md border p-4 sm:grid-cols-2">
              <div>
                <p className="type-supporting text-muted-foreground">
                  Sinh viên
                </p>
                <p className="mt-1 font-semibold">{submission.studentName}</p>
                <p className="text-sm text-muted-foreground">
                  {submission.studentCode}
                </p>
              </div>
              <div className="sm:text-right">
                <p className="type-supporting text-muted-foreground">
                  Trạng thái
                </p>
                <div className="mt-1 sm:flex sm:justify-end">
                  <StatusBadge status={submission.status} />
                </div>
              </div>
              <div>
                <p className="type-supporting text-muted-foreground">Hóa đơn</p>
                <p className="mt-1 font-medium">{submission.invoiceCode}</p>
              </div>
              <div className="sm:text-right">
                <p className="type-supporting text-muted-foreground">
                  Số tiền trong hồ sơ
                </p>
                <p className="mt-1 font-semibold">{money(submission.amount)}</p>
              </div>
            </div>

            <div className="grid gap-3 rounded-md border p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">Biên lai thanh toán</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {submission.receiptFileName} ·{" "}
                    {formatBytes(submission.receiptSizeBytes)}
                  </p>
                </div>
                <Button variant="outline" size="sm" className="gap-1.5" asChild>
                  <a href={receiptUrl} target="_blank" rel="noreferrer">
                    <Download className="size-3.5" />
                    Mở biên lai
                  </a>
                </Button>
              </div>
              {isImage ? (
                <div className="flex min-h-48 items-center justify-center rounded-md border bg-muted/20 p-3">
                  <img
                    src={receiptUrl}
                    alt={"Biên lai của " + submission.studentName}
                    className="max-h-[28rem] max-w-full rounded-md object-contain"
                  />
                </div>
              ) : isPdf ? (
                <iframe
                  src={receiptUrl}
                  title="Xem biên lai PDF"
                  className="h-[28rem] w-full rounded-md border bg-muted/20"
                />
              ) : (
                <div className="flex min-h-32 items-center justify-center rounded-md border bg-muted/20 text-sm text-muted-foreground">
                  Không thể xem trước tệp này. Hãy mở biên lai trong cửa sổ mới.
                </div>
              )}
            </div>

            <div className="grid gap-3 rounded-md border p-4 sm:grid-cols-2">
              <div>
                <p className="type-supporting text-muted-foreground">
                  Phương thức
                </p>
                <p className="mt-1 font-medium">Chuyển khoản</p>
              </div>
              <div>
                <p className="type-supporting text-muted-foreground">
                  Thời điểm nộp
                </p>
                <p className="mt-1 font-medium">
                  {dateTime(submission.submittedAt)}
                </p>
              </div>
              <div className="sm:col-span-2">
                <p className="type-supporting text-muted-foreground">
                  Nội dung chuyển khoản
                </p>
                <code className="mt-1 block break-all rounded-md bg-muted/40 px-2 py-1.5 text-sm">
                  {submission.transferContent || "—"}
                </code>
              </div>
              {submission.referenceNo ? (
                <div>
                  <p className="type-supporting text-muted-foreground">
                    Mã tham chiếu
                  </p>
                  <p className="mt-1 font-medium">{submission.referenceNo}</p>
                </div>
              ) : null}
              {submission.reviewedAt ? (
                <div>
                  <p className="type-supporting text-muted-foreground">
                    Thời điểm xử lý
                  </p>
                  <p className="mt-1 font-medium">
                    {dateTime(submission.reviewedAt)}
                  </p>
                </div>
              ) : null}
              {submission.reviewNote ? (
                <div className="sm:col-span-2">
                  <p className="type-supporting text-muted-foreground">
                    Ghi chú xử lý
                  </p>
                  <p className="mt-1 text-sm">{submission.reviewNote}</p>
                </div>
              ) : null}
            </div>

            {canReview && submission.status === "submitted" ? (
              <div className="grid gap-3 rounded-md border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-start gap-2">
                  <FileCheck2 className="mt-0.5 size-4 shrink-0 text-primary" />
                  <div>
                    <p className="font-semibold">Xử lý hồ sơ</p>
                    <p className="text-sm text-muted-foreground">
                      Chỉ xác nhận khi số tiền và nội dung chuyển khoản khớp với
                      chứng từ thực tế.
                    </p>
                  </div>
                </div>
                {reviewMode ? (
                  <form
                    className="grid gap-3"
                    onSubmit={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      void form.handleSubmit();
                    }}
                  >
                    <form.Field name="reviewNote">
                      {(field) => (
                        <div className="grid gap-1.5">
                          <Label htmlFor="payment-review-note">
                            {reviewMode === "reject"
                              ? "Lý do từ chối"
                              : "Ghi chú đối soát (không bắt buộc)"}
                          </Label>
                          <Textarea
                            id="payment-review-note"
                            value={field.state.value}
                            disabled={verify.isPending || reject.isPending}
                            placeholder={
                              reviewMode === "reject"
                                ? "Ví dụ: Ảnh biên lai không rõ số tiền..."
                                : "Ghi chú thêm cho hồ sơ nếu cần..."
                            }
                            onChange={(event) => {
                              setReviewError(undefined);
                              field.handleChange(event.target.value);
                            }}
                          />
                          {reviewError ||
                          getFormErrorMessage(field.state.meta.errors) ? (
                            <p
                              className="text-sm text-destructive"
                              role="alert"
                            >
                              {reviewError ||
                                getFormErrorMessage(field.state.meta.errors)}
                            </p>
                          ) : null}
                        </div>
                      )}
                    </form.Field>
                    {mutationError ? (
                      <p className="text-sm text-destructive" role="alert">
                        {mutationError instanceof Error
                          ? mutationError.message
                          : "Không thể xử lý hồ sơ. Vui lòng thử lại."}
                      </p>
                    ) : null}
                    <div className="flex flex-wrap justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        disabled={verify.isPending || reject.isPending}
                        onClick={() => {
                          setReviewMode(undefined);
                          setReviewError(undefined);
                          form.reset();
                        }}
                      >
                        Hủy
                      </Button>
                      <Button
                        type="submit"
                        variant={
                          reviewMode === "reject" ? "destructive" : "default"
                        }
                        disabled={verify.isPending || reject.isPending}
                      >
                        {verify.isPending || reject.isPending
                          ? "Đang xử lý..."
                          : reviewMode === "reject"
                            ? "Xác nhận từ chối"
                            : "Xác nhận thanh toán"}
                      </Button>
                    </div>
                  </form>
                ) : (
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        form.reset();
                        setReviewError(undefined);
                        setReviewMode("reject");
                      }}
                    >
                      <XCircle />
                      Từ chối
                    </Button>
                    <Button
                      onClick={() => {
                        form.reset();
                        setReviewError(undefined);
                        setReviewMode("verify");
                      }}
                    >
                      <CheckCircle2 />
                      Xác nhận thanh toán
                    </Button>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        )}

        <ResponsiveDialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Đóng
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

export function PaymentSubmissionsPage({
  search,
  onSearch,
  canVerify,
}: {
  search: {
    q: string;
    status?: PaymentSubmissionStatus;
    page: number;
    pageSize: number;
  };
  onSearch: (changes: Partial<typeof search>) => void;
  canVerify: boolean;
}) {
  const query = usePaymentSubmissionsQuery({
    search: search.q.trim() || undefined,
    status: search.status,
    page: search.page,
    pageSize: search.pageSize,
  });
  const statsQuery = usePaymentSubmissionsStatsQuery({
    search: search.q.trim() || undefined,
  });
  const [selectedId, setSelectedId] = useState<string>();
  const [isExporting, setIsExporting] = useState(false);
  const items = query.data?.items ?? [];

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      await exportPaymentSubmissionsToExcel({
        status: search.status,
        search: search.q.trim() || undefined,
      });
      toast.success("Xuất file Excel đối soát thanh toán thành công!");
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
  const columns = useMemo<ColumnDef<PaymentSubmission>[]>(
    () => [
      {
        accessorKey: "student",
        header: "Sinh viên",
        cell: ({ row }) => (
          <div>
            <p className="font-medium">{row.original.studentName}</p>
            <p className="type-supporting text-muted-foreground">
              {row.original.studentCode}
            </p>
          </div>
        ),
      },
      {
        accessorKey: "invoiceCode",
        header: "Hóa đơn",
        cell: ({ row }) => (
          <span className="font-medium">{row.original.invoiceCode}</span>
        ),
      },
      {
        accessorKey: "amount",
        header: () => <span className="block text-right">Số tiền</span>,
        cell: ({ row }) => (
          <span className="block text-right font-medium">
            {money(row.original.amount)}
          </span>
        ),
      },
      {
        accessorKey: "submittedAt",
        header: "Ngày nộp",
        cell: ({ row }) => (
          <span className="type-supporting">
            {dateTime(row.original.submittedAt)}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Trạng thái",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => setSelectedId(row.original.id)}
            >
              <Eye className="size-3.5" />
              Xem
            </Button>
          </div>
        ),
      },
    ],
    [],
  );

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Chờ xác nhận"
          value={statsQuery.data?.submitted ?? 0}
          icon={Clock3}
          variant="amber"
          isActive={search.status === "submitted"}
          onClick={() =>
            onSearch({
              status: search.status === "submitted" ? undefined : "submitted",
              page: 1,
            })
          }
        />
        <MetricCard
          title="Đã xác nhận"
          value={statsQuery.data?.verified ?? 0}
          icon={CheckCircle2}
          variant="emerald"
          isActive={search.status === "verified"}
          onClick={() =>
            onSearch({
              status: search.status === "verified" ? undefined : "verified",
              page: 1,
            })
          }
        />
        <MetricCard
          title="Cần nộp lại"
          value={statsQuery.data?.rejected ?? 0}
          icon={XCircle}
          variant="rose"
          isActive={search.status === "rejected"}
          onClick={() =>
            onSearch({
              status: search.status === "rejected" ? undefined : "rejected",
              page: 1,
            })
          }
        />
        <MetricCard
          title="Tổng hồ sơ"
          value={statsQuery.data?.total ?? query.data?.total ?? 0}
          icon={ReceiptText}
          variant="slate"
          isActive={!search.status}
          onClick={() => onSearch({ status: undefined, page: 1 })}
        />
      </div>

      <Card>
        <CardHeader className="gap-1">
          <CardTitle>Danh sách nộp thanh toán</CardTitle>
          <CardDescription>
            Kiểm tra biên lai sinh viên đã nộp và cập nhật trạng thái đối soát.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="w-full lg:max-w-md">
              <DebouncedSearchInput
                value={search.q}
                placeholder="Tìm mã sinh viên, tên hoặc mã hóa đơn..."
                onChange={(val) => onSearch({ q: val, page: 1 })}
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Select
                value={search.status ?? "all"}
                onValueChange={(value) =>
                  onSearch({
                    status:
                      value === "all"
                        ? undefined
                        : (value as PaymentSubmissionStatus),
                    page: 1,
                  })
                }
              >
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Tất cả trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tất cả trạng thái</SelectItem>
                  <SelectItem value="submitted">Chờ xác nhận</SelectItem>
                  <SelectItem value="verified">Đã xác nhận</SelectItem>
                  <SelectItem value="rejected">Từ chối</SelectItem>
                  <SelectItem value="cancelled">Đã hủy</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                size="sm"
                className="gap-2 shrink-0 border-emerald-600/30 text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-950/30"
                disabled={isExporting}
                onClick={handleExportExcel}
              >
                <FileSpreadsheet className="size-4 text-emerald-600 dark:text-emerald-400" />
                {isExporting ? "Đang xuất..." : "Xuất Excel"}
              </Button>
            </div>
          </div>

          {query.isError ? (
            <Alert variant="destructive">
              <Info />
              <div>
                <AlertTitle>Không thể tải danh sách nộp thanh toán</AlertTitle>
                <AlertDescription>
                  {query.error instanceof Error
                    ? query.error.message
                    : "Vui lòng thử lại."}
                </AlertDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="ml-auto shrink-0"
                onClick={() => void query.refetch()}
              >
                <RefreshCw />
                Thử lại
              </Button>
            </Alert>
          ) : query.isLoading ? (
            <div className="grid gap-2">
              {Array.from({ length: 5 }, (_, index) => (
                <Skeleton key={index} className="h-14" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <DataTableEmpty
              title={
                search.q || search.status
                  ? "Không tìm thấy hồ sơ phù hợp"
                  : "Chưa có hồ sơ nộp thanh toán"
              }
              description={
                search.q || search.status
                  ? "Thử thay đổi từ khóa hoặc bộ lọc."
                  : "Hồ sơ sẽ xuất hiện sau khi sinh viên nộp biên lai."
              }
              action={
                search.q || search.status
                  ? {
                      label: "Xóa bộ lọc",
                      onClick: () =>
                        onSearch({ q: "", status: undefined, page: 1 }),
                    }
                  : undefined
              }
            />
          ) : (
            <div className="grid gap-3">
              <div className="overflow-x-auto rounded-md border">
                <Table>
                  <TableHeader className="bg-muted/30">
                    {table.getHeaderGroups().map((headerGroup) => (
                      <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                          <TableHead key={header.id}>
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
                    {table.getRowModel().rows.map((row) => (
                      <TableRow key={row.id}>
                        {row.getVisibleCells().map((cell) => (
                          <TableCell key={cell.id}>
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext(),
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {query.data ? (
                <DataTablePagination
                  page={query.data.page}
                  pageSize={query.data.pageSize}
                  pageCount={query.data.totalPages}
                  onPageChange={(page) => onSearch({ page })}
                  onPageSizeChange={(pageSize) =>
                    onSearch({ page: 1, pageSize })
                  }
                />
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>

      <ReviewDialog
        submissionId={selectedId}
        open={Boolean(selectedId)}
        onOpenChange={(open) => {
          if (!open) setSelectedId(undefined);
        }}
        canReview={canVerify}
      />
    </>
  );
}

function MetricCard({
  title,
  value,
  icon: Icon,
  variant,
  isActive,
  onClick,
}: {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  variant: "amber" | "emerald" | "rose" | "slate";
  isActive?: boolean;
  onClick?: () => void;
}) {
  const variantStyles = {
    amber: {
      border: isActive
        ? "border-amber-500 ring-2 ring-amber-500/20 bg-amber-50/50 dark:bg-amber-950/20"
        : "hover:border-amber-400/80",
      iconBg:
        "bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300",
    },
    emerald: {
      border: isActive
        ? "border-emerald-500 ring-2 ring-emerald-500/20 bg-emerald-50/50 dark:bg-emerald-950/20"
        : "hover:border-emerald-400/80",
      iconBg:
        "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300",
    },
    rose: {
      border: isActive
        ? "border-rose-500 ring-2 ring-rose-500/20 bg-rose-50/50 dark:bg-rose-950/20"
        : "hover:border-rose-400/80",
      iconBg:
        "bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300",
    },
    slate: {
      border: isActive
        ? "border-primary ring-2 ring-primary/20 bg-muted/40"
        : "hover:border-border",
      iconBg: "bg-muted text-muted-foreground",
    },
  };

  const style = variantStyles[variant];

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      className={cn(
        "cursor-pointer transition-all duration-200 hover:shadow-md select-none",
        style.border,
      )}
    >
      <CardContent className="p-4 flex items-center justify-between">
        <div>
          <p className="type-supporting text-muted-foreground font-medium">
            {title}
          </p>
          <p className="mt-1 text-2xl font-bold tabular-nums tracking-tight">
            {value}
          </p>
        </div>
        <div className={cn("p-2.5 rounded-lg shrink-0", style.iconBg)}>
          <Icon className="size-5" />
        </div>
      </CardContent>
    </Card>
  );
}
