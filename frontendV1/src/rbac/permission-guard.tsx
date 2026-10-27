import { useRbac } from "@/rbac/context";

export function PermissionGuard({
  permission,
  fallback = null,
  children,
}: {
  permission: string;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}) {
  const { can } = useRbac();
  return can(permission) ? children : fallback;
}
