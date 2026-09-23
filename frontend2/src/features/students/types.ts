export type StudentStatus =
  | "studying"
  | "paused"
  | "graduated"
  | "unknown"
  | "inactive";
export type StudentGender = "male" | "female" | "other";
export type Student = {
  id: string;
  studentCode: string;
  fullName: string;
  dateOfBirth?: string | null;
  gender: StudentGender;
  email?: string | null;
  schoolEmail?: string | null;
  userId?: string | null;
  phoneNumber?: string | null;
  faculty?: string | null;
  className?: string | null;
  status: StudentStatus;
  created: string;
  lastModified: string;
};
export type StudentDetail = Student & {
  major?: string | null;
  permanentAddress?: string | null;
  contactAddress?: string | null;
  applicationCount: number;
  residenceCount: number;
  createdBy?: string | null;
  lastModifiedBy?: string | null;
};
export type StudentsPage = {
  items: Student[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
export type StudentsListParams = {
  search?: string;
  status?: StudentStatus;
  faculty?: string;
  page: number;
  pageSize: number;
};
export type StudentFormValues = {
  studentCode: string;
  fullName: string;
  dateOfBirth: Date | undefined;
  gender: StudentGender;
  email: string;
  phoneNumber: string;
  faculty: string;
  className: string;
  major: string;
  permanentAddress: string;
  contactAddress: string;
};

export type StudentLookupDto = {
  id: string;
  studentCode: string;
  fullName: string;
  dateOfBirth?: string | null;
  gender?: string | null;
  email?: string | null;
  schoolEmail?: string | null;
  phoneNumber?: string | null;
  faculty?: string | null;
  className?: string | null;
  major?: string | null;
  permanentAddress?: string | null;
  contactAddress?: string | null;
  status: string;
  fromUis: boolean;
};
