export type RoomStatus = "available" | "full" | "maintenance" | "inactive";
export type EditableRoomStatus = Exclude<RoomStatus, "full">;

export type Room = {
  id: string;
  code: string;
  name: string;
  buildingCode: string;
  buildingName?: string | null;
  floorNumber: number;
  roomTypeName: string;
  capacity: number;
  operationalCapacity: number;
  occupiedPlaces: number;
  availablePlaces: number;
  status: RoomStatus;
};

export type RoomDetail = Omit<Room, "buildingName"> & {
  buildingName?: string | null;
  buildingId: string;
  floorId: string;
  roomTypeId: string;
  note?: string | null;
  created: string;
  lastModified: string;
};

export type RoomsPage = {
  items: Room[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type RoomsListParams = {
  buildingId?: string;
  floorId?: string;
  roomTypeId?: string;
  status?: RoomStatus;
  searchCodeOrName?: string;
  page: number;
  pageSize: number;
};

export type RoomFormValues = {
  buildingId: string;
  floorId: string;
  roomTypeId: string;
  code: string;
  name: string;
  capacity: number;
  operationalCapacity: number;
  note: string;
};

export type CreateRoomInput = Omit<RoomFormValues, "note"> & {
  note?: string;
};

export type UpdateRoomInput = Pick<
  RoomFormValues,
  "name" | "capacity" | "operationalCapacity"
> & {
  note?: string;
};
