export type UserStatus = "active" | "inactive" | "pending" | "suspended";
export type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  status: UserStatus;
  createdAt: string;
  lastActive?: string;
};

export const userStatusValues = [
  "all",
  "active",
  "inactive",
  "pending",
  "suspended",
] as const;
export const userSortValues = [
  "name.asc",
  "name.desc",
  "role.asc",
  "role.desc",
  "status.asc",
  "status.desc",
  "createdAt.asc",
  "createdAt.desc",
] as const;
export type UserSort = (typeof userSortValues)[number];
