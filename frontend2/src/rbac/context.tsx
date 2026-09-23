import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import { useAuth } from "@/app/auth";
import {
  backendRoleRecords,
  permissionsForBackendClaims,
} from "@/rbac/backend-role-map";
import { demoRoles, type RoleKey, type RoleRecord } from "@/rbac/demo";
import { canDeleteRole } from "@/rbac/policy";

export type RoleInput = Pick<
  RoleRecord,
  "key" | "name" | "description" | "permissions" | "status"
>;

type RbacContextValue = {
  roles: RoleRecord[];
  roleKey: RoleKey;
  roleName: string;
  accessSource: "backend" | "demo";
  isAccessVerified: boolean;
  setRoleKey: (role: RoleKey) => void;
  can: (permission?: string) => boolean;
  isDemoMode: boolean;
  createRole: (input: RoleInput) => RoleRecord;
  updateRole: (id: string, input: Partial<RoleInput>) => void;
  duplicateRole: (role: RoleRecord) => RoleRecord;
  deleteRole: (id: string) => boolean;
};
const RbacContext = createContext<RbacContextValue | null>(null);
const STORAGE_KEY = "admin-starter-role";

export function RbacProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const isDemoMode = auth.isDemoMode;
  const isAccessVerified =
    isDemoMode ||
    (auth.isAuthenticated && !auth.isLoading && auth.error === null);
  const [demoRoleRecords, setDemoRoleRecords] = useState<RoleRecord[]>(() =>
    demoRoles.map((role) => ({ ...role, permissions: [...role.permissions] })),
  );
  const [roleKey, setRoleKeyState] = useState<RoleKey>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return demoRoles.some((role) => role.key === stored)
      ? (stored as RoleKey)
      : "administrator";
  });
  const backendRoles = useMemo(
    () =>
      backendRoleRecords(
        auth.user?.roles ?? [],
        auth.user?.userType,
        auth.user?.roleMetadata ?? [],
      ),
    [auth.user?.roleMetadata, auth.user?.roles, auth.user?.userType],
  );
  const roles = isDemoMode && isAccessVerified ? demoRoleRecords : backendRoles;
  const activeRoleKey = isDemoMode ? roleKey : (backendRoles[0]?.key ?? "");
  const role = roles.find((item) => item.key === activeRoleKey);
  const permissions = useMemo<Set<string>>(
    () =>
      new Set(
        isDemoMode && isAccessVerified
          ? (role?.permissions ?? [])
          : permissionsForBackendClaims(auth.user?.permissions ?? []),
      ),
    [auth.user?.permissions, isAccessVerified, isDemoMode, role?.permissions],
  );
  const createRole = useCallback(
    (input: RoleInput) => {
      const roleRecord: RoleRecord = {
        ...input,
        id: `role-${crypto.randomUUID?.() ?? Date.now()}`,
        userCount: 0,
        isSystem: false,
        permissions: [...input.permissions],
      };
      if (isDemoMode) setDemoRoleRecords((current) => [roleRecord, ...current]);
      return roleRecord;
    },
    [isDemoMode],
  );
  const updateRole = useCallback(
    (id: string, input: Partial<RoleInput>) => {
      if (!isDemoMode) return;
      setDemoRoleRecords((current) =>
        current.map((item) =>
          item.id === id
            ? {
                ...item,
                ...input,
                permissions: input.permissions ?? item.permissions,
              }
            : item,
        ),
      );
    },
    [isDemoMode],
  );
  const duplicateRole = useCallback(
    (source: RoleRecord) =>
      createRole({
        key: `${source.key}_copy`,
        name: `Bản sao của ${source.name}`,
        description: source.description,
        permissions: [...source.permissions],
        status: source.status,
      }),
    [createRole],
  );
  const deleteRole = useCallback(
    (id: string) => {
      if (!isDemoMode) return false;
      const target = demoRoleRecords.find((item) => item.id === id);
      if (!target || !canDeleteRole(target)) return false;
      setDemoRoleRecords((current) => current.filter((item) => item.id !== id));
      if (target.key === roleKey) {
        setRoleKeyState("administrator");
        localStorage.setItem(STORAGE_KEY, "administrator");
      }
      return true;
    },
    [demoRoleRecords, isDemoMode, roleKey],
  );
  const value = useMemo<RbacContextValue>(
    () => ({
      roles,
      roleKey: activeRoleKey,
      accessSource: isDemoMode ? "demo" : "backend",
      isAccessVerified,
      roleName: role?.name ?? "Chưa xác định",
      isDemoMode,
      setRoleKey: (next) => {
        if (!isDemoMode || !roles.some((item) => item.key === next)) return;
        setRoleKeyState(next);
        localStorage.setItem(STORAGE_KEY, next);
      },
      can: (permission) => {
        if (!permission) return true;
        const p = permission.trim().toLowerCase();
        if (permissions.has(p)) return true;

        const isAdmin =
          auth.user?.roles?.some(
            (r) => r.trim().toLowerCase() === "administrator",
          ) || permissions.has("ktx.access.admin");
        if (isAdmin) return true;

        const isManager = permissions.has("ktx.access.manage");
        if (isManager) {
          if (p.startsWith("ktx.")) return true;
        }

        const isReader = permissions.has("ktx.access.read");
        if (isReader) {
          if (p.endsWith(".view") || p.endsWith(".read")) return true;
        }

        return false;
      },
      createRole,
      updateRole,
      duplicateRole,
      deleteRole,
    }),
    [
      auth.user?.roles,
      createRole,
      deleteRole,
      duplicateRole,
      isDemoMode,
      permissions,
      roles,
      updateRole,
      activeRoleKey,
      isAccessVerified,
      role?.name,
    ],
  );
  return <RbacContext.Provider value={value}>{children}</RbacContext.Provider>;
}

export function useRbac() {
  const value = useContext(RbacContext);
  if (!value) throw new Error("useRbac must be used within RbacProvider");
  return value;
}
