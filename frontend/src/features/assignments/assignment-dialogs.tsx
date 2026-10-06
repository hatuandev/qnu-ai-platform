import { CheckCheck, LogIn, RotateCcw, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/app/api/client";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DatePicker } from "@/components/admin/date-pickers";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  useCancelAssignment,
  useRefundAndCancelAssignment,
} from "@/features/assignments/api";
import type { Assignment } from "@/features/assignments/types";
import { useCheckIn, useCheckInBatch } from "@/features/residences/api";
import { formatDateOnly } from "@/lib/date-utils";

export function CancelDialog({
  assignment,
  onClose,
}: {
  assignment: Assignment | null;
  onClose: () => void;
}) {
  const cancel = useCancelAssignment();
  return (
    <ConfirmDialog
      open={Boolean(assignment)}
      onOpenChange={(open) => {
        if (!open && !cancel.isPending) onClose();
      }}
      title="Hủy xếp phòng?"
      description={
        assignment
          ? `Phân phòng của ${assignment.studentName} tại ${assignment.roomCode} sẽ được hủy và hóa đơn chưa thanh toán sẽ tự động được xóa. Lưu ý: Tuyệt đối không áp dụng nếu sinh viên đã thanh toán tiền phòng.`
          : ""
      }
      confirmLabel="Hủy xếp phòng"
      isLoading={cancel.isPending}
      onConfirm={() => {
        if (!assignment) return;
        void cancel
          .mutateAsync({ id: assignment.id })
          .then(() => {
            onClose();
            toast.success(
              "Đã hủy phân phòng và dọn dẹp hóa đơn chưa thanh toán.",
            );
          })
          .catch((error: unknown) =>
            toast.error(
              error instanceof Error
                ? error.message
                : "Không thể hủy phân phòng.",
            ),
          );
      }}
    />
  );
}

