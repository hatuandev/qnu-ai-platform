export type AssignmentStatus =
  | "selected"
  | "assigned"
  | "checked_in"
  | "cancelled";

export type Assignment = {
  id: string;
  applicationId: string;
  applicationCode: string;
  studentId: string;
  studentCode: string;
  studentName: string;
  studentGender?: string;
  studentPhone?: string | null;
  roomId: string;
  roomCode: string;
  roomName?: string | null;
  buildingCode?: string | null;
  buildingName?: string | null;
  floorNumber?: number | null;
  roomTypeName?: string | null;
  roomGenderPolicy?: string | null;
  status: AssignmentStatus;
  assignedAt: string;
  note?: string | null;
};

export type AssignmentWorkspace = {
  registrationPeriodId: string;
  periodCode: string;
  periodName: string;
  periodStatus: string;
  allocationStatus:
    | "not_allocated"
    | "allocated"
    | "selection_open"
    | "selection_ended"
    | "finalized";
  roomSelectionStartAt?: string | null;
  roomSelectionEndAt?: string | null;
  roomSelectionNotificationSentAt?: string | null;
  roomAllocationFinalizedAt?: string | null;
  roomSelectionFinalizedAt?: string | null;
  selectionWindowEnded: boolean;
  canFinalizeSelection: boolean;
  selectedCount: number;
  assignedCount: number;
  checkedInCount: number;
  cancelledCount: number;
  awaitingAssignmentCount: number;
  openedRoomCount: number;
  availablePlaceCount: number;
};

export type EligibleApplication = {
  id: string;
  applicationCode: string;
  studentId: string;
  studentCode: string;
  studentName: string;
  studentPhone?: string | null;
  faculty?: string | null;
  className?: string | null;
  gender: string;
  periodName: string;
  requestedRoomTypeName?: string | null;
  priorityObjectName?: string | null;
  priorityScore: number;
  submittedAt?: string | null;
};

export type EligibleApplicationsPage = {
  items: EligibleApplication[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
export type RoomAssignmentByRoom = {
  id: string;
  studentCode: string;
  studentName: string;
  status: AssignmentStatus;
  assignedAt: string;
  note?: string | null;
};
export type Room = {
  id: string;
  code: string;
  name: string;
  buildingCode?: string | null;
  buildingName: string;
  roomTypeName?: string | null;
  operationalCapacity: number;
  occupiedPlaces: number;
  availablePlaces: number;
  status: string;
};
export type AssignmentsPage = {
  items: Assignment[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
export type AssignmentsListParams = {
  status?: AssignmentStatus;
  search?: string;
  registrationPeriodId?: string;
  buildingId?: string;
  floorId?: string;
  roomId?: string;
  page: number;
  pageSize: number;
};
