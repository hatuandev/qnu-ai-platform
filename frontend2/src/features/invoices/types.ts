export type InvoiceStatus = "unpaid" | "partial" | "paid" | "cancelled";

export const invoiceStatusLabels: Record<InvoiceStatus, string> = {
  unpaid: "Chưa thanh toán",
  partial: "Thanh toán một phần",
  paid: "Đã thanh toán",
  cancelled: "Đã hủy",
};

export type InvoiceBadgeVariant =
  | "secondary"
  | "destructive"
  | "success"
  | "warning";

export const invoiceStatusVariants: Record<InvoiceStatus, InvoiceBadgeVariant> =
  {
    unpaid: "destructive",
    partial: "warning",
    paid: "success",
    cancelled: "secondary",
  };
export type PaymentMethod = "cash" | "bank_transfer" | "other";
export type PaymentStatus = "completed" | "voided";
export type Invoice = {
  id: string;
  invoiceCode: string;
  studentCode: string;
  studentName: string;
  academicYearCode: string;
  registrationPeriodId?: string | null;
  registrationPeriodCode?: string | null;
  registrationPeriodName?: string | null;
  totalAmount: number;
  paidAmount: number;
  remainingAmount: number;
  status: InvoiceStatus;
  dueDate?: string | null;
  issuedAt: string;
};
export type InvoicePage = {
  items: Invoice[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
export type InvoiceLine = {
  id: string;
  description: string;
  quantity: number;
  unitAmount: number;
  lineAmount: number;
};
export type InvoiceDetail = Invoice & {
  studentId: string;
  faculty?: string | null;
  residenceId?: string | null;
  academicYearId: string;
  note?: string | null;
  lines: InvoiceLine[];
  created: string;
  createdBy?: string | null;
  lastModified: string;
  lastModifiedBy?: string | null;
};
export type Payment = {
  id: string;
  invoiceId: string;
  amount: number;
  paidAt: string;
  paymentMethod: PaymentMethod;
  status: PaymentStatus;
  voidedAt?: string | null;
  voidedBy?: string | null;
  referenceNo?: string | null;
  receivedBy?: string | null;
  note?: string | null;
};
export type Debt = {
  studentId: string;
  studentCode: string;
  studentName: string;
  faculty?: string | null;
  roomId?: string | null;
  roomCode?: string | null;
  roomName?: string | null;
  buildingCode?: string | null;
  buildingName?: string | null;
  floorNumber?: number | null;
  invoiceCount: number;
  totalDebt: number;
};
export type InvoiceListParams = {
  studentId?: string;
  academicYearId?: string;
  registrationPeriodId?: string;
  status?: InvoiceStatus;
  search?: string;
  page: number;
  pageSize: number;
};
export type DebtListParams = {
  academicYearId?: string;
  roomId?: string;
  search?: string;
};
export type GenerateInvoiceInput = {
  residenceId: string;
  dueDate?: string;
  note?: string;
};
export type GenerateBatchInput = {
  academicYearId: string;
  registrationPeriodId: string;
  dueDate?: string;
  note?: string;
};
export type GenerateBatchResult = {
  generated: number;
  skipped: number;
  errors: string[];
};
export type CreatePaymentInput = {
  invoiceId: string;
  amount: number;
  paymentMethod: PaymentMethod;
  referenceNo?: string;
  receivedBy?: string;
  note?: string;
};
