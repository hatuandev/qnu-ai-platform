import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  MyApplication,
  MyNotification,
  OpenRegistrationPeriod,
  StudentRegistrationCatalog,
  StudentRoomSelection,
  SubmitStudentApplicationInput,
  SubmitStudentApplicationWithEvidenceInput,
} from "@/features/student/types";

const applicationsPath = "/DormitoryApplications";
const periodsPath = "/RegistrationPeriods/open";
const catalogPath = "/StudentRegistrationCatalog";

export const studentQueryKeys = {
  all: ["student"] as const,
  openPeriods: () => [...studentQueryKeys.all, "open-periods"] as const,
  catalog: () => [...studentQueryKeys.all, "catalog"] as const,
  roomSelection: (registrationPeriodId: string) =>
    [...studentQueryKeys.all, "room-selection", registrationPeriodId] as const,
  applications: () => [...studentQueryKeys.all, "applications"] as const,
  notifications: () => [...studentQueryKeys.all, "notifications"] as const,
};

export function useOpenRegistrationPeriodsQuery() {
  return useQuery({
    queryKey: studentQueryKeys.openPeriods(),
    queryFn: () => apiClient.get<OpenRegistrationPeriod[]>(periodsPath),
    staleTime: 60_000,
  });
}

export function useStudentRoomSelectionQuery(registrationPeriodId?: string) {
  return useQuery({
    queryKey: studentQueryKeys.roomSelection(registrationPeriodId ?? "none"),
    queryFn: () =>
      apiClient.get<StudentRoomSelection>("/RoomAssignments/my-selection", {
        searchParams: { registrationPeriodId },
      }),
    enabled: Boolean(registrationPeriodId),
    retry: false,
  });
}

export function useSelectStudentRoom() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      registrationPeriodId: string;
      roomId: string;
      note?: string;
    }) => apiClient.post<string>("/RoomAssignments/select", input),
    onSuccess: (_data, input) => {
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.roomSelection(input.registrationPeriodId),
      });
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.applications(),
      });
    },
  });
}

export function useStudentRegistrationCatalogQuery(
  registrationPeriodId?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: [...studentQueryKeys.catalog(), registrationPeriodId ?? "none"],
    queryFn: () =>
      apiClient.get<StudentRegistrationCatalog>(catalogPath, {
        searchParams: registrationPeriodId
          ? { registrationPeriodId }
          : undefined,
      }),
    enabled,
    staleTime: 5 * 60_000,
  });
}

export function useMyApplicationsQuery() {
  return useQuery({
    queryKey: studentQueryKeys.applications(),
    queryFn: () => apiClient.get<MyApplication[]>(`${applicationsPath}/my`),
    staleTime: 30_000,
    // A missing Student.UserId is a permanent authorization/business-state
    // problem for the current session. Retrying it makes the registration
    // form feel frozen without improving the outcome.
    retry: false,
  });
}

export function useMyNotificationsQuery() {
  return useQuery({
    queryKey: studentQueryKeys.notifications(),
    queryFn: () => apiClient.get<MyNotification[]>("/Notifications/my"),
    staleTime: 30_000,
    retry: false,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) =>
      apiClient.put<void>(`/Notifications/${notificationId}/read`, {
        notificationId,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.notifications(),
      });
    },
  });
}

export function useSubmitStudentApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SubmitStudentApplicationInput) =>
      apiClient.post<string>(`${applicationsPath}/submit`, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.applications(),
      });
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.openPeriods(),
      });
    },
  });
}

export function useSubmitStudentApplicationWithEvidence() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SubmitStudentApplicationWithEvidenceInput) => {
      const formData = new FormData();
      formData.append("RegistrationPeriodId", input.registrationPeriodId);
      if (input.requestedRoomTypeId) {
        formData.append("RequestedRoomTypeId", input.requestedRoomTypeId);
      }
      if (input.priorityObjectId) {
        formData.append("PriorityObjectId", input.priorityObjectId);
      }
      if (input.priorityResidenceAreaId) {
        formData.append(
          "PriorityResidenceAreaId",
          input.priorityResidenceAreaId,
        );
      }
      if (input.priorityResidenceVillage) {
        formData.append(
          "PriorityResidenceVillage",
          input.priorityResidenceVillage,
        );
      }
      if (input.reason) {
        formData.append("Reason", input.reason);
      }
      if (input.applicantClassAndFaculty)
        formData.append(
          "ApplicantClassAndFaculty",
          input.applicantClassAndFaculty,
        );
      if (input.applicantMajor)
        formData.append("ApplicantMajor", input.applicantMajor);
      if (input.applicantEmail)
        formData.append("ApplicantEmail", input.applicantEmail);
      if (input.applicantPhoneNumber)
        formData.append("ApplicantPhoneNumber", input.applicantPhoneNumber);
      if (input.applicantSchoolEmail)
        formData.append("ApplicantSchoolEmail", input.applicantSchoolEmail);
      if (input.applicantPermanentAddress)
        formData.append(
          "ApplicantPermanentAddress",
          input.applicantPermanentAddress,
        );
      if (input.applicantEthnicity)
        formData.append("ApplicantEthnicity", input.applicantEthnicity);
      for (const file of input.evidenceFiles) {
        formData.append("EvidenceFiles", file, file.name);
      }
      return apiClient.post<string>(
        `${applicationsPath}/submit-with-evidence`,
        formData,
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.applications(),
      });
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.openPeriods(),
      });
    },
  });
}

export function useSaveStudentApplicationDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SubmitStudentApplicationInput) =>
      apiClient.post<string>(`${applicationsPath}/draft`, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.applications(),
      });
    },
  });
}

export function useWithdrawStudentApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: string) =>
      apiClient.put<void>(`${applicationsPath}/${applicationId}/withdraw`),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.applications(),
      });
      void queryClient.invalidateQueries({
        queryKey: studentQueryKeys.openPeriods(),
      });
    },
  });
}
