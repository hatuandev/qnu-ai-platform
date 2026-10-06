import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import { runtimeConfig } from "@/app/config/runtime";
import type {
  ApplicationDetail,
  ApplicationHistory,
  ApplicationsListParams,
  ApplicationsPage,
  BulkReviewDecision,
  BulkReviewResult,
  DormitoryApplication,
  ReviewPriorityVerificationInput,
  UpdateApplicationInput,
} from "@/features/applications/types";

const path = "/DormitoryApplications";
const reviewPath = "/ApplicationReviews";

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null;

const isPage = (v: unknown): v is ApplicationsPage =>
  isRecord(v) &&
  Array.isArray(v.items) &&
  typeof v.total === "number" &&
  typeof v.page === "number" &&
  typeof v.pageSize === "number" &&
  typeof v.totalPages === "number";

const isApplication = (v: unknown): v is DormitoryApplication =>
  isRecord(v) &&
  typeof v.id === "string" &&
  typeof v.applicationCode === "string" &&
  typeof v.studentName === "string";

export const applicationsQueryKeys = {
  all: ["applications"] as const,
  list: (params: ApplicationsListParams) =>
    [...applicationsQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...applicationsQueryKeys.all, "detail", id] as const,
  history: (id: string) =>
    [...applicationsQueryKeys.all, "history", id] as const,
};

export function useApplicationsQuery(params: ApplicationsListParams) {
  return useQuery({
    queryKey: applicationsQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(path, {
        searchParams: {
          RegistrationPeriodId: params.registrationPeriodId,
          Status: params.status,
          SearchStudentCodeOrName: params.search,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isPage(response))
        throw new Error(
          "Phản hồi danh sách hồ sơ đăng ký không đúng định dạng.",
        );
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useApplicationQuery(id: string) {
  return useQuery({
    queryKey: applicationsQueryKeys.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${path}/${id}`);
      if (!isApplication(response))
        throw new Error("Phản hồi chi tiết hồ sơ không đúng định dạng.");
      return response as ApplicationDetail;
    },
    enabled: Boolean(id),
  });
}

export function useApplicationHistoryQuery(id: string) {
  return useQuery({
    queryKey: applicationsQueryKeys.history(id),
    queryFn: () => apiClient.get<ApplicationHistory[]>(`${path}/${id}/history`),
    enabled: Boolean(id),
  });
}

function reviewMutation(action: "approve" | "reject" | "request-supplement") {
  return function useReview() {
    const client = useQueryClient();
    return useMutation({
      mutationFn: ({ id, reviewNote }: { id: string; reviewNote?: string }) =>
        apiClient.post<void>(`${reviewPath}/${id}/${action}`, {
          applicationId: id,
          reviewNote,
        }),
      onSuccess: (_data, variables) => {
        void client.invalidateQueries({ queryKey: applicationsQueryKeys.all });
        void client.invalidateQueries({
          queryKey: applicationsQueryKeys.detail(variables.id),
        });
      },
    });
  };
}

export const useApproveApplication = reviewMutation("approve");
export const useRejectApplication = reviewMutation("reject");
export const useRequestApplicationSupplement =
  reviewMutation("request-supplement");

export function useBulkReviewApplications() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      applicationIds: string[];
      decision: BulkReviewDecision;
      reviewNote?: string;
    }) => apiClient.post<BulkReviewResult>(`${reviewPath}/bulk`, input),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: applicationsQueryKeys.all });
    },
  });
}

export type BulkApprovePeriodResult = {
  approvedCount: number;
  periodName: string;
};

export function useBulkApprovePeriodApplications() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      registrationPeriodId: string;
      reviewNote?: string;
    }) =>
      apiClient.post<BulkApprovePeriodResult>(
        `${reviewPath}/bulk-approve-period`,
        input,
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: applicationsQueryKeys.all });
    },
  });
}

export function useReviewPriorityVerification() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: ReviewPriorityVerificationInput;
    }) =>
      apiClient.post<void>(`${reviewPath}/${id}/priority-verification`, {
        applicationId: id,
        ...input,
      }),
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: applicationsQueryKeys.all });
      void client.invalidateQueries({
        queryKey: applicationsQueryKeys.detail(variables.id),
      });
    },
  });
}

export function attachmentDownloadUrl(
  applicationId: string,
  attachmentId: string,
): string {
  return `/api${path}/${applicationId}/attachments/${attachmentId}`;
}

export type CreateApplicationInput = {
  studentId: string;
  registrationPeriodId: string;
  requestedRoomTypeId?: string;
  priorityObjectId?: string;
  gender?: string;
  reason?: string;
  initialStatus?: "submitted" | "approved" | "draft";
};

export function useCreateApplication() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateApplicationInput) =>
      apiClient.post<string>(path, input),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: applicationsQueryKeys.all });
      void client.invalidateQueries({ queryKey: ["students"] });
    },
  });
}

export function useUpdateApplication() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: UpdateApplicationInput;
    }) => apiClient.put<void>(`${path}/${id}`, input),
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: applicationsQueryKeys.all });
      void client.invalidateQueries({
        queryKey: applicationsQueryKeys.detail(variables.id),
      });
      void client.invalidateQueries({
        queryKey: applicationsQueryKeys.history(variables.id),
      });
    },
  });
}

export function useDeleteApplication() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete<void>(`${path}/${id}`),
    onSuccess: (_data, id) => {
      void client.invalidateQueries({ queryKey: applicationsQueryKeys.all });
      void client.removeQueries({ queryKey: applicationsQueryKeys.detail(id) });
      void client.invalidateQueries({ queryKey: ["room-assignments"] });
      void client.invalidateQueries({ queryKey: ["invoices"] });
    },
  });
}

export async function exportApplicationsToExcel(params: {
  registrationPeriodId?: string;
  status?: string;
  search?: string;
}) {
  const queryParams = new URLSearchParams();
  if (params.registrationPeriodId) {
    queryParams.append("RegistrationPeriodId", params.registrationPeriodId);
  }
  if (params.status) {
    queryParams.append("Status", params.status);
  }
  if (params.search) {
    queryParams.append("SearchStudentCodeOrName", params.search);
  }

  const queryString = queryParams.toString();
  const url = `${runtimeConfig.apiBaseUrl}${path}/export${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(
      "Không thể xuất file Excel hồ sơ đăng ký. Vui lòng thử lại sau.",
    );
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get("content-disposition");
  let fileName = `DanhSach_HoSoDangKy_${new Date().toISOString().slice(0, 10)}.xlsx`;
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(
      /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/,
    );
    if (filenameMatch?.[1]) {
      fileName = filenameMatch[1].replace(/['"]/g, "");
    }
  }

  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(downloadUrl);
}

export function useImportApplications() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({
      file,
      registrationPeriodId,
    }: {
      file: File;
      registrationPeriodId: string;
    }) => {
      const formData = new FormData();
      formData.append("RegistrationPeriodId", registrationPeriodId);
      formData.append("File", file);
      return apiClient.post<
        import("./types").ImportDormitoryApplicationsResult
      >(`${path}/import`, formData);
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: applicationsQueryKeys.all });
    },
  });
}

export async function downloadApplicationsImportTemplate() {
  const url = `${runtimeConfig.apiBaseUrl}${path}/import-template`;
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Không thể tải file mẫu Excel. Vui lòng thử lại sau.");
  }

  const blob = await response.blob();
  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = "Danh_Sach_Dang_Ky_KTX_Template.xlsx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(downloadUrl);
}
