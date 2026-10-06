import type { User, UserStatus } from "@/features/users/types";

export function updateUsersStatus(
  current: User[],
  selectedUsers: User[],
  status: UserStatus,
) {
  const selectedIds = new Set(selectedUsers.map((user) => user.id));
  return current.map((user) =>
    selectedIds.has(user.id) ? { ...user, status } : user,
  );
}
