export type PaymentInvoiceStatus = "unpaid" | "partial" | "paid" | "cancelled";

export type PaymentSubmissionStatus =
  | "submitted"
  | "verified"
  | "rejected"
  | "cancelled";

export {
  invoiceStatusLabels as paymentInvoiceStatusLabels,
  invoiceStatusVariants as paymentInvoiceStatusVariants,
} from "@/features/invoices/types";

export const paymentSubmissionStatusLabels: Record<
  PaymentSubmissionStatus,
  string
> = {
  submitted: "Chờ xác nhận",
  verified: "Đã xác nhận",
  rejected: "Cần nộp lại",
  cancelled: "Đã hủy",
};

export type PaymentSubmissionBadgeVariant =
  | "secondary"
  | "destructive"
  | "success"
  | "warning";

export const paymentSubmissionStatusVariants: Record<
  PaymentSubmissionStatus,
  PaymentSubmissionBadgeVariant
> = {
  submitted: "warning",
  verified: "success",
  rejected: "destructive",
  cancelled: "secondary",
};

export type PaymentSubmissionsStats = {
  total: number;
  submitted: number;
  verified: number;
  rejected: number;
  cancelled: number;
};

export type PaymentSubmissionSummary = {
  id: string;
  amount: number;
  status: PaymentSubmissionStatus;
  receiptFileName: string;
  submittedAt: string;
  reviewedAt?: string | null;
  reviewNote?: string | null;
};

export type PaymentSubmission = {
  id: string;
  invoiceId: string;
  invoiceCode: string;
  studentId: string;
  studentCode: string;
  studentName: string;
  amount: number;
  paymentMethod: string;
  status: PaymentSubmissionStatus;
  transferContent: string;
  receiptFileName: string;
  receiptContentType?: string | null;
  receiptSizeBytes?: number | null;
  referenceNo?: string | null;
  submittedAt: string;
  reviewedAt?: string | null;
  reviewedByUserId?: string | null;
  reviewNote?: string | null;
  paymentId?: string | null;
};

export type PaymentSubmissionPage = {
  items: PaymentSubmission[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type PaymentSubmissionListParams = {
  invoiceId?: string;
  status?: PaymentSubmissionStatus;
  search?: string;
  page: number;
  pageSize: number;
};

export type PaymentInvoice = {
  id: string;
  invoiceCode: string;
  registrationPeriodId?: string | null;
  registrationPeriodCode?: string | null;
  registrationPeriodName?: string | null;
  totalAmount: number;
  paidAmount: number;
  remainingAmount: number;
  status: PaymentInvoiceStatus;
  dueDate?: string | null;
  issuedAt: string;
  latestSubmission?: PaymentSubmissionSummary | null;
};

export type PaymentInvoicePage = {
  items: PaymentInvoice[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type PaymentQr = {
  invoiceId: string;
  invoiceCode: string;
  studentCode: string;
  amount: number;
  currency: string;
  enabled: boolean;
  bankCode: string;
  accountNumber: string;
  accountName: string;
  transferContent: string;
  instructionText: string;
  qrMode: string;
  qrImageUrl?: string | null;
};

export type PaymentInvoiceListParams = {
  page: number;
  pageSize: number;
};

export type SubmitPaymentReceiptInput = {
  invoiceId: string;
  receipt: File;
};
