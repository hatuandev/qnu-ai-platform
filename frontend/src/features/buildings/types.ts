export type BuildingStatus = "active" | "inactive";

export type Building = {
  id: string;
  code: string;
  name: string;
  address: string | null;
  description?: string | null;
  status: BuildingStatus;
  floorCount: number;
  roomCount: number;
  created: string;
  createdBy?: string | null;
  lastModified: string;
  lastModifiedBy?: string | null;
};

export type BuildingsPage = {
  items: Building[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type BuildingsListParams = {
  searchCodeOrName?: string;
  status?: BuildingStatus;
  page: number;
  pageSize: number;
};

export type CreateBuildingInput = {
  code: string;
  name: string;
  address?: string;
  description?: string;
};

export type UpdateBuildingInput = {
  name: string;
  address?: string;
  description?: string;
};

export type BuildingFormValues = CreateBuildingInput;
