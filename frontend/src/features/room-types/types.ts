export type RoomType = {
  id: string;
  code: string;
  name: string;
  capacity: number;
  description?: string | null;
  isActive: boolean;
  roomCount: number;
  created?: string;
  createdBy?: string | null;
  lastModified?: string;
  lastModifiedBy?: string | null;
};

export type RoomTypesPage = {
  items: RoomType[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type RoomTypesListParams = {
  searchCodeOrName?: string;
  isActive?: boolean;
  page: number;
  pageSize: number;
};

export type RoomTypeFormValues = {
  code: string;
  name: string;
  capacity: number;
  description: string;
};
