export type ResidenceStatus =
  | "active"
  | "extended"
  | "checked_out"
  | "cancelled";

export type Residence = {
  id: string;
  studentId: string;
  studentCode: string;
  studentName: string;
  faculty?: string | null;
  className?: string | null;
  gender?: string | null;
  phoneNumber?: string | null;

  roomId: string;
  roomCode: string;
  roomName: string;
  buildingId?: string | null;
  buildingCode: string;
  buildingName: string;
  floorId?: string | null;
  floorName?: string | null;
  floorNumber?: number | null;
  roomCapacity: number;
  roomOperationalCapacity: number;
  roomOccupantsCount: number;

  academicYearId?: string | null;
  academicYearName?: string | null;
  registrationPeriodId?: string | null;
  registrationPeriodName?: string | null;

  startDate: string;
  expectedEndDate?: string | null;
  actualEndDate?: string | null;
  status: ResidenceStatus;
  checkInAt?: string | null;
  checkOutAt?: string | null;
};

export type ResidenceDetail = Residence & {
  applicationId?: string | null;
  applicationCode?: string | null;
  academicYearCode: string;
  note?: string | null;
  created: string;
  lastModified: string;
};

export type ResidenceHistory = {
  id: string;
  action: string;
  fromRoomId?: string | null;
  toRoomId?: string | null;
  fromDate?: string | null;
  toDate?: string | null;
  note?: string | null;
  performedBy: string;
  performedAt: string;
};

export type ResidencesPage = {
  items: Residence[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type ResidencesListParams = {
  status?: ResidenceStatus;
  buildingId?: string;
  floorId?: string;
  roomId?: string;
  registrationPeriodId?: string;
  academicYearId?: string;
  search?: string;
  page: number;
  pageSize: number;
  enabled?: boolean;
};
