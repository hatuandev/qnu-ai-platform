export type RegistrationPeriod = {
  id: string;
  code: string;
  name: string;
  academicYearId: string;
  academicYearCode: string;
  paymentConfigurationId?: string | null;
  paymentConfigurationName?: string | null;
  startAt: string;
  endAt: string;
  roomSelectionStartAt?: string | null;
  roomSelectionEndAt?: string | null;
  roomSelectionNotificationSentAt?: string | null;
  roomAllocationFinalizedAt?: string | null;
  roomSelectionFinalizedAt?: string | null;
  status: "draft" | "open" | "closed" | "archived";
  note?: string | null;
  created?: string;
  lastModified?: string;
};
export type RegistrationPeriodsPage = {
  items: RegistrationPeriod[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
export type RegistrationPeriodsListParams = {
  search?: string;
  status?: string;
  academicYearId?: string;
  page: number;
  pageSize: number;
};
export type RegistrationPeriodInput = {
  code?: string;
  name: string;
  academicYearId: string;
  paymentConfigurationId?: string;
  startAt: string;
  endAt: string;
  roomSelectionStartAt?: string;
  roomSelectionEndAt?: string;
  note?: string;
};

export type RegistrationPeriodRoomGenderPolicy =
  | "male"
  | "female"
  | "mixed"
  | "unspecified";

export type RegistrationPeriodRoomRule = {
  roomId: string;
  roomCode: string;
  roomName: string;
  buildingCode: string;
  buildingName: string;
  floorNumber: number;
  roomTypeName: string;
  roomStatus: string;
  capacity: number;
  operationalCapacity: number;
  availablePlaceCount: number;
  occupiedPlaceCount: number;
  isEnabled: boolean;
  genderPolicy: RegistrationPeriodRoomGenderPolicy;
};

export type RegistrationPeriodBuildingOption = {
  buildingId: string;
  buildingCode: string;
  buildingName: string;
  totalRooms: number;
  enabledRooms: number;
};

export type RegistrationPeriodRoomRulesParams = {
  buildingCode?: string;
  floorNumber?: number;
};

export type RegistrationPeriodRoomRules = {
  registrationPeriodId: string;
  periodName: string;
  periodStatus: RegistrationPeriod["status"];
  roomSelectionStartAt?: string | null;
  roomSelectionEndAt?: string | null;
  roomSelectionNotificationSentAt?: string | null;
  roomAllocationFinalizedAt?: string | null;
  roomSelectionFinalizedAt?: string | null;
  canFinalizeAllocation: boolean;
  allocationStatus:
    | "not_allocated"
    | "allocated"
    | "selection_open"
    | "selection_ended"
    | "finalized";
  canEdit: boolean;
  canNotify: boolean;
  hasExplicitRules: boolean;
  buildings?: RegistrationPeriodBuildingOption[];
  rooms: RegistrationPeriodRoomRule[];
};

export type UpdateRegistrationPeriodRoomRulesInput = {
  rooms: Array<{
    roomId: string;
    isEnabled: boolean;
    genderPolicy: RegistrationPeriodRoomGenderPolicy;
  }>;
};
