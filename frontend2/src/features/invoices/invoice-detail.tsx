import { useForm } from "@tanstack/react-form";
import { useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  Ban,
  Check,
  CreditCard,
  Download,
  Eye,
  FileCheck2,
  FileText,
  Receipt,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { runtimeConfig } from "@/app/config/runtime";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
import { NoteConfirmDialog } from "@/components/admin/note-confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreatePayment,
  useDeleteInvoice,
  useInvoicePaymentsQuery,
  useInvoiceQuery,
  useVoidPayment,
} from "@/features/invoices/api";
import { money } from "@/features/invoices/invoices-page";
import {
  invoiceStatusLabels,
  invoiceStatusVariants,
  type PaymentMethod,
} from "@/features/invoices/types";
import {
  usePaymentSubmissionsQuery,
  useRejectPaymentSubmission,
  useVerifyPaymentSubmission,
} from "@/features/payments/api";
import {
  type PaymentSubmissionStatus,
  paymentSubmissionStatusLabels,
  paymentSubmissionStatusVariants,
} from "@/features/payments/types";
import { formatDateTimeValue, formatDateValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

const paymentFormSchema = z.object({
  amount: z.number().positive("Số tiền phải lớn hơn 0."),
  paymentMethod: z.enum(["cash", "bank_transfer", "other"]),
  referenceNo: z.string().max(100, "Mã tham chiếu tối đa 100 ký tự."),
  note: z.string().max(2000, "Ghi chú tối đa 2.000 ký tự."),
});

const overpaymentMessage = "Số tiền không được vượt quá số tiền còn nợ.";

const vndInputFormatter = new Intl.NumberFormat("vi-VN");

function formatVndInput(value: number) {
  return vndInputFormatter.format(value);
}

function parseVndInput(raw: string) {
  const digits = raw.replace(/\D/g, "");
  if (!digits) return 0;
  return Number(digits);
}

function firstError(errors: unknown[]): string | undefined {
  if (!errors.length) return undefined;
  const first = errors[0];
  if (typeof first === "string") return first;
  if (first && typeof first === "object" && "message" in first) {
    return String((first as { message: unknown }).message);
  }
  return undefined;
}

export function InvoiceDetailPage({
  invoiceId,
  canPay,
  canVoid,
  canViewSubmissions,
  canVerifySubmission,
}: {
  invoiceId: string;
  canPay: boolean;
  canVoid: boolean;
  canViewSubmissions: boolean;
  canVerifySubmission: boolean;
}) {
  const invoice = useInvoiceQuery(invoiceId);
  const payments = useInvoicePaymentsQuery(invoiceId);
  const submissions = usePaymentSubmissionsQuery(
    { invoiceId, page: 1, pageSize: 20 },
    canViewSubmissions,
  );
  const createPayment = useCreatePayment();
  const voidPayment = useVoidPayment();
  const deleteInvoice = useDeleteInvoice();
  const navigate = useNavigate();
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const verifySubmission = useVerifyPaymentSubmission();
  const rejectSubmission = useRejectPaymentSubmission();
  const [paymentError, setPaymentError] = useState<string>();
  const [voidTarget, setVoidTarget] = useState<string>();
  const [verifyTarget, setVerifyTarget] = useState<string>();
  const [rejectTarget, setRejectTarget] = useState<string>();
  const [previewSubmissionId, setPreviewSubmissionId] = useState<string>();
  const [activeTab, setActiveTab] = useState("lines");
  const [useManualForm, setUseManualForm] = useState(false);

  const pendingSubmission = submissions.data?.items.find(
    (s) => s.status === "submitted",
  );

  const remainingAmount = invoice.data?.remainingAmount ?? 0;
  const isFullyPaid = remainingAmount <= 0;
  const paidPercent =
    invoice.data && invoice.data.totalAmount > 0
      ? Math.round((invoice.data.paidAmount / invoice.data.totalAmount) * 100)
      : 0;

  const paymentForm = useForm({
    defaultValues: {
      amount: 0,
      paymentMethod: "cash" as PaymentMethod,
      referenceNo: "",
      note: "",
    },
    validators: { onSubmit: paymentFormSchema },
    onSubmit: async ({ value }) => {
      setPaymentError(undefined);
      if (value.amount > remainingAmount) {
        setPaymentError(overpaymentMessage);
        return;
      }
      await createPayment.mutateAsync({
        invoiceId,
        amount: value.amount,
        paymentMethod: value.paymentMethod,
        referenceNo: value.referenceNo.trim() || undefined,
        note: value.note.trim() || undefined,
      });
      paymentForm.reset();
      paymentForm.setFieldValue("amount", remainingAmount);
    },
  });

  useEffect(() => {
    if (invoice.data && paymentForm.state.values.amount === 0) {
      paymentForm.setFieldValue("amount", invoice.data.remainingAmount);
    }
  }, [invoice.data, paymentForm]);

  if (invoice.isLoading) {
    return (
      <div className="mx-auto w-full max-w-[1280px] space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (invoice.isError || !invoice.data) {
    return (
      <div className="mx-auto w-full max-w-[1280px] rounded-lg border border-dashed p-8 text-center">
        <p className="text-sm">Không thể tải chi tiết hóa đơn.</p>
        <Button
          className="mt-3"
          variant="outline"
          size="sm"
          onClick={() => void invoice.refetch()}
        >
          Thử lại
        </Button>
      </div>
    );
  }

  const data = invoice.data;
  const previewSubmission = submissions.data?.items.find(
    (item) => item.id === previewSubmissionId,
  );
  const previewUrl = previewSubmission
    ? runtimeConfig.apiBaseUrl +
      "/PaymentSubmissions/" +
      previewSubmission.id +
      "/receipt"
    : undefined;

  return (
    <div className="mx-auto w-full max-w-[1280px] space-y-4">
      <Button
        className="-ml-2 h-8 text-muted-foreground"
        variant="ghost"
        size="sm"
        onClick={() => window.history.back()}
      >
        <ArrowLeft className="size-4" /> Quay lại
      </Button>

      <PageHeader
        eyebrow={`Hóa đơn · ${data.invoiceCode}`}
        title={data.studentName}
        description={`${data.studentCode}${data.faculty ? ` · ${data.faculty}` : ""} · Năm học ${data.academicYearCode}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge
              variant={invoiceStatusVariants[data.status]}
              className="text-xs"
            >
              {invoiceStatusLabels[data.status]}
            </Badge>
            {(data.status === "unpaid" || data.status === "cancelled") && (
              <Button
                variant="destructive"
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setDeleteConfirmOpen(true)}
              >
                <Trash2 className="size-3.5" />
                <span>Xóa hóa đơn</span>
              </Button>
            )}
          </div>
        }
      />

      {/* KPI - 12-col để thẳng hàng với Main */}
      <div className="grid gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-12">
        <Card className="p-4 sm:col-span-1 lg:col-span-4">
          <p className="type-supporting text-muted-foreground">Tổng tiền</p>
          <p className="mt-1 text-lg font-semibold tabular-nums">
            {money(data.totalAmount)}
          </p>
          <p className="type-supporting mt-1 text-muted-foreground">
            Phát hành {formatDateValue(data.issuedAt) || "—"}
            {data.dueDate ? ` · Hạn ${formatDateValue(data.dueDate)}` : ""}
          </p>
        </Card>
        <Card className="p-4 sm:col-span-1 lg:col-span-4">
          <p className="type-supporting text-muted-foreground">Đã thanh toán</p>
          <p className="mt-1 text-lg font-semibold tabular-nums">
            {money(data.paidAmount)}
          </p>
          <div className="mt-2 flex items-center gap-2">
            <Progress value={paidPercent} className="h-1.5 flex-1" />
            <span className="text-xs font-medium tabular-nums">
              {paidPercent}%
            </span>
          </div>
        </Card>
        <Card
          className={cn(
            "p-4 sm:col-span-1 lg:col-span-4",
            isFullyPaid
              ? "border-success/20 bg-success/5"
              : "border-destructive/20 bg-destructive/5",
          )}
        >
          <p className="type-supporting text-muted-foreground">Còn nợ</p>
          <p
            className={cn(
              "mt-1 text-lg font-semibold tabular-nums",
              isFullyPaid ? "text-success" : "text-destructive",
            )}
          >
            {money(remainingAmount)}
          </p>
          <p className="type-supporting mt-1 text-muted-foreground">
            {data.registrationPeriodName
              ? `${data.registrationPeriodCode} · ${data.registrationPeriodName}`
              : (data.registrationPeriodCode ?? "Chưa gắn đợt")}
          </p>
        </Card>
      </div>

      {/* Main - cùng 12-col, left 8 (=2 KPI) right 4 (=1 KPI) để mép thẳng hàng */}
      <div className="grid gap-3 sm:gap-4 lg:grid-cols-12 lg:items-start">
        <div className="min-w-0 space-y-3 sm:space-y-4 lg:col-span-8">
          {/* Ghi nhận / Xác nhận thanh toán - luồng chính, đặt ngay dưới KPI */}
          {canPay && !isFullyPaid ? (
            pendingSubmission && !useManualForm ? (
              <Card className="border-primary/30 bg-primary/5 shadow-xs">
                <CardHeader className="p-4 pb-3">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 text-sm font-bold text-primary">
                      <FileCheck2 className="size-4" />
                      Sinh viên đã nộp 1 biên lai chuyển khoản (VietQR)
                    </CardTitle>
                    <Badge
                      variant="warning"
                      className="text-[11px] font-semibold"
                    >
                      Chờ xác nhận
                    </Badge>
                  </div>
                  <p className="type-supporting text-muted-foreground">
                    Kiểm tra thông tin biên lai bên dưới và bấm xác nhận để tất
                    toán hóa đơn và kích hoạt chỗ ở.
                  </p>
                </CardHeader>
                <CardContent className="p-4 pt-0 space-y-3">
                  <div className="flex items-center gap-3 rounded-lg border bg-card p-3 shadow-xs">
                    <button
                      type="button"
                      onClick={() => {
                        const isImg =
                          pendingSubmission.receiptContentType?.startsWith(
                            "image/",
                          ) ?? false;
                        const rUrl = `${runtimeConfig.apiBaseUrl}/PaymentSubmissions/${pendingSubmission.id}/receipt`;
                        if (isImg) setPreviewSubmissionId(pendingSubmission.id);
                        else window.open(rUrl, "_blank");
                      }}
                      className="size-16 shrink-0 overflow-hidden rounded-md border bg-muted/30 flex items-center justify-center hover:opacity-85 transition-opacity"
                      title="Bấm để xem ảnh biên lai"
                    >
                      {(pendingSubmission.receiptContentType?.startsWith(
                        "image/",
                      ) ?? false) ? (
                        <img
                          src={`${runtimeConfig.apiBaseUrl}/PaymentSubmissions/${pendingSubmission.id}/receipt`}
                          alt={pendingSubmission.receiptFileName}
                          className="size-full object-cover"
                        />
                      ) : (
                        <FileText className="size-6 text-muted-foreground" />
                      )}
                    </button>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-sm truncate">
                        {pendingSubmission.receiptFileName}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Số tiền:{" "}
                        <strong className="text-foreground font-mono font-bold text-sm">
                          {money(pendingSubmission.amount)}
                        </strong>{" "}
                        · Nộp{" "}
                        {formatDateTimeValue(pendingSubmission.submittedAt)}
                      </p>
                      {pendingSubmission.referenceNo && (
                        <p className="text-xs text-muted-foreground font-mono mt-0.5">
                          Mã GD: {pendingSubmission.referenceNo}
                        </p>
                      )}
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs"
                      onClick={() => {
                        const isImg =
                          pendingSubmission.receiptContentType?.startsWith(
                            "image/",
                          ) ?? false;
                        const rUrl = `${runtimeConfig.apiBaseUrl}/PaymentSubmissions/${pendingSubmission.id}/receipt`;
                        if (isImg) setPreviewSubmissionId(pendingSubmission.id);
                        else window.open(rUrl, "_blank");
                      }}
                    >
                      <Eye className="size-3.5 mr-1" /> Xem ảnh
                    </Button>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <Button
                      size="sm"
                      className="flex-1 sm:flex-none font-semibold text-xs"
                      disabled={verifySubmission.isPending}
                      onClick={() => setVerifyTarget(pendingSubmission.id)}
                    >
                      <Check className="size-3.5 mr-1.5" />
                      {verifySubmission.isPending
                        ? "Đang xử lý..."
                        : "Xác nhận thanh toán"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs"
                      disabled={rejectSubmission.isPending}
                      onClick={() => setRejectTarget(pendingSubmission.id)}
                    >
                      <X className="size-3.5 mr-1.5" />
                      Từ chối biên lai
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-xs text-muted-foreground ml-auto"
                      onClick={() => setUseManualForm(true)}
                    >
                      Nộp hình thức khác (Tiền mặt)
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader className="p-4 pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <CreditCard className="size-4 text-primary" />
                      Xác nhận thanh toán
                    </CardTitle>
                    {pendingSubmission && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-xs text-primary h-7 px-2"
                        onClick={() => setUseManualForm(false)}
                      >
                        ← Quay lại duyệt biên lai đã nộp
                      </Button>
                    )}
                  </div>
                  <p className="type-supporting text-muted-foreground">
                    Còn nợ {money(remainingAmount)} · Xác nhận số tiền và hình
                    thức thanh toán để kích hoạt chỗ ở.
                  </p>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <PaymentForm
                    paymentForm={paymentForm}
                    remainingAmount={remainingAmount}
                    paymentError={paymentError}
                    setPaymentError={setPaymentError}
                    createPayment={createPayment}
                  />
                </CardContent>
              </Card>
            )
          ) : isFullyPaid ? (
            <Card className="border-success/20 bg-success/5 p-4">
              <p className="flex items-center gap-2 text-sm font-medium text-success">
                <Check className="size-4" /> Đã thanh toán đủ · Không cần ghi
                nhận thêm
              </p>
            </Card>
          ) : null}

          {/* Left: Tabs - bỏ overflow-hidden để Table cuộn ngang không bị che trên mobile */}
          <Card>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <div className="border-b px-4 pt-2">
                <TabsList className="h-auto gap-1 border-0 p-0">
                  <TabsTrigger value="lines" className="gap-1.5">
                    <FileText className="size-3.5" /> Chi tiết
                  </TabsTrigger>
                  <TabsTrigger value="payments" className="gap-1.5">
                    <Receipt className="size-3.5" /> Lịch sử
                    {payments.data?.length ? (
                      <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                        {payments.data.length}
                      </Badge>
                    ) : null}
                  </TabsTrigger>
                  {canViewSubmissions ? (
                    <TabsTrigger value="submissions" className="gap-1.5">
                      <FileCheck2 className="size-3.5" /> Biên lai
                      {submissions.data?.total ? (
                        <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                          {submissions.data.total}
                        </Badge>
                      ) : null}
                    </TabsTrigger>
                  ) : null}
                </TabsList>
              </div>

              <TabsContent value="lines" className="mt-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader className="bg-muted/30">
                      <TableRow>
                        <TableHead>Nội dung</TableHead>
                        <TableHead className="text-right">SL</TableHead>
                        <TableHead className="text-right">Đơn giá</TableHead>
                        <TableHead className="text-right">Thành tiền</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.lines.map((line) => (
                        <TableRow key={line.id}>
                          <TableCell className="text-sm">
                            {line.description}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {line.quantity}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {money(line.unitAmount)}
                          </TableCell>
                          <TableCell className="text-right font-medium tabular-nums">
                            {money(line.lineAmount)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                {data.note ? (
                  <div className="border-t px-4 py-3">
                    <p className="type-supporting font-medium">
                      Ghi chú hóa đơn
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {data.note}
                    </p>
                  </div>
                ) : null}
                <div className="border-t bg-muted/20 px-4 py-2.5 text-xs text-muted-foreground">
                  Tạo {formatDateTimeValue(data.created)}
                  {data.createdBy ? ` · ${data.createdBy}` : ""} · Cập nhật{" "}
                  {formatDateTimeValue(data.lastModified)}
                </div>
              </TabsContent>

              <TabsContent value="payments" className="mt-0">
                {payments.isLoading ? (
                  <div className="space-y-2 p-4">
                    <Skeleton className="h-12" />
                    <Skeleton className="h-12" />
                  </div>
                ) : payments.isError ? (
                  <div className="p-4 text-sm">
                    <p className="text-destructive">Không thể tải lịch sử.</p>
                    <Button
                      className="mt-2"
                      size="sm"
                      variant="outline"
                      onClick={() => void payments.refetch()}
                    >
                      Thử lại
                    </Button>
                  </div>
                ) : (payments.data ?? []).length ? (
                  <ul className="divide-y">
                    {(payments.data ?? []).map((payment) => (
                      <li
                        key={payment.id}
                        className="flex items-center justify-between gap-3 px-4 py-3"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium tabular-nums">
                            {money(payment.amount)} ·{" "}
                            {payment.paymentMethod === "bank_transfer"
                              ? "Chuyển khoản"
                              : payment.paymentMethod === "cash"
                                ? "Tiền mặt"
                                : "Khác"}
                          </p>
                          <p className="type-supporting truncate text-muted-foreground">
                            {formatDateTimeValue(payment.paidAt)}
                            {payment.referenceNo
                              ? ` · ${payment.referenceNo}`
                              : ""}
                            {payment.note ? ` · ${payment.note}` : ""}
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-1.5">
                          <Badge
                            variant={
                              payment.status === "voided"
                                ? "secondary"
                                : "success"
                            }
                            className="h-5"
                          >
                            {payment.status === "voided"
                              ? "Đã hủy"
                              : "Hoàn tất"}
                          </Badge>
                          {canVoid && payment.status !== "voided" ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2"
                              onClick={() => setVoidTarget(payment.id)}
                            >
                              <Ban className="size-3.5" />
                            </Button>
                          ) : null}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState
                    icon={Receipt}
                    title="Chưa có thanh toán"
                    description="Lịch sử sẽ xuất hiện sau khi ghi nhận."
                    className="py-6"
                  />
                )}
              </TabsContent>

              <TabsContent value="submissions" className="mt-0">
                {submissions.isLoading ? (
                  <div className="space-y-2 p-4">
                    <Skeleton className="h-20" />
                    <Skeleton className="h-20" />
                  </div>
                ) : submissions.isError ? (
                  <div className="p-4 text-sm">
                    <p className="text-destructive">Không thể tải biên lai.</p>
                    <Button
                      className="mt-2"
                      size="sm"
                      variant="outline"
                      onClick={() => void submissions.refetch()}
                    >
                      Thử lại
                    </Button>
                  </div>
                ) : submissions.data?.items.length ? (
                  <ul className="divide-y">
                    {submissions.data.items.map((submission) => {
                      const receiptUrl =
                        runtimeConfig.apiBaseUrl +
                        "/PaymentSubmissions/" +
                        submission.id +
                        "/receipt";
                      const isImage =
                        submission.receiptContentType?.startsWith("image/") ??
                        false;
                      const isPending = submission.status === "submitted";
                      return (
                        <li
                          key={submission.id}
                          className="flex gap-3 px-4 py-3"
                        >
                          <button
                            type="button"
                            onClick={() =>
                              isImage
                                ? setPreviewSubmissionId(submission.id)
                                : window.open(receiptUrl, "_blank")
                            }
                            className="size-16 shrink-0 overflow-hidden rounded-md border bg-muted/30"
                            aria-label="Xem biên lai"
                          >
                            {isImage ? (
                              <img
                                src={receiptUrl}
                                alt={submission.receiptFileName}
                                loading="lazy"
                                className="size-full object-cover"
                              />
                            ) : (
                              <span className="flex size-full items-center justify-center">
                                <FileText className="size-5 text-muted-foreground" />
                              </span>
                            )}
                          </button>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-start justify-between gap-2">
                              <p className="truncate text-sm font-medium">
                                {submission.receiptFileName}
                              </p>
                              <Badge
                                variant={
                                  paymentSubmissionStatusVariants[
                                    submission.status as PaymentSubmissionStatus
                                  ]
                                }
                                className="h-5 shrink-0"
                              >
                                {paymentSubmissionStatusLabels[
                                  submission.status as PaymentSubmissionStatus
                                ] ?? submission.status}
                              </Badge>
                            </div>
                            <p className="type-supporting mt-0.5 text-muted-foreground">
                              {money(submission.amount)} ·{" "}
                              {formatDateTimeValue(submission.submittedAt)}
                              {submission.referenceNo
                                ? ` · ${submission.referenceNo}`
                                : ""}
                            </p>
                            {submission.reviewNote ? (
                              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                                Ghi chú: {submission.reviewNote}
                              </p>
                            ) : null}
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              <Button
                                asChild
                                variant="outline"
                                size="sm"
                                className="h-7 px-2"
                              >
                                <a
                                  href={receiptUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  <Download className="size-3.5" /> Mở
                                </a>
                              </Button>
                              {isPending && canVerifySubmission ? (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-7 px-2"
                                  onClick={() => setRejectTarget(submission.id)}
                                >
                                  <X className="size-3.5 mr-1" /> Từ chối
                                </Button>
                              ) : null}
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <EmptyState
                    icon={FileCheck2}
                    title="Chưa có biên lai"
                    description="Sinh viên chưa nộp biên lai cho hóa đơn này."
                    className="py-6"
                  />
                )}
              </TabsContent>
            </Tabs>
          </Card>
        </div>

        {/* Right sidebar - 4 cột = đúng 1 KPI, thẳng mép với KPI thứ 3 */}
        <aside className="min-w-0 space-y-3 sm:space-y-4 lg:col-span-4 lg:sticky lg:top-4">
          <Card className="p-4">
            <p className="text-sm font-semibold">Thông tin hóa đơn</p>
            <dl className="mt-3 space-y-2.5 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Mã HĐ</dt>
                <dd className="font-mono text-xs font-medium">
                  {data.invoiceCode}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Năm học</dt>
                <dd className="font-medium">{data.academicYearCode}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Đợt ĐK</dt>
                <dd className="text-right font-medium">
                  {data.registrationPeriodCode ?? "—"}
                  {data.registrationPeriodName
                    ? ` · ${data.registrationPeriodName}`
                    : ""}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Phát hành</dt>
                <dd className="font-medium">
                  {formatDateValue(data.issuedAt) || "—"}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Hạn TT</dt>
                <dd className="font-medium">
                  {data.dueDate ? formatDateValue(data.dueDate) : "—"}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Trạng thái</dt>
                <dd>
                  <Badge
                    variant={invoiceStatusVariants[data.status]}
                    className="h-5"
                  >
                    {invoiceStatusLabels[data.status]}
                  </Badge>
                </dd>
              </div>
            </dl>
            <div className="mt-3 border-t pt-3 text-xs text-muted-foreground">
              <p>Tạo {formatDateTimeValue(data.created)}</p>
              {data.createdBy ? <p>· {data.createdBy}</p> : null}
            </div>
          </Card>
        </aside>
      </div>

      {/* Preview dialog */}
      <Dialog
        open={Boolean(previewSubmissionId)}
        onOpenChange={(open) => {
          if (!open) setPreviewSubmissionId(undefined);
        }}
      >
        <DialogContent className="max-w-3xl p-2 sm:p-4">
          <DialogHeader className="px-2 pt-2">
            <DialogTitle className="truncate pr-6 text-sm">
              {previewSubmission?.receiptFileName ?? "Biên lai"}
            </DialogTitle>
          </DialogHeader>
          {previewUrl &&
          previewSubmission?.receiptContentType?.startsWith("image/") ? (
            <div className="flex max-h-[70vh] items-center justify-center overflow-auto rounded-md bg-muted/20 p-2">
              <img
                src={previewUrl}
                alt={previewSubmission?.receiptFileName ?? "Biên lai"}
                className="max-h-[65vh] w-auto rounded object-contain"
              />
            </div>
          ) : (
            <p className="p-4 text-sm text-muted-foreground">
              Không hỗ trợ xem trước. Hãy mở biên lai trong tab mới.
            </p>
          )}
          {previewUrl ? (
            <div className="flex justify-end px-2 pb-2">
              <Button asChild size="sm" variant="outline">
                <a href={previewUrl} target="_blank" rel="noreferrer">
                  <Download className="size-4" /> Mở tab mới
                </a>
              </Button>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(voidTarget)}
        onOpenChange={(open) => {
          if (!open) setVoidTarget(undefined);
        }}
        title="Hủy khoản thanh toán?"
        description={
          <p>
            Khoản thanh toán sẽ được đánh dấu đã hủy và công nợ sẽ được tính
            lại.
          </p>
        }
        confirmLabel="Hủy thanh toán"
        isLoading={voidPayment.isPending}
        onConfirm={() => {
          if (voidTarget) {
            void voidPayment.mutate(
              { paymentId: voidTarget },
              { onSuccess: () => setVoidTarget(undefined) },
            );
          }
        }}
      />

      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={(open) => {
          if (!open && !deleteInvoice.isPending) setDeleteConfirmOpen(false);
        }}
        title="Xóa hóa đơn?"
        description={`Bạn có chắc chắn muốn xóa hóa đơn ${data.invoiceCode}? Toàn bộ các dòng chi tiết sẽ bị xóa.`}
        confirmLabel="Xóa hóa đơn"
        isLoading={deleteInvoice.isPending}
        onConfirm={() => {
          deleteInvoice
            .mutateAsync({ id: data.id })
            .then(() => {
              toast.success("Đã xóa hóa đơn thành công.");
              void navigate({
                to: "/invoices",
                search: { q: "", page: 1, pageSize: 10 },
              });
            })
            .catch((err: unknown) => {
              toast.error(
                err instanceof Error ? err.message : "Không thể xóa hóa đơn.",
              );
            });
        }}
      />

      <NoteConfirmDialog
        open={Boolean(verifyTarget)}
        onOpenChange={(open) => {
          if (!open) setVerifyTarget(undefined);
        }}
        title="Duyệt biên lai?"
        description="Xác nhận số tiền và thông tin biên lai phù hợp với hóa đơn."
        noteLabel="Ghi chú duyệt (tuỳ chọn)"
        requireNote={false}
        confirmLabel="Duyệt"
        confirmVariant="default"
        isLoading={verifySubmission.isPending}
        onConfirm={(reviewNote) => {
          if (verifyTarget) {
            verifySubmission.mutate(
              { id: verifyTarget, reviewNote },
              { onSuccess: () => setVerifyTarget(undefined) },
            );
          }
        }}
      />

      <NoteConfirmDialog
        open={Boolean(rejectTarget)}
        onOpenChange={(open) => {
          if (!open) setRejectTarget(undefined);
        }}
        title="Từ chối biên lai?"
        description="Sinh viên sẽ nhận được thông báo và cần nộp lại biên lai."
        noteLabel="Lý do từ chối"
        requireNote={true}
        confirmLabel="Từ chối"
        isLoading={rejectSubmission.isPending}
        onConfirm={(reviewNote) => {
          if (rejectTarget) {
            rejectSubmission.mutate(
              { id: rejectTarget, reviewNote },
              { onSuccess: () => setRejectTarget(undefined) },
            );
          }
        }}
      />
    </div>
  );
}

function PaymentForm({
  paymentForm,
  remainingAmount,
  paymentError,
  setPaymentError,
  createPayment,
}: {
  paymentForm: any;
  remainingAmount: number;
  paymentError?: string;
  setPaymentError: (value: string | undefined) => void;
  createPayment: any;
}) {
  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        event.stopPropagation();
        if (
          (paymentForm.state.values as { amount: number }).amount >
          remainingAmount
        ) {
          setPaymentError(overpaymentMessage);
          return;
        }
        void paymentForm.handleSubmit();
      }}
    >
      <paymentForm.Field name="amount">
        {(field: any) => (
          <Field>
            <FieldLabel htmlFor="invoice-payment-amount">
              Số tiền (₫)
            </FieldLabel>
            <Input
              id="invoice-payment-amount"
              type="text"
              inputMode="numeric"
              value={formatVndInput(field.state.value || 0)}
              disabled={createPayment.isPending}
              onChange={(event) => {
                const amount = parseVndInput(event.target.value);
                field.handleChange(amount);
                setPaymentError(
                  amount > remainingAmount ? overpaymentMessage : undefined,
                );
              }}
            />
            <FieldDescription>
              Tối đa: {money(remainingAmount)}
            </FieldDescription>
            {firstError(field.state.meta.errors) ? (
              <FieldError>{firstError(field.state.meta.errors)}</FieldError>
            ) : null}
          </Field>
        )}
      </paymentForm.Field>
      <paymentForm.Field name="paymentMethod">
        {(field: any) => (
          <Field>
            <FieldLabel>Phương thức</FieldLabel>
            <Select
              value={field.state.value}
              disabled={createPayment.isPending}
              onValueChange={field.handleChange}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="cash">Tiền mặt</SelectItem>
                <SelectItem value="bank_transfer">Chuyển khoản</SelectItem>
                <SelectItem value="other">Khác</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        )}
      </paymentForm.Field>
      <paymentForm.Field name="referenceNo">
        {(field: any) => (
          <Field>
            <FieldLabel htmlFor="invoice-payment-reference">
              Mã tham chiếu
            </FieldLabel>
            <Input
              id="invoice-payment-reference"
              value={field.state.value}
              placeholder="VD: FT20250821001"
              disabled={createPayment.isPending}
              onChange={(event) => field.handleChange(event.target.value)}
            />
            {firstError(field.state.meta.errors) ? (
              <FieldError>{firstError(field.state.meta.errors)}</FieldError>
            ) : null}
          </Field>
        )}
      </paymentForm.Field>
      <paymentForm.Field name="note">
        {(field: any) => (
          <Field>
            <FieldLabel htmlFor="invoice-payment-note">
              Ghi chú ({field.state.value.length}/2000)
            </FieldLabel>
            <Textarea
              id="invoice-payment-note"
              rows={2}
              value={field.state.value}
              disabled={createPayment.isPending}
              onChange={(event) => field.handleChange(event.target.value)}
            />
            {firstError(field.state.meta.errors) ? (
              <FieldError>{firstError(field.state.meta.errors)}</FieldError>
            ) : null}
          </Field>
        )}
      </paymentForm.Field>
      <paymentForm.Subscribe
        selector={(state: any) => [state.canSubmit, state.isSubmitting]}
      >
        {(state: any) => {
          const [canSubmit, formSubmitting] = state as [boolean, boolean];
          return (
            <Button
              type="submit"
              size="sm"
              disabled={!canSubmit || formSubmitting || createPayment.isPending}
              className="w-full"
            >
              {createPayment.isPending
                ? "Đang xử lý..."
                : "Xác nhận thanh toán"}
            </Button>
          );
        }}
      </paymentForm.Subscribe>
      {paymentError || createPayment.isError ? (
        <p className="text-xs text-destructive" role="alert">
          {paymentError ?? "Không thể ghi nhận thanh toán."}
        </p>
      ) : null}
    </form>
  );
}
