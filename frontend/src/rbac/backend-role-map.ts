import type { BackendRoleMetadata } from "@/app/auth/types";
import type { RoleRecord } from "@/rbac/demo";

export function permissionsForBackendClaims(permissions: string[]): string[] {
  return [
    ...new Set(
      permissions
        .map((permission) => permission.trim().toLowerCase())
        .filter(Boolean),
    ),
  ];
}

export function isStudentAccount(userType?: string): boolean {
  return userType?.trim().toLowerCase() === "student";
}

export function backendHomeRoute(_userType?: string): "/dashboard" {
  return "/dashboard";
}

export function backendRoleLabel(
  roles: string[],
  userType?: string,
  roleMetadata: BackendRoleMetadata[] = [],
): string {
  const metadata = roles
    .map((role) =>
      roleMetadata.find(
        (item) => item.key.toLowerCase() === role.trim().toLowerCase(),
      ),
    )
    .find(Boolean);

  if (isStudentAccount(userType)) return "Sinh viên";
  if (metadata?.displayName?.trim()) return metadata.displayName;
  return roles.find((role) => role.trim()) ?? "Vai trò ứng dụng";
}

export function backendRoleRecords(
  roles: string[],
  userType?: string,
  roleMetadata: BackendRoleMetadata[] = [],
): RoleRecord[] {
  const effectiveRoles = roles.length
    ? roles
    : isStudentAccount(userType)
      ? ["AccountType.Student"]
      : roles;

  return effectiveRoles.map((role) => {
    const metadata = roleMetadata.find(
      (item) => item.key.toLowerCase() === role.trim().toLowerCase(),
    );

    return {
      id: `backend-role-${role}`,
      key: role,
      name: backendRoleLabel([role], userType, roleMetadata),
      description:
        metadata?.description ??
        "Vai trò được cấp bởi phiên đăng nhập backend.",
      permissions: [],
      userCount: 1,
      isSystem: metadata?.isSystem ?? true,
      status: metadata?.isEnabled === false ? "inactive" : "active",
    };
  });
}
