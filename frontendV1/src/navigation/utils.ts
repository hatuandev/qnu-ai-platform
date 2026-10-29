import { hiddenRouteMeta, navigationGroups } from "@/navigation/config";
import type { NavGroup, NavItem } from "@/navigation/types";
import { isStudentAccount } from "@/rbac/backend-role-map";
import { workspaceFeatureKeys, workspaceFeatures } from "./config";
import { isFeatureActive } from "./workspace-features";

export type PermissionCheck = (permission?: string) => boolean;

const denyAll: PermissionCheck = () => false;

/**
 * Filter navigation for the current viewer.
 *
 * `can` is the KTX template predicate; `canV1` is the backendV1 permission
 * predicate plus v1 session state. They stay apart so a demo KTX role can never
 * reveal a real QNU AI screen (and vice versa).
 */
export function filterNavigationGroups(
  groups: NavGroup[],
  can: PermissionCheck,
  userType?: string,
  canV1: PermissionCheck = denyAll,
): NavGroup[] {
  return groups
    .map((group) => ({
      ...group,
      items: group.items
        .map((item) => filterItem(item, can, canV1, userType))
        .filter(Boolean) as NavItem[],
    }))
    .filter((group) => group.items.length > 0);
}

function filterItem(
  item: NavItem,
  can: PermissionCheck,
  canV1: PermissionCheck,
  userType?: string,
): NavItem | null {
  const isStudent = isStudentAccount(userType);
  if (item.audience === "student" && !isStudent) return null;
  if (item.audience === "staff" && isStudent) return null;
  const check = item.scope === "v1" ? canV1 : can;
  if (!check(item.permission)) return null;
  const children = item.children
    ?.map((child) => filterItem(child, can, canV1, userType))
    .filter(Boolean) as NavItem[] | undefined;
  if (item.children && (!children || children.length === 0) && !item.to)
    return null;
  return { ...item, children };
}

export function flattenNavigation(groups = navigationGroups): NavItem[] {
  const output: NavItem[] = [];
  for (const group of groups)
    for (const item of group.items) {
      if (item.to) output.push(item);
      if (item.children)
        output.push(...item.children.filter((child) => child.to));
    }
  return output;
}

export function isItemActive(item: NavItem, pathname: string): boolean {
  if (item.to && pathname === item.to) return true;
  if (item.to === "/workspaces")
    return /^\/workspaces\/[^/]+\/?$/.test(pathname);
  if (item.to && pathname.startsWith(`${item.to}/`)) return true;
  return (
    item.children?.some(
      (child) =>
        child.to === pathname ||
        (child.to ? pathname.startsWith(`${child.to}/`) : false),
    ) ?? false
  );
}

type BreadcrumbItem = { label: string };

function withoutDuplicateLabels(items: BreadcrumbItem[]): BreadcrumbItem[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.label)) return false;
    seen.add(item.label);
    return true;
  });
}

export function getBreadcrumbs(
  pathname: string,
  search: Record<string, unknown> = {},
) {
  const feature = workspaceFeatureKeys.find((key) =>
    isFeatureActive(key, pathname, search),
  );
  if (feature)
    return [
      { label: "QNU AI" },
      { label: workspaceFeatures[feature].group },
      { label: workspaceFeatures[feature].title },
    ];
  // QNU AI detail routes carry ids, so they need explicit labels.
  if (pathname.startsWith("/workspaces/")) {
    return [
      { label: "QNU AI" },
      { label: "Workspaces" },
      { label: "Chi tiết" },
    ];
  }
  if (pathname.startsWith("/modelops/providers/")) {
    return [
      { label: "QNU AI" },
      { label: "ModelOps" },
      { label: "Nhà cung cấp" },
      { label: "Chi tiết" },
    ];
  }
  if (pathname.startsWith("/modelops/models/")) {
    return [
      { label: "QNU AI" },
      { label: "ModelOps" },
      { label: "Model" },
      { label: "Chi tiết" },
    ];
  }
  if (pathname.startsWith("/buildings/")) {
    return [
      { label: "Ký túc xá" },
      { label: "Tòa nhà" },
      { label: "Chi tiết" },
    ];
  }
  if (pathname.startsWith("/floors/")) {
    return [{ label: "Ký túc xá" }, { label: "Tầng" }, { label: "Chi tiết" }];
  }
  const studentRouteBreadcrumbs: Record<string, BreadcrumbItem[]> = {
    "/dashboard": [{ label: "Trang chủ" }, { label: "Tổng quan" }],
    "/reference-dashboard": [
      { label: "Mẫu giao diện" },
      { label: "Tổng quan KTX" },
    ],
    "/student/register": [
      { label: "Trang chủ" },
      { label: "Không gian sinh viên" },
      { label: "Đăng ký phòng" },
    ],
    "/student/registration-history": [
      { label: "Trang chủ" },
      { label: "Không gian sinh viên" },
      { label: "Lịch sử đăng ký" },
    ],
    "/student/room-selection": [
      { label: "Trang chủ" },
      { label: "Không gian sinh viên" },
      { label: "Chọn phòng" },
    ],
    "/student/payments": [
      { label: "Trang chủ" },
      { label: "Không gian sinh viên" },
      { label: "Thanh toán" },
    ],
  };
  const studentBreadcrumbs = studentRouteBreadcrumbs[pathname];
  if (studentBreadcrumbs) return studentBreadcrumbs;

  for (const group of navigationGroups) {
    for (const item of group.items) {
      if (item.to === pathname)
        return withoutDuplicateLabels([
          { label: group.label },
          { label: item.title },
        ]);
      const child = item.children?.find(
        (candidate) => candidate.to === pathname,
      );
      if (child)
        return withoutDuplicateLabels([
          { label: group.label },
          { label: item.title },
          { label: child.title },
        ]);
    }
  }
  const hidden = hiddenRouteMeta.find((item) => item.to === pathname);
  return hidden ? [{ label: hidden.title }] : [{ label: "Quản trị" }];
}
