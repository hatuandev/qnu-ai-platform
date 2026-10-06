import type { RoleRecord } from "@/rbac/demo";

export function canEditRole(role: RoleRecord) {
  return role.status === "active";
}

export function canRenameRoleKey(role: RoleRecord) {
  return !role.isSystem;
}

export function canDeleteRole(role: RoleRecord) {
  return !role.isSystem && role.userCount === 0;
}

export function roleTypeLabel(role: RoleRecord) {
  return role.isSystem ? "Hệ thống" : "Tùy chỉnh";
}
