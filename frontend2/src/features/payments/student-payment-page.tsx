import { useForm } from "@tanstack/react-form";
import {
  CheckCircle2,
  Clock3,
  CreditCard,
  FileCheck2,
  Info,
  QrCode,
  RefreshCw,
  Upload,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { CopyButton } from "@/components/admin/copy-button";
import { PageHeader } from "@/components/admin/page-header";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  useMyPaymentInvoicesQuery,
  usePaymentQrQuery,
  useSubmitPaymentReceipt,
} from "@/features/payments/api";
import {
  paymentInvoiceStatusLabels as invoiceStatusLabels,
  type PaymentInvoice,
  type PaymentSubmissionStatus,
  paymentInvoiceStatusVariants,
  paymentSubmissionStatusVariants,
  paymentSubmissionStatusLabels as submissionStatusLabels,
} from "@/features/payments/types";
import { formatDateValue } from "@/lib/date-utils";
import { getFormErrorMessage } from "@/lib/form-errors";

const money = (value: number) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);

const date = (value?: string | null) =>
  value ? formatDateValue(value) : "Chưa có";

function SubmissionStatus({ status }: { status: PaymentSubmissionStatus }) {
  const Icon =
    status === "verified"
      ? CheckCircle2
      : status === "rejected"
        ? XCircle
        : status === "submitted"
          ? Clock3
          : FileCheck2;

  return (
    <Badge variant={paymentSubmissionStatusVariants[status]}>
      <Icon /> {submissionStatusLabels[status]}
    </Badge>
  );
}

