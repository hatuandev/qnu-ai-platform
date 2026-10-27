export type DailyTrendItem = {
  date: string;
  label: string;
  count: number;
};

export type ActionCenterSummary = {
  pendingApplicationsCount: number;
  needSupplementApplicationsCount: number;
  openSupportRequestsCount: number;
  maintenanceRequestsCount: number;
  expiringContractsCount: number;
  overdueInvoicesCount: number;
  overdueInvoicesAmount: number;
};

export type DashboardStats = {
  totalStudents: number;
  activeStudents: number;
  totalActiveResidences: number;
  totalCheckedOutResidences: number;
  totalRooms: number;
  totalPlaces: number;
  availablePlaces: number;
  occupiedPlaces: number;
  placeOccupancyRate: number;
  totalApplications: number;
  applicationsByStatus: Record<string, number>;
  totalInvoices: number;
  invoicesByStatus: Record<string, number>;
  totalInvoicedAmount: number;
  totalPaidAmount: number;
  totalOutstandingAmount: number;
  totalSupportRequests: number;
  supportRequestsByStatus: Record<string, number>;
  dailyApplicationTrends?: DailyTrendItem[];
  actionCenter?: ActionCenterSummary;
};

export type ApplicationStats = {
  totalCount: number;
  byStatus: Record<string, number>;
  byAcademicYear: Record<string, number>;
};

export type RoomOccupancyStats = {
  totalRooms: number;
  roomsByStatus: Record<string, number>;
  totalPlaces: number;
  occupiedPlaces: number;
  availablePlaces: number;
  totalActiveResidences: number;
  placeOccupancyRate: number;
  roomOccupancyRate: number;
  byBuilding: Array<{
    buildingId: string;
    buildingCode: string;
    buildingName: string;
    totalRooms: number;
    totalPlaces: number;
    occupiedPlaces: number;
    occupancyRate: number;
  }>;
};

export type RevenueStats = {
  totalInvoices: number;
  totalPayments: number;
  invoicesByStatus: Record<string, number>;
  totalInvoicedAmount: number;
  totalCollectedAmount: number;
  totalVoidedAmount: number;
  totalOutstandingAmount: number;
  collectionRate: number;
};
