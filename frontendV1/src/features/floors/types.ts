export type FloorStatus = "active" | "inactive";

export type Floor = {
  id: string;
  buildingId: string;
  floorNumber: number;
  name: string;
  status: FloorStatus;
  roomCount: number;
  created?: string;
  createdBy?: string | null;
  lastModified?: string;
  lastModifiedBy?: string | null;
};

export type FloorFormValues = {
  floorNumber: number;
  name: string;
};