function PaymentReceiptDialog({
  invoice,
  open,
  onOpenChange,
}: {
  invoice?: PaymentInvoice;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const qr = usePaymentQrQuery(invoice?.id, open);
  const submit = useSubmitPaymentReceipt();
  const [file, setFile] = useState<File>();

  const form = useForm({
    defaultValues: {
      receipt: undefined as File | undefined,
    },
    validators: {
      onSubmit: z.object({
        receipt: z
          .custom<File>(
            (value) => value instanceof File,
            "Biên lai là bắt buộc.",
          )
          .refine(
            (value) => value.size <= 10 * 1024 * 1024,
            "Biên lai không được vượt quá 10 MB.",
          )
          .refine(
            (value) =>
              value.type.startsWith("image/") ||
              value.type === "application/pdf",
            "Chỉ chấp nhận ảnh hoặc tệp PDF.",
          ),
      }),
    },
    onSubmit: async ({ value }) => {
      if (!invoice || !value.receipt) return;
      await submit.mutateAsync({
        invoiceId: invoice.id,
        receipt: value.receipt,
      });
      toast.success("Đã nộp biên lai. Nhà trường sẽ kiểm tra và xác nhận.");
      setFile(undefined);
      form.reset();
      onOpenChange(false);
    },
  });

  const firstError = (errors: unknown[]) =>
    errors.length ? getFormErrorMessage(errors[0]) : undefined;

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && !submit.isPending) {
          setFile(undefined);
          form.reset();
        }
        onOpenChange(nextOpen);
      }}
    >
      <ResponsiveDialogContent className="max-w-3xl">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            Thanh toán và nộp biên lai
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Quét QR của trường, chuyển khoản đúng nội dung rồi tải ảnh hoặc PDF
            biên lai để nhà trường đối soát.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        {qr.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-[240px_minmax(0,1fr)]">
            <Skeleton className="aspect-square w-full rounded-xl" />
            <div className="grid gap-3">
              <Skeleton className="h-16 rounded-xl" />
              <Skeleton className="h-24 rounded-xl" />
              <Skeleton className="h-24 rounded-xl" />
            </div>
          </div>
        ) : qr.isError || !qr.data ? (
          <Alert variant="destructive">
            <Info />
            <div>
              <AlertTitle>Không thể tải thông tin QR</AlertTitle>
              <AlertDescription>
                Vui lòng đóng cửa sổ và thử lại sau.
              </AlertDescription>
            </div>
          </Alert>
        ) : (
          <form
            className="grid max-h-[calc(100dvh-10rem)] gap-4 overflow-y-auto px-1 pb-1 sm:max-h-[calc(100dvh-12rem)]"
            onSubmit={(event) => {
              event.preventDefault();
              event.stopPropagation();
              void form.handleSubmit();
            }}
          >
            <div className="grid gap-4 sm:grid-cols-[minmax(200px,240px)_minmax(0,1fr)] sm:items-start">
              {/* QR Code Container */}
              <div className="flex flex-col items-center justify-center rounded-xl border bg-muted/20 p-3 text-center sm:p-4">
                {qr.data.qrImageUrl ? (
                  <div className="overflow-hidden rounded-lg bg-white p-1.5 shadow-2xs">
                    <img
                      src={qr.data.qrImageUrl}
                      alt={`Mã QR thanh toán ${qr.data.invoiceCode}`}
                      className="mx-auto h-auto max-h-[260px] w-auto max-w-full object-contain"
                    />
                  </div>
                ) : (
                  <div className="flex h-52 w-full items-center justify-center rounded-lg bg-muted/50 text-center text-sm text-muted-foreground">
                    QR chưa được cấu hình
                  </div>
                )}
                <p className="mt-2 text-center text-xs text-muted-foreground">
                  Quét mã qua ứng dụng ngân hàng hoặc VietQR
                </p>
              </div>

              {/* Bank & Payment Info */}
              <div className="grid content-start gap-3">
                {/* Số tiền cần chuyển */}
                <div className="flex items-center justify-between rounded-xl border bg-muted/30 p-3 sm:p-3.5">
                  <div className="min-w-0">
                    <p className="text-xs text-muted-foreground">
                      Số tiền cần chuyển
                    </p>
                    <p className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
                      {money(qr.data.amount)}
                    </p>
                  </div>
                  <CopyButton
                    value={qr.data.amount.toString()}
                    label="số tiền"
                    tooltip="Sao chép số tiền"
                    showToast
                    className="size-8 rounded-lg border bg-background shadow-2xs hover:bg-muted"
                  />
                </div>

                {/* Thông tin ngân hàng */}
                <div className="divide-y rounded-xl border bg-card text-sm">
                  <div className="flex items-center justify-between gap-3 px-3.5 py-2.5">
                    <span className="shrink-0 text-muted-foreground">
                      Ngân hàng
                    </span>
                    <span className="font-semibold text-foreground">
                      {qr.data.bankCode}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3 px-3.5 py-2.5">
                    <span className="shrink-0 text-muted-foreground">
                      Số tài khoản
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono font-bold tracking-wider text-foreground">
                        {qr.data.accountNumber}
                      </span>
                      <CopyButton
                        value={qr.data.accountNumber}
                        label="số tài khoản"
                        tooltip="Sao chép số tài khoản"
                        showToast
                      />
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-3 px-3.5 py-2.5">
                    <span className="shrink-0 text-muted-foreground">
                      Tên tài khoản
                    </span>
                    <span className="text-right font-medium text-foreground">
                      {qr.data.accountName || "Chưa cấu hình"}
                    </span>
                  </div>
                </div>

                {/* Cú pháp chuyển khoản bắt buộc */}
                <div className="grid gap-1.5 rounded-xl border-2 border-primary/30 bg-primary/5 p-3 sm:p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-primary">
                      Nội dung chuyển khoản bắt buộc
                    </span>
                    <CopyButton
                      value={qr.data.transferContent}
                      label="nội dung chuyển khoản"
                      tooltip="Sao chép cú pháp"
                      showToast
                      className="size-7 rounded-md bg-primary/15 text-primary hover:bg-primary/25"
                    />
                  </div>
                  <div className="rounded-lg border bg-background/90 p-2.5 shadow-2xs">
                    <code className="break-all font-mono text-xs font-bold text-primary sm:text-sm">
                      {qr.data.transferContent}
                    </code>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    ⚠️ Nhập chính xác cú pháp trên để hệ thống tự động gạch nợ.
                  </p>
                </div>

                {qr.data.instructionText ? (
                  <div className="grid gap-1 rounded-xl border bg-muted/20 p-3 text-xs sm:text-sm">
                    <span className="font-semibold text-muted-foreground">
                      Hướng dẫn thanh toán theo đợt
                    </span>
                    <p className="whitespace-pre-wrap text-foreground">
                      {qr.data.instructionText}
                    </p>
                  </div>
                ) : null}
              </div>
            </div>

            {!qr.data.enabled ? (
              <Alert variant="warning">
                <Info />
                <div>
                  <AlertTitle>Chưa thể nộp thanh toán trực tuyến</AlertTitle>
                  <AlertDescription>
                    Tài khoản nhận QR chưa được cấu hình hoặc nghĩa vụ này đã
                    được thanh toán.
                  </AlertDescription>
                </div>
              </Alert>
            ) : (
              <div className="grid gap-3 rounded-xl border bg-card p-3.5 sm:p-4">
                <div className="rounded-lg bg-muted/40 p-3">
                  <p className="text-xs font-semibold text-foreground">
                    Sau khi chuyển khoản thành công
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">
                    Chụp màn hình giao dịch hoặc tải file PDF biên lai lên để
                    nhà trường đối soát và xác nhận.
                  </p>
                </div>

                <form.Field name="receipt">
                  {(field) => (
                    <div className="grid gap-2">
                      <Label
                        htmlFor="payment-receipt"
                        className="text-xs font-semibold"
                      >
                        Đính kèm ảnh / PDF biên lai{" "}
                        <span className="text-destructive">*</span>
                      </Label>

                      <div
                        className="relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-muted-foreground/25 p-4 text-center transition-colors hover:border-primary/50 hover:bg-muted/10 cursor-pointer"
                        onClick={() =>
                          document.getElementById("payment-receipt")?.click()
                        }
                      >
                        <input
                          id="payment-receipt"
                          type="file"
                          accept="image/*,application/pdf"
                          disabled={submit.isPending}
                          className="sr-only"
                          onChange={(event) => {
                            const nextFile = event.target.files?.[0];
                            setFile(nextFile);
                            field.handleChange(nextFile);
                          }}
                        />

                        {file ? (
                          <div className="flex flex-col items-center gap-1.5 py-1">
                            <div className="flex size-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
                              <FileCheck2 className="size-5" />
                            </div>
                            <p className="max-w-[280px] truncate text-sm font-semibold text-foreground">
                              {file.name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {(file.size / (1024 * 1024)).toFixed(2)} MB · Bấm
                              để đổi tệp khác
                            </p>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center gap-1 py-1">
                            <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                              <Upload className="size-5" />
                            </div>
                            <p className="text-sm font-medium text-foreground">
                              Bấm để tải ảnh hoặc PDF biên lai
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Hỗ trợ JPG, PNG, PDF (Tối đa 10 MB)
                            </p>
                          </div>
                        )}
                      </div>

                      {firstError(field.state.meta.errors) ? (
                        <p
                          className="text-xs font-medium text-destructive"
                          role="alert"
                        >
                          {firstError(field.state.meta.errors)}
                        </p>
                      ) : null}
                    </div>
                  )}
                </form.Field>
              </div>
            )}

            {submit.isError ? (
              <Alert variant="destructive">
                <Info />
                <div>
                  <AlertTitle>Không thể nộp biên lai</AlertTitle>
                  <AlertDescription>
                    {submit.error instanceof Error
                      ? submit.error.message
                      : "Vui lòng kiểm tra lại tệp và thử lại."}
                  </AlertDescription>
                </div>
              </Alert>
            ) : null}

            <ResponsiveDialogFooter className="mt-2 flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button
                type="button"
                variant="outline"
                className="w-full sm:w-auto"
                disabled={submit.isPending}
                onClick={() => onOpenChange(false)}
              >
                Đóng
              </Button>
              <Button
                type="submit"
                className="w-full sm:w-auto"
                disabled={submit.isPending || !qr.data.enabled || !file}
              >
                {submit.isPending ? (
                  <>
                    <RefreshCw className="mr-2 size-4 animate-spin" />
                    Đang gửi biên lai...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 size-4" />
                    Nộp biên lai thanh toán
                  </>
                )}
              </Button>
            </ResponsiveDialogFooter>
          </form>
        )}
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

