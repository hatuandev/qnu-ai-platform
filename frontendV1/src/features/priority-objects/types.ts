export const PRIORITY_OBJECT_VERIFICATION_TYPE = {
  None: "none",
  ImageEvidence: "image_evidence",
  ResidenceArea: "residence_area",
  ImageAndResidenceArea: "image_and_residence_area",
} as const;

export type PriorityObjectVerificationType =
  (typeof PRIORITY_OBJECT_VERIFICATION_TYPE)[keyof typeof PRIORITY_OBJECT_VERIFICATION_TYPE];

export const PRIORITY_OBJECT_VERIFICATION_TYPE_LABELS: Record<
  PriorityObjectVerificationType,
  string
> = {
  none: "Không yêu cầu",
  image_evidence: "Ảnh minh chứng",
  residence_area: "Theo địa bàn",
  image_and_residence_area: "Ảnh + địa bàn",
};

export type PriorityObject = {
  id: string;
  code: string;
  name: string;
  score: number;
  description?: string | null;
  isActive: boolean;
  verificationType: PriorityObjectVerificationType;
  evidenceInstructions?: string | null;
  maxEvidenceFiles: number;
  maxEvidenceFileSizeBytes: number;
  eligibleAreaCount: number;
  created: string;
  lastModified: string;
};

export type PriorityObjectsPage = {
  items: PriorityObject[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type PriorityObjectsListParams = {
  searchCodeOrName?: string;
  verificationType?: PriorityObjectVerificationType;
  isActive?: boolean;
  page: number;
  pageSize: number;
};

export type CreatePriorityObjectInput = {
  code: string;
  name: string;
  score: number;
  description?: string;
  isActive: boolean;
  verificationType: PriorityObjectVerificationType;
  evidenceInstructions?: string;
  maxEvidenceFiles?: number;
  maxEvidenceFileSizeBytes?: number;
};

export type UpdatePriorityObjectInput = Omit<CreatePriorityObjectInput, "code">;

export type PriorityObjectEligibleAreaDto = {
  priorityObjectId: string;
  administrativeAreaId: string;
  externalCode: string;
  name: string;
  divisionType: string;
  codename: string;
  provinceCode?: string | null;
  provinceName?: string | null;
  specificVillages?: string | null;
  isWholeArea?: boolean;
  isActive: boolean;
  created: string;
  lastModified: string;
};

export type PriorityObjectEligibleAreasPage = {
  items: PriorityObjectEligibleAreaDto[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type PriorityObjectEligibleAreaListParams = {
  page: number;
  pageSize: number;
  isActive?: boolean;
  provinceName?: string;
  search?: string;
};

export type AdministrativeAreaSummary = {
  id: string;
  externalCode: string;
  name: string;
  divisionType: string;
  provinceCode?: string | null;
  provinceName?: string | null;
  specificVillages?: string | null;
  isWholeArea?: boolean;
};

export type AdministrativeAreaListParams = {
  search?: string;
  provinceCode?: string;
  divisionType?: string;
  page: number;
  pageSize: number;
};

export type AdministrativeAreaPage = {
  items: AdministrativeAreaSummary[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
