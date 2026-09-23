export type AcademicYear = {
  id: string;
  code: string;
  name: string;
  startDate: string;
  endDate: string;
  isCurrent: boolean;
  registrationPeriodCount: number;
  created?: string;
  createdBy?: string | null;
  lastModified?: string;
  lastModifiedBy?: string | null;
};

export type AcademicYearsPage = {
  items: AcademicYear[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type AcademicYearsListParams = {
  searchCodeOrName?: string;
  isCurrent?: boolean;
  page: number;
  pageSize: number;
};

export type AcademicYearFormValues = {
  code: string;
  name: string;
  startDate: Date | undefined;
  endDate: Date | undefined;
  isCurrent: boolean;
};
