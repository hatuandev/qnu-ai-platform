import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  CreatePaymentInput,
  Debt,
  DebtListParams,
  GenerateBatchInput,
  GenerateBatchResult,
  GenerateInvoiceInput,
  InvoiceDetail,
  InvoiceListParams,
  InvoicePage,
  Payment,
} from "@/features/invoices/types";

const path = "/Invoices";
const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;
const isPage = (value: unknown): value is InvoicePage =>
  isRecord(value) &&
  Array.isArray(value.items) &&
  typeof value.total === "number" &&
  typeof value.page === "number" &&
  typeof value.pageSize === "number" &&
  typeof value.totalPages === "number";

export const invoiceQueryKeys = {
  all: ["invoices"] as const,
  list: (params: InvoiceListParams) =>
    [...invoiceQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...invoiceQueryKeys.all, "detail", id] as const,
  payments: (id: string) => [...invoiceQueryKeys.all, "payments", id] as const,
  debts: (params: DebtListParams) =>
    [...invoiceQueryKeys.all, "debts", params] as const,
};

export function useInvoicesQuery(params: InvoiceListParams) {
  return useQuery({
    queryKey: invoiceQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(path, {
        searchParams: {
          StudentId: params.studentId,
          AcademicYearId: params.academicYearId,
          RegistrationPeriodId: params.registrationPeriodId,
          Status: params.status,
          SearchStudentCodeOrName: params.search,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isPage(response))
        throw new Error("Phản hồi danh sách hóa đơn không hợp lệ.");
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useInvoiceQuery(id: string) {
  return useQuery({
    queryKey: invoiceQueryKeys.detail(id),
    queryFn: () => apiClient.get<InvoiceDetail>(`${path}/${id}`),
    enabled: Boolean(id),
  });
}

export function useInvoicePaymentsQuery(id: string) {
  return useQuery({
    queryKey: invoiceQueryKeys.payments(id),
    queryFn: () => apiClient.get<Payment[]>(`${path}/${id}/payments`),
    enabled: Boolean(id),
  });
}

export function useDebtListQuery(params: DebtListParams) {
  return useQuery({
    queryKey: invoiceQueryKeys.debts(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${path}/debts`, {
        searchParams: {
          AcademicYearId: params.academicYearId,
          RoomId: params.roomId,
          SearchStudentCodeOrName: params.search,
        },
      });
      if (Array.isArray(response)) return response as Debt[];
      if (isRecord(response) && Array.isArray(response.items)) {
        return response.items as Debt[];
      }
      throw new Error("Phản hồi danh sách công nợ không hợp lệ.");
    },
  });
}

function invalidate(
  client: ReturnType<typeof useQueryClient>,
  invoiceId?: string,
) {
  void client.invalidateQueries({ queryKey: invoiceQueryKeys.all });
  void client.invalidateQueries({ queryKey: ["payments"] });
  void client.invalidateQueries({ queryKey: ["residencies"] });
  void client.invalidateQueries({ queryKey: ["room-assignments"] });
  void client.invalidateQueries({ queryKey: ["notifications"] });
  if (invoiceId) {
    void client.invalidateQueries({
      queryKey: invoiceQueryKeys.detail(invoiceId),
    });
    void client.invalidateQueries({
      queryKey: invoiceQueryKeys.payments(invoiceId),
    });
  }
}

export function useGenerateInvoice() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: GenerateInvoiceInput) =>
      apiClient.post<string>(`${path}/generate`, input),
    onSuccess: () => invalidate(client),
  });
}

export function useGenerateInvoicesBatch() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: GenerateBatchInput) =>
      apiClient.post<GenerateBatchResult>(`${path}/generate-batch`, input),
    onSuccess: () => invalidate(client),
  });
}

export function useCreatePayment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: CreatePaymentInput) =>
      apiClient.post<string>(`${path}/${input.invoiceId}/payments`, input),
    onSuccess: (_data, variables) => invalidate(client, variables.invoiceId),
  });
}

export function useVoidPayment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ paymentId, note }: { paymentId: string; note?: string }) =>
      apiClient.request<void>(`${path}/payments/${paymentId}`, {
        method: "DELETE",
        body: { paymentId, note },
      }),
    onSuccess: () => invalidate(client),
  });
}

export function useDeleteInvoice() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      apiClient.request<void>(
        `${path}/${id}${reason ? `?reason=${encodeURIComponent(reason)}` : ""}`,
        {
          method: "DELETE",
        },
      ),
    onSuccess: () => invalidate(client),
  });
}

export async function exportInvoicesToExcel(params: {
  studentId?: string;
  academicYearId?: string;
  registrationPeriodId?: string;
  status?: string;
  search?: string;
}) {
  const searchParams: Record<string, string | undefined> = {
    StudentId: params.studentId,
    AcademicYearId: params.academicYearId,
    RegistrationPeriodId: params.registrationPeriodId,
    Status: params.status,
    SearchStudentCodeOrName: params.search,
  };
  const qs = Object.entries(searchParams)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => (v === undefined ? "" : `${k}=${encodeURIComponent(v)}`))
    .join("&");
  const url = `/api/Invoices/export${qs ? `?${qs}` : ""}`;
  const response = await fetch(url, { credentials: "include" });
  if (!response.ok) throw new Error("Xuất file Excel thất bại.");
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = /filename[^;=\n]*=["']?([^"';\n]+)["']?/.exec(disposition);
  const fileName = match?.[1] ?? "HoaDon_KTX.xlsx";
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(objectUrl);
}

export async function exportDebtsToExcel(params: {
  academicYearId?: string;
  roomId?: string;
  search?: string;
}) {
  const searchParams: Record<string, string | undefined> = {
    AcademicYearId: params.academicYearId,
    RoomId: params.roomId,
    SearchStudentCodeOrName: params.search,
  };
  const qs = Object.entries(searchParams)
    .filter(([, value]) => value !== undefined && value !== "")
    .map(([key, value]) =>
      value === undefined ? "" : `${key}=${encodeURIComponent(value)}`,
    )
    .join("&");
  const url = `/api/Invoices/debts/export${qs ? `?${qs}` : ""}`;
  const response = await fetch(url, { credentials: "include" });
  if (!response.ok) throw new Error("Xuất file Excel công nợ thất bại.");
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = /filename[^;=\n]*=["']?([^"';\n]+)["']?/.exec(disposition);
  const fileName = match?.[1] ?? "CongNo_KTX.xlsx";
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}