function InvoiceCard({
  invoice,
  canSubmit,
  onSubmitReceipt,
}: {
  invoice: PaymentInvoice;
  canSubmit: boolean;
  onSubmitReceipt: (invoice: PaymentInvoice) => void;
}) {
  const submission = invoice.latestSubmission;
  const isPaid = invoice.status === "paid";
  const hasActiveSubmission =
    submission?.status === "submitted" || submission?.status === "verified";
  const canOpenReceipt = canSubmit && !isPaid && !hasActiveSubmission;

  return (
    <Card>
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle>{invoice.invoiceCode}</CardTitle>
          <CardDescription>
            Phát hành {date(invoice.issuedAt)}
            {invoice.dueDate ? ` · Hạn ${date(invoice.dueDate)}` : ""}
          </CardDescription>
          <p className="type-supporting text-muted-foreground">
            {invoice.registrationPeriodName
              ? `${invoice.registrationPeriodName} (${invoice.registrationPeriodCode ?? ""})`
              : "ChÆ°a gÃ¡n Ä‘á»£t Ä‘Äƒng kÃ½"}
          </p>
        </div>
        <Badge variant={paymentInvoiceStatusVariants[invoice.status]}>
          {invoiceStatusLabels[invoice.status]}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <p className="type-supporting text-muted-foreground">
              Tổng phải nộp
            </p>
            <p className="mt-1 font-semibold">{money(invoice.totalAmount)}</p>
          </div>
          <div>
            <p className="type-supporting text-muted-foreground">Đã xác nhận</p>
            <p className="mt-1 font-semibold text-success">
              {money(invoice.paidAmount)}
            </p>
          </div>
          <div>
            <p className="type-supporting text-muted-foreground">
              Còn phải nộp
            </p>
            <p className="mt-1 text-lg font-semibold text-destructive">
              {money(invoice.remainingAmount)}
            </p>
          </div>
        </div>

        {submission ? (
          <div className="flex flex-col gap-2 rounded-md border bg-muted/20 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-start gap-2">
              <FileCheck2 className="mt-0.5 size-4 shrink-0 text-primary" />
              <div className="min-w-0">
                <p className="text-sm font-medium">Biên lai gần nhất</p>
                <p className="truncate text-sm text-muted-foreground">
                  {submission.receiptFileName} · {money(submission.amount)}
                </p>
                {submission.reviewNote ? (
                  <p className="mt-1 text-sm text-destructive">
                    {submission.reviewNote}
                  </p>
                ) : null}
              </div>
            </div>
            <SubmissionStatus status={submission.status} />
          </div>
        ) : null}

        <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <CreditCard className="size-4" />
            Chuyển khoản qua QR của nhà trường
          </p>
          <Button
            disabled={!canOpenReceipt}
            onClick={() => onSubmitReceipt(invoice)}
          >
            <QrCode />
            {submission?.status === "rejected"
              ? "Nộp lại biên lai"
              : isPaid
                ? "Đã hoàn tất"
                : hasActiveSubmission
                  ? "Đang chờ xác nhận"
                  : "Thanh toán qua QR"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function StudentPaymentPage({ canSubmit }: { canSubmit: boolean }) {
  const query = useMyPaymentInvoicesQuery({ page: 1, pageSize: 20 });
  const [activeInvoice, setActiveInvoice] = useState<PaymentInvoice>();

  const invoices = query.data?.items ?? [];
  const outstanding = invoices.filter((invoice) => invoice.remainingAmount > 0);
  const pending = invoices.filter(
    (invoice) => invoice.latestSubmission?.status === "submitted",
  ).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Sinh viên / Tài chính"
        title="Thanh toán ký túc xá"
        description="Theo dõi khoản phải nộp, chuyển khoản bằng QR và gửi biên lai để nhà trường xác nhận."
      />

      {query.isLoading ? (
        <div className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
          <Skeleton className="h-56" />
          <Skeleton className="h-56" />
        </div>
      ) : query.isError ? (
        <Alert variant="destructive">
          <Info />
          <div>
            <AlertTitle>Không thể tải thông tin thanh toán</AlertTitle>
            <AlertDescription className="flex flex-wrap items-center gap-3">
              {query.error instanceof Error
                ? query.error.message
                : "Vui lòng thử lại sau."}
              <Button
                size="sm"
                variant="outline"
                onClick={() => void query.refetch()}
              >
                <RefreshCw /> Thử lại
              </Button>
            </AlertDescription>
          </div>
        </Alert>
      ) : invoices.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <CreditCard className="size-10 text-muted-foreground/50" />
            <h2 className="text-lg font-semibold">Chưa có khoản phải nộp</h2>
            <p className="max-w-md text-sm text-muted-foreground">
              Khi nhà trường phát hành hóa đơn cho hồ sơ cư trú, thông tin sẽ
              xuất hiện tại đây.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Card>
              <CardContent className="p-4">
                <p className="type-supporting text-muted-foreground">
                  Tổng nghĩa vụ
                </p>
                <p className="mt-1 text-2xl font-semibold">{invoices.length}</p>
                <p className="mt-1 text-sm text-muted-foreground">hóa đơn</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="type-supporting text-muted-foreground">
                  Còn phải nộp
                </p>
                <p className="mt-1 text-2xl font-semibold text-destructive">
                  {money(
                    outstanding.reduce(
                      (total, invoice) => total + invoice.remainingAmount,
                      0,
                    ),
                  )}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  trên {outstanding.length} hóa đơn
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="type-supporting text-muted-foreground">
                  Chờ xác nhận
                </p>
                <p className="mt-1 text-2xl font-semibold text-warning">
                  {pending}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  biên lai đã nộp
                </p>
              </CardContent>
            </Card>
          </div>

          <Alert>
            <Upload />
            <div>
              <AlertTitle>Quy trình thanh toán</AlertTitle>
              <AlertDescription>
                Chuyển khoản đúng số tiền và nội dung hiển thị trong QR, sau đó
                tải biên lai. Khoản nộp chỉ được ghi nhận chính thức sau khi cán
                bộ kiểm tra.
              </AlertDescription>
            </div>
          </Alert>

          <div className="grid gap-4">
            {invoices.map((invoice) => (
              <InvoiceCard
                key={invoice.id}
                invoice={invoice}
                canSubmit={canSubmit}
                onSubmitReceipt={setActiveInvoice}
              />
            ))}
          </div>
        </>
      )}

      <PaymentReceiptDialog
        invoice={activeInvoice}
        open={Boolean(activeInvoice)}
        onOpenChange={(open) => {
          if (!open) setActiveInvoice(undefined);
        }}
      />
    </div>
  );
}
