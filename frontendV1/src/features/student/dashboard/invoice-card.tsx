import { Link } from "@tanstack/react-router";
import { ArrowRight, CircleCheck, Clock3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type PaymentInvoice,
  paymentInvoiceStatusLabels,
  paymentInvoiceStatusVariants,
  paymentSubmissionStatusLabels,
} from "@/features/payments/types";
import { money, useLiveCountdown } from "@/features/student/dashboard/helpers";
import { formatDateValue } from "@/lib/date-utils";

export function InvoiceCard({
  invoice,
  totalUnpaid,
}: {
  invoice?: PaymentInvoice | null;
  totalUnpaid: number;
}) {
  const isUnpaid = (invoice?.remainingAmount ?? 0) > 0 || totalUnpaid > 0;
  const dueStatus = useLiveCountdown(isUnpaid ? invoice?.dueDate : null);

  const headerBadge =
    totalUnpaid > 0 ? (
      dueStatus?.isExpired ? (
        <Badge variant="destructive">Quá hạn nợ {money(totalUnpaid)}</Badge>
      ) : (
        <Badge variant="warning">Chưa thanh toán {money(totalUnpaid)}</Badge>
      )
    ) : (
      <Badge variant="success">Không có nợ</Badge>
    );

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-base">KTX phí</CardTitle>
          {headerBadge}
        </div>
        <CardDescription>
          Khoản phí ký túc xá cần thanh toán của bạn
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {invoice ? (
          <div className="rounded-lg border bg-muted/30 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="font-mono text-sm font-semibold">
                {invoice.invoiceCode}
              </p>
              <Badge variant={paymentInvoiceStatusVariants[invoice.status]}>
                {paymentInvoiceStatusLabels[invoice.status]}
              </Badge>
            </div>
            <div className="mt-2 grid gap-1.5 text-sm text-muted-foreground">
              <p>
                Số tiền:{" "}
                <span className="font-medium text-foreground">
                  {money(invoice.totalAmount)}
                </span>
              </p>
              {invoice.remainingAmount > 0 ? (
                <p>
                  Còn thiếu:{" "}
                  <span className="font-medium text-foreground">
                    {money(invoice.remainingAmount)}
                  </span>
                </p>
              ) : null}
              {invoice.dueDate ? (
                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  <Clock3 className="size-3.5 shrink-0 text-muted-foreground" />
                  <span className="text-muted-foreground">Hạn nộp:</span>
                  <span className="font-medium text-foreground">
                    {formatDateValue(invoice.dueDate)}
                  </span>
                  {dueStatus && isUnpaid ? (
                    <Badge
                      variant={dueStatus.badgeVariant}
                      className="px-1.5 py-0 text-[10px]"
                    >
                      {dueStatus.detailedLabel}
                    </Badge>
                  ) : null}
                </div>
              ) : null}
              {invoice.latestSubmission ? (
                <p className="flex items-center gap-1 text-xs">
                  {invoice.latestSubmission.status === "verified" ? (
                    <CircleCheck className="size-3.5 text-success" />
                  ) : invoice.latestSubmission.status === "rejected" ? (
                    <Clock3 className="size-3.5 text-destructive" />
                  ) : (
                    <Clock3 className="size-3.5" />
                  )}
                  Giấy nộp:{" "}
                  {
                    paymentSubmissionStatusLabels[
                      invoice.latestSubmission.status
                    ]
                  }
                </p>
              ) : null}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Chưa có hóa đơn nào. Nhà trường sẽ thông báo khi phát sinh phí.
          </p>
        )}
        <Button asChild variant="outline" size="sm" className="w-full">
          <Link to="/student/payments">
            Xem tất cả hóa đơn <ArrowRight />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
