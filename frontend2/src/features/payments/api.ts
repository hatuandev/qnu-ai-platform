import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import {
  type PaymentInvoiceListParams,
  type PaymentInvoicePage,
  type PaymentQr,
  type PaymentSubmission,
  type PaymentSubmissionListParams,
  type PaymentSubmissionPage,
  type PaymentSubmissionStatus,
  type PaymentSubmissionsStats,
  paymentSubmissionStatusLabels,
  type SubmitPaymentReceiptInput,
} from "@/features/payments/types";

const path = "/PaymentSubmissions";

export const paymentQueryKeys = {
  all: ["payments"] as const,
  myInvoices: (params: PaymentInvoiceListParams) =>
    [...paymentQueryKeys.all, "my-invoices", params] as const,
  qr: (invoiceId: string) =>
    [...paymentQueryKeys.all, "qr", invoiceId] as const,
  submissions: (params: PaymentSubmissionListParams) =>
    [...paymentQueryKeys.all, "submissions", params] as const,
  stats: (params?: { search?: string; invoiceId?: string }) =>
    [...paymentQueryKeys.all, "stats", params] as const,
  submission: (id: string) =>
    [...paymentQueryKeys.all, "submission", id] as const,
};

export function useMyPaymentInvoicesQuery(
  params: PaymentInvoiceListParams,
  enabled = true,
) {
  return useQuery({
    queryKey: paymentQueryKeys.myInvoices(params),
    queryFn: () =>
      apiClient.get<PaymentInvoicePage>(`${path}/me/invoices`, {
        searchParams: {
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      }),
    enabled,
    staleTime: 30_000,
    retry: false,
  });
}

export function usePaymentQrQuery(invoiceId?: string, enabled = true) {
  return useQuery({
    queryKey: paymentQueryKeys.qr(invoiceId ?? "none"),
    queryFn: () =>
      apiClient.get<PaymentQr>(`${path}/me/invoices/${invoiceId}/qr`),
    enabled: Boolean(invoiceId) && enabled,
    staleTime: 30_000,
    retry: false,
  });
}

export function usePaymentSubmissionsQuery(
  params: PaymentSubmissionListParams,
  enabled = true,
) {
  return useQuery({
    queryKey: paymentQueryKeys.submissions(params),
    queryFn: () =>
      apiClient.get<PaymentSubmissionPage>(path, {
        searchParams: {
          InvoiceId: params.invoiceId,
          Status: params.status,
          SearchStudentCodeOrName: params.search,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      }),
    placeholderData: (previous) => previous,
    enabled,
  });
}

export function usePaymentSubmissionsStatsQuery(
  params?: { search?: string; invoiceId?: string },
  enabled = true,
) {
  return useQuery({
    queryKey: paymentQueryKeys.stats(params),
    queryFn: () =>
      apiClient.get<PaymentSubmissionsStats>(`${path}/stats`, {
        searchParams: {
          InvoiceId: params?.invoiceId,
          SearchStudentCodeOrName: params?.search,
        },
      }),
    enabled,
    staleTime: 10_000,
  });
}

export function usePaymentSubmissionQuery(id?: string, enabled = true) {
  return useQuery({
    queryKey: paymentQueryKeys.submission(id ?? "none"),
    queryFn: () => apiClient.get<PaymentSubmission>(path + "/" + id),
    enabled: Boolean(id) && enabled,
  });
}

export function useSubmitPaymentReceipt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: SubmitPaymentReceiptInput) => {
      const body = new FormData();
      body.append("InvoiceId", input.invoiceId);
      body.append("Receipt", input.receipt);

      return apiClient.post<string>(path, body);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: paymentQueryKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["invoices"] });
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

function invalidateSubmissions(
  client: ReturnType<typeof useQueryClient>,
  id?: string,
) {
  void client.invalidateQueries({
    queryKey: paymentQueryKeys.submissions({ page: 1, pageSize: 20 }),
  });
  void client.invalidateQueries({ queryKey: paymentQueryKeys.all });
  void client.invalidateQueries({ queryKey: ["invoices"] });
  void client.invalidateQueries({ queryKey: ["residencies"] });
  void client.invalidateQueries({ queryKey: ["room-assignments"] });
  void client.invalidateQueries({ queryKey: ["notifications"] });
  if (id) {
    void client.invalidateQueries({
      queryKey: paymentQueryKeys.submission(id),
    });
  }
}

export function useVerifyPaymentSubmission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      reviewNote,
      referenceNo,
    }: {
      id: string;
      reviewNote?: string;
      referenceNo?: string;
    }) =>
      apiClient.post<void>(path + "/" + id + "/verify", {
        reviewNote: reviewNote?.trim() || undefined,
        referenceNo: referenceNo?.trim() || undefined,
      }),
    onSuccess: (_data, variables) =>
      invalidateSubmissions(queryClient, variables.id),
  });
}

export function useRejectPaymentSubmission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, reviewNote }: { id: string; reviewNote: string }) =>
      apiClient.post<void>(path + "/" + id + "/reject", {
        reviewNote: reviewNote.trim(),
      }),
    onSuccess: (_data, variables) =>
      invalidateSubmissions(queryClient, variables.id),
  });
}

export async function exportPaymentSubmissionsToExcel(params: {
  status?: PaymentSubmissionStatus;
  search?: string;
  invoiceId?: string;
}) {
  const { exportToExcel } = await import("@/lib/excel-export");
  const { formatDateTimeValue } = await import("@/lib/date-utils");

  const res = await apiClient.get<PaymentSubmissionPage>(path, {
    searchParams: {
      InvoiceId: params.invoiceId,
      Status: params.status,
      SearchStudentCodeOrName: params.search,
      PageIndex: 1,
      PageSize: 10000,
    },
  });

  const items = res?.items ?? [];
  exportToExcel<PaymentSubmission>({
    filename: `doi_soat_thanh_toan_${new Date().toISOString().slice(0, 10)}.xlsx`,
    sheetName: "Nộp thanh toán",
    data: items,
    columns: [
      { header: "STT", accessor: (_item, index) => (index ?? 0) + 1, width: 6 },
      {
        header: "Mã sinh viên",
        accessor: (item) => item.studentCode,
        width: 14,
      },
      { header: "Họ và tên", accessor: (item) => item.studentName, width: 24 },
      { header: "Mã hóa đơn", accessor: (item) => item.invoiceCode, width: 24 },
      { header: "Số tiền (VNĐ)", accessor: (item) => item.amount, width: 16 },
      {
        header: "Ngày nộp",
        accessor: (item) =>
          item.submittedAt ? formatDateTimeValue(item.submittedAt) : "—",
        width: 20,
      },
      {
        header: "Nội dung chuyển khoản",
        accessor: (item) => item.transferContent || "—",
        width: 30,
      },
      {
        header: "Mã tham chiếu",
        accessor: (item) => item.referenceNo || "—",
        width: 18,
      },
      {
        header: "Tên tệp biên lai",
        accessor: (item) => item.receiptFileName || "—",
        width: 26,
      },
      {
        header: "Trạng thái",
        accessor: (item) =>
          paymentSubmissionStatusLabels[item.status] ?? item.status,
        width: 16,
      },
      {
        header: "Thời điểm xử lý",
        accessor: (item) =>
          item.reviewedAt ? formatDateTimeValue(item.reviewedAt) : "—",
        width: 20,
      },
      {
        header: "Ghi chú xử lý",
        accessor: (item) => item.reviewNote || "—",
        width: 30,
      },
    ],
  });
}
