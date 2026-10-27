export type ResidenceContractStatus =
  | "draft"
  | "pending_signature"
  | "active"
  | "cancelled";

export type ResidenceContract = {
  id: string;
  contractNumber: string;
  residenceId: string;
  studentId: string;
  studentCode: string;
  studentName: string;
  status: ResidenceContractStatus;
  effectiveFrom: string;
  effectiveTo: string;
  totalAmount: number;
  paymentPlan: "one_time" | "monthly" | string;
  currency: string;
  buildingName: string;
  roomCode: string;
  signedAt?: string | null;
};

export type ResidenceContractDetail = ResidenceContract & {
  signedBy?: string | null;
  studentDateOfBirth?: string | null;
  studentGender: string;
  studentEthnicity?: string | null;
  studentFaculty?: string | null;
  studentClassName?: string | null;
  studentPhoneNumber?: string | null;
  studentPermanentAddress?: string | null;
  roomName: string;
  terminationNoticeDate?: string | null;
  terminationEffectiveDate?: string | null;
  terminatedAt?: string | null;
  terminationReason?: string | null;
  liquidatedAt?: string | null;
  liquidationNote?: string | null;
  note?: string | null;
  created: string;
  lastModified: string;
};

export type ResidenceContractsPage = {
  items: ResidenceContract[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type ResidenceContractsListParams = {
  search?: string;
  status?: ResidenceContractStatus;
  page: number;
  pageSize: number;
};

export type ResidenceContractInput = {
  residenceId: string;
  effectiveFrom: string;
  effectiveTo: string;
  totalAmount?: number;
  paymentPlan: "one_time" | "monthly";
  currency: string;
  note?: string;
};

export type ResidenceContractUpdateInput = Omit<
  ResidenceContractInput,
  "residenceId"
>;
