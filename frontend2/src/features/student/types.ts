import type { ApplicationStatus } from "@/features/applications/types";

export {
  applicationStatusLabels,
  applicationStatusVariants,
} from "@/features/applications/types";

export type StudentApplicationStatus = ApplicationStatus;

export type OpenRegistrationPeriod = {
  id: string;
  code: string;
  name: string;
  academicYearId: string;
  academicYearCode: string;
  startAt: string;
  endAt: string;
  roomSelectionStartAt?: string | null;
  roomSelectionEndAt?: string | null;
  status: string;
  note?: string | null;
  applicationCount: number;
};

export type MyApplication = {
  id: string;
  applicationCode: string;
  registrationPeriodId: string;
  registrationPeriodName: string;
  requestedRoomTypeId?: string | null;
  requestedRoomTypeName?: string | null;
  priorityObjectId?: string | null;
  priorityObjectName?: string | null;
  reason?: string | null;
  reviewNote?: string | null;
  status: StudentApplicationStatus;
  submittedAt?: string | null;
  created: string;
};

export type MyNotification = {
  id: string;
  title: string;
  content: string;
  type:
    | "application_result"
    | "check_in"
    | "fee_due"
    | "room_selection"
    | "general";
  createdAt: string;
  readAt?: string | null;
};

export type StudentRoomTypeOption = {
  id: string;
  code: string;
  name: string;
  capacity: number;
};

export type StudentPriorityObjectOption = {
  id: string;
  code: string;
  name: string;
  score: number;
  description?: string | null;
  verificationType:
    | "none"
    | "image_evidence"
    | "residence_area"
    | "image_and_residence_area";
  evidenceInstructions?: string | null;
  maxEvidenceFiles: number;
  maxEvidenceFileSizeBytes: number;
};

export type StudentRegistrationCatalog = {
  student?: StudentRegistrationStudent | null;
  roomTypes: StudentRoomTypeOption[];
  priorityObjects: StudentPriorityObjectOption[];
};

export type StudentRegistrationStudent = {
  studentCode: string;
  fullName: string;
  email?: string | null;
  schoolEmail?: string | null;
  phoneNumber?: string | null;
  faculty?: string | null;
  className?: string | null;
  major?: string | null;
  permanentAddress?: string | null;
};

export type SubmitStudentApplicationInput = {
  registrationPeriodId: string;
  requestedRoomTypeId?: string;
  priorityObjectId?: string;
  reason?: string;
  applicantClassAndFaculty?: string;
  applicantMajor?: string;
  applicantEmail?: string;
  applicantPhoneNumber?: string;
  applicantSchoolEmail?: string;
  applicantPermanentAddress?: string;
  applicantEthnicity?: string;
};

export type SubmitStudentApplicationWithEvidenceInput =
  SubmitStudentApplicationInput & {
    priorityResidenceAreaId?: string | null;
    priorityResidenceVillage?: string | null;
    evidenceFiles: File[];
  };

export type StudentRoomSelection = {
  registrationPeriodId: string;
  periodName: string;
  selectionStartAt?: string | null;
  selectionEndAt?: string | null;
  isOpen: boolean;
  selectionStatus:
    | "not_allocated"
    | "awaiting_approval"
    | "awaiting_notification"
    | "not_scheduled"
    | "scheduled"
    | "open"
    | "ended"
    | "assigned";
  applicationId: string;
  applicationCode: string;
  applicationStatus: StudentApplicationStatus;
  currentSelection?: StudentSelectedRoom | null;
  availableRooms: StudentSelectableRoom[];
};

export type StudentSelectedRoom = {
  assignmentId: string;
  roomId: string;
  roomCode: string;
  roomName: string;
  buildingName: string;
  floorName: string;
  status: "selected" | "assigned" | "checked_in";
  selectedAt: string;
};

export type StudentSelectableRoom = {
  id: string;
  code: string;
  name: string;
  roomTypeName: string;
  buildingName: string;
  floorName: string;
  capacity: number;
  operationalCapacity: number;
  occupiedPlaces: number;
  availablePlaces: number;
  isAvailable: boolean;
  isSelectedByCurrentStudent: boolean;
  occupancyStatus: string;
  priceAmount?: number | null;
  priceCurrency?: string | null;
};