export function RefundAndCancelDialog({
  assignment,
  onClose,
}: {
  assignment: Assignment | null;
  onClose: () => void;
}) {
  const refundAndCancel = useRefundAndCancelAssignment();
  const [refundAmount, setRefundAmount] = useState<number>(0);
  const [refundReason, setRefundReason] = useState<string>("");
  const [bankName, setBankName] = useState<string>("");
  const [bankAccountNumber, setBankAccountNumber] = useState<string>("");
  const [bankAccountHolder, setBankAccountHolder] = useState<string>("");
  const [transactionReference, setTransactionReference] = useState<string>("");

  useEffect(() => {
    if (assignment) {
      setRefundAmount(0);
      setRefundReason("");
      setBankName("");
      setBankAccountNumber("");
      setBankAccountHolder(assignment.studentName || "");
      setTransactionReference("");
    }
  }, [assignment]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignment) return;
    if (!refundReason.trim()) {
      toast.error("Vui lòng nhập lý do hoàn tiền và không ở KTX.");
      return;
    }
    if (refundAmount <= 0) {
      toast.error("Vui lòng nhập số tiền hoàn hợp lệ (> 0).");
      return;
    }
    if (
      !bankName.trim() ||
      !bankAccountNumber.trim() ||
      !bankAccountHolder.trim()
    ) {
      toast.error(
        "Vui lòng nhập đầy đủ thông tin tài khoản ngân hàng nhận tiền.",
      );
      return;
    }

    refundAndCancel
      .mutateAsync({
        assignmentId: assignment.id,
        refundAmount,
        refundReason: refundReason.trim(),
        bankName: bankName.trim(),
        bankAccountNumber: bankAccountNumber.trim(),
        bankAccountHolder: bankAccountHolder.trim(),
        transactionReference: transactionReference.trim() || undefined,
      })
      .then(() => {
        toast.success("Đã hoàn tiền và hủy phòng thành công.");
        onClose();
      })
      .catch((error: unknown) => {
        toast.error(
          error instanceof Error
            ? error.message
            : "Không thể hoàn tiền và hủy phòng.",
        );
      });
  };

  return (
    <ResponsiveDialog
      open={Boolean(assignment)}
      onOpenChange={(open) => {
        if (!open && !refundAndCancel.isPending) onClose();
      }}
    >
      <ResponsiveDialogContent className="sm:max-w-[550px]">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle className="flex items-center gap-2 text-destructive">
            <RotateCcw className="size-5" />
            Quy trình ngược: Hủy phòng & Hoàn tiền
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Áp dụng cho sinh viên đã thanh toán tiền phòng nhưng có lý do xin
            rút không ở KTX nữa.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        {assignment && (
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <div className="rounded-lg border bg-muted/40 p-3 text-xs space-y-1">
              <div>
                <span className="font-semibold text-muted-foreground">
                  Sinh viên:{" "}
                </span>
                <span className="font-bold text-foreground">
                  {assignment.studentName}
                </span>{" "}
                ({assignment.studentCode})
              </div>
              <div>
                <span className="font-semibold text-muted-foreground">
                  Phòng đang xếp:{" "}
                </span>
                <span className="font-semibold text-foreground">
                  {assignment.roomCode}
                </span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="refund-amount">
                  Số tiền hoàn lại (VNĐ){" "}
                  <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="refund-amount"
                  type="number"
                  min={1000}
                  step={10000}
                  placeholder="Nhập số tiền hoàn trả..."
                  value={refundAmount || ""}
                  onChange={(e) => setRefundAmount(Number(e.target.value))}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="refund-reason">
                  Lý do xin rút và hoàn tiền{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <Textarea
                  id="refund-reason"
                  rows={2}
                  placeholder="Nhập lý do sinh viên xin rút không ở KTX và hoàn tiền..."
                  value={refundReason}
                  onChange={(e) => setRefundReason(e.target.value)}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="bank-name">
                    Ngân hàng nhận <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="bank-name"
                    placeholder="VD: Vietcombank, MB..."
                    value={bankName}
                    onChange={(e) => setBankName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="bank-acc">
                    Số tài khoản <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="bank-acc"
                    placeholder="Số tài khoản ngân hàng..."
                    value={bankAccountNumber}
                    onChange={(e) => setBankAccountNumber(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="bank-holder">
                    Tên chủ tài khoản{" "}
                    <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="bank-holder"
                    placeholder="VD: NGUYEN VAN A"
                    value={bankAccountHolder}
                    onChange={(e) => setBankAccountHolder(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="trans-ref">Mã giao dịch hoàn (nếu có)</Label>
                  <Input
                    id="trans-ref"
                    placeholder="Mã GD ngân hàng..."
                    value={transactionReference}
                    onChange={(e) => setTransactionReference(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-2.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
              Hệ thống sẽ: <strong>Void thanh toán</strong>, chuyển hóa đơn sang{" "}
              <strong>Đã hủy</strong> kèm biên nhận hoàn tiền, chuyển trạng thái
              phân phòng sang <strong>Đã hủy</strong> (giải phóng 1 chỗ trống),
              chuyển hồ sơ sang <strong>Đã hủy</strong> và thông báo cho sinh
              viên.
            </div>

            <ResponsiveDialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                disabled={refundAndCancel.isPending}
                onClick={onClose}
              >
                Đóng
              </Button>
              <Button
                type="submit"
                variant="destructive"
                disabled={refundAndCancel.isPending}
              >
                {refundAndCancel.isPending
                  ? "Đang xử lý..."
                  : "Xác nhận Hoàn tiền & Hủy phòng"}
              </Button>
            </ResponsiveDialogFooter>
          </form>
        )}
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

export function CheckInDialog({
  assignment,
  onClose,
}: {
  assignment: Assignment | null;
  onClose: () => void;
}) {
  const checkIn = useCheckIn();
  const [startDate, setStartDate] = useState<Date | undefined>(undefined);
  const [expectedEndDate, setExpectedEndDate] = useState<Date | undefined>(
    undefined,
  );
  const [note, setNote] = useState("");

  useEffect(() => {
    if (assignment) {
      setStartDate(new Date());
      setExpectedEndDate(undefined);
      setNote("");
    }
  }, [assignment]);

  const submit = () => {
    if (!assignment || !startDate) {
      toast.error("Hãy chọn ngày nhận phòng.");
      return;
    }
    void checkIn
      .mutateAsync({
        assignmentId: assignment.id,
        startDate: formatDateOnly(startDate),
        expectedEndDate: expectedEndDate
          ? formatDateOnly(expectedEndDate)
          : undefined,
        note: note.trim() || undefined,
      })
      .then(() => {
        onClose();
        toast.success("Đã xác nhận nhận phòng.");
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof ApiError
            ? error.message
            : "Không thể xác nhận nhận phòng.",
        ),
      );
  };

  return (
    <ResponsiveDialog
      open={Boolean(assignment)}
      onOpenChange={(open) => {
        if (!open && !checkIn.isPending) onClose();
      }}
    >
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] w-full max-w-lg flex-col overflow-hidden p-0 gap-0 shadow-xl">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-6 py-4 pr-12">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base sm:text-lg font-bold">
            <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground shrink-0">
              <LogIn className="size-4" />
            </div>
            <span>Xác nhận nhận phòng</span>
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs text-muted-foreground mt-0.5">
            Chuyển phân phòng sang trạng thái đã nhận phòng và bắt đầu theo dõi
            cư trú.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        {assignment ? (
          <div className="min-h-0 flex-1 overflow-y-auto space-y-3.5 px-6 py-4">
            <div className="rounded-lg border bg-muted/20 px-3.5 py-2.5 text-xs">
              <p className="font-semibold text-foreground">
                {assignment.studentName}
              </p>
              <p className="text-muted-foreground">
                Mã SV: {assignment.studentCode} · Phòng: {assignment.roomCode}
              </p>
            </div>
            <div className="space-y-1.5">
              <Label
                htmlFor="check-in-start-date"
                className="text-xs font-medium"
              >
                Ngày nhận phòng <span className="text-destructive">*</span>
              </Label>
              <DatePicker
                id="check-in-start-date"
                value={startDate}
                onChange={setStartDate}
              />
            </div>
            <div className="space-y-1.5">
              <Label
                htmlFor="check-in-expected-end-date"
                className="text-xs font-medium"
              >
                Ngày dự kiến trả phòng (không bắt buộc)
              </Label>
              <DatePicker
                id="check-in-expected-end-date"
                value={expectedEndDate}
                onChange={setExpectedEndDate}
                minDate={startDate}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="check-in-note" className="text-xs font-medium">
                Ghi chú bàn giao
              </Label>
              <Textarea
                id="check-in-note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Ghi chú nhận phòng (không bắt buộc)"
                rows={2}
                className="text-xs"
              />
            </div>
          </div>
        ) : null}

        <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6 sm:py-3.5">
          <div className="grid grid-cols-2 gap-3 w-full sm:flex sm:w-auto sm:items-center sm:justify-end sm:gap-2.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full sm:w-auto h-9 text-xs"
              disabled={checkIn.isPending}
              onClick={onClose}
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              className="w-full sm:w-auto h-9 text-xs font-semibold"
              disabled={checkIn.isPending || !startDate}
              onClick={submit}
            >
              {checkIn.isPending ? "Đang lưu..." : "Xác nhận nhận phòng"}
            </Button>
          </div>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

export function BatchCheckInDialog({
  open,
  selectedAssignments = [],
  periodId,
  periodName,
  onClose,
  onSuccess,
}: {
  open: boolean;
  selectedAssignments?: Assignment[];
  periodId?: string;
  periodName?: string;
  onClose: () => void;
  onSuccess?: () => void;
}) {
  const checkInBatch = useCheckInBatch();
  const [startDate, setStartDate] = useState<Date | undefined>(new Date());
  const [expectedEndDate, setExpectedEndDate] = useState<Date | undefined>(
    undefined,
  );
  const [note, setNote] = useState("");

  useEffect(() => {
    if (open) {
      setStartDate(new Date());
      setExpectedEndDate(undefined);
      setNote("");
    }
  }, [open]);

  const count = selectedAssignments.length;
  const isPeriodMode = Boolean(periodId);

  const submit = () => {
    if (!startDate) {
      toast.error("Hãy chọn ngày nhận phòng.");
      return;
    }

    if (!isPeriodMode && count === 0) {
      toast.error("Chưa chọn sinh viên nào để nhận phòng.");
      return;
    }

    void checkInBatch
      .mutateAsync({
        assignmentIds: isPeriodMode
          ? undefined
          : selectedAssignments.map((a) => a.id),
        registrationPeriodId: isPeriodMode ? periodId : undefined,
        startDate: formatDateOnly(startDate),
        expectedEndDate: expectedEndDate
          ? formatDateOnly(expectedEndDate)
          : undefined,
        note: note.trim() || undefined,
      })
      .then((res) => {
        onClose();
        if (onSuccess) onSuccess();
        toast.success(
          `Đã nhận phòng thành công cho ${res.succeededCount}/${res.totalRequested} sinh viên.${
            res.failedCount > 0
              ? ` (${res.failedCount} sinh viên bỏ qua do lỗi)`
              : ""
          }`,
        );
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof ApiError
            ? error.message
            : "Không thể nhận phòng hàng loạt.",
        ),
      );
  };

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen && !checkInBatch.isPending) onClose();
      }}
    >
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] w-full max-w-lg flex-col overflow-hidden p-0 gap-0 shadow-xl">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-6 py-4 pr-12">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base sm:text-lg font-bold">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
              <CheckCheck className="size-4" />
            </div>
            <span>
              {isPeriodMode
                ? "Nhận phòng toàn bộ đợt"
                : `Nhận phòng hàng loạt (${count} sinh viên)`}
            </span>
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs text-muted-foreground mt-0.5">
            {isPeriodMode
              ? `Tất cả các sinh viên đã được xếp phòng trong đợt '${periodName ?? "đã chọn"}' sẽ chuyển sang trạng thái đã nhận phòng.`
              : `Xác nhận nhận phòng cùng lúc cho ${count} sinh viên đã chọn.`}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <div className="min-h-0 flex-1 overflow-y-auto space-y-3.5 px-6 py-4">
          <div className="rounded-lg border bg-primary/5 border-primary/20 px-3.5 py-2.5 text-xs text-foreground">
            <div className="flex items-center gap-2 font-medium">
              <Users className="size-4 text-primary shrink-0" />
              <span>
                {isPeriodMode
                  ? `Áp dụng cho tất cả phân phòng hợp lệ của đợt: ${periodName ?? ""}`
                  : `Đang chọn ${count} sinh viên để bàn giao phòng đồng loạt`}
              </span>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="batch-start-date" className="text-xs font-medium">
              Ngày nhận phòng áp dụng{" "}
              <span className="text-destructive">*</span>
            </Label>
            <DatePicker
              id="batch-start-date"
              value={startDate}
              onChange={setStartDate}
            />
          </div>

          <div className="space-y-1.5">
            <Label
              htmlFor="batch-expected-end-date"
              className="text-xs font-medium"
            >
              Ngày dự kiến kết thúc (không bắt buộc)
            </Label>
            <DatePicker
              id="batch-expected-end-date"
              value={expectedEndDate}
              onChange={setExpectedEndDate}
              minDate={startDate}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="batch-note" className="text-xs font-medium">
              Ghi chú chung đợt bàn giao
            </Label>
            <Textarea
              id="batch-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Ví dụ: Bàn giao chìa khóa tập trung đầu năm học..."
              rows={2}
              className="text-xs"
            />
          </div>
        </div>

        <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6 sm:py-3.5">
          <div className="grid grid-cols-2 gap-3 w-full sm:flex sm:w-auto sm:items-center sm:justify-end sm:gap-2.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full sm:w-auto h-9 text-xs"
              disabled={checkInBatch.isPending}
              onClick={onClose}
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              className="w-full sm:w-auto h-9 text-xs font-semibold"
              disabled={
                checkInBatch.isPending ||
                !startDate ||
                (!isPeriodMode && count === 0)
              }
              onClick={submit}
            >
              {checkInBatch.isPending
                ? "Đang xử lý..."
                : isPeriodMode
                  ? "Xác nhận nhận phòng cả đợt"
                  : `Xác nhận nhận phòng (${count})`}
            </Button>
          </div>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
