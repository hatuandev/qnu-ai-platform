export type ApplicationStatus =
  | "draft"
  | "submitted"
  | "need_supplement"
  | "approved"
  | "rejected"
  | "cancelled"
  | "assigned";

export const applicationStatusLabels: Record<ApplicationStatus, string> = {
  draft: "Bản nháp",
  submitted: "Chờ duyệt",
  need_supplement: "Cần bổ sung",
  approved: "Đã duyệt",
  rejected: "Từ chối",
  cancelled: "Đã rút hồ sơ",
  assigned: "Đã xếp phòng",
};

export type BadgeVariant =
  | "default"
  | "secondary"
  | "outline"
  | "destructive"
  | "success"
  | "warning"
  | "info";

export const applicationStatusVariants: Record<
  ApplicationStatus,
  BadgeVariant
> = {
  draft: "secondary",
  submitted: "info",
  need_supplement: "warning",
  approved: "success",
  rejected: "destructive",
  cancelled: "secondary",
  assigned: "success",
};
export type DormitoryApplication = {
  id: string;
  applicationCode: string;
  studentId: string;
  studentCode: string;
  studentName: string;
  faculty?: string | null;
  registrationPeriodId: string;
  registrationPeriodName: string;
  requestedRoomTypeName?: string | null;
  priorityObjectName?: string | null;
  priorityScore: number;
  status: ApplicationStatus;
  submittedAt?: string | null;
  created: string;
};
export type ApplicationAttachment = {
  id: string;
  fileName: string;
  contentType?: string | null;
  sizeBytes?: number | null;
  attachmentType?: string | null;
  uploadedAt: string;
};
export type ApplicationHistory = {
  id: string;
  fromStatus?: ApplicationStatus | null;
  toStatus: ApplicationStatus;
  note?: string | null;
  changedBy?: string | null;
  changedAt: string;
};
export type ApplicationsPage = {
  items: DormitoryApplication[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
export type ApplicationsListParams = {
  registrationPeriodId?: string;
  status?: ApplicationStatus;
  search?: string;
  page: number;
  pageSize: number;
};

export type BulkReviewDecision = "approve" | "reject" | "request-supplement";

export type BulkReviewResult = {
  processedCount: number;
  skippedCount: number;
  failures: Array<{
    applicationId: string;
    reason: string;
  }>;
};

export type PriorityEvidenceReviewStatus =
  | "not_required"
  | "pending_review"
  | "approved"
  | "need_supplement"
  | "rejected";

export type PriorityResidenceReviewStatus =
  | "not_required"
  | "pending_review"
  | "valid"
  | "invalid"
  | "need_correction";

export const priorityEvidenceReviewStatusLabels: Record<
  PriorityEvidenceReviewStatus,
  string
> = {
  not_required: "Không yêu cầu",
  pending_review: "Chờ duyệt",
  approved: "Hợp lệ",
  need_supplement: "Yêu cầu bổ sung",
  rejected: "Không hợp lệ",
};

export const priorityResidenceReviewStatusLabels: Record<
  PriorityResidenceReviewStatus,
  string
> = {
  not_required: "Không yêu cầu",
  pending_review: "Chờ duyệt",
  valid: "Hợp lệ",
  invalid: "Không hợp lệ",
  need_correction: "Cần chỉnh sửa",
};

export type ApplicationDetail = DormitoryApplication & {
  className?: string | null;
  periodCode: string;
  requestedRoomTypeId?: string | null;
  priorityObjectId?: string | null;
  priorityObjectCode?: string | null;
  major?: string | null;
  email?: string | null;
  phoneNumber?: string | null;
  schoolEmail?: string | null;
  permanentAddress?: string | null;
  ethnicity?: string | null;
  reason?: string | null;
  reviewedBy?: string | null;
  reviewedAt?: string | null;
  reviewNote?: string | null;
  attachmentCount: number;
  attachments: ApplicationAttachment[];
  createdBy?: string | null;
  lastModified: string;
  lastModifiedBy?: string | null;
  priorityEvidenceRequired: boolean;
  priorityResidenceAreaId?: string | null;
  priorityResidenceAreaCodeSnapshot?: string | null;
  priorityResidenceAreaNameSnapshot?: string | null;
  priorityResidenceProvinceSnapshot?: string | null;
  priorityResidenceVillageSnapshot?: string | null;
  priorityResidenceReviewStatus: PriorityResidenceReviewStatus;
  priorityResidenceReviewNote?: string | null;
  priorityEvidenceReviewStatus: PriorityEvidenceReviewStatus;
  priorityEvidenceReviewNote?: string | null;
  priorityVerificationType:
    | "none"
    | "image_evidence"
    | "residence_area"
    | "image_and_residence_area";
  priorityResidenceReviewedAt?: string | null;
  priorityEvidenceReviewedAt?: string | null;
};

export type ReviewPriorityVerificationInput = {
  residenceReviewStatus?: PriorityResidenceReviewStatus | null;
  residenceReviewNote?: string;
  evidenceReviewStatus?: PriorityEvidenceReviewStatus | null;
  evidenceReviewNote?: string;
  propagateToApplicationStatus: boolean;
};

export type ImportDormitoryApplicationRowError = {
  rowNumber: number;
  studentCode?: string | null;
  studentName?: string | null;
  errorMessage: string;
};

export type ImportDormitoryApplicationsResult = {
  totalRows: number;
  successCount: number;
  newStudentsCount: number;
  updatedDraftsCount: number;
  failedCount: number;
  errors: ImportDormitoryApplicationRowError[];
  importedApplicationIds: string[];
};

export type UpdateApplicationInput = {
  studentId: string;
  requestedRoomTypeId?: string | null;
  priorityObjectId?: string | null;
  reason?: string | null;
};
